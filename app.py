from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
import math
from urllib.parse import unquote
from werkzeug.utils import secure_filename

# Import your existing components
from gemini_test import (
    initialize_gemini, 
    generate_search_queries, 
    search_related_tickets, 
    create_jira_ticket_content,
    parse_ticket_content,
    create_jira_ticket,
    load_jira_config
)

# Import search_rag functions
from search_rag import (
    search_similar,
    search_tickets,
    search_documents
)

# Import PDF and image processing functions
from pdf_processor import process_pdf  # Use the existing process_pdf
from image_breaker import analyze_image

app = Flask(__name__)

def get_pdf_context_as_string(pdf_path):
    """
    Wrapper to use process_pdf and return the extracted content as a string.
    """
    from pathlib import Path
    import io
    import sys

    # Redirect stdout to capture process_pdf's print output (if needed)
    old_stdout = sys.stdout
    sys.stdout = mystdout = io.StringIO()
    # Prepare containers to collect extracted content
    extracted = {"text": [], "tables": [], "images": []}

    # Patch save_pdf_content to collect content instead of saving to disk
    import pdf_processor
    original_save_pdf_content = pdf_processor.save_pdf_content

    def collect_content(pdf_path, texts, tables, image_contexts):
        if texts:
            extracted["text"].extend(texts)
        if tables:
            extracted["tables"].extend(tables)
        if image_contexts:
            extracted["images"].extend(image_contexts)

    pdf_processor.save_pdf_content = collect_content
    try:
        process_pdf(pdf_path)
    finally:
        pdf_processor.save_pdf_content = original_save_pdf_content
        sys.stdout = old_stdout

    # Combine all extracted content into a single string
    context = ""
    if extracted["text"]:
        context += "\n".join(extracted["text"]) + "\n"
    if extracted["tables"]:
        context += "\n".join(extracted["tables"]) + "\n"
    if extracted["images"]:
        context += "\n".join(extracted["images"]) + "\n"
    return context.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create-story', methods=['POST'])
def create_story():
    try:
        # Accept both JSON and multipart form
        if request.content_type.startswith('multipart/form-data'):
            requirement = request.form.get('requirement', '')
            create_in_jira = request.form.get('create_in_jira', 'false') == 'true'
            doc_file = request.files.get('docInput')
            img_file = request.files.get('imgInput')
        else:
            data = request.get_json()
            requirement = data.get('requirement', '')
            create_in_jira = data.get('create_in_jira', False)
            doc_file = None
            img_file = None

        if not requirement:
            return jsonify({'error': 'Requirement is required'}), 400

        # Process document and image if provided
        doc_context = None
        if doc_file:
            filename = secure_filename(doc_file.filename)
            temp_path = os.path.join('temp_uploads', filename)
            os.makedirs('temp_uploads', exist_ok=True)
            doc_file.save(temp_path)
            # Use process_pdf and collect context as string
            doc_context = get_pdf_context_as_string(temp_path)
            os.remove(temp_path)
        img_context = None
        if img_file:
            filename = secure_filename(img_file.filename)
            temp_path = os.path.join('temp_uploads', filename)
            os.makedirs('temp_uploads', exist_ok=True)
            img_file.save(temp_path)
            img_context = analyze_image(temp_path)  # Should return extracted image context
            os.remove(temp_path)

        # Combine contexts if both are present
        extra_context = None
        if doc_context and img_context:
            extra_context = f"Document Context:\n{doc_context}\n\nImage Context:\n{img_context}"
        elif doc_context:
            extra_context = doc_context
        elif img_context:
            extra_context = img_context

        # Initialize Gemini
        client = initialize_gemini()
        if not client:
            return jsonify({'error': 'Failed to initialize Gemini AI client. Check API_KEY.txt'}), 500
        
        # Load JIRA config
        jira_config = load_jira_config()
        
        # Step 1: Generate search queries
        queries = generate_search_queries(client, requirement)
        
        # Step 2: Search for related tickets
        related_tickets = []
        if queries:
            related_tickets = search_related_tickets(queries)
        
        # Step 3: Generate JIRA ticket content (now with extra_context)
        ticket_content = create_jira_ticket_content(client, requirement, related_tickets, extra_context)
        
        if not ticket_content:
            return jsonify({'error': 'Failed to generate ticket content'}), 500
        
        # Parse the generated content
        ticket_data = parse_ticket_content(ticket_content)
        
        # Clean up results to ensure JSON serializability (replace NaN/inf with None)
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean(v) for v in obj]
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            else:
                return obj

        response_data = {
            'success': True,
            'ticket_content': ticket_content,
            'ticket_data': ticket_data,
            'related_tickets_count': len(related_tickets),
            'search_queries': queries,
            'related_tickets': related_tickets  # Return top 3 for display
        }
        
        # Step 4: Create in JIRA if requested
        if create_in_jira and jira_config:
            ticket_key, ticket_url = create_jira_ticket(jira_config, ticket_data)
            
            if ticket_key:
                response_data.update({
                    'jira_created': True,
                    'ticket_key': ticket_key,
                    'ticket_url': ticket_url
                })
            else:
                response_data.update({
                    'jira_created': False,
                    'jira_error': 'Failed to create ticket in JIRA'
                })
        elif create_in_jira and not jira_config:
            response_data.update({
                'jira_created': False,
                'jira_error': 'JIRA configuration not found. Create jira_config.json'
            })

        # Clean the response before sending
        cleaned_response = clean(response_data)
        return jsonify(cleaned_response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search-tickets', methods=['POST'])
def search_tickets_route():
    try:
        data = request.get_json()
        search_query = data.get('search_query', '')
        print(f"[DEBUG] Received search query: {search_query}")

        if not search_query:
            print("[DEBUG] No search query provided.")
            return jsonify({'error': 'Search query is required'}), 400

        # Search for tickets using the search_rag functions
        search_results = search_similar(search_query, similarity_threshold=0.4, top_k=15)
        print(f"[DEBUG] search_similar returned {len(search_results)} results with threshold 0.4")

        if not search_results:
            search_results = search_similar(search_query, similarity_threshold=0.3, top_k=15)
            print(f"[DEBUG] search_similar returned {len(search_results)} results with threshold 0.3")

        # Clean up results to ensure JSON serializability (replace NaN/inf with None)
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean(v) for v in obj]
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            else:
                return obj

        cleaned_results = clean(search_results)
        print(f"[DEBUG] Cleaned results for JSON serialization.")

        response_data = {
            'success': True,
            'search_query': search_query,
            'results_count': len(cleaned_results),
            'search_results': cleaned_results
        }

        print(f"[DEBUG] Sending response with {len(cleaned_results)} results.")
        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] Exception in /search-tickets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/downloads/<path:filename>')
def download_file(filename):
    downloads_dir = os.path.join(os.getcwd(), 'downloads')
    print(f"[DEBUG] Download request for: {filename} from {downloads_dir}")

    # Remove suffixes to get the original filename (no extension)
    for suffix in ['_tables.txt', '_text.txt', '_image_contexts.txt']:
        if filename.endswith(suffix):
            filename = filename[:-len(suffix)]
            break

    # Decode URL encoding (e.g., %20 to space)
    filename = unquote(filename)
    print(f"[DEBUG] Normalized filename for search: {filename}")

    # Search for any file with the same base name (case-insensitive, any extension)
    for root, dirs, files in os.walk(downloads_dir):
        for f in files:
            base, ext = os.path.splitext(f)
            if base.lower() == filename.lower():
                found_path = os.path.join(root, f)
                print(f"[DEBUG] Found file at: {found_path}")
                rel_dir = os.path.relpath(root, downloads_dir)
                return send_from_directory(os.path.join(downloads_dir, rel_dir), f, as_attachment=True)
    print(f"[ERROR] File not found: {filename}")
    return "File not found", 404

@app.route('/edit-ticket')
def edit_ticket():
    return render_template('edit_ticket.html')

@app.route('/create-final-ticket', methods=['POST'])
def create_final_ticket():
    try:
        data = request.get_json()
        # Extract all possible fields from the frontend form
        ticket_data = data.get('ticket_data', {})
        create_in_jira = data.get('create_in_jira', False)
        ticket_content = data.get('ticket_content', None)

        # Explicitly extract all fields that may be present in the form
        summary = ticket_data.get('summary') or ''
        description = ticket_data.get('description') or ''
        issue_type = ticket_data.get('issuetype') or ticket_data.get('issue_type') or 'Story'
        priority = ticket_data.get('priority') or 'Medium'
        acceptance_criteria = ticket_data.get('acceptance_criteria') or ''
        story_points = ticket_data.get('story_points') or ''
        labels = ticket_data.get('labels') or []
        if isinstance(labels, str):
            labels = [l.strip() for l in labels.split(',') if l.strip()]

        # Clean up ticket_data to ensure JSON serializability (replace NaN/inf with None)
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean(v) for v in obj]
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            else:
                return obj

        # If ticket_content is present, parse it to get all possible fields
        parsed_data = {}
        if ticket_content:
            parsed_data = parse_ticket_content(ticket_content)
        # Merge/override with user-edited fields (user-edited fields take precedence)
        merged_data = {**parsed_data, **ticket_data}
        # Ensure all fields are present and up-to-date
        merged_data.update({
            'summary': summary,
            'title': summary,
            'description': description,
            'issue_type': issue_type,
            'priority': priority,
            'acceptance_criteria': acceptance_criteria,
            'story_points': story_points,
            'labels': labels,
        })
        merged_data = clean(merged_data)

        # Ensure 'title' and 'issue_type' keys exist for JIRA creation
        if 'title' not in merged_data or not merged_data['title']:
            merged_data['title'] = merged_data.get('summary', 'Untitled')
        if 'issue_type' not in merged_data or not merged_data['issue_type']:
            merged_data['issue_type'] = merged_data.get('issuetype', 'Task')

        # Load JIRA config
        jira_config = load_jira_config()

        response_data = {
            'success': True
        }

        # Step 4: Create in JIRA if requested
        if create_in_jira and jira_config:
            ticket_key, ticket_url = create_jira_ticket(jira_config, merged_data)
            if ticket_key:
                response_data.update({
                    'jira_created': True,
                    'ticket_key': ticket_key,
                    'ticket_url': ticket_url
                })
            else:
                response_data.update({
                    'jira_created': False,
                    'jira_error': 'Failed to create ticket in JIRA'
                })
        elif create_in_jira and not jira_config:
            response_data.update({
                'jira_created': False,
                'jira_error': 'JIRA configuration not found. Create jira_config.json'
            })

        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Disable reloader for production-like stability
    # or use exclude_patterns to ignore system packages
    app.run(
        debug=True, 
        host='127.0.0.1', 
        port=5000,
        use_reloader=True,
        reloader_type='stat',  # Use stat reloader instead of watchdog
        extra_files=None  # Only watch specific files if needed
    )
