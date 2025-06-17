from flask import Flask, render_template, request, jsonify
import json
import os

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
