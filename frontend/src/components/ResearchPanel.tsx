/**
 * ResearchPanel — Canvas (left) + Note list (right sidebar).
 * Canvas shows dots with popup editor on double-click.
 * Note list on right side for browsing.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import NoteMarkdownViewer from './NoteMarkdownViewer';
import NoteGraph from './NoteGraph';

interface Note { id: number; slug: string; title: string; content?: string; tags_json?: string; created_at: string; updated_at: string; }
interface Backlink { slug: string; title: string; context: string; }
interface TagInfo { tag: string; count: number; }

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
  hr: { prefix: '\n---\n', suffix: '', placeholder: '', block: true },
  check: { prefix: '- [ ] ', suffix: '', placeholder: '할 일', block: true },
  strike: { prefix: '~~', suffix: '~~', placeholder: '취소선' },
  tag: { prefix: '#', suffix: ' ', placeholder: '태그' },
};

export default function ResearchPanel({ projectName }: { projectName: string }) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [allTags, setAllTags] = useState<TagInfo[]>([]);
  const [showList, setShowList] = useState(true);

  // Editor (in-panel, not popup)
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(true);
  const [viewMode, setViewMode] = useState<'split' | 'edit' | 'preview'>('split');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [graphRefreshKey, setGraphRefreshKey] = useState(0);

  const contentRef = useRef(content);
  const titleRef = useRef(title);
  contentRef.current = content;
  titleRef.current = title;

  const [backlinks, setBacklinks] = useState<Backlink[]>([]);
  const [showBacklinks, setShowBacklinks] = useState(true);
  const [showGraph, setShowGraph] = useState(true); // Default to graph view

  // Context menu
  const [noteCtx, setNoteCtx] = useState<{ x: number; y: number; slug: string; title: string } | null>(null);
  const [renamingSlug, setRenamingSlug] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const existingSlugs = new Set(notes.map(n => n.slug));

  const loadNotes = useCallback(async () => {
    if (!projectName) return;
    try { setNotes(await api.listNotes(projectName, tagFilter || undefined)); } catch {}
  }, [projectName, tagFilter]);

  const loadTags = useCallback(async () => {
    if (!projectName) return;
    try { setAllTags(await api.getNoteTags(projectName)); } catch {}
  }, [projectName]);

  useEffect(() => { loadNotes(); loadTags(); }, [loadNotes, loadTags]);

  useEffect(() => {
    if (!noteCtx) return;
    const close = () => setNoteCtx(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [noteCtx]);

  const selectNote = useCallback(async (slug: string) => {
    if (!projectName) return;
    try {
      const note = await api.getNote(projectName, slug);
      setActiveSlug(slug);
      setTitle(note.title);
      setContent(note.content || '');
      setSaved(true);
      setShowGraph(false); // Switch to editor view
      try { setBacklinks(await api.getNoteBacklinks(projectName, slug)); } catch { setBacklinks([]); }
    } catch {}
  }, [projectName]);

  const handleCreate = useCallback(async () => {
    if (!projectName) return;
    const note = await api.createNote(projectName, { title: '새 노트' });
    if (note?.slug) {
      await loadNotes(); await loadTags();
      selectNote(note.slug);
      setGraphRefreshKey(k => k + 1);
    }
  }, [projectName, loadNotes, loadTags, selectNote]);

  const activeSlugRef = useRef(activeSlug);
  activeSlugRef.current = activeSlug;

  const doSave = useCallback(async () => {
    if (!projectName || !activeSlugRef.current) return;
    setSaving(true);
    try {
      await api.updateNote(projectName, activeSlugRef.current, { content: contentRef.current, title: titleRef.current });
      setSaved(true);
      loadNotes(); loadTags();
      setGraphRefreshKey(k => k + 1);
      try { setBacklinks(await api.getNoteBacklinks(projectName, activeSlugRef.current)); } catch {}
    } catch {}
    setSaving(false);
  }, [projectName, loadNotes, loadTags]);

  const scheduleSave = useCallback(() => {
    setSaved(false);
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(doSave, 1500);
  }, [doSave]);

  const handleDelete = useCallback(async (slug?: string) => {
    const target = slug || activeSlug;
    if (!projectName || !target) return;
    if (!confirm('이 노트를 삭제하시겠습니까?')) return;
    await api.deleteNote(projectName, target);
    if (target === activeSlug) { setActiveSlug(null); setContent(''); setTitle(''); setShowGraph(true); }
    loadNotes(); loadTags();
    setGraphRefreshKey(k => k + 1);
  }, [projectName, activeSlug, loadNotes, loadTags]);

  const handleRename = useCallback(async (slug: string, newTitle: string) => {
    if (!projectName || !newTitle.trim()) return;
    await api.updateNote(projectName, slug, { title: newTitle.trim() });
    if (slug === activeSlug) setTitle(newTitle.trim());
    loadNotes(); setRenamingSlug(null);
    setGraphRefreshKey(k => k + 1);
  }, [projectName, activeSlug, loadNotes]);

  const applyTool = (toolId: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const tool = TOOLS[toolId];
    if (!tool) return;
    const start = ta.selectionStart, end = ta.selectionEnd;
    const selected = content.slice(start, end) || tool.placeholder;
    const before = content.slice(0, start), after = content.slice(end);
    const nl = tool.block && start > 0 && before[before.length - 1] !== '\n';
    const ins = (nl ? '\n' : '') + tool.prefix + selected + tool.suffix;
    setContent(before + ins + after); scheduleSave();
    requestAnimationFrame(() => { ta.focus(); ta.setSelectionRange(before.length + (nl ? 1 : 0) + tool.prefix.length, before.length + (nl ? 1 : 0) + tool.prefix.length + selected.length); });
  };

  const handleNavigate = useCallback((inputSlug: string) => {
    if (existingSlugs.has(inputSlug)) { selectNote(inputSlug); return; }
    const byTitle = notes.find(n => n.title.toLowerCase().replace(/\s+/g, '-') === inputSlug || n.title.toLowerCase() === inputSlug.replace(/-/g, ' ') || n.slug === inputSlug);
    if (byTitle) { selectNote(byTitle.slug); return; }
    (async () => {
      const note = await api.createNote(projectName, { title: inputSlug.replace(/-/g, ' ') });
      if (note?.slug) { await loadNotes(); selectNote(note.slug); setGraphRefreshKey(k => k + 1); }
    })();
  }, [existingSlugs, notes, selectNote, projectName, loadNotes]);

  const filteredNotes = search ? notes.filter(n => n.title.toLowerCase().includes(search.toLowerCase())) : notes;
  const ToolBtn = ({ id, label }: { id: string; label: string }) => (
    <button onClick={() => applyTool(id)} className="px-1.5 py-0.5 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded" title={id}>{label}</button>
  );

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Main area: Graph or Editor ── */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Graph (always mounted, display toggle) */}
        <div className={`absolute inset-0 ${showGraph ? '' : 'hidden'}`} style={{ zIndex: showGraph ? 1 : 0 }}>
          <NoteGraph projectName={projectName} activeSlug={activeSlug} refreshKey={graphRefreshKey}
            onNavigate={slug => { selectNote(slug); }}
            onNoteCreated={() => { loadNotes(); loadTags(); }} />
        </div>

        {/* Editor — MarkText-inspired clean design */}
        {!showGraph && activeSlug && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white" style={{ zIndex: 2 }}>
            {/* Top bar */}
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-100 shrink-0">
              <button onClick={() => { setShowGraph(true); setActiveSlug(null); }} className="text-slate-300 hover:text-slate-500 transition-colors">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <input value={title} onChange={e => { setTitle(e.target.value); scheduleSave(); }}
                className="flex-1 text-base font-bold text-slate-800 bg-transparent border-none focus:outline-none" placeholder="제목 없음" />
              <span className={`text-[10px] px-2 py-0.5 rounded-full ${saving ? 'bg-amber-50 text-amber-600' : saved ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-400'}`}>
                {saving ? '저장 중' : saved ? '저장됨' : '수정됨'}
              </span>
              <div className="flex border border-slate-200 rounded-lg overflow-hidden">
                {(['edit', 'split', 'preview'] as const).map(m => (
                  <button key={m} onClick={() => setViewMode(m)}
                    className={`px-2.5 py-1 text-[10px] transition-colors ${viewMode === m ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-50'}`}>
                    {m === 'edit' ? '편집' : m === 'split' ? '분할' : '보기'}
                  </button>
                ))}
              </div>
              {backlinks.length > 0 && (
                <button onClick={() => setShowBacklinks(!showBacklinks)}
                  className={`px-1.5 py-0.5 text-[10px] rounded ${showBacklinks ? 'bg-indigo-50 text-indigo-600' : 'text-slate-400'}`}>
                  ← {backlinks.length}
                </button>
              )}
              <button onClick={() => handleDelete()} className="text-slate-300 hover:text-red-500 transition-colors">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14"/></svg>
              </button>
            </div>
            {/* Toolbar — minimal, MarkText style */}
            {viewMode !== 'preview' && (
              <div className="flex items-center gap-1 px-4 py-1.5 border-b border-slate-50 shrink-0">
                <ToolBtn id="bold" label="B" /><ToolBtn id="italic" label="I" />
                <span className="w-px h-3.5 bg-slate-150 mx-1" />
                <ToolBtn id="h2" label="H2" /><ToolBtn id="h3" label="H3" />
                <span className="w-px h-3.5 bg-slate-150 mx-1" />
                <ToolBtn id="link" label="[[" /><ToolBtn id="tag" label="#" />
                <span className="w-px h-3.5 bg-slate-150 mx-1" />
                <ToolBtn id="ul" label="•" /><ToolBtn id="ol" label="1." /><ToolBtn id="check" label="☐" /><ToolBtn id="quote" label=">" /><ToolBtn id="code" label="</>" /><ToolBtn id="hr" label="—" /><ToolBtn id="strike" label="S̶" /><ToolBtn id="table" label="⊞" />
              </div>
            )}
            <div className="flex-1 flex overflow-hidden">
              {viewMode !== 'preview' && (
                <textarea ref={textareaRef} value={content}
                  onChange={e => { setContent(e.target.value); scheduleSave(); }}
                  onKeyDown={e => {
                    const ta = textareaRef.current!;
                    const start = ta.selectionStart, end = ta.selectionEnd;
                    const val = content;
                    const lineStart = val.lastIndexOf('\n', start - 1) + 1;
                    const currentLine = val.slice(lineStart, val.indexOf('\n', start) === -1 ? val.length : val.indexOf('\n', start));

                    // Ctrl shortcuts
                    if (e.ctrlKey || e.metaKey) {
                      if (e.key === 'b') { e.preventDefault(); applyTool('bold'); return; }
                      if (e.key === 'i') { e.preventDefault(); applyTool('italic'); return; }
                      if (e.key === 'k') { e.preventDefault(); applyTool('link'); return; }
                      if (e.key === 's') { e.preventDefault(); doSave(); return; }
                    }

                    // Tab: indent / Shift+Tab: outdent
                    if (e.key === 'Tab') {
                      e.preventDefault();
                      if (e.shiftKey) {
                        // Outdent: remove leading 2 spaces
                        if (currentLine.startsWith('  ')) {
                          const nc = val.slice(0, lineStart) + val.slice(lineStart + 2);
                          setContent(nc); scheduleSave();
                          requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = Math.max(lineStart, start - 2); });
                        }
                      } else {
                        const nc = val.slice(0, start) + '  ' + val.slice(end);
                        setContent(nc); scheduleSave();
                        requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = start + 2; });
                      }
                      return;
                    }

                    // Enter: auto-continue lists
                    if (e.key === 'Enter') {
                      const listMatch = currentLine.match(/^(\s*)([-*+]|\d+\.)\s/);
                      if (listMatch) {
                        const indent = listMatch[1];
                        const marker = listMatch[2];
                        const textAfterMarker = currentLine.slice(listMatch[0].length);
                        // If empty list item, remove marker instead
                        if (!textAfterMarker.trim()) {
                          e.preventDefault();
                          const nc = val.slice(0, lineStart) + '\n' + val.slice(lineStart + currentLine.length);
                          setContent(nc); scheduleSave();
                          requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = lineStart + 1; });
                          return;
                        }
                        e.preventDefault();
                        // Increment number for ordered lists
                        let nextMarker = marker;
                        if (/\d+\./.test(marker)) {
                          nextMarker = (parseInt(marker) + 1) + '.';
                        }
                        const ins = `\n${indent}${nextMarker} `;
                        const nc = val.slice(0, start) + ins + val.slice(end);
                        setContent(nc); scheduleSave();
                        requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = start + ins.length; });
                        return;
                      }
                    }
                  }}
                  className={`${viewMode === 'split' ? 'w-1/2 border-r border-slate-100' : 'w-full'} px-6 py-4 text-[15px] text-slate-700 resize-none focus:outline-none bg-white`}
                  style={{ fontFamily: "'JetBrains Mono','Fira Code','Consolas','Monaco',monospace", lineHeight: '1.8', letterSpacing: '-0.01em' }}
                  placeholder="마크다운으로 작성하세요..." />
              )}
              {viewMode !== 'edit' && (
                <div className={`${viewMode === 'split' ? 'w-1/2' : 'w-full'} px-6 py-4 overflow-y-auto text-[15px] leading-relaxed bg-white`}>
                  {content ? <NoteMarkdownViewer content={content} existingSlugs={existingSlugs} onNavigate={handleNavigate} onTagClick={tag => setTagFilter(tag)} /> : <span className="text-slate-400">미리보기</span>}
                </div>
              )}
            </div>
            {showBacklinks && backlinks.length > 0 && (
              <div className="border-t border-slate-200 px-3 py-2 bg-slate-50/50 max-h-28 overflow-y-auto">
                <div className="text-[10px] font-semibold text-slate-400 mb-1">← 백링크</div>
                {backlinks.map(bl => (
                  <button key={bl.slug} onClick={() => selectNote(bl.slug)}
                    className="block w-full text-left px-2 py-1 rounded hover:bg-slate-100 text-xs">
                    <span className="font-medium text-indigo-600">{bl.title}</span>
                    {bl.context && <span className="text-[10px] text-slate-400 ml-2">{bl.context}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Right sidebar: Note list ── */}
      {showList && (
        <div className="w-48 shrink-0 border-l border-slate-200 flex flex-col overflow-hidden bg-white">
          <div className="p-2 space-y-1.5 border-b border-slate-100">
            <div className="flex gap-1">
              <button onClick={handleCreate}
                className="flex-1 px-2 py-1.5 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">+ 새 노트</button>
              <button onClick={() => setShowList(false)}
                className="px-1.5 py-1.5 text-slate-400 hover:text-slate-600 text-xs">✕</button>
            </div>
            <button onClick={() => setShowGraph(!showGraph)}
              className={`w-full px-2 py-1 text-xs rounded-lg border flex items-center justify-center gap-1 ${showGraph ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'}`}>
              🕸 {showGraph ? '캔버스' : '캔버스 보기'}
            </button>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="검색..."
              className="w-full px-2 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-400" />
          </div>
          <div className="flex-1 overflow-y-auto">
            {filteredNotes.map(n => (
              <div key={n.slug}
                onClick={() => selectNote(n.slug)}
                onContextMenu={e => { e.preventDefault(); setNoteCtx({ x: e.clientX, y: e.clientY, slug: n.slug, title: n.title }); }}
                className={`w-full text-left px-3 py-2 border-b border-slate-50 cursor-pointer transition-colors ${
                  n.slug === activeSlug ? 'bg-indigo-50 border-l-2 border-l-indigo-500' : 'hover:bg-slate-50'
                }`}>
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
                    <div className="text-[10px] text-slate-400 mt-0.5">{new Date(n.updated_at).toLocaleDateString('ko')}</div>
                  </>
                )}
              </div>
            ))}
            {filteredNotes.length === 0 && <div className="px-3 py-4 text-xs text-slate-400 text-center">{notes.length === 0 ? '노트 없음' : '결과 없음'}</div>}
          </div>
          {allTags.length > 0 && (
            <div className="border-t border-slate-200 p-2 max-h-28 overflow-y-auto">
              <div className="text-[10px] font-semibold text-slate-400 mb-1">태그</div>
              <div className="flex flex-wrap gap-1">
                {tagFilter && <button onClick={() => setTagFilter(null)} className="px-1.5 py-0.5 text-[10px] bg-red-50 text-red-500 rounded-full">✕</button>}
                {allTags.filter(t => !t.tag.includes('/')).map(t => (
                  <button key={t.tag} onClick={() => setTagFilter(t.tag === tagFilter ? null : t.tag)}
                    className={`px-1.5 py-0.5 text-[10px] rounded-full ${t.tag === tagFilter ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-indigo-50'}`}>
                    #{t.tag} <span className="opacity-60">{t.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Show list button when hidden */}
      {!showList && (
        <button onClick={() => setShowList(true)}
          className="absolute top-2 right-2 z-10 px-2 py-1 text-[10px] bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 shadow-sm">
          목록 ▸
        </button>
      )}

      {/* Note list context menu */}
      {noteCtx && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[140px]"
          style={{ left: noteCtx.x, top: noteCtx.y }} onClick={e => e.stopPropagation()}>
          <button className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50"
            onClick={() => { setRenamingSlug(noteCtx.slug); setRenameValue(noteCtx.title); setNoteCtx(null); }}>✏️ 이름 변경</button>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-4 py-2 text-sm hover:bg-red-50 text-red-600"
            onClick={() => { handleDelete(noteCtx.slug); setNoteCtx(null); }}>🗑 삭제</button>
        </div>,
        document.body
      )}
    </div>
  );
}
