import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { useAuthStore } from '../stores/authStore';
import { api } from '../api/client';

const NAV_SECTIONS = [
  {
    title: 'Main',
    items: [
      { label: '홈', id: 'home', icon: '🏠' },
      { label: '프로젝트', id: 'project', icon: '📂' },
    ],
  },
  {
    title: 'Workflow',
    items: [
      { label: '사전 정보 수집', id: 'phase1', icon: '📥' },
      { label: '문서 작성', id: 'phase2', icon: '📝' },
    ],
  },
  {
    title: 'Tools',
    items: [
      { label: '자유양식 문서', id: 'freedoc', icon: '📝' },
      { label: 'LP Q&A 대응', id: 'lp_qa', icon: '🙋' },
      { label: '자료기반 Q&A', id: 'qa_session', icon: '💬' },
      { label: '문서 업데이트', id: 'doc_updater', icon: '🔄' },
    ],
  },
  {
    title: 'Utilities',
    items: [
      { label: '오디오 전사', id: 'audio', icon: '🎤' },
      { label: '웹 크롤러', id: 'crawler', icon: '🌐' },
      { label: '문서 OCR', id: 'ocr', icon: '👁' },
      { label: 'MD to Word', id: 'markdown', icon: '📝' },
      { label: '문서양식', id: 'doctemplate', icon: '📋' },
      { label: '문장 정리기', id: 'text_organizer', icon: '✏️' },
      { label: 'QuickMail', id: 'quickmail', icon: '✉️' },
      { label: '국민연금 사업장', id: 'nps', icon: '🏢' },
      { label: 'DartWings', id: 'dartwings', icon: '📊' },
    ],
  },
];

export default function Sidebar() {
  const { activePage, openTab, currentProject, setCurrentProject } = useAppStore();
  const { user, logout } = useAuthStore();
  const [projects, setProjects] = useState<string[]>([]);

  useEffect(() => {
    api.listProjects().then((list) => {
      setProjects(list.map((p: any) => p.name || p));
    }).catch(() => {});
  }, [currentProject]);

  return (
    <aside className="w-[260px] min-w-[260px] flex flex-col h-screen relative overflow-hidden"
      style={{ background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)' }}>

      {/* Subtle gradient orb */}
      <div className="absolute top-0 right-0 w-40 h-40 rounded-full opacity-[0.07] pointer-events-none"
        style={{ background: 'radial-gradient(circle, #3b82f6, transparent 70%)' }} />

      {/* Logo */}
      <div className="px-5 pt-5 pb-3 relative">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}>
            💎
          </div>
          <div>
            <div className="text-[13px] font-bold text-white tracking-tight">GEM Intern</div>
            <div className="text-[10px] text-slate-500 font-medium tracking-wider">v7.0</div>
          </div>
        </div>
      </div>

      {/* Project selector */}
      <div className="px-4 pb-3">
        <select
          className="w-full px-3 py-2 text-xs rounded-lg bg-white/[0.06] border border-white/[0.08] text-slate-300 focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.08] transition-all appearance-none cursor-pointer"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M3 5l3 3 3-3' fill='none' stroke='%2394a3b8' stroke-width='1.5'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center' }}
          value={currentProject}
          onChange={(e) => setCurrentProject(e.target.value)}
        >
          <option value="">프로젝트 선택...</option>
          {projects.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-white/[0.06]" />

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 dark-scrollbar">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-1">
            <div className="px-2 pt-3 pb-1.5 text-[10px] font-semibold text-slate-500 uppercase tracking-[0.1em]">
              {section.title}
            </div>
            {section.items.map((item) => {
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => openTab(item.id)}
                  className={`w-full text-left flex items-center gap-2.5 px-2.5 py-[7px] rounded-lg text-[13px] transition-all duration-150 group ${
                    isActive
                      ? 'bg-blue-500/15 text-blue-400 font-medium'
                      : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-200'
                  }`}
                >
                  {isActive && (
                    <div className="absolute left-0 w-[3px] h-5 rounded-r-full bg-blue-400" />
                  )}
                  <span className="text-sm opacity-75 group-hover:opacity-100 transition-opacity">{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom */}
      <div className="border-t border-white/[0.06] p-3">
        {user?.is_admin && (
          <button
            className="w-full text-left flex items-center gap-2.5 px-2.5 py-[7px] text-[13px] text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] rounded-lg transition-all"
            onClick={() => openTab('admin')}
          >
            <span className="text-sm">🛡️</span>
            <span>관리자</span>
          </button>
        )}
        <button
          className="w-full text-left flex items-center gap-2.5 px-2.5 py-[7px] text-[13px] text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] rounded-lg transition-all"
          onClick={() => openTab('settings')}
        >
          <span className="text-sm">⚙️</span>
          <span>설정</span>
        </button>
        <div className="flex items-center justify-between px-2.5 py-1.5 mt-1">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] text-slate-400">{user?.username}</span>
          </div>
          <button onClick={logout} className="text-[11px] text-slate-600 hover:text-slate-400 transition-colors">
            로그아웃
          </button>
        </div>
      </div>
    </aside>
  );
}
