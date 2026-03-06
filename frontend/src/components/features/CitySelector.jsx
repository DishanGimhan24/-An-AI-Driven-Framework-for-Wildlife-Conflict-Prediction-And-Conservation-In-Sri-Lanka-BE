import { useEffect, useState } from 'react';
import { getCitiesByDistrict } from '../../api/cityAPI';

export default function CitySelector({ district, value, onChange, label = "Select City/Division", disabled = false }) {
    console.log('CitySelector props:', { district, value, disabled });
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load cities when district changes
  useEffect(() => {
    console.log('District changed:', district);
    if (district) {
      loadCities();
    } else {
      setCities([]);
    }
  }, [district]);

  const loadCities = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await getCitiesByDistrict(district);
      
      if (response.status === 'success') {
        setCities(response.data.cities);
      }
    } catch (err) {
      console.error('Failed to load cities:', err);
      setError('Failed to load cities');
      setCities([]);
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = disabled || loading || !district;

  return (
    <div className="w-full">
      <label className="block mb-2 text-sm font-medium text-gray-700">
        {label}
      </label>
      
      <select
        value={value}
        onChange={onChange}
        disabled={isDisabled}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
      >
        <option value="">
          {loading 
            ? 'Loading cities...' 
            : !district 
            ? 'Select district first' 
            : cities.length === 0 
            ? 'No cities available'
            : 'Select a city'}
        </option>
        
        {cities.map((city) => (
          <option key={city.gid} value={city.name}>
            {city.name}
          </option>
        ))}
      </select>

      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
      
      {!loading && !error && cities.length > 0 && district && (
        <p className="mt-1 text-xs text-gray-500">
          {cities.length} cities available
        </p>
      )}
    </div>
  );
}