/**
 * NoteGraph — Obsidian Canvas style.
 *
 * HTML cards on a pannable/zoomable infinite canvas.
 * Connection lines drawn on a <canvas> layer underneath.
 * Cards can be resized from edges, minimized to dots.
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
const MIN_CARD_W = 120;
const MIN_CARD_H = 80;

const PALETTE = [
  '#ffffff', '#e0e7ff', '#dbeafe', '#dcfce7', '#fef9c3',
  '#fce7f3', '#fde68a', '#fed7aa', '#e9d5ff', '#d1d5db',
];

export default function NoteGraph({ projectName, activeSlug, onNavigate }: NoteGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<CanvasNode[]>([]);
  const edgesRef = useRef<CanvasEdge[]>([]);
  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const [edges, setEdges] = useState<CanvasEdge[]>([]);
  const [loaded, setLoaded] = useState(false);

  const panRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);
  const [, forceRender] = useState(0);
  const rerender = () => forceRender(v => v + 1);

  const dragRef = useRef<{ slug: string; startX: number; startY: number; nodeStartX: number; nodeStartY: number; moved: boolean } | null>(null);
  const resizeRef = useRef<{ slug: string; startX: number; startY: number; startW: number; startH: number } | null>(null);
  const panDragRef = useRef<{ startX: number; startY: number; panStartX: number; panStartY: number } | null>(null);
  const [linkDrag, setLinkDrag] = useState<{ sourceSlug: string; mx: number; my: number } | null>(null);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; node: CanvasNode } | null>(null);
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const existingSlugs = new Set(nodes.map(n => n.slug));

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
        let content = prev?.content || '';
        if (!prev) {
          try { content = (await api.getNote(projectName, n.slug))?.content || ''; } catch {}
        }
        noteNodes.push({
          slug: n.slug, title: n.title, content,
          x: prev?.x ?? (i % cols) * (CARD_W + 40) + 60,
          y: prev?.y ?? Math.floor(i / cols) * (CARD_H + 40) + 60,
          w: prev?.w ?? CARD_W, h: prev?.h ?? CARD_H,
          color: prev?.color ?? '#ffffff',
          minimized: prev?.minimized ?? false,
        });
      }
      nodesRef.current = noteNodes;
      edgesRef.current = data.edges;
      setNodes([...noteNodes]); setEdges([...data.edges]); setLoaded(true);
    } catch {}
  }, [projectName]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  useEffect(() => {
    if (!ctxMenu) return;
    const close = () => setCtxMenu(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [ctxMenu]);

  // ── Draw edges ──
  useEffect(() => {
    const canvas = canvasRef.current, container = containerRef.current;
    if (!canvas || !container) return;
    let running = true;
    const draw = () => {
      if (!running) return;
      const rect = container.getBoundingClientRect();
      if (rect.width > 0 && (canvas.width !== rect.width || canvas.height !== rect.height)) {
        canvas.width = rect.width; canvas.height = rect.height;
      }
      const ctx = canvas.getContext('2d');
      if (!ctx || canvas.width < 2) { requestAnimationFrame(draw); return; }
      const s = scaleRef.current, px = panRef.current.x, py = panRef.current.y;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const nodeMap = new Map(nodesRef.current.map(n => [n.slug, n]));
      ctx.save(); ctx.translate(px, py); ctx.scale(s, s);

      for (const e of edgesRef.current) {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) continue;
        const ax = a.minimized ? a.x : a.x + a.w / 2;
        const ay = a.minimized ? a.y : a.y + a.h / 2;
        const bx = b.minimized ? b.x : b.x + b.w / 2;
        const by = b.minimized ? b.y : b.y + b.h / 2;
        ctx.strokeStyle = '#6366f1'; ctx.lineWidth = 2.5 / s; ctx.globalAlpha = 0.5;
        ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
        ctx.globalAlpha = 1;
        const ang = Math.atan2(by - ay, bx - ax);
        const dist = b.minimized ? DOT_R + 2 : 20;
        const arrX = bx - Math.cos(ang) * dist, arrY = by - Math.sin(ang) * dist;
        ctx.fillStyle = '#6366f1'; ctx.globalAlpha = 0.7;
        ctx.beginPath(); ctx.moveTo(arrX, arrY);
        ctx.lineTo(arrX - Math.cos(ang - 0.4) * 10 / s, arrY - Math.sin(ang - 0.4) * 10 / s);
        ctx.lineTo(arrX - Math.cos(ang + 0.4) * 10 / s, arrY - Math.sin(ang + 0.4) * 10 / s);
        ctx.fill(); ctx.globalAlpha = 1;
      }

      if (linkDrag) {
        const src = nodeMap.get(linkDrag.sourceSlug);
        if (src) {
          const sx = src.minimized ? src.x : src.x + src.w / 2;
          const sy = src.minimized ? src.y : src.y + src.h / 2;
          const wx = (linkDrag.mx - px) / s, wy = (linkDrag.my - py) / s;
          ctx.strokeStyle = '#22c55e'; ctx.lineWidth = 2.5 / s;
          ctx.setLineDash([6 / s, 4 / s]);
          ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(wx, wy); ctx.stroke();
          ctx.setLineDash([]);
        }
      }
      ctx.restore();
      requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
    return () => { running = false; };
  }, [edges, linkDrag]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const obs = new ResizeObserver(() => rerender());
    obs.observe(container);
    return () => obs.disconnect();
  }, []);

  // ── Card drag ──
  const handleCardMouseDown = (e: React.MouseEvent, slug: string) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    const node = nodesRef.current.find(n => n.slug === slug);
    if (!node) return;
    dragRef.current = { slug, startX: e.clientX, startY: e.clientY, nodeStartX: node.x, nodeStartY: node.y, moved: false };
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX, dy = ev.clientY - dragRef.current.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragRef.current.moved = true;
      if (dragRef.current.moved) {
        const nd = nodesRef.current.find(n => n.slug === dragRef.current!.slug);
        if (nd) { nd.x = dragRef.current.nodeStartX + dx / scaleRef.current; nd.y = dragRef.current.nodeStartY + dy / scaleRef.current; setNodes([...nodesRef.current]); }
      }
    };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); dragRef.current = null; };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  };

  // ── Card resize (from bottom-right corner) ──
  const handleResizeStart = (e: React.MouseEvent, slug: string) => {
    e.stopPropagation(); e.preventDefault();
    const node = nodesRef.current.find(n => n.slug === slug);
    if (!node) return;
    resizeRef.current = { slug, startX: e.clientX, startY: e.clientY, startW: node.w, startH: node.h };
    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      const nd = nodesRef.current.find(n => n.slug === resizeRef.current!.slug);
      if (!nd) return;
      nd.w = Math.max(MIN_CARD_W, resizeRef.current.startW + (ev.clientX - resizeRef.current.startX) / scaleRef.current);
      nd.h = Math.max(MIN_CARD_H, resizeRef.current.startH + (ev.clientY - resizeRef.current.startY) / scaleRef.current);
      setNodes([...nodesRef.current]);
    };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); resizeRef.current = null; };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  };

  // ── Pan ──
  const handleBgMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    panDragRef.current = { startX: e.clientX, startY: e.clientY, panStartX: panRef.current.x, panStartY: panRef.current.y };
    const onMove = (ev: MouseEvent) => {
      if (!panDragRef.current) return;
      panRef.current.x = panDragRef.current.panStartX + ev.clientX - panDragRef.current.startX;
      panRef.current.y = panDragRef.current.panStartY + ev.clientY - panDragRef.current.startY;
      rerender();
    };
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); panDragRef.current = null; };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  };

  // ── Zoom ──
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const oldS = scaleRef.current;
    const newS = Math.min(3, Math.max(0.15, oldS * (e.deltaY > 0 ? 0.92 : 1.08)));
    panRef.current.x = mx - (mx - panRef.current.x) * (newS / oldS);
    panRef.current.y = my - (my - panRef.current.y) * (newS / oldS);
    scaleRef.current = newS; rerender();
  };

  // ── Connect handle ──
  const handleConnectStart = (e: React.MouseEvent, slug: string) => {
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
      const s = scaleRef.current, px = panRef.current.x, py = panRef.current.y;
      const wx = (ev.clientX - r.left - px) / s, wy = (ev.clientY - r.top - py) / s;
      const target = nodesRef.current.find(n => {
        if (n.slug === slug) return false;
        if (n.minimized) return Math.hypot(wx - n.x, wy - n.y) < DOT_R + 6;
        return wx >= n.x && wx <= n.x + n.w && wy >= n.y && wy <= n.y + n.h;
      });
      if (target) {
        try {
          const srcNote = await api.getNote(projectName, slug);
          if (srcNote) {
            const link = `[[${target.title}]]`;
            if (!(srcNote.content || '').includes(link)) {
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

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden bg-slate-50"
      onMouseDown={handleBgMouseDown} onWheel={handleWheel}
      style={{ cursor: panDragRef.current ? 'grabbing' : 'default' }}>

      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" style={{ zIndex: 1 }} />

      <div className="absolute inset-0" style={{ zIndex: 2, pointerEvents: 'none' }}>
        {loaded && nodes.map(node => {
          if (node.minimized) {
            // Minimized: small dot
            return (
              <div key={node.slug}
                className="absolute rounded-full border-2 cursor-pointer"
                style={{
                  left: node.x * s + px - DOT_R * s,
                  top: node.y * s + py - DOT_R * s,
                  width: DOT_R * 2 * s, height: DOT_R * 2 * s,
                  backgroundColor: node.color === '#ffffff' ? '#6366f1' : node.color,
                  borderColor: node.slug === activeSlug ? '#4338ca' : '#9ca3af',
                  pointerEvents: 'auto',
                }}
                onMouseDown={e => handleCardMouseDown(e, node.slug)}
                onDoubleClick={e => { e.stopPropagation(); const nd = nodesRef.current.find(n => n.slug === node.slug); if (nd) { nd.minimized = false; setNodes([...nodesRef.current]); } }}
                onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setCtxMenu({ x: e.clientX, y: e.clientY, node }); }}
                title={node.title}
              >
                {/* Title tooltip on hover */}
                <div className="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] text-slate-500 pointer-events-none"
                  style={{ fontSize: Math.max(8, 10 * s) }}>{node.title}</div>
              </div>
            );
          }

          // Full card
          return (
            <div key={node.slug}
              className={`absolute rounded-xl border-2 shadow-md overflow-hidden hover:shadow-lg ${
                node.slug === activeSlug ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200'
              }`}
              style={{
                left: node.x * s + px, top: node.y * s + py,
                width: node.w * s, height: node.h * s,
                backgroundColor: node.color,
                pointerEvents: 'auto',
                fontSize: Math.max(9, 12 * s),
              }}
              onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setCtxMenu({ x: e.clientX, y: e.clientY, node }); }}
            >
              {/* Title bar — draggable */}
              <div className="px-2 py-1 border-b border-slate-100 flex items-center gap-1 cursor-grab select-none"
                onMouseDown={e => handleCardMouseDown(e, node.slug)}
                style={{ fontSize: Math.max(10, 12 * s) }}>
                {/* Minimize button */}
                <button className="w-3 h-3 rounded-full bg-slate-300 hover:bg-amber-400 shrink-0 transition-colors"
                  title="최소화"
                  onMouseDown={e => e.stopPropagation()}
                  onClick={e => { e.stopPropagation(); const nd = nodesRef.current.find(n => n.slug === node.slug); if (nd) { nd.minimized = true; setNodes([...nodesRef.current]); } }}
                />
                <span className="font-semibold text-slate-700 truncate flex-1">{node.title}</span>
                {/* Connect handle */}
                <div className="w-3.5 h-3.5 rounded-full bg-indigo-400 hover:bg-indigo-600 cursor-crosshair shrink-0 opacity-40 hover:opacity-100 transition-opacity"
                  title="드래그하여 연결"
                  onMouseDown={e => handleConnectStart(e, node.slug)} />
              </div>

              {/* Content */}
              <div className="px-2 py-1 overflow-hidden text-slate-600 flex-1"
                style={{ height: `calc(100% - ${28 * s}px)` }}>
                {editingSlug === node.slug ? (
                  <div onClick={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}>
                    <textarea autoFocus value={editContent} onChange={e => setEditContent(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Escape') setEditingSlug(null); if (e.ctrlKey && e.key === 's') { e.preventDefault(); handleSaveEdit(node.slug); } }}
                      className="w-full border border-indigo-200 rounded p-1 resize-none focus:outline-none focus:border-indigo-400"
                      style={{ height: '80%', fontSize: Math.max(9, 11 * s) }} />
                    <div className="flex gap-1 mt-1">
                      <button onClick={e => { e.stopPropagation(); handleSaveEdit(node.slug); }}
                        className="px-2 py-0.5 text-white bg-indigo-500 rounded text-[10px]">저장</button>
                      <button onClick={e => { e.stopPropagation(); setEditingSlug(null); }}
                        className="px-2 py-0.5 text-slate-500 rounded text-[10px]">취소</button>
                    </div>
                  </div>
                ) : (
                  <div className="h-full overflow-hidden cursor-pointer"
                    onClick={e => { e.stopPropagation(); setEditingSlug(node.slug); setEditContent(node.content); }}
                    onDoubleClick={e => { e.stopPropagation(); onNavigate(node.slug); }}
                    style={{ fontSize: Math.max(9, 11 * s) }}>
                    {node.content ? (
                      <NoteMarkdownViewer content={node.content.slice(0, 500)} existingSlugs={existingSlugs}
                        onNavigate={onNavigate} className="leading-snug" />
                    ) : (
                      <span className="text-slate-400 italic">클릭하여 편집</span>
                    )}
                  </div>
                )}
              </div>

              {/* Resize handle (bottom-right) */}
              <div className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize"
                onMouseDown={e => handleResizeStart(e, node.slug)}>
                <svg className="w-3 h-3 text-slate-300 absolute bottom-0.5 right-0.5" viewBox="0 0 6 6">
                  <circle cx="5" cy="5" r="1" fill="currentColor" />
                  <circle cx="5" cy="2" r="1" fill="currentColor" />
                  <circle cx="2" cy="5" r="1" fill="currentColor" />
                </svg>
              </div>
            </div>
          );
        })}
      </div>

      {!loaded && <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm z-10">캔버스 로딩 중...</div>}

      <div className="absolute top-2 left-2 text-[10px] text-slate-400 bg-white/80 backdrop-blur px-2 py-1 rounded-lg z-10">
        드래그: 이동 · 더블클릭: 노트 열기 · ● 연결 · 모서리: 크기 조절
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

      {/* Context menu */}
      {ctxMenu && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[150px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }} onClick={e => e.stopPropagation()}>
          <div className="px-3 py-1.5 text-xs font-semibold text-slate-700 border-b border-slate-100 mb-1 truncate">
            {ctxMenu.node.title}
          </div>
          <div className="px-3 py-1.5">
            <div className="text-[10px] text-slate-400 mb-1">색상</div>
            <div className="flex flex-wrap gap-1">
              {PALETTE.map(c => (
                <button key={c}
                  onClick={() => { const nd = nodesRef.current.find(n => n.slug === ctxMenu.node.slug); if (nd) nd.color = c; setNodes([...nodesRef.current]); setCtxMenu(null); }}
                  className="w-5 h-5 rounded-full border border-slate-200 hover:scale-125 transition-transform"
                  style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { onNavigate(ctxMenu.node.slug); setCtxMenu(null); }}>
            📝 노트 열기
          </button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => {
              const nd = nodesRef.current.find(n => n.slug === ctxMenu.node.slug);
              if (nd) { nd.minimized = !nd.minimized; setNodes([...nodesRef.current]); }
              setCtxMenu(null);
            }}>
            {ctxMenu.node.minimized ? '🔲 카드로 보기' : '⚫ 최소화'}
          </button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { setEditingSlug(ctxMenu.node.slug); setEditContent(ctxMenu.node.content); setCtxMenu(null); }}>
            ✏️ 캔버스에서 편집
          </button>
        </div>,
        document.body
      )}
    </div>
  );
}
