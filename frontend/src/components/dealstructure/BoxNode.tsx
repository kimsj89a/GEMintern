import { useState, useEffect, useRef } from 'react';
import { Handle, Position, NodeResizer, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

const PALETTE: Record<string, { bg: string; border: string; text: string }> = {
  blue:   { bg: '#eff6ff', border: '#3b82f6', text: '#1e3a8a' },
  green:  { bg: '#ecfdf5', border: '#10b981', text: '#064e3b' },
  amber:  { bg: '#fffbeb', border: '#f59e0b', text: '#78350f' },
  rose:   { bg: '#fff1f2', border: '#f43f5e', text: '#881337' },
  violet: { bg: '#f5f3ff', border: '#8b5cf6', text: '#4c1d95' },
  slate:  { bg: '#f8fafc', border: '#64748b', text: '#1e293b' },
};

type BoxData = {
  title?: string;
  body?: string;
  color?: keyof typeof PALETTE;
};

export default function BoxNode({ id, data, selected }: NodeProps) {
  const d = (data || {}) as BoxData;
  const color = (d.color && PALETTE[d.color]) ? d.color : 'blue';
  const palette = PALETTE[color];
  const { setNodes } = useReactFlow();

  const [editingField, setEditingField] = useState<'title' | 'body' | null>(null);
  const [title, setTitle] = useState(d.title ?? '제목');
  const [body, setBody] = useState(d.body ?? '');
  const titleRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { setTitle(d.title ?? '제목'); }, [d.title]);
  useEffect(() => { setBody(d.body ?? ''); }, [d.body]);

  useEffect(() => {
    if (editingField === 'title' && titleRef.current) titleRef.current.focus();
    if (editingField === 'body' && bodyRef.current) bodyRef.current.focus();
  }, [editingField]);

  const commit = (field: 'title' | 'body', value: string) => {
    setNodes((nodes) => nodes.map((n) =>
      n.id === id ? { ...n, data: { ...(n.data || {}), [field]: value } } : n
    ));
    setEditingField(null);
  };

  const setColor = (c: keyof typeof PALETTE) => {
    setNodes((nodes) => nodes.map((n) =>
      n.id === id ? { ...n, data: { ...(n.data || {}), color: c } } : n
    ));
  };

  return (
    <div
      className="rounded-lg shadow-sm w-full h-full flex flex-col overflow-hidden"
      style={{ background: palette.bg, border: `2px solid ${palette.border}`, color: palette.text, minWidth: 160, minHeight: 80 }}
    >
      <NodeResizer minWidth={160} minHeight={80} isVisible={selected} lineStyle={{ borderColor: palette.border }} handleStyle={{ background: palette.border, width: 8, height: 8 }} />

      <Handle type="target" position={Position.Top} id="t" style={{ background: palette.border }} />
      <Handle type="source" position={Position.Top} id="t-src" style={{ background: palette.border, opacity: 0 }} />
      <Handle type="target" position={Position.Right} id="r" style={{ background: palette.border }} />
      <Handle type="source" position={Position.Right} id="r-src" style={{ background: palette.border, opacity: 0 }} />
      <Handle type="target" position={Position.Bottom} id="b" style={{ background: palette.border }} />
      <Handle type="source" position={Position.Bottom} id="b-src" style={{ background: palette.border, opacity: 0 }} />
      <Handle type="target" position={Position.Left} id="l" style={{ background: palette.border }} />
      <Handle type="source" position={Position.Left} id="l-src" style={{ background: palette.border, opacity: 0 }} />

      <div className="px-3 py-2 border-b" style={{ borderColor: palette.border, background: 'rgba(255,255,255,0.4)' }}>
        {editingField === 'title' ? (
          <input
            ref={titleRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={() => commit('title', title)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); commit('title', title); } }}
            className="w-full bg-transparent outline-none font-semibold text-sm"
            style={{ color: palette.text }}
          />
        ) : (
          <div onDoubleClick={() => setEditingField('title')} className="font-semibold text-sm cursor-text truncate">
            {title || '제목'}
          </div>
        )}
      </div>

      <div className="flex-1 px-3 py-2">
        {editingField === 'body' ? (
          <textarea
            ref={bodyRef}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onBlur={() => commit('body', body)}
            className="w-full h-full bg-transparent outline-none resize-none text-xs leading-relaxed"
            style={{ color: palette.text }}
          />
        ) : (
          <div onDoubleClick={() => setEditingField('body')} className="text-xs leading-relaxed cursor-text whitespace-pre-wrap">
            {body || <span className="opacity-50">더블클릭하여 편집</span>}
          </div>
        )}
      </div>

      {selected && (
        <div className="flex gap-1 px-2 py-1 border-t" style={{ borderColor: palette.border, background: 'rgba(255,255,255,0.5)' }}>
          {(Object.keys(PALETTE) as (keyof typeof PALETTE)[]).map((c) => (
            <button
              key={c}
              onClick={(e) => { e.stopPropagation(); setColor(c); }}
              title={c}
              className={`w-4 h-4 rounded-full ${color === c ? 'ring-2 ring-offset-1 ring-slate-700' : ''}`}
              style={{ background: PALETTE[c].border }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
