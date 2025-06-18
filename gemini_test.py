import os
from google import genai
import json
import requests
from requests.auth import HTTPBasicAuth
import re

def load_api_key():
    """Load API key from API_KEY.txt"""
    try:
        with open('API_KEY.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: API_KEY.txt file not found. Please create it with your Gemini API key.")
        return None

def initialize_gemini():
    """Initialize Gemini client"""
    api_key = load_api_key()
    if not api_key:
        return None
    
    return genai.Client(api_key=api_key)

def generate_search_queries(client, user_requirement):
    """Generate 1-2 search queries to find related tickets"""
    prompt = f"""
    Based on this user requirement for a new JIRA ticket:
    "{user_requirement}"
    
    Generate 1-2 specific search queries that would help find related existing tickets or documentation.
    These queries should focus on:
    - Similar features or functionality
    - Related technical components
    - Common issues or bugs in the same area
    
    Return only the search queries, one sentence per line, without numbering or explanations.
    Maximum 2 queries.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        queries = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
        return queries[:2]  # Limit to 2 queries
    except Exception as e:
        print(f"Error generating search queries: {e}")
        return []

def search_related_tickets(queries):
    """Search for related tickets using the generated queries"""
    # Import here to avoid circular imports
    from search_rag import search_with_fixed_threshold
    
    all_results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n🔍 Search Query {i}: {query}")
        print("=" * 50)
        
        results = search_with_fixed_threshold(query)
        all_results.extend(results)
        
        print(f"Found {len(results)} results for this query")
    
    # Remove duplicates based on URL
    unique_results = []
    seen_urls = set()
    for result in all_results:
        if result['url'] not in seen_urls:
            unique_results.append(result)
            seen_urls.add(result['url'])
    
    return unique_results

def create_jira_ticket_content(client, user_requirement, related_tickets, extra_context=None):
    """Generate JIRA ticket content based on requirement and related tickets"""
    
    # Prepare context from related tickets
    context = ""
    if related_tickets:
        context = "\n\nRELATED TICKETS FOUND:\n"
        for i, ticket in enumerate(related_tickets[:5], 1):  # Limit to top 5
            context += f"\n{i}. [{ticket['source'].upper()}] {ticket['title']}\n"
            context += f"   URL: {ticket['url']}\n"
            context += f"   Similarity: {ticket['similarity_score']:.3f}\n"
            
            if ticket['source'] == 'jira':
                metadata = ticket['metadata']
                context += f"   Status: {metadata['status']} | Priority: {metadata['priority']}\n"
                context += f"   Type: {metadata['issue_type']}\n"
            
            # Add brief content preview
            preview = ticket['text'][:200] + "..." if len(ticket['text']) > 200 else ticket['text']
            context += f"   Preview: {preview}\n"
    
    prompt = f"""
    Create a comprehensive JIRA ticket based on this requirement:
    "{user_requirement}"
    
    {context}
    """
    if extra_context:
        prompt += f"\n\nADDITIONAL CONTEXT FROM USER DOCUMENTS/IMAGES:\n{extra_context}\n"

    prompt += """
    Based on the related tickets above, create a detailed JIRA ticket that includes:
    
    1. **Title**: Clear, concise title for the ticket
    2. **Description**: Detailed description of what needs to be done (MAX:200 WORDS)
    3. **Acceptance Criteria**: Specific, testable criteria (use bullet points)(max 4 bullets)
    4. **Priority**: Suggest priority level (High/Medium/Low) with reasoning(one word answer)
    5. **Type**: Suggest ticket type (Story/Task/Bug/Epic)(one word answer)
    6. **Related Work**: Reference to similar tickets found (if any)(just the ticket number and title and description)
    7. **Technical Considerations**: Any technical aspects based on related tickets(max 200 words)
    8. **Story Points**: Generate a number of story points **(1 or 2 or 3 or 5 or 8 or 13)** based on complexity(Just the number and number only)  
    Format the response clearly with proper sections and bullet points.
    If related tickets show similar work was done before, mention how this ticket differs or builds upon that work.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        return response.text
    except Exception as e:
        print(f"Error generating JIRA ticket: {e}")
        return None

def parse_ticket_content(ticket_content):
    """
    Parse the LLM-generated ticket markdown to extract title and description.
    Returns a dict with at least 'summary' and 'description'.
    """
    # Extract title
    title_match = re.search(r"\**1\. Title:\**\s*(.+)", ticket_content)
    summary = title_match.group(1).strip() if title_match else "Untitled"

    # Extract description (from *2. Description:* to next numbered section or end)
    desc_match = re.search(r"\*2\. Description:\*\s*([\s\S]+?)(?:\n\s*\*\d+\.\s|\Z)", ticket_content)
    description = desc_match.group(1).strip() if desc_match else ticket_content

    # Extract priority
    severity_match = re.search(r"\*4\. Priority:\*\s*(\w+)", ticket_content)
    severity = severity_match.group(1).strip() if   severity_match else "Medium"

    # Extract story points
    story_points_match = re.search(r"\*8\. Story Points:\*\s*(\d+)", ticket_content)
    story_points = story_points_match.group(1).strip() if story_points_match else "1"

    # Optionally, include the rest of the ticket content as well
    return {
        "summary": summary,
        "description": description,
        "title": summary,  # Use summary as title
        "issue_type": "Story",
        "priority" : severity, # Default to Task if not specified
        "story_points": story_points  # Default to 1 if not specified
        # Add more fields if needed
    }
'''ticket_data = {
                    'id': issue['id'],
                    'key': issue['key'],
                    'project_key': issue['fields']['project']['key'],
                    'project_name': issue['fields']['project']['name'],
                    'summary': issue['fields']['summary'],
                    'description': issue['fields']['description'],
                    'status': issue['fields']['status']['name'],
                    'priority': issue['fields']['priority']['name'] if issue['fields']['priority'] else None,
                    'issue_type': issue['fields']['issuetype']['name'],
                    'created': issue['fields']['created'],
                    'updated': issue['fields']['updated'],
                    'assignee': issue['fields']['assignee']['displayName'] if issue['fields']['assignee'] else None,
                    'reporter': issue['fields']['reporter']['displayName'] if issue['fields']['reporter'] else None,
                    'labels': issue['fields']['labels'],
                    'components': [comp['name'] for comp in issue['fields']['components']],
                    'url': f"https://{self.domain}/browse/{issue['key']}"
                }'''
def create_jira_ticket(jira_config, ticket_data):
    """Create a JIRA ticket using the REST API"""
    url = f"{jira_config['url']}/rest/api/2/issue"
    
    auth = HTTPBasicAuth(jira_config['username'], jira_config['api_token'])
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Basic payload with only required fields
    payload = {
        "fields": {
            "project": {
                "key": jira_config['project_key']
            },
            "summary": ticket_data['title'],
            "description": ticket_data['description'],
            "issuetype": {
                "name": ticket_data['issue_type']  # Use name instead of ID
            }
        }
    }
    
    # Optionally add priority if it's configured in jira_config
    if jira_config.get('include_priority', False):
        payload["fields"]["priority"] = {
            "name": ticket_data['priority']
        }
    
    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        
        if response.status_code == 201:
            ticket_info = response.json()
            ticket_key = ticket_info['key']
            ticket_url = f"{jira_config['url']}/browse/{ticket_key}"
            return ticket_key, ticket_url
        else:
            print(f"Failed to create JIRA ticket. Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Try again without issue type if it failed
            if response.status_code == 400 and "issuetype" in response.text:
                print("Retrying with default Task issue type...")
                payload["fields"]["issuetype"] = {"name": "Task"}
                
                retry_response = requests.post(url, json=payload, headers=headers, auth=auth)
                if retry_response.status_code == 201:
                    ticket_info = retry_response.json()
                    ticket_key = ticket_info['key']
                    ticket_url = f"{jira_config['url']}/browse/{ticket_key}"
                    return ticket_key, ticket_url
            
            return None, None
            
    except Exception as e:
        print(f"Error creating JIRA ticket: {e}")
        return None, None

def load_jira_config():
    """Load JIRA configuration from jira_config.json"""
    try:
        with open('jira_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: jira_config.json not found. JIRA integration disabled.")
        print("Create jira_config.json with:")
        print('{"url": "your-jira-url", "username": "email", "api_token": "token", "project_key": "PROJECT", "include_priority": false}')
        return None

def create_jira_ticket_interactive():
    """Interactive JIRA ticket creation with Gemini"""
    print("🎯 JIRA Ticket Creator with AI Search")
    print("=" * 50)
    
    # Initialize Gemini
    client = initialize_gemini()
    if not client:
        return
    
    # Load JIRA config
    jira_config = load_jira_config()
    
    while True:
        user_requirement = input("\n📝 Enter your requirement for a new JIRA ticket (or 'quit' to exit): ").strip()
        
        if user_requirement.lower() in ['quit', 'exit', 'q']:
            break
            
        if not user_requirement:
            continue
        
        print(f"\n🤖 Processing requirement: {user_requirement}")
        
        # Step 1: Generate search queries
        print("\n📋 Step 1: Generating search queries...")
        queries = generate_search_queries(client, user_requirement)
        
        if queries:
            print(f"Generated {len(queries)} search queries:")
            for i, query in enumerate(queries, 1):
                print(f"  {i}. {query}")
        else:
            print("No search queries generated, proceeding without context...")
            queries = []
        
        # Step 2: Search for related tickets
        print("\n📋 Step 2: Searching for related tickets...")
        related_tickets = []
        if queries:
            related_tickets = search_related_tickets(queries)
            print(f"\n✅ Found {len(related_tickets)} unique related tickets")
        else:
            print("Skipping search due to no queries...")
        
        # Step 3: Generate JIRA ticket
        print("\n📋 Step 3: Generating JIRA ticket content...")
        ticket_content = create_jira_ticket_content(client, user_requirement, related_tickets)
        
        if ticket_content:
            print("\n" + "="*80)
            print("🎟️  GENERATED JIRA TICKET")
            print("="*80)
            print(ticket_content)
            print("="*80)
            
            # Ask for confirmation to create in JIRA
            if jira_config:
                create_ticket = input("\n❓ Do you want to create this ticket in JIRA? (Y/N): ").strip().upper()
                
                if create_ticket == 'Y':
                    print("\n🔄 Creating ticket in JIRA...")
                    
                    # Parse the generated content
                    ticket_data = parse_ticket_content(ticket_content)
                    
                    # Create the ticket
                    ticket_key, ticket_url = create_jira_ticket(jira_config, ticket_data)
                    
                    if ticket_key:
                        print(f"✅ Successfully created JIRA ticket!")
                        print(f"🎫 Ticket Key: {ticket_key}")
                        print(f"🔗 URL: {ticket_url}")
                    else:
                        print("❌ Failed to create JIRA ticket")
                else:
                    print("📝 Ticket not created in JIRA")
            else:
                print("\n💡 JIRA integration not configured. Set up jira_config.json to create tickets directly.")
        else:
            print("❌ Failed to generate ticket content")

if __name__ == "__main__":
    create_jira_ticket_interactive()
