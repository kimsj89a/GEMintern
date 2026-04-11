/**
 * TimelinePanel — 3-section layout:
 *   Top: Mini calendar
 *   Middle: Gantt chart (horizontal bars)
 *   Bottom: Kanban board (작업예정/진행중/완료)
 */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';

interface TEvent {
  id: number; title: string; content: string;
  event_date: string; end_date: string | null;
  color: string;
}

const STATUSES = [
  { id: 'todo', label: '작업 예정', dot: 'bg-red-400' },
  { id: 'doing', label: '진행 중', dot: 'bg-amber-400' },
  { id: 'done', label: '완료', dot: 'bg-green-400' },
];
const COLORS = ['#6366f1', '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

function getStatus(ev: TEvent): string {
  if (ev.content?.includes('#done') || ev.content?.includes('#완료')) return 'done';
  if (ev.content?.includes('#doing') || ev.content?.includes('#진행')) return 'doing';
  return 'todo';
}

// daysBetween removed — not used

export default function TimelinePanel({ projectName }: { projectName: string }) {
  const [events, setEvents] = useState<TEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const today = new Date();
  const [calYear, setCalYear] = useState(today.getFullYear());
  const [calMonth, setCalMonth] = useState(today.getMonth());
  const [editId, setEditId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editStart, setEditStart] = useState('');
  const [editEnd, setEditEnd] = useState('');
  const [dragId, setDragId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try { setEvents(await api.listTimeline(projectName)); } catch {}
    setLoading(false);
  }, [projectName]);
  useEffect(() => { load(); }, [load]);

  const todayStr = today.toISOString().slice(0, 10);
  const handleCreate = async (status: string) => {
    const tag = status === 'doing' ? '#doing' : status === 'done' ? '#done' : '';
    const ev = await api.createTimelineEvent(projectName, {
      title: '새 작업', content: tag, event_date: todayStr,
      end_date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
      color: COLORS[events.length % COLORS.length],
    });
    if (ev?.id) { await load(); startEdit(ev); }
  };

  const startEdit = (ev: TEvent) => {
    setEditId(ev.id); setEditTitle(ev.title); setEditContent(ev.content);
    setEditStart(ev.event_date); setEditEnd(ev.end_date || ev.event_date);
  };

  const handleSave = async () => {
    if (!editId) return;
    await api.updateTimelineEvent(projectName, editId, { title: editTitle, content: editContent, event_date: editStart, end_date: editEnd });
    setEditId(null); load();
  };

  const handleDrop = async (targetStatus: string) => {
    if (!dragId) return;
    const ev = events.find(e => e.id === dragId);
    if (!ev) { setDragId(null); return; }
    let c = ev.content.replace(/#(done|doing|완료|진행)/g, '').trim();
    if (targetStatus === 'doing') c += '\n#doing';
    else if (targetStatus === 'done') c += '\n#done';
    await api.updateTimelineEvent(projectName, dragId, { content: c });
    setDragId(null); load();
  };

  // Calendar
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  const firstDay = new Date(calYear, calMonth, 1).getDay();
  const eventDates = new Set(events.map(e => e.event_date));

  const ganttDays = daysInMonth;

  // Kanban
  const byStatus: Record<string, TEvent[]> = { todo: [], doing: [], done: [] };
  events.forEach(ev => byStatus[getStatus(ev)].push(ev));

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#FAFAFA]" style={{ fontFamily: "'Noto Sans KR', sans-serif" }}>
      {/* ── TOP: Mini calendar ── */}
      <div className="shrink-0 bg-white border-b border-slate-100 px-4 py-2">
        <div className="flex items-center justify-between mb-1.5">
          <button onClick={() => { if (calMonth === 0) { setCalYear(y => y - 1); setCalMonth(11); } else setCalMonth(m => m - 1); }}
            className="text-[#9B9B9B] hover:text-[#3C3C3C] text-xs px-1">◀</button>
          <span className="text-xs font-bold text-[#2A2A2A]">{calYear}년 {calMonth + 1}월</span>
          <button onClick={() => { if (calMonth === 11) { setCalYear(y => y + 1); setCalMonth(0); } else setCalMonth(m => m + 1); }}
            className="text-[#9B9B9B] hover:text-[#3C3C3C] text-xs px-1">▶</button>
        </div>
        <div className="grid grid-cols-7 gap-0.5 text-center">
          {['일','월','화','수','목','금','토'].map(d => <div key={d} className="text-[8px] text-[#9B9B9B] py-0.5">{d}</div>)}
          {Array.from({ length: firstDay }).map((_, i) => <div key={`e${i}`} />)}
          {Array.from({ length: daysInMonth }).map((_, i) => {
            const day = i + 1;
            const ds = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = ds === todayStr;
            const has = eventDates.has(ds);
            return (
              <div key={day} className={`text-[10px] py-0.5 rounded ${isToday ? 'bg-indigo-500 text-white font-bold' : has ? 'bg-indigo-50 text-indigo-600 font-medium' : 'text-[#3C3C3C]'}`}>{day}</div>
            );
          })}
        </div>
      </div>

      {/* ── MIDDLE: Gantt chart bars ── */}
      <div className="shrink-0 bg-white border-b border-slate-100 overflow-x-auto" style={{ minHeight: 80, maxHeight: 200 }}>
        {/* Day headers */}
        <div className="flex border-b border-slate-50 sticky top-0 bg-white z-[1]" style={{ minWidth: ganttDays * 28 }}>
          <div className="w-24 shrink-0 px-2 py-1 text-[8px] text-[#9B9B9B] border-r border-slate-50">작업</div>
          {Array.from({ length: ganttDays }).map((_, i) => {
            const d = i + 1;
            const ds = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            const isToday = ds === todayStr;
            return (
              <div key={i} className={`w-7 shrink-0 text-center text-[8px] py-1 border-r border-slate-50 ${isToday ? 'bg-indigo-50 text-indigo-600 font-bold' : 'text-[#9B9B9B]'}`}>{d}</div>
            );
          })}
        </div>
        {/* Bars */}
        {events.map(ev => {
          const start = new Date(ev.event_date);
          const end = ev.end_date ? new Date(ev.end_date) : start;
          const startDay = Math.max(1, start.getDate()) - 1;
          const endDay = Math.min(ganttDays, end.getDate());
          const monthMatch = start.getFullYear() === calYear && start.getMonth() === calMonth;
          if (!monthMatch && !(ev.end_date && new Date(ev.end_date).getMonth() === calMonth)) return null;
          const barStart = monthMatch ? startDay : 0;
          const barEnd = (ev.end_date && new Date(ev.end_date).getFullYear() === calYear && new Date(ev.end_date).getMonth() === calMonth) ? endDay : ganttDays;
          const barWidth = Math.max(1, barEnd - barStart);
          return (
            <div key={ev.id} className="flex items-center" style={{ minWidth: ganttDays * 28, height: 24 }}>
              <div className="w-24 shrink-0 px-2 text-[9px] text-[#3C3C3C] truncate border-r border-slate-50">{ev.title}</div>
              <div className="flex-1 relative h-full">
                <div className="absolute top-1 rounded-full h-4 text-[8px] text-white flex items-center px-1.5 truncate cursor-pointer hover:opacity-80"
                  style={{ left: barStart * 28, width: barWidth * 28, backgroundColor: ev.color }}
                  onClick={() => startEdit(ev)}>
                  {barWidth > 2 && ev.title}
                </div>
              </div>
            </div>
          );
        })}
        {events.length === 0 && <div className="text-center text-[10px] text-[#9B9B9B] py-3">작업을 추가하면 간트차트가 표시됩니다</div>}
      </div>

      {/* ── BOTTOM: Kanban board ── */}
      <div className="flex-1 flex overflow-hidden">
        {STATUSES.map(col => (
          <div key={col.id} className="flex-1 flex flex-col border-r border-slate-100 last:border-r-0 overflow-hidden"
            onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('bg-indigo-50/30'); }}
            onDragLeave={e => { e.currentTarget.classList.remove('bg-indigo-50/30'); }}
            onDrop={e => { e.preventDefault(); e.currentTarget.classList.remove('bg-indigo-50/30'); handleDrop(col.id); }}>
            <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-50 shrink-0 bg-white">
              <div className={`w-2 h-2 rounded-full ${col.dot}`} />
              <span className="text-[11px] font-bold text-[#2A2A2A]">{col.label}</span>
              <span className="text-[10px] text-[#9B9B9B] ml-auto">{byStatus[col.id].length}</span>
            </div>
            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1.5">
              {byStatus[col.id].map(ev => (
                <div key={ev.id} draggable onDragStart={() => setDragId(ev.id)} onDragEnd={() => setDragId(null)}
                  className={`bg-white rounded-xl border border-slate-100 px-3 py-2 cursor-grab hover:shadow-[0_2px_6px_rgba(0,0,0,0.05)] transition-shadow relative group ${dragId === ev.id ? 'opacity-40' : ''}`}
                  style={{ borderLeft: `3px solid ${ev.color}` }}>
                  {editId === ev.id ? (
                    <div className="space-y-1" onClick={e => e.stopPropagation()}>
                      <input autoFocus value={editTitle} onChange={e => setEditTitle(e.target.value)}
                        className="w-full text-[11px] font-medium border border-indigo-200 rounded px-1.5 py-0.5 focus:outline-none" />
                      <div className="flex gap-1">
                        <input type="date" value={editStart} onChange={e => setEditStart(e.target.value)} className="flex-1 text-[9px] border border-slate-200 rounded px-1 py-0.5" />
                        <input type="date" value={editEnd} onChange={e => setEditEnd(e.target.value)} className="flex-1 text-[9px] border border-slate-200 rounded px-1 py-0.5" />
                      </div>
                      <textarea value={editContent} onChange={e => setEditContent(e.target.value)}
                        className="w-full text-[9px] border border-slate-200 rounded px-1.5 py-0.5 h-8 resize-none focus:outline-none" placeholder="메모..." />
                      <div className="flex gap-1">
                        <button onClick={handleSave} className="px-2 py-0.5 text-[9px] bg-indigo-500 text-white rounded">저장</button>
                        <button onClick={() => setEditId(null)} className="px-2 py-0.5 text-[9px] text-slate-500">취소</button>
                        <button onClick={() => { api.deleteTimelineEvent(projectName, ev.id); setEditId(null); load(); }} className="px-2 py-0.5 text-[9px] text-red-500 ml-auto">삭제</button>
                      </div>
                    </div>
                  ) : (
                    <div onClick={() => startEdit(ev)}>
                      <div className="text-[11px] font-medium text-[#2A2A2A]">{ev.title}</div>
                      <div className="text-[9px] text-[#9B9B9B] mt-0.5">{ev.event_date}{ev.end_date && ev.end_date !== ev.event_date ? ` ~ ${ev.end_date}` : ''}</div>
                    </div>
                  )}
                </div>
              ))}
              <button onClick={() => handleCreate(col.id)}
                className="w-full text-center text-[10px] text-indigo-500 hover:bg-indigo-50 py-1.5 rounded-lg border border-dashed border-slate-200 hover:border-indigo-300">
                + 새 항목
              </button>
            </div>
          </div>
        ))}
      </div>

      {loading && <div className="absolute inset-0 flex items-center justify-center bg-white/50 z-10"><div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" /></div>}
    </div>
  );
}
