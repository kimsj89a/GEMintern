import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useAppStore } from '../stores/appStore';
import { useAuthStore } from '../stores/authStore';
import { api } from '../api/client';

const PROJECT_EMOJIS = ['🤝', '🚀', '📊', '💼', '🏢', '📈', '🔬', '💎', '🎯', '⚡', '🌟', '📋', '🔥', '💰', '🏆', '🎪', '🧬', '⚙️', '🛡️', '🌍'];

const STANDALONE_TOOLS = [
  { id: 'quick_chat', label: '빠른 채팅', icon: '💬', desc: '파일 업로드 + 즉시 AI 채팅' },
  { id: 'compare', label: '신구비교', icon: '⚖️', desc: '텀싯↔계약서 비교표' },
  { id: 'docx_markup', label: 'DOCX Markup', icon: '📝', desc: '변경추적 추출·비교' },
  { id: 'draftdoc', label: '기안문', icon: '📝', desc: '기안문 작성' },
  { id: 'freedoc', label: '자유양식', icon: '✏️', desc: '자유 구조 문서' },
  { id: 'doc_updater', label: '문서 업데이트', icon: '🔄', desc: '기존 문서 수정' },
  { id: 'ocr', label: 'OCR', icon: '👁', desc: '문서 텍스트 추출' },
  { id: 'audio', label: '오디오 전사', icon: '🎙', desc: '음성→텍스트' },
  { id: 'crawler', label: '웹 크롤러', icon: '🌐', desc: '웹사이트 수집' },
  { id: 'markdown', label: 'MD → Word', icon: '📄', desc: '마크다운 변환' },
  { id: 'doctemplate', label: '문서양식', icon: '📋', desc: '표준 템플릿' },
  { id: 'text_organizer', label: '문장 정리기', icon: '✂️', desc: '텍스트 정리' },
  { id: 'quickmail', label: '메일 작성', icon: '📧', desc: '이메일 생성' },
];

export default function ProjectDashboard() {
  const { enterProject, openLegacyTool } = useAppStore();
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(true);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; name: string } | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [emojiPicker, setEmojiPicker] = useState<string | null>(null);
  const [dragProject, setDragProject] = useState<string | null>(null);
  const [dropIdx, setDropIdx] = useState<number | null>(null);
  // Custom emoji overrides stored in localStorage
  const [customEmojis, setCustomEmojis] = useState<Record<string, string>>(() => {
    try { return JSON.parse(localStorage.getItem('project_emojis') || '{}'); } catch { return {}; }
  });

  const loadProjects = async () => {
    try {
      const list = await api.listProjects();
      // Apply saved order from localStorage
      const savedOrder: string[] = (() => { try { return JSON.parse(localStorage.getItem('project_order') || '[]'); } catch { return []; } })();
      if (savedOrder.length > 0) {
        const byName = new Map(list.map((p: any) => [p.name || p, p]));
        const ordered: any[] = [];
        for (const name of savedOrder) {
          if (byName.has(name)) { ordered.push(byName.get(name)); byName.delete(name); }
        }
        // Append any new projects not in saved order
        for (const p of byName.values()) ordered.push(p);
        setProjects(ordered);
      } else {
        setProjects(list);
      }
    } catch { setProjects([]); }
    setLoading(false);
  };

  const saveProjectOrder = (list: any[]) => {
    const names = list.map((p: any) => p.name || p);
    localStorage.setItem('project_order', JSON.stringify(names));
  };

  useEffect(() => { loadProjects(); }, []);

  useEffect(() => {
    if (!ctxMenu) return;
    const close = () => setCtxMenu(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [ctxMenu]);

  const setProjectEmoji = (name: string, emoji: string) => {
    const next = { ...customEmojis, [name]: emoji };
    setCustomEmojis(next);
    localStorage.setItem('project_emojis', JSON.stringify(next));
    setEmojiPicker(null);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await api.createProject(newName.trim());
      enterProject(newName.trim());
    } catch {}
    setNewName('');
    setCreating(false);
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`'${name}' 프로젝트를 삭제하시겠습니까?`)) return;
    try { await api.deleteProject(name); loadProjects(); } catch {}
  };

  const handleRename = async (oldName: string, newN: string) => {
    if (!newN.trim() || newN === oldName) { setRenaming(null); return; }
    try { await api.renameProject(oldName, newN.trim()); loadProjects(); } catch {}
    setRenaming(null);
  };

  const getEmoji = (name: string) => {
    if (customEmojis[name]) return customEmojis[name];
    const hash = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    return PROJECT_EMOJIS[hash % PROJECT_EMOJIS.length];
  };

  // getBgColor removed — StyleSeed: white cards only

  return (
    <div className="min-h-screen bg-[#FAFAFA]" style={{ fontFamily: "'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      {/* Header — StyleSeed: white card on #FAFAFA, shadow 4-8% */}
      <header className="flex items-center justify-between px-4 md:px-6 py-3 bg-white border-b border-slate-100 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-base bg-indigo-500 text-white shadow-sm">
            G
          </div>
          <span className="text-lg font-bold text-slate-800">GEM Intern</span>
        </div>
        <div className="flex items-center gap-3">
          {user?.is_admin && (
            <button onClick={() => { useAppStore.getState().setView('legacy'); useAppStore.getState().openTab('admin'); }}
              className="text-sm text-slate-500 hover:text-slate-700">관리자</button>
          )}
          <button onClick={() => { useAppStore.getState().setView('legacy'); useAppStore.getState().openTab('settings'); }}
            className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-bold">
            {(user?.username || 'U')[0].toUpperCase()}
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-3 md:px-8 py-4 md:py-8">
        {/* 독립 도구 — StyleSeed: card on #FAFAFA, single accent */}
        <div className="text-xs font-bold text-[#9B9B9B] uppercase tracking-wider mb-3">도구</div>
        <div className="grid grid-cols-4 md:grid-cols-5 lg:grid-cols-9 gap-2 md:gap-3 mb-8 md:mb-10">
          {STANDALONE_TOOLS.map((tool) => (
            <button
              key={tool.id}
              onClick={() => openLegacyTool(tool.id)}
              className="bg-white rounded-xl md:rounded-2xl border border-slate-100 hover:border-indigo-200 p-2.5 md:p-3.5 flex flex-col items-center gap-1.5 md:gap-2.5 transition-all hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)] group"
            >
              <span className="text-xl md:text-2xl group-hover:scale-110 transition-transform">{tool.icon}</span>
              <span className="text-[9px] md:text-[11px] font-medium text-[#3C3C3C] group-hover:text-indigo-600 text-center leading-tight">{tool.label}</span>
            </button>
          ))}
        </div>

        <div className="text-xs font-bold text-[#9B9B9B] uppercase tracking-wider mb-4">프로젝트</div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-4">
            {/* 새 프로젝트 만들기 카드 */}
            {creating ? (
              <div className="bg-white rounded-2xl border-2 border-blue-300 p-5 flex flex-col items-center gap-3">
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                  placeholder="프로젝트명"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500"
                />
                <div className="flex gap-2 w-full">
                  <button onClick={handleCreate} className="flex-1 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600">만들기</button>
                  <button onClick={() => { setCreating(false); setNewName(''); }} className="flex-1 py-1.5 text-sm text-slate-500 border rounded-lg hover:bg-slate-50">취소</button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setCreating(true)}
                className="bg-white rounded-xl md:rounded-2xl border-2 border-dashed border-slate-200 hover:border-blue-300 p-4 md:p-5 flex flex-col items-center justify-center gap-2 md:gap-3 min-h-[100px] md:min-h-[160px] transition-all hover:shadow-sm group"
              >
                <div className="w-12 h-12 rounded-full bg-slate-100 group-hover:bg-blue-50 flex items-center justify-center transition-colors">
                  <span className="text-2xl text-blue-500">+</span>
                </div>
                <span className="text-sm font-medium text-slate-500 group-hover:text-blue-600">새 프로젝트 만들기</span>
              </button>
            )}

            {/* 프로젝트 카드들 */}
            {projects.map((p, idx) => {
              const name = p.name || p;
              return (
                <div
                  key={name}
                  draggable
                  onDragStart={() => setDragProject(name)}
                  onDragOver={e => { e.preventDefault(); setDropIdx(idx); }}
                  onDragLeave={() => setDropIdx(null)}
                  onDrop={() => {
                    if (dragProject && dragProject !== name) {
                      const from = projects.findIndex((pp: any) => (pp.name || pp) === dragProject);
                      if (from >= 0) {
                        const reordered = [...projects];
                        const [moved] = reordered.splice(from, 1);
                        reordered.splice(idx, 0, moved);
                        setProjects(reordered);
                        saveProjectOrder(reordered);
                      }
                    }
                    setDragProject(null); setDropIdx(null);
                  }}
                  onDragEnd={() => { setDragProject(null); setDropIdx(null); }}
                  className={`bg-white rounded-xl md:rounded-2xl border ${dropIdx === idx ? 'border-indigo-400 ring-2 ring-indigo-100' : 'border-slate-100 hover:border-slate-200'} p-4 md:p-5 flex flex-col items-center justify-center gap-2 md:gap-3 min-h-[100px] md:min-h-[160px] transition-all hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)] relative group cursor-pointer ${dragProject === name ? 'opacity-40' : ''}`}
                  onClick={() => { if (!renaming) enterProject(name); }}
                  onContextMenu={e => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, name }); }}
                >
                  <span className="text-4xl cursor-grab">{getEmoji(name)}</span>
                  {renaming === name ? (
                    <input autoFocus value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') handleRename(name, renameValue); if (e.key === 'Escape') setRenaming(null); }}
                      onBlur={() => handleRename(name, renameValue)}
                      onClick={e => e.stopPropagation()}
                      className="w-full px-2 py-1 text-sm text-center border border-blue-300 rounded-lg focus:outline-none" />
                  ) : (
                    <span className="text-sm font-semibold text-[#2A2A2A] text-center leading-tight">{name}</span>
                  )}
                  {p.doc_count != null && (
                    <div className="flex items-baseline gap-1">
                      <span className="text-lg font-bold text-[#3C3C3C]">{p.doc_count}</span>
                      <span className="text-[10px] text-[#9B9B9B]">소스</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

      </div>

      {/* Project context menu */}
      {ctxMenu && createPortal(
        <div ref={el => {
          if (!el) return;
          const r = el.getBoundingClientRect();
          if (r.bottom > window.innerHeight) el.style.top = `${ctxMenu.y - r.height}px`;
          if (r.right > window.innerWidth) el.style.left = `${ctxMenu.x - r.width}px`;
        }}
          className="fixed bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-[9999] min-w-[150px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }} onClick={e => e.stopPropagation()}>
          <div className="px-3 py-1.5 text-xs font-semibold text-slate-700 border-b border-slate-100 mb-1 truncate">
            {getEmoji(ctxMenu.name)} {ctxMenu.name}
          </div>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { setRenaming(ctxMenu.name); setRenameValue(ctxMenu.name); setCtxMenu(null); }}>
            ✏️ 이름 변경
          </button>
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50"
            onClick={() => { setEmojiPicker(ctxMenu.name); setCtxMenu(null); }}>
            😀 아이콘 변경
          </button>
          <div className="border-t border-slate-100 my-1" />
          <button className="w-full text-left px-3 py-1.5 text-xs hover:bg-red-50 text-red-600"
            onClick={() => { handleDelete(ctxMenu.name); setCtxMenu(null); }}>
            🗑 삭제
          </button>
        </div>,
        document.body
      )}

      {/* Emoji picker modal */}
      {emojiPicker && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={() => setEmojiPicker(null)}>
          <div className="bg-white rounded-2xl shadow-xl p-4 w-[280px]" onClick={e => e.stopPropagation()}>
            <div className="text-sm font-semibold text-slate-700 mb-3">아이콘 선택: {emojiPicker}</div>
            <div className="grid grid-cols-8 gap-1.5">
              {PROJECT_EMOJIS.map(e => (
                <button key={e} onClick={() => setProjectEmoji(emojiPicker, e)}
                  className="w-8 h-8 flex items-center justify-center text-lg rounded-lg hover:bg-slate-100 transition-colors">
                  {e}
                </button>
              ))}
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
