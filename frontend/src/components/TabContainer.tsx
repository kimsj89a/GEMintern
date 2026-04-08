import { Suspense } from 'react';
import { useAppStore } from '../stores/appStore';
import { PAGE_REGISTRY } from '../pages';

export default function TabContainer({ mobile, hideTabBar }: { mobile?: boolean; hideTabBar?: boolean } = {}) {
  const { openTabs, activePage, setActivePage, closeTab, backToDashboard, view } = useAppStore();
  const isToolView = view === 'tool';
  const currentPage = PAGE_REGISTRY[activePage];

  return (
    <div className={`flex-1 flex flex-col h-full overflow-hidden ${isToolView ? 'bg-[#FAFAFA]' : 'bg-mesh'}`}
      style={isToolView ? { fontFamily: "'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" } : undefined}>
      {/* Tool view header — back button, no sidebar */}
      {isToolView && (
        <header className="flex items-center gap-3 px-5 py-3 bg-white border-b border-slate-100 shadow-[0_1px_2px_rgba(0,0,0,0.04)] shrink-0">
          <button onClick={backToDashboard} className="text-[#9B9B9B] hover:text-[#3C3C3C] transition-colors">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <span className="text-sm font-bold text-[#2A2A2A]">{currentPage?.label || activePage}</span>
        </header>
      )}
      {/* Tab bar — 모바일에서는 숨기기 가능 */}
      {!hideTabBar && <div className={`flex items-center bg-white/60 backdrop-blur-sm border-b border-slate-200/80 overflow-x-auto px-1 ${mobile ? 'min-h-[36px]' : 'min-h-[40px]'}`}>
        {openTabs.map((tabId) => {
          const page = PAGE_REGISTRY[tabId];
          if (!page) return null;
          const isActive = tabId === activePage;
          return (
            <div
              key={tabId}
              className={`relative flex items-center gap-1 ${mobile ? 'px-2.5 py-1.5 text-[12px] max-w-[140px]' : 'px-3.5 py-2 text-[13px] max-w-[200px]'} cursor-pointer shrink-0 select-none rounded-t-lg transition-all duration-150 ${
                isActive
                  ? 'bg-white text-slate-800 font-medium shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 hover:bg-white/40'
              }`}
              onClick={() => setActivePage(tabId)}
            >
              {isActive && (
                <div className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full gradient-accent" />
              )}
              <span className="truncate">{page.label}</span>
              {openTabs.length > 1 && (
                <button
                  className="ml-1 w-4 h-4 flex items-center justify-center rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 text-xs leading-none transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(tabId);
                  }}
                >
                  &times;
                </button>
              )}
            </div>
          );
        })}
      </div>}

      {/* Page content */}
      <div className="flex-1 overflow-y-auto">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-64">
              <div className="flex items-center gap-3 text-slate-400">
                <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm">로딩 중...</span>
              </div>
            </div>
          }
        >
          {openTabs.map((tabId) => {
            const page = PAGE_REGISTRY[tabId];
            if (!page) return null;
            const Component = page.component;
            return (
              <div
                key={tabId}
                className={tabId === activePage ? 'animate-fade-in' : 'hidden'}
              >
                <Component />
              </div>
            );
          })}
        </Suspense>
      </div>
    </div>
  );
}
