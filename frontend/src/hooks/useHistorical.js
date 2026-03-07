import { useState } from 'react';
import { getConflictsByDistrict, getHistoricalConflicts, getStatistics } from '../api/historicalAPI';
import { useApp } from '../context/AppContext';

export const useHistorical = () => {
  const [conflicts, setConflicts] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { showError } = useApp();

  // Get historical conflicts
  const getConflicts = async (startDate = null, endDate = null, district = null) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getHistoricalConflicts(startDate, endDate, district);
      
      if (response.status === 'success') {
        setConflicts(response.data.conflicts || []);
        return response.data.conflicts;
      } else {
        throw new Error(response.message || 'Failed to load conflicts');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to load historical data';
      setError(errorMsg);
      showError(errorMsg);
      return [];
    } finally {
      setLoading(false);
    }
  };

  // Get statistics
  const getStats = async (startDate = null, endDate = null) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getStatistics(startDate, endDate);
      
      if (response.status === 'success') {
        setStatistics(response.data);
        return response.data;
      } else {
        throw new Error(response.message || 'Failed to load statistics');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to load statistics';
      setError(errorMsg);
      showError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Get conflicts by district
  const getDistrictConflicts = async (district) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getConflictsByDistrict(district);
      
      if (response.status === 'success') {
        return response.data.conflicts || [];
      } else {
        throw new Error(response.message || 'Failed to load district conflicts');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to load district conflicts';
      setError(errorMsg);
      showError(errorMsg);
      return [];
    } finally {
      setLoading(false);
    }
  };

  return {
    conflicts,
    statistics,
    loading,
    error,
    getConflicts,
    getStats,
    getDistrictConflicts
  };
};