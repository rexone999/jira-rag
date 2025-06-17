import requests
import json
import os
from datetime import datetime
import pandas as pd
import time

class AtlassianExtractor:
    def __init__(self):
        # Load credentials from JSON file
        try:
            with open('credentials.json', 'r') as f:
                credentials = json.load(f)
        except FileNotFoundError:
            raise ValueError("credentials.json file not found. Please create it with your Atlassian credentials.")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in credentials.json file.")
        
        self.email = credentials.get('email')
        self.api_token = credentials.get('api_token')
        domain_url = credentials.get('domain')
        
        if not all([self.email, self.api_token, domain_url]):
            raise ValueError("Please set email, api_token, and domain in credentials.json file")
        
        # Extract domain name from URL if full URL is provided
        if domain_url.startswith('http'):
            self.domain = domain_url.replace('https://', '').replace('http://', '')
        else:
            self.domain = domain_url
        
        self.auth = (self.email, self.api_token)
        self.jira_base_url = f"https://{self.domain}/rest/api/3"
        self.confluence_base_url = f"https://{self.domain}/wiki/rest/api"
        
    def extract_jira_tickets(self, max_results=1000):
        """Extract all JIRA tickets from all projects"""
        print("Starting JIRA ticket extraction from all projects...")
        all_tickets = []
        start_at = 0
        
        while True:
            # JQL query to get all tickets ordered by creation date
            jql = "order by created DESC"
            
            url = f"{self.jira_base_url}/search"
            params = {
                'jql': jql,
                'startAt': start_at,
                'maxResults': min(100, max_results - len(all_tickets)),
                'fields': 'summary,description,status,priority,created,updated,assignee,reporter,issuetype,labels,components,project'
            }
            
            response = requests.get(url, auth=self.auth, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching JIRA tickets: {response.status_code} - {response.text}")
                break
            
            data = response.json()
            issues = data['issues']
            
            if not issues:
                break
                
            for issue in issues:
                ticket_data = {
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
                }
                all_tickets.append(ticket_data)
            
            print(f"Extracted {len(all_tickets)} tickets so far...")
            
            if len(all_tickets) >= max_results or len(issues) < params['maxResults']:
                break
                
            start_at += len(issues)
            time.sleep(0.1)  # Rate limiting
        
        print(f"Total JIRA tickets extracted: {len(all_tickets)}")
        
        # Print project summary
        if all_tickets:
            project_counts = {}
            for ticket in all_tickets:
                project_key = ticket['project_key']
                project_counts[project_key] = project_counts.get(project_key, 0) + 1
            
            print("Tickets by project:")
            for project, count in sorted(project_counts.items()):
                print(f"  {project}: {count} tickets")
        
        return all_tickets
    
    def extract_confluence_pages(self, max_results=1000):
        """Extract all Confluence pages"""
        print("Starting Confluence page extraction...")
        all_pages = []
        start_at = 0
        
        while True:
            url = f"{self.confluence_base_url}/content"
            params = {
                'start': start_at,
                'limit': min(100, max_results - len(all_pages)),
                'expand': 'body.storage,version,space,ancestors'
            }
            
            response = requests.get(url, auth=self.auth, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching Confluence pages: {response.status_code} - {response.text}")
                break
            
            data = response.json()
            pages = data['results']
            
            if not pages:
                break
            
            for page in pages:
                page_data = {
                    'id': page['id'],
                    'title': page['title'],
                    'content': page['body']['storage']['value'] if 'body' in page and 'storage' in page['body'] else '',
                    'space_key': page['space']['key'],
                    'space_name': page['space']['name'],
                    'created': page['version']['when'],
                    'version': page['version']['number'],
                    'url': f"https://{self.domain}/wiki{page['_links']['webui']}"
                }
                all_pages.append(page_data)
            
            print(f"Extracted {len(all_pages)} pages so far...")
            
            if len(all_pages) >= max_results or len(pages) < params['limit']:
                break
                
            start_at += len(pages)
            time.sleep(0.1)  # Rate limiting
        
        print(f"Total Confluence pages extracted: {len(all_pages)}")
        return all_pages
    
    def save_data(self, jira_tickets, confluence_pages):
        """Save extracted data to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        # Save JIRA tickets
        jira_df = pd.DataFrame(jira_tickets)
        jira_csv_path = f"data/jira_tickets_{timestamp}.csv"
        
        jira_df.to_csv(jira_csv_path, index=False, encoding='utf-8')
        
        # Save Confluence pages
        confluence_df = pd.DataFrame(confluence_pages)
        confluence_csv_path = f"data/confluence_pages_{timestamp}.csv"
        
        confluence_df.to_csv(confluence_csv_path, index=False, encoding='utf-8')
        
        print(f"Data saved:")
        print(f"  JIRA: {jira_csv_path}")
        print(f"  Confluence: {confluence_csv_path}")

def main():
    try:
        extractor = AtlassianExtractor()
        
        # Extract data
        jira_tickets = extractor.extract_jira_tickets()
        confluence_pages = extractor.extract_confluence_pages()
        
        # Save data
        extractor.save_data(jira_tickets, confluence_pages)
        
        print("\nExtraction completed successfully!")
        print(f"Total items extracted: {len(jira_tickets)} JIRA tickets, {len(confluence_pages)} Confluence pages")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
