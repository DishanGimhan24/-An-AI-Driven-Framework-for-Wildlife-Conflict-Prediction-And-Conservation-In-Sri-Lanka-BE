import { useState } from 'react';
import { forecastRisk } from '../api/forecastAPI';
import { useApp } from '../context/AppContext';

export const useForecast = () => {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { showError } = useApp();

  // Get forecast for location
  const getForecast = async (latitude, longitude, forecastDays = 7, startDate = null) => {
    setLoading(true);
    setError(null);
    setForecast(null);

    try {
      const response = await forecastRisk(latitude, longitude, forecastDays, startDate);
      
      if (response.status === 'success') {
        // Transform API response to match frontend expectations
        const transformedData = {
          location: response.data.location,
          start_date: response.data.start_date,
          forecast: response.data.forecasts,  // Map "forecasts" → "forecast"
          summary: response.data.summary
        };
        
        setForecast(transformedData);
        return transformedData;
      } else {
        throw new Error(response.message || 'Forecast failed');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to get forecast';
      setError(errorMsg);
      showError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Clear forecast
  const clearForecast = () => {
    setForecast(null);
    setError(null);
  };

  return {
    forecast,
    loading,
    error,
    getForecast,
    clearForecast
  };
};