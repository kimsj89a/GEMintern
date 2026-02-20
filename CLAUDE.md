# GEM Intern - AI-Powered Investment Analysis Assistant

## Project Overview

**GEM Intern v7.0**은 투자 분석 업무를 지원하는 AI 기반 Streamlit 웹 애플리케이션입니다.
Google Gemini API를 활용하여 투자심의보고서 작성, 문서 분석, PPT 생성 등 PE/VC 투자 프로세스 전반을 자동화합니다.

## Technical Stack

### Core Technologies
- **Framework**: Streamlit (Python web app framework)
- **AI/ML**: Google Gemini API (gemini-2.0-flash-thinking-exp-1219)
- **Document Processing**:
  - Google Cloud Document AI
  - MarkItDown (문서 변환)
  - python-docx, python-pptx (Office 문서 처리)
  - PyPDF, PyMuPDF (PDF 처리)
- **Data Processing**: pandas, openpyxl, XlsxWriter
- **Authentication**: MSAL (Microsoft Authentication Library)
- **Environment**: python-dotenv (환경변수 관리)

### Python Version
- Python 3.x (가상환경: `.venv/`)

## Project Structure

```
C:\Users\kimsj\GEMintern/
├── app.py                      # Main Streamlit application entry point
├── main_window.py              # Main window UI logic
├── app_state.py                # Application state management
├── styles.py                   # CSS styles and theming
├── workers.py                  # Background worker threads
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (API keys, secrets)
│
├── Core Logic Modules (코어 비즈니스 로직)
│   ├── core_logic.py           # Main business logic and file parsing
│   ├── core_rag.py             # RAG (Retrieval-Augmented Generation) system
│   ├── core_rfi.py             # RFI (Request for Information) processing
│   ├── core_chained.py         # Chained prompting logic
│   ├── core_ppt_updater.py     # PPT update automation
│   └── prompts.py              # AI prompt templates (67KB, extensive)
│
├── UI Modules (사용자 인터페이스)
│   ├── ui_workflow.py          # Phase workflow UI (3-phase investment process)
│   ├── ui_input.py             # Settings and input panels
│   ├── ui_output.py            # Output display and download
│   ├── ui_project.py           # Project management UI
│   ├── ui_lp_qa.py             # LP Q&A response system
│   ├── ui_ppt_tools.py         # PPT tools panel
│   ├── ui_ppt_updater.py       # PPT updater UI
│   ├── ui_audio.py             # Audio transcription panel
│   ├── ui_crawler.py           # Web crawler panel
│   ├── ui_ocr.py               # OCR panel
│   ├── ui_markdown.py          # Markdown to Word converter
│   ├── ui_doctemplate.py       # Document template panel
│   └── ui_text_organizer.py    # Text organization tool
│
├── Utility Modules (유틸리티)
│   ├── utils.py                # General utilities
│   ├── utils_audio.py          # Audio processing utilities
│   ├── utils_docai.py          # Document AI utilities
│   ├── utils_onedrive.py       # OneDrive integration
│   ├── utils_ppt.py            # PowerPoint utilities
│   ├── ocr.py                  # OCR processing
│   └── local_storage.py        # Local file storage
│
├── pages/                      # Streamlit multi-page app pages
│   ├── home_page.py
│   ├── workflow_page.py
│   ├── project_page.py
│   ├── settings_page.py
│   ├── lp_qa_page.py
│   ├── ppt_tools_page.py
│   ├── audio_page.py
│   ├── crawler_page.py
│   ├── ocr_page.py
│   ├── markdown_page.py
│   ├── doctemplate_page.py
│   └── text_organizer_page.py
│
├── components/                 # Reusable UI components
│   └── local_storage/          # Local storage component
│
├── widgets/                    # Custom Streamlit widgets
├── scripts/                    # Utility scripts
├── template/                   # Document templates
├── .claude/                    # Claude Code configuration
│   └── settings.local.json     # Local permissions
├── .venv/                      # Python virtual environment
└── .git/                       # Git repository
```

## Key Features & Workflows

### 1. Phase Workflow (3단계 투자 프로세스)
- **Phase 1: 사전 정보 수집** - 자료 수집, 시장 조사, 초기 검토
- **Phase 2: 투심보고서 작성** - IM 작성, Valuation, 투자심의
- *(Phase 3/4: FDD/LDD - 현재 비활성화)*

### 2. Independent Tools
- **IM 작성**: Investment Memorandum 자동 생성
- **발표자료 (PPT)**: 프레젠테이션 자동화
- **LP Q&A 대응**: Limited Partner 질의응답 시스템

### 3. Utilities
- **오디오 전사**: 음성 파일을 텍스트로 변환
- **웹 크롤러**: 웹사이트 정보 수집
- **문서 OCR**: 이미지/스캔 문서에서 텍스트 추출
- **MD to Word**: Markdown을 Word 문서로 변환
- **문서양식**: 표준 문서 템플릿 관리
- **문장 정리기**: 텍스트 정리 및 요약

### 4. Project Management & RAG
- 프로젝트별 문서 저장소
- RAG (Retrieval-Augmented Generation) 기반 문서 검색
- 프로젝트 컨텍스트 관리 (`core_rag.py`)

## Environment Variables (.env)

```bash
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key

# Google Cloud Document AI (optional)
DOCAI_PROJECT_ID=your_project_id
DOCAI_PROCESSOR_ID=your_processor_id
DOCAI_LOCATION=us

# Microsoft OneDrive (optional)
ONEDRIVE_CLIENT_ID=your_client_id
ONEDRIVE_CLIENT_SECRET=your_client_secret
```

## Running the Application

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py
```

## Development Guidelines

### Code Organization
- **Core Logic**: Business logic은 `core_*.py` 모듈에 구현
- **UI Components**: UI 로직은 `ui_*.py` 모듈에 분리
- **Utilities**: 재사용 가능한 유틸리티는 `utils*.py`에 배치
- **Prompts**: AI 프롬프트는 `prompts.py`에 중앙 관리

### Naming Conventions
- **Modules**: `snake_case` (예: `core_logic.py`, `ui_workflow.py`)
- **Functions**: `snake_case` (예: `parse_all_files()`, `render_dashboard()`)
- **Classes**: `PascalCase` (필요시)
- **Constants**: `UPPER_CASE` (예: `NAV_SECTIONS`, `PHASE_PAGES`)

### State Management
- Streamlit session state를 통한 상태 관리
- 주요 상태 키:
  - `app_started`: 앱 시작 여부
  - `selected_page`: 현재 선택된 페이지
  - `current_project`: 현재 프로젝트명
  - `latest_settings`: 최신 설정값
  - `p1_generated_text`, `p2_generated_text`: Phase별 생성 결과

### UI/UX Patterns
- **Design System**: Gemini-inspired color palette (CSS variables in `styles.py`)
- **Navigation**: Sidebar navigation with grouped sections
- **Breadcrumb**: 현재 위치 경로 표시
- **Project Banner**: 활성 프로젝트 컨텍스트 표시
- **Dashboard Cards**: Phase workflow 상태 시각화

## Working with AI (Gemini)

### Model Configuration
- Default Model: `gemini-3.1-pro-preview`
- Thinking Levels: MINIMAL, MEDIUM, MAXIMUM
- Structured output support (JSON schemas)

### Prompt Engineering
- `prompts.py`에 모든 프롬프트 템플릿 정의
- 주요 프롬프트 카테고리:
  - `LOGIC_PROMPTS`: 비즈니스 로직용 프롬프트
  - 구조 추출, 문서 분석, 보고서 생성 등

### RAG Implementation
- `core_rag.py`: 문서 인덱싱 및 검색
- 프로젝트별 독립적인 문서 저장소
- Context-aware document retrieval

## File Processing

### Supported Formats
- **Documents**: PDF, DOCX, TXT, MD
- **Spreadsheets**: XLSX, XLS
- **Presentations**: PPTX
- **Images**: PNG, JPG (OCR 지원)
- **Audio**: MP3, WAV, M4A (전사 지원)

### Processing Pipeline
1. File upload via Streamlit `file_uploader`
2. Parsing: `utils.parse_uploaded_file()` (with API key & DocAI config)
3. Storage: `utils.save_to_local_storage()` or `core_rag.index_texts()`
4. Retrieval: `core_rag.load_all_project_docs()`

## Testing & Debugging

### Running Tests
```bash
# Python syntax check
python -m py_compile *.py

# Run specific module
python -c "import core_logic; print('OK')"
```

### Debugging Tips
- Streamlit reruns the entire script on each interaction
- Use `st.session_state` for persistent data
- Check `st.write()` or `st.code()` for debugging output
- Monitor API rate limits (Gemini API)

## Security Considerations

### Secrets Management
- Never commit `.env` file to Git
- Store API keys in environment variables
- Use `.gitignore` to exclude:
  - `*.json` (service account credentials)
  - `.env`
  - `.venv/`
  - `__pycache__/`

### Permission Management
- Claude Code permissions: `.claude/settings.local.json`
- Allow minimal necessary bash commands
- Restrict file access to project directory

## Common Tasks

### Adding a New Feature
1. Create UI module: `ui_newfeature.py`
2. Create core logic: `core_newfeature.py`
3. Add prompts to `prompts.py`
4. Update `app.py` navigation:
   - Add to `NAV_SECTIONS`
   - Add page routing in `main()`
5. Test with sample data

### Modifying Prompts
1. Locate prompt in `prompts.py` (e.g., `LOGIC_PROMPTS['structure_extraction']`)
2. Edit prompt text (consider thinking level, format, examples)
3. Test with `core_logic.py` or relevant module
4. Validate output quality

### Managing Projects
- Create project: `core_rag.create_project(name)`
- List projects: `core_rag.list_projects()`
- Add documents: `core_rag.index_texts(api_key, {filename: text}, project_name)`
- Delete project: `core_rag.delete_project(project_name)`

## Troubleshooting

### Common Issues

**Streamlit App Won't Start**
- Check virtual environment activation
- Verify all dependencies installed: `pip install -r requirements.txt`
- Ensure port 8501 is available

**Gemini API Errors**
- Verify API key in `.env`
- Check API quota/rate limits
- Ensure model name is correct

**File Parsing Fails**
- Check file format support
- Verify DocAI config (if using)
- Inspect `utils.parse_uploaded_file()` error messages

**Session State Lost**
- Streamlit reruns entire script on interaction
- Use `st.session_state` for persistence
- Avoid relying on global variables

## Future Enhancements

- [ ] FDD (재무실사) Phase 3 활성화
- [ ] LDD (법률실사) Phase 4 활성화
- [ ] Multi-user support
- [ ] Database integration (currently file-based)
- [ ] Advanced analytics & dashboards
- [ ] Export to multiple formats (PDF, Excel)

## Contact & Support

For project-specific questions, refer to:
- Code comments in `app.py`, `core_logic.py`, `ui_workflow.py`
- Prompt templates in `prompts.py`
- Streamlit documentation: https://docs.streamlit.io/

---

**Last Updated**: 2026-02-15
**Version**: 7.0
**Maintained by**: kimsj
**Project Path**: `C:\Users\kimsj\GEMintern`
