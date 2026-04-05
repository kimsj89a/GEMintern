/**
 * NoteGraph — Dot-based canvas with popup note editor.
 * All notes shown as colored dots. Double-click to open popup editor.
 * Bezier edges between connected dots.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import NoteMarkdownViewer from './NoteMarkdownViewer';

interface CanvasNode {
  slug: string;
  title: string;
  content: string;
  x: number; y: number;
  color: string;
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

  // Popup viewer (read-only preview)
  const [popup, setPopup] = useState<{ slug: string; title: string; content: string } | null>(null);

  // Drag / link
  const [linkDrag, setLinkDrag] = useState<{ sourceSlug: string; mx: number; my: number } | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; node: CanvasNode } | null>(null);
  const [edgeCtx, setEdgeCtx] = useState<{ x: number; y: number; edge: CanvasEdge } | null>(null);
  const [bgCtx, setBgCtx] = useState<{ x: number; y: number; wx: number; wy: number } | null>(null);

  const existingSlugs = new Set(nodes.map(n => n.slug));

  // ── Persist layout to localStorage ──
  const layoutKey = `canvas_layout_${projectName}`;

  const saveLayout = useCallback(() => {
    const layout: Record<string, { x: number; y: number; color: string }> = {};
    nodesRef.current.forEach(n => { layout[n.slug] = { x: n.x, y: n.y, color: n.color }; });
    try { localStorage.setItem(layoutKey, JSON.stringify(layout)); } catch {}
  }, [layoutKey]);

  const loadLayout = useCallback((): Record<string, { x: number; y: number; color: string }> => {
    try {
      const raw = localStorage.getItem(layoutKey);
      return raw ? JSON.parse(raw) : {};
    } catch { return {}; }
  }, [layoutKey]);

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
      const savedLayout = loadLayout();
      const cols = Math.max(4, Math.ceil(Math.sqrt(data.nodes.length)));
      const noteNodes: CanvasNode[] = [];
      for (let i = 0; i < data.nodes.length; i++) {
        const n = data.nodes[i];
        const prev = prevMap.get(n.slug);
        const saved = savedLayout[n.slug];
        let content = '';
        try { content = (await api.getNote(projectName, n.slug))?.content || ''; } catch {}
        noteNodes.push({
          slug: n.slug, title: n.title, content,
          x: prev?.x ?? saved?.x ?? (i % cols) * 80 + 60,
          y: prev?.y ?? saved?.y ?? Math.floor(i / cols) * 80 + 60,
          color: prev?.color ?? saved?.color ?? PALETTE[i % PALETTE.length],
        });
      }
      nodesRef.current = noteNodes;
      setNodes([...noteNodes]); setEdges([...data.edges]); setLoaded(true);
    } catch {}
  }, [projectName, loadLayout]);

  useEffect(() => { loadGraph(); }, [loadGraph, refreshKey]);

  // Close menus
  useEffect(() => {
    if (!ctxMenu && !edgeCtx && !bgCtx) return;
    const close = () => { setCtxMenu(null); setEdgeCtx(null); setBgCtx(null); };
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [ctxMenu, edgeCtx, bgCtx]);

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
        const out = getOutPort(a), inp = getInPort(b);
        const pad = 30;
        const minX = Math.min(out.x, inp.x) - pad, minY = Math.min(out.y, inp.y) - pad;
        const w = Math.abs(out.x - inp.x) + pad * 2, h = Math.abs(out.y - inp.y) + pad * 2;
        const lsx = out.x - minX, lsy = out.y - minY, lex = inp.x - minX, ley = inp.y - minY;
        const path = bezierPath(lsx, lsy, lex, ley);
        return (
          <svg key={`e-${i}`} style={{ position: 'absolute', left: minX, top: minY, width: w, height: h, pointerEvents: 'none', zIndex: 0, overflow: 'visible' }}>
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
        return (
          <div key={node.slug}>
            {/* Title above */}
            <div className="absolute pointer-events-none text-center" style={{ left: cx - 50, top: cy - r - 16, width: 100, fontSize: Math.max(9, 11 * s) }}>
              <span className="text-slate-600 font-medium whitespace-nowrap">{node.title}</span>
            </div>
            {/* Dot */}
            <div className="absolute rounded-full cursor-grab border-2 transition-shadow"
              style={{
                left: cx - r, top: cy - r, width: r * 2, height: r * 2,
                backgroundColor: node.color,
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
      <div className="absolute top-2 left-2 text-[10px] text-slate-400 bg-white/80 backdrop-blur px-2 py-1 rounded-lg z-10">
        더블클릭: 노트 열기 · 드래그: 이동 · 포트 드래그: 연결 · 우클릭: 메뉴
        {edges.length > 0 && <span className="ml-1 text-indigo-500">· {edges.length}개 연결</span>}
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

      {/* ── Note popup modal ── */}
      {popup && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setPopup(null)}
          onWheel={e => e.stopPropagation()}>
          <div className="bg-white rounded-2xl shadow-2xl w-[600px] max-w-[90vw] max-h-[80vh] flex flex-col overflow-hidden"
            onClick={e => e.stopPropagation()}
            onWheel={e => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
              <span className="font-bold text-slate-800 text-lg">{popup.title}</span>
              <div className="flex items-center gap-2">
                <button onClick={() => { setPopup(null); onNavigate(popup.slug); }}
                  className="px-3 py-1 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">편집</button>
                <button onClick={() => setPopup(null)}
                  className="text-slate-400 hover:text-slate-600 text-lg">✕</button>
              </div>
            </div>
            {/* Read-only rendered content */}
            <div className="flex-1 overflow-y-auto px-6 py-4 text-[15px] leading-relaxed">
              {popup.content ? (
                <NoteMarkdownViewer content={popup.content} existingSlugs={existingSlugs}
                  onNavigate={slug => { setPopup(null); onNavigate(slug); }} />
              ) : (
                <span className="text-slate-400 italic">내용이 없습니다. "편집" 버튼을 눌러 작성하세요.</span>
              )}
            </div>
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
            onClick={() => { setPopup({ slug: ctxMenu.node.slug, title: ctxMenu.node.title, content: ctxMenu.node.content }); setCtxMenu(null); }}>📝 미리보기</button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { onNavigate(ctxMenu.node.slug); setCtxMenu(null); }}>📄 에디터에서 열기</button>
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
                nodesRef.current.push({ slug: note.slug, title: note.title, content: '', x: bgCtx.wx, y: bgCtx.wy, color: PALETTE[nodesRef.current.length % PALETTE.length] });
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
