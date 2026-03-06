import { useEffect, useState } from 'react';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import DatePicker from '../components/common/DatePicker';
import ErrorMessage from '../components/common/ErrorMessage';
import Loading from '../components/common/Loading';
import CitySelector from '../components/features/CitySelector';
import DistrictSelector from '../components/features/DistrictSelector';
import MonthlyCalendar from '../components/features/MonthlyCalendar';
import RiskHeatmap from '../components/features/RiskHeatmap';
import Footer from '../components/layout/Footer';
import Navbar from '../components/layout/Navbar';
import { useCityHeatmap } from '../hooks/useCityHeatmap';
import { useForecast } from '../hooks/useForecast';
import { useHeatmap } from '../hooks/useHeatmap';
import { DISTRICT_COORDINATES } from '../utils/constants';
import { getTodayDate } from '../utils/helpers';

export default function MapCalendar() {
  const [activeTab, setActiveTab] = useState('map');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedDate, setSelectedDate] = useState(getTodayDate());
  const [calendarPredictions, setCalendarPredictions] = useState([]);
  const [viewMode, setViewMode] = useState('district');
  
  const { getForecast, loading: forecasting } = useForecast();
  const { 
    districtData, 
    loading: loadingHeatmap, 
    error: heatmapError, 
    loadDistrictHeatmap 
  } = useHeatmap();
  
  const {
    cityHeatmapData,
    loading: loadingCityHeatmap,
    loadCityHeatmap
  } = useCityHeatmap();

  // Load district heatmap on mount
  useEffect(() => {
    if (activeTab === 'map' && viewMode === 'district') {
      loadDistrictHeatmap(getTodayDate());
    }
  }, [activeTab, viewMode]);

  // Load city heatmap when district changes
  useEffect(() => {
    if (activeTab === 'map' && viewMode === 'city' && selectedDistrict) {
      loadCityHeatmap(selectedDistrict, selectedDate);
    }
  }, [selectedDistrict, selectedDate, viewMode, activeTab]);

  // Generate calendar forecast
  const handleGenerateCalendar = async () => {
    if (!selectedDistrict) {
      alert('Please select a district first');
      return;
    }

    const coords = DISTRICT_COORDINATES[selectedDistrict];
    
    if (!coords || !coords.lat || !coords.lng) {
      alert(`Coordinates not found for ${selectedDistrict}`);
      return;
    }
    
    const result = await getForecast(coords.lat, coords.lng, 30, selectedDate);
    
    if (result && result.forecast) {
      setCalendarPredictions(result.forecast.map(day => ({
        date: day.date,
        risk_score: day.risk_score,
        risk_level: day.risk_level
      })));
    }
  };

  // Reload heatmap with new date
  const handleDateChange = async (e) => {
    const newDate = e.target.value;
    setSelectedDate(newDate);
    
    if (activeTab === 'map') {
      if (viewMode === 'district') {
        await loadDistrictHeatmap(newDate);
      } else if (viewMode === 'city' && selectedDistrict) {
        await loadCityHeatmap(selectedDistrict, newDate);
      }
    }
  };

  const currentHeatmapData = viewMode === 'city' ? cityHeatmapData : districtData;
  const currentLoading = viewMode === 'city' ? loadingCityHeatmap : loadingHeatmap;

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="container flex-1 px-4 py-8 mx-auto">
        <h1 className="mb-6 text-3xl font-bold text-gray-800">
          Risk Map & Calendar
        </h1>

        {/* Tabs */}
        <div className="flex mb-6 space-x-4 border-b border-gray-200">
          <button
            onClick={() => setActiveTab('map')}
            className={`pb-3 px-4 font-medium transition-colors ${
              activeTab === 'map'
                ? 'text-primary border-b-2 border-primary'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Risk Map
          </button>
          <button
            onClick={() => setActiveTab('calendar')}
            className={`pb-3 px-4 font-medium transition-colors ${
              activeTab === 'calendar'
                ? 'text-primary border-b-2 border-primary'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Risk Calendar
          </button>
        </div>

        {/* Map Tab */}
        {activeTab === 'map' && (
          <div className="space-y-6">
            {/* View Mode Toggle */}
            <Card>
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">View Mode</h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setViewMode('district')}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      viewMode === 'district'
                        ? 'bg-primary text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    District View
                  </button>
                  <button
                    onClick={() => setViewMode('city')}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      viewMode === 'city'
                        ? 'bg-primary text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    City View
                  </button>
                </div>
              </div>
            </Card>

            {/* Controls */}
            <Card title="Map Settings">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <DatePicker
                  label="Select Date"
                  value={selectedDate}
                  onChange={handleDateChange}
                />
                
                {viewMode === 'city' && (
                  <>
                    <DistrictSelector
                      value={selectedDistrict}
                      onChange={(e) => setSelectedDistrict(e.target.value)}
                      label="Select District"
                    />
                    <CitySelector
                      district={selectedDistrict}
                      value={selectedCity}
                      onChange={(e) => setSelectedCity(e.target.value)}
                      label="Select City/Division"
                    />
                  </>
                )}
              </div>
            </Card>

            {/* Map */}
            <Card>
              {currentLoading ? (
                <Loading message="Loading map data..." />
              ) : heatmapError ? (
                <ErrorMessage message={heatmapError} />
              ) : currentHeatmapData ? (
                <>
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold">
                      {viewMode === 'city' ? `${selectedDistrict} - City Level Risk` : 'District Level Risk Map'}
                    </h3>
                    <p className="mt-1 text-sm text-gray-600">
                      Date: {selectedDate}
                    </p>
                  </div>
                  <RiskHeatmap 
                    districtData={currentHeatmapData}
                    viewMode={viewMode}
                  />
                </>
              ) : (
                <div className="py-12 text-center text-gray-600">
                  {viewMode === 'city' ? 'Select a district to view city-level risks' : 'Loading map...'}
                </div>
              )}
            </Card>

            {/* Summary */}
            {currentHeatmapData && currentHeatmapData.summary && (
              <Card title="Risk Summary">
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 text-center rounded-lg bg-red-50">
                    <p className="text-2xl font-bold text-red-600">
                      {currentHeatmapData.summary.high_risk_cities || 
                       currentHeatmapData.summary.high_risk_districts || 0}
                    </p>
                    <p className="text-sm text-gray-600">High Risk</p>
                  </div>
                  <div className="p-4 text-center rounded-lg bg-yellow-50">
                    <p className="text-2xl font-bold text-yellow-600">
                      {currentHeatmapData.summary.medium_risk_cities || 
                       currentHeatmapData.summary.medium_risk_districts || 0}
                    </p>
                    <p className="text-sm text-gray-600">Medium Risk</p>
                  </div>
                  <div className="p-4 text-center rounded-lg bg-green-50">
                    <p className="text-2xl font-bold text-green-600">
                      {currentHeatmapData.summary.low_risk_cities || 
                       currentHeatmapData.summary.low_risk_districts || 0}
                    </p>
                    <p className="text-sm text-gray-600">Low Risk</p>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Calendar Tab */}
        {activeTab === 'calendar' && (
          <div className="space-y-6">
            <Card title="Calendar Settings">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <DistrictSelector
                  value={selectedDistrict}
                  onChange={(e) => setSelectedDistrict(e.target.value)}
                  label="Select District"
                />
                <DatePicker
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  label="Start Date"
                  min={getTodayDate()}
                />
              </div>
              <Button
                onClick={handleGenerateCalendar}
                variant="primary"
                className="w-full mt-4"
                loading={forecasting}
                disabled={!selectedDistrict || forecasting}
              >
                Generate 30-Day Calendar
              </Button>
            </Card>

            {forecasting && <Loading message="Generating forecast..." />}

            {calendarPredictions.length > 0 && (
              <Card title="Monthly Risk Calendar">
                <MonthlyCalendar predictions={calendarPredictions} />
              </Card>
            )}
          </div>
        )}
      </div>

      <Footer />
    </div>
  );
}