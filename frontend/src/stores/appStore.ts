import { create } from 'zustand';

type ViewMode = 'dashboard' | 'workspace' | 'legacy';

interface AppState {
  view: ViewMode;
  setView: (v: ViewMode) => void;
  activePanel: 'sources' | 'chat' | 'studio';
  setActivePanel: (p: 'sources' | 'chat' | 'studio') => void;
  activeTool: string | null; // workspace 내 활성 도구 (null=채팅)
  setActiveTool: (t: string | null) => void;
  currentProject: string;
  setCurrentProject: (p: string) => void;
  activePage: string;
  setActivePage: (p: string) => void;
  openTabs: string[];
  openTab: (page: string) => void;
  closeTab: (page: string) => void;
  settings: Record<string, any>;
  setSettings: (s: Record<string, any>) => void;
  appStarted: boolean;
  setAppStarted: (v: boolean) => void;
  enterProject: (name: string) => void;
  backToDashboard: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  view: 'dashboard' as ViewMode,
  setView: (v) => {
    const prev = get().view;
    set({ view: v });
    // 브라우저 히스토리에 상태 push
    if (v !== prev) {
      window.history.pushState({ view: v, project: get().currentProject }, '');
    }
  },
  activePanel: 'chat' as const,
  setActivePanel: (p) => set({ activePanel: p }),
  activeTool: null,
  setActiveTool: (t) => set({ activeTool: t }),

  currentProject: localStorage.getItem('lastProject') || '',
  setCurrentProject: (p) => {
    localStorage.setItem('lastProject', p);
    set({ currentProject: p });
  },

  enterProject: (name) => {
    localStorage.setItem('lastProject', name);
    set({ currentProject: name, view: 'workspace', activePanel: 'chat', activeTool: null });
    window.history.pushState({ view: 'workspace', project: name }, '');
  },
  backToDashboard: () => {
    set({ view: 'dashboard', activeTool: null });
    window.history.pushState({ view: 'dashboard' }, '');
  },

  activePage: 'home',
  setActivePage: (p) => {
    const { openTabs } = get();
    if (!openTabs.includes(p)) {
      set({ activePage: p, openTabs: [...openTabs, p] });
    } else {
      set({ activePage: p });
    }
  },

  openTabs: ['home'],
  openTab: (page) => {
    const { openTabs } = get();
    if (!openTabs.includes(page)) {
      set({ openTabs: [...openTabs, page], activePage: page });
    } else {
      set({ activePage: page });
    }
  },
  closeTab: (page) => {
    const { openTabs, activePage } = get();
    if (openTabs.length <= 1) return;
    const next = openTabs.filter((t) => t !== page);
    set({
      openTabs: next,
      activePage: activePage === page ? next[next.length - 1] : activePage,
    });
  },

  settings: {},
  setSettings: (s) => set({ settings: s }),
  appStarted: false,
  setAppStarted: (v) => set({ appStarted: v }),
}));

// 브라우저 뒤로가기/앞으로가기 처리
window.addEventListener('popstate', (e) => {
  const state = e.state;
  if (state?.view) {
    const store = useAppStore.getState();
    if (state.view === 'dashboard') {
      store.setView !== undefined && useAppStore.setState({ view: 'dashboard', activeTool: null });
    } else if (state.view === 'workspace' && state.project) {
      useAppStore.setState({ view: 'workspace', currentProject: state.project, activeTool: null });
    }
  } else {
    // 히스토리 없으면 대시보드로
    useAppStore.setState({ view: 'dashboard', activeTool: null });
  }
});
