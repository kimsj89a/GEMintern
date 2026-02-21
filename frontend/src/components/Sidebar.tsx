import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';

const NAV_SECTIONS = [
  {
    title: 'Main',
    items: [
      { label: '🏠 홈', id: 'home' },
      { label: '📂 프로젝트', id: 'project' },
    ],
  },
  {
    title: 'Phase Workflow',
    items: [
      { label: '📥 사전 정보 수집', id: 'phase1' },
      { label: '📝 투심보고서 작성', id: 'phase2' },
    ],
  },
  {
    title: 'Independent Tools',
    items: [
      { label: '📑 IM 작성', id: 'im' },
      { label: '📢 발표자료 (PPT)', id: 'ppt_tools' },
      { label: '🙋‍♂️ LP Q&A 대응', id: 'lp_qa' },
      { label: '💬 자료기반 Q&A', id: 'qa_session' },
    ],
  },
  {
    title: 'Utilities',
    items: [
      { label: '🎤 오디오 전사', id: 'audio' },
      { label: '🌐 웹 크롤러', id: 'crawler' },
      { label: '👁️ 문서 OCR', id: 'ocr' },
      { label: '📝 MD to Word', id: 'markdown' },
      { label: '📋 문서양식', id: 'doctemplate' },
      { label: '✏️ 문장 정리기', id: 'text_organizer' },
    ],
  },
];

export default function Sidebar() {
  const { activePage, openTab, currentProject, setCurrentProject } = useAppStore();
  const [projects, setProjects] = useState<string[]>([]);

  useEffect(() => {
    api.listProjects().then((list) => {
      setProjects(list.map((p: any) => p.name || p));
    }).catch(() => {});
  }, [currentProject]);

  return (
    <aside className="w-64 min-w-[260px] bg-[#F7F6F3] border-r border-[#E9E9E7] flex flex-col h-screen">
      {/* Title */}
      <div className="px-5 py-4">
        <h1 className="text-lg font-bold text-[#37352F]">💎 GEM Intern v7.0</h1>
      </div>

      {/* Project selector */}
      <div className="px-4 pb-3">
        <select
          className="w-full px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-md bg-white text-[#37352F] focus:outline-none focus:border-[#2383E2]"
          value={currentProject}
          onChange={(e) => setCurrentProject(e.target.value)}
        >
          <option value="">-- 선택하세요 --</option>
          {projects.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-1">
            <div className="px-3 py-1.5 text-xs font-semibold text-[#9B9A97] uppercase tracking-wider">
              {section.title}
            </div>
            {section.items.map((item) => (
              <button
                key={item.id}
                onClick={() => openTab(item.id)}
                className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
                  activePage === item.id
                    ? 'bg-[#E8F3FC] text-[#2383E2] font-medium'
                    : 'text-[#37352F] hover:bg-[#EBEBEA]'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-[#E9E9E7] p-3 space-y-1.5">
        <button
          className="w-full text-left px-3 py-1.5 text-sm text-[#787774] hover:bg-[#EBEBEA] rounded-md"
          onClick={() => openTab('settings')}
        >
          ⚙️ 설정 수정
        </button>
        <div className="px-3 py-1 text-xs text-[#9B9A97]">
          🔴 클라우드 미연결
        </div>
      </div>
    </aside>
  );
}
