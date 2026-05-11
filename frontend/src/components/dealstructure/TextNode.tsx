import { useState, useEffect, useRef } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

type TextData = { text?: string };

export default function TextNode({ id, data, selected }: NodeProps) {
  const d = (data || {}) as TextData;
  const { setNodes } = useReactFlow();
  const [text, setText] = useState(d.text ?? '메모...');
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { setText(d.text ?? '메모...'); }, [d.text]);

  // Auto-resize textarea
  useEffect(() => {
    if (taRef.current) {
      taRef.current.style.height = 'auto';
      taRef.current.style.height = `${taRef.current.scrollHeight}px`;
    }
  }, [text]);

  const commit = () => {
    setNodes((nodes) => nodes.map((n) =>
      n.id === id ? { ...n, data: { ...(n.data || {}), text } } : n
    ));
  };

  return (
    <div className={`p-2 rounded ${selected ? 'ring-2 ring-blue-400' : ''}`} style={{ minWidth: 120 }}>
      <Handle type="target" position={Position.Top} id="t" style={{ background: '#94a3b8', opacity: 0.6 }} />
      <Handle type="source" position={Position.Top} id="t-src" style={{ background: '#94a3b8', opacity: 0 }} />
      <Handle type="target" position={Position.Right} id="r" style={{ background: '#94a3b8', opacity: 0.6 }} />
      <Handle type="source" position={Position.Right} id="r-src" style={{ background: '#94a3b8', opacity: 0 }} />
      <Handle type="target" position={Position.Bottom} id="b" style={{ background: '#94a3b8', opacity: 0.6 }} />
      <Handle type="source" position={Position.Bottom} id="b-src" style={{ background: '#94a3b8', opacity: 0 }} />
      <Handle type="target" position={Position.Left} id="l" style={{ background: '#94a3b8', opacity: 0.6 }} />
      <Handle type="source" position={Position.Left} id="l-src" style={{ background: '#94a3b8', opacity: 0 }} />

      <textarea
        ref={taRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={commit}
        className="w-full bg-transparent outline-none resize-none text-sm text-slate-700 leading-relaxed"
        rows={1}
      />
    </div>
  );
}
