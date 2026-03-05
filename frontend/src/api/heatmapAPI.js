import apiClient from './axiosConfig';

// Get heatmap grid data
export const getHeatmapGrid = async (date = null, regenerate = false) => {
  try {
    const params = {};
    if (date) params.date = date;
    if (regenerate) params.regenerate = 'true';
    
    const response = await apiClient.get('/heatmap/grid', { params });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get district-level heatmap data
export const getDistrictHeatmap = async (date = null) => {
  try {
    const params = {};
    if (date) params.date = date;
    
    const response = await apiClient.get('/heatmap/districts', { params });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get available pre-computed dates
export const getAvailableDates = async () => {
  try {
    const response = await apiClient.get('/heatmap/available-dates');
    return response.data;
  } catch (error) {
    throw error;
  }
};