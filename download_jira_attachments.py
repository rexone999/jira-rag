#!/usr/bin/env python3
"""
Script to download all attachments from 'Story' issues across all Jira projects accessible by the given credentials.

Reads credentials from credentials.json with structure:
{
  "email": "...",
  "api_token": "...",
  "domain": "https://<your-domain>.atlassian.net"
}

Saves attachments under ./downloads/{project_key}/{issue_key}/{filename}
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, HTTPError

CREDENTIALS_FILE = "credentials.json"
OUTPUT_DIR = Path("downloads")
ISSUE_PAGE_SIZE = 50  # number of issues per page in search
PROJECT_PAGE_SIZE = 50  # if using paginated project API

def load_credentials(path: str = CREDENTIALS_FILE) -> Dict[str, str]:
    """
    Load credentials JSON containing "email", "api_token", "domain".
    """
    if not os.path.isfile(path):
        print(f"Credentials file not found: {path}")
        raise FileNotFoundError(f"{path} not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key in ("email", "api_token", "domain"):
        if key not in data:
            print(f"Missing '{key}' in credentials file")
            raise KeyError(f"Missing '{key}' in credentials.json")
    # Ensure domain does not end with a slash
    domain = data["domain"].rstrip("/")
    return {
        "email": data["email"],
        "api_token": data["api_token"],
        "domain": domain
    }

def get_auth_session(email: str, api_token: str) -> requests.Session:
    """
    Returns a requests.Session configured for basic auth with Jira Cloud.
    """
    session = requests.Session()
    session.auth = HTTPBasicAuth(email, api_token)
    # Recommended headers
    session.headers.update({
        "Accept": "application/json"
    })
    return session

def fetch_all_projects(session: requests.Session, domain: str) -> List[Dict]:
    """
    Fetch all projects visible to the user.
    Uses GET /rest/api/3/project/search for pagination (if many projects),
    otherwise GET /rest/api/3/project returns all accessible projects.
    """
    projects = []
    # Attempt paginated endpoint first:
    url = f"{domain}/rest/api/3/project/search"
    start_at = 0
    while True:
        params = {
            "startAt": start_at,
            "maxResults": PROJECT_PAGE_SIZE,
        }
        try:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
        except HTTPError as he:
            # If 404 or unsupported, fallback to /project
            if resp.status_code == 404:
                print("/project/search not available; falling back to /project")
                break
            else:
                print(f"Error fetching projects (search): {he}")
                raise
        data = resp.json()
        values = data.get("values", [])
        projects.extend(values)
        total = data.get("total", 0)
        count = len(projects)
        print(f"Fetched {count}/{total} projects")
        if count >= total:
            break
        start_at += len(values)
        # small delay to avoid rate limits
        time.sleep(0.1)
    if not projects:
        # fallback
        url2 = f"{domain}/rest/api/3/project"
        try:
            resp2 = session.get(url2, timeout=30)
            resp2.raise_for_status()
            projects = resp2.json()
            print(f"Fetched {len(projects)} projects via fallback endpoint")
        except Exception as e:
            print(f"Failed to fetch projects via fallback: {e}")
            raise
    return projects

def search_issues_for_project(session: requests.Session, domain: str, project_key: str) -> List[Dict]:
    """
    Search for issues in the given project with issuetype = Story.
    Returns list of issues (as JSON objects) including 'key' and 'fields' with 'attachment'.
    Paginates through all results.
    """
    issues = []
    start_at = 0
    url = f"{domain}/rest/api/3/search"
    jql = f'project = "{project_key}" AND issuetype = Story'
    # Request attachment field with proper expansion
    fields = "key,attachment"
    expand = "attachment"
    while True:
        params = {
            "jql": jql,
            "fields": fields,
            "expand": expand,
            "startAt": start_at,
            "maxResults": ISSUE_PAGE_SIZE
        }
        try:
            resp = session.get(url, params=params, timeout=30)
            # Handle rate limiting
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"Rate limited, sleeping for {retry_after} seconds")
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
        except HTTPError as he:
            print(f"Error searching issues in project {project_key}: {he}")
            break
        data = resp.json()
        batch = data.get("issues", [])
        issues.extend(batch)
        total = data.get("total", 0)
        print(f"Project {project_key}: fetched {len(issues)}/{total} issues of type Story")
        if len(issues) >= total:
            break
        start_at += len(batch)
        time.sleep(0.1)
    return issues

def is_downloadable_attachment(attachment: Dict) -> bool:
    """
    Determine if the given attachment should be downloaded.
    Currently downloads all attachments - you can add filtering logic here if needed.
    """
    filename = attachment.get("filename", "")
    mime_type = attachment.get("mimeType") or attachment.get("contentType") or ""
    
    # Skip if no filename
    if not filename:
        return False
    
    # You can add exclusion logic here if needed, for now download everything
    return True

def download_attachment(session: requests.Session, url: str, save_path: Path):
    """
    Download a single attachment from the given URL to save_path.
    """
    try:
        resp = session.get(url, stream=True, timeout=60)
        # Handle rate limiting
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 5))
            print(f"Rate limited when downloading {url}. Sleeping for {retry_after} seconds.")
            time.sleep(retry_after)
            return download_attachment(session, url, save_path)  # recursive retry once
        resp.raise_for_status()
        # Write to file in chunks
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Downloaded attachment to {save_path}")
    except RequestException as e:
        print(f"Failed to download {url}: {e}")

def main():
    # Load credentials
    creds = load_credentials()
    email = creds["email"]
    api_token = creds["api_token"]
    domain = creds["domain"]
    session = get_auth_session(email, api_token)

    # Fetch all projects
    print("Fetching all accessible projects...")
    try:
        projects = fetch_all_projects(session, domain)
    except Exception as e:
        print(f"Could not fetch projects: {e}")
        return

    if not projects:
        print("No projects found. Exiting.")
        return

    print(f"Total projects to process: {len(projects)}")

    # Iterate projects
    total_attachments = 0
    for proj in projects:
        project_key = proj.get("key")
        project_name = proj.get("name", "")
        if not project_key:
            continue
        print(f"Processing project: {project_key} ({project_name})")

        # Search for Story issues
        issues = search_issues_for_project(session, domain, project_key)
        if not issues:
            print(f"No Story issues found in project {project_key}")
            continue

        # For each issue, check attachments
        for issue in issues:
            issue_key = issue.get("key")
            fields = issue.get("fields", {})
            attachments = fields.get("attachment", [])
            
            # Debug: Print detailed attachment info
            print(f"Issue {issue_key}: Found {len(attachments)} total attachments")
            for i, att in enumerate(attachments):
                print(f"  Attachment {i+1}: {att.get('filename', 'NO_FILENAME')} - {att.get('mimeType', 'NO_MIMETYPE')}")
            
            if not attachments:
                continue
            
            print(f"Processing issue {issue_key} with {len(attachments)} attachments")
            
            for att in attachments:
                filename = att.get("filename", "unknown")
                mime_type = att.get("mimeType", "unknown")
                
                print(f"  Checking attachment: {filename} ({mime_type})")
                
                if not is_downloadable_attachment(att):
                    print(f"    -> Skipping attachment (filtered out)")
                    continue
                
                print(f"    -> Will download this attachment")
                
                # Download
                content_url = att.get("content")
                if not content_url or not filename:
                    print(f"    -> Missing content URL or filename, skipping")
                    continue
                # Prepare save path: downloads/{project_key}/{issue_key}/{filename}
                save_dir = OUTPUT_DIR / project_key / issue_key
                save_path = save_dir / filename
                
                # Skip if already exists
                if save_path.exists():
                    print(f"Skipping existing file: {save_path}")
                    continue
                
                print(f"Downloading attachment: {filename} from {issue_key}")
                download_attachment(session, content_url, save_path)
                total_attachments += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.2)

    print(f"Download complete! Total attachments downloaded: {total_attachments}")

if __name__ == "__main__":
    main()
