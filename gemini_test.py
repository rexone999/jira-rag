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

def classify_task_complexity(client, user_requirement, context):
    """Classify the task complexity as SMALL, MEDIUM, or BIG"""
    prompt = f"""
    Analyze this user requirement and classify its complexity:
    
    REQUIREMENT: "{user_requirement}"
    
    {context}
    
    Classify this task as one of the following based on scope, effort, and complexity:
    
    SMALL: Simple features, bug fixes, minor enhancements that can be completed in 1-2 stories
    - Examples: UI text changes, simple form additions, basic configuration updates
    
    MEDIUM: Moderate features requiring multiple components, integration work, needs 1 epic with 4-5 stories
    - Examples: New feature modules, API integrations, workflow enhancements
    
    BIG: Complex features, system-wide changes, major new functionality requiring 3-4 epics with 10-20 stories
    - Examples: Complete new systems, major architectural changes, large-scale integrations
    
    Return ONLY one word: SMALL, MEDIUM, or BIG
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        classification = response.text.strip().upper()
        if classification in ['SMALL', 'MEDIUM', 'BIG']:
            return classification
        else:
            return 'MEDIUM'  # Default fallback
    except Exception as e:
        print(f"Error classifying task complexity: {e}")
        return 'MEDIUM'  # Default fallback

def small_agent(client, user_requirement, context):
    """Generate 1-2 stories for SMALL tasks"""
    prompt = f"""
    Create 1-2 JIRA stories for this SMALL task:
    
    REQUIREMENT: "{user_requirement}"
    
    {context}
    
    Generate 1-2 user stories that cover this requirement completely. Each story should include:
    
    1. **Story Title**: Clear, concise title
    2. **Description**: Detailed description (MAX: 150 words)
    3. **Acceptance Criteria**: 3-4 specific, testable criteria (bullet points)
    4. **Story Points**: 1, 2, 3, 5, 8, or 13 based on complexity
    5. **Priority**: High/Medium/Low
    
    Format each story clearly and number them (Story 1, Story 2, etc.).
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        return response.text
    except Exception as e:
        print(f"Error in small_agent: {e}")
        return None

def medium_agent(client, user_requirement, context):
    """Generate 1 epic and 4-5 stories for MEDIUM tasks"""
    prompt = f"""
    Create 1 EPIC and 4-5 user stories for this MEDIUM task:
    
    REQUIREMENT: "{user_requirement}"
    
    {context}
    
    First, create 1 EPIC that encompasses the entire requirement:
    
    **EPIC:**
    1. **Epic Title**: High-level feature title
    2. **Epic Description**: Overview of the complete feature (MAX: 200 words)
    3. **Business Value**: Why this epic is important
    4. **Acceptance Criteria**: High-level criteria for epic completion
    
    Then create 4-5 user stories that break down this epic:
    
    **STORIES:**
    For each story include:
    1. **Story Title**: Clear, specific title
    2. **Description**: Detailed description (MAX: 150 words)
    3. **Acceptance Criteria**: 3-4 specific, testable criteria (bullet points)
    4. **Story Points**: 1, 2, 3, 5, 8, or 13 based on complexity
    5. **Priority**: High/Medium/Low
    6. **Epic Link**: Reference to the parent epic
    
    Number each story (Story 1, Story 2, etc.) and ensure they collectively complete the epic.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        return response.text
    except Exception as e:
        print(f"Error in medium_agent: {e}")
        return None

def large_agent(client, user_requirement, context):
    """Generate 3-4 epics and 10-20 stories for BIG tasks"""
    prompt = f"""
    Create 3-4 EPICS and 10-20 user stories for this BIG task:
    
    REQUIREMENT: "{user_requirement}"
    
    {context}
    
    First, create 3-4 EPICS that break down the requirement into major components:
    
    **EPICS:**
    For each epic include:
    1. **Epic Title**: High-level component title
    2. **Epic Description**: Overview of this component (MAX: 200 words)
    3. **Business Value**: Why this epic is important
    4. **Dependencies**: How this epic relates to others
    5. **Acceptance Criteria**: High-level criteria for epic completion
    
    Then create 10-20 user stories distributed across these epics:
    
    **STORIES:**
    For each story include:
    1. **Story Title**: Clear, specific title
    2. **Description**: Detailed description (MAX: 150 words)
    3. **Acceptance Criteria**: 3-4 specific, testable criteria (bullet points)
    4. **Story Points**: 1, 2, 3, 5, 8, or 13 based on complexity
    5. **Priority**: High/Medium/Low
    6. **Epic Link**: Reference to the parent epic
    7. **Dependencies**: Any dependencies on other stories
    
    Organize stories by epic and number them within each epic (Epic 1 - Story 1, Epic 1 - Story 2, etc.).
    Ensure the stories collectively complete all epics and the overall requirement.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        return response.text
    except Exception as e:
        print(f"Error in large_agent: {e}")
        return None

def create_jira_ticket_content(client, user_requirement, related_tickets, extra_context=None):
    """Generate JIRA ticket content using sequential agents based on task complexity"""
    
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
    
    if extra_context:
        context += f"\n\nADDITIONAL CONTEXT FROM USER DOCUMENTS/IMAGES:\n{extra_context}\n"
    
    # Step 1: Classify task complexity
    print("\n🤖 Step 1: Classifying task complexity...")
    complexity = classify_task_complexity(client, user_requirement, context)
    print(f"📊 Task classified as: {complexity}")
    
    # Step 2: Trigger appropriate agent based on complexity
    print(f"\n🤖 Step 2: Triggering {complexity.lower()}_agent...")
    
    if complexity == 'SMALL':
        return small_agent(client, user_requirement, context)
    elif complexity == 'MEDIUM':
        return medium_agent(client, user_requirement, context)
    elif complexity == 'BIG':
        return large_agent(client, user_requirement, context)
    else:
        # Fallback to medium if classification fails
        return medium_agent(client, user_requirement, context)

def parse_ticket_content(ticket_content):
    """
    Parse the LLM-generated content to extract tickets/epics.
    Returns a list of ticket dictionaries for creation.
    """
    tickets = []
    
    # Split content into sections for epics and stories
    lines = ticket_content.split('\n')
    current_ticket = {}
    
    for line in lines:
        line = line.strip()
        
        # Look for Epic or Story titles
        if line.startswith('**Epic') or line.startswith('**Story'):
            if current_ticket:
                tickets.append(current_ticket)
            current_ticket = {
                "title": "Untitled",
                "description": "",
                "issue_type": "Epic" if "Epic" in line else "Story",
                "priority": "Medium",
                "story_points": "3"
            }
        
        # Extract titles
        elif line.startswith('1. **Epic Title**') or line.startswith('1. **Story Title**'):
            title_text = line.split(':', 1)
            if len(title_text) > 1:
                current_ticket["title"] = title_text[1].strip()
        
        # Extract descriptions
        elif line.startswith('2. **Description**') or line.startswith('2. **Epic Description**'):
            desc_text = line.split(':', 1)
            if len(desc_text) > 1:
                current_ticket["description"] = desc_text[1].strip()
        
        # Extract priority
        elif 'Priority' in line and ':' in line:
            priority_text = line.split(':', 1)[1].strip()
            if priority_text in ['High', 'Medium', 'Low']:
                current_ticket["priority"] = priority_text
        
        # Extract story points
        elif 'Story Points' in line and ':' in line:
            points_text = line.split(':', 1)[1].strip()
            if points_text.isdigit():
                current_ticket["story_points"] = points_text
    
    # Add the last ticket
    if current_ticket:
        tickets.append(current_ticket)
    
    # If no structured tickets found, create a single ticket from the content
    if not tickets:
        # Fallback: treat entire content as a single story
        tickets.append({
            "title": "Generated Requirement",
            "description": ticket_content[:500] if len(ticket_content) > 500 else ticket_content,
            "issue_type": "Story",
            "priority": "Medium",
            "story_points": "3"
        })
    
    return tickets
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

def create_multiple_jira_tickets(jira_config, tickets_data):
    """Create multiple JIRA tickets and return results"""
    results = []
    
    for i, ticket_data in enumerate(tickets_data, 1):
        print(f"\n🔄 Creating ticket {i}/{len(tickets_data)}: {ticket_data['title']}")
        
        ticket_key, ticket_url = create_jira_ticket(jira_config, ticket_data)
        
        if ticket_key:
            results.append({
                'success': True,
                'key': ticket_key,
                'url': ticket_url,
                'title': ticket_data['title'],
                'type': ticket_data['issue_type']
            })
            print(f"✅ Created {ticket_data['issue_type']}: {ticket_key}")
        else:
            results.append({
                'success': False,
                'title': ticket_data['title'],
                'type': ticket_data['issue_type']
            })
            print(f"❌ Failed to create {ticket_data['issue_type']}: {ticket_data['title']}")
    
    return results

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
        
        # Step 3: Generate JIRA tickets based on complexity
        print("\n📋 Step 3: Generating JIRA tickets...")
        ticket_content = create_jira_ticket_content(client, user_requirement, related_tickets)
        
        if ticket_content:
            print("\n" + "="*80)
            print("🎟️  GENERATED JIRA TICKETS")
            print("="*80)
            print(ticket_content)
            print("="*80)
            
            # Ask for confirmation to create in JIRA
            if jira_config:
                create_ticket = input("\n❓ Do you want to create these tickets in JIRA? (Y/N): ").strip().upper()
                
                if create_ticket == 'Y':
                    print("\n🔄 Creating tickets in JIRA...")
                    
                    # Parse the generated content into multiple tickets
                    tickets_data = parse_ticket_content(ticket_content)
                    print(f"📊 Found {len(tickets_data)} tickets to create")
                    
                    # Create multiple tickets
                    results = create_multiple_jira_tickets(jira_config, tickets_data)
                    
                    # Summary of results
                    successful = [r for r in results if r['success']]
                    failed = [r for r in results if not r['success']]
                    
                    print(f"\n📊 CREATION SUMMARY:")
                    print(f"✅ Successfully created: {len(successful)} tickets")
                    print(f"❌ Failed to create: {len(failed)} tickets")
                    
                    if successful:
                        print(f"\n🎫 CREATED TICKETS:")
                        for ticket in successful:
                            print(f"   {ticket['type']}: {ticket['key']} - {ticket['title']}")
                            print(f"   🔗 {ticket['url']}")
                    
                    if failed:
                        print(f"\n❌ FAILED TICKETS:")
                        for ticket in failed:
                            print(f"   {ticket['type']}: {ticket['title']}")
                else:
                    print("📝 Tickets not created in JIRA")
            else:
                print("\n💡 JIRA integration not configured. Set up jira_config.json to create tickets directly.")
        else:
            print("❌ Failed to generate ticket content")

if __name__ == "__main__":
    create_jira_ticket_interactive()
