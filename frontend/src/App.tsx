import { useEffect, useRef } from 'react';
import { useAuthStore } from './stores/authStore';
import { api } from './api/client';
import LoginPage from './pages/LoginPage';
import Sidebar from './components/Sidebar';
import TabContainer from './components/TabContainer';

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

  if (!token) {
    return <LoginPage />;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <TabContainer />
    </div>
  );
}
