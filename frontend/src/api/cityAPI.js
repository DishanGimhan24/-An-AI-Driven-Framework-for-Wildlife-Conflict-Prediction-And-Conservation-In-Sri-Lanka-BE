import apiClient from './axiosConfig';

// Get all districts
export const getDistricts = async () => {
  try {
    const response = await apiClient.get('/districts');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get cities by district
export const getCitiesByDistrict = async (district) => {
  try {
    const response = await apiClient.get('/cities', {
      params: { district }
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get city details with geometry
export const getCityDetails = async (gid) => {
  try {
    const response = await apiClient.get('/city/details', {
      params: { gid }
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Predict risk for a city
export const predictCityRisk = async (district, city, date) => {
  try {
    const response = await apiClient.post('/predict/city', {
      district,
      city,
      date
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get city-level heatmap for district
export const getCityHeatmap = async (district, date = null) => {
  try {
    const params = { district };
    if (date) params.date = date;
    
    const response = await apiClient.get('/heatmap/cities', { params });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get forecast for a city
export const forecastCity = async (district, city, days = 7, startDate = null) => {
  try {
    const response = await apiClient.post('/forecast/city', {
      district,
      city,
      days,
      start_date: startDate
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};