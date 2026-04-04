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
            "SELECT id, slug, title FROM research_notes WHERE project_id = ?", (pid,)
        ).fetchall()
        slugs = {r["slug"] for r in notes}
        nodes = [{"slug": r["slug"], "title": r["title"]} for r in notes]

        links = conn.execute(
            "SELECT rn.slug AS source, nb.target_slug AS target FROM note_backlinks nb JOIN research_notes rn ON nb.source_note_id = rn.id WHERE nb.project_id = ?",
            (pid,),
        ).fetchall()
        # Only include edges where both nodes exist
        edges = [{"source": r["source"], "target": r["target"]} for r in links if r["target"] in slugs]
    return {"nodes": nodes, "edges": edges}


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
