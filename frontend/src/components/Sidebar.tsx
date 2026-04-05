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
      { label: '생성 이력', id: 'history', icon: '📋' },
    ],
  },
  {
    title: 'Tools',
    items: [
      { label: '빠른 채팅', id: 'quick_chat', icon: '💬' },
      { label: '자유양식 문서', id: 'freedoc', icon: '📝' },
      { label: '기안문 작성', id: 'draftdoc', icon: '📄' },
      { label: '발표자료 (PPT)', id: 'ppt_tools', icon: '📊' },
    ],
  },
  {
    title: 'Workflow',
    items: [
      { label: '사전 정보 수집', id: 'phase1', icon: '📥' },
      { label: '문서 작성', id: 'phase2', icon: '📝' },
      { label: 'LP Q&A 대응', id: 'lp_qa', icon: '🙋' },
      { label: '자료기반 Q&A', id: 'qa_session', icon: '💬' },
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
      { label: 'PDF 잠금 해제', id: 'pdf_unlock', icon: '🔓' },
    ],
  },
];

export default function Sidebar({ onNavigate }: { onNavigate?: () => void } = {}) {
  const { activePage, openTab: _openTab, currentProject, setCurrentProject } = useAppStore();
  const openTab = (id: string) => { _openTab(id); onNavigate?.(); };
  const { user, logout } = useAuthStore();
  const [projects, setProjects] = useState<string[]>([]);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebarCollapsed') === 'true');
  const [version, setVersion] = useState('');

  useEffect(() => {
    api.health().then((r) => setVersion(r.version || '')).catch(() => {});
  }, []);

  useEffect(() => {
    api.listProjects().then((list) => {
      setProjects(list.map((p: any) => p.name));
    }).catch(() => {});
  }, [currentProject]);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      localStorage.setItem('sidebarCollapsed', String(!prev));
      return !prev;
    });
  };

  const sidebarWidth = collapsed ? 'w-[60px] min-w-[60px]' : 'w-[260px] min-w-[260px]';

  return (
    <aside className={`${sidebarWidth} flex flex-col h-screen relative overflow-hidden transition-all duration-200`}
      style={{ background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)' }}>

      {/* Subtle gradient orb */}
      {!collapsed && (
        <div className="absolute top-0 right-0 w-40 h-40 rounded-full opacity-[0.07] pointer-events-none"
          style={{ background: 'radial-gradient(circle, #3b82f6, transparent 70%)' }} />
      )}

      {/* Logo + Toggle */}
      <div className={`${collapsed ? 'px-2 pt-4 pb-2' : 'px-5 pt-5 pb-3'} relative flex items-center ${collapsed ? 'justify-center' : 'justify-between'}`}>
        {collapsed ? (
          <div className="flex flex-col items-center gap-1.5">
            <button onClick={() => openTab('home')} className="w-9 h-9 rounded-lg flex items-center justify-center text-sm hover:bg-white/10 transition-colors"
              style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }} title="홈으로 이동">
              💎
            </button>
            <button onClick={toggleCollapsed}
              className="w-7 h-7 rounded flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-white/10 transition-colors"
              title="사이드바 펼치기">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M13 17l5-5-5-5" /><path d="M6 17l5-5-5-5" />
              </svg>
            </button>
          </div>
        ) : (
          <>
            <button onClick={() => openTab('home')} className="flex items-center gap-2.5 hover:opacity-80 transition-opacity" title="홈으로 이동">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
                style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}>
                💎
              </div>
              <div className="text-left">
                <div className="text-[13px] font-bold text-white tracking-tight">GEM Intern</div>
                <div className="text-[10px] text-slate-500 font-medium tracking-wider">{version}</div>
              </div>
            </button>
            <button onClick={toggleCollapsed}
              className="w-6 h-6 rounded flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-white/10 transition-colors"
              title="사이드바 접기">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 17l-5-5 5-5" /><path d="M18 17l-5-5 5-5" />
              </svg>
            </button>
          </>
        )}
      </div>

      {/* Project selector */}
      {!collapsed ? (
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
      ) : (
        <div className="px-2 pb-2">
          <button onClick={() => openTab('project')}
            className="w-full h-9 rounded-lg flex items-center justify-center text-sm text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors"
            title={currentProject || '프로젝트 선택'}>
            📂
          </button>
        </div>
      )}

      {/* Divider */}
      <div className="mx-4 h-px bg-white/[0.06]" />

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-2 dark-scrollbar">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-1">
            {!collapsed && (
              <div className="px-2 pt-3 pb-1.5 text-[10px] font-semibold text-slate-500 uppercase tracking-[0.1em]">
                {section.title}
              </div>
            )}
            {collapsed && <div className="h-2" />}
            {section.items.map((item) => {
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => openTab(item.id)}
                  title={collapsed ? item.label : undefined}
                  className={`w-full text-left flex items-center ${collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-2.5 py-[7px]'} rounded-lg text-[13px] transition-all duration-150 group ${
                    isActive
                      ? 'bg-blue-500/15 text-blue-400 font-medium'
                      : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-200'
                  }`}
                >
                  {isActive && !collapsed && (
                    <div className="absolute left-0 w-[3px] h-5 rounded-r-full bg-blue-400" />
                  )}
                  <span className={`${collapsed ? 'text-base' : 'text-sm'} opacity-75 group-hover:opacity-100 transition-opacity`}>{item.icon}</span>
                  {!collapsed && <span>{item.label}</span>}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom */}
      <div className="border-t border-white/[0.06] p-2">
        {user?.is_admin && (
          <button
            className={`w-full text-left flex items-center ${collapsed ? 'justify-center px-0' : 'gap-2.5 px-2.5'} py-[7px] text-[13px] text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] rounded-lg transition-all`}
            onClick={() => openTab('admin')}
            title={collapsed ? '관리자' : undefined}
          >
            <span className="text-sm">🛡️</span>
            {!collapsed && <span>관리자</span>}
          </button>
        )}
        <button
          className={`w-full text-left flex items-center ${collapsed ? 'justify-center px-0' : 'gap-2.5 px-2.5'} py-[7px] text-[13px] text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] rounded-lg transition-all`}
          onClick={() => openTab('settings')}
          title={collapsed ? '설정' : undefined}
        >
          <span className="text-sm">⚙️</span>
          {!collapsed && <span>설정</span>}
        </button>
        {!collapsed ? (
          <div className="flex items-center justify-between px-2.5 py-1.5 mt-1">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] text-slate-400">{user?.username}</span>
            </div>
            <button onClick={logout} className="text-[11px] text-slate-600 hover:text-slate-400 transition-colors">
              로그아웃
            </button>
          </div>
        ) : (
          <button onClick={logout}
            className="w-full flex items-center justify-center py-[7px] text-[13px] text-slate-600 hover:text-slate-400 hover:bg-white/[0.05] rounded-lg transition-all mt-1"
            title="로그아웃">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        )}
      </div>
    </aside>
  );
}
