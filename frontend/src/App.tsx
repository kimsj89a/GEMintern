import { useAuthStore } from './stores/authStore';
import LoginPage from './pages/LoginPage';
import Sidebar from './components/Sidebar';
import TabContainer from './components/TabContainer';

export default function App() {
  const token = useAuthStore((s) => s.token);

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
