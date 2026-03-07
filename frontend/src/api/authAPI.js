

// Login (mock for now - adjust based on your backend)
export const login = async (username, password) => {
  try {
    // Since your backend doesn't have auth yet, mock this
    // You can implement backend auth later
    
    // Mock response
    if (username && password) {
      const mockToken = 'mock-jwt-token-' + Date.now();
      localStorage.setItem('token', mockToken);
      localStorage.setItem('user', JSON.stringify({ username }));
      
      return {
        status: 'success',
        data: {
          token: mockToken,
          user: { username }
        }
      };
    } else {
      throw new Error('Invalid credentials');
    }
    
    // When you implement backend auth, use this:
    // const response = await apiClient.post('/auth/login', { username, password });
    // localStorage.setItem('token', response.data.token);
    // localStorage.setItem('user', JSON.stringify(response.data.user));
    // return response.data;
    
  } catch (error) {
    throw error;
  }
};

// Logout
export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return localStorage.getItem('token') !== null;
};

// Get current user
export const getCurrentUser = () => {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
};