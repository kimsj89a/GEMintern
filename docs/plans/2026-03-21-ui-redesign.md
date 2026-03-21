# GEMintern UI Redesign — NotebookLM 스타일

**Date**: 2026-03-21
**Status**: Planning
**Reference**: Google NotebookLM UI

---

## 개요

현재 사이드바+탭 구조를 **프로젝트 중심 3-페이지 구조**로 전면 개편.

---

## 페이지 구성

### Page 1: 프로젝트 대시보드 (로그인 후 첫 화면)

```
┌─────────────────────────────────────────────┐
│  💎 GEM Intern                    ⚙️  👤   │
├─────────────────────────────────────────────┤
│                                             │
│  최근 프로젝트                               │
│                                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │  +   │ │ 🤝   │ │ 🚀   │ │ 📊   │       │
│  │새 프로│ │ FDC  │ │Redvel│ │(주)킴 │       │
│  │젝트   │ │      │ │vet   │ │투자검토│       │
│  │만들기 │ │소스15 │ │소스28 │ │소스 8 │       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│                                             │
└─────────────────────────────────────────────┘
```

**구성요소:**
- 상단 헤더: 로고 + 설정 + 프로필
- 프로젝트 카드 그리드 (반응형: 4열→2열→1열)
- 카드: 이모지 아이콘 + 프로젝트명 + 소스 수 + ⋮ 메뉴(이름변경/삭제)
- "새 프로젝트 만들기" 카드 (항상 첫 번째)
- 카드 클릭 → Page 2 (작업 페이지)로 진입

**데이터:**
- `GET /projects` → 카드 목록
- `POST /projects` → 새 프로젝트 생성

---

### Page 2: 메인 작업 페이지 (3열 레이아웃)

```
┌──────────────────────────────────────────────────────────────┐
│  ← 프로젝트명                    📊분석  📤공유  ⚙️설정     │
├────────────┬─────────────────────────┬───────────────────────┤
│  출처       │  채팅                    │  스튜디오              │
│            │                         │                       │
│ + 소스 추가 │                         │ ┌─────┐ ┌─────┐      │
│            │                         │ │📊   │ │📄   │      │
│ 🔍검색     │       🤝                │ │PPT  │ │보고서│      │
│            │      FDC               │ │     │ │     │      │
│ ☑ 문서1.pdf│     소스 15개            │ └─────┘ └─────┘      │
│ ☑ 문서2.docx│                        │ ┌─────┐ ┌─────┐      │
│ ☑ 문서3.xlsx│                        │ │💬   │ │📋   │      │
│ ...       │                         │ │Q&A  │ │IM   │      │
│            │                         │ │     │ │     │      │
│            │  입력을 시작하세요...      │ └─────┘ └─────┘      │
│            │  소스 15개        →      │                       │
└────────────┴─────────────────────────┴───────────────────────┘
```

**왼쪽 패널 — 출처 (Sources)**
- 소스 추가 버튼 (파일 업로드 / 폴더 업로드 / URL)
- 문서 목록 (체크박스 + 파일 아이콘 + 파일명)
- "모든 소스 선택" 토글
- 문서 클릭 → 문서 내용 미리보기
- 검색 바 (문서 내 검색)

**가운데 패널 — 채팅**
- 프로젝트 RAG 기반 대화
- 하단 입력창 + 소스 수 표시 + 전송 버튼
- 채팅 히스토리 저장/로드
- 기존 QaSessionPage 로직 재활용

**오른쪽 패널 — 스튜디오 (Tools)**
- 도구 카드 그리드 (2열)
- 카드 클릭 → 모달/시트로 도구 실행

**스튜디오 도구 목록:**
| 카드 | 아이콘 | 기능 | 기존 페이지 매핑 |
|------|--------|------|-----------------|
| PPT 생성 | 📊 | 슬라이드 생성 | PptToolsPage |
| 보고서 작성 | 📄 | 문서 작성 | WorkflowPage phase2 |
| IM 작성 | 📋 | Investment Memo | WorkflowPage (im) |
| Q&A 대응 | 💬 | LP Q&A | LpQaPage |
| DD 보고서 | 🔬 | Due Diligence | WorkflowPage (dd_report) |
| 자료 분석 | 📥 | 사전 분석 | WorkflowPage phase1 |
| 문서 업데이트 | 🔄 | 기존 문서 수정 | DocUpdaterPage |
| 기안문 | 📝 | 기안문 작성 | DraftDocPage |

**모바일 대응:**
- 3열 → 탭 전환 (출처/채팅/스튜디오)
- 하단 탭바 3개로 전환

---

### Page 3: 슬라이드 생성 모달

NotebookLM "슬라이드 자료 맞춤설정" 참고.

```
┌─────────────────────────────────────────────┐
│  📊 슬라이드 자료 맞춤설정              ✕    │
├─────────────────────────────────────────────┤
│                                             │
│  형식                                       │
│  ┌───────────────┐ ┌───────────────┐        │
│  │ 자세한 자료  ✓ │ │ 발표자 슬라이드│        │
│  │ 전체 텍스트와  │ │ 핵심 내용을 담은│        │
│  │ 세부정보 포함  │ │ 시각적 슬라이드│        │
│  └───────────────┘ └───────────────┘        │
│                                             │
│  템플릿                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │투심보고│ │Teaser│ │DD    │ │IM    │       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│                                             │
│  길이                                       │
│  [ 짧게 ] [ ✓ 기본값 ] [ 상세 ]              │
│                                             │
│  만들려는 슬라이드 자료에 대한 설명            │
│  ┌─────────────────────────────────┐        │
│  │ 10p 정도 Deal Teaser            │        │
│  └─────────────────────────────────┘        │
│                                             │
│                              [ 생성 ]       │
└─────────────────────────────────────────────┘
```

**옵션:**
- 형식: 자세한 자료 (보고서형) / 발표자 슬라이드 (PPT형)
- 템플릿: 투심보고서, Teaser, DD, IM, Term Sheet, 자유양식
- 길이: 짧게 (5-8p) / 기본값 (10-15p) / 상세 (20-30p)
- 설명: 자유 텍스트 입력
- 생성 버튼 → 기존 DYNAMIC_PPTX_PROMPT 호출

**생성 후:**
- 슬라이드 미리보기 (HTML/CSS)
- 다운로드 버튼 (PPTX)
- 개별 슬라이드 편집/재생성

---

## 기술 설계

### 라우팅 변경

```
현재: App.tsx → Sidebar + TabContainer(openTabs) → 각 페이지
변경: App.tsx → Router
  /           → ProjectDashboard (Page 1)
  /project/:id → WorkspacePage (Page 2 — 3열)
  /settings    → SettingsPage
  /admin       → AdminPage
```

React Router는 오버킬 — 기존 Zustand store에 `view` 상태 추가로 충분.

```typescript
// appStore 확장
view: 'dashboard' | 'workspace'
currentProject: string
activePanel: 'sources' | 'chat' | 'studio' // 모바일용
```

### 컴포넌트 구조

```
App.tsx
├── ProjectDashboard.tsx (Page 1 — 새로 만듦)
│   ├── ProjectCard.tsx
│   └── CreateProjectModal.tsx
│
├── WorkspacePage.tsx (Page 2 — 새로 만듦)
│   ├── SourcePanel.tsx (왼쪽 — ProjectPage + FilePicker 재활용)
│   ├── ChatPanel.tsx (가운데 — QaSessionPage 재활용)
│   └── StudioPanel.tsx (오른쪽 — 도구 카드 그리드)
│       └── SlideGeneratorModal.tsx (Page 3)
│
└── MobileWorkspace.tsx (모바일 — 탭 전환)
```

### 기존 코드 재활용

| 신규 컴포넌트 | 재활용 대상 |
|-------------|-----------|
| SourcePanel | ProjectPage의 FolderTree + FilePicker |
| ChatPanel | QaSessionPage의 ChatWidget + 채팅 로직 |
| StudioPanel | 기존 페이지들을 모달로 호출 |
| SlideGeneratorModal | PptToolsPage 로직 |
| ProjectDashboard | HomePage 카드 + ProjectPage 프로젝트 CRUD |

### 마이그레이션 전략

**Phase 1: 신규 페이지 추가 (기존 유지)**
- ProjectDashboard, WorkspacePage 추가
- 기존 사이드바+탭 구조 그대로 유지
- 대시보드에서 프로젝트 선택 시 WorkspacePage로 전환

**Phase 2: 기존 페이지를 모달/패널로 전환**
- PptToolsPage → SlideGeneratorModal
- WorkflowPage → StudioPanel 내 도구로 흡수
- QaSessionPage → ChatPanel로 흡수

**Phase 3: 사이드바+탭 제거**
- Sidebar.tsx, TabContainer.tsx 제거
- 모든 네비게이션을 대시보드+작업페이지로 통합

---

## 우선순위

1. ProjectDashboard (로그인 후 첫 화면)
2. WorkspacePage 3열 레이아웃
3. SlideGeneratorModal (PPT 생성 UX)
4. 모바일 대응 (3열 → 탭 전환)
5. 기존 페이지 마이그레이션

---

## 비고

- Utilities (오디오, OCR, 크롤러 등)는 스튜디오 "더보기" 또는 설정에서 접근
- DartWings는 독립 도구로 유지 (프로젝트 비종속)
- 관리자 페이지는 설정 내 탭으로 이동
