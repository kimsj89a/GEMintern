# FundFlow — LP 펀딩 트래커 설계 문서

## Overview

LP(Limited Partner) 자금모집 현황을 팀 단위로 관리하는 별도 웹 앱. 펀드별 LP 파이프라인, 미팅 기록, 요청사항/할일, 팀 활동 피드를 제공한다.

## Goals

- 펀드 레이징 현황을 팀 전원이 실시간으로 파악
- LP별 상태(접촉→확약→납입)를 체계적으로 추적
- LP 요청사항/액션아이템을 놓치지 않도록 관리
- 미팅 기록과 히스토리를 한곳에 축적

## Non-Goals (Phase 1)

- 딜 파이프라인 관리 (Phase 2에서 추가)
- 외부 시스템 연동 (이메일, 캘린더 등)
- 실시간 WebSocket 알림 (폴링으로 충분)
- 모바일 전용 UI

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **State**: Zustand
- **DB**: SQLite (WAL mode)
- **Auth**: JWT (HS256)
- **Deploy**: Railway (별도 서비스)

GEMintern과 동일한 패턴을 따르되, 별도 프로젝트/리포로 구성한다.

## Data Model

### Team
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT NOT NULL | 팀명 |
| created_at | TIMESTAMP | |

### User
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| username | TEXT UNIQUE | |
| password_hash | TEXT | |
| password_salt | TEXT | |
| team_id | INTEGER FK → Team | |
| role | TEXT | 'admin' or 'member' |
| display_name | TEXT | 활동 피드에 표시되는 이름 |
| created_at | TIMESTAMP | |

### InviteCode
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| code | TEXT UNIQUE | |
| team_id | INTEGER FK → Team | 이 코드로 가입 시 배정될 팀 |
| created_by | INTEGER FK → User | |
| used_by | INTEGER FK → User NULL | |
| used_at | TIMESTAMP NULL | |
| created_at | TIMESTAMP | |

### Fund
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| team_id | INTEGER FK → Team | |
| name | TEXT | 펀드명 |
| target_amount | INTEGER | 목표 금액 (억 단위) |
| status | TEXT | 'active', 'closed', 'cancelled' |
| description | TEXT | |
| created_at | TIMESTAMP | |

### LP
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| team_id | INTEGER FK → Team | 팀 공유 LP 풀 |
| name | TEXT | LP명 (기관명) |
| type | TEXT | 'insurance', 'securities', 'bank', 'pension', 'mutual_aid', 'other' |
| contact_name | TEXT | 담당자명 |
| contact_info | TEXT | 연락처/이메일 |
| notes | TEXT | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| UNIQUE(team_id, name) | | |

### FundLP
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| fund_id | INTEGER FK → Fund | |
| lp_id | INTEGER FK → LP | |
| status | TEXT | 'contacted', 'interested', 'negotiating', 'committed', 'paid', 'dropped' |
| commit_amount | INTEGER DEFAULT 0 | 확약/커밋 금액 (억 단위) |
| paid_amount | INTEGER DEFAULT 0 | 실제 납입 금액 |
| assigned_to | INTEGER FK → User | 담당자 |
| notes | TEXT | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| UNIQUE(fund_id, lp_id) | | |

**FundLP status values and display:**
- `contacted` → 접촉
- `interested` → 관심표명
- `negotiating` → 조건협의
- `committed` → 확약
- `paid` → 납입
- `dropped` → Drop

**LP type values and display:**
- `insurance` → 보험
- `securities` → 증권사
- `bank` → 은행
- `pension` → 연기금
- `mutual_aid` → 공제회
- `other` → 기타

### Activity
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| team_id | INTEGER FK → Team | |
| user_id | INTEGER FK → User | 행위자 |
| fund_lp_id | INTEGER FK → FundLP NULL | |
| fund_id | INTEGER FK → Fund NULL | |
| action | TEXT | 아래 action types 참고 |
| detail | TEXT | JSON string, 아래 스키마 참고 |
| created_at | TIMESTAMP | |

**Activity population rules:**
- `fund_id`만 설정: 펀드 자체 생성/수정 시 (LP 무관)
- `fund_lp_id` + `fund_id` 둘 다 설정: LP 관련 활동 (fund_id는 FundLP에서 파생)

**Activity.detail JSON schema per action:**
- `status_change`: `{"from": "contacted", "to": "committed", "lp_name": "한국투자"}`
- `amount_changed`: `{"field": "commit_amount", "from": 0, "to": 100, "lp_name": "한국투자"}`
- `lp_added`: `{"lp_name": "삼성생명", "fund_name": "AI Growth Fund I"}`
- `meeting_added`: `{"lp_name": "NH투자", "date": "2026-03-15"}`
- `note_added`: `{"lp_name": "교보생명"}`
- `action_item_created`: `{"title": "추가 재무자료 요청"}`
- `action_item_completed`: `{"title": "IR 자료 발송"}`

### Meeting
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| fund_lp_id | INTEGER FK → FundLP | |
| date | DATE | 미팅 날짜 |
| summary | TEXT | 미팅 내용 요약 |
| next_action | TEXT | 후속 조치 |
| created_by | INTEGER FK → User | |
| created_at | TIMESTAMP | |

### ActionItem
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| team_id | INTEGER FK → Team | |
| fund_lp_id | INTEGER FK → FundLP NULL | LP 연관 (optional) |
| title | TEXT | 할일 제목 |
| due_date | DATE NULL | 기한 |
| assigned_to | INTEGER FK → User NULL | 담당자 |
| completed | BOOLEAN DEFAULT 0 | |
| completed_at | TIMESTAMP NULL | |
| created_by | INTEGER FK → User | |
| created_at | TIMESTAMP | |

## Pages & UI

### 1. 대시보드 (/)

**레이아웃**: 좌측 펀드 목록 (280px) + 우측 2단 (LP 요청사항 / 최근 활동)

**좌측 — 펀드 목록**:
- 컴팩트 카드: 펀드명, 확약률(%), 금액(확약/목표), 프로그레스 바
- 클릭 시 펀드 상세로 이동
- 하단에 "+ 새 펀드" 버튼

**우측 상단 — LP 요청사항/할일**:
- ActionItem 테이블, 기한순 정렬
- 긴급도 색상: 빨강(D-1~D-2), 노랑(D-3~D-7), 기본(그 외)
- 각 항목: 제목, 관련 LP/펀드, 기한(D-day), 담당자
- 완료 체크 가능, 완료 항목은 흐리게 표시

**우측 하단 — 최근 활동**:
- Activity 테이블 최신순
- 아바타(이니셜) + "김팀장이 한국투자 상태를 확약으로 변경" 형태
- 타임스탬프 + 관련 펀드명

### 2. 펀드 상세 (/fund/:id)

**상단**: 펀드명, 목표금액, 확약금액, 납입금액, 확약률 요약

**뷰 토글**: [칸반 | 테이블] 탭

**칸반 뷰**:
- 상태별 컬럼 (접촉 → 관심표명 → 조건협의 → 확약 → 납입 + Drop)
- LP 카드: LP명, 금액, 담당자
- 드래그 앤 드롭으로 LP 상태 변경 가능 (PATCH /api/fund-lps/:id 호출, Activity 자동 기록)
- 카드 클릭 → LP 상세 모달/패널

**테이블 뷰**:
- 컬럼: LP명, 유형, 상태(badge), 커밋금액, 납입금액, 담당자, 최근활동
- 컬럼 정렬 가능
- 상태 필터 가능

**공통**: "+ LP 추가" 버튼 (LP 마스터에서 선택 or 새로 생성)

### 3. LP 상세 (/fund/:fundId/lp/:lpId)

슬라이드 패널 또는 모달로 열림.

- **헤더**: LP명, 유형, 현재 상태(변경 가능 드롭다운), 커밋금액(수정 가능), 담당자
- **탭**:
  - **미팅 기록**: 날짜순 미팅 리스트 + 새 미팅 추가 폼
  - **히스토리**: 상태변경/금액변경 타임라인 (Activity에서 필터)
  - **메모**: 자유 텍스트 메모 (FundLP.notes 필드에 저장, PATCH /api/fund-lps/:id로 수정)

### 4. LP 마스터 (/lps)

- 팀 전체 LP 풀 테이블
- 컬럼: LP명, 유형, 연락처, 참여 펀드 수
- 검색 + 유형별 필터
- "+ 새 LP" 추가
- LP 클릭 → LP 정보 수정

### 5. 설정 (/settings)

- **팀 정보**: 팀명 변경
- **멤버 관리**: 초대 코드 생성, 멤버 목록, 역할 변경
- **내 정보**: 표시 이름, 비밀번호 변경

## API Endpoints

### Auth
- `POST /api/auth/register` — 회원가입
  - 팀 생성 모드: `{ username, password, display_name, team_name }` → 팀 생성 + admin 유저
  - 팀 가입 모드: `{ username, password, display_name, invite_code }` → 기존 팀에 member로 가입
- `POST /api/auth/login` — 로그인 → JWT `{ username, password }`
- `GET /api/auth/me` — 현재 유저 정보 (id, username, display_name, team_id, role)
- `PATCH /api/auth/me` — 내 정보 수정 (display_name, password)

### Fund
- `GET /api/funds` — 팀의 펀드 목록
- `POST /api/funds` — 펀드 생성
- `GET /api/funds/:id` — 펀드 상세
- `PATCH /api/funds/:id` — 펀드 수정
- `DELETE /api/funds/:id` — 펀드 삭제

### Team
- `PATCH /api/team` — 팀 정보 수정 (name) [admin only]
- `GET /api/team/members` — 팀 멤버 목록
- `PATCH /api/team/members/:id` — 멤버 역할 변경 [admin only]
- `POST /api/team/invite-codes` — 초대코드 생성 [admin only]
- `GET /api/team/invite-codes` — 초대코드 목록 [admin only]

### LP
- `GET /api/lps` — 팀의 LP 마스터 목록
- `GET /api/lps/:id` — LP 상세
- `POST /api/lps` — LP 생성
- `PATCH /api/lps/:id` — LP 수정
- `DELETE /api/lps/:id` — LP 삭제

### FundLP
- `GET /api/funds/:id/lps` — 펀드의 LP 목록 (상태, 금액 포함)
- `GET /api/fund-lps/:id` — FundLP 단건 상세
- `POST /api/funds/:id/lps` — 펀드에 LP 추가
- `PATCH /api/fund-lps/:id` — 상태/금액/담당자 변경 (Activity 자동 기록)
- `DELETE /api/fund-lps/:id` — 펀드에서 LP 제거

### Meeting
미팅 기록은 append-only. 추가만 가능, 수정/삭제 불가 (히스토리 보존).
- `GET /api/fund-lps/:id/meetings` — 미팅 목록
- `POST /api/fund-lps/:id/meetings` — 미팅 추가

### ActionItem
- `GET /api/action-items` — 팀의 할일 목록 (미완료 우선)
- `POST /api/action-items` — 할일 생성
- `PATCH /api/action-items/:id` — 완료 처리/수정
- `DELETE /api/action-items/:id` — 할일 삭제

### Activity
- `GET /api/activities` — 팀의 최근 활동 (페이지네이션)

### Dashboard
- `GET /api/dashboard` — 대시보드 요약
  - 응답 형태:
  ```json
  {
    "funds": [{ "id", "name", "target_amount", "committed_amount", "paid_amount", "commit_rate", "status" }],
    "action_items": [{ "id", "title", "due_date", "assigned_to_name", "fund_name", "lp_name", "completed" }],
    "recent_activities": [{ "id", "user_display_name", "action", "detail", "created_at", "fund_name" }]
  }
  ```

## Pagination & Query Parameters

목록 API는 `?page=1&per_page=20` 쿼리 파라미터를 지원한다. 기본값: page=1, per_page=20.
- `GET /api/activities` — 페이지네이션 필수 (데이터 증가 빠름)
- `GET /api/action-items` — 선택 (Phase 1에서는 전체 반환 가능, 팀 규모 작음)
- 기타 목록 API — Phase 1에서는 전체 반환, 필요 시 추가

## Fund Detail & Delete Behavior

**`GET /api/funds/:id` 응답:**
```json
{
  "id", "name", "target_amount", "status", "description", "created_at",
  "committed_amount": 192,  // SUM(fund_lps.commit_amount) - 서버에서 계산
  "paid_amount": 42,        // SUM(fund_lps.paid_amount) - 서버에서 계산
  "commit_rate": 64.0,      // committed_amount / target_amount * 100
  "lp_count": 14            // COUNT(fund_lps)
}
```

**Delete 동작:**
- `DELETE /api/funds/:id` — 연관 FundLP, Meeting, ActionItem, Activity 모두 cascade delete. 되돌릴 수 없으므로 프론트에서 확인 다이얼로그 표시.
- `DELETE /api/lps/:id` — 해당 LP가 FundLP에 연결되어 있으면 400 에러 반환. 먼저 모든 FundLP에서 제거 후 삭제 가능.
- `DELETE /api/fund-lps/:id` — 연관 Meeting, ActionItem cascade delete. Activity는 보존 (히스토리).

## Auth & Team Flow

1. 첫 번째 유저: 회원가입 시 팀 자동 생성, role=admin
2. Admin이 초대코드 생성
3. 초대코드로 가입한 유저는 같은 팀에 role=member로 배정
4. 같은 팀 소속 유저는 모든 펀드/LP/활동 데이터 공유

## Project Structure

```
fundflow/
├── backend/
│   ├── main.py           # FastAPI app, serve static
│   ├── database.py       # SQLite init, get_db
│   ├── auth.py           # JWT helpers
│   ├── auth_routes.py    # /auth/* endpoints
│   ├── api_routes.py     # /funds, /lps, /fund-lps, etc.
│   ├── api_models.py     # Pydantic models
│   └── static/           # Built frontend
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── api/client.ts
│   │   ├── stores/
│   │   │   ├── authStore.ts
│   │   │   └── appStore.ts
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── FundDetailPage.tsx
│   │   │   ├── LpMasterPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   └── components/
│   │       ├── Sidebar.tsx
│   │       ├── KanbanBoard.tsx
│   │       ├── LpTable.tsx
│   │       ├── LpDetailPanel.tsx
│   │       ├── ActivityFeed.tsx
│   │       └── ActionItemList.tsx
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt
├── .env
└── .gitignore
```

## Phase 2: 딜 파이프라인 (향후)

Phase 1 완료 후 별도 spec으로 추가:
- Deal 테이블 (name, stage, fund_id, assigned members)
- 스테이지: 소싱 → 검토 → DD → 투심위 → 집행 → 모니터링
- 딜별 체크리스트, 마일스톤, 핵심 딜 정보
- 기존 GEMintern 프로젝트 문서 연동
