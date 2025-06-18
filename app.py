from flask import Flask, render_template, request, jsonify
import json
import os
import math

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

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create-story', methods=['POST'])
def create_story():
    try:
        data = request.get_json()
        requirement = data.get('requirement', '')
        create_in_jira = data.get('create_in_jira', False)
        
        if not requirement:
            return jsonify({'error': 'Requirement is required'}), 400
        
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
        
        # Step 3: Generate JIRA ticket content
        ticket_content = create_jira_ticket_content(client, requirement, related_tickets)
        
        if not ticket_content:
            return jsonify({'error': 'Failed to generate ticket content'}), 500
        
        # Parse the generated content
        ticket_data = parse_ticket_content(ticket_content)
        
        response_data = {
            'success': True,
            'ticket_content': ticket_content,
            'ticket_data': ticket_data,
            'related_tickets_count': len(related_tickets),
            'search_queries': queries,
            'related_tickets': related_tickets[:3]  # Return top 3 for display
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
        
        return jsonify(response_data)
    
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
