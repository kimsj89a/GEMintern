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
        self.scopes = scopes or ["Files.Read", "User.Read"]
        self.redirect_uri = redirect_uri or "http://localhost:8501"
        
        # Initialize MSAL Public Client (for Device Code or Interactive flow)
        # Note: Streamlit runs on server, but for "import", we act as a public client in some flows,
        # or confidential if we had a secret. Here we assume implicit/code flow for simplicity in Streamlit.
        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            client_credential=None, # We are using strictly public client flow or just constructing URLs manually if needed
            # Actually for Streamlit, the best way without a backend callback handler is often 
            # the "Device Code Flow" or just constructing the auth URL manually and asking user to paste code/token.
            # But let's try to support a standard flow if we can. 
            # For simplicity in this "Intern" app, we might use the Device Flow which is easiest for scripts,
            # but for web, we need a redirect.
        )
        # Re-init as Public for cleaner usage if no secret
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
