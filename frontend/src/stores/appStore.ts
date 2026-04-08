import { create } from 'zustand';

type ViewMode = 'dashboard' | 'workspace' | 'legacy' | 'tool';

interface AppState {
  view: ViewMode;
  setView: (v: ViewMode) => void;
  activePanel: 'sources' | 'chat' | 'studio';
  setActivePanel: (p: 'sources' | 'chat' | 'studio') => void;
  activeTool: string | null;
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
  openLegacyTool: (page: string) => void;
}

// pushState 중복 방지 플래그
let _skipNextPush = false;

export const useAppStore = create<AppState>((set, get) => ({
  view: 'dashboard' as ViewMode,
  setView: (v) => set({ view: v }),

  activePanel: 'chat' as const,
  setActivePanel: (p) => set({ activePanel: p }),
  activeTool: null,
  setActiveTool: (t) => {
    const prev = get().activeTool;
    set({ activeTool: t });
    if (!_skipNextPush && t && t !== prev) {
      const project = get().currentProject;
      window.history.pushState(
        { view: 'workspace', project, tool: t },
        '',
        `#project/${encodeURIComponent(project)}/tool/${t}`
      );
    }
  },

  currentProject: localStorage.getItem('lastProject') || '',
  setCurrentProject: (p) => {
    localStorage.setItem('lastProject', p);
    set({ currentProject: p });
  },

  enterProject: (name) => {
    localStorage.setItem('lastProject', name);
    set({ currentProject: name, view: 'workspace', activePanel: 'chat', activeTool: null });
    if (!_skipNextPush) {
      window.history.pushState({ view: 'workspace', project: name }, '', `#project/${encodeURIComponent(name)}`);
    }
  },
  backToDashboard: () => {
    set({ view: 'dashboard', activeTool: null });
    if (!_skipNextPush) {
      window.history.pushState({ view: 'dashboard' }, '', '#');
    }
  },

  openLegacyTool: (page) => {
    // All standalone tools render full-screen (no sidebar)
    const { openTabs } = get();
    const tabs = openTabs.includes(page) ? openTabs : [...openTabs, page];
    set({ view: 'tool', activePage: page, openTabs: tabs });
    if (!_skipNextPush) {
      window.history.pushState({ view: 'tool', page }, '', `#tool/${page}`);
    }
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

// ── 브라우저 히스토리 관리 ──

// 초기 상태 설정 (SPA 첫 로드 시)
const initHash = window.location.hash;
if (initHash.startsWith('#project/')) {
  // #project/name 또는 #project/name/tool/toolId
  const raw = initHash.slice(9);
  const toolSep = raw.indexOf('/tool/');
  const projectName = decodeURIComponent(toolSep >= 0 ? raw.slice(0, toolSep) : raw);
  const toolId = toolSep >= 0 ? raw.slice(toolSep + 6) : null;
  if (projectName) {
    _skipNextPush = true;
    useAppStore.getState().enterProject(projectName);
    if (toolId) useAppStore.getState().setActiveTool(toolId);
    _skipNextPush = false;
  }
} else if (initHash.startsWith('#tool/')) {
  const page = initHash.slice(6);
  if (page) {
    _skipNextPush = true;
    useAppStore.getState().openLegacyTool(page); // routes to 'tool' view (fullscreen)
    _skipNextPush = false;
  }
}

const s = useAppStore.getState();
window.history.replaceState(
  { view: s.view, project: s.currentProject, tool: s.activeTool, page: s.activePage },
  ''
);

// 뒤로가기/앞으로가기 처리
window.addEventListener('popstate', (e) => {
  const state = e.state;
  _skipNextPush = true;

  if (state?.view === 'workspace' && state?.project) {
    useAppStore.setState({
      view: 'workspace',
      currentProject: state.project,
      activeTool: state.tool || null,
      activePanel: 'chat',
    });
    localStorage.setItem('lastProject', state.project);
  } else if (state?.view === 'tool' && state?.page) {
    const { openTabs } = useAppStore.getState();
    const tabs = openTabs.includes(state.page) ? openTabs : [...openTabs, state.page];
    useAppStore.setState({ view: 'tool', activePage: state.page, openTabs: tabs, activeTool: null });
  } else if (state?.view === 'legacy' && state?.page) {
    const { openTabs } = useAppStore.getState();
    const tabs = openTabs.includes(state.page) ? openTabs : [...openTabs, state.page];
    useAppStore.setState({ view: 'legacy', activePage: state.page, openTabs: tabs, activeTool: null });
  } else {
    useAppStore.setState({ view: 'dashboard', activeTool: null });
  }

  _skipNextPush = false;
});
