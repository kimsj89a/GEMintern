/**
 * NoteGraph — Force-directed graph of research notes.
 * Nodes = notes, edges = [[wikilink]] connections.
 * Canvas-based, no external dependencies.
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

// ── Force simulation parameters ──
const REPULSION = 800;
const SPRING_K = 0.03;
const SPRING_LEN = 120;
const DAMPING = 0.85;
const CENTER_PULL = 0.01;
const MIN_RADIUS = 18;
const MAX_RADIUS = 32;

export default function NoteGraph({ projectName, activeSlug, onNavigate }: NoteGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const animRef = useRef<number>(0);
  const dragRef = useRef<{ node: GraphNode; offsetX: number; offsetY: number } | null>(null);
  const panRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);
  const hoverRef = useRef<GraphNode | null>(null);
  const [loaded, setLoaded] = useState(false);

  // ── Load graph data ──
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
          slug: n.slug,
          title: n.title,
          x: cx + Math.cos(angle) * r,
          y: cy + Math.sin(angle) * r,
          vx: 0,
          vy: 0,
          radius: Math.min(MAX_RADIUS, MIN_RADIUS + links * 3),
        };
      });
      edgesRef.current = data.edges;
      setLoaded(true);
    } catch {}
  }, [projectName]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  // ── Force simulation + render loop ──
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

      // Forces
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        if (dragRef.current?.node === a) continue;
        // Center pull
        a.vx += (cx - a.x) * CENTER_PULL;
        a.vy += (cy - a.y) * CENTER_PULL;
        // Repulsion
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          let dx = a.x - b.x;
          let dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = REPULSION / (dist * dist);
          dx *= force / dist;
          dy *= force / dist;
          a.vx += dx; a.vy += dy;
          if (dragRef.current?.node !== b) { b.vx -= dx; b.vy -= dy; }
        }
      }
      // Spring (edges)
      for (const e of edges) {
        const a = nodeMap.get(e.source);
        const b = nodeMap.get(e.target);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - SPRING_LEN) * SPRING_K;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (dragRef.current?.node !== a) { a.vx += fx; a.vy += fy; }
        if (dragRef.current?.node !== b) { b.vx -= fx; b.vy -= fy; }
      }
      // Integrate
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
        const a = nodeMap.get(e.source);
        const b = nodeMap.get(e.target);
        if (!a || !b) continue;
        ctx.strokeStyle = '#cbd5e1';
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        // Arrow
        const angle = Math.atan2(b.y - a.y, b.x - a.x);
        const arrowX = b.x - Math.cos(angle) * b.radius;
        const arrowY = b.y - Math.sin(angle) * b.radius;
        ctx.fillStyle = '#94a3b8';
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(arrowX - Math.cos(angle - 0.4) * 8 / s, arrowY - Math.sin(angle - 0.4) * 8 / s);
        ctx.lineTo(arrowX - Math.cos(angle + 0.4) * 8 / s, arrowY - Math.sin(angle + 0.4) * 8 / s);
        ctx.fill();
      }

      // Nodes
      for (const n of nodes) {
        const isActive = n.slug === activeSlug;
        const isHover = hoverRef.current === n;
        // Shadow
        ctx.shadowColor = isActive ? 'rgba(99,102,241,0.3)' : 'rgba(0,0,0,0.1)';
        ctx.shadowBlur = isActive ? 12 : 6;
        // Circle
        ctx.fillStyle = isActive ? '#6366f1' : isHover ? '#818cf8' : '#f8fafc';
        ctx.strokeStyle = isActive ? '#4f46e5' : isHover ? '#6366f1' : '#e2e8f0';
        ctx.lineWidth = (isActive || isHover ? 2.5 : 1.5) / s;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.shadowBlur = 0;
        // Label
        ctx.fillStyle = isActive ? '#fff' : '#334155';
        ctx.font = `${Math.max(10, 11 / s)}px -apple-system, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const label = n.title.length > 8 ? n.title.slice(0, 7) + '…' : n.title;
        ctx.fillText(label, n.x, n.y);
      }
      ctx.restore();
      animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [loaded, activeSlug]);

  // ── Resize ──
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  // ── Mouse interactions ──
  const getNodeAt = (mx: number, my: number): GraphNode | null => {
    const s = scaleRef.current;
    const x = (mx - panRef.current.x) / s;
    const y = (my - panRef.current.y) / s;
    for (const n of nodesRef.current) {
      const dx = x - n.x;
      const dy = y - n.y;
      if (dx * dx + dy * dy < n.radius * n.radius) return n;
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const node = getNodeAt(mx, my);
    if (node) {
      const s = scaleRef.current;
      dragRef.current = { node, offsetX: (mx - panRef.current.x) / s - node.x, offsetY: (my - panRef.current.y) / s - node.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    if (dragRef.current) {
      const s = scaleRef.current;
      dragRef.current.node.x = (mx - panRef.current.x) / s - dragRef.current.offsetX;
      dragRef.current.node.y = (my - panRef.current.y) / s - dragRef.current.offsetY;
      dragRef.current.node.vx = 0;
      dragRef.current.node.vy = 0;
    } else {
      const node = getNodeAt(mx, my);
      hoverRef.current = node;
      if (canvasRef.current) canvasRef.current.style.cursor = node ? 'pointer' : 'default';
    }
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (dragRef.current) {
      // Check if it was a click (not a drag)
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        const node = getNodeAt(mx, my);
        if (node && node === dragRef.current.node) {
          onNavigate(node.slug);
        }
      }
      dragRef.current = null;
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    scaleRef.current = Math.min(3, Math.max(0.3, scaleRef.current * delta));
  };

  return (
    <div className="w-full h-full relative bg-slate-50">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => { dragRef.current = null; hoverRef.current = null; }}
        onWheel={handleWheel}
      />
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
          그래프 로딩 중...
        </div>
      )}
      {loaded && nodesRef.current.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
          노트를 생성하면 그래프가 표시됩니다
        </div>
      )}
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
