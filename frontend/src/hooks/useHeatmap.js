import { useState } from 'react';
import { getAvailableDates, getDistrictHeatmap, getHeatmapGrid } from '../api/heatmapAPI';
import { useApp } from '../context/AppContext';

export const useHeatmap = () => {
  const [heatmapData, setHeatmapData] = useState(null);
  const [districtData, setDistrictData] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { showError } = useApp();

  // Load grid-based heatmap
  const loadHeatmap = async (date = null, regenerate = false) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getHeatmapGrid(date, regenerate);
      
      if (response.status === 'success') {
        setHeatmapData(response.data);
        return response.data;
      } else {
        throw new Error(response.message || 'Failed to load heatmap');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to load heatmap';
      setError(errorMsg);
      showError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Load district-level heatmap
  const loadDistrictHeatmap = async (date = null) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getDistrictHeatmap(date);
      
      if (response.status === 'success') {
        setDistrictData(response.data);
        return response.data;
      } else {
        throw new Error(response.message || 'Failed to load district heatmap');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to load district heatmap';
      setError(errorMsg);
      showError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Load available dates
  const loadAvailableDates = async () => {
    try {
      const response = await getAvailableDates();
      
      if (response.status === 'success') {
        setAvailableDates(response.data.dates);
        return response.data.dates;
      }
    } catch (err) {
      console.error('Failed to load available dates:', err);
      return [];
    }
  };

  // Clear heatmap
  const clearHeatmap = () => {
    setHeatmapData(null);
    setDistrictData(null);
    setError(null);
  };

  return {
    heatmapData,
    districtData,
    availableDates,
    loading,
    error,
    loadHeatmap,
    loadDistrictHeatmap,
    loadAvailableDates,
    clearHeatmap
  };
};