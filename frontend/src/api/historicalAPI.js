import apiClient from './axiosConfig';

// Get historical conflicts
export const getHistoricalConflicts = async (startDate = null, endDate = null, district = null) => {
  try {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (district) params.district = district;
    
    // Changed from '/historical/conflicts' to '/historical-conflicts'
    const response = await apiClient.get('/conflicts', { params });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get statistics
export const getStatistics = async (startDate = null, endDate = null) => {
  try {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    
    const response = await apiClient.get('/conflict-stats', { params });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get conflicts by district
export const getConflictsByDistrict = async (district) => {
  try {
    // Changed from '/historical/conflicts' to '/historical-conflicts'
    const response = await apiClient.get(`/conflicts`, {
      params: { district }
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};