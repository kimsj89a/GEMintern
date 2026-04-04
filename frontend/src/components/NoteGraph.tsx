/**
 * NoteGraph — Obsidian Canvas style.
 *
 * HTML cards (draggable, editable) on a pannable/zoomable infinite canvas.
 * Connection lines drawn on a <canvas> layer underneath.
 *
 *   Drag card          → move
 *   Double-click card  → open note in editor
 *   Right-click card   → context menu (color, connect, delete link)
 *   Drag canvas bg     → pan
 *   Scroll             → zoom toward cursor
 *   Drag from handle   → create connection
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
}

interface CanvasEdge { source: string; target: string }

interface NoteGraphProps {
  projectName: string;
  activeSlug?: string | null;
  onNavigate: (slug: string) => void;
}

const CARD_W = 240;
const CARD_H = 160;

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

  // Viewport
  const panRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);
  const [, forceRender] = useState(0);
  const rerender = () => forceRender(v => v + 1);

  // Drag state
  const dragRef = useRef<{ slug: string; startX: number; startY: number; nodeStartX: number; nodeStartY: number; moved: boolean } | null>(null);
  const panDragRef = useRef<{ startX: number; startY: number; panStartX: number; panStartY: number } | null>(null);

  // Connection drag
  const [linkDrag, setLinkDrag] = useState<{ sourceSlug: string; mx: number; my: number } | null>(null);

  // Context menu
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; node: CanvasNode } | null>(null);

  // Inline editing
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const existingSlugs = new Set(nodes.map(n => n.slug));

  // ── Load graph data + note contents ──
  const loadGraph = useCallback(async () => {
    try {
      const data = await api.getNoteGraph(projectName);
      const prevMap = new Map(nodesRef.current.map(n => [n.slug, n]));

      // Load content for each note
      const noteNodes: CanvasNode[] = [];
      const cols = Math.max(3, Math.ceil(Math.sqrt(data.nodes.length)));
      for (let i = 0; i < data.nodes.length; i++) {
        const n = data.nodes[i];
        const prev = prevMap.get(n.slug);
        let content = prev?.content || '';
        if (!prev) {
          try {
            const full = await api.getNote(projectName, n.slug);
            content = full?.content || '';
          } catch {}
        }
        noteNodes.push({
          slug: n.slug,
          title: n.title,
          content,
          x: prev?.x ?? (i % cols) * (CARD_W + 40) + 60,
          y: prev?.y ?? Math.floor(i / cols) * (CARD_H + 40) + 60,
          w: prev?.w ?? CARD_W,
          h: prev?.h ?? CARD_H,
          color: prev?.color ?? '#ffffff',
        });
      }
      nodesRef.current = noteNodes;
      edgesRef.current = data.edges;
      setNodes([...noteNodes]);
      setEdges([...data.edges]);
      setLoaded(true);
    } catch {}
  }, [projectName]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  // Close context menu
  useEffect(() => {
    if (!ctxMenu) return;
    const close = () => setCtxMenu(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [ctxMenu]);

  // ── Draw edges on canvas ──
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const draw = () => {
      const rect = container.getBoundingClientRect();
      if (canvas.width !== rect.width || canvas.height !== rect.height) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const s = scaleRef.current;
      const px = panRef.current.x, py = panRef.current.y;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const nodeMap = new Map(nodesRef.current.map(n => [n.slug, n]));

      ctx.save();
      ctx.translate(px, py);
      ctx.scale(s, s);

      // Edges
      for (const e of edgesRef.current) {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) continue;
        const ax = a.x + a.w / 2, ay = a.y + a.h / 2;
        const bx = b.x + b.w / 2, by = b.y + b.h / 2;
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2 / s;
        ctx.globalAlpha = 0.4;
        ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
        ctx.globalAlpha = 1;
        // Arrow
        const ang = Math.atan2(by - ay, bx - ax);
        const arrowX = bx - Math.cos(ang) * 20;
        const arrowY = by - Math.sin(ang) * 20;
        ctx.fillStyle = '#6366f1';
        ctx.globalAlpha = 0.6;
        ctx.beginPath(); ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(arrowX - Math.cos(ang - 0.4) * 10 / s, arrowY - Math.sin(ang - 0.4) * 10 / s);
        ctx.lineTo(arrowX - Math.cos(ang + 0.4) * 10 / s, arrowY - Math.sin(ang + 0.4) * 10 / s);
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // Link drag line
      if (linkDrag) {
        const src = nodeMap.get(linkDrag.sourceSlug);
        if (src) {
          const sx = src.x + src.w / 2, sy = src.y + src.h / 2;
          const wx = (linkDrag.mx - px) / s, wy = (linkDrag.my - py) / s;
          ctx.strokeStyle = '#22c55e';
          ctx.lineWidth = 2.5 / s;
          ctx.setLineDash([6 / s, 4 / s]);
          ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(wx, wy); ctx.stroke();
          ctx.setLineDash([]);
        }
      }

      ctx.restore();
      requestAnimationFrame(draw);
    };
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [edges, linkDrag]);

  // ── Canvas resize ──
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
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragRef.current.moved = true;
      if (dragRef.current.moved) {
        const s = scaleRef.current;
        const node = nodesRef.current.find(n => n.slug === dragRef.current!.slug);
        if (node) {
          node.x = dragRef.current.nodeStartX + dx / s;
          node.y = dragRef.current.nodeStartY + dy / s;
          setNodes([...nodesRef.current]);
        }
      }
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      dragRef.current = null;
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  // ── Canvas pan ──
  const handleBgMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    panDragRef.current = { startX: e.clientX, startY: e.clientY, panStartX: panRef.current.x, panStartY: panRef.current.y };

    const onMove = (ev: MouseEvent) => {
      if (!panDragRef.current) return;
      panRef.current.x = panDragRef.current.panStartX + ev.clientX - panDragRef.current.startX;
      panRef.current.y = panDragRef.current.panStartY + ev.clientY - panDragRef.current.startY;
      rerender();
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      panDragRef.current = null;
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  // ── Zoom ──
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const oldS = scaleRef.current;
    const newS = Math.min(3, Math.max(0.2, oldS * (e.deltaY > 0 ? 0.92 : 1.08)));
    panRef.current.x = mx - (mx - panRef.current.x) * (newS / oldS);
    panRef.current.y = my - (my - panRef.current.y) * (newS / oldS);
    scaleRef.current = newS;
    rerender();
  };

  // ── Connection handle drag ──
  const handleConnectStart = (e: React.MouseEvent, slug: string) => {
    e.stopPropagation();
    e.preventDefault();
    setLinkDrag({ sourceSlug: slug, mx: e.clientX - (containerRef.current?.getBoundingClientRect().left || 0), my: e.clientY - (containerRef.current?.getBoundingClientRect().top || 0) });

    const onMove = (ev: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      setLinkDrag(prev => prev ? { ...prev, mx: ev.clientX - rect.left, my: ev.clientY - rect.top } : null);
    };
    const onUp = async (ev: MouseEvent) => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      // Find target card under cursor
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) { setLinkDrag(null); return; }
      const wx = (ev.clientX - rect.left - panRef.current.x) / scaleRef.current;
      const wy = (ev.clientY - rect.top - panRef.current.y) / scaleRef.current;
      const target = nodesRef.current.find(n => n.slug !== slug && wx >= n.x && wx <= n.x + n.w && wy >= n.y && wy <= n.y + n.h);
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
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  // ── Inline edit save ──
  const handleSaveEdit = async (slug: string) => {
    try {
      await api.updateNote(projectName, slug, { content: editContent });
      const node = nodesRef.current.find(n => n.slug === slug);
      if (node) node.content = editContent;
      setNodes([...nodesRef.current]);
    } catch {}
    setEditingSlug(null);
  };

  const s = scaleRef.current;
  const px = panRef.current.x, py = panRef.current.y;

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden bg-slate-50"
      onMouseDown={handleBgMouseDown} onWheel={handleWheel}
      style={{ cursor: panDragRef.current ? 'grabbing' : 'default' }}>

      {/* Canvas layer — connection lines */}
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" style={{ zIndex: 1 }} />

      {/* Cards layer */}
      <div className="absolute inset-0" style={{ zIndex: 2, pointerEvents: 'none' }}>
        {loaded && nodes.map(node => (
          <div
            key={node.slug}
            className={`absolute rounded-xl border-2 shadow-md overflow-hidden transition-shadow hover:shadow-lg ${
              node.slug === activeSlug ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200'
            }`}
            style={{
              left: node.x * s + px,
              top: node.y * s + py,
              width: node.w * s,
              minHeight: 60 * s,
              maxHeight: node.h * s,
              backgroundColor: node.color,
              transform: `scale(1)`,
              pointerEvents: 'auto',
              fontSize: `${Math.max(9, 12 * s)}px`,
            }}
            onMouseDown={e => handleCardMouseDown(e, node.slug)}
            onDoubleClick={e => { e.stopPropagation(); onNavigate(node.slug); }}
            onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setCtxMenu({ x: e.clientX, y: e.clientY, node }); }}
          >
            {/* Title bar */}
            <div className="px-2 py-1 border-b border-slate-100 flex items-center gap-1 cursor-grab"
              style={{ fontSize: `${Math.max(10, 12 * s)}px` }}>
              <span className="font-semibold text-slate-700 truncate flex-1">{node.title}</span>
              {/* Connect handle */}
              <div
                className="w-3 h-3 rounded-full bg-indigo-400 hover:bg-indigo-600 cursor-crosshair shrink-0 opacity-50 hover:opacity-100 transition-opacity"
                title="드래그하여 연결"
                onMouseDown={e => handleConnectStart(e, node.slug)}
              />
            </div>
            {/* Content preview */}
            <div className="px-2 py-1 overflow-hidden text-slate-600" style={{ maxHeight: (node.h - 30) * s }}>
              {editingSlug === node.slug ? (
                <div onClick={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}>
                  <textarea
                    autoFocus
                    value={editContent}
                    onChange={e => setEditContent(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Escape') setEditingSlug(null);
                      if (e.ctrlKey && e.key === 's') { e.preventDefault(); handleSaveEdit(node.slug); }
                    }}
                    className="w-full h-24 text-xs border border-indigo-200 rounded p-1 resize-none focus:outline-none focus:border-indigo-400"
                    style={{ fontSize: `${Math.max(9, 11 * s)}px` }}
                  />
                  <div className="flex gap-1 mt-1">
                    <button onClick={e => { e.stopPropagation(); handleSaveEdit(node.slug); }}
                      className="px-2 py-0.5 text-white bg-indigo-500 rounded text-[10px] hover:bg-indigo-600">저장</button>
                    <button onClick={e => { e.stopPropagation(); setEditingSlug(null); }}
                      className="px-2 py-0.5 text-slate-500 rounded text-[10px] hover:bg-slate-100">취소</button>
                  </div>
                </div>
              ) : (
                <div
                  className="line-clamp-6 cursor-pointer"
                  onClick={e => { e.stopPropagation(); setEditingSlug(node.slug); setEditContent(node.content); }}
                  style={{ fontSize: `${Math.max(9, 11 * s)}px` }}
                >
                  {node.content ? (
                    <NoteMarkdownViewer content={node.content.slice(0, 500)} existingSlugs={existingSlugs}
                      onNavigate={onNavigate} className="text-xs leading-snug" />
                  ) : (
                    <span className="text-slate-400 italic">클릭하여 편집</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Help + controls */}
      {!loaded && <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm z-10">캔버스 로딩 중...</div>}
      <div className="absolute top-2 left-2 text-[10px] text-slate-400 bg-white/80 backdrop-blur px-2 py-1 rounded-lg z-10">
        드래그: 이동 · 더블클릭: 노트 열기 · 클릭 내용: 편집 · ● 드래그: 연결 · 우클릭: 메뉴
      </div>
      <div className="absolute bottom-2 right-2 flex gap-1 z-10">
        <button onClick={() => { scaleRef.current = 1; panRef.current = { x: 0, y: 0 }; rerender(); }}
          className="px-2 h-7 bg-white border border-slate-200 rounded-lg text-[10px] text-slate-500 hover:bg-slate-50">리셋</button>
        <button onClick={() => { scaleRef.current = Math.min(3, scaleRef.current * 1.2); rerender(); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 font-bold">+</button>
        <button onClick={() => { scaleRef.current = Math.max(0.2, scaleRef.current * 0.8); rerender(); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 font-bold">-</button>
      </div>

      {/* Link drag indicator */}
      {linkDrag && (
        <div className="absolute top-2 right-2 text-xs text-green-600 bg-green-50 border border-green-200 px-3 py-1.5 rounded-lg animate-pulse z-10">
          🔗 카드 위에서 놓으면 연결됩니다
        </div>
      )}

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
                  onClick={() => {
                    const node = nodesRef.current.find(n => n.slug === ctxMenu.node.slug);
                    if (node) node.color = c;
                    setNodes([...nodesRef.current]);
                    setCtxMenu(null);
                  }}
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
            onClick={() => { setEditingSlug(ctxMenu.node.slug); setEditContent(ctxMenu.node.content); setCtxMenu(null); }}>
            ✏️ 캔버스에서 편집
          </button>
        </div>,
        document.body
      )}
    </div>
  );
}
