"""
Google Sheets integration for GEM Intern.
Uses gspread with service account authentication.
Manages structured data: project registry, analysis history, work log, OCR history.
"""

import datetime
import gspread

# Sheet names
SHEET_PROJECTS = "Projects"
SHEET_ANALYSIS = "Analysis_History"
SHEET_WORK_LOG = "Work_Log"
SHEET_OCR = "OCR_History"

# Column headers per sheet
HEADERS = {
    SHEET_PROJECTS: ["name", "created", "doc_count", "last_synced"],
    SHEET_ANALYSIS: ["timestamp", "project", "template_type", "model", "summary"],
    SHEET_WORK_LOG: ["timestamp", "action_type", "project", "details"],
    SHEET_OCR: ["timestamp", "filename", "engine", "pages", "status"],
}


class GSheetsClient:
    def __init__(self, credentials_json_path):
        self.gc = gspread.service_account(filename=credentials_json_path)
        self._workbook = None
        self._spreadsheet_id = None

    def ensure_workbook(self, title="GEMintern_DB", spreadsheet_id=None):
        """Open existing spreadsheet by ID, or by title, or create new one.
        Returns the Spreadsheet object.
        """
        if self._workbook:
            return self._workbook

        # Try by ID first (most reliable)
        if spreadsheet_id:
            try:
                self._workbook = self.gc.open_by_key(spreadsheet_id)
                self._spreadsheet_id = spreadsheet_id
                self._ensure_sheets()
                return self._workbook
            except gspread.exceptions.SpreadsheetNotFound:
                pass

        # Try by title
        try:
            self._workbook = self.gc.open(title)
            self._spreadsheet_id = self._workbook.id
            self._ensure_sheets()
            return self._workbook
        except gspread.exceptions.SpreadsheetNotFound:
            pass

        # Create new (may fail if service account has no Drive quota)
        try:
            self._workbook = self.gc.create(title)
            self._spreadsheet_id = self._workbook.id
            self._ensure_sheets()
            return self._workbook
        except Exception as e:
            raise RuntimeError(
                f"스프레드시트를 찾을 수 없습니다. "
                f"Google Sheets에서 '{title}' 시트를 만들고 서비스 계정 이메일에 편집 권한을 공유해주세요. "
                f"또는 spreadsheet_id를 직접 지정하세요. 원본 에러: {e}"
            )

    @property
    def spreadsheet_id(self):
        return self._spreadsheet_id

    def _ensure_sheets(self):
        """Ensure all required worksheets exist with headers."""
        existing = [ws.title for ws in self._workbook.worksheets()]
        for sheet_name, headers in HEADERS.items():
            if sheet_name not in existing:
                ws = self._workbook.add_worksheet(title=sheet_name, rows=1, cols=len(headers))
                ws.append_row(headers, value_input_option="RAW")
            else:
                ws = self._workbook.worksheet(sheet_name)
                # Add headers if first row is empty
                first_row = ws.row_values(1)
                if not first_row:
                    ws.append_row(headers, value_input_option="RAW")

        # Remove default Sheet1 if we created other sheets
        if "Sheet1" in existing and len(existing) > 1:
            try:
                self._workbook.del_worksheet(self._workbook.worksheet("Sheet1"))
            except Exception:
                pass

    def _get_sheet(self, name):
        wb = self.ensure_workbook()
        return wb.worksheet(name)

    # --- Project Registry ---

    def sync_project_registry(self, projects):
        """Full sync of project list. Replaces all rows below header.
        projects: list of dicts with keys matching HEADERS[SHEET_PROJECTS]
        """
        ws = self._get_sheet(SHEET_PROJECTS)
        # Clear data rows (keep header)
        if ws.row_count > 1:
            ws.delete_rows(2, ws.row_count)

        if not projects:
            return

        now = datetime.datetime.now().isoformat(timespec="seconds")
        rows = []
        for p in projects:
            rows.append([
                p.get("name", ""),
                p.get("created", ""),
                str(p.get("doc_count", 0)),
                now,
            ])
        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")

    # --- Analysis History ---

    def append_analysis_record(self, record):
        """Append a single analysis record.
        record: dict with keys: project, template_type, model, summary
        """
        ws = self._get_sheet(SHEET_ANALYSIS)
        row = [
            datetime.datetime.now().isoformat(timespec="seconds"),
            record.get("project", ""),
            record.get("template_type", ""),
            record.get("model", ""),
            str(record.get("summary", ""))[:500],  # truncate for sheet cell limit
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")

    # --- Work Log ---

    def append_work_log(self, log_entry):
        """Append a work log entry.
        log_entry: dict with keys: action_type, project, details
        """
        ws = self._get_sheet(SHEET_WORK_LOG)
        row = [
            datetime.datetime.now().isoformat(timespec="seconds"),
            log_entry.get("action_type", ""),
            log_entry.get("project", ""),
            str(log_entry.get("details", ""))[:500],
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")

    # --- OCR History ---

    def append_ocr_record(self, record):
        """Append an OCR processing record.
        record: dict with keys: filename, engine, pages, status
        """
        ws = self._get_sheet(SHEET_OCR)
        row = [
            datetime.datetime.now().isoformat(timespec="seconds"),
            record.get("filename", ""),
            record.get("engine", ""),
            str(record.get("pages", "")),
            record.get("status", ""),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")

    # --- Docs Index ---

    _INDEX_HEADERS = [
        "project", "doc_name", "chars", "parts", "preview", "synced_at"
    ]

    def sync_docs_index(self, all_projects_docs):
        """Create/update a Docs_Index sheet with an overview of all documents.

        Args:
            all_projects_docs: dict of {project_name: {filename: content}}
        """
        wb = self.ensure_workbook()
        sheet_name = "Docs_Index"

        existing = [ws.title for ws in wb.worksheets()]
        if sheet_name in existing:
            ws = wb.worksheet(sheet_name)
            ws.clear()
        else:
            ws = wb.add_worksheet(title=sheet_name, rows=1, cols=len(self._INDEX_HEADERS))

        now = datetime.datetime.now().isoformat(timespec="seconds")
        rows = [self._INDEX_HEADERS]

        for project_name in sorted(all_projects_docs.keys()):
            docs = all_projects_docs[project_name]
            for fname in sorted(docs.keys()):
                content = docs[fname] or ""
                total_chars = len(content)
                parts = (total_chars // self._DOC_CHUNK_SIZE) + (1 if total_chars % self._DOC_CHUNK_SIZE else 0)
                if parts == 0:
                    parts = 1
                # Preview: first 200 chars, single line
                preview = content[:200].replace("\n", " ").strip()
                rows.append([
                    project_name, fname, str(total_chars),
                    str(parts), preview, now,
                ])

        if len(rows) > 1:
            ws.update(rows, value_input_option="RAW")

        return {"sheet": sheet_name, "total_docs": len(rows) - 1}

    # --- Project Document Storage ---

    _DOC_CHUNK_SIZE = 40000  # chars per cell (Sheets limit ~50K)
    _DOC_HEADERS = ["doc_name", "part", "total_parts", "chars", "synced_at", "content"]

    def sync_project_documents(self, project_name, docs_dict):
        """Store all project documents in a dedicated sheet tab.
        Creates '{project_name}_Docs' sheet. Large docs are split into chunks.

        Args:
            project_name: project name (used as sheet tab prefix)
            docs_dict: {filename: content_string}
        """
        wb = self.ensure_workbook()
        sheet_name = f"{project_name}_Docs"

        # Get or create sheet
        existing = [ws.title for ws in wb.worksheets()]
        if sheet_name in existing:
            ws = wb.worksheet(sheet_name)
            ws.clear()
        else:
            ws = wb.add_worksheet(title=sheet_name, rows=1, cols=len(self._DOC_HEADERS))

        # Header
        now = datetime.datetime.now().isoformat(timespec="seconds")
        rows = [self._DOC_HEADERS]

        for fname, content in sorted(docs_dict.items()):
            content = content or ""
            total_chars = len(content)

            if total_chars <= self._DOC_CHUNK_SIZE:
                rows.append([fname, "1", "1", str(total_chars), now, content])
            else:
                # Split into chunks
                chunks = []
                for i in range(0, total_chars, self._DOC_CHUNK_SIZE):
                    chunks.append(content[i:i + self._DOC_CHUNK_SIZE])
                total_parts = len(chunks)
                for idx, chunk in enumerate(chunks, 1):
                    rows.append([
                        fname, str(idx), str(total_parts),
                        str(len(chunk)), now, chunk
                    ])

        # Batch write all rows at once
        if len(rows) > 1:
            ws.update(rows, value_input_option="RAW")

        return {"sheet": sheet_name, "docs": len(docs_dict), "rows": len(rows) - 1}
