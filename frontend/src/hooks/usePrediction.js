import { useState } from 'react';
import { predictCityRisk } from '../api/cityAPI';
import { useApp } from '../context/AppContext';

export const usePrediction = () => {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { showError } = useApp();

  const predict = async (district, city, date) => {
    setLoading(true);
    setError(null);

    try {
      const response = await predictCityRisk(district, city, date);
      
      if (response.status === 'success') {
        setPrediction(response.data);
        return response.data;
      } else {
        throw new Error(response.message || 'Prediction failed');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to predict risk';
      setError(errorMsg);
      showError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearPrediction = () => {
    setPrediction(null);
    setError(null);
  };

  return {
    prediction,
    loading,
    error,
    predict,
    clearPrediction
  };
};