# GEM Intern - AI-Powered Investment Analysis Assistant

## Project Overview

**GEM Intern** (2026.03.13)은 투자 분석 업무를 지원하는 AI 기반 웹 애플리케이션입니다.
Google Gemini API를 활용하여 투자심의보고서 작성, 문서 분석, PPT 생성 등 PE/VC 투자 프로세스 전반을 자동화합니다.

**아키텍처**: FastAPI 백엔드 + React (Vite) 프론트엔드, localhost 전용.

## Technical Stack

### Core Technologies
- **Backend**: FastAPI (Python) + Uvicorn
- **Frontend**: React + TypeScript + Vite
- **State Management**: Zustand (프론트엔드)
- **AI/ML**: Google Gemini API, Anthropic Claude API
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
GEMintern/
├── backend/                    # FastAPI 백엔드
│   ├── main.py                 # 서버 엔트리포인트
│   ├── api_routes.py           # REST API 라우트
│   ├── api_models.py           # Pydantic 모델
│   ├── api_ws.py               # WebSocket 엔드포인트
│   └── static/                 # 빌드된 프론트엔드 (production)
│
├── frontend/                   # React + Vite 프론트엔드
│   ├── src/
│   │   ├── App.tsx             # 메인 앱 컴포넌트
│   │   ├── main.tsx            # React 엔트리
│   │   ├── pages/              # 페이지 컴포넌트
│   │   ├── components/         # 재사용 UI 컴포넌트
│   │   ├── stores/             # Zustand 스토어
│   │   ├── api/                # API 클라이언트
│   │   └── utils/              # 프론트엔드 유틸리티
│   ├── package.json
│   └── vite.config.ts
│
├── Core Logic Modules (코어 비즈니스 로직)
│   ├── core_logic.py           # Main business logic and file parsing
│   ├── core_rag.py             # RAG (Retrieval-Augmented Generation) system
│   ├── core_rag_vector.py      # Vector-based RAG
│   ├── core_rfi.py             # RFI (Request for Information) processing
│   ├── core_chained.py         # Chained prompting logic
│   ├── core_im.py              # Investment Memorandum 생성
│   ├── core_im_ppt.py          # IM PPT 생성
│   ├── core_ppt_updater.py     # PPT update automation
│   ├── core_doc_updater.py     # Document update automation
│   └── prompts.py              # AI prompt templates
│
├── Utility Modules (유틸리티)
│   ├── utils.py                # General utilities
│   ├── utils_audio.py          # Audio processing utilities
│   ├── utils_docai.py          # Document AI utilities
│   ├── utils_doctemplate.py    # Document template utilities
│   ├── utils_gdrive.py         # Google Drive integration
│   ├── utils_gsheets.py        # Google Sheets integration
│   ├── utils_markdown.py       # Markdown utilities
│   ├── utils_onedrive.py       # OneDrive integration
│   ├── utils_ppt.py            # PowerPoint utilities
│   ├── ocr.py                  # OCR processing
│   ├── local_storage.py        # Local file storage
│   └── cloud_sync.py           # Cloud sync utilities
│
├── requirements.txt            # Python dependencies
├── run_gemintern.bat           # Windows 실행 스크립트
├── settings.json               # 앱 설정
├── .env                        # Environment variables (API keys)
├── template/                   # Document templates
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
│   └── plans/                  # Design & implementation plans
├── .venv/                      # Python virtual environment
└── .git/                       # Git repository
```

## Running the Application

```bash
# 가상환경 활성화
.venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 웹 서버 실행 (기본 모드 — 브라우저 자동 오픈)
python -m backend.main

# 프론트엔드 개발 모드 (API 서버만 실행)
python -m backend.main --dev
# 별도 터미널에서: cd frontend && npm run dev
```

**접속**: http://localhost:8741

## Key Features & Workflows

### 1. Phase Workflow (3단계 투자 프로세스)
- **Phase 1: 사전 정보 수집** — 자료 수집, 시장 조사, 초기 검토
- **Phase 2: 투심보고서 작성** — IM 작성, Valuation, 투자심의

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
- RAG 기반 문서 검색
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

## Development Guidelines

### Code Organization
- **Backend API**: `backend/api_routes.py`에 REST 엔드포인트 추가
- **Core Logic**: Business logic은 `core_*.py` 모듈에 구현
- **Frontend Pages**: `frontend/src/pages/`에 React 페이지 추가
- **Frontend Components**: `frontend/src/components/`에 재사용 컴포넌트
- **Utilities**: 재사용 가능한 유틸리티는 `utils*.py`에 배치
- **Prompts**: AI 프롬프트는 `prompts.py`에 중앙 관리

### Naming Conventions
- **Python Modules**: `snake_case` (예: `core_logic.py`, `api_routes.py`)
- **Python Functions**: `snake_case` (예: `parse_all_files()`)
- **React Components**: `PascalCase` (예: `WorkflowPage.tsx`)
- **TypeScript files**: `PascalCase` for pages/components, `camelCase` for utilities
- **Constants**: `UPPER_CASE` (예: `DEFAULT_PORT`)

### State Management
- **Frontend**: Zustand 스토어 (`frontend/src/stores/`)
- **Backend**: 서버 상태는 FastAPI 의존성 주입 패턴 사용

### Adding a New Feature
1. Backend API 엔드포인트 추가: `backend/api_routes.py`
2. Pydantic 모델 정의: `backend/api_models.py`
3. Core logic 구현: `core_newfeature.py`
4. Frontend 페이지 생성: `frontend/src/pages/NewFeaturePage.tsx`
5. API 클라이언트 함수 추가: `frontend/src/api/`
6. 라우터에 페이지 등록: `frontend/src/App.tsx`
7. 프롬프트 추가 (AI 기능): `prompts.py`

## Working with AI (Gemini)

### Model Configuration
- Default Model: `gemini-3.1-pro-preview`
- Thinking Levels: MINIMAL, MEDIUM, MAXIMUM
- Structured output support (JSON schemas)

### Prompt Engineering
- `prompts.py`에 모든 프롬프트 템플릿 정의
- 주요 프롬프트 카테고리: 구조 추출, 문서 분석, 보고서 생성 등

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

## Testing & Debugging

```bash
# Python syntax check
python -m py_compile core_logic.py

# Import test
python -c "import core_logic, core_rag, utils; print('OK')"

# Backend server test
python -m backend.main --dev
```

## Security Considerations

- Never commit `.env` file to Git
- Store API keys in environment variables
- `.gitignore` excludes: `*.json`, `.env`, `.venv/`, `__pycache__/`

---

**Last Updated**: 2026-03-15
**Version**: 2026.03.15T6
**Maintained by**: kimsj
**Project Path**: `C:\Users\kimsj\GEMintern\GEMintern`
