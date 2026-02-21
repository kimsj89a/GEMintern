import { Suspense } from 'react';
import { useAppStore } from '../stores/appStore';
import { PAGE_REGISTRY } from '../pages';

export default function TabContainer() {
  const { openTabs, activePage, setActivePage, closeTab } = useAppStore();

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden">
      {/* Tab bar */}
      <div className="flex bg-[#F7F6F3] border-b border-[#E9E9E7] min-h-[36px] overflow-x-auto">
        {openTabs.map((tabId) => {
          const page = PAGE_REGISTRY[tabId];
          if (!page) return null;
          const isActive = tabId === activePage;
          return (
            <div
              key={tabId}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm cursor-pointer border-r border-[#E9E9E7] max-w-[200px] shrink-0 select-none ${
                isActive
                  ? 'bg-white text-[#37352F] font-medium'
                  : 'text-[#787774] hover:bg-[#EBEBEA]'
              }`}
              onClick={() => setActivePage(tabId)}
            >
              <span className="truncate">{page.label}</span>
              {openTabs.length > 1 && (
                <button
                  className="ml-1 text-[#9B9A97] hover:text-[#37352F] text-xs leading-none"
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(tabId);
                  }}
                >
                  ×
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Page content */}
      <div className="flex-1 overflow-y-auto bg-white">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-64 text-[#9B9A97]">
              로딩 중...
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
                className={tabId === activePage ? '' : 'hidden'}
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
