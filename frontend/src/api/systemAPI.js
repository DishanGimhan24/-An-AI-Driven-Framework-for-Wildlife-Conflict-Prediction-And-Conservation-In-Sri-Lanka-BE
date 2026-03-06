import apiClient from './axiosConfig';

// Health check
export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get system status
export const getSystemStatus = async () => {
  try {
    const response = await apiClient.get('/status');
    return response.data;
  } catch (error) {
    throw error;
  }
};