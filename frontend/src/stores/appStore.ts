import { create } from 'zustand';

type ViewMode = 'dashboard' | 'workspace' | 'legacy';

interface AppState {
  view: ViewMode;
  setView: (v: ViewMode) => void;
  activePanel: 'sources' | 'chat' | 'studio';
  setActivePanel: (p: 'sources' | 'chat' | 'studio') => void;
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
  setView: (v) => set({ view: v }),
  activePanel: 'chat' as const,
  setActivePanel: (p) => set({ activePanel: p }),

  currentProject: localStorage.getItem('lastProject') || '',
  setCurrentProject: (p) => {
    localStorage.setItem('lastProject', p);
    set({ currentProject: p });
  },

  enterProject: (name) => {
    localStorage.setItem('lastProject', name);
    set({ currentProject: name, view: 'workspace', activePanel: 'chat' });
  },
  backToDashboard: () => set({ view: 'dashboard' }),

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
