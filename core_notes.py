"""
Research notes module — Obsidian-like wikilinks, backlinks, tags.
"""
import json
import re
from typing import Dict, List, Optional

from backend.database import get_db

# ── Slug ──

def slugify(title: str) -> str:
    """Korean-safe slug: lowercase, spaces→hyphens, strip specials."""
    s = title.strip().lower()
    s = re.sub(r'[\\/*?:"<>|]', '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'untitled'


# ── Wikilink parsing ──

_WIKILINK_RE = re.compile(r'\[\[([^\]]+)\]\]')

def parse_wikilinks(content: str) -> List[Dict]:
    """Extract [[slug]], [[slug#heading]], [[slug|alias]] from content.
    Returns list of {slug, heading, alias}.
    """
    results = []
    for m in _WIKILINK_RE.finditer(content):
        inner = m.group(1).strip()
        alias = None
        heading = None
        if '|' in inner:
            inner, alias = inner.split('|', 1)
            inner = inner.strip()
            alias = alias.strip()
        if '#' in inner:
            inner, heading = inner.split('#', 1)
            inner = inner.strip()
            heading = heading.strip()
        slug = slugify(inner) if inner else ''
        if slug:
            results.append({'slug': slug, 'heading': heading, 'alias': alias})
    return results


# ── Tag parsing ──

_TAG_RE = re.compile(r'(?:^|\s)#([\w가-힣/\-]+)', re.UNICODE)
_CODE_BLOCK_RE = re.compile(r'(`{1,3})[^`]*?\1', re.DOTALL)

def parse_tags(content: str) -> List[str]:
    """Extract #tag and #parent/child from content (not inside code blocks)."""
    # Remove code blocks to avoid false positives
    cleaned = _CODE_BLOCK_RE.sub('', content)
    tags = set()
    for m in _TAG_RE.finditer(cleaned):
        tag = m.group(1)
        tags.add(tag)
        # Add parent prefixes for hierarchy: "시장/경쟁" → also add "시장"
        parts = tag.split('/')
        for i in range(1, len(parts)):
            tags.add('/'.join(parts[:i]))
    return sorted(tags)


# ── Backlink computation ──

def compute_backlinks(project_id: int, note_id: int, content: str):
    """Recompute note_backlinks table for a given note."""
    links = parse_wikilinks(content)
    with get_db() as conn:
        conn.execute("DELETE FROM note_backlinks WHERE source_note_id = ?", (note_id,))
        for link in links:
            # Extract context snippet around the link
            pattern = re.compile(re.escape(f'[[') + r'[^\]]*' + re.escape(link['slug']) + r'[^\]]*' + re.escape(']]'))
            match = pattern.search(content)
            ctx = ''
            if match:
                start = max(0, match.start() - 40)
                end = min(len(content), match.end() + 40)
                ctx = content[start:end].replace('\n', ' ').strip()
            conn.execute(
                "INSERT INTO note_backlinks (project_id, source_note_id, target_slug, context) VALUES (?, ?, ?, ?)",
                (project_id, note_id, link['slug'], ctx),
            )


# ── Tag computation ──

def compute_tags(project_id: int, note_id: int, content: str, explicit_tags: List[str] = None):
    """Recompute note_tags table for a given note."""
    content_tags = parse_tags(content)
    all_tags = set(content_tags)
    if explicit_tags:
        for t in explicit_tags:
            all_tags.add(t)
            # Also add parent prefixes
            parts = t.split('/')
            for i in range(1, len(parts)):
                all_tags.add('/'.join(parts[:i]))

    with get_db() as conn:
        conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
        for tag in sorted(all_tags):
            conn.execute(
                "INSERT INTO note_tags (project_id, note_id, tag) VALUES (?, ?, ?)",
                (project_id, note_id, tag),
            )


# ── CRUD helpers ──

def _get_project_id(project_name: str, owner_id: int) -> Optional[int]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE name = ? AND owner_id = ?",
            (project_name, owner_id),
        ).fetchone()
        return row["id"] if row else None


def list_notes(project_name: str, owner_id: int, tag: str = None) -> List[Dict]:
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return []
    with get_db() as conn:
        if tag:
            # Filter by tag (includes hierarchy: filtering "투자" also matches "투자/PEF")
            rows = conn.execute("""
                SELECT DISTINCT rn.id, rn.slug, rn.title, rn.tags_json, rn.created_at, rn.updated_at
                FROM research_notes rn
                JOIN note_tags nt ON nt.note_id = rn.id
                WHERE rn.project_id = ? AND (nt.tag = ? OR nt.tag LIKE ?)
                ORDER BY rn.updated_at DESC
            """, (pid, tag, f"{tag}/%")).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, slug, title, tags_json, created_at, updated_at FROM research_notes WHERE project_id = ? ORDER BY updated_at DESC",
                (pid,),
            ).fetchall()
    return [dict(r) for r in rows]


def create_note(project_name: str, owner_id: int, title: str, content: str = '', tags: List[str] = None) -> Dict:
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return {"error": "프로젝트를 찾을 수 없습니다."}
    slug = slugify(title)
    tags = tags or []
    with get_db() as conn:
        # Ensure unique slug
        existing = conn.execute(
            "SELECT id FROM research_notes WHERE project_id = ? AND slug = ?", (pid, slug)
        ).fetchone()
        if existing:
            # Append numeric suffix
            i = 2
            while conn.execute("SELECT id FROM research_notes WHERE project_id = ? AND slug = ?", (pid, f"{slug}-{i}")).fetchone():
                i += 1
            slug = f"{slug}-{i}"
        conn.execute(
            "INSERT INTO research_notes (project_id, slug, title, content, tags_json) VALUES (?, ?, ?, ?, ?)",
            (pid, slug, title, content, json.dumps(tags, ensure_ascii=False)),
        )
        note = conn.execute(
            "SELECT id, slug, title, content, tags_json, created_at, updated_at FROM research_notes WHERE project_id = ? AND slug = ?",
            (pid, slug),
        ).fetchone()
    note = dict(note)
    # Compute backlinks and tags
    compute_backlinks(pid, note["id"], content)
    compute_tags(pid, note["id"], content, tags)
    return note


def get_note(project_name: str, owner_id: int, slug: str) -> Optional[Dict]:
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, slug, title, content, tags_json, created_at, updated_at FROM research_notes WHERE project_id = ? AND slug = ?",
            (pid, slug),
        ).fetchone()
    return dict(row) if row else None


def update_note(project_name: str, owner_id: int, slug: str, title: str = None, content: str = None, tags: List[str] = None) -> Dict:
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return {"error": "프로젝트를 찾을 수 없습니다."}
    with get_db() as conn:
        note = conn.execute(
            "SELECT id, content, tags_json FROM research_notes WHERE project_id = ? AND slug = ?",
            (pid, slug),
        ).fetchone()
        if not note:
            return {"error": f"노트 '{slug}'를 찾을 수 없습니다."}

        sets = ["updated_at = CURRENT_TIMESTAMP"]
        params = []
        if title is not None:
            sets.append("title = ?")
            params.append(title)
        if content is not None:
            sets.append("content = ?")
            params.append(content)
        if tags is not None:
            sets.append("tags_json = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        params.append(pid)
        params.append(slug)
        conn.execute(
            f"UPDATE research_notes SET {', '.join(sets)} WHERE project_id = ? AND slug = ?",
            params,
        )
        updated = conn.execute(
            "SELECT id, slug, title, content, tags_json, created_at, updated_at FROM research_notes WHERE project_id = ? AND slug = ?",
            (pid, slug),
        ).fetchone()

    updated = dict(updated)
    final_content = content if content is not None else note["content"]
    final_tags = tags if tags is not None else json.loads(note["tags_json"] or '[]')
    compute_backlinks(pid, updated["id"], final_content)
    compute_tags(pid, updated["id"], final_content, final_tags)
    return updated


def delete_note(project_name: str, owner_id: int, slug: str) -> Dict:
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return {"error": "프로젝트를 찾을 수 없습니다."}
    with get_db() as conn:
        note = conn.execute(
            "SELECT id FROM research_notes WHERE project_id = ? AND slug = ?", (pid, slug)
        ).fetchone()
        if not note:
            return {"error": f"노트 '{slug}'를 찾을 수 없습니다."}
        conn.execute("DELETE FROM research_notes WHERE id = ?", (note["id"],))
    return {"success": True}


def get_backlinks(project_name: str, owner_id: int, slug: str) -> List[Dict]:
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return []
    with get_db() as conn:
        rows = conn.execute("""
            SELECT rn.slug, rn.title, nb.context
            FROM note_backlinks nb
            JOIN research_notes rn ON nb.source_note_id = rn.id
            WHERE nb.project_id = ? AND nb.target_slug = ?
            ORDER BY rn.updated_at DESC
        """, (pid, slug)).fetchall()
    return [dict(r) for r in rows]


def get_graph(project_name: str, owner_id: int) -> Dict:
    """Return graph data: nodes (notes) + edges (wikilinks between them)."""
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return {"nodes": [], "edges": []}
    with get_db() as conn:
        notes = conn.execute(
            "SELECT id, slug, title, content, canvas_x, canvas_y, canvas_color "
            "FROM research_notes WHERE project_id = ?", (pid,)
        ).fetchall()
        slugs = {r["slug"] for r in notes}
        # Per-note tags (single query, grouped client-side)
        tag_map: Dict[int, List[str]] = {}
        for r in conn.execute(
            "SELECT note_id, tag FROM note_tags WHERE project_id = ?", (pid,)
        ).fetchall():
            tag_map.setdefault(r["note_id"], []).append(r["tag"])
        # Also build title→slug map for fuzzy matching
        title_to_slug = {}
        for r in notes:
            title_to_slug[slugify(r["title"])] = r["slug"]
            title_to_slug[r["slug"]] = r["slug"]
        nodes = [{
            "slug": r["slug"], "title": r["title"],
            "content": r["content"] or "",
            "canvas_x": r["canvas_x"], "canvas_y": r["canvas_y"], "canvas_color": r["canvas_color"],
            "tags": sorted(tag_map.get(r["id"], [])),
        } for r in notes]

        links = conn.execute(
            "SELECT rn.slug AS source, nb.target_slug AS target FROM note_backlinks nb JOIN research_notes rn ON nb.source_note_id = rn.id WHERE nb.project_id = ?",
            (pid,),
        ).fetchall()
        # Match edges: try exact slug, then title-based slug mapping
        edges = []
        for r in links:
            target = r["target"]
            if target in slugs:
                edges.append({"source": r["source"], "target": target})
            elif target in title_to_slug:
                edges.append({"source": r["source"], "target": title_to_slug[target]})
    return {"nodes": nodes, "edges": edges}


def save_canvas_positions(project_name: str, owner_id: int, positions: Dict) -> Dict:
    """Save canvas node positions/colors to DB. positions = {slug: {x, y, color}}"""
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return {"error": "프로젝트를 찾을 수 없습니다."}
    with get_db() as conn:
        for slug, pos in positions.items():
            conn.execute(
                "UPDATE research_notes SET canvas_x = ?, canvas_y = ?, canvas_color = ? WHERE project_id = ? AND slug = ?",
                (pos.get("x"), pos.get("y"), pos.get("color"), pid, slug),
            )
    return {"success": True}


_FTS_AVAILABLE: Optional[bool] = None

def _fts_available() -> bool:
    global _FTS_AVAILABLE
    if _FTS_AVAILABLE is None:
        try:
            with get_db() as conn:
                conn.execute("SELECT count(*) FROM notes_fts").fetchone()
            _FTS_AVAILABLE = True
        except Exception:
            _FTS_AVAILABLE = False
    return _FTS_AVAILABLE


def _escape_fts(q: str) -> str:
    """FTS5 MATCH-safe quoting: wrap each whitespace-separated token in double quotes."""
    out = []
    for tok in q.strip().split():
        tok = tok.replace('"', '""')
        out.append(f'"{tok}"')
    return ' '.join(out)


def search_notes(
    project_name: str,
    owner_id: int,
    query: str = '',
    tags: List[str] = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
) -> List[Dict]:
    """Full-text + tag + date range search. Returns notes with snippet."""
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return []
    tags = [t for t in (tags or []) if t]
    q = (query or '').strip()

    where = ["rn.project_id = ?"]
    params: List = [pid]
    joins = []
    select_extra = ""
    order = "rn.updated_at DESC"

    use_fts = bool(q) and _fts_available()
    if use_fts:
        joins.append("JOIN notes_fts fts ON fts.rowid = rn.id")
        where.append("notes_fts MATCH ?")
        params.append(_escape_fts(q))
        select_extra = ", snippet(notes_fts, 1, '<mark>', '</mark>', '…', 16) AS snippet"
        order = "rank"
    elif q:
        like = f"%{q}%"
        where.append("(rn.title LIKE ? OR rn.content LIKE ?)")
        params.extend([like, like])

    if tags:
        # AND-match: a note must have ALL filter tags (or any with hierarchical descendants)
        tag_conds = []
        for t in tags:
            tag_conds.append(
                "EXISTS (SELECT 1 FROM note_tags nt WHERE nt.note_id = rn.id AND (nt.tag = ? OR nt.tag LIKE ?))"
            )
            params.extend([t, f"{t}/%"])
        where.append("(" + " AND ".join(tag_conds) + ")")

    if date_from:
        where.append("rn.updated_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("rn.updated_at <= ?")
        params.append(date_to)

    sql = (
        f"SELECT rn.id, rn.slug, rn.title, rn.tags_json, rn.created_at, rn.updated_at"
        f"{select_extra} "
        f"FROM research_notes rn "
        + " ".join(joins) +
        f" WHERE " + " AND ".join(where) +
        f" ORDER BY {order} LIMIT ?"
    )
    params.append(int(limit))

    out: List[Dict] = []
    with get_db() as conn:
        try:
            rows = conn.execute(sql, params).fetchall()
        except Exception:
            # FTS query parse error → retry as LIKE search (one-shot, no infinite loop)
            if use_fts:
                like = f"%{q}%"
                fb_where = ["rn.project_id = ?", "(rn.title LIKE ? OR rn.content LIKE ?)"]
                fb_params: List = [pid, like, like]
                if tags:
                    for t in tags:
                        fb_where.append(
                            "EXISTS (SELECT 1 FROM note_tags nt WHERE nt.note_id = rn.id AND (nt.tag = ? OR nt.tag LIKE ?))"
                        )
                        fb_params.extend([t, f"{t}/%"])
                if date_from:
                    fb_where.append("rn.updated_at >= ?"); fb_params.append(date_from)
                if date_to:
                    fb_where.append("rn.updated_at <= ?"); fb_params.append(date_to)
                fb_params.append(int(limit))
                rows = conn.execute(
                    "SELECT rn.id, rn.slug, rn.title, rn.tags_json, rn.created_at, rn.updated_at, "
                    "substr(rn.content, 1, 160) AS snippet "
                    "FROM research_notes rn WHERE " + " AND ".join(fb_where) +
                    " ORDER BY rn.updated_at DESC LIMIT ?",
                    fb_params,
                ).fetchall()
            else:
                return []

        for r in rows:
            d = dict(r)
            if 'snippet' not in d or d['snippet'] is None:
                preview_row = conn.execute(
                    "SELECT substr(content, 1, 160) AS p FROM research_notes WHERE id = ?", (d['id'],)
                ).fetchone()
                d['snippet'] = (preview_row['p'] if preview_row else '') or ''
            out.append(d)
    return out


def get_tags(project_name: str, owner_id: int) -> List[Dict]:
    """Get all tags with counts, structured for hierarchy."""
    pid = _get_project_id(project_name, owner_id)
    if not pid:
        return []
    with get_db() as conn:
        rows = conn.execute("""
            SELECT tag, COUNT(DISTINCT note_id) as count
            FROM note_tags WHERE project_id = ?
            GROUP BY tag ORDER BY tag
        """, (pid,)).fetchall()
    return [dict(r) for r in rows]


# ── AI helpers (Gemini via ai_client) ──

_AI_MODEL = "gemini-2.5-flash"


def _gemini_text(api_key: str, prompt: str, json_mode: bool = False) -> str:
    """Single-shot Gemini text generation. Returns response text or raises."""
    from ai_client import get_client
    client = get_client(api_key)
    config = None
    if json_mode:
        try:
            from google.genai import types as gtypes
            config = gtypes.GenerateContentConfig(response_mime_type="application/json")
        except Exception:
            config = None
    resp = client.models.generate_content(model=_AI_MODEL, contents=prompt, config=config)
    return getattr(resp, "text", "") or ""


def summarize_note(project_name: str, owner_id: int, slug: str, api_key: str) -> Dict:
    note = get_note(project_name, owner_id, slug)
    if not note:
        return {"error": "노트를 찾을 수 없습니다."}
    content = (note.get("content") or "").strip()
    if not content:
        return {"summary": "(빈 노트)"}
    prompt = (
        "다음 노트 내용을 한국어로 3~5줄, 핵심만 요약하세요. "
        "불필요한 머리말 없이 본문만 출력. 마크다운 사용 금지.\n\n"
        f"# {note.get('title', '')}\n\n{content}"
    )
    try:
        summary = _gemini_text(api_key, prompt).strip()
        return {"summary": summary}
    except Exception as e:
        return {"error": f"요약 실패: {e}"}


def recommend_related_notes(project_name: str, owner_id: int, slug: str, api_key: str, top_k: int = 5) -> Dict:
    """Use LLM to pick most relevant notes from the same project."""
    note = get_note(project_name, owner_id, slug)
    if not note:
        return {"error": "노트를 찾을 수 없습니다."}
    pid = _get_project_id(project_name, owner_id)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT slug, title, substr(content, 1, 200) AS preview FROM research_notes "
            "WHERE project_id = ? AND slug != ? ORDER BY updated_at DESC LIMIT 60",
            (pid, slug),
        ).fetchall()
    candidates = [dict(r) for r in rows]
    if not candidates:
        return {"items": []}

    cand_text = "\n".join(
        f"- slug={c['slug']} | {c['title']} :: {(c.get('preview') or '').strip()[:100]}"
        for c in candidates
    )
    prompt = (
        "당신은 노트 관계 분석가입니다. 아래 [기준 노트]와 가장 관련성이 높은 후보 노트를 "
        f"최대 {top_k}개 선정하세요. JSON 배열로만 답하세요. 형식: "
        '[{"slug":"...","reason":"한 줄 이유"}, ...]\n\n'
        f"[기준 노트]\n# {note.get('title','')}\n{(note.get('content') or '')[:1500]}\n\n"
        f"[후보 노트]\n{cand_text}\n"
    )
    try:
        raw = _gemini_text(api_key, prompt, json_mode=True)
        items = json.loads(raw)
        if not isinstance(items, list):
            items = []
        # Enrich with title from candidates
        title_map = {c["slug"]: c["title"] for c in candidates}
        out = []
        for it in items[:top_k]:
            s = it.get("slug")
            if s in title_map:
                out.append({"slug": s, "title": title_map[s], "reason": it.get("reason", "")})
        return {"items": out}
    except Exception as e:
        return {"error": f"추천 실패: {e}", "items": []}


def auto_tag_note(project_name: str, owner_id: int, slug: str, api_key: str, max_tags: int = 5, apply: bool = False) -> Dict:
    note = get_note(project_name, owner_id, slug)
    if not note:
        return {"error": "노트를 찾을 수 없습니다."}
    content = (note.get("content") or "").strip()
    if not content:
        return {"tags": []}
    prompt = (
        f"다음 노트의 주제를 대표하는 한국어 태그를 최대 {max_tags}개 추천하세요. "
        "JSON 배열로만 답하세요. 예: [\"투자\",\"PEF/실사\",\"법률\"]. "
        "각 태그는 1~12자, 공백 없음, 계층은 / 로 표현 가능.\n\n"
        f"# {note.get('title','')}\n\n{content[:3000]}"
    )
    try:
        raw = _gemini_text(api_key, prompt, json_mode=True)
        tags = json.loads(raw)
        if not isinstance(tags, list):
            tags = []
        tags = [str(t).strip().lstrip('#') for t in tags if str(t).strip()][:max_tags]
        if apply and tags:
            existing = json.loads(note.get("tags_json") or "[]")
            merged = sorted(set(existing) | set(tags))
            update_note(project_name, owner_id, slug, tags=merged)
        return {"tags": tags, "applied": bool(apply)}
    except Exception as e:
        return {"error": f"태깅 실패: {e}", "tags": []}
