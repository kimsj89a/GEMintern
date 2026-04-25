"""
Note templates — Obsidian Templater-style.
저장 위치:
- 전역(읽기 전용): rag_storage/_global_templates/*.md  (앱이 첫 실행 시 5종 시드)
- 프로젝트별 사용자 정의: rag_storage/{storage_name}/_templates/*.md  (CRUD)

치환 변수: ${date}, ${time}, ${title}, ${project}
"""
from __future__ import annotations

import datetime
import os
import re
from typing import Dict, List, Optional

from core_rag import RAG_STORAGE_DIR, _get_storage_name, _get_project_dir

GLOBAL_DIR = os.path.join(RAG_STORAGE_DIR, "_global_templates")
USER_SUBDIR = "_templates"

DEFAULT_TEMPLATES: Dict[str, str] = {
    "IR 미팅": (
        "# ${title}\n\n"
        "- 회사명: \n"
        "- 일시: ${date} ${time}\n"
        "- 참석자: \n\n"
        "## 주요 발언\n- \n\n"
        "## Q&A\n- Q. \n  - A. \n\n"
        "## 팔로업\n- [ ] \n\n"
        "#IR #미팅\n"
    ),
    "산업 조사": (
        "# ${title}\n\n"
        "- 산업: \n"
        "- 일자: ${date}\n\n"
        "## 시장 규모·성장률\n- 시장규모: \n- CAGR: \n\n"
        "## 주요 플레이어\n- \n\n"
        "## 규제·정책\n- \n\n"
        "## 리스크\n- \n\n"
        "## 소스\n- \n\n"
        "#산업조사\n"
    ),
    "딜 가설": (
        "# ${title}\n\n"
        "- 일자: ${date}\n"
        "- 프로젝트: ${project}\n\n"
        "## 가설\n> \n\n"
        "## 근거\n- \n\n"
        "## 반증 조건 (이 조건이 사실이면 가설 기각)\n- \n\n"
        "## 검증 방법\n- \n\n"
        "## 결과\n- \n\n"
        "#가설 #${project}\n"
    ),
    "임원/사용자 인터뷰": (
        "# ${title}\n\n"
        "- 인터뷰이: \n"
        "- 직책·소속: \n"
        "- 일시: ${date} ${time}\n\n"
        "## 주요 인용\n> \n\n"
        "## 인사이트\n- \n\n"
        "## 팔로업 질문\n- [ ] \n\n"
        "#인터뷰\n"
    ),
    "자료 요약": (
        "# ${title}\n\n"
        "- 원자료: \n"
        "- 링크: \n"
        "- 일자: ${date}\n\n"
        "## 한 줄 요약\n> \n\n"
        "## 핵심 포인트\n- \n\n"
        "## 원문 인용\n> \n\n"
        "## 연결 노트\n- [[]]\n\n"
        "#자료요약\n"
    ),
}


# ── 파일 저장소 헬퍼 ──

_SAFE = re.compile(r'[\\/*?:"<>|]')


def _safe_name(name: str) -> str:
    s = _SAFE.sub('', name).strip()
    return s or 'untitled'


def _user_dir(storage_name: str) -> str:
    return os.path.join(_get_project_dir(storage_name), USER_SUBDIR)


def _read_md(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def _write_md(path: str, body: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


# ── Seeding (앱 시작 시 1회 호출) ──

def seed_global_templates():
    """전역 템플릿 디렉토리에 기본 5종을 시드한다. 이미 있으면 덮어쓰지 않음."""
    os.makedirs(GLOBAL_DIR, exist_ok=True)
    for name, body in DEFAULT_TEMPLATES.items():
        path = os.path.join(GLOBAL_DIR, f"{_safe_name(name)}.md")
        if not os.path.exists(path):
            _write_md(path, body)


# ── 변수 치환 ──

_VAR_RE = re.compile(r'\$\{(\w+)\}')


def render_template(body: str, *, title: str = '', project: str = '') -> str:
    now = datetime.datetime.now()
    vars_map = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "title": title,
        "project": project,
    }

    def sub(m):
        return vars_map.get(m.group(1), m.group(0))

    return _VAR_RE.sub(sub, body)


# ── CRUD ──

def list_templates(project_name: str, owner_id: int | None = None) -> List[Dict]:
    """전역 + 프로젝트별 사용자 템플릿 목록. scope='global'|'user' 표시."""
    out: List[Dict] = []
    if os.path.isdir(GLOBAL_DIR):
        for f in sorted(os.listdir(GLOBAL_DIR)):
            if f.endswith(".md"):
                out.append({"name": f[:-3], "scope": "global", "editable": False})
    storage = _get_storage_name(project_name, owner_id=owner_id)
    udir = _user_dir(storage)
    if os.path.isdir(udir):
        for f in sorted(os.listdir(udir)):
            if f.endswith(".md"):
                out.append({"name": f[:-3], "scope": "user", "editable": True})
    return out


def get_template(project_name: str, owner_id: int | None, name: str) -> Optional[Dict]:
    """사용자 템플릿 우선, 없으면 전역."""
    safe = _safe_name(name)
    storage = _get_storage_name(project_name, owner_id=owner_id)
    udir = _user_dir(storage)
    upath = os.path.join(udir, f"{safe}.md")
    if os.path.exists(upath):
        body = _read_md(upath)
        if body is not None:
            return {"name": safe, "scope": "user", "editable": True, "body": body}
    gpath = os.path.join(GLOBAL_DIR, f"{safe}.md")
    if os.path.exists(gpath):
        body = _read_md(gpath)
        if body is not None:
            return {"name": safe, "scope": "global", "editable": False, "body": body}
    return None


def save_user_template(project_name: str, owner_id: int | None, name: str, body: str) -> Dict:
    safe = _safe_name(name)
    if not safe:
        return {"error": "유효하지 않은 템플릿 이름입니다."}
    storage = _get_storage_name(project_name, owner_id=owner_id)
    path = os.path.join(_user_dir(storage), f"{safe}.md")
    _write_md(path, body)
    return {"success": True, "name": safe, "scope": "user"}


def delete_user_template(project_name: str, owner_id: int | None, name: str) -> Dict:
    safe = _safe_name(name)
    storage = _get_storage_name(project_name, owner_id=owner_id)
    path = os.path.join(_user_dir(storage), f"{safe}.md")
    if not os.path.exists(path):
        return {"error": "사용자 템플릿을 찾을 수 없습니다 (전역 템플릿은 삭제 불가)."}
    try:
        os.remove(path)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
