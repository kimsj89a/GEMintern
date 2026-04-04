/**
 * ResearchPanel — Obsidian-like research notes with wikilinks, backlinks, tags.
 * Two-column layout: note list (left) + editor/preview (right).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import NoteMarkdownViewer from './NoteMarkdownViewer';
import NoteGraph from './NoteGraph';

interface Note {
  id: number;
  slug: string;
  title: string;
  content?: string;
  tags_json?: string;
  created_at: string;
  updated_at: string;
}

interface Backlink {
  slug: string;
  title: string;
  context: string;
}

interface TagInfo {
  tag: string;
  count: number;
}

// ── Markdown toolbar ──
const TOOLS: Record<string, { prefix: string; suffix: string; placeholder: string; block?: boolean }> = {
  bold: { prefix: '**', suffix: '**', placeholder: '굵은 텍스트' },
  italic: { prefix: '_', suffix: '_', placeholder: '기울임' },
  h2: { prefix: '## ', suffix: '', placeholder: '제목', block: true },
  h3: { prefix: '### ', suffix: '', placeholder: '소제목', block: true },
  link: { prefix: '[[', suffix: ']]', placeholder: '노트 이름' },
  ul: { prefix: '- ', suffix: '', placeholder: '항목', block: true },
  ol: { prefix: '1. ', suffix: '', placeholder: '항목', block: true },
  quote: { prefix: '> ', suffix: '', placeholder: '인용', block: true },
  code: { prefix: '`', suffix: '`', placeholder: 'code' },
  table: { prefix: '| 헤더1 | 헤더2 |\n|-------|-------|\n| ', suffix: ' | 값2 |', placeholder: '값1', block: true },
  tag: { prefix: '#', suffix: ' ', placeholder: '태그' },
};

export default function ResearchPanel({ projectName }: { projectName: string }) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [allTags, setAllTags] = useState<TagInfo[]>([]);

  // Editor
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(true);
  const [viewMode, setViewMode] = useState<'split' | 'edit' | 'preview'>('split');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Use refs for latest values (fixes stale closure in debounced save)
  const contentRef = useRef(content);
  const titleRef = useRef(title);
  contentRef.current = content;
  titleRef.current = title;

  // Backlinks
  const [backlinks, setBacklinks] = useState<Backlink[]>([]);
  const [showBacklinks, setShowBacklinks] = useState(true);
  const [showGraph, setShowGraph] = useState(false);

  // Note list context menu
  const [noteCtx, setNoteCtx] = useState<{ x: number; y: number; slug: string; title: string } | null>(null);
  const [renamingSlug, setRenamingSlug] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  // Note list drag reorder
  const [dragSlug, setDragSlug] = useState<string | null>(null);
  const [dropIndex, setDropIndex] = useState<number | null>(null);

  const existingSlugs = new Set(notes.map(n => n.slug));

  // ── Load ──
  const loadNotes = useCallback(async () => {
    if (!projectName) return;
    try { setNotes(await api.listNotes(projectName, tagFilter || undefined)); } catch {}
  }, [projectName, tagFilter]);

  const loadTags = useCallback(async () => {
    if (!projectName) return;
    try { setAllTags(await api.getNoteTags(projectName)); } catch {}
  }, [projectName]);

  useEffect(() => { loadNotes(); loadTags(); }, [loadNotes, loadTags]);

  // Close context menu
  useEffect(() => {
    if (!noteCtx) return;
    const close = () => setNoteCtx(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [noteCtx]);

  // ── Select note ──
  const selectNote = useCallback(async (slug: string) => {
    if (!projectName) return;
    try {
      const note = await api.getNote(projectName, slug);
      setActiveSlug(slug);
      setTitle(note.title);
      setContent(note.content || '');
      setSaved(true);
      try { setBacklinks(await api.getNoteBacklinks(projectName, slug)); } catch { setBacklinks([]); }
    } catch {}
  }, [projectName]);

  // ── Create ──
  const handleCreate = useCallback(async () => {
    if (!projectName) return;
    const note = await api.createNote(projectName, { title: '새 노트' });
    if (note?.slug) {
      await loadNotes();
      await loadTags();
      selectNote(note.slug);
    }
  }, [projectName, loadNotes, loadTags, selectNote]);

  // ── Auto-save (refs to avoid stale closure) ──
  const activeSlugRef = useRef(activeSlug);
  activeSlugRef.current = activeSlug;

  const doSave = useCallback(async () => {
    if (!projectName || !activeSlugRef.current) return;
    setSaving(true);
    try {
      await api.updateNote(projectName, activeSlugRef.current, {
        content: contentRef.current,
        title: titleRef.current,
      });
      setSaved(true);
      loadNotes();
      loadTags();
      try { setBacklinks(await api.getNoteBacklinks(projectName, activeSlugRef.current)); } catch {}
    } catch {}
    setSaving(false);
  }, [projectName, loadNotes, loadTags]);

  const scheduleSave = useCallback(() => {
    setSaved(false);
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(doSave, 1500);
  }, [doSave]);

  // ── Delete ──
  const handleDelete = useCallback(async (slug?: string) => {
    const target = slug || activeSlug;
    if (!projectName || !target) return;
    if (!confirm('이 노트를 삭제하시겠습니까?')) return;
    await api.deleteNote(projectName, target);
    if (target === activeSlug) { setActiveSlug(null); setContent(''); setTitle(''); }
    loadNotes(); loadTags();
  }, [projectName, activeSlug, loadNotes, loadTags]);

  // ── Rename ──
  const handleRename = useCallback(async (slug: string, newTitle: string) => {
    if (!projectName || !newTitle.trim()) return;
    await api.updateNote(projectName, slug, { title: newTitle.trim() });
    if (slug === activeSlug) setTitle(newTitle.trim());
    loadNotes();
    setRenamingSlug(null);
  }, [projectName, activeSlug, loadNotes]);

  // ── Toolbar ──
  const applyTool = (toolId: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const tool = TOOLS[toolId];
    if (!tool) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const selected = content.slice(start, end) || tool.placeholder;
    const before = content.slice(0, start);
    const after = content.slice(end);
    const needNewline = tool.block && start > 0 && before[before.length - 1] !== '\n';
    const insertion = (needNewline ? '\n' : '') + tool.prefix + selected + tool.suffix;
    const newContent = before + insertion + after;
    setContent(newContent);
    scheduleSave();
    requestAnimationFrame(() => {
      const prefixStart = before.length + (needNewline ? 1 : 0) + tool.prefix.length;
      ta.focus();
      ta.setSelectionRange(prefixStart, prefixStart + selected.length);
    });
  };

  // ── Navigate wikilink ──
  const handleNavigate = useCallback((slug: string) => {
    if (existingSlugs.has(slug)) {
      selectNote(slug);
    } else {
      (async () => {
        const note = await api.createNote(projectName, { title: slug });
        if (note?.slug) { await loadNotes(); selectNote(note.slug); }
      })();
    }
  }, [existingSlugs, selectNote, projectName, loadNotes]);

  // ── Drag reorder ──
  const handleDragStart = (slug: string) => setDragSlug(slug);
  const handleDragOver = (e: React.DragEvent, index: number) => { e.preventDefault(); setDropIndex(index); };
  const handleDrop = async (targetIndex: number) => {
    if (!dragSlug) return;
    const fromIndex = filteredNotes.findIndex(n => n.slug === dragSlug);
    if (fromIndex < 0 || fromIndex === targetIndex) { setDragSlug(null); setDropIndex(null); return; }
    // Reorder locally (visual only — no backend sort_order field needed for MVP)
    const reordered = [...filteredNotes];
    const [moved] = reordered.splice(fromIndex, 1);
    reordered.splice(targetIndex, 0, moved);
    setNotes(reordered);
    setDragSlug(null);
    setDropIndex(null);
  };

  const filteredNotes = search
    ? notes.filter(n => n.title.toLowerCase().includes(search.toLowerCase()))
    : notes;

  const ToolBtn = ({ id, label }: { id: string; label: string }) => (
    <button onClick={() => applyTool(id)}
      className="px-1.5 py-0.5 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
      title={id}>{label}</button>
  );

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Left: Note list ── */}
      <div className="w-52 shrink-0 border-r border-slate-200 flex flex-col overflow-hidden">
        <div className="p-2 space-y-1.5 border-b border-slate-100">
          <div className="flex gap-1">
            <button onClick={handleCreate}
              className="flex-1 px-2 py-1.5 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors">
              + 새 노트
            </button>
            <button onClick={() => setShowGraph(!showGraph)}
              className={`px-2 py-1.5 text-xs rounded-lg transition-colors ${showGraph ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
              title="그래프 뷰">🕸</button>
          </div>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="노트 검색..."
            className="w-full px-2 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-400" />
        </div>

        <div className="flex-1 overflow-y-auto">
          {filteredNotes.map((n, i) => (
            <div
              key={n.slug}
              draggable
              onDragStart={() => handleDragStart(n.slug)}
              onDragOver={e => handleDragOver(e, i)}
              onDrop={() => handleDrop(i)}
              onDragEnd={() => { setDragSlug(null); setDropIndex(null); }}
              onClick={() => { if (renamingSlug !== n.slug) selectNote(n.slug); }}
              onContextMenu={e => { e.preventDefault(); setNoteCtx({ x: e.clientX, y: e.clientY, slug: n.slug, title: n.title }); }}
              className={`w-full text-left px-3 py-2 border-b transition-colors cursor-grab ${
                dragSlug === n.slug ? 'opacity-40' : ''
              } ${dropIndex === i && dragSlug !== n.slug ? 'border-t-2 border-t-indigo-400' : 'border-b-slate-50'
              } ${n.slug === activeSlug ? 'bg-indigo-50 border-l-2 border-l-indigo-500' : 'hover:bg-slate-50'}`}
            >
              {renamingSlug === n.slug ? (
                <input autoFocus value={renameValue}
                  onChange={e => setRenameValue(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleRename(n.slug, renameValue); if (e.key === 'Escape') setRenamingSlug(null); }}
                  onBlur={() => handleRename(n.slug, renameValue)}
                  onClick={e => e.stopPropagation()}
                  className="w-full px-1 py-0.5 text-xs border border-indigo-300 rounded focus:outline-none" />
              ) : (
                <>
                  <div className="text-xs font-medium text-slate-700 truncate">{n.title}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {new Date(n.updated_at).toLocaleDateString('ko')}
                  </div>
                </>
              )}
            </div>
          ))}
          {filteredNotes.length === 0 && (
            <div className="px-3 py-4 text-xs text-slate-400 text-center">
              {notes.length === 0 ? '노트가 없습니다' : '검색 결과 없음'}
            </div>
          )}
        </div>

        {/* Tags */}
        {allTags.length > 0 && (
          <div className="border-t border-slate-200 p-2 max-h-36 overflow-y-auto">
            <div className="text-[10px] font-semibold text-slate-400 mb-1">태그</div>
            <div className="flex flex-wrap gap-1">
              {tagFilter && (
                <button onClick={() => setTagFilter(null)}
                  className="px-1.5 py-0.5 text-[10px] bg-red-50 text-red-500 rounded-full">✕ 필터 해제</button>
              )}
              {allTags.filter(t => !t.tag.includes('/')).map(t => (
                <button key={t.tag}
                  onClick={() => setTagFilter(t.tag === tagFilter ? null : t.tag)}
                  className={`px-1.5 py-0.5 text-[10px] rounded-full transition-colors ${
                    t.tag === tagFilter ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-indigo-50'
                  }`}>
                  #{t.tag} <span className="text-[9px] opacity-60">{t.count}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Right: Graph or Editor ── */}
      {showGraph ? (
        <div className="flex-1 overflow-hidden">
          <NoteGraph projectName={projectName} activeSlug={activeSlug}
            onNavigate={slug => { setShowGraph(false); selectNote(slug); }} />
        </div>
      ) : activeSlug ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200">
            <input value={title}
              onChange={e => { setTitle(e.target.value); scheduleSave(); }}
              className="flex-1 text-sm font-bold text-slate-800 bg-transparent border-none focus:outline-none"
              placeholder="노트 제목" />
            <span className="text-[10px] text-slate-400">
              {saving ? '저장 중...' : saved ? '저장됨' : '수정됨'}
            </span>
            <div className="flex border border-slate-200 rounded-lg overflow-hidden">
              {(['edit', 'split', 'preview'] as const).map(m => (
                <button key={m} onClick={() => setViewMode(m)}
                  className={`px-2 py-0.5 text-[10px] ${viewMode === m ? 'bg-slate-700 text-white' : 'text-slate-500 hover:bg-slate-100'}`}>
                  {m === 'edit' ? '편집' : m === 'split' ? '분할' : '미리보기'}
                </button>
              ))}
            </div>
            <button onClick={() => setShowBacklinks(!showBacklinks)}
              className={`px-1.5 py-0.5 text-[10px] rounded ${showBacklinks ? 'bg-indigo-50 text-indigo-600' : 'text-slate-400'}`}>
              ← {backlinks.length}
            </button>
            <button onClick={() => handleDelete()} className="text-xs text-slate-400 hover:text-red-500">🗑</button>
          </div>

          {viewMode !== 'preview' && (
            <div className="flex items-center gap-0.5 px-3 py-1 border-b border-slate-100 bg-slate-50/50 flex-wrap">
              <ToolBtn id="bold" label="B" />
              <ToolBtn id="italic" label="I" />
              <span className="w-px h-4 bg-slate-200 mx-0.5" />
              <ToolBtn id="h2" label="H2" />
              <ToolBtn id="h3" label="H3" />
              <span className="w-px h-4 bg-slate-200 mx-0.5" />
              <ToolBtn id="link" label="[[" />
              <ToolBtn id="tag" label="#" />
              <span className="w-px h-4 bg-slate-200 mx-0.5" />
              <ToolBtn id="ul" label="•" />
              <ToolBtn id="ol" label="1." />
              <ToolBtn id="quote" label=">" />
              <ToolBtn id="code" label="<>" />
              <ToolBtn id="table" label="⊞" />
            </div>
          )}

          <div className="flex-1 flex overflow-hidden">
            {viewMode !== 'preview' && (
              <textarea ref={textareaRef} value={content}
                onChange={e => { setContent(e.target.value); scheduleSave(); }}
                onKeyDown={e => {
                  if (e.ctrlKey || e.metaKey) {
                    if (e.key === 'b') { e.preventDefault(); applyTool('bold'); }
                    if (e.key === 'i') { e.preventDefault(); applyTool('italic'); }
                    if (e.key === 'k') { e.preventDefault(); applyTool('link'); }
                    if (e.key === 's') { e.preventDefault(); doSave(); }
                  }
                }}
                className={`${viewMode === 'split' ? 'w-1/2 border-r border-slate-200' : 'w-full'} p-3 text-[13px] text-slate-700 leading-relaxed resize-none focus:outline-none font-mono`}
                placeholder={'마크다운으로 작성하세요...\n\n[[다른노트]]로 링크, #태그로 분류'} />
            )}
            {viewMode !== 'edit' && (
              <div className={`${viewMode === 'split' ? 'w-1/2' : 'w-full'} p-3 overflow-y-auto text-[13px]`}>
                {content ? (
                  <NoteMarkdownViewer content={content} existingSlugs={existingSlugs}
                    onNavigate={handleNavigate} onTagClick={tag => setTagFilter(tag)} />
                ) : (
                  <div className="text-slate-400 text-sm">미리보기가 여기에 표시됩니다</div>
                )}
              </div>
            )}
          </div>

          {showBacklinks && backlinks.length > 0 && (
            <div className="border-t border-slate-200 px-3 py-2 bg-slate-50/50 max-h-32 overflow-y-auto">
              <div className="text-[10px] font-semibold text-slate-400 mb-1">← 이 노트를 참조하는 노트</div>
              {backlinks.map(bl => (
                <button key={bl.slug} onClick={() => selectNote(bl.slug)}
                  className="block w-full text-left px-2 py-1 rounded hover:bg-slate-100 transition-colors">
                  <span className="text-xs font-medium text-indigo-600">{bl.title}</span>
                  {bl.context && <span className="text-[10px] text-slate-400 ml-2">{bl.context}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-400">
          <div className="text-center">
            <div className="text-3xl mb-2">📝</div>
            <div className="text-sm">노트를 선택하거나 새로 만드세요</div>
            <button onClick={handleCreate}
              className="mt-3 px-4 py-1.5 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">
              + 새 노트 만들기
            </button>
          </div>
        </div>
      )}

      {/* Note list context menu */}
      {noteCtx && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[140px]"
          style={{ left: noteCtx.x, top: noteCtx.y }}
          onClick={e => e.stopPropagation()}>
          <button className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 flex items-center gap-2"
            onClick={() => {
              setRenamingSlug(noteCtx.slug);
              setRenameValue(noteCtx.title);
              setNoteCtx(null);
            }}>
            ✏️ 이름 변경
          </button>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-4 py-2 text-sm hover:bg-red-50 text-red-600 flex items-center gap-2"
            onClick={() => { handleDelete(noteCtx.slug); setNoteCtx(null); }}>
            🗑 삭제
          </button>
        </div>,
        document.body
      )}
    </div>
  );
}
