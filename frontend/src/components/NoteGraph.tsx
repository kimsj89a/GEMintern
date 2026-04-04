/**
 * NoteGraph — Force-directed graph of research notes.
 * Left-click = open note. Left-drag = move node (stays in place).
 * Right-drag from node to node = create [[wikilink]] connection.
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
  pinned: boolean; // true after user drag → skip forces
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

const REPULSION = 600;
const SPRING_K = 0.025;
const SPRING_LEN = 140;
const DAMPING = 0.88;
const CENTER_PULL = 0.003;
const MIN_RADIUS = 22;
const MAX_RADIUS = 36;
const CLICK_THRESHOLD = 5;

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
        const r = 80 + Math.random() * 100;
        const links = linkCount[n.slug] || 0;
        return {
          slug: n.slug, title: n.title,
          x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r,
          vx: 0, vy: 0, pinned: false,
          radius: Math.min(MAX_RADIUS, MIN_RADIUS + links * 3),
        };
      });
      edgesRef.current = data.edges;
      setLoaded(true);
    } catch {}
  }, [projectName]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

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
      const w = canvas.width, h = canvas.height;
      const cx = w / 2, cy = h / 2;
      nodeMap.clear();
      nodes.forEach(n => nodeMap.set(n.slug, n));

      // Forces (skip pinned and currently-dragged nodes)
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        if (a.pinned || dragRef.current?.node === a) continue;
        a.vx += (cx - a.x) * CENTER_PULL;
        a.vy += (cy - a.y) * CENTER_PULL;
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = REPULSION / (dist * dist);
          dx *= force / dist; dy *= force / dist;
          a.vx += dx; a.vy += dy;
          if (!b.pinned && dragRef.current?.node !== b) { b.vx -= dx; b.vy -= dy; }
        }
      }
      for (const e of edges) {
        const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
        if (!a || !b) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - SPRING_LEN) * SPRING_K;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        if (!a.pinned && dragRef.current?.node !== a) { a.vx += fx; a.vy += fy; }
        if (!b.pinned && dragRef.current?.node !== b) { b.vx -= fx; b.vy -= fy; }
      }
      for (const n of nodes) {
        if (n.pinned || dragRef.current?.node === n) continue;
        n.vx *= DAMPING; n.vy *= DAMPING;
        n.x += n.vx; n.y += n.vy;
      }

      // ── Draw ──
      const s = scaleRef.current;
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.scale(s, s);
      ctx.translate(panRef.current.x / s, panRef.current.y / s);

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

      // Right-drag link line
      if (linkDragRef.current) {
        const src = linkDragRef.current.source;
        const lmx = (linkDragRef.current.mx) / s - panRef.current.x / s;
        const lmy = (linkDragRef.current.my) / s - panRef.current.y / s;
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2.5 / s;
        ctx.setLineDash([6 / s, 4 / s]);
        ctx.beginPath(); ctx.moveTo(src.x, src.y); ctx.lineTo(lmx, lmy); ctx.stroke();
        ctx.setLineDash([]);
      }

      // Nodes
      for (const n of nodes) {
        const isActive = n.slug === activeSlug;
        const isHover = hoverRef.current === n;
        ctx.shadowColor = isActive ? 'rgba(99,102,241,0.3)' : 'rgba(0,0,0,0.06)';
        ctx.shadowBlur = isActive ? 12 : 3;
        ctx.fillStyle = isActive ? '#6366f1' : isHover ? '#818cf8' : '#ffffff';
        ctx.strokeStyle = isActive ? '#4f46e5' : isHover ? '#6366f1' : '#d1d5db';
        ctx.lineWidth = (isActive || isHover ? 2.5 : 1.5) / s;
        ctx.beginPath(); ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.shadowBlur = 0;

        // Short label inside circle
        ctx.fillStyle = isActive ? '#fff' : '#475569';
        const fontSize = Math.max(10, 11 / s);
        ctx.font = `600 ${fontSize}px -apple-system, sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        const shortLabel = n.title.length > 6 ? n.title.slice(0, 5) + '…' : n.title;
        ctx.fillText(shortLabel, n.x, n.y);

        // Full title above circle
        ctx.fillStyle = '#334155';
        ctx.font = `500 ${Math.max(9, 10 / s)}px -apple-system, sans-serif`;
        ctx.fillText(n.title, n.x, n.y - n.radius - 6 / s);
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
    const x = mx / s - panRef.current.x / s, y = my / s - panRef.current.y / s;
    for (const n of nodesRef.current) {
      const dx = x - n.x, dy = y - n.y;
      if (dx * dx + dy * dy < (n.radius + 4) * (n.radius + 4)) return n;
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const node = getNodeAt(mx, my);

    if (e.button === 0 && node) {
      // Left: prepare drag/click
      dragRef.current = { node, startX: mx, startY: my, moved: false };
      node.vx = 0; node.vy = 0;
    } else if (e.button === 2 && node) {
      // Right: start link creation
      linkDragRef.current = { source: node, mx, my };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;

    if (dragRef.current) {
      const dx = mx - dragRef.current.startX, dy = my - dragRef.current.startY;
      if (Math.abs(dx) > CLICK_THRESHOLD || Math.abs(dy) > CLICK_THRESHOLD) dragRef.current.moved = true;
      if (dragRef.current.moved) {
        const s = scaleRef.current;
        dragRef.current.node.x += e.movementX / s;
        dragRef.current.node.y += e.movementY / s;
        dragRef.current.node.vx = 0; dragRef.current.node.vy = 0;
      }
      return;
    }

    if (linkDragRef.current) {
      linkDragRef.current.mx = mx;
      linkDragRef.current.my = my;
      return;
    }

    hoverRef.current = getNodeAt(mx, my);
    if (canvasRef.current) canvasRef.current.style.cursor = hoverRef.current ? 'grab' : 'default';
  };

  const handleMouseUp = async (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;

    // Left button: click or drag-end
    if (e.button === 0 && dragRef.current) {
      if (!dragRef.current.moved) {
        onNavigate(dragRef.current.node.slug);
      } else {
        // Pin node so forces don't pull it back
        dragRef.current.node.pinned = true;
        dragRef.current.node.vx = 0;
        dragRef.current.node.vy = 0;
      }
      dragRef.current = null;
    }

    // Right button: complete link creation
    if (e.button === 2 && linkDragRef.current) {
      const target = getNodeAt(mx, my);
      if (target && target !== linkDragRef.current.source) {
        try {
          const srcNote = await api.getNote(projectName, linkDragRef.current.source.slug);
          if (srcNote) {
            const newContent = (srcNote.content || '') + `\n\n[[${target.title}]]`;
            await api.updateNote(projectName, linkDragRef.current.source.slug, { content: newContent });
            loadGraph();
          }
        } catch {}
      }
      linkDragRef.current = null;
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => { e.preventDefault(); };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    scaleRef.current = Math.min(3, Math.max(0.3, scaleRef.current * (e.deltaY > 0 ? 0.9 : 1.1)));
  };

  // Unpin all nodes
  const handleUnpinAll = () => { nodesRef.current.forEach(n => { n.pinned = false; }); };

  return (
    <div className="w-full h-full relative bg-slate-50">
      <canvas ref={canvasRef} className="w-full h-full"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => { dragRef.current = null; linkDragRef.current = null; hoverRef.current = null; }}
        onContextMenu={handleContextMenu}
        onWheel={handleWheel} />
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">그래프 로딩 중...</div>
      )}
      {loaded && nodesRef.current.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">노트를 생성하면 그래프가 표시됩니다</div>
      )}
      <div className="absolute top-2 left-2 text-[10px] text-slate-400 bg-white/80 px-2 py-1 rounded-lg">
        클릭: 열기 · 드래그: 이동 · 우클릭 드래그: 연결
      </div>
      <div className="absolute bottom-2 right-2 flex gap-1">
        <button onClick={handleUnpinAll}
          className="px-2 h-7 bg-white border border-slate-200 rounded-lg text-[10px] text-slate-500 hover:bg-slate-50">고정 해제</button>
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
