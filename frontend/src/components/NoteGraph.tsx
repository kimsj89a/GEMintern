/**
 * NoteGraph — Obsidian Canvas + NodeGraphProcessor style.
 *
 * Each card has:
 *   LEFT port (●) = input  — connections arrive here
 *   RIGHT port (●) = output — drag from here to create connections
 *
 * Edges: cubic bezier curves from output→input with horizontal-biased control points.
 * Each edge is an individual positioned <svg> — no layer/z-index issues.
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
  w: number; h: number;
  color: string;
  minimized: boolean;
}

interface CanvasEdge { source: string; target: string }

interface NoteGraphProps {
  projectName: string;
  activeSlug?: string | null;
  onNavigate: (slug: string) => void;
}

const CARD_W = 240;
const CARD_H = 160;
const DOT_R = 6;
const PORT_R = 2;
const MIN_W = 100;
const MIN_H = 60;
const AUTO_MIN_W = 50;
const AUTO_MIN_H = 35;

const PALETTE = [
  '#ffffff', '#e0e7ff', '#dbeafe', '#dcfce7', '#fef9c3',
  '#fce7f3', '#fde68a', '#fed7aa', '#e9d5ff', '#d1d5db',
];

// Port colors
const PORT_OUT_COLOR = '#6366f1'; // indigo — output
const PORT_IN_COLOR = '#22c55e';  // green — input
const EDGE_COLOR = '#6366f1';
const EDGE_DRAG_COLOR = '#22c55e';

export default function NoteGraph({ projectName, activeSlug, onNavigate }: NoteGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<CanvasNode[]>([]);
  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const [edges, setEdges] = useState<CanvasEdge[]>([]);
  const [loaded, setLoaded] = useState(false);

  const panRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);
  const [, setTick] = useState(0);
  const rerender = () => setTick(v => v + 1);

  const [linkDrag, setLinkDrag] = useState<{ sourceSlug: string; mx: number; my: number } | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; node: CanvasNode } | null>(null);
  const [edgeCtx, setEdgeCtx] = useState<{ x: number; y: number; edge: CanvasEdge } | null>(null);
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const existingSlugs = new Set(nodes.map(n => n.slug));

  // ── Delete edge: remove [[link]] from source note content ──
  const deleteEdge = async (edge: CanvasEdge) => {
    try {
      const srcNote = await api.getNote(projectName, edge.source);
      const targetNode = nodesRef.current.find(n => n.slug === edge.target);
      if (!srcNote || !targetNode) return;
      let c = srcNote.content || '';
      // Remove [[target.title]] and [[target.slug]] variations
      c = c.replace(new RegExp(`\\n*\\[\\[${targetNode.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\]\\]`, 'g'), '');
      c = c.replace(new RegExp(`\\n*\\[\\[${edge.target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\]\\]`, 'g'), '');
      await api.updateNote(projectName, edge.source, { content: c.trim() });
      loadGraph();
    } catch {}
  };

  // ── Port positions in screen space ──
  const getOutputPort = (n: CanvasNode) => {
    const s = scaleRef.current, px = panRef.current.x, py = panRef.current.y;
    if (n.minimized) return { x: n.x * s + px + DOT_R * s, y: n.y * s + py };
    return { x: (n.x + n.w) * s + px, y: (n.y + n.h / 2) * s + py };
  };

  const getInputPort = (n: CanvasNode) => {
    const s = scaleRef.current, px = panRef.current.x, py = panRef.current.y;
    if (n.minimized) return { x: n.x * s + px - DOT_R * s, y: n.y * s + py };
    return { x: n.x * s + px, y: (n.y + n.h / 2) * s + py };
  };

  // ── Bezier path: horizontal-biased cubic curve ──
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
      const cols = Math.max(3, Math.ceil(Math.sqrt(data.nodes.length)));
      const noteNodes: CanvasNode[] = [];
      for (let i = 0; i < data.nodes.length; i++) {
        const n = data.nodes[i];
        const prev = prevMap.get(n.slug);
        let content = '';
        try { content = (await api.getNote(projectName, n.slug))?.content || ''; } catch {}
        noteNodes.push({
          slug: n.slug, title: n.title, content,
          x: prev?.x ?? (i % cols) * (CARD_W + 60) + 80,
          y: prev?.y ?? Math.floor(i / cols) * (CARD_H + 50) + 80,
          w: prev?.w ?? CARD_W, h: prev?.h ?? CARD_H,
          color: prev?.color ?? '#ffffff',
          minimized: prev?.minimized ?? false,
        });
      }
      nodesRef.current = noteNodes;
      setNodes([...noteNodes]); setEdges([...data.edges]); setLoaded(true);
    } catch {}
  }, [projectName]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  useEffect(() => {
    if (!ctxMenu && !edgeCtx) return;
    const close = () => { setCtxMenu(null); setEdgeCtx(null); };
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [ctxMenu, edgeCtx]);

  // ── Card drag ──
  const handleCardDrag = (e: React.MouseEvent, slug: string) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    const node = nodesRef.current.find(n => n.slug === slug);
    if (!node) return;
    const startX = e.clientX, startY = e.clientY, nx = node.x, ny = node.y;
    const onMove = (ev: MouseEvent) => {
      const nd = nodesRef.current.find(n => n.slug === slug);
      if (!nd) return;
      nd.x = nx + (ev.clientX - startX) / scaleRef.current;
      nd.y = ny + (ev.clientY - startY) / scaleRef.current;
      setNodes([...nodesRef.current]);
    };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  };

  // ── Card resize ──
  const handleResize = (e: React.MouseEvent, slug: string) => {
    e.stopPropagation(); e.preventDefault();
    const node = nodesRef.current.find(n => n.slug === slug);
    if (!node) return;
    const startX = e.clientX, startY = e.clientY, sw = node.w, sh = node.h;
    const onMove = (ev: MouseEvent) => {
      const nd = nodesRef.current.find(n => n.slug === slug);
      if (!nd) return;
      const nw = sw + (ev.clientX - startX) / scaleRef.current;
      const nh = sh + (ev.clientY - startY) / scaleRef.current;
      if (nw < AUTO_MIN_W || nh < AUTO_MIN_H) { nd.minimized = true; }
      else { nd.w = Math.max(MIN_W, nw); nd.h = Math.max(MIN_H, nh); nd.minimized = false; }
      setNodes([...nodesRef.current]);
    };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
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

  // ── Zoom ──
  const handleBgWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const oldS = scaleRef.current, newS = Math.min(3, Math.max(0.15, oldS * (e.deltaY > 0 ? 0.92 : 1.08)));
    panRef.current.x = mx - (mx - panRef.current.x) * (newS / oldS);
    panRef.current.y = my - (my - panRef.current.y) * (newS / oldS);
    scaleRef.current = newS; rerender();
  };

  // ── Connection: drag from any port ──
  // sourceSlug = the note being dragged FROM
  // On drop: find nearest card/port, create [[link]] in source note
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
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      const r = containerRef.current?.getBoundingClientRect();
      if (!r) { setLinkDrag(null); return; }

      // Find target: check proximity to each node's INPUT port first, then bounding box
      const mx = ev.clientX - r.left, my = ev.clientY - r.top;
      let target: CanvasNode | undefined;

      // 1. Check input port proximity (within 20px screen space)
      for (const n of nodesRef.current) {
        if (n.slug === slug) continue;
        const inp = getInputPort(n);
        if (Math.hypot(mx - inp.x, my - inp.y) < 20) { target = n; break; }
      }

      // 2. Fallback: check card bounding box
      if (!target) {
        const s = scaleRef.current, ppx = panRef.current.x, ppy = panRef.current.y;
        const wx = (mx - ppx) / s, wy = (my - ppy) / s;
        target = nodesRef.current.find(n => {
          if (n.slug === slug) return false;
          if (n.minimized) return Math.hypot(wx - n.x, wy - n.y) < DOT_R + 15;
          return wx >= n.x - 10 && wx <= n.x + n.w + 10 && wy >= n.y - 10 && wy <= n.y + n.h + 10;
        });
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

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  // ── Inline edit ──
  const handleSaveEdit = async (slug: string) => {
    try {
      await api.updateNote(projectName, slug, { content: editContent });
      const node = nodesRef.current.find(n => n.slug === slug);
      if (node) node.content = editContent;
      setNodes([...nodesRef.current]);
    } catch {}
    setEditingSlug(null);
  };

  const s = scaleRef.current, px = panRef.current.x, py = panRef.current.y;
  const nodeMap = new Map(nodes.map(n => [n.slug, n]));

  // ── Render edges as individual SVGs ──
  const renderEdge = (e: CanvasEdge, i: number) => {
    const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
    if (!a || !b) return null;
    const out = getOutputPort(a);
    const inp = getInputPort(b);
    const pad = 30;
    const minX = Math.min(out.x, inp.x) - pad;
    const minY = Math.min(out.y, inp.y) - pad;
    const w = Math.abs(out.x - inp.x) + pad * 2;
    const h = Math.abs(out.y - inp.y) + pad * 2;
    const lsx = out.x - minX, lsy = out.y - minY;
    const lex = inp.x - minX, ley = inp.y - minY;
    const path = bezierPath(lsx, lsy, lex, ley);

    return (
      <svg key={`e-${e.source}-${e.target}-${i}`}
        style={{ position: 'absolute', left: minX, top: minY, width: w, height: h, pointerEvents: 'none', zIndex: 1, overflow: 'visible' }}>
        {/* Invisible fat hit area for right-click */}
        <path d={path} fill="none" stroke="transparent" strokeWidth="14"
          style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
          onContextMenu={(ev) => { ev.preventDefault(); ev.stopPropagation(); setEdgeCtx({ x: ev.clientX, y: ev.clientY, edge: e }); }} />
        {/* Shadow */}
        <path d={path} fill="none" stroke="rgba(99,102,241,0.15)" strokeWidth="6" style={{ pointerEvents: 'none' }} />
        {/* Main line */}
        <path d={path} fill="none" stroke={EDGE_COLOR} strokeWidth="2.5" strokeOpacity="0.7" style={{ pointerEvents: 'none' }} />
        {/* Dot at input port */}
        <circle cx={lex} cy={ley} r="2.5" fill={PORT_IN_COLOR} style={{ pointerEvents: 'none' }} />
      </svg>
    );
  };

  // ── Render link drag line ──
  const renderLinkDrag = () => {
    if (!linkDrag) return null;
    const src = nodeMap.get(linkDrag.sourceSlug);
    if (!src) return null;
    const out = getOutputPort(src);
    const mx = linkDrag.mx, my = linkDrag.my;
    const pad = 30;
    const minX = Math.min(out.x, mx) - pad;
    const minY = Math.min(out.y, my) - pad;
    const w = Math.abs(out.x - mx) + pad * 2;
    const h = Math.abs(out.y - my) + pad * 2;
    const lsx = out.x - minX, lsy = out.y - minY;
    const lex = mx - minX, ley = my - minY;
    const path = bezierPath(lsx, lsy, lex, ley);

    return (
      <svg style={{ position: 'absolute', left: minX, top: minY, width: w, height: h, pointerEvents: 'none', zIndex: 5, overflow: 'visible' }}>
        <path d={path} fill="none" stroke={EDGE_DRAG_COLOR} strokeWidth="2.5" strokeDasharray="8 4" />
        <circle cx={lex} cy={ley} r="4" fill={EDGE_DRAG_COLOR} fillOpacity="0.5" />
      </svg>
    );
  };

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden bg-[#fafafa]"
      onMouseDown={handleBgDown} onWheel={handleBgWheel}>

      {/* Edges */}
      {edges.map((e, i) => renderEdge(e, i))}

      {/* Link drag */}
      {renderLinkDrag()}

      {/* Cards */}
      {loaded && nodes.map(node => {
        const screenX = node.x * s + px;
        const screenY = node.y * s + py;

        if (node.minimized) {
          const outPort = getOutputPort(node);
          const inPort = getInputPort(node);
          return (
            <div key={node.slug}>
              {/* Dot */}
              <div className="absolute rounded-full border-2 cursor-pointer"
                style={{
                  left: screenX - DOT_R * s, top: screenY - DOT_R * s,
                  width: DOT_R * 2 * s, height: DOT_R * 2 * s,
                  backgroundColor: node.color === '#ffffff' ? PORT_OUT_COLOR : node.color,
                  borderColor: node.slug === activeSlug ? '#4338ca' : '#9ca3af',
                  zIndex: 3,
                }}
                onMouseDown={e => handleCardDrag(e, node.slug)}
                onDoubleClick={e => { e.stopPropagation(); const nd = nodesRef.current.find(n => n.slug === node.slug); if (nd) { nd.minimized = false; nd.w = CARD_W; nd.h = CARD_H; setNodes([...nodesRef.current]); } }}
                onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setCtxMenu({ x: e.clientX, y: e.clientY, node }); }}
              >
                <div className="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap text-slate-500 pointer-events-none"
                  style={{ fontSize: Math.max(8, 10 * s) }}>{node.title}</div>
              </div>
              {/* Output port */}
              <div className="absolute rounded-full cursor-crosshair hover:scale-150 transition-transform"
                style={{ left: outPort.x - 4, top: outPort.y - 4, width: 8, height: 8, backgroundColor: PORT_OUT_COLOR, zIndex: 4 }}
                onMouseDown={e => handlePortDrag(e, node.slug)} />
              {/* Input port */}
              <div className="absolute rounded-full"
                style={{ left: inPort.x - 4, top: inPort.y - 4, width: 8, height: 8, backgroundColor: PORT_IN_COLOR, zIndex: 4, opacity: 0.6 }} />
            </div>
          );
        }

        const outPort = getOutputPort(node);
        const inPort = getInputPort(node);

        return (
          <div key={node.slug}>
            {/* Output port (RIGHT side) — small dot, larger hit area via padding */}
            <div className="absolute cursor-crosshair"
              title="드래그하여 연결"
              style={{ left: outPort.x - 8, top: outPort.y - 8, width: 16, height: 16, zIndex: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              onMouseDown={e => handlePortDrag(e, node.slug)}>
              <div className="rounded-full" style={{ width: PORT_R * 2, height: PORT_R * 2, backgroundColor: PORT_OUT_COLOR }} />
            </div>
            {/* Input port (LEFT side) */}
            <div className="absolute cursor-crosshair"
              title="드래그하여 연결"
              style={{ left: inPort.x - 8, top: inPort.y - 8, width: 16, height: 16, zIndex: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              onMouseDown={e => handlePortDrag(e, node.slug)}>
              <div className="rounded-full" style={{ width: PORT_R * 2, height: PORT_R * 2, backgroundColor: PORT_IN_COLOR, opacity: 0.7 }} />
            </div>

            {/* Card body */}
            <div className={`absolute rounded-xl border-2 shadow-md flex flex-col ${
                node.slug === activeSlug ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200 hover:border-slate-300'
              }`}
              style={{ left: screenX, top: screenY, width: node.w * s, height: node.h * s, backgroundColor: node.color, zIndex: 3, fontSize: Math.max(9, 12 * s) }}
              onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setCtxMenu({ x: e.clientX, y: e.clientY, node }); }}
            >
              {/* Title bar */}
              <div className="px-2 py-1 border-b border-slate-100 flex items-center gap-1 cursor-grab select-none shrink-0"
                onMouseDown={e => handleCardDrag(e, node.slug)} style={{ fontSize: Math.max(10, 12 * s) }}>
                <button className="text-slate-400 hover:text-amber-500 text-[10px] shrink-0" title="최소화"
                  onMouseDown={e => e.stopPropagation()}
                  onClick={e => { e.stopPropagation(); const nd = nodesRef.current.find(n => n.slug === node.slug); if (nd) { nd.minimized = true; setNodes([...nodesRef.current]); } }}>⋯</button>
                <span className="font-semibold text-slate-700 truncate flex-1">{node.title}</span>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-1 text-slate-600" onWheel={e => e.stopPropagation()}>
                {editingSlug === node.slug ? (
                  <div onClick={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}>
                    <textarea autoFocus value={editContent} onChange={e => setEditContent(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Escape') setEditingSlug(null); if (e.ctrlKey && e.key === 's') { e.preventDefault(); handleSaveEdit(node.slug); } }}
                      className="w-full border border-indigo-200 rounded p-1 resize-none focus:outline-none"
                      style={{ height: '85%', fontSize: Math.max(9, 11 * s) }} />
                    <div className="flex gap-1 mt-1">
                      <button onClick={e => { e.stopPropagation(); handleSaveEdit(node.slug); }} className="px-2 py-0.5 text-white bg-indigo-500 rounded text-[10px]">저장</button>
                      <button onClick={e => { e.stopPropagation(); setEditingSlug(null); }} className="px-2 py-0.5 text-slate-500 rounded text-[10px]">취소</button>
                    </div>
                  </div>
                ) : (
                  <div className="cursor-pointer min-h-[20px]"
                    onClick={e => { e.stopPropagation(); setEditingSlug(node.slug); setEditContent(node.content); }}
                    onDoubleClick={e => { e.stopPropagation(); onNavigate(node.slug); }}
                    style={{ fontSize: Math.max(9, 11 * s) }}>
                    {node.content ? (
                      <NoteMarkdownViewer content={node.content.slice(0, 500)} existingSlugs={existingSlugs} onNavigate={onNavigate} className="leading-snug" />
                    ) : <span className="text-slate-400 italic">클릭하여 편집</span>}
                  </div>
                )}
              </div>

              {/* Resize */}
              <div className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize" onMouseDown={e => handleResize(e, node.slug)}>
                <svg className="w-3 h-3 text-slate-300 absolute bottom-0.5 right-0.5" viewBox="0 0 6 6">
                  <circle cx="5" cy="5" r="1" fill="currentColor" /><circle cx="5" cy="2" r="1" fill="currentColor" /><circle cx="2" cy="5" r="1" fill="currentColor" />
                </svg>
              </div>
            </div>
          </div>
        );
      })}

      {!loaded && <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm z-10">캔버스 로딩 중...</div>}

      <div className="absolute top-2 left-2 text-[10px] text-slate-400 bg-white/90 backdrop-blur px-2 py-1 rounded-lg z-10">
        제목 드래그: 이동 · 더블클릭: 노트 열기 · <span style={{color: PORT_OUT_COLOR}}>●</span> 출력포트 드래그 → <span style={{color: PORT_IN_COLOR}}>●</span> 입력포트: 연결
        {edges.length > 0 && <span className="ml-1 text-indigo-500">· {edges.length}개 연결</span>}
      </div>

      {linkDrag && (
        <div className="absolute top-2 right-2 text-xs text-green-600 bg-green-50 border border-green-200 px-3 py-1.5 rounded-lg animate-pulse z-10">
          🔗 카드 위에서 놓으면 연결됩니다
        </div>
      )}

      <div className="absolute bottom-2 right-2 flex gap-1 z-10">
        <button onClick={() => { scaleRef.current = 1; panRef.current = { x: 0, y: 0 }; rerender(); }}
          className="px-2 h-7 bg-white border border-slate-200 rounded-lg text-[10px] text-slate-500 hover:bg-slate-50">리셋</button>
        <button onClick={() => { scaleRef.current = Math.min(3, scaleRef.current * 1.2); rerender(); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 font-bold">+</button>
        <button onClick={() => { scaleRef.current = Math.max(0.15, scaleRef.current * 0.8); rerender(); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 font-bold">-</button>
      </div>

      {ctxMenu && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[150px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }} onClick={e => e.stopPropagation()}>
          <div className="px-3 py-1.5 text-xs font-semibold text-slate-700 border-b border-slate-100 mb-1 truncate">{ctxMenu.node.title}</div>
          <div className="px-3 py-1.5">
            <div className="text-[10px] text-slate-400 mb-1">색상</div>
            <div className="flex flex-wrap gap-1">
              {PALETTE.map(c => (
                <button key={c} onClick={() => { const nd = nodesRef.current.find(n => n.slug === ctxMenu.node.slug); if (nd) nd.color = c; setNodes([...nodesRef.current]); setCtxMenu(null); }}
                  className="w-5 h-5 rounded-full border border-slate-200 hover:scale-125 transition-transform" style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50" onClick={() => { onNavigate(ctxMenu.node.slug); setCtxMenu(null); }}>📝 노트 열기</button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { const nd = nodesRef.current.find(n => n.slug === ctxMenu.node.slug); if (nd) { nd.minimized = !nd.minimized; if (!nd.minimized) { nd.w = CARD_W; nd.h = CARD_H; } setNodes([...nodesRef.current]); } setCtxMenu(null); }}>
            {ctxMenu.node.minimized ? '🔲 카드로' : '⋯ 최소화'}
          </button>
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
            onClick={() => { deleteEdge(edgeCtx.edge); setEdgeCtx(null); }}>
            🗑 연결 삭제
          </button>
        </div>,
        document.body
      )}
    </div>
  );
}
