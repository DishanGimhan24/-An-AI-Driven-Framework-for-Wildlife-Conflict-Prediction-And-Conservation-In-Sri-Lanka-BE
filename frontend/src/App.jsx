import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import Dashboard from './pages/Dashboard';
import Historical from './pages/Historical';
import Login from './pages/Login';
import MapCalendar from './pages/MapCalendar';
import RiskPrediction from './pages/RiskPrediction';

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isLoggedIn } = useApp();
  
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

// Public Route Component (redirect to dashboard if already logged in)
function PublicRoute({ children }) {
  const { isLoggedIn } = useApp();
  
  if (isLoggedIn) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/predict"
        element={
          <ProtectedRoute>
            <RiskPrediction />
          </ProtectedRoute>
        }
      />

      <Route
        path="/map-calendar"
        element={
          <ProtectedRoute>
            <MapCalendar />
          </ProtectedRoute>
        }
      />

      <Route
        path="/historical"
        element={
          <ProtectedRoute>
            <Historical />
          </ProtectedRoute>
        }
      />

      {/* Default Route */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 404 Not Found */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

// 404 Page Component
function NotFound() {
  const { isLoggedIn } = useApp();

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-primary mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">
          Page Not Found
        </h2>
        <p className="text-gray-600 mb-8">
          The page you're looking for doesn't exist.
        </p>
        <a
          href={isLoggedIn ? "/dashboard" : "/login"}
          className="inline-block bg-primary text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors"
        >
          {isLoggedIn ? "Go to Dashboard" : "Go to Login"}
        </a>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppProvider>
        <AppRoutes />
      </AppProvider>
    </Router>
  );
}

export default App;