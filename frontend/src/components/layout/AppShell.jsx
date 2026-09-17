import Sidebar from './Sidebar';

export default function AppShell({ children }) {
  return (
    <div className="app-gradient-bg">
      <Sidebar />
      <div className="ml-28 p-8">
        {children}
      </div>
    </div>
  );
}