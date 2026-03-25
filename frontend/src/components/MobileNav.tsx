import { useState } from 'react';
import { useAppStore } from '../stores/appStore';

const SECTIONS = [
  {
    id: 'main', label: 'Main', icon: '🏠',
    items: [
      { label: '홈', id: 'home', icon: '🏠' },
      { label: '프로젝트', id: 'project', icon: '📂' },
      { label: '생성 이력', id: 'history', icon: '📋' },
    ],
  },
  {
    id: 'tools', label: 'Tools', icon: '🛠',
    items: [
      { label: '자유양식', id: 'freedoc', icon: '📝' },
      { label: '기안문', id: 'draftdoc', icon: '📄' },
      { label: 'PPT', id: 'ppt_tools', icon: '📊' },
    ],
  },
  {
    id: 'workflow', label: 'Workflow', icon: '⚡',
    items: [
      { label: '정보 수집', id: 'phase1', icon: '📥' },
      { label: '문서 작성', id: 'phase2', icon: '📝' },
      { label: 'LP Q&A', id: 'lp_qa', icon: '🙋' },
      { label: 'Q&A', id: 'qa_session', icon: '💬' },
    ],
  },
  {
    id: 'utils', label: 'Utils', icon: '🔧',
    items: [
      { label: '오디오', id: 'audio', icon: '🎤' },
      { label: '크롤러', id: 'crawler', icon: '🌐' },
      { label: 'OCR', id: 'ocr', icon: '👁' },
      { label: 'MD→Word', id: 'markdown', icon: '📝' },
      { label: '문서양식', id: 'doctemplate', icon: '📋' },
      { label: '문장정리', id: 'text_organizer', icon: '✏️' },
      { label: 'QuickMail', id: 'quickmail', icon: '✉️' },
      { label: 'NPS', id: 'nps', icon: '🏢' },
      { label: 'DartWings', id: 'dartwings', icon: '📊' },
      { label: 'PDF잠금', id: 'pdf_unlock', icon: '🔓' },
    ],
  },
];

export default function MobileNav() {
  const { activePage, openTab } = useAppStore();
  const [activeSection, setActiveSection] = useState<string | null>(null);

  // 현재 활성 페이지가 속한 섹션 찾기
  const currentSection = SECTIONS.find(s => s.items.some(i => i.id === activePage));

  const handleSectionClick = (sectionId: string) => {
    if (activeSection === sectionId) {
      setActiveSection(null); // 토글
    } else {
      setActiveSection(sectionId);
    }
  };

  const handleItemClick = (itemId: string) => {
    openTab(itemId);
    setActiveSection(null);
  };

  const section = SECTIONS.find(s => s.id === activeSection);

  return (
    <>
      {/* 그리드 패널 (하단 탭바 위에 표시) */}
      {activeSection && section && (
        <>
          <div className="fixed inset-0 bg-black/30 z-30" onClick={() => setActiveSection(null)} />
          <div className="fixed bottom-[56px] left-0 right-0 z-40 bg-white border-t border-slate-200 rounded-t-2xl shadow-xl animate-slide-up">
            <div className="px-4 pt-3 pb-1">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">{section.label}</div>
            </div>
            <div className="grid grid-cols-4 gap-1 px-3 pb-4 pt-1">
              {section.items.map(item => {
                const isActive = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleItemClick(item.id)}
                    className={`flex flex-col items-center gap-1.5 py-3 rounded-xl transition-all ${
                      isActive
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-slate-600 hover:bg-slate-50 active:bg-slate-100'
                    }`}
                  >
                    <span className="text-2xl">{item.icon}</span>
                    <span className={`text-[11px] leading-tight text-center ${isActive ? 'font-semibold' : ''}`}>
                      {item.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* 하단 탭바 */}
      <div className="flex items-stretch bg-white border-t border-slate-200 shrink-0 safe-area-bottom" style={{ height: 56 }}>
        {SECTIONS.map(s => {
          const isCurrentSection = currentSection?.id === s.id;
          const isOpen = activeSection === s.id;
          return (
            <button
              key={s.id}
              onClick={() => handleSectionClick(s.id)}
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors ${
                isOpen
                  ? 'text-blue-600 bg-blue-50/50'
                  : isCurrentSection
                    ? 'text-blue-500'
                    : 'text-slate-400'
              }`}
            >
              <span className="text-xl">{s.icon}</span>
              <span className={`text-[10px] ${isOpen || isCurrentSection ? 'font-semibold' : ''}`}>{s.label}</span>
            </button>
          );
        })}
      </div>
    </>
  );
}
