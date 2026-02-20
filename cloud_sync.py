"""
Cloud synchronization layer for GEM Intern.
Bridges local file storage (core_rag) with OneDrive (documents) and Google Sheets (structured data).
"""

import traceback


class CloudSyncManager:
    def __init__(self, onedrive_client=None, onedrive_token=None,
                 gsheets_client=None, gdrive_client=None):
        """
        Args:
            onedrive_client: OneDriveClient instance (or None to disable)
            onedrive_token: access_token string for OneDrive API calls
            gsheets_client: GSheetsClient instance (or None to disable)
            gdrive_client: GoogleDriveClient instance (or None to disable)
        """
        self.onedrive = onedrive_client
        self.onedrive_token = onedrive_token
        self.gsheets = gsheets_client
        self.gdrive = gdrive_client
        self._last_error = None

    def set_onedrive_token(self, token):
        self.onedrive_token = token

    @property
    def onedrive_enabled(self):
        return self.onedrive is not None and self.onedrive_token is not None

    @property
    def gsheets_enabled(self):
        return self.gsheets is not None

    @property
    def gdrive_enabled(self):
        return self.gdrive is not None and self.gdrive.is_authenticated

    @property
    def last_error(self):
        return self._last_error

    # ========================================
    # Auto-sync event hooks (called from core_rag)
    # ========================================

    def on_document_saved(self, project_name, filename, content):
        """Called after a document is saved locally."""
        self._last_error = None
        # OneDrive: upload .md file
        if self.onedrive_enabled:
            try:
                docs_folder_id = self.onedrive.ensure_project_folder(
                    self.onedrive_token, project_name
                )
                if docs_folder_id:
                    md_name = filename if filename.endswith(".md") else f"{filename}.md"
                    self.onedrive.upload_file(
                        self.onedrive_token, docs_folder_id,
                        md_name, content
                    )
            except Exception as e:
                self._last_error = f"OneDrive upload: {e}"
                traceback.print_exc()

        # Google Drive: upload .md file
        if self.gdrive_enabled:
            try:
                docs_folder_id = self.gdrive.ensure_project_folder(project_name)
                if docs_folder_id:
                    md_name = filename if filename.endswith(".md") else f"{filename}.md"
                    self.gdrive.upload_file(docs_folder_id, md_name, content)
            except Exception as e:
                self._last_error = f"Google Drive upload: {e}"
                traceback.print_exc()

        # GSheets: log
        if self.gsheets_enabled:
            try:
                self.gsheets.append_work_log({
                    "action_type": "document_saved",
                    "project": project_name,
                    "details": f"Saved: {filename}",
                })
            except Exception as e:
                self._last_error = f"GSheets log: {e}"
                traceback.print_exc()

    def on_document_deleted(self, project_name, doc_name):
        """Called after a document is trashed locally."""
        self._last_error = None
        if self.gsheets_enabled:
            try:
                self.gsheets.append_work_log({
                    "action_type": "document_deleted",
                    "project": project_name,
                    "details": f"Trashed: {doc_name}",
                })
            except Exception as e:
                self._last_error = f"GSheets log: {e}"
                traceback.print_exc()

    def on_analysis_complete(self, project_name, template_type, model, result_preview):
        """Called after an AI analysis is completed."""
        self._last_error = None
        if self.gsheets_enabled:
            try:
                self.gsheets.append_analysis_record({
                    "project": project_name,
                    "template_type": template_type,
                    "model": model,
                    "summary": result_preview[:500] if result_preview else "",
                })
            except Exception as e:
                self._last_error = f"GSheets analysis record: {e}"
                traceback.print_exc()

    def on_ocr_complete(self, filename, engine, pages, status):
        """Called after OCR processing completes."""
        self._last_error = None
        if self.gsheets_enabled:
            try:
                self.gsheets.append_ocr_record({
                    "filename": filename,
                    "engine": engine,
                    "pages": pages,
                    "status": status,
                })
            except Exception as e:
                self._last_error = f"GSheets OCR record: {e}"
                traceback.print_exc()

    def on_project_created(self, project_name):
        """Called after a new project is created locally."""
        self._last_error = None
        # OneDrive: create folder structure
        if self.onedrive_enabled:
            try:
                self.onedrive.ensure_project_folder(self.onedrive_token, project_name)
            except Exception as e:
                self._last_error = f"OneDrive folder creation: {e}"
                traceback.print_exc()

        # Google Drive: create folder structure
        if self.gdrive_enabled:
            try:
                self.gdrive.ensure_project_folder(project_name)
            except Exception as e:
                self._last_error = f"Google Drive folder creation: {e}"
                traceback.print_exc()

        # GSheets: log + registry update
        if self.gsheets_enabled:
            try:
                self.gsheets.append_work_log({
                    "action_type": "project_created",
                    "project": project_name,
                    "details": "New project created",
                })
                self._sync_project_registry()
            except Exception as e:
                self._last_error = f"GSheets project create: {e}"
                traceback.print_exc()

    # ========================================
    # Manual sync operations
    # ========================================

    def push_project(self, project_name):
        """Push all local docs for a project to cloud (OneDrive + Google Drive)."""
        self._last_error = None
        results = {}

        import core_rag
        docs = core_rag.load_project_docs_dict(project_name)
        if not docs:
            return {"success": True, "uploaded": 0}

        # OneDrive push
        if self.onedrive_enabled:
            try:
                docs_folder_id = self.onedrive.ensure_project_folder(
                    self.onedrive_token, project_name
                )
                if docs_folder_id:
                    uploaded = 0
                    for fname, content in docs.items():
                        result = self.onedrive.upload_file(
                            self.onedrive_token, docs_folder_id, fname, content
                        )
                        if "id" in result:
                            uploaded += 1
                    results["onedrive"] = {"success": True, "uploaded": uploaded}
            except Exception as e:
                results["onedrive"] = {"success": False, "error": str(e)}
                self._last_error = f"OneDrive push: {e}"

        # Google Drive push
        if self.gdrive_enabled:
            try:
                gdrive_result = self.gdrive.push_project(project_name, docs)
                results["gdrive"] = gdrive_result
            except Exception as e:
                results["gdrive"] = {"success": False, "error": str(e)}
                self._last_error = f"Google Drive push: {e}"

        if not self.onedrive_enabled and not self.gdrive_enabled:
            return {"success": False, "error": "클라우드 스토리지가 연결되지 않았습니다"}

        return {"success": True, "total": len(docs), **results}

    def pull_project(self, project_name):
        """Pull documents from cloud (OneDrive + Google Drive) into local storage."""
        self._last_error = None
        results = {}
        import core_rag

        # OneDrive pull
        if self.onedrive_enabled:
            try:
                app_folder_id = self.onedrive.ensure_app_folder(self.onedrive_token)
                proj = self.onedrive.find_item_by_name(
                    self.onedrive_token, app_folder_id, project_name
                )
                if not proj:
                    results["onedrive"] = {"success": True, "downloaded": 0}
                else:
                    docs_folder = self.onedrive.find_item_by_name(
                        self.onedrive_token, proj["id"], "docs"
                    )
                    if not docs_folder:
                        results["onedrive"] = {"success": True, "downloaded": 0}
                    else:
                        files = self.onedrive.list_files(self.onedrive_token, docs_folder["id"])
                        downloaded = 0
                        for f in files:
                            if f.get("name", "").endswith(".md"):
                                content_bytes = self.onedrive.download_file(
                                    self.onedrive_token, f["id"]
                                )
                                if content_bytes:
                                    content = content_bytes.decode("utf-8", errors="replace")
                                    core_rag.index_single_document(
                                        "", f["name"], content, project_name
                                    )
                                    downloaded += 1
                        results["onedrive"] = {"success": True, "downloaded": downloaded}
            except Exception as e:
                results["onedrive"] = {"success": False, "error": str(e)}
                self._last_error = f"OneDrive pull: {e}"

        # Google Drive pull
        if self.gdrive_enabled:
            try:
                gdrive_docs = self.gdrive.pull_project(project_name)
                downloaded = 0
                for fname, content in gdrive_docs.items():
                    core_rag.index_single_document("", fname, content, project_name)
                    downloaded += 1
                results["gdrive"] = {"success": True, "downloaded": downloaded}
            except Exception as e:
                results["gdrive"] = {"success": False, "error": str(e)}
                self._last_error = f"Google Drive pull: {e}"

        if not self.onedrive_enabled and not self.gdrive_enabled:
            return {"success": False, "error": "클라우드 스토리지가 연결되지 않았습니다"}

        return {"success": True, **results}

    def full_sync(self, project_name):
        """Bidirectional sync: push local, then pull remote additions."""
        push_result = self.push_project(project_name)
        pull_result = self.pull_project(project_name)
        return {
            "push": push_result,
            "pull": pull_result,
        }

    def sync_project_documents(self, project_name):
        """Sync all documents of a project to Google Sheets (project_Docs tab)."""
        self._last_error = None
        if not self.gsheets_enabled:
            return {"success": False, "error": "Google Sheets not connected"}
        try:
            import core_rag
            docs = core_rag.load_project_docs_dict(project_name)
            if not docs:
                return {"success": True, "docs": 0, "message": "No documents to sync"}
            result = self.gsheets.sync_project_documents(project_name, docs)
            return {"success": True, **result}
        except Exception as e:
            self._last_error = str(e)
            return {"success": False, "error": str(e)}

    def sync_all_projects(self):
        """Sync project registry to Google Sheets."""
        self._last_error = None
        if self.gsheets_enabled:
            try:
                self._sync_project_registry()
                return {"success": True}
            except Exception as e:
                self._last_error = str(e)
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Google Sheets not connected"}

    def _sync_project_registry(self):
        """Internal: sync project list to GSheets."""
        if not self.gsheets_enabled:
            return
        import core_rag
        projects = core_rag.list_projects()
        self.gsheets.sync_project_registry(projects)
