import { Link, useLocation, useNavigate } from 'react-router-dom';
import { logout } from '../../api/authAPI';
import { useApp } from '../../context/AppContext';

export default function Navbar() {
  const { user, logout: logoutContext, isLoggedIn } = useApp();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    logoutContext();
    navigate('/login');
  };

  if (location.pathname === '/login') {
    return null;
  }

  return (
    <nav className="bg-primary shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="bg-white rounded-full p-2">
              <svg className="h-8 w-8 text-primary" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">ELESAFE</h1>
              <p className="text-xs text-white/90">Wildlife Conflict Prediction</p>
            </div>
          </Link>

          <div className="hidden md:flex items-center gap-6">
            <Link to="/dashboard" className="text-white hover:text-white/80 transition-colors">
              Dashboard
            </Link>
            <Link to="/predict" className="text-white hover:text-white/80 transition-colors">
              Predict Risk
            </Link>
            <Link to="/map-calendar" className="text-white hover:text-white/80 transition-colors">
              Map & Calendar
            </Link>
            <Link to="/historical" className="text-white hover:text-white/80 transition-colors">
              Historical Data
            </Link>
          </div>

          {isLoggedIn && (
            <div className="flex items-center gap-4">
              <div className="hidden md:block text-right">
                <p className="text-sm font-medium text-white">{user?.username || 'User'}</p>
                <p className="text-xs text-white/90">Wildlife Officer</p>
              </div>
              <button onClick={handleLogout} className="bg-white text-primary px-4 py-2 rounded-lg hover:bg-white/90 transition-colors text-sm font-medium">
                Logout
              </button>
            </div>
          )}
        </div>

        <div className="md:hidden pb-4">
          <div className="flex flex-col gap-2">
            <Link to="/dashboard" className="text-white hover:text-white/80 transition-colors py-1">
              Dashboard
            </Link>
            <Link to="/predict" className="text-white hover:text-white/80 transition-colors py-1">
              Predict Risk
            </Link>
            <Link to="/map-calendar" className="text-white hover:text-white/80 transition-colors py-1">
              Map & Calendar
            </Link>
            <Link to="/historical" className="text-white hover:text-white/80 transition-colors py-1">
              Historical Data
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}