import apiClient from './axiosConfig';

// Forecast risk for next N days
export const forecastRisk = async (latitude, longitude, forecastDays = 7, startDate = null) => {
  try {
    const payload = {
      latitude,
      longitude,
      forecast_days: forecastDays
    };
    
    if (startDate) {
      payload.start_date = startDate;
    }
    
    const response = await apiClient.post('/forecast', payload);
    return response.data;
  } catch (error) {
    throw error;
  }
};