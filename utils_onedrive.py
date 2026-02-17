import msal
import requests
import os
import urllib.parse

# Microsoft Graph API Endpoints
GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'

class OneDriveClient:
    def __init__(self, client_id, authority=None, scopes=None, redirect_uri=None):
        self.client_id = client_id
        self.authority = authority or "https://login.microsoftonline.com/common"
        self.scopes = scopes or ["Files.ReadWrite", "User.Read"]
        self.redirect_uri = redirect_uri or "http://localhost:8501"

        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority
        )

    def get_auth_url(self):
        """Generates the authorization URL for the user to log in."""
        auth_url = self.app.get_authorization_request_url(
            self.scopes,
            redirect_uri=self.redirect_uri
        )
        return auth_url

    def acquire_token_from_code(self, code):
        """Exchanges the authorization code for an access token."""
        result = self.app.acquire_token_by_authorization_code(
            code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        return result

    def get_headers(self, access_token):
        return {
            'Authorization': 'Bearer ' + access_token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def get_user_info(self, access_token):
        """Get current user's profile."""
        headers = self.get_headers(access_token)
        response = requests.get(f'{GRAPH_API_ENDPOINT}/me', headers=headers)
        if response.status_code == 200:
            return response.json()
        return None

    def list_files(self, access_token, folder_id=None):
        """Lists files in the root or specified folder."""
        headers = self.get_headers(access_token)
        if folder_id:
            url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{folder_id}/children'
        else:
            url = f'{GRAPH_API_ENDPOINT}/me/drive/root/children'
            
        # Select specific fields to reduce payload
        params = {
            '$select': 'id,name,folder,file,size,lastModifiedDateTime,webUrl'
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get('value', [])
        else:
            # Handle error (e.g., token expired)
            # print(f"Error listing files: {response.status_code} - {response.text}")
            return []

    def download_file(self, access_token, file_id):
        """Downloads a file by ID."""
        headers = self.get_headers(access_token)
        url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{file_id}/content'

        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            return response.content
        return None

    # ========================================
    # Write operations
    # ========================================

    def upload_file(self, access_token, parent_id, filename, content_bytes):
        """Upload a file (up to 250MB) into a folder.
        PUT /me/drive/items/{parent-id}:/{filename}:/content
        """
        safe_name = urllib.parse.quote(filename)
        url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{parent_id}:/{safe_name}:/content'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream',
        }
        if isinstance(content_bytes, str):
            content_bytes = content_bytes.encode('utf-8')
        resp = requests.put(url, headers=headers, data=content_bytes)
        if resp.status_code in (200, 201):
            return resp.json()
        return {"error": resp.status_code, "message": resp.text}

    def update_file(self, access_token, file_id, content_bytes):
        """Update an existing file's contents.
        PUT /me/drive/items/{file-id}/content
        """
        url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{file_id}/content'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream',
        }
        if isinstance(content_bytes, str):
            content_bytes = content_bytes.encode('utf-8')
        resp = requests.put(url, headers=headers, data=content_bytes)
        if resp.status_code in (200, 201):
            return resp.json()
        return {"error": resp.status_code, "message": resp.text}

    def create_folder(self, access_token, parent_id, folder_name):
        """Create a folder under parent_id.
        POST /me/drive/items/{parent-id}/children
        """
        url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{parent_id}/children'
        headers = self.get_headers(access_token)
        body = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code in (200, 201):
            return resp.json()
        return {"error": resp.status_code, "message": resp.text}

    def delete_file(self, access_token, file_id):
        """Delete (move to recycle bin) a file or folder.
        DELETE /me/drive/items/{file-id}
        """
        url = f'{GRAPH_API_ENDPOINT}/me/drive/items/{file_id}'
        headers = {'Authorization': f'Bearer {access_token}'}
        resp = requests.delete(url, headers=headers)
        return resp.status_code == 204

    def find_item_by_name(self, access_token, parent_id, name):
        """Find a child item by name under parent_id. Returns item dict or None."""
        items = self.list_files(access_token, parent_id)
        for item in items:
            if item.get("name") == name:
                return item
        return None

    def ensure_app_folder(self, access_token):
        """Ensure 'GEMintern' folder exists in OneDrive root. Returns folder ID."""
        # Search in root
        items = self.list_files(access_token)
        for item in items:
            if item.get("name") == "GEMintern" and "folder" in item:
                return item["id"]
        # Create if not found
        result = self.create_folder(access_token, "root", "GEMintern")
        return result.get("id")

    def ensure_project_folder(self, access_token, project_name):
        """Ensure 'GEMintern/{project_name}/docs/' structure exists. Returns docs folder ID."""
        app_folder_id = self.ensure_app_folder(access_token)
        if not app_folder_id:
            return None

        # Project folder
        proj = self.find_item_by_name(access_token, app_folder_id, project_name)
        if not proj:
            proj = self.create_folder(access_token, app_folder_id, project_name)
        proj_id = proj.get("id")
        if not proj_id:
            return None

        # docs sub-folder
        docs = self.find_item_by_name(access_token, proj_id, "docs")
        if not docs:
            docs = self.create_folder(access_token, proj_id, "docs")
        return docs.get("id")
