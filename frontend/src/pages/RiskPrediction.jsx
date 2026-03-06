import { useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import ErrorMessage from '../components/common/ErrorMessage';
import Loading from '../components/common/Loading';
import CityRiskMap from '../components/features/CityRiskMap';
import PredictionForm from '../components/features/PredictionForm';
import RiskBadge from '../components/features/RiskBadge';
import Footer from '../components/layout/Footer';
import Navbar from '../components/layout/Navbar';
import { useForecast } from '../hooks/useForecast';
import { usePrediction } from '../hooks/usePrediction';
import { formatDateDisplay } from '../utils/helpers';

export default function RiskPrediction() {
  const [forecastDays, setForecastDays] = useState(7);
  const { prediction, loading: predictionLoading, error: predictionError, predict, clearPrediction } = usePrediction();
  const { forecast, loading: forecastLoading, getForecast } = useForecast();

  // Handle prediction
  const handlePredict = async (formData) => {
    const result = await predict(formData.district, formData.city, formData.date);
    
    // Also get forecast if prediction successful
    if (result && result.coordinates) {
      await getForecast(
        result.coordinates.lat,
        result.coordinates.lng,
        forecastDays,
        formData.date
      );
    }
  };

  // Handle forecast days change
  const handleForecastDaysChange = async (days) => {
    setForecastDays(days);
    if (prediction && prediction.coordinates) {
      await getForecast(
        prediction.coordinates.lat,
        prediction.coordinates.lng,
        days,
        prediction.date
      );
    }
  };

  // Prepare chart data
  const getChartData = () => {
    if (!forecast || !forecast.forecast) return [];
    
    return forecast.forecast.map(day => ({
      date: formatDateDisplay(day.date),
      risk: Math.round(day.risk_score * 100),
      day: day.day
    }));
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <Navbar />

      <main className="container flex-1 px-4 py-8 mx-auto">
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-800">
            Risk Prediction
          </h1>
          <p className="text-gray-600">
            Predict wildlife conflict risk for any city and date
          </p>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Input Form */}
          <div className="lg:col-span-1">
            <Card title="Enter Location Details">
              <PredictionForm
                onSubmit={handlePredict}
                loading={predictionLoading}
              />
              
              {prediction && (
                <Button
                  onClick={clearPrediction}
                  variant="outline"
                  className="w-full mt-4"
                >
                  Clear & Predict Again
                </Button>
              )}
            </Card>

            {predictionError && (
              <div className="mt-4">
                <ErrorMessage message={predictionError} />
              </div>
            )}
          </div>

          {/* Results */}
          <div className="space-y-6 lg:col-span-2">
            {predictionLoading ? (
              <Card>
                <Loading message="Analyzing risk factors..." />
              </Card>
            ) : prediction ? (
              <>
                {/* Risk Result Card */}
                <Card title="Prediction Result">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-semibold text-gray-800">
                          {prediction.city}, {prediction.district}
                        </h3>
                        <p className="text-sm text-gray-600">
                          Date: {formatDateDisplay(prediction.date)}
                        </p>
                      </div>
                      <RiskBadge level={prediction.risk_level} size="large" />
                    </div>

                    <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-gray-50">
                      <div>
                        <p className="text-sm text-gray-600">Risk Score</p>
                        <p className="text-2xl font-bold text-gray-800">
                          {Math.round(prediction.risk_score * 100)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Confidence</p>
                        <p className="text-2xl font-bold text-gray-800">
                          {Math.round(prediction.confidence * 100)}%
                        </p>
                      </div>
                    </div>

                    {prediction.contributing_factors && (
                      <div>
                        <h4 className="mb-2 font-semibold text-gray-700">Contributing Factors</h4>
                        <ul className="space-y-1 text-sm text-gray-600">
                          {Object.entries(prediction.contributing_factors).map(([key, value]) => (
                            <li key={key} className="flex justify-between">
                              <span>{key.replace(/_/g, ' ').toUpperCase()}:</span>
                              <span className="font-medium">{value}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Card>

                {/* City Map */}
                <Card title="Location Map">
                  <CityRiskMap
                    district={prediction.district}
                    city={prediction.city}
                    riskLevel={prediction.risk_level}
                    riskScore={prediction.risk_score}
                  />
                </Card>

                {/* Forecast Section */}
                <Card title="Risk Forecast">
                  <div className="mb-4">
                    <label className="block mb-2 text-sm font-medium text-gray-700">
                      Forecast Days
                    </label>
                    <div className="flex gap-2">
                      {[7, 14, 30].map(days => (
                        <button
                          key={days}
                          onClick={() => handleForecastDaysChange(days)}
                          className={`px-4 py-2 rounded-lg transition-colors ${
                            forecastDays === days
                              ? 'bg-primary text-white'
                              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                          }`}
                        >
                          {days} Days
                        </button>
                      ))}
                    </div>
                  </div>

                  {forecastLoading ? (
                    <Loading message="Generating forecast..." />
                  ) : forecast && forecast.forecast ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={getChartData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="date" 
                          tick={{ fontSize: 12 }}
                          angle={-45}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis 
                          label={{ value: 'Risk %', angle: -90, position: 'insideLeft' }}
                        />
                        <Tooltip />
                        <Legend />
                        <Line 
                          type="monotone" 
                          dataKey="risk" 
                          stroke="#10B981" 
                          strokeWidth={2}
                          name="Risk Score %"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : null}
                </Card>
              </>
            ) : (
              <Card>
                <div className="py-12 text-center text-gray-500">
                  <p>Select a city and date to predict risk</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}