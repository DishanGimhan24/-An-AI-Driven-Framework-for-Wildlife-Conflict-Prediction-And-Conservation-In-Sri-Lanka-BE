import { createContext, useContext, useEffect, useState } from 'react';
import { getCurrentUser, isAuthenticated } from '../api/authAPI';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = () => {
      const authenticated = isAuthenticated();
      setIsLoggedIn(authenticated);
      if (authenticated) {
        const currentUser = getCurrentUser();
        setUser(currentUser);
      }
    };
    checkAuth();
  }, []);

  // Login function
  const login = (userData) => {
    setUser(userData);
    setIsLoggedIn(true);
  };

  // Logout function
  const logoutUser = () => {
    setUser(null);
    setIsLoggedIn(false);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  // Show error with auto-clear
  const showError = (message, duration = 5000) => {
    setError(message);
    setTimeout(() => setError(null), duration);
  };

  // Clear error
  const clearError = () => {
    setError(null);
  };

  const value = {
    user,
    isLoggedIn,
    selectedDistrict,
    setSelectedDistrict,
    selectedDate,
    setSelectedDate,
    loading,
    setLoading,
    error,
    showError,
    clearError,
    login,
    logout: logoutUser
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// Custom hook to use context
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};