import { Suspense } from 'react';
import { useAppStore } from '../stores/appStore';
import { PAGE_REGISTRY } from '../pages';

export default function TabContainer() {
  const { openTabs, activePage, setActivePage, closeTab } = useAppStore();

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-mesh">
      {/* Tab bar */}
      <div className="flex items-center bg-white/60 backdrop-blur-sm border-b border-slate-200/80 min-h-[40px] overflow-x-auto px-1">
        {openTabs.map((tabId) => {
          const page = PAGE_REGISTRY[tabId];
          if (!page) return null;
          const isActive = tabId === activePage;
          return (
            <div
              key={tabId}
              className={`relative flex items-center gap-1.5 px-3.5 py-2 text-[13px] cursor-pointer max-w-[200px] shrink-0 select-none rounded-t-lg transition-all duration-150 ${
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
      </div>

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
