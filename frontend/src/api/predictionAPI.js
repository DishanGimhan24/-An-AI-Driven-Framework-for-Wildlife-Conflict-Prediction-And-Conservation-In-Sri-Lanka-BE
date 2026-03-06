import apiClient from './axiosConfig';

// Predict risk for single location
export const predictRisk = async (latitude, longitude, date) => {
  try {
    const response = await apiClient.post('/predict', {
      latitude,
      longitude,
      date
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Predict risk for multiple locations (batch)
export const predictBatch = async (locations) => {
  try {
    const response = await apiClient.post('/predict/batch', {
      locations
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Get feature importance
export const getFeatureImportance = async () => {
  try {
    const response = await apiClient.get('/model/feature-importance');
    return response.data;
  } catch (error) {
    throw error;
  }
};