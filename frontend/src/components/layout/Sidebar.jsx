import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, role, logout } = useAuth();

  const isActive = (path) => location.pathname === path;
  const profilePath = isAuthenticated
    ? (role === 'ORGANIZER' ? '/organizer/dashboard' : '/player/dashboard')
    : '/auth';

  async function handleLogout() {
    await logout();
    navigate('/');
  }

  return (
    <div className="w-20 bg-sidebar h-[92vh] flex flex-col items-center py-6 gap-8 fixed left-4 top-[4vh] rounded-full">
      <Link to="/" className="text-text-primary text-2xl">🏆</Link>

      <Link
        to="/"
        className={`p-3 rounded-full ${isActive('/') ? 'bg-text-primary/10 shadow-[0_0_20px_rgba(242,232,224,0.4)]' : ''}`}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 text-text-primary">
          <path d="M12 3l9 8h-3v9h-5v-6h-2v6H6v-9H3z" />
        </svg>
      </Link>

      <Link
        to={profilePath}
        className={`p-3 rounded-full ${isActive(profilePath) ? 'bg-text-primary/10 shadow-[0_0_20px_rgba(242,232,224,0.4)]' : ''}`}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 text-text-primary">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
        </svg>
      </Link>

      {isAuthenticated && (
        <button
          onClick={handleLogout}
          className="p-3 rounded-full mt-auto hover:bg-text-primary/10"
          title="Log out"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-6 h-6 text-text-primary">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M16 17l5-5-5-5M21 12H9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      )}
    </div>
  );
}