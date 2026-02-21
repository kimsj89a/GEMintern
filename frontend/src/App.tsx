import Sidebar from './components/Sidebar';
import TabContainer from './components/TabContainer';

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <TabContainer />
    </div>
  );
}
