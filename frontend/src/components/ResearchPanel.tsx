/**
 * ResearchPanel — Canvas (left) + Note list (right sidebar).
 * Canvas shows dots with popup editor on double-click.
 * Note list on right side for browsing.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import NoteMarkdownViewer from './NoteMarkdownViewer';
import NoteGraph from './NoteGraph';
import TemplateManager from './TemplateManager';

interface Note { id: number; slug: string; title: string; content?: string; tags_json?: string; snippet?: string; is_inbox?: number; created_at: string; updated_at: string; }
interface Backlink { slug: string; title: string; context: string; }
interface TagInfo { tag: string; count: number; }
interface NoteTemplate { name: string; scope: 'global' | 'user'; editable: boolean; body?: string; }

// Allow only <mark>…</mark> in FTS5 snippet, escape everything else.
function sanitizeSnippet(s: string): string {
  const esc = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return esc.replace(/&lt;mark&gt;/g, '<mark class="bg-yellow-100 text-slate-800 rounded px-0.5">')
            .replace(/&lt;\/mark&gt;/g, '</mark>');
}

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
  const [searchResults, setSearchResults] = useState<Note[] | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showAdvSearch, setShowAdvSearch] = useState(false);
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

  // AI panel
  type AiResult =
    | { type: 'summary'; loading: boolean; text?: string; error?: string }
    | { type: 'related'; loading: boolean; items?: { slug: string; title: string; reason: string }[]; error?: string }
    | { type: 'tags'; loading: boolean; tags?: string[]; applied?: boolean; error?: string };
  const [aiResult, setAiResult] = useState<AiResult | null>(null);
  const [aiMenuOpen, setAiMenuOpen] = useState(false);

  const runSummarize = async () => {
    if (!projectName || !activeSlug) return;
    setAiMenuOpen(false);
    setAiResult({ type: 'summary', loading: true });
    try {
      const r = await api.summarizeNote(projectName, activeSlug);
      setAiResult({ type: 'summary', loading: false, text: r.summary, error: r.error });
    } catch (e: any) { setAiResult({ type: 'summary', loading: false, error: String(e?.message || e) }); }
  };
  const runRelated = async () => {
    if (!projectName || !activeSlug) return;
    setAiMenuOpen(false);
    setAiResult({ type: 'related', loading: true });
    try {
      const r = await api.relatedNotes(projectName, activeSlug);
      setAiResult({ type: 'related', loading: false, items: r.items || [], error: r.error });
    } catch (e: any) { setAiResult({ type: 'related', loading: false, error: String(e?.message || e) }); }
  };
  const runAutoTag = async (apply = false) => {
    if (!projectName || !activeSlug) return;
    setAiMenuOpen(false);
    setAiResult({ type: 'tags', loading: true });
    try {
      const r = await api.autoTagNote(projectName, activeSlug, apply);
      setAiResult({ type: 'tags', loading: false, tags: r.tags || [], applied: r.applied, error: r.error });
      if (apply) { loadTags(); loadNotes(); }
    } catch (e: any) { setAiResult({ type: 'tags', loading: false, error: String(e?.message || e) }); }
  };

  // Reset AI panel when active note changes
  useEffect(() => { setAiResult(null); setAiMenuOpen(false); }, [activeSlug]);

  // Context menu
  const [noteCtx, setNoteCtx] = useState<{ x: number; y: number; slug: string; title: string } | null>(null);
  const [renamingSlug, setRenamingSlug] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  // ── Quick Capture (브레인덤프) + Inbox + Templates ──
  const [quickOpen, setQuickOpen] = useState(false);
  const [quickText, setQuickText] = useState('');
  const [quickSaving, setQuickSaving] = useState(false);
  const [showInbox, setShowInbox] = useState(true);
  const [promoteTarget, setPromoteTarget] = useState<Note | null>(null);
  const [promoteTitle, setPromoteTitle] = useState('');
  const [promoteTags, setPromoteTags] = useState<string[]>([]);
  const [promoteTagInput, setPromoteTagInput] = useState('');
  const [templates, setTemplates] = useState<NoteTemplate[]>([]);
  const [newNoteMenuOpen, setNewNoteMenuOpen] = useState(false);
  const [tplMgrOpen, setTplMgrOpen] = useState(false);

  const existingSlugs = new Set(notes.map(n => n.slug));

  const loadNotes = useCallback(async () => {
    if (!projectName) return;
    try { setNotes(await api.listNotes(projectName)); } catch {}
  }, [projectName]);

  const loadTags = useCallback(async () => {
    if (!projectName) return;
    try { setAllTags(await api.getNoteTags(projectName)); } catch {}
  }, [projectName]);

  const loadTemplates = useCallback(async () => {
    if (!projectName) return;
    try { setTemplates(await api.listNoteTemplates(projectName)); } catch {}
  }, [projectName]);

  useEffect(() => { loadNotes(); loadTags(); loadTemplates(); }, [loadNotes, loadTags, loadTemplates]);

  // Split notes into inbox vs regular for separate UI sections
  const inboxNotes = useMemo(() => notes.filter(n => n.is_inbox), [notes]);
  const nonInboxNotes = useMemo(() => notes.filter(n => !n.is_inbox), [notes]);

  // ── Backend search (FTS5 + tags + date range) ──
  const isSearchActive = !!search.trim() || selectedTags.size > 0 || !!dateFrom || !!dateTo;
  useEffect(() => {
    if (!projectName) return;
    if (!isSearchActive) { setSearchResults(null); return; }
    let cancelled = false;
    setSearchLoading(true);
    const t = setTimeout(async () => {
      try {
        const r = await api.searchNotes(projectName, {
          q: search.trim() || undefined,
          tags: selectedTags.size > 0 ? Array.from(selectedTags) : undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        });
        if (!cancelled) setSearchResults(r);
      } catch { if (!cancelled) setSearchResults([]); }
      finally { if (!cancelled) setSearchLoading(false); }
    }, 250);
    return () => { cancelled = true; clearTimeout(t); };
  }, [projectName, search, selectedTags, dateFrom, dateTo, isSearchActive]);

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

  // ── Quick Capture ──
  const openQuickCapture = useCallback(() => {
    setQuickText('');
    setQuickOpen(true);
  }, []);

  const submitQuickCapture = useCallback(async () => {
    if (!projectName) return;
    setQuickSaving(true);
    try {
      const note = await api.quickCapture(projectName, quickText);
      if (note?.slug) {
        await loadNotes();
        setQuickOpen(false);
        setQuickText('');
        setShowInbox(true);
      }
    } catch {} finally { setQuickSaving(false); }
  }, [projectName, quickText, loadNotes]);

  // Global hotkey: Ctrl+Shift+M → Quick Capture
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && (e.key === 'm' || e.key === 'M')) {
        // 입력 요소에 포커스가 있어도 Quick Capture는 글로벌하게 열어준다
        e.preventDefault();
        openQuickCapture();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openQuickCapture]);

  // ── Promote inbox note ──
  const openPromote = useCallback((n: Note) => {
    setPromoteTarget(n);
    setPromoteTitle(n.title.startsWith('Quick ') ? '' : n.title);
    setPromoteTags([]);
    setPromoteTagInput('');
  }, []);

  const submitPromote = useCallback(async () => {
    if (!projectName || !promoteTarget) return;
    try {
      await api.promoteInboxNote(projectName, promoteTarget.slug, {
        title: promoteTitle.trim() || undefined,
        tags: promoteTags.length > 0 ? promoteTags : undefined,
      });
      setPromoteTarget(null);
      await loadNotes(); await loadTags();
    } catch {}
  }, [projectName, promoteTarget, promoteTitle, promoteTags, loadNotes, loadTags]);

  // ── Templates ──
  const handleCreateFromTemplate = useCallback(async (templateName: string) => {
    if (!projectName) return;
    const userTitle = window.prompt(`"${templateName}" 템플릿으로 새 노트 — 제목:`, templateName);
    if (userTitle === null) return; // cancelled
    const note = await api.createNoteFromTemplate(projectName, templateName, userTitle.trim() || undefined);
    if (note?.slug) {
      await loadNotes(); await loadTags();
      selectNote(note.slug);
      setNewNoteMenuOpen(false);
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

  // ── Autocomplete: slash menu + [[ note picker ──
  type AcMode = null | 'slash' | 'link';
  const [acMode, setAcMode] = useState<AcMode>(null);
  const [acQuery, setAcQuery] = useState('');
  const [acIndex, setAcIndex] = useState(0);
  const [acTriggerStart, setAcTriggerStart] = useState(0); // index in textarea where trigger starts (inclusive of '/' or '[[')

  const closeAc = useCallback(() => { setAcMode(null); setAcQuery(''); setAcIndex(0); }, []);

  // Slash command items
  type SlashCmd = { id: string; label: string; hint: string; toolId: string };
  const SLASH_CMDS = useMemo<SlashCmd[]>(() => [
    { id: 'h2', label: '제목 H2', hint: '## ', toolId: 'h2' },
    { id: 'h3', label: '소제목 H3', hint: '### ', toolId: 'h3' },
    { id: 'ul', label: '글머리 목록', hint: '- ', toolId: 'ul' },
    { id: 'ol', label: '번호 목록', hint: '1. ', toolId: 'ol' },
    { id: 'check', label: '체크박스', hint: '- [ ] ', toolId: 'check' },
    { id: 'quote', label: '인용', hint: '> ', toolId: 'quote' },
    { id: 'code', label: '인라인 코드', hint: '`code`', toolId: 'code' },
    { id: 'codeblock', label: '코드 블록', hint: '```', toolId: '__codeblock' },
    { id: 'hr', label: '구분선', hint: '---', toolId: 'hr' },
    { id: 'link', label: '노트 링크', hint: '[[…]]', toolId: 'link' },
    { id: 'tag', label: '태그', hint: '#tag', toolId: 'tag' },
    { id: 'table', label: '표', hint: '⊞', toolId: 'table' },
    { id: 'strike', label: '취소선', hint: '~~~~', toolId: 'strike' },
  ], []);

  const slashFiltered = useMemo(() => {
    const q = acQuery.toLowerCase();
    if (!q) return SLASH_CMDS;
    return SLASH_CMDS.filter(c => c.label.toLowerCase().includes(q) || c.id.includes(q));
  }, [acQuery, SLASH_CMDS]);

  const linkFiltered = useMemo(() => {
    const q = acQuery.toLowerCase();
    const list = q ? notes.filter(n => n.title.toLowerCase().includes(q) || n.slug.includes(q)) : notes;
    return list.slice(0, 8);
  }, [acQuery, notes]);

  // Reset highlight on filter change
  useEffect(() => { setAcIndex(0); }, [acQuery, acMode]);

  // Replace trigger range with text. Reads textarea.value directly so fast typing
  // never desyncs from React state. Closes autocomplete.
  const replaceTrigger = useCallback((insertText: string, caretOffset?: number) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const cur = ta.value;
    const caret = ta.selectionStart;
    const before = cur.slice(0, acTriggerStart);
    const after = cur.slice(caret);
    const next = before + insertText + after;
    setContent(next); scheduleSave();
    requestAnimationFrame(() => {
      ta.focus();
      const pos = before.length + (caretOffset ?? insertText.length);
      ta.setSelectionRange(pos, pos);
    });
    closeAc();
  }, [acTriggerStart, scheduleSave, closeAc]);

  // Slash commands compute their own insertion against ta.value so we don't depend
  // on React state catching up between setContent and the next frame.
  const acceptSlash = useCallback((cmdId: string) => {
    const cmd = SLASH_CMDS.find(c => c.id === cmdId);
    if (!cmd) { closeAc(); return; }
    const ta = textareaRef.current;
    if (!ta) return;
    const cur = ta.value;
    const caret = ta.selectionStart;
    const before = cur.slice(0, acTriggerStart);
    const after = cur.slice(caret);

    if (cmd.toolId === '__codeblock') {
      const insert = '```\n\n```';
      const next = before + insert + after;
      setContent(next); scheduleSave(); closeAc();
      requestAnimationFrame(() => {
        ta.focus();
        const pos = before.length + 4; // inside the fences
        ta.setSelectionRange(pos, pos);
      });
      return;
    }

    const tool = TOOLS[cmd.toolId];
    if (!tool) { closeAc(); return; }
    // Block-level tools want a leading newline if not already at line start.
    const needsNl = !!tool.block && before.length > 0 && before[before.length - 1] !== '\n';
    const lead = needsNl ? '\n' : '';
    const insert = lead + tool.prefix + tool.placeholder + tool.suffix;
    const next = before + insert + after;
    setContent(next); scheduleSave(); closeAc();
    requestAnimationFrame(() => {
      ta.focus();
      const selStart = before.length + lead.length + tool.prefix.length;
      const selEnd = selStart + tool.placeholder.length;
      ta.setSelectionRange(selStart, selEnd);
    });
  }, [SLASH_CMDS, acTriggerStart, scheduleSave, closeAc]);

  const acceptLink = useCallback((noteTitle: string) => {
    replaceTrigger(`[[${noteTitle}]]`);
  }, [replaceTrigger]);

  // Detect triggers from textarea state
  const detectAcTriggers = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) { closeAc(); return; }
    const caret = ta.selectionStart;
    const text = ta.value.slice(0, caret);

    // [[query → link mode
    const linkM = text.match(/\[\[([^\[\]\n]{0,40})$/);
    if (linkM) {
      setAcMode('link');
      setAcQuery(linkM[1]);
      setAcTriggerStart(caret - linkM[0].length); // include '[['
      return;
    }
    // /query → slash mode (only at line start or after whitespace, max 20 chars)
    const slashM = text.match(/(?:^|\s)\/([^\s\/\n]{0,20})$/);
    if (slashM) {
      setAcMode('slash');
      setAcQuery(slashM[1]);
      // trigger starts at the '/' character
      const slashIdx = caret - slashM[1].length - 1;
      setAcTriggerStart(slashIdx);
      return;
    }
    closeAc();
  }, [closeAc]);

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

  // Inbox 노트는 일반 목록에서 제외 (전용 섹션에서 따로 보여줌)
  const filteredNotes: Note[] = isSearchActive
    ? (searchResults || []).filter(n => !n.is_inbox)
    : nonInboxNotes;
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
              {/* AI menu */}
              <div className="relative">
                <button onClick={() => setAiMenuOpen(v => !v)}
                  className={`px-1.5 py-0.5 text-[10px] rounded border ${aiMenuOpen || aiResult ? 'bg-indigo-50 text-indigo-600 border-indigo-200' : 'text-slate-500 border-slate-200 hover:bg-slate-50'}`}
                  title="AI 보조">✨ AI</button>
                {aiMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 z-30 bg-white border border-slate-200 rounded-lg shadow-lg py-1 min-w-[140px]"
                    onMouseLeave={() => setAiMenuOpen(false)}>
                    <button onClick={runSummarize} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50">📝 요약</button>
                    <button onClick={runRelated} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50">🔗 관련 노트</button>
                    <button onClick={() => runAutoTag(false)} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50">🏷 태그 추천</button>
                    <button onClick={() => runAutoTag(true)} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50">🏷 태그 추천+적용</button>
                  </div>
                )}
              </div>
              {/* Export */}
              <button onClick={() => {
                const blob = new Blob([`# ${title}\n\n${content}`], { type: 'text/markdown' });
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
                a.download = `${title || 'note'}.md`; a.click(); URL.revokeObjectURL(a.href);
              }} className="text-[10px] text-slate-400 hover:text-slate-600 px-1" title="MD 다운로드">↓MD</button>
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
            <div className="flex-1 flex overflow-hidden relative">
              {/* Autocomplete dropdown — anchored above textarea bottom */}
              {acMode && (
                <div className="absolute bottom-2 left-4 z-20 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden text-xs"
                  style={{ width: 280, maxHeight: 240 }}
                  onMouseDown={e => e.preventDefault()}>
                  <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-400 bg-slate-50 border-b border-slate-100">
                    {acMode === 'slash' ? `슬래시 명령 ${acQuery && `· /${acQuery}`}` : `노트 링크 ${acQuery && `· ${acQuery}`}`}
                  </div>
                  <div className="overflow-y-auto" style={{ maxHeight: 200 }}>
                    {acMode === 'slash' ? (
                      slashFiltered.length === 0 ? (
                        <div className="px-3 py-2 text-slate-400">일치하는 명령 없음</div>
                      ) : slashFiltered.map((c, i) => (
                        <button key={c.id}
                          onMouseEnter={() => setAcIndex(i)}
                          onClick={() => acceptSlash(c.id)}
                          className={`w-full text-left px-3 py-1.5 flex items-center justify-between gap-2 ${i === acIndex ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-slate-50'}`}>
                          <span>{c.label}</span>
                          <code className="text-[10px] text-slate-400">{c.hint}</code>
                        </button>
                      ))
                    ) : (
                      <>
                        {linkFiltered.length === 0 && acQuery && (
                          <button onClick={() => acceptLink(acQuery)}
                            className="w-full text-left px-3 py-1.5 text-indigo-600 hover:bg-indigo-50 italic">
                            새 노트로 링크: "{acQuery}"
                          </button>
                        )}
                        {linkFiltered.map((n, i) => (
                          <button key={n.slug}
                            onMouseEnter={() => setAcIndex(i)}
                            onClick={() => acceptLink(n.title)}
                            className={`w-full text-left px-3 py-1.5 ${i === acIndex ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-slate-50'}`}>
                            <div className="font-medium truncate">{n.title}</div>
                            <div className="text-[10px] text-slate-400">{n.slug}</div>
                          </button>
                        ))}
                        {linkFiltered.length === 0 && !acQuery && (
                          <div className="px-3 py-2 text-slate-400">노트 없음</div>
                        )}
                      </>
                    )}
                  </div>
                  <div className="px-3 py-1 text-[10px] text-slate-400 bg-slate-50 border-t border-slate-100">↑↓ 선택 · Enter 적용 · Esc 취소</div>
                </div>
              )}
              {viewMode !== 'preview' && (
                <textarea ref={textareaRef} value={content}
                  onChange={e => { setContent(e.target.value); scheduleSave(); requestAnimationFrame(detectAcTriggers); }}
                  onKeyUp={() => { if (acMode) detectAcTriggers(); }}
                  onClick={() => { if (acMode) detectAcTriggers(); }}
                  onBlur={() => setTimeout(closeAc, 150)}
                  onKeyDown={e => {
                    // Autocomplete navigation has highest priority
                    if (acMode) {
                      const list = acMode === 'slash' ? slashFiltered : linkFiltered;
                      if (e.key === 'Escape') { e.preventDefault(); closeAc(); return; }
                      if (e.key === 'ArrowDown') { e.preventDefault(); setAcIndex(i => list.length ? (i + 1) % list.length : 0); return; }
                      if (e.key === 'ArrowUp') { e.preventDefault(); setAcIndex(i => list.length ? (i - 1 + list.length) % list.length : 0); return; }
                      if (e.key === 'Enter' || e.key === 'Tab') {
                        if (list.length) {
                          e.preventDefault();
                          if (acMode === 'slash') acceptSlash((list[acIndex] as any).id);
                          else acceptLink((list[acIndex] as any).title);
                          return;
                        }
                      }
                    }

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
                      if (e.key === 'p') { e.preventDefault(); setViewMode(v => v === 'preview' ? 'split' : 'preview'); return; }
                    }

                    // Tab: indent list / Shift+Tab: outdent list
                    if (e.key === 'Tab') {
                      e.preventDefault();
                      const listM = currentLine.match(/^(\s*)([-*+]|\d+\.)\s/);
                      if (e.shiftKey) {
                        // Outdent: remove leading 2 spaces, switch * → -
                        if (currentLine.startsWith('  ')) {
                          let newLine = currentLine.slice(2);
                          // If outdenting from *, switch to -
                          if (newLine.match(/^\s*\*\s/)) newLine = newLine.replace(/^(\s*)\*/, '$1-');
                          const nc = val.slice(0, lineStart) + newLine + val.slice(lineStart + currentLine.length);
                          setContent(nc); scheduleSave();
                          requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = Math.max(lineStart, start - 2); });
                        }
                      } else if (listM) {
                        // Indent list item: add 2 spaces, switch - → * for sub-level
                        let newLine = '  ' + currentLine;
                        // If it was top-level -, switch to * for visual distinction
                        if (listM[1] === '' && listM[2] === '-') {
                          newLine = '  * ' + currentLine.slice(listM[0].length);
                        }
                        const nc = val.slice(0, lineStart) + newLine + val.slice(lineStart + currentLine.length);
                        setContent(nc); scheduleSave();
                        requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = start + 2; });
                      } else {
                        // Plain text: just insert 2 spaces
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
                  {content ? <NoteMarkdownViewer content={content} existingSlugs={existingSlugs} onNavigate={handleNavigate} onTagClick={tag => setSelectedTags(prev => { const n = new Set(prev); n.add(tag); return n; })} /> : <span className="text-slate-400">미리보기</span>}
                </div>
              )}
            </div>
            {aiResult && (
              <div className="border-t border-indigo-100 px-3 py-2 bg-indigo-50/40 max-h-44 overflow-y-auto">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-[10px] font-semibold text-indigo-700">
                    ✨ AI · {aiResult.type === 'summary' ? '요약' : aiResult.type === 'related' ? '관련 노트' : '태그 추천'}
                    {aiResult.loading && <span className="ml-1 text-slate-400">생성중…</span>}
                  </div>
                  <button onClick={() => setAiResult(null)} className="text-slate-400 hover:text-slate-600 text-xs">✕</button>
                </div>
                {aiResult.error && <div className="text-xs text-red-600">{aiResult.error}</div>}
                {!aiResult.loading && aiResult.type === 'summary' && aiResult.text && (
                  <div className="text-xs text-slate-700 whitespace-pre-wrap leading-relaxed">{aiResult.text}</div>
                )}
                {!aiResult.loading && aiResult.type === 'related' && (
                  <div className="space-y-1">
                    {(aiResult.items || []).length === 0 && <div className="text-xs text-slate-400">관련 노트 없음</div>}
                    {(aiResult.items || []).map(it => (
                      <button key={it.slug} onClick={() => selectNote(it.slug)}
                        className="block w-full text-left px-2 py-1 rounded hover:bg-white">
                        <span className="font-medium text-indigo-600 text-xs">{it.title}</span>
                        {it.reason && <span className="text-[10px] text-slate-500 ml-2">{it.reason}</span>}
                      </button>
                    ))}
                  </div>
                )}
                {!aiResult.loading && aiResult.type === 'tags' && (
                  <div className="flex flex-wrap gap-1">
                    {(aiResult.tags || []).length === 0 && <div className="text-xs text-slate-400">추천 태그 없음</div>}
                    {(aiResult.tags || []).map(t => (
                      <span key={t} className="px-1.5 py-0.5 text-[10px] rounded-full bg-white border border-indigo-200 text-indigo-700">#{t}</span>
                    ))}
                    {aiResult.applied && <span className="text-[10px] text-green-600 ml-2">노트에 적용됨</span>}
                  </div>
                )}
              </div>
            )}
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
            <div className="flex gap-1 relative">
              <button onClick={handleCreate}
                className="flex-1 px-2 py-1.5 text-xs bg-indigo-500 text-white rounded-l-lg hover:bg-indigo-600">+ 새 노트</button>
              <button onClick={() => setNewNoteMenuOpen(v => !v)}
                title="템플릿으로 만들기"
                className="px-2 py-1.5 text-xs bg-indigo-500 text-white rounded-r-lg hover:bg-indigo-600 border-l border-indigo-400">▾</button>
              <button onClick={() => setShowList(false)}
                className="px-1.5 py-1.5 text-slate-400 hover:text-slate-600 text-xs">✕</button>
              {newNoteMenuOpen && (
                <div className="absolute top-full left-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-50 min-w-[180px] py-1"
                  onMouseLeave={() => setNewNoteMenuOpen(false)}>
                  <button onClick={() => { handleCreate(); setNewNoteMenuOpen(false); }}
                    className="block w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50">📝 빈 노트</button>
                  {templates.length > 0 && <div className="border-t border-slate-100 my-1" />}
                  {templates.map(t => (
                    <button key={`${t.scope}-${t.name}`}
                      onClick={() => handleCreateFromTemplate(t.name)}
                      className="block w-full text-left px-3 py-1.5 text-xs hover:bg-indigo-50 truncate">
                      <span className="text-slate-400 mr-1">{t.scope === 'global' ? '📋' : '⭐'}</span>
                      {t.name}
                    </button>
                  ))}
                  <div className="border-t border-slate-100 my-1" />
                  <button onClick={() => { setTplMgrOpen(true); setNewNoteMenuOpen(false); }}
                    className="block w-full text-left px-3 py-1.5 text-[11px] text-slate-500 hover:bg-slate-50">⚙ 템플릿 관리</button>
                </div>
              )}
            </div>
            <button onClick={() => setShowGraph(!showGraph)}
              className={`w-full px-2 py-1 text-xs rounded-lg border flex items-center justify-center gap-1 ${showGraph ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'}`}>
              🕸 {showGraph ? '캔버스' : '캔버스 보기'}
            </button>
            <div className="flex items-center gap-1">
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="제목·본문 검색..."
                className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-400" />
              <button onClick={() => setShowAdvSearch(v => !v)} title="고급 검색"
                className={`px-1.5 py-1 text-[10px] rounded border ${showAdvSearch || dateFrom || dateTo ? 'bg-indigo-50 text-indigo-600 border-indigo-200' : 'text-slate-400 border-slate-200 hover:bg-slate-50'}`}>⚙</button>
            </div>
            {showAdvSearch && (
              <div className="space-y-1 pt-1 border-t border-slate-100">
                <div className="flex items-center gap-1">
                  <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                    className="flex-1 px-1.5 py-0.5 text-[10px] border border-slate-200 rounded focus:outline-none focus:border-indigo-400" />
                  <span className="text-[10px] text-slate-400">~</span>
                  <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                    className="flex-1 px-1.5 py-0.5 text-[10px] border border-slate-200 rounded focus:outline-none focus:border-indigo-400" />
                </div>
                {(dateFrom || dateTo) && (
                  <button onClick={() => { setDateFrom(''); setDateTo(''); }}
                    className="w-full text-[10px] text-slate-400 hover:text-slate-600 py-0.5">날짜 초기화</button>
                )}
              </div>
            )}
            {isSearchActive && (
              <div className="flex items-center justify-between text-[10px] text-slate-500">
                <span>{searchLoading ? '검색중…' : `${filteredNotes.length}건`}</span>
                <button onClick={() => { setSearch(''); setSelectedTags(new Set()); setDateFrom(''); setDateTo(''); }}
                  className="text-slate-400 hover:text-indigo-600">초기화</button>
              </div>
            )}
          </div>
          <div className="flex-1 overflow-y-auto">
            {/* 📥 인박스 (Quick Capture 모은 곳) */}
            {!isSearchActive && inboxNotes.length > 0 && (
              <div className="border-b-2 border-amber-100 bg-amber-50/40">
                <button onClick={() => setShowInbox(v => !v)}
                  className="w-full px-3 py-1.5 text-[11px] font-semibold text-amber-700 hover:bg-amber-50 flex items-center justify-between">
                  <span>📥 인박스 ({inboxNotes.length})</span>
                  <span className="text-amber-400">{showInbox ? '▾' : '▸'}</span>
                </button>
                {showInbox && inboxNotes.map(n => (
                  <div key={n.slug}
                    onClick={() => selectNote(n.slug)}
                    onContextMenu={e => { e.preventDefault(); setNoteCtx({ x: e.clientX, y: e.clientY, slug: n.slug, title: n.title }); }}
                    className={`group w-full text-left px-3 py-1.5 border-b border-amber-50 cursor-pointer flex items-start gap-1 ${
                      n.slug === activeSlug ? 'bg-amber-100/60 border-l-2 border-l-amber-500' : 'hover:bg-amber-50'
                    }`}>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-slate-700 truncate">{n.title}</div>
                      <div className="text-[10px] text-amber-600/60 mt-0.5">{new Date(n.created_at).toLocaleString('ko', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                    </div>
                    <button onClick={e => { e.stopPropagation(); openPromote(n); }}
                      title="정리해서 정식 노트로 승격"
                      className="opacity-0 group-hover:opacity-100 transition-opacity px-1.5 py-0.5 text-[10px] bg-amber-500 text-white rounded hover:bg-amber-600">📁</button>
                  </div>
                ))}
              </div>
            )}
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
                    {isSearchActive && n.snippet ? (
                      <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-2"
                        dangerouslySetInnerHTML={{ __html: sanitizeSnippet(n.snippet) }} />
                    ) : (
                      <div className="text-[10px] text-slate-400 mt-0.5">{new Date(n.updated_at).toLocaleDateString('ko')}</div>
                    )}
                  </>
                )}
              </div>
            ))}
            {filteredNotes.length === 0 && <div className="px-3 py-4 text-xs text-slate-400 text-center">{notes.length === 0 ? '노트 없음' : '결과 없음'}</div>}
          </div>
          {allTags.length > 0 && (
            <div className="border-t border-slate-200 p-2 max-h-32 overflow-y-auto">
              <div className="flex items-center justify-between mb-1">
                <div className="text-[10px] font-semibold text-slate-400">태그 (다중선택 AND)</div>
                {selectedTags.size > 0 && (
                  <button onClick={() => setSelectedTags(new Set())}
                    className="text-[10px] text-slate-400 hover:text-indigo-600">해제</button>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                {allTags.filter(t => !t.tag.includes('/')).map(t => {
                  const active = selectedTags.has(t.tag);
                  return (
                    <button key={t.tag}
                      onClick={() => setSelectedTags(prev => {
                        const next = new Set(prev);
                        if (next.has(t.tag)) next.delete(t.tag); else next.add(t.tag);
                        return next;
                      })}
                      className={`px-1.5 py-0.5 text-[10px] rounded-full ${active ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-indigo-50'}`}>
                      #{t.tag} <span className="opacity-60">{t.count}</span>
                    </button>
                  );
                })}
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

      {/* ⚡ Floating Quick Capture button (Ctrl+Shift+M) */}
      <button onClick={openQuickCapture}
        title="빠른 메모 (Ctrl+Shift+M)"
        className="fixed bottom-6 right-6 z-30 w-12 h-12 rounded-full bg-amber-500 text-white shadow-lg hover:bg-amber-600 hover:scale-105 transition-all flex items-center justify-center text-xl">
        ⚡
      </button>

      {/* Quick Capture modal */}
      {quickOpen && createPortal(
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30"
          onClick={() => setQuickOpen(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-[520px] max-w-[90vw] flex flex-col overflow-hidden"
            onClick={e => e.stopPropagation()}>
            <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-700">⚡ 빠른 메모 — 인박스</div>
              <span className="text-[10px] text-slate-400">Ctrl+Enter 저장 · Esc 닫기</span>
            </div>
            <textarea autoFocus
              value={quickText}
              onChange={e => setQuickText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Escape') { setQuickOpen(false); }
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submitQuickCapture(); }
              }}
              placeholder="떠오르는 생각을 그대로… (제목은 자동, 인박스에 저장됨)"
              className="px-5 py-4 text-[14px] leading-relaxed outline-none resize-none font-mono"
              style={{ minHeight: '180px' }} />
            <div className="px-5 py-3 border-t border-slate-200 flex justify-between items-center bg-slate-50">
              <div className="text-[11px] text-slate-500">자동 제목: Quick {new Date().toLocaleString('ko', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(/\. /g, '-').replace(/\.$/, '')}</div>
              <div className="flex gap-2">
                <button onClick={() => setQuickOpen(false)}
                  className="px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100 rounded-lg">취소</button>
                <button onClick={submitQuickCapture} disabled={quickSaving}
                  className="px-4 py-1.5 text-xs bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50">
                  {quickSaving ? '저장중…' : '인박스에 담기'}
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Promote (인박스 → 정식 노트) modal */}
      {promoteTarget && createPortal(
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30"
          onClick={() => setPromoteTarget(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-[480px] max-w-[90vw] flex flex-col overflow-hidden"
            onClick={e => e.stopPropagation()}>
            <div className="px-5 py-3 border-b border-slate-200">
              <div className="text-sm font-semibold text-slate-700">📁 인박스에서 정리</div>
              <div className="text-[11px] text-slate-400 mt-0.5 truncate">현재: {promoteTarget.title}</div>
            </div>
            <div className="px-5 py-4 space-y-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-600 mb-1">제목 (선택, 비우면 그대로)</label>
                <input value={promoteTitle} onChange={e => setPromoteTitle(e.target.value)}
                  placeholder="예: 한화비전 IR 미팅 메모"
                  className="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-400" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-slate-600 mb-1">태그</label>
                <div className="flex flex-wrap gap-1 mb-1.5">
                  {promoteTags.map(t => (
                    <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] bg-indigo-50 text-indigo-600 rounded-full">
                      #{t}
                      <button onClick={() => setPromoteTags(prev => prev.filter(x => x !== t))}
                        className="text-indigo-400 hover:text-indigo-700">×</button>
                    </span>
                  ))}
                </div>
                <input value={promoteTagInput}
                  onChange={e => setPromoteTagInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ',' || e.key === ' ') {
                      e.preventDefault();
                      const t = promoteTagInput.trim().replace(/^#/, '');
                      if (t && !promoteTags.includes(t)) setPromoteTags(prev => [...prev, t]);
                      setPromoteTagInput('');
                    }
                  }}
                  placeholder="태그 입력 후 Enter (예: 인터뷰)"
                  className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-400" />
                {allTags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {allTags.filter(t => !t.tag.includes('/') && !promoteTags.includes(t.tag)).slice(0, 12).map(t => (
                      <button key={t.tag} onClick={() => setPromoteTags(prev => [...prev, t.tag])}
                        className="px-1.5 py-0.5 text-[10px] bg-slate-100 text-slate-600 rounded-full hover:bg-indigo-50 hover:text-indigo-600">
                        + #{t.tag}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="px-5 py-3 border-t border-slate-200 flex justify-end gap-2 bg-slate-50">
              <button onClick={() => setPromoteTarget(null)}
                className="px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100 rounded-lg">취소</button>
              <button onClick={submitPromote}
                className="px-4 py-1.5 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">정리 완료</button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Template manager modal */}
      {tplMgrOpen && createPortal(
        <TemplateManager
          projectName={projectName}
          templates={templates}
          onClose={() => setTplMgrOpen(false)}
          onChanged={loadTemplates}
        />,
        document.body
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
