import apiClient from './axiosConfig';

// Get dashboard stats
export const getStats = async () => {
  try {
    const response = await apiClient.get('/stats');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get summary stats for dashboard cards
export const getSummaryStats = async () => {
  try {
    const response = await apiClient.get('/stats/summary');
    return response.data;
  } catch (error) {
    throw error;
  }
};