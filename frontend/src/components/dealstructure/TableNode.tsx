import { useState, useEffect } from 'react';
import { Handle, Position, NodeResizer, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

type TableData = {
  title?: string;
  headers?: string[];
  rows?: string[][];
};

export default function TableNode({ id, data, selected }: NodeProps) {
  const d = (data || {}) as TableData;
  const { setNodes } = useReactFlow();

  const [title, setTitle] = useState(d.title ?? '표');
  const [headers, setHeaders] = useState<string[]>(d.headers ?? ['항목', '값']);
  const [rows, setRows] = useState<string[][]>(d.rows ?? [['', '']]);

  useEffect(() => { setTitle(d.title ?? '표'); }, [d.title]);
  useEffect(() => { if (d.headers) setHeaders(d.headers); }, [d.headers]);
  useEffect(() => { if (d.rows) setRows(d.rows); }, [d.rows]);

  const commit = (next: Partial<TableData>) => {
    setNodes((nodes) => nodes.map((n) =>
      n.id === id ? { ...n, data: { ...(n.data || {}), ...next } } : n
    ));
  };

  const updateHeader = (col: number, val: string) => {
    const next = [...headers];
    next[col] = val;
    setHeaders(next);
    commit({ headers: next });
  };

  const updateCell = (r: number, c: number, val: string) => {
    const next = rows.map((row) => [...row]);
    next[r][c] = val;
    setRows(next);
    commit({ rows: next });
  };

  const addRow = () => {
    const next = [...rows, headers.map(() => '')];
    setRows(next);
    commit({ rows: next });
  };

  const removeRow = () => {
    if (rows.length <= 1) return;
    const next = rows.slice(0, -1);
    setRows(next);
    commit({ rows: next });
  };

  const addCol = () => {
    const nextHeaders = [...headers, ''];
    const nextRows = rows.map((row) => [...row, '']);
    setHeaders(nextHeaders);
    setRows(nextRows);
    commit({ headers: nextHeaders, rows: nextRows });
  };

  const removeCol = () => {
    if (headers.length <= 1) return;
    const nextHeaders = headers.slice(0, -1);
    const nextRows = rows.map((row) => row.slice(0, -1));
    setHeaders(nextHeaders);
    setRows(nextRows);
    commit({ headers: nextHeaders, rows: nextRows });
  };

  return (
    <div className="rounded-lg shadow-sm bg-white border-2 border-slate-300 w-full h-full flex flex-col overflow-hidden" style={{ minWidth: 240, minHeight: 120 }}>
      <NodeResizer minWidth={240} minHeight={120} isVisible={selected} lineStyle={{ borderColor: '#64748b' }} handleStyle={{ background: '#64748b', width: 8, height: 8 }} />

      <Handle type="target" position={Position.Top} id="t" style={{ background: '#64748b' }} />
      <Handle type="source" position={Position.Top} id="t-src" style={{ background: '#64748b', opacity: 0 }} />
      <Handle type="target" position={Position.Right} id="r" style={{ background: '#64748b' }} />
      <Handle type="source" position={Position.Right} id="r-src" style={{ background: '#64748b', opacity: 0 }} />
      <Handle type="target" position={Position.Bottom} id="b" style={{ background: '#64748b' }} />
      <Handle type="source" position={Position.Bottom} id="b-src" style={{ background: '#64748b', opacity: 0 }} />
      <Handle type="target" position={Position.Left} id="l" style={{ background: '#64748b' }} />
      <Handle type="source" position={Position.Left} id="l-src" style={{ background: '#64748b', opacity: 0 }} />

      <div className="px-3 py-2 border-b border-slate-200 bg-slate-50">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => commit({ title })}
          className="w-full bg-transparent outline-none font-semibold text-sm text-slate-700"
        />
      </div>

      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100">
              {headers.map((h, c) => (
                <th key={c} className="border border-slate-200 px-2 py-1 font-semibold text-slate-700 text-left">
                  <input
                    value={h}
                    onChange={(e) => updateHeader(c, e.target.value)}
                    className="w-full bg-transparent outline-none font-semibold"
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, r) => (
              <tr key={r}>
                {row.map((cell, c) => (
                  <td key={c} className="border border-slate-200 px-2 py-1">
                    <input
                      value={cell}
                      onChange={(e) => updateCell(r, c, e.target.value)}
                      className="w-full bg-transparent outline-none"
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="flex gap-1 px-2 py-1 border-t border-slate-200 bg-slate-50 text-[10px]">
          <button onClick={(e) => { e.stopPropagation(); addRow(); }} className="px-2 py-0.5 rounded bg-white border border-slate-300 hover:bg-slate-100">+ 행</button>
          <button onClick={(e) => { e.stopPropagation(); removeRow(); }} className="px-2 py-0.5 rounded bg-white border border-slate-300 hover:bg-slate-100">- 행</button>
          <button onClick={(e) => { e.stopPropagation(); addCol(); }} className="px-2 py-0.5 rounded bg-white border border-slate-300 hover:bg-slate-100">+ 열</button>
          <button onClick={(e) => { e.stopPropagation(); removeCol(); }} className="px-2 py-0.5 rounded bg-white border border-slate-300 hover:bg-slate-100">- 열</button>
        </div>
      )}
    </div>
  );
}
