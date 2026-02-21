import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';

const WORKFLOW_CARDS = [
  {
    id: 'phase1',
    phase: 'Phase 1',
    icon: '📥',
    title: '사전 정보 수집',
    desc: '투자 대상 기업/자산의 기초 자료를 수집하고 분석합니다.',
    color: 'border-l-blue-400',
  },
  {
    id: 'phase2',
    phase: 'Phase 2',
    icon: '📝',
    title: '투심보고서 작성',
    desc: '수집된 자료를 바탕으로 AI 투심보고서를 생성합니다.',
    color: 'border-l-purple-400',
  },
];

const TOOL_BUTTONS = [
  { id: 'im', icon: '📑', label: '문서작성' },
  { id: 'ppt_tools', icon: '📢', label: 'PPT작성' },
  { id: 'lp_qa', icon: '🙋‍♂️', label: 'LP Q&A 대응' },
  { id: 'qa_session', icon: '💬', label: '자료기반 Q&A' },
];

export default function HomePage() {
  const { openTab, currentProject } = useAppStore();
  const [projectCount, setProjectCount] = useState(0);
  const [docCount, setDocCount] = useState(0);

  useEffect(() => {
    api.listProjects().then((list) => {
      setProjectCount(list.length);
    }).catch(() => {});

    if (currentProject) {
      api.getProjectDocs(currentProject).then((data) => {
        setDocCount(data.count || 0);
      }).catch(() => {});
    }
  }, [currentProject]);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-[#37352F] mb-1">🏠 GEM Intern Dashboard</h1>
      <p className="text-sm text-[#787774] mb-8">AI 기반 투자분석 데스크톱</p>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-[#F7F6F3] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-[#2383E2]">{projectCount}</div>
          <div className="text-xs text-[#787774]">프로젝트</div>
        </div>
        <div className="bg-[#F7F6F3] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-[#2383E2]">{docCount}</div>
          <div className="text-xs text-[#787774]">현재 프로젝트 문서</div>
        </div>
        <div className="bg-[#F7F6F3] rounded-xl p-4 text-center cursor-pointer hover:bg-[#EBEBEA] transition-colors"
             onClick={() => openTab('project')}>
          <div className="text-2xl">📂</div>
          <div className="text-xs text-[#787774]">프로젝트 관리</div>
        </div>
      </div>

      {/* Workflow cards */}
      <h2 className="text-sm font-semibold text-[#9B9A97] uppercase tracking-wider mb-3">Investment Workflow</h2>
      <div className="grid grid-cols-2 gap-4 mb-8">
        {WORKFLOW_CARDS.map((card) => (
          <div
            key={card.id}
            onClick={() => openTab(card.id)}
            className={`bg-white border border-[#E9E9E7] ${card.color} border-l-4 rounded-xl p-5 cursor-pointer hover:shadow-md transition-shadow`}
          >
            <div className="text-xs font-semibold text-[#9B9A97] mb-1">{card.phase}</div>
            <div className="text-lg font-semibold text-[#37352F] mb-1">
              {card.icon} {card.title}
            </div>
            <div className="text-sm text-[#787774]">{card.desc}</div>
          </div>
        ))}
      </div>

      {/* Independent tools */}
      <h2 className="text-sm font-semibold text-[#9B9A97] uppercase tracking-wider mb-3">Independent Tools</h2>
      <div className="grid grid-cols-4 gap-3">
        {TOOL_BUTTONS.map((tool) => (
          <button
            key={tool.id}
            onClick={() => openTab(tool.id)}
            className="bg-white border border-[#E9E9E7] rounded-xl p-4 text-center hover:shadow-md hover:border-[#2383E2] transition-all"
          >
            <div className="text-2xl mb-1">{tool.icon}</div>
            <div className="text-sm text-[#37352F]">{tool.label}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
