import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  addEdge,
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import BoxNode from '../components/dealstructure/BoxNode';
import TableNode from '../components/dealstructure/TableNode';
import TextNode from '../components/dealstructure/TextNode';
import GroupNode from '../components/dealstructure/GroupNode';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

function DealStructureCanvas({ project }: { project: string }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [viewport, setViewport] = useState<{ x: number; y: number; zoom: number } | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [savedAt, setSavedAt] = useState<string>('');
  const [loaded, setLoaded] = useState(false);
  const { screenToFlowPosition } = useReactFlow();

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const skipSaveRef = useRef(true);
  const idCounterRef = useRef(0);

  const nodeTypes = useMemo(() => ({
    box: BoxNode,
    table: TableNode,
    text: TextNode,
    group: GroupNode,
  }), []);

  // Initial load
  useEffect(() => {
    if (!project) return;
    skipSaveRef.current = true;
    setLoaded(false);
    api.getDealStructure(project)
      .then((res) => {
        setNodes((res?.nodes ?? []) as Node[]);
        setEdges((res?.edges ?? []) as Edge[]);
        if (res?.viewport) setViewport(res.viewport);
        setLoaded(true);
        // Allow saves after the initial render commits
        setTimeout(() => { skipSaveRef.current = false; }, 200);
      })
      .catch(() => {
        setLoaded(true);
        setTimeout(() => { skipSaveRef.current = false; }, 200);
      });
  }, [project, setNodes, setEdges]);

  const doSave = useCallback(async () => {
    if (!project) return;
    setSaveStatus('saving');
    try {
      const res = await api.saveDealStructure(project, {
        nodes,
        edges,
        viewport,
        version: 1,
      });
      const ts = res?.updated_at ? new Date(res.updated_at) : new Date();
      const hh = String(ts.getHours()).padStart(2, '0');
      const mm = String(ts.getMinutes()).padStart(2, '0');
      setSavedAt(`${hh}:${mm}`);
      setSaveStatus('saved');
    } catch {
      setSaveStatus('error');
    }
  }, [project, nodes, edges, viewport]);

  // Debounced auto-save on changes
  useEffect(() => {
    if (skipSaveRef.current || !loaded) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { doSave(); }, 1500);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [nodes, edges, viewport, loaded, doSave]);

  const onConnect = useCallback((conn: Connection) => {
    setEdges((eds) => addEdge({ ...conn, animated: false, style: { stroke: '#64748b', strokeWidth: 1.5 } }, eds));
  }, [setEdges]);

  const nextId = () => {
    idCounterRef.current += 1;
    return `n_${Date.now().toString(36)}_${idCounterRef.current}`;
  };

  const addNode = (type: 'box' | 'table' | 'text' | 'group') => {
    const center = screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
    const id = nextId();
    const baseData =
      type === 'box'   ? { title: '제목', body: '내용', color: 'blue' } :
      type === 'table' ? { title: '표', headers: ['항목', '값'], rows: [['', ''], ['', '']] } :
      type === 'text'  ? { text: '메모' } :
                         { label: '그룹' };
    const size =
      type === 'box'   ? { width: 220, height: 120 } :
      type === 'table' ? { width: 320, height: 180 } :
      type === 'text'  ? { width: 180, height: 60 } :
                         { width: 320, height: 220 };
    const newNode: Node = {
      id,
      type,
      position: center,
      data: baseData,
      ...size,
      ...(type === 'group' ? { style: { zIndex: -1 } } : {}),
    };
    setNodes((nds) => nds.concat(newNode));
  };

  const statusBadge = () => {
    if (saveStatus === 'saving') return <span className="text-xs text-amber-600">● 저장 중...</span>;
    if (saveStatus === 'saved')  return <span className="text-xs text-emerald-600">✓ 저장됨 {savedAt}</span>;
    if (saveStatus === 'error')  return <span className="text-xs text-rose-600">⚠ 저장 실패</span>;
    return <span className="text-xs text-slate-400">대기 중</span>;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 bg-white">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-slate-800">🏗️ 딜 구조 — {project}</h1>
          {statusBadge()}
        </div>
        <button
          onClick={doSave}
          className="px-3 py-1.5 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors"
        >
          즉시 저장
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 px-5 py-2 border-b border-slate-200 bg-slate-50">
        <span className="text-xs text-slate-500 mr-2">노드 추가:</span>
        <button onClick={() => addNode('box')}   className="px-3 py-1 text-xs rounded-md bg-white border border-slate-300 hover:bg-blue-50 hover:border-blue-400 transition-colors">➕ 박스</button>
        <button onClick={() => addNode('table')} className="px-3 py-1 text-xs rounded-md bg-white border border-slate-300 hover:bg-blue-50 hover:border-blue-400 transition-colors">➕ 표</button>
        <button onClick={() => addNode('text')}  className="px-3 py-1 text-xs rounded-md bg-white border border-slate-300 hover:bg-blue-50 hover:border-blue-400 transition-colors">➕ 텍스트</button>
        <button onClick={() => addNode('group')} className="px-3 py-1 text-xs rounded-md bg-white border border-slate-300 hover:bg-blue-50 hover:border-blue-400 transition-colors">➕ 그룹</button>
      </div>

      {/* Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          onMoveEnd={(_e, vp) => setViewport(vp)}
          defaultViewport={viewport ?? { x: 0, y: 0, zoom: 1 }}
          fitView={!viewport}
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={16} size={1} color="#cbd5e1" />
          <Controls />
          <MiniMap pannable zoomable nodeStrokeWidth={2} />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function DealStructurePage() {
  const currentProject = useAppStore((s) => s.currentProject);

  if (!currentProject) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500">
        <div className="text-4xl mb-3">🏗️</div>
        <div className="text-sm">프로젝트를 먼저 선택해주세요.</div>
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <DealStructureCanvas project={currentProject} />
    </ReactFlowProvider>
  );
}
