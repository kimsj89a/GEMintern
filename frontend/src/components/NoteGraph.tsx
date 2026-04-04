/**
 * NoteGraph — Force-directed graph of research notes.
 *
 *   Left-click node     → open note
 *   Left-drag node      → move node (pins in place)
 *   Left-drag canvas    → pan view
 *   Shift+Left-drag     → create [[wikilink]] connection
 *   Right-click node    → context menu (color, connect, size)
 *   Scroll              → zoom (toward cursor)
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api/client';

interface GraphNode {
  slug: string;
  title: string;
  x: number; y: number;
  vx: number; vy: number;
  radius: number;
  pinned: boolean;
  color: string; // fill color
}

interface GraphEdge { source: string; target: string }

interface NoteGraphProps {
  projectName: string;
  activeSlug?: string | null;
  onNavigate: (slug: string) => void;
}

const REPULSION = 600;
const SPRING_K = 0.025;
const SPRING_LEN = 140;
const DAMPING = 0.88;
const CENTER_PULL = 0.003;
const DEFAULT_R = 12;
const CLICK_THRESHOLD = 5;

const PALETTE = [
  '#ffffff', '#e0e7ff', '#dbeafe', '#dcfce7', '#fef9c3',
  '#fce7f3', '#fde68a', '#fed7aa', '#e9d5ff', '#d1d5db',
];

export default function NoteGraph({ projectName, activeSlug, onNavigate }: NoteGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const animRef = useRef<number>(0);
  const hoverRef = useRef<GraphNode | null>(null);
  const scaleRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const [nodeRadius, setNodeRadius] = useState(DEFAULT_R);

  // Left drag
  const leftDragRef = useRef<{
    node: GraphNode | null; startX: number; startY: number; moved: boolean; shift: boolean;
  } | null>(null);

  // Shift+drag link creation
  const linkDragRef = useRef<{ source: GraphNode; worldX: number; worldY: number; targetNode: GraphNode | null } | null>(null);
  // linkDragRef is used for visual feedback only during node→node drag

  // Context menu
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; node: GraphNode } | null>(null);
  const [connectMode, setConnectMode] = useState(false);
  const connectSourceRef = useRef<GraphNode | null>(null);

  const [loaded, setLoaded] = useState(false);

  const screenToWorld = (sx: number, sy: number) => ({
    x: (sx - panRef.current.x) / scaleRef.current,
    y: (sy - panRef.current.y) / scaleRef.current,
  });

  const getNodeAt = (sx: number, sy: number): GraphNode | null => {
    const { x, y } = screenToWorld(sx, sy);
    for (const n of nodesRef.current) {
      const dx = x - n.x, dy = y - n.y;
      if (dx * dx + dy * dy < (n.radius + 6) * (n.radius + 6)) return n;
    }
    return null;
  };

  const loadGraph = useCallback(async () => {
    try {
      const data = await api.getNoteGraph(projectName);
      const linkCount: Record<string, number> = {};
      for (const e of data.edges) {
        linkCount[e.source] = (linkCount[e.source] || 0) + 1;
        linkCount[e.target] = (linkCount[e.target] || 0) + 1;
      }
      const canvas = canvasRef.current;
      const cx = (canvas?.width || 600) / 2, cy = (canvas?.height || 400) / 2;
      // Preserve existing colors/pins
      const prevMap = new Map(nodesRef.current.map(n => [n.slug, n]));
      nodesRef.current = data.nodes.map((n: any, i: number) => {
        const prev = prevMap.get(n.slug);
        const angle = (2 * Math.PI * i) / Math.max(data.nodes.length, 1);
        const r = 80 + Math.random() * 100;
        return {
          slug: n.slug, title: n.title,
          x: prev?.x ?? cx + Math.cos(angle) * r,
          y: prev?.y ?? cy + Math.sin(angle) * r,
          vx: 0, vy: 0,
          pinned: prev?.pinned ?? false,
          color: prev?.color ?? '#ffffff',
          radius: nodeRadius,
        };
      });
      edgesRef.current = data.edges;
      setLoaded(true);
    } catch {}
  }, [projectName, nodeRadius]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  // Update radii when slider changes
  useEffect(() => {
    nodesRef.current.forEach(n => { n.radius = nodeRadius; });
  }, [nodeRadius]);

  // Close context menu
  useEffect(() => {
    if (!ctxMenu) return;
    const close = () => setCtxMenu(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [ctxMenu]);

  // ── Simulation + render ──
  useEffect(() => {
    if (!loaded) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const nodeMap = new Map<string, GraphNode>();

    const tick = () => {
      const nodes = nodesRef.current, edges = edgesRef.current;
      // Auto-resize canvas when parent becomes visible (fixes hidden→visible transition)
      const parentRect = canvas.parentElement?.getBoundingClientRect();
      if (parentRect && parentRect.width > 0 && (canvas.width < 2 || canvas.height < 2)) {
        canvas.width = parentRect.width;
        canvas.height = parentRect.height;
      }
      const w = canvas.width, h = canvas.height;
      if (w < 2 || h < 2) { animRef.current = requestAnimationFrame(tick); return; }
      const wcx = (w / 2 - panRef.current.x) / scaleRef.current;
      const wcy = (h / 2 - panRef.current.y) / scaleRef.current;
      nodeMap.clear();
      nodes.forEach(n => nodeMap.set(n.slug, n));

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        if (a.pinned || leftDragRef.current?.node === a) continue;
        a.vx += (wcx - a.x) * CENTER_PULL;
        a.vy += (wcy - a.y) * CENTER_PULL;
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = REPULSION / (d * d);
          dx *= f / d; dy *= f / d;
          a.vx += dx; a.vy += dy;
          if (!b.pinned && leftDragRef.current?.node !== b) { b.vx -= dx; b.vy -= dy; }
        }
      }
      for (const e of edges) {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (d - SPRING_LEN) * SPRING_K;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        if (!a.pinned && leftDragRef.current?.node !== a) { a.vx += fx; a.vy += fy; }
        if (!b.pinned && leftDragRef.current?.node !== b) { b.vx -= fx; b.vy -= fy; }
      }
      for (const n of nodes) {
        if (n.pinned || leftDragRef.current?.node === n) continue;
        n.vx *= DAMPING; n.vy *= DAMPING; n.x += n.vx; n.y += n.vy;
      }

      const s = scaleRef.current;
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate(panRef.current.x, panRef.current.y);
      ctx.scale(s, s);

      // Edges
      for (const e of edges) {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) continue;
        ctx.strokeStyle = '#6366f1'; ctx.lineWidth = 2 / s;
        ctx.globalAlpha = 0.5;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        ctx.globalAlpha = 1;
        // Arrowhead
        const ang = Math.atan2(b.y - a.y, b.x - a.x);
        const ax = b.x - Math.cos(ang) * (b.radius + 2), ay = b.y - Math.sin(ang) * (b.radius + 2);
        ctx.fillStyle = '#6366f1';
        ctx.beginPath(); ctx.moveTo(ax, ay);
        ctx.lineTo(ax - Math.cos(ang - 0.4) * 8 / s, ay - Math.sin(ang - 0.4) * 8 / s);
        ctx.lineTo(ax - Math.cos(ang + 0.4) * 8 / s, ay - Math.sin(ang + 0.4) * 8 / s);
        ctx.fill();
      }

      // Link drag line
      const ld = linkDragRef.current;
      if (ld) {
        ctx.strokeStyle = ld.targetNode ? '#22c55e' : '#6366f1';
        ctx.lineWidth = 2 / s; ctx.setLineDash([5 / s, 3 / s]);
        ctx.beginPath(); ctx.moveTo(ld.source.x, ld.source.y); ctx.lineTo(ld.worldX, ld.worldY); ctx.stroke();
        ctx.setLineDash([]);
        if (ld.targetNode) {
          ctx.strokeStyle = '#22c55e'; ctx.lineWidth = 2.5 / s;
          ctx.beginPath(); ctx.arc(ld.targetNode.x, ld.targetNode.y, ld.targetNode.radius + 4, 0, Math.PI * 2); ctx.stroke();
        }
      }

      // Nodes (circle only, no text inside)
      for (const n of nodes) {
        const isActive = n.slug === activeSlug;
        const isHover = hoverRef.current === n;
        const isLinkTarget = ld?.targetNode === n;
        ctx.shadowColor = isActive ? 'rgba(99,102,241,0.4)' : 'rgba(0,0,0,0.05)';
        ctx.shadowBlur = isActive ? 10 : 2;
        ctx.fillStyle = isLinkTarget ? '#bbf7d0' : isActive ? '#6366f1' : isHover ? '#c7d2fe' : n.color;
        ctx.strokeStyle = isLinkTarget ? '#22c55e' : isActive ? '#4338ca' : isHover ? '#6366f1' : '#9ca3af';
        ctx.lineWidth = (isActive || isHover || isLinkTarget ? 2.5 : 1.2) / s;
        ctx.beginPath(); ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.shadowBlur = 0;
        // Full title above
        ctx.fillStyle = isActive ? '#4338ca' : '#334155';
        ctx.font = `500 ${Math.max(9, 10 / s)}px -apple-system, sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
        ctx.fillText(n.title, n.x, n.y - n.radius - 3 / s);
      }

      if (ld) {
        const label = ld.targetNode ? `→ ${ld.targetNode.title}` : '노드 위에서 놓기';
        ctx.fillStyle = ld.targetNode ? '#16a34a' : '#6366f1';
        ctx.font = `600 ${10 / s}px -apple-system, sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
        ctx.fillText(label, ld.worldX, ld.worldY - 10 / s);
      }

      ctx.restore();
      animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [loaded, activeSlug]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const p = canvas.parentElement?.getBoundingClientRect();
      if (p) { canvas.width = p.width; canvas.height = p.height; }
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  // ── Mouse handlers ──
  // Left-click = open note
  // Left-drag node → drop on empty = move node
  // Left-drag node → drop ON another node = CREATE LINK
  // Left-drag canvas = pan
  // Right-click = context menu
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setCtxMenu(null);
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const node = getNodeAt(mx, my);

    // Connect mode (from context menu "연결" button)
    if (connectMode && connectSourceRef.current && node && node !== connectSourceRef.current) {
      createLink(connectSourceRef.current, node);
      setConnectMode(false); connectSourceRef.current = null;
      return;
    }
    if (connectMode) { setConnectMode(false); connectSourceRef.current = null; }

    leftDragRef.current = { node, startX: mx, startY: my, moved: false, shift: false };
    if (node) { node.vx = 0; node.vy = 0; }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;

    if (leftDragRef.current && (e.buttons & 1)) {
      const ld = leftDragRef.current;
      const dx = mx - ld.startX, dy = my - ld.startY;
      if (Math.abs(dx) > CLICK_THRESHOLD || Math.abs(dy) > CLICK_THRESHOLD) ld.moved = true;
      if (ld.moved) {
        if (ld.node) {
          ld.node.x += e.movementX / scaleRef.current;
          ld.node.y += e.movementY / scaleRef.current;
          ld.node.vx = 0; ld.node.vy = 0;
          // Show link-drag visual when hovering over another node during drag
          const w = screenToWorld(mx, my);
          const target = getNodeAt(mx, my);
          const validTarget = (target && target !== ld.node) ? target : null;
          if (validTarget) {
            linkDragRef.current = { source: ld.node, worldX: w.x, worldY: w.y, targetNode: validTarget };
          } else {
            linkDragRef.current = null;
          }
        } else {
          panRef.current.x += e.movementX;
          panRef.current.y += e.movementY;
        }
      }
      if (canvasRef.current) {
        const target = ld.node ? getNodeAt(mx, my) : null;
        canvasRef.current.style.cursor =
          (target && target !== ld.node) ? 'crosshair' : ld.node ? 'grabbing' : 'move';
      }
      return;
    }

    hoverRef.current = getNodeAt(mx, my);
    if (canvasRef.current) canvasRef.current.style.cursor =
      connectMode ? 'crosshair' : hoverRef.current ? 'grab' : 'default';
  };

  const handleMouseUp = async (e: React.MouseEvent) => {
    linkDragRef.current = null; // clear link visual

    if (e.button !== 0 || !leftDragRef.current) return;
    const ld = leftDragRef.current;
    leftDragRef.current = null;
    if (canvasRef.current) canvasRef.current.style.cursor = 'default';

    if (!ld.moved && ld.node) {
      // Single click on node → no action (double-click to open)
      return;
    }

    if (ld.moved && ld.node) {
      // Check if dropped ON another node → create link
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const mx = e.clientX - rect.left, my = e.clientY - rect.top;
        const dropTarget = getNodeAt(mx, my);
        if (dropTarget && dropTarget !== ld.node) {
          // Drop on another node = create connection
          await createLink(ld.node, dropTarget);
          // Move the dragged node back (it was being dragged onto the target)
          return;
        }
      }
      // Drop on empty = pin node in place
      ld.node.pinned = true;
      ld.node.vx = 0; ld.node.vy = 0;
    }
  };

  // Right-click = context menu
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const node = getNodeAt(mx, my);
    if (node) {
      setCtxMenu({ x: e.clientX, y: e.clientY, node });
    }
  };

  const createLink = async (source: GraphNode, target: GraphNode) => {
    try {
      const srcNote = await api.getNote(projectName, source.slug);
      if (srcNote) {
        const link = `[[${target.title}]]`;
        if (!(srcNote.content || '').includes(link)) {
          await api.updateNote(projectName, source.slug, { content: (srcNote.content || '') + `\n\n${link}` });
          loadGraph();
        }
      }
    } catch {}
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const oldS = scaleRef.current;
    const newS = Math.min(3, Math.max(0.3, oldS * (e.deltaY > 0 ? 0.9 : 1.1)));
    panRef.current.x = mx - (mx - panRef.current.x) * (newS / oldS);
    panRef.current.y = my - (my - panRef.current.y) * (newS / oldS);
    scaleRef.current = newS;
  };

  return (
    <div className="w-full h-full relative bg-slate-50">
      <canvas ref={canvasRef} className="w-full h-full"
        onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}
        onDoubleClick={(e) => {
          const rect = canvasRef.current?.getBoundingClientRect();
          if (!rect) return;
          const node = getNodeAt(e.clientX - rect.left, e.clientY - rect.top);
          if (node) onNavigate(node.slug);
        }}
        onMouseLeave={() => { leftDragRef.current = null; hoverRef.current = null; }}
        onContextMenu={handleContextMenu} onWheel={handleWheel} />

      {!loaded && <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">그래프 로딩 중...</div>}
      {loaded && nodesRef.current.length === 0 && <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">노트를 생성하면 그래프가 표시됩니다</div>}

      <div className="absolute top-2 left-2 text-[10px] text-slate-400 bg-white/80 backdrop-blur px-2 py-1 rounded-lg">
        더블클릭: 열기 · 드래그: 이동 · 노드→노드 드래그: 연결 · 우클릭: 메뉴
      </div>

      {connectMode && (
        <div className="absolute top-2 right-2 text-xs text-indigo-600 bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-lg animate-pulse">
          🔗 연결할 노드를 클릭하세요
        </div>
      )}

      {/* Bottom controls */}
      <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between">
        <div className="flex items-center gap-2 bg-white/80 backdrop-blur px-2 py-1 rounded-lg">
          <span className="text-[10px] text-slate-400">크기</span>
          <input type="range" min="6" max="40" value={nodeRadius}
            onChange={e => setNodeRadius(Number(e.target.value))}
            className="w-20 h-1 accent-indigo-500" />
          <span className="text-[10px] text-slate-500 w-4">{nodeRadius}</span>
        </div>
        <div className="flex gap-1">
          <button onClick={() => nodesRef.current.forEach(n => { n.pinned = false; })}
            className="px-2 h-7 bg-white border border-slate-200 rounded-lg text-[10px] text-slate-500 hover:bg-slate-50">고정 해제</button>
          <button onClick={() => { scaleRef.current = 1; panRef.current = { x: 0, y: 0 }; }}
            className="px-2 h-7 bg-white border border-slate-200 rounded-lg text-[10px] text-slate-500 hover:bg-slate-50">리셋</button>
        </div>
      </div>

      {/* Node context menu */}
      {ctxMenu && createPortal(
        <div className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[150px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }} onClick={e => e.stopPropagation()}>
          <div className="px-3 py-1.5 text-xs font-semibold text-slate-700 border-b border-slate-100 mb-1">
            {ctxMenu.node.title}
          </div>
          {/* Color palette */}
          <div className="px-3 py-1.5">
            <div className="text-[10px] text-slate-400 mb-1">색상</div>
            <div className="flex flex-wrap gap-1">
              {PALETTE.map(c => (
                <button key={c}
                  onClick={() => { ctxMenu.node.color = c; setCtxMenu(null); }}
                  className="w-5 h-5 rounded-full border border-slate-200 hover:scale-125 transition-transform"
                  style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => {
              connectSourceRef.current = ctxMenu.node;
              setConnectMode(true);
              setCtxMenu(null);
            }}>
            🔗 다른 노트에 연결
          </button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { onNavigate(ctxMenu.node.slug); setCtxMenu(null); }}>
            📝 노트 열기
          </button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { ctxMenu.node.pinned = !ctxMenu.node.pinned; setCtxMenu(null); }}>
            📌 {ctxMenu.node.pinned ? '고정 해제' : '위치 고정'}
          </button>
        </div>,
        document.body
      )}
    </div>
  );
}
