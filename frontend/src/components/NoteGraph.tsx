/**
 * NoteGraph — Dot-based canvas with popup note editor.
 * All notes shown as colored dots. Double-click to open popup editor.
 * Bezier edges between connected dots.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';

interface CanvasNode {
  slug: string;
  title: string;
  content: string;
  x: number; y: number;
  color: string;
  tags: string[];
}

interface CanvasEdge { source: string; target: string }

interface NoteGraphProps {
  projectName: string;
  activeSlug?: string | null;
  onNavigate: (slug: string) => void;
  refreshKey?: number;
  onNoteCreated?: () => void;
}

const DOT_R = 6;
const PORT_R = 2;
const PALETTE = [
  '#6366f1', '#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#64748b',
];

export default function NoteGraph({ projectName, activeSlug, onNavigate, refreshKey, onNoteCreated }: NoteGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<CanvasNode[]>([]);
  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const [edges, setEdges] = useState<CanvasEdge[]>([]);
  const [loaded, setLoaded] = useState(false);

  const panRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);
  const [, setTick] = useState(0);
  const rerender = () => setTick(v => v + 1);

  // Popup editor (inline edit)
  const [popup, setPopup] = useState<{ slug: string; title: string; content: string; dirty?: boolean; saving?: boolean } | null>(null);
  const popupSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingPatchRef = useRef<{ slug: string; patch: { title?: string; content?: string } } | null>(null);

  // Drag / link
  const [linkDrag, setLinkDrag] = useState<{ sourceSlug: string; mx: number; my: number } | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; node: CanvasNode } | null>(null);
  const [edgeCtx, setEdgeCtx] = useState<{ x: number; y: number; edge: CanvasEdge } | null>(null);
  const [bgCtx, setBgCtx] = useState<{ x: number; y: number; wx: number; wy: number } | null>(null);

  // ── Filter / search / auto-color ──
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTags, setActiveTags] = useState<Set<string>>(new Set());
  const [autoColor, setAutoColor] = useState(false);

  // Tag → color map (deterministic by tag name hash, stable across renders)
  const tagColorMap = useMemo(() => {
    const all = new Set<string>();
    nodes.forEach(n => n.tags.forEach(t => all.add(t.split('/')[0])));
    const sorted = Array.from(all).sort();
    const m = new Map<string, string>();
    sorted.forEach((t, i) => m.set(t, PALETTE[i % PALETTE.length]));
    return m;
  }, [nodes]);

  const colorOf = useCallback((n: CanvasNode) => {
    if (!autoColor) return n.color;
    const root = n.tags[0]?.split('/')[0];
    return (root && tagColorMap.get(root)) || n.color;
  }, [autoColor, tagColorMap]);

  // All tags for filter chips (with counts)
  const tagList = useMemo(() => {
    const counts = new Map<string, number>();
    nodes.forEach(n => n.tags.forEach(t => counts.set(t, (counts.get(t) || 0) + 1)));
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [nodes]);

  // Search matches: direct title/content hit + all downstream nodes reachable via outgoing edges
  const searchMatchSet = useMemo<Set<string> | null>(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return null;
    const direct = new Set<string>();
    nodes.forEach(n => {
      if (n.title.toLowerCase().includes(q) || (n.content || '').toLowerCase().includes(q)) {
        direct.add(n.slug);
      }
    });
    const adj = new Map<string, string[]>();
    edges.forEach(e => {
      const arr = adj.get(e.source);
      if (arr) arr.push(e.target); else adj.set(e.source, [e.target]);
    });
    const result = new Set(direct);
    const queue = Array.from(direct);
    while (queue.length) {
      const cur = queue.shift()!;
      const next = adj.get(cur);
      if (!next) continue;
      for (const t of next) {
        if (!result.has(t)) { result.add(t); queue.push(t); }
      }
    }
    return result;
  }, [nodes, edges, searchQuery]);

  const matchesNode = useCallback((n: CanvasNode) => {
    if (activeTags.size > 0) {
      // hierarchical match: filter "투자" matches "투자/PEF"
      const hit = Array.from(activeTags).some(at =>
        n.tags.some(t => t === at || t.startsWith(at + '/'))
      );
      if (!hit) return false;
    }
    if (searchMatchSet && !searchMatchSet.has(n.slug)) return false;
    return true;
  }, [activeTags, searchMatchSet]);

  const isFiltering = activeTags.size > 0 || !!searchQuery.trim();

  // ── Persist layout to server ──
  const saveLayout = useCallback(() => {
    const positions: Record<string, { x: number; y: number; color: string }> = {};
    nodesRef.current.forEach(n => { positions[n.slug] = { x: n.x, y: n.y, color: n.color }; });
    api.saveCanvasPositions(projectName, positions).catch(() => {});
  }, [projectName]);

  // Auto-save layout on node changes (debounced)
  const layoutSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleLayoutSave = useCallback(() => {
    if (layoutSaveTimer.current) clearTimeout(layoutSaveTimer.current);
    layoutSaveTimer.current = setTimeout(saveLayout, 500);
  }, [saveLayout]);

  // ── Port positions in screen space ──
  const getOutPort = (n: CanvasNode) => ({ x: n.x * scaleRef.current + panRef.current.x + DOT_R * scaleRef.current, y: n.y * scaleRef.current + panRef.current.y });
  const getInPort = (n: CanvasNode) => ({ x: n.x * scaleRef.current + panRef.current.x - DOT_R * scaleRef.current, y: n.y * scaleRef.current + panRef.current.y });

  const bezierPath = (sx: number, sy: number, ex: number, ey: number) => {
    const dx = ex - sx;
    const cp = Math.max(50, Math.abs(dx) * 0.5);
    return `M${sx},${sy} C${sx + cp},${sy} ${ex - cp},${ey} ${ex},${ey}`;
  };

  // ── Load ──
  const loadGraph = useCallback(async () => {
    try {
      const data = await api.getNoteGraph(projectName);
      const prevMap = new Map(nodesRef.current.map(n => [n.slug, n]));
      const cols = Math.max(4, Math.ceil(Math.sqrt(data.nodes.length)));
      // Backend now ships content in graph payload — no per-node round-trip needed.
      const noteNodes: CanvasNode[] = data.nodes.map((n: any, i: number) => {
        const prev = prevMap.get(n.slug);
        return {
          slug: n.slug, title: n.title,
          content: typeof n.content === 'string' ? n.content : '',
          x: prev?.x ?? n.canvas_x ?? (i % cols) * 80 + 60,
          y: prev?.y ?? n.canvas_y ?? Math.floor(i / cols) * 80 + 60,
          color: prev?.color ?? n.canvas_color ?? PALETTE[i % PALETTE.length],
          tags: Array.isArray(n.tags) ? n.tags : [],
        };
      });
      nodesRef.current = noteNodes;
      setNodes([...noteNodes]); setEdges([...data.edges]); setLoaded(true);
    } catch {}
  }, [projectName]);

  useEffect(() => { loadGraph(); }, [loadGraph, refreshKey]);

  // Close menus
  useEffect(() => {
    if (!ctxMenu && !edgeCtx && !bgCtx) return;
    const close = () => { setCtxMenu(null); setEdgeCtx(null); setBgCtx(null); };
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [ctxMenu, edgeCtx, bgCtx]);

  // ── Debounced popup save (merges title+content patches; flush actually persists) ──
  const performPopupSave = useCallback(async () => {
    const pending = pendingPatchRef.current;
    if (!pending) return;
    pendingPatchRef.current = null;
    const { slug, patch } = pending;
    setPopup(p => p && p.slug === slug ? { ...p, saving: true } : p);
    try {
      await api.updateNote(projectName, slug, patch);
      const node = nodesRef.current.find(n => n.slug === slug);
      if (node) {
        if (patch.title !== undefined) node.title = patch.title;
        if (patch.content !== undefined) node.content = patch.content;
        setNodes([...nodesRef.current]);
      }
      setPopup(p => p && p.slug === slug ? { ...p, saving: false, dirty: false } : p);
    } catch {
      setPopup(p => p && p.slug === slug ? { ...p, saving: false } : p);
    }
  }, [projectName]);

  const schedulePopupSave = useCallback((slug: string, patch: { title?: string; content?: string }) => {
    if (popupSaveTimer.current) clearTimeout(popupSaveTimer.current);
    // Merge with any pending patch for the same note so we never drop a field
    const prev = pendingPatchRef.current;
    pendingPatchRef.current = (prev && prev.slug === slug)
      ? { slug, patch: { ...prev.patch, ...patch } }
      : { slug, patch };
    setPopup(p => p && p.slug === slug ? { ...p, dirty: true } : p);
    popupSaveTimer.current = setTimeout(() => { performPopupSave(); }, 600);
  }, [performPopupSave]);

  const flushPopupSave = useCallback(async () => {
    if (popupSaveTimer.current) {
      clearTimeout(popupSaveTimer.current);
      popupSaveTimer.current = null;
    }
    await performPopupSave();
  }, [performPopupSave]);

  // ── Delete node ──
  const deleteNode = async (node: CanvasNode) => {
    if (!window.confirm(`"${node.title}" 노트를 삭제하시겠습니까?\n연결된 백링크와 태그도 함께 제거됩니다.`)) return;
    try {
      await api.deleteNote(projectName, node.slug);
      nodesRef.current = nodesRef.current.filter(n => n.slug !== node.slug);
      setNodes([...nodesRef.current]);
      setEdges(prev => prev.filter(e => e.source !== node.slug && e.target !== node.slug));
      if (popup?.slug === node.slug) setPopup(null);
      onNoteCreated?.();
      loadGraph();
    } catch {}
  };

  // ── Delete edge ──
  const deleteEdge = async (edge: CanvasEdge) => {
    try {
      const srcNote = await api.getNote(projectName, edge.source);
      const targetNode = nodesRef.current.find(n => n.slug === edge.target);
      if (!srcNote || !targetNode) return;
      let c = srcNote.content || '';
      c = c.replace(new RegExp(`\\n*\\[\\[${targetNode.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\]\\]`, 'g'), '');
      c = c.replace(new RegExp(`\\n*\\[\\[${edge.target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\]\\]`, 'g'), '');
      await api.updateNote(projectName, edge.source, { content: c.trim() });
      loadGraph();
    } catch {}
  };

  // ── Dot drag ──
  const handleDotDrag = (e: React.MouseEvent, slug: string) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    const node = nodesRef.current.find(n => n.slug === slug);
    if (!node) return;
    const startX = e.clientX, startY = e.clientY, nx = node.x, ny = node.y;
    let moved = false;
    const onMove = (ev: MouseEvent) => {
      if (Math.abs(ev.clientX - startX) > 3 || Math.abs(ev.clientY - startY) > 3) moved = true;
      if (moved) {
        node.x = nx + (ev.clientX - startX) / scaleRef.current;
        node.y = ny + (ev.clientY - startY) / scaleRef.current;
        setNodes([...nodesRef.current]);
      }
    };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); if (moved) scheduleLayoutSave(); };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  };

  // ── Port drag (connection) ──
  const handlePortDrag = (e: React.MouseEvent, slug: string) => {
    e.stopPropagation(); e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setLinkDrag({ sourceSlug: slug, mx: e.clientX - rect.left, my: e.clientY - rect.top });
    const onMove = (ev: MouseEvent) => {
      const r = containerRef.current?.getBoundingClientRect();
      if (!r) return;
      setLinkDrag(prev => prev ? { ...prev, mx: ev.clientX - r.left, my: ev.clientY - r.top } : null);
    };
    const onUp = async (ev: MouseEvent) => {
      document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp);
      const r = containerRef.current?.getBoundingClientRect();
      if (!r) { setLinkDrag(null); return; }
      const mx = ev.clientX - r.left, my = ev.clientY - r.top;
      // Find target by port proximity
      let target: CanvasNode | undefined;
      for (const n of nodesRef.current) {
        if (n.slug === slug) continue;
        const inp = getInPort(n);
        if (Math.hypot(mx - inp.x, my - inp.y) < 20) { target = n; break; }
      }
      if (!target) {
        const s = scaleRef.current, ppx = panRef.current.x, ppy = panRef.current.y;
        const wx = (mx - ppx) / s, wy = (my - ppy) / s;
        target = nodesRef.current.find(n => n.slug !== slug && Math.hypot(wx - n.x, wy - n.y) < DOT_R + 15);
      }
      if (target) {
        try {
          const srcNote = await api.getNote(projectName, slug);
          if (srcNote) {
            const link = `[[${target.title}]]`;
            const linkAlt = `[[${target.slug}]]`;
            if (!(srcNote.content || '').includes(link) && !(srcNote.content || '').includes(linkAlt)) {
              await api.updateNote(projectName, slug, { content: (srcNote.content || '') + `\n\n${link}` });
              loadGraph();
            }
          }
        } catch {}
      }
      setLinkDrag(null);
    };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  };

  // ── Pan ──
  const handleBgDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    const startX = e.clientX, startY = e.clientY, px0 = panRef.current.x, py0 = panRef.current.y;
    const onMove = (ev: MouseEvent) => { panRef.current.x = px0 + ev.clientX - startX; panRef.current.y = py0 + ev.clientY - startY; rerender(); };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  };

  // ── Zoom (non-passive wheel listener to allow preventDefault) ──
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const oldS = scaleRef.current, newS = Math.min(4, Math.max(0.2, oldS * (e.deltaY > 0 ? 0.92 : 1.08)));
      panRef.current.x = mx - (mx - panRef.current.x) * (newS / oldS);
      panRef.current.y = my - (my - panRef.current.y) * (newS / oldS);
      scaleRef.current = newS; rerender();
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // (popup is read-only viewer, no save needed)

  const s = scaleRef.current, px = panRef.current.x, py = panRef.current.y;
  const nodeMap = new Map(nodes.map(n => [n.slug, n]));

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden bg-[#fafafa]"
      onMouseDown={handleBgDown}
      onContextMenu={e => {
        e.preventDefault();
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        const wx = (e.clientX - rect.left - px) / s, wy = (e.clientY - rect.top - py) / s;
        setBgCtx({ x: e.clientX, y: e.clientY, wx, wy });
      }}>

      {/* Edges */}
      {edges.map((e, i) => {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) return null;
        const dim = isFiltering && (!matchesNode(a) || !matchesNode(b));
        const out = getOutPort(a), inp = getInPort(b);
        const pad = 30;
        const minX = Math.min(out.x, inp.x) - pad, minY = Math.min(out.y, inp.y) - pad;
        const w = Math.abs(out.x - inp.x) + pad * 2, h = Math.abs(out.y - inp.y) + pad * 2;
        const lsx = out.x - minX, lsy = out.y - minY, lex = inp.x - minX, ley = inp.y - minY;
        const path = bezierPath(lsx, lsy, lex, ley);
        return (
          <svg key={`e-${i}`} style={{ position: 'absolute', left: minX, top: minY, width: w, height: h, pointerEvents: 'none', zIndex: 0, overflow: 'visible', opacity: dim ? 0.1 : 1 }}>
            <path d={path} fill="none" stroke="transparent" strokeWidth="14" style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
              onContextMenu={ev => { ev.preventDefault(); ev.stopPropagation(); setEdgeCtx({ x: ev.clientX, y: ev.clientY, edge: e }); }} />
            <path d={path} fill="none" stroke="#6366f1" strokeWidth="2" strokeOpacity="0.45" style={{ pointerEvents: 'none' }} />
            <circle cx={lex} cy={ley} r="2.5" fill="#22c55e" style={{ pointerEvents: 'none' }} />
          </svg>
        );
      })}

      {/* Link drag */}
      {linkDrag && (() => {
        const src = nodeMap.get(linkDrag.sourceSlug);
        if (!src) return null;
        const out = getOutPort(src);
        const pad = 30;
        const minX = Math.min(out.x, linkDrag.mx) - pad, minY = Math.min(out.y, linkDrag.my) - pad;
        const w = Math.abs(out.x - linkDrag.mx) + pad * 2, h = Math.abs(out.y - linkDrag.my) + pad * 2;
        const lsx = out.x - minX, lsy = out.y - minY, lex = linkDrag.mx - minX, ley = linkDrag.my - minY;
        return (
          <svg style={{ position: 'absolute', left: minX, top: minY, width: w, height: h, pointerEvents: 'none', zIndex: 5, overflow: 'visible' }}>
            <path d={bezierPath(lsx, lsy, lex, ley)} fill="none" stroke="#22c55e" strokeWidth="2.5" strokeDasharray="6 4" />
          </svg>
        );
      })()}

      {/* Dots */}
      {loaded && nodes.map(node => {
        const cx = node.x * s + px, cy = node.y * s + py;
        const r = DOT_R * s;
        const isActive = node.slug === activeSlug || node.slug === popup?.slug;
        const dim = isFiltering && !matchesNode(node);
        const fill = colorOf(node);
        return (
          <div key={node.slug} style={{ opacity: dim ? 0.18 : 1, transition: 'opacity 0.15s' }}>
            {/* Title above */}
            <div className="absolute pointer-events-none text-center" style={{ left: cx - 50, top: cy - r - 32, width: 100, fontSize: Math.max(9, 11 * s) }}>
              <span className="text-slate-600 font-medium whitespace-nowrap">{node.title}</span>
            </div>
            {/* Dot */}
            <div className="absolute rounded-full cursor-grab border-2 transition-shadow"
              style={{
                left: cx - r, top: cy - r, width: r * 2, height: r * 2,
                backgroundColor: fill,
                borderColor: isActive ? '#4338ca' : 'rgba(255,255,255,0.8)',
                boxShadow: isActive ? '0 0 0 3px rgba(99,102,241,0.3)' : '0 1px 3px rgba(0,0,0,0.15)',
                zIndex: 3,
              }}
              onMouseDown={e => handleDotDrag(e, node.slug)}
              onDoubleClick={e => { e.stopPropagation(); setPopup({ slug: node.slug, title: node.title, content: node.content }); }}
              onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setCtxMenu({ x: e.clientX, y: e.clientY, node }); }}
            />
            {/* Output port (right) */}
            <div className="absolute cursor-crosshair" title="드래그하여 연결"
              style={{ left: cx + r - 2, top: cy - 6, width: 12, height: 12, zIndex: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              onMouseDown={e => handlePortDrag(e, node.slug)}>
              <div className="rounded-full" style={{ width: PORT_R * 2, height: PORT_R * 2, backgroundColor: '#6366f1' }} />
            </div>
            {/* Input port (left) */}
            <div className="absolute cursor-crosshair" title="연결 입력"
              style={{ left: cx - r - 10, top: cy - 6, width: 12, height: 12, zIndex: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              onMouseDown={e => handlePortDrag(e, node.slug)}>
              <div className="rounded-full" style={{ width: PORT_R * 2, height: PORT_R * 2, backgroundColor: '#22c55e', opacity: 0.7 }} />
            </div>
          </div>
        );
      })}

      {/* HUD */}
      {!loaded && <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm z-10">로딩 중...</div>}

      {/* Top toolbar: search + tag filter + auto color */}
      <div className="absolute top-2 left-2 right-2 flex items-start gap-2 z-10 pointer-events-none">
        <div className="flex flex-col gap-1.5 pointer-events-auto" style={{ minWidth: 240, maxWidth: 'calc(100% - 200px)' }}>
          {/* Search */}
          <div className="flex items-center gap-1 bg-white/90 backdrop-blur border border-slate-200 rounded-lg px-2 h-7 shadow-sm">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-slate-400">
              <circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>
            </svg>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="제목·내용 검색"
              className="flex-1 text-xs bg-transparent outline-none placeholder:text-slate-400"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="text-slate-400 hover:text-slate-600 text-xs leading-none">✕</button>
            )}
            <label className="flex items-center gap-1 text-[10px] text-slate-500 cursor-pointer pl-1.5 ml-1 border-l border-slate-200">
              <input type="checkbox" checked={autoColor} onChange={e => setAutoColor(e.target.checked)} className="w-3 h-3" />
              태그색
            </label>
          </div>
          {/* Tag chips */}
          {tagList.length > 0 && (
            <div className="flex flex-wrap gap-1 bg-white/80 backdrop-blur border border-slate-200 rounded-lg px-1.5 py-1 shadow-sm max-h-[72px] overflow-y-auto">
              {tagList.map(([tag, count]) => {
                const active = activeTags.has(tag);
                const root = tag.split('/')[0];
                const dot = autoColor ? tagColorMap.get(root) : null;
                return (
                  <button key={tag}
                    onClick={() => setActiveTags(prev => {
                      const next = new Set(prev);
                      if (next.has(tag)) next.delete(tag); else next.add(tag);
                      return next;
                    })}
                    className={`inline-flex items-center gap-1 text-[10px] px-1.5 h-5 rounded-full border transition ${
                      active ? 'bg-indigo-500 text-white border-indigo-500' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}>
                    {dot && <span className="w-2 h-2 rounded-full" style={{ backgroundColor: dot }} />}
                    <span>#{tag}</span>
                    <span className={active ? 'text-indigo-100' : 'text-slate-400'}>{count}</span>
                  </button>
                );
              })}
              {activeTags.size > 0 && (
                <button onClick={() => setActiveTags(new Set())}
                  className="text-[10px] px-1.5 h-5 rounded-full text-slate-500 hover:text-slate-700">전체해제</button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom-left help */}
      <div className="absolute bottom-2 left-2 text-[10px] text-slate-400 bg-white/80 backdrop-blur px-2 py-1 rounded-lg z-10">
        더블클릭: 빠른 편집 · 드래그: 이동 · 포트 드래그: 연결 · 우클릭: 메뉴
        {edges.length > 0 && <span className="ml-1 text-indigo-500">· {edges.length}개 연결</span>}
        {isFiltering && <span className="ml-1 text-amber-600">· 필터 적용중</span>}
      </div>
      {linkDrag && <div className="absolute top-2 right-2 text-xs text-green-600 bg-green-50 border border-green-200 px-3 py-1.5 rounded-lg animate-pulse z-10">🔗 노드에 놓으면 연결</div>}
      <div className="absolute bottom-2 right-2 flex gap-1 z-10">
        <button onClick={() => { scaleRef.current = 1; panRef.current = { x: 0, y: 0 }; rerender(); }}
          className="px-2 h-7 bg-white border border-slate-200 rounded-lg text-[10px] text-slate-500 hover:bg-slate-50">리셋</button>
        <button onClick={() => { scaleRef.current = Math.min(4, scaleRef.current * 1.2); rerender(); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 font-bold">+</button>
        <button onClick={() => { scaleRef.current = Math.max(0.2, scaleRef.current * 0.8); rerender(); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 font-bold">-</button>
      </div>

      {/* ── Note popup editor (inline edit) ── */}
      {popup && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => { flushPopupSave(); setPopup(null); }}
          onMouseDown={e => e.stopPropagation()}
          onWheel={e => e.stopPropagation()}>
          <div className="bg-white rounded-2xl shadow-2xl w-[640px] max-w-[90vw] max-h-[80vh] flex flex-col overflow-hidden"
            onClick={e => e.stopPropagation()}
            onMouseDown={e => e.stopPropagation()}
            onWheel={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 gap-3">
              <input
                value={popup.title}
                onChange={e => { const v = e.target.value; setPopup(p => p ? { ...p, title: v } : p); schedulePopupSave(popup.slug, { title: v }); }}
                placeholder="제목"
                className="flex-1 font-bold text-slate-800 text-lg bg-transparent outline-none focus:bg-slate-50 rounded px-2 py-1 -mx-2"
              />
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] text-slate-400 min-w-[40px] text-right">
                  {popup.saving ? '저장중…' : popup.dirty ? '편집중' : '저장됨'}
                </span>
                <button onClick={async () => {
                  try { await navigator.clipboard.writeText(popup.content); } catch {}
                }}
                  className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">복사</button>
                <button onClick={async () => { await flushPopupSave(); const slug = popup.slug; setPopup(null); onNavigate(slug); }}
                  className="px-3 py-1 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">노트로 열기</button>
                <button onClick={() => { flushPopupSave(); setPopup(null); }}
                  className="text-slate-400 hover:text-slate-600 text-lg">✕</button>
              </div>
            </div>
            {/* Inline editable content */}
            <textarea
              value={popup.content}
              onChange={e => { const v = e.target.value; setPopup(p => p ? { ...p, content: v } : p); schedulePopupSave(popup.slug, { content: v }); }}
              placeholder="내용을 입력하세요. [[다른노트]] 로 링크할 수 있습니다."
              className="flex-1 px-6 py-4 text-[15px] leading-relaxed outline-none resize-none font-mono"
              style={{ minHeight: '320px' }}
            />
          </div>
        </div>,
        document.body
      )}

      {/* Dot context menu */}
      {ctxMenu && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[140px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }} onClick={e => e.stopPropagation()}>
          <div className="px-3 py-1.5 text-xs font-semibold text-slate-700 border-b border-slate-100 mb-1 truncate">{ctxMenu.node.title}</div>
          <div className="px-3 py-1.5">
            <div className="text-[10px] text-slate-400 mb-1">색상</div>
            <div className="flex flex-wrap gap-1">
              {PALETTE.map(c => (
                <button key={c} onClick={() => { const nd = nodesRef.current.find(n => n.slug === ctxMenu.node.slug); if (nd) nd.color = c; setNodes([...nodesRef.current]); scheduleLayoutSave(); setCtxMenu(null); }}
                  className="w-5 h-5 rounded-full border border-white hover:scale-125 transition-transform shadow-sm" style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { setPopup({ slug: ctxMenu.node.slug, title: ctxMenu.node.title, content: ctxMenu.node.content }); setCtxMenu(null); }}>📝 빠른 편집</button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { onNavigate(ctxMenu.node.slug); setCtxMenu(null); }}>📄 노트로 열기</button>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-red-50 text-red-600"
            onClick={() => { const node = ctxMenu.node; setCtxMenu(null); deleteNode(node); }}>🗑 노드 삭제</button>
        </div>,
        document.body
      )}

      {/* Background context menu */}
      {bgCtx && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[140px]"
          style={{ left: bgCtx.x, top: bgCtx.y }} onClick={e => e.stopPropagation()}>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={async () => {
              const newTitle = prompt('노트 제목:', '새 노트');
              if (!newTitle) { setBgCtx(null); return; }
              const note = await api.createNote(projectName, { title: newTitle });
              if (note?.slug) {
                nodesRef.current.push({ slug: note.slug, title: note.title, content: '', x: bgCtx.wx, y: bgCtx.wy, color: PALETTE[nodesRef.current.length % PALETTE.length], tags: [] });
                setNodes([...nodesRef.current]);
                loadGraph();
                onNoteCreated?.();
              }
              setBgCtx(null);
            }}>📝 새 노트 만들기</button>
        </div>,
        document.body
      )}

      {/* Edge context menu */}
      {edgeCtx && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[140px]"
          style={{ left: edgeCtx.x, top: edgeCtx.y }} onClick={e => e.stopPropagation()}>
          <div className="px-3 py-1 text-[10px] text-slate-400 border-b border-slate-100 mb-1">
            {nodeMap.get(edgeCtx.edge.source)?.title} → {nodeMap.get(edgeCtx.edge.target)?.title}
          </div>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-red-50 text-red-600"
            onClick={() => { deleteEdge(edgeCtx.edge); setEdgeCtx(null); }}>🗑 연결 삭제</button>
        </div>,
        document.body
      )}
    </div>
  );
}
