import { useEffect, useRef, useState } from 'react';
import { useAuthStore } from './stores/authStore';
import { useAppStore } from './stores/appStore';
import { api } from './api/client';
import LoginPage from './pages/LoginPage';
import Sidebar from './components/Sidebar';
import TabContainer from './components/TabContainer';
import MobileNav from './components/MobileNav';
import ProjectDashboard from './pages/ProjectDashboard';

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < breakpoint);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < breakpoint);
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, [breakpoint]);
  return isMobile;
}

function useSessionKeepAlive() {
  const token = useAuthStore((s) => s.token);
  const setAuth = useAuthStore((s) => s.setAuth);
  const lastRefresh = useRef(0);

  useEffect(() => {
    if (!token) return;

    const tryRefresh = async () => {
      const now = Date.now();
      // 최소 30분 간격으로 갱신
      if (now - lastRefresh.current < 30 * 60 * 1000) return;
      try {
        const { token: newToken, user } = await api.refreshToken();
        setAuth(newToken, user);
        lastRefresh.current = now;
      } catch {
        // 401 → api client가 자동으로 logout 처리
      }
    };

    // 앱 마운트 시 1회 갱신
    tryRefresh();

    // 탭 복귀 시 토큰 갱신
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        tryRefresh();
      }
    };

    // 네트워크 복귀 시 토큰 갱신
    const onOnline = () => tryRefresh();

    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('online', onOnline);

    // 6시간마다 자동 갱신
    const interval = setInterval(tryRefresh, 6 * 60 * 60 * 1000);

    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('online', onOnline);
      clearInterval(interval);
    };
  }, [token, setAuth]);
}

export default function App() {
  const token = useAuthStore((s) => s.token);
  useSessionKeepAlive();
  const isMobile = useIsMobile();
  const view = useAppStore((s) => s.view);

  if (!token) {
    return <LoginPage />;
  }

  // 대시보드 뷰 (NotebookLM 스타일)
  if (view === 'dashboard') {
    return <ProjectDashboard />;
  }

  // 작업 페이지 뷰 (추후 WorkspacePage로 교체)
  // 현재는 legacy와 동일하게 동작
  if (view === 'workspace') {
    if (isMobile) {
      return (
        <div className="flex flex-col h-screen overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <TabContainer mobile hideTabBar />
          </div>
          <MobileNav />
        </div>
      );
    }
    return (
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <TabContainer />
      </div>
    );
  }

  // 레거시 뷰 (설정/관리자 등)
  if (isMobile) {
    return (
      <div className="flex flex-col h-screen overflow-hidden">
        <div className="flex-1 overflow-hidden">
          <TabContainer mobile hideTabBar />
        </div>
        <MobileNav />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <TabContainer />
    </div>
  );
}
