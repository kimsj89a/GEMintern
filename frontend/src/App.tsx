import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuthStore } from './stores/authStore';
import { api } from './api/client';
import LoginPage from './pages/LoginPage';
import Sidebar from './components/Sidebar';
import TabContainer from './components/TabContainer';

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobileMenu = useCallback(() => setMobileMenuOpen(false), []);

  if (!token) {
    return <LoginPage />;
  }

  if (isMobile) {
    return (
      <div className="flex flex-col h-screen overflow-hidden">
        {/* 모바일 헤더 */}
        <div className="flex items-center justify-between px-3 py-2 bg-slate-900 shrink-0">
          <button onClick={() => setMobileMenuOpen(true)} className="w-9 h-9 flex items-center justify-center text-white rounded-lg hover:bg-white/10">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded flex items-center justify-center text-xs" style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}>💎</div>
            <span className="text-sm font-bold text-white">GEM Intern</span>
          </div>
          <div className="w-9" />
        </div>
        {/* 모바일 콘텐츠 */}
        <div className="flex-1 overflow-hidden">
          <TabContainer mobile />
        </div>
        {/* 모바일 사이드바 오버레이 */}
        {mobileMenuOpen && (
          <>
            <div className="fixed inset-0 bg-black/50 z-40" onClick={closeMobileMenu} />
            <div className="fixed inset-y-0 left-0 z-50 w-[280px] animate-slide-in">
              <Sidebar onNavigate={closeMobileMenu} />
            </div>
          </>
        )}
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
