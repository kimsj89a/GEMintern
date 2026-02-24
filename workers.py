"""
QThread workers for background tasks: AI generation, file parsing, etc.
These prevent UI blocking during long operations.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import traceback


class GenerateWorker(QThread):
    """Worker for streaming AI report generation."""
    chunk_received = pyqtSignal(str)       # partial text chunk
    finished = pyqtSignal(str)             # full response text
    error = pyqtSignal(str)                # error message
    status_update = pyqtSignal(str)        # status message

    def __init__(self, api_key, model_name, inputs, thinking_level, file_context,
                 mode="single", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model_name = model_name
        self.inputs = inputs
        self.thinking_level = thinking_level
        self.file_context = file_context
        self.mode = mode  # "single" or "chained"
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            import core_logic
            import core_chained

            if self.mode == "im_chained":
                import core_im
                self.status_update.emit("📑 IM 단계별 생성 모드로 작성 중...")
                stream = core_im.generate_im_chained_stream(
                    self.api_key, self.model_name,
                    self.inputs, self.thinking_level, self.file_context,
                    investment_type=self.inputs.get("investment_type", "Growth"),
                )
            elif self.mode == "chained" and core_chained.is_chained_supported(
                self.inputs.get("template_option", "")
            ):
                self.status_update.emit("🔗 단계별 생성 모드로 작성 중...")
                stream = core_logic.generate_report_stream_chained(
                    self.api_key, self.model_name,
                    self.inputs, self.thinking_level, self.file_context,
                )
            else:
                self.status_update.emit("📝 문서 작성 중 (스트리밍)...")
                stream = core_logic.generate_report_stream(
                    self.api_key, self.model_name,
                    self.inputs, self.thinking_level, self.file_context,
                )

            import re
            status_pattern = re.compile(r'\s*---\s*\*\*\[.+?\] 생성 중\.\.\.\*\*\s*')
            full_response = ""
            for chunk in stream:
                if self._stopped:
                    self.finished.emit(full_response)
                    return
                if chunk.text:
                    # Filter out status messages like "[Part 1/5: 투자내용] 생성 중..."
                    if status_pattern.search(chunk.text):
                        status_match = re.search(r'\*\*\[(.+?)\] 생성 중\.\.\.\*\*', chunk.text)
                        if status_match:
                            self.status_update.emit(f"📝 {status_match.group(1)} 생성 중...")
                        continue
                    full_response += chunk.text
                    self.chunk_received.emit(full_response)

            self.finished.emit(full_response)

        except Exception as e:
            if not self._stopped:
                self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


class RefineWorker(QThread):
    """Worker for report refinement."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, model_name, current_text, chat_history,
                 refine_query, additional_context="", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model_name = model_name
        self.current_text = current_text
        self.chat_history = chat_history
        self.refine_query = refine_query
        self.additional_context = additional_context
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            import core_logic
            result = core_logic.refine_report_with_context(
                self.api_key, self.model_name,
                self.current_text, self.chat_history,
                self.refine_query, self.additional_context,
            )
            if not self._stopped:
                self.finished.emit(result)
        except Exception as e:
            if not self._stopped:
                self.error.emit(str(e))


class FileParseWorker(QThread):
    """Worker for file parsing."""
    progress = pyqtSignal(int, int)         # current, total
    finished = pyqtSignal(str, str, dict)   # file_context, ocr_text, parse_results
    error = pyqtSignal(str)
    file_error = pyqtSignal(str, str)       # filename, error_msg

    def __init__(self, file_paths, api_key, docai_config=None,
                 template_option="", project_name=None, selected_docs=None, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.api_key = api_key
        self.docai_config = docai_config
        self.template_option = template_option
        self.project_name = project_name
        self.selected_docs = selected_docs  # List of selected document names
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            import core_logic
            import core_rag
            import utils
            import os

            # Load project docs as base context (only selected documents)
            project_context = ""
            if self.project_name:
                if self.selected_docs:
                    # Load only selected documents
                    project_context = core_rag.load_selected_project_docs(
                        self.project_name, self.selected_docs
                    )
                else:
                    # Load all documents if no selection specified
                    project_context = core_rag.load_all_project_docs(self.project_name)

                if project_context:
                    selected_info = f"{len(self.selected_docs)}개 선택" if self.selected_docs else "전체"
                    project_context = f"--- [프로젝트 문서: {self.project_name} ({selected_info})] ---\n{project_context}\n\n"

            # Parse files from paths (create file-like objects)
            file_context_parts = []
            parse_results = {}  # {filename: {"success": bool, "error": str or None}}
            total = len(self.file_paths)

            for i, fpath in enumerate(self.file_paths):
                if self._stopped:
                    break
                self.progress.emit(i + 1, total)
                filename = os.path.basename(fpath)

                try:
                    with open(fpath, 'rb') as f:
                        # Create a simple file-like wrapper
                        parsed = utils.parse_uploaded_file(
                            _FileWrapper(f, fpath),
                            api_key=self.api_key,
                            docai_config=self.docai_config,
                        )
                        if parsed:
                            file_context_parts.append(parsed)
                            parse_results[filename] = {"success": True, "error": None}
                        else:
                            error_msg = "파일 파싱 결과가 없습니다."
                            parse_results[filename] = {"success": False, "error": error_msg}
                            self.file_error.emit(filename, error_msg)
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    parse_results[filename] = {"success": False, "error": error_msg}
                    self.file_error.emit(filename, error_msg)

            file_context = "\n\n".join(file_context_parts)
            combined = project_context + file_context
            self.finished.emit(combined, combined, parse_results)

        except Exception as e:
            self.error.emit(str(e))


class AnalysisWorker(QThread):
    """Worker for AI analysis tasks (material summary, Q&A, etc.)."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, task_type, api_key, model_name, selected_docs=None, **kwargs):
        super().__init__()
        self.task_type = task_type
        self.api_key = api_key
        self.model_name = model_name
        self.selected_docs = selected_docs  # List of selected document names
        self.kwargs = kwargs
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            import core_logic

            if self.task_type == "material_summary":
                result = core_logic.generate_material_summary(
                    self.api_key, self.model_name,
                    self.kwargs["file_context"],
                )
            elif self.task_type == "followup_analysis":
                result = core_logic.generate_followup_analysis(
                    self.api_key, self.model_name,
                    self.kwargs["file_context"],
                    self.kwargs["existing_analysis"],
                    self.kwargs["user_input"],
                )
            elif self.task_type == "qa_answer":
                result = core_logic.generate_qa_answer(
                    self.api_key, self.model_name,
                    self.kwargs["file_context"],
                    self.kwargs["question"],
                    prev_qa_context=self.kwargs.get("prev_qa_context", ""),
                    rag_context=self.kwargs.get("rag_context", ""),
                )
            elif self.task_type == "followup_questions":
                result = core_logic.generate_followup_questions(
                    self.api_key, self.model_name,
                    self.kwargs["file_context"],
                    rag_context=self.kwargs.get("rag_context", ""),
                )
            elif self.task_type == "additional_questions":
                result = core_logic.generate_additional_questions(
                    self.api_key, self.model_name,
                    self.kwargs["file_context"],
                    self.kwargs["existing_questions"],
                    self.kwargs["user_input"],
                    rag_context=self.kwargs.get("rag_context", ""),
                )
            elif self.task_type == "checklist_eval":
                result = core_logic.evaluate_checklist_item(
                    self.api_key, self.model_name,
                    self.kwargs["item_name"],
                    self.kwargs["file_context"],
                )
            elif self.task_type == "dd_issues":
                result = core_logic.analyze_dd_issues(
                    self.api_key, self.model_name,
                    self.kwargs["file_context"],
                    self.kwargs.get("context_text", ""),
                )
            elif self.task_type == "slide_json":
                result = core_logic.generate_slide_json(
                    self.api_key, self.model_name,
                    self.kwargs["file_context"],
                    self.kwargs.get("context_text", ""),
                )
            else:
                result = f"Unknown task type: {self.task_type}"

            if not self._stopped:
                self.finished.emit(result)
        except Exception as e:
            if not self._stopped:
                self.error.emit(str(e))


class SyncWorker(QThread):
    """Worker for cloud sync operations (runs in background)."""
    finished = pyqtSignal(dict)   # result dict
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)  # progress messages

    def __init__(self, sync_manager, action="full_sync", project_name=None, parent=None):
        super().__init__(parent)
        self.sync_manager = sync_manager
        self.action = action  # "push", "pull", "full_sync", "sync_registry"
        self.project_name = project_name
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            if not self.sync_manager:
                self.error.emit("Sync manager not initialized")
                return

            result = {}
            if self.action == "push" and self.project_name:
                self.status_update.emit("☁️ 업로드 중...")
                result = self.sync_manager.push_project(self.project_name)
            elif self.action == "pull" and self.project_name:
                self.status_update.emit("📥 다운로드 중...")
                result = self.sync_manager.pull_project(self.project_name)
            elif self.action == "full_sync" and self.project_name:
                self.status_update.emit("🔄 동기화 중...")
                result = self.sync_manager.full_sync(self.project_name)
            elif self.action == "sync_registry":
                self.status_update.emit("📋 프로젝트 목록 동기화 중...")
                result = self.sync_manager.sync_all_projects()
            else:
                result = {"success": False, "error": f"Unknown action: {self.action}"}

            if not self._stopped:
                self.finished.emit(result)
        except Exception as e:
            if not self._stopped:
                self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


class _FileWrapper:
    """Simple wrapper to make a file object look like a Streamlit UploadedFile.
    Uses io.BytesIO internally so pandas/openpyxl read, seek, tell all work."""
    def __init__(self, file_obj, path):
        import os, io
        self.name = os.path.basename(path)
        self.size = os.path.getsize(path)
        self._data = file_obj.read()
        file_obj.seek(0)
        self._buf = io.BytesIO(self._data)

    def read(self, n=-1):
        return self._buf.read(n)

    def getvalue(self):
        return self._data

    def seek(self, pos, whence=0):
        self._buf.seek(pos, whence)

    def tell(self):
        return self._buf.tell()

    def readable(self):
        return True

    def seekable(self):
        return True
