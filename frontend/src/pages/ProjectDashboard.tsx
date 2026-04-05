import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { useAuthStore } from '../stores/authStore';
import { api } from '../api/client';

const STANDALONE_TOOLS = [
  { id: 'quick_chat', label: '빠른 채팅', icon: '💬', desc: '파일 업로드 + 즉시 AI 채팅' },
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

  const loadProjects = async () => {
    try {
      const list = await api.listProjects();
      setProjects(list);
    } catch { setProjects([]); }
    setLoading(false);
  };

  useEffect(() => { loadProjects(); }, []);

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
    try {
      await api.deleteProject(name);
      loadProjects();
    } catch {}
  };

  // 프로젝트 이모지 (이름 기반 해시)
  const getEmoji = (name: string) => {
    const emojis = ['🤝', '🚀', '📊', '💼', '🏢', '📈', '🔬', '💎', '🎯', '⚡', '🌟', '📋'];
    const hash = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    return emojis[hash % emojis.length];
  };

  const getBgColor = (name: string) => {
    const colors = ['bg-blue-50', 'bg-purple-50', 'bg-amber-50', 'bg-green-50', 'bg-rose-50', 'bg-cyan-50'];
    const hash = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}>
            💎
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
      <div className="max-w-5xl mx-auto px-4 md:px-8 py-8">
        {/* 독립 도구 */}
        <h2 className="text-xl font-bold text-slate-800 mb-4">도구</h2>
        <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-3 mb-10">
          {STANDALONE_TOOLS.map((tool) => (
            <button
              key={tool.id}
              onClick={() => openLegacyTool(tool.id)}
              className="bg-white rounded-xl border border-slate-200 hover:border-slate-300 p-3 flex flex-col items-center gap-2 transition-all hover:shadow-sm group"
            >
              <span className="text-2xl">{tool.icon}</span>
              <span className="text-xs font-medium text-slate-700 group-hover:text-slate-900 text-center leading-tight">{tool.label}</span>
            </button>
          ))}
        </div>

        <h2 className="text-xl font-bold text-slate-800 mb-6">최근 프로젝트</h2>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
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
                className="bg-white rounded-2xl border-2 border-dashed border-slate-200 hover:border-blue-300 p-5 flex flex-col items-center justify-center gap-3 min-h-[160px] transition-all hover:shadow-sm group"
              >
                <div className="w-12 h-12 rounded-full bg-slate-100 group-hover:bg-blue-50 flex items-center justify-center transition-colors">
                  <span className="text-2xl text-blue-500">+</span>
                </div>
                <span className="text-sm font-medium text-slate-500 group-hover:text-blue-600">새 프로젝트 만들기</span>
              </button>
            )}

            {/* 프로젝트 카드들 */}
            {projects.map((p) => {
              const name = p.name || p;
              return (
                <button
                  key={name}
                  onClick={() => enterProject(name)}
                  className={`${getBgColor(name)} rounded-2xl border border-slate-200 hover:border-slate-300 p-5 flex flex-col items-center justify-center gap-3 min-h-[160px] transition-all hover:shadow-md relative group`}
                >
                  {/* 삭제 메뉴 */}
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(name); }}
                      className="w-7 h-7 rounded-full bg-white/80 hover:bg-white flex items-center justify-center text-slate-400 hover:text-red-500 shadow-sm"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                    </button>
                  </div>
                  <span className="text-4xl">{getEmoji(name)}</span>
                  <span className="text-sm font-semibold text-slate-700 text-center leading-tight">{name}</span>
                  {p.doc_count != null && (
                    <span className="text-xs text-slate-400">소스 {p.doc_count}개</span>
                  )}
                </button>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}
