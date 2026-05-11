import { useState, useEffect } from 'react';
import { NodeResizer, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

type GroupData = { label?: string };

export default function GroupNode({ id, data, selected }: NodeProps) {
  const d = (data || {}) as GroupData;
  const { setNodes } = useReactFlow();
  const [label, setLabel] = useState(d.label ?? '그룹');

  useEffect(() => { setLabel(d.label ?? '그룹'); }, [d.label]);

  const commit = () => {
    setNodes((nodes) => nodes.map((n) =>
      n.id === id ? { ...n, data: { ...(n.data || {}), label } } : n
    ));
  };

  return (
    <div
      className="w-full h-full rounded-xl border-2 border-dashed"
      style={{
        background: 'rgba(99, 102, 241, 0.04)',
        borderColor: selected ? '#6366f1' : 'rgba(99, 102, 241, 0.4)',
        minWidth: 240,
        minHeight: 160,
      }}
    >
      <NodeResizer minWidth={240} minHeight={160} isVisible={selected} lineStyle={{ borderColor: '#6366f1' }} handleStyle={{ background: '#6366f1', width: 8, height: 8 }} />

      <div className="absolute top-1.5 right-2 z-10">
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={commit}
          className="bg-white/80 px-2 py-0.5 rounded text-xs font-medium text-indigo-700 outline-none border border-indigo-200 max-w-[140px]"
        />
      </div>
    </div>
  );
}
