import { useState } from 'react';
import { getCityHeatmap } from '../api/cityAPI';
import { useApp } from '../context/AppContext';

export const useCityHeatmap = () => {
  const [cityHeatmapData, setCityHeatmapData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { showError } = useApp();

  // Load city-level heatmap
  const loadCityHeatmap = async (district, date = null) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getCityHeatmap(district, date);
      
      if (response.status === 'success') {
        setCityHeatmapData(response.data);
        return response.data;
      } else {
        throw new Error(response.message || 'Failed to load city heatmap');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to load city heatmap';
      setError(errorMsg);
      showError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Clear data
  const clearCityHeatmap = () => {
    setCityHeatmapData(null);
    setError(null);
  };

  return {
    cityHeatmapData,
    loading,
    error,
    loadCityHeatmap,
    clearCityHeatmap
  };
};