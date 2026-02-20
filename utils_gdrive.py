"""
Google Drive integration for GEM Intern.
Uses OAuth 2.0 (Desktop App flow) - user logs in via browser, no service account JSON needed.
"""

import os
import io
import json
from typing import Optional, List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# OAuth scopes
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Token storage path (next to settings.json)
_TOKEN_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(_TOKEN_DIR, "gdrive_token.json")

# App folder name in Drive root
APP_FOLDER_NAME = "GEMintern"
DOCS_SUBFOLDER = "docs"


class GoogleDriveClient:
    """Google Drive client using OAuth 2.0 Desktop App flow."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._creds: Optional[Credentials] = None
        self._service = None

    # ========================================
    # Authentication
    # ========================================

    @property
    def is_authenticated(self) -> bool:
        return self._creds is not None and self._creds.valid

    @property
    def user_email(self) -> str:
        """Return logged-in user's email (from token info)."""
        if self._creds and hasattr(self._creds, 'token'):
            try:
                about = self._get_service().files().get(
                    fileId='root', fields='owners'
                ).execute()
                owners = about.get('owners', [])
                if owners:
                    return owners[0].get('emailAddress', '')
            except Exception:
                pass
        return ""

    def load_saved_token(self) -> bool:
        """Try to load and refresh a previously saved token. Returns True if valid."""
        if os.path.exists(TOKEN_PATH):
            try:
                self._creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
                if self._creds and self._creds.expired and self._creds.refresh_token:
                    self._creds.refresh(Request())
                    self._save_token()
                if self._creds and self._creds.valid:
                    self._service = None  # reset service to use new creds
                    return True
            except Exception:
                self._creds = None
        return False

    def login(self) -> bool:
        """Open browser for Google OAuth login. Returns True on success."""
        client_config = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        try:
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            self._creds = flow.run_local_server(
                port=0,
                prompt="consent",
                success_message="Google Drive 로그인 성공! 이 창을 닫아도 됩니다.",
            )
            self._save_token()
            self._service = None
            return True
        except Exception as e:
            print(f"Google Drive login error: {e}")
            return False

    def logout(self):
        """Clear stored credentials."""
        self._creds = None
        self._service = None
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)

    def _save_token(self):
        if self._creds:
            with open(TOKEN_PATH, "w") as f:
                f.write(self._creds.to_json())

    def _get_service(self):
        if self._service is None:
            if not self._creds or not self._creds.valid:
                raise RuntimeError("Google Drive에 로그인되어 있지 않습니다.")
            self._service = build("drive", "v3", credentials=self._creds)
        return self._service

    # ========================================
    # Folder operations
    # ========================================

    def list_files(self, folder_id: str = "root") -> List[Dict[str, Any]]:
        """List files/folders in a folder."""
        service = self._get_service()
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size, modifiedTime)",
            orderBy="name",
            pageSize=200,
        ).execute()
        return results.get("files", [])

    def find_folder(self, parent_id: str, name: str) -> Optional[Dict]:
        """Find a folder by name under parent. Returns file metadata or None."""
        service = self._get_service()
        query = (
            f"'{parent_id}' in parents and "
            f"name = '{name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])
        return files[0] if files else None

    def find_file(self, parent_id: str, name: str) -> Optional[Dict]:
        """Find a file by name under parent."""
        service = self._get_service()
        query = (
            f"'{parent_id}' in parents and "
            f"name = '{name}' and "
            f"mimeType != 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])
        return files[0] if files else None

    def create_folder(self, parent_id: str, name: str) -> Dict:
        """Create a folder."""
        service = self._get_service()
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = service.files().create(body=metadata, fields="id, name").execute()
        return folder

    def ensure_folder(self, parent_id: str, name: str) -> str:
        """Ensure folder exists, return its ID."""
        existing = self.find_folder(parent_id, name)
        if existing:
            return existing["id"]
        created = self.create_folder(parent_id, name)
        return created["id"]

    def ensure_app_folder(self) -> str:
        """Ensure 'GEMintern' folder in Drive root."""
        return self.ensure_folder("root", APP_FOLDER_NAME)

    def ensure_project_folder(self, project_name: str) -> str:
        """Ensure 'GEMintern/{project}/docs/' structure. Returns docs folder ID."""
        app_id = self.ensure_app_folder()
        proj_id = self.ensure_folder(app_id, project_name)
        docs_id = self.ensure_folder(proj_id, DOCS_SUBFOLDER)
        return docs_id

    # ========================================
    # File operations
    # ========================================

    def upload_file(self, parent_id: str, filename: str, content: str) -> Dict:
        """Upload/update a text file (markdown)."""
        service = self._get_service()

        # Check if file already exists
        existing = self.find_file(parent_id, filename)

        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype="text/markdown",
            resumable=True,
        )

        if existing:
            # Update existing
            result = service.files().update(
                fileId=existing["id"],
                media_body=media,
                fields="id, name",
            ).execute()
        else:
            # Create new
            metadata = {"name": filename, "parents": [parent_id]}
            result = service.files().create(
                body=metadata,
                media_body=media,
                fields="id, name",
            ).execute()

        return result

    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file's content."""
        service = self._get_service()
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def delete_file(self, file_id: str) -> bool:
        """Move file to trash."""
        service = self._get_service()
        try:
            service.files().update(
                fileId=file_id, body={"trashed": True}
            ).execute()
            return True
        except Exception:
            return False

    # ========================================
    # High-level sync operations
    # ========================================

    def push_project(self, project_name: str, docs_dict: Dict[str, str]) -> Dict:
        """Upload all project docs to Drive."""
        if not docs_dict:
            return {"success": True, "uploaded": 0}

        try:
            docs_folder_id = self.ensure_project_folder(project_name)
            uploaded = 0
            for fname, content in docs_dict.items():
                md_name = fname if fname.endswith(".md") else f"{fname}.md"
                self.upload_file(docs_folder_id, md_name, content)
                uploaded += 1
            return {"success": True, "uploaded": uploaded, "total": len(docs_dict)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def pull_project(self, project_name: str) -> Dict[str, str]:
        """Download all .md files from Drive project folder. Returns {filename: content}."""
        result = {}
        try:
            app_folder = self.find_folder("root", APP_FOLDER_NAME)
            if not app_folder:
                return result

            proj_folder = self.find_folder(app_folder["id"], project_name)
            if not proj_folder:
                return result

            docs_folder = self.find_folder(proj_folder["id"], DOCS_SUBFOLDER)
            if not docs_folder:
                return result

            files = self.list_files(docs_folder["id"])
            for f in files:
                if f["name"].endswith(".md"):
                    content_bytes = self.download_file(f["id"])
                    if content_bytes:
                        result[f["name"]] = content_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            print(f"Google Drive pull error: {e}")

        return result
