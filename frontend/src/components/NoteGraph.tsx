/**
 * NoteGraph — Force-directed graph of research notes.
 * Left-click drag = move node. Left-click release (no drag) = open note.
 * Right-click drag from node to node = create [[wikilink]] connection.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

interface GraphNode {
  slug: string;
  title: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

interface GraphEdge {
  source: string;
  target: string;
}

interface NoteGraphProps {
  projectName: string;
  activeSlug?: string | null;
  onNavigate: (slug: string) => void;
}

const REPULSION = 800;
const SPRING_K = 0.03;
const SPRING_LEN = 120;
const DAMPING = 0.85;
const CENTER_PULL = 0.01;
const MIN_RADIUS = 20;
const MAX_RADIUS = 34;
const CLICK_THRESHOLD = 6; // px — under this = click, over = drag

export default function NoteGraph({ projectName, activeSlug, onNavigate }: NoteGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const animRef = useRef<number>(0);
  const dragRef = useRef<{ node: GraphNode; startX: number; startY: number; moved: boolean } | null>(null);
  const linkDragRef = useRef<{ source: GraphNode; mx: number; my: number } | null>(null);
  const panRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);
  const hoverRef = useRef<GraphNode | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; node: GraphNode } | null>(null);

  const loadGraph = useCallback(async () => {
    try {
      const data = await api.getNoteGraph(projectName);
      const linkCount: Record<string, number> = {};
      for (const e of data.edges) {
        linkCount[e.source] = (linkCount[e.source] || 0) + 1;
        linkCount[e.target] = (linkCount[e.target] || 0) + 1;
      }
      const canvas = canvasRef.current;
      const cx = (canvas?.width || 600) / 2;
      const cy = (canvas?.height || 400) / 2;
      nodesRef.current = data.nodes.map((n: any, i: number) => {
        const angle = (2 * Math.PI * i) / Math.max(data.nodes.length, 1);
        const r = 100 + Math.random() * 80;
        const links = linkCount[n.slug] || 0;
        return {
          slug: n.slug, title: n.title,
          x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r,
          vx: 0, vy: 0,
          radius: Math.min(MAX_RADIUS, MIN_RADIUS + links * 3),
        };
      });
      edgesRef.current = data.edges;
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

  // ── Force simulation + render ──
  useEffect(() => {
    if (!loaded) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const nodeMap = new Map<string, GraphNode>();

    const tick = () => {
      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2 - panRef.current.x;
      const cy = h / 2 - panRef.current.y;
      nodeMap.clear();
      nodes.forEach(n => nodeMap.set(n.slug, n));

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        if (dragRef.current?.node === a) continue;
        a.vx += (cx - a.x) * CENTER_PULL;
        a.vy += (cy - a.y) * CENTER_PULL;
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = REPULSION / (dist * dist);
          dx *= force / dist; dy *= force / dist;
          a.vx += dx; a.vy += dy;
          if (dragRef.current?.node !== b) { b.vx -= dx; b.vy -= dy; }
        }
      }
      for (const e of edges) {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - SPRING_LEN) * SPRING_K;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        if (dragRef.current?.node !== a) { a.vx += fx; a.vy += fy; }
        if (dragRef.current?.node !== b) { b.vx -= fx; b.vy -= fy; }
      }
      for (const n of nodes) {
        if (dragRef.current?.node === n) continue;
        n.vx *= DAMPING; n.vy *= DAMPING;
        n.x += n.vx; n.y += n.vy;
      }

      // ── Draw ──
      const s = scaleRef.current;
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate(panRef.current.x, panRef.current.y);
      ctx.scale(s, s);

      // Edges
      ctx.lineWidth = 1.5 / s;
      for (const e of edges) {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) continue;
        ctx.strokeStyle = '#cbd5e1';
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        const angle = Math.atan2(b.y - a.y, b.x - a.x);
        const ax = b.x - Math.cos(angle) * b.radius, ay = b.y - Math.sin(angle) * b.radius;
        ctx.fillStyle = '#94a3b8';
        ctx.beginPath(); ctx.moveTo(ax, ay);
        ctx.lineTo(ax - Math.cos(angle - 0.4) * 8 / s, ay - Math.sin(angle - 0.4) * 8 / s);
        ctx.lineTo(ax - Math.cos(angle + 0.4) * 8 / s, ay - Math.sin(angle + 0.4) * 8 / s);
        ctx.fill();
      }

      // Right-click drag line (link creation)
      if (linkDragRef.current) {
        const src = linkDragRef.current.source;
        const lmx = (linkDragRef.current.mx - panRef.current.x) / s;
        const lmy = (linkDragRef.current.my - panRef.current.y) / s;
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2 / s;
        ctx.setLineDash([6 / s, 4 / s]);
        ctx.beginPath(); ctx.moveTo(src.x, src.y); ctx.lineTo(lmx, lmy); ctx.stroke();
        ctx.setLineDash([]);
      }

      // Nodes
      for (const n of nodes) {
        const isActive = n.slug === activeSlug;
        const isHover = hoverRef.current === n;
        ctx.shadowColor = isActive ? 'rgba(99,102,241,0.3)' : 'rgba(0,0,0,0.08)';
        ctx.shadowBlur = isActive ? 12 : 4;
        ctx.fillStyle = isActive ? '#6366f1' : isHover ? '#818cf8' : '#f8fafc';
        ctx.strokeStyle = isActive ? '#4f46e5' : isHover ? '#6366f1' : '#e2e8f0';
        ctx.lineWidth = (isActive || isHover ? 2.5 : 1.5) / s;
        ctx.beginPath(); ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.fillStyle = isActive ? '#fff' : '#334155';
        ctx.font = `${Math.max(10, 11 / s)}px -apple-system, sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        const label = n.title.length > 8 ? n.title.slice(0, 7) + '…' : n.title;
        ctx.fillText(label, n.x, n.y);
      }
      ctx.restore();
      animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [loaded, activeSlug]);

  // Resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) { canvas.width = rect.width; canvas.height = rect.height; }
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  const getNodeAt = (mx: number, my: number): GraphNode | null => {
    const s = scaleRef.current;
    const x = (mx - panRef.current.x) / s, y = (my - panRef.current.y) / s;
    for (const n of nodesRef.current) {
      const dx = x - n.x, dy = y - n.y;
      if (dx * dx + dy * dy < n.radius * n.radius) return n;
    }
    return null;
  };

  // ── Left click: drag node, release without move = navigate ──
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // left only
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const node = getNodeAt(mx, my);
    if (node) {
      dragRef.current = {
        node,
        startX: mx, startY: my, moved: false,
      };
      node.vx = 0; node.vy = 0;
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;

    // Left drag: move node
    if (dragRef.current) {
      const dx = mx - dragRef.current.startX, dy = my - dragRef.current.startY;
      if (Math.abs(dx) > CLICK_THRESHOLD || Math.abs(dy) > CLICK_THRESHOLD) dragRef.current.moved = true;
      if (dragRef.current.moved) {
        const s = scaleRef.current;
        dragRef.current.node.x += (e.movementX) / s;
        dragRef.current.node.y += (e.movementY) / s;
        dragRef.current.node.vx = 0; dragRef.current.node.vy = 0;
      }
      return;
    }

    // Right drag: draw link line
    if (linkDragRef.current) {
      linkDragRef.current.mx = mx;
      linkDragRef.current.my = my;
      const target = getNodeAt(mx, my);
      if (canvasRef.current) canvasRef.current.style.cursor = (target && target !== linkDragRef.current.source) ? 'crosshair' : 'default';
      return;
    }

    const node = getNodeAt(mx, my);
    hoverRef.current = node;
    if (canvasRef.current) canvasRef.current.style.cursor = node ? 'grab' : 'default';
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (e.button === 0 && dragRef.current) {
      if (!dragRef.current.moved) {
        // Click (no drag) → navigate
        onNavigate(dragRef.current.node.slug);
      }
      dragRef.current = null;
    }
  };

  // ── Right click: context menu or link drag ──
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const node = getNodeAt(mx, my);
    if (node) {
      // Start link drag on right-press
      linkDragRef.current = { source: node, mx, my };
      setCtxMenu(null);
    }
  };

  const handleMouseUpRight = async (e: React.MouseEvent) => {
    if (linkDragRef.current) {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const mx = e.clientX - rect.left, my = e.clientY - rect.top;
        const target = getNodeAt(mx, my);
        if (target && target !== linkDragRef.current.source) {
          // Create link: append [[target]] to source note
          try {
            const srcNote = await api.getNote(projectName, linkDragRef.current.source.slug);
            if (srcNote) {
              const newContent = srcNote.content + `\n\n[[${target.title}]]`;
              await api.updateNote(projectName, linkDragRef.current.source.slug, { content: newContent });
              loadGraph(); // refresh
            }
          } catch {}
        }
      }
      linkDragRef.current = null;
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    scaleRef.current = Math.min(3, Math.max(0.3, scaleRef.current * (e.deltaY > 0 ? 0.9 : 1.1)));
  };

  return (
    <div className="w-full h-full relative bg-slate-50">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={(e) => { handleMouseUp(e); handleMouseUpRight(e); }}
        onMouseLeave={() => { dragRef.current = null; linkDragRef.current = null; hoverRef.current = null; }}
        onContextMenu={handleContextMenu}
        onWheel={handleWheel}
      />
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">그래프 로딩 중...</div>
      )}
      {loaded && nodesRef.current.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">노트를 생성하면 그래프가 표시됩니다</div>
      )}
      {/* Help text */}
      <div className="absolute top-2 left-2 text-[10px] text-slate-400 bg-white/80 px-2 py-1 rounded-lg">
        클릭: 노트 열기 · 드래그: 이동 · 우클릭 드래그: 연결
      </div>
      <div className="absolute bottom-2 right-2 flex gap-1">
        <button onClick={() => { scaleRef.current = Math.min(3, scaleRef.current * 1.2); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 text-sm font-bold">+</button>
        <button onClick={() => { scaleRef.current = Math.max(0.3, scaleRef.current * 0.8); }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 text-sm font-bold">-</button>
        <button onClick={() => { scaleRef.current = 1; panRef.current = { x: 0, y: 0 }; }}
          className="w-7 h-7 bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-slate-50 text-[10px]">1:1</button>
      </div>
    </div>
  );
}
