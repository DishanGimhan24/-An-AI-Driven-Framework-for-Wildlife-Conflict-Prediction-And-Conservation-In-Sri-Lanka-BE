import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getStats } from '../api/statsAPI';
import { checkHealth } from '../api/systemAPI';
import Card from '../components/common/Card';
import ErrorMessage from '../components/common/ErrorMessage';
import Loading from '../components/common/Loading';
import StatCard from '../components/features/StatCard';
import Footer from '../components/layout/Footer';
import Navbar from '../components/layout/Navbar';
import { formatDate } from '../utils/helpers';

export default function Dashboard() {
  // State
  const [systemStatus, setSystemStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load data on mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError('');

    try {
      // Load both system status and stats
      const [healthData, statsData] = await Promise.all([
        checkHealth(),
        getStats()
      ]);

      setSystemStatus(healthData);
      setStats(statsData.data);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Quick actions data
  const quickActions = [
    {
      title: 'Predict Risk',
      description: 'Get real-time risk predictions for any location',
      icon: (
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
          <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
        </svg>
      ),
      color: 'bg-primary',
      link: '/predict'
    },
    {
      title: 'View Map',
      description: 'Explore risk areas on interactive map',
      icon: (
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M12 1.586l-4 4v12.828l4-4V1.586zM3.707 3.293A1 1 0 002 4v10a1 1 0 00.293.707L6 18.414V5.586L3.707 3.293zM17.707 5.293L14 1.586v12.828l2.293 2.293A1 1 0 0018 16V6a1 1 0 00-.293-.707z" clipRule="evenodd" />
        </svg>
      ),
      color: 'bg-blue-600',
      link: '/map-calendar'
    },
    {
      title: 'Historical Data',
      description: 'Analyze past conflicts and trends',
      icon: (
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
        </svg>
      ),
      color: 'bg-yellow-600',
      link: '/historical'
    }
  ];

  // Render loading state
  if (loading) {
    return (
      <div className="flex flex-col min-h-screen bg-gray-50">
        <Navbar />
        <main className="flex items-center justify-center flex-1">
          <Loading text="Loading dashboard..." />
        </main>
        <Footer />
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="flex flex-col min-h-screen bg-gray-50">
        <Navbar />
        <main className="container flex-1 px-4 py-8 mx-auto">
          <ErrorMessage message={error} />
          <button
            onClick={loadDashboardData}
            className="px-4 py-2 mt-4 text-white rounded-lg bg-primary hover:bg-green-700"
          >
            Retry
          </button>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <Navbar />

      <main className="container flex-1 px-4 py-8 mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="mb-2 text-3xl font-bold text-gray-800">
              Wildlife Conflict Dashboard
            </h1>
            <p className="text-gray-600">
              Monitor and analyze wildlife conflict risks in real-time
            </p>
          </div>
          <button
            onClick={loadDashboardData}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
            </svg>
            Refresh
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-6 mb-8 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="High Risk Areas"
            value={stats?.predictions?.high_risk_count || 0}
            icon={(
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            )}
            color="danger"
          />

          <StatCard
            title="Medium Risk Areas"
            value={stats?.predictions?.medium_risk_count || 0}
            icon={(
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            )}
            color="warning"
          />

          <StatCard
            title="Low Risk Areas"
            value={stats?.predictions?.low_risk_count || 0}
            icon={(
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
            color="info"
          />

          <StatCard
            title="Total Predictions"
            value={stats?.predictions?.total_predictions || 0}
            icon={(
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
              </svg>
            )}
            color="primary"
          />
        </div>

        {/* Quick Actions */}
        <Card title="Quick Actions" className="mb-8">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {quickActions.map((action, index) => (
              <Link
                key={index}
                to={action.link}
                className="p-6 transition-all border-2 border-gray-200 rounded-lg group hover:border-primary hover:shadow-lg"
              >
                <div className={`${action.color} w-12 h-12 rounded-lg flex items-center justify-center text-white mb-4 group-hover:scale-110 transition-transform`}>
                  {action.icon}
                </div>
                <h3 className="mb-2 text-lg font-semibold text-gray-800 transition-colors group-hover:text-primary">
                  {action.title}
                </h3>
                <p className="text-sm text-gray-600">
                  {action.description}
                </p>
              </Link>
            ))}
          </div>
        </Card>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          {/* System Status */}
          <Card title="System Status">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-green-50">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                  <span className="font-medium text-gray-800">API Status</span>
                </div>
                <span className="font-semibold text-green-600">
                  {systemStatus?.api || 'Running'}
                </span>
              </div>

              <div className="flex items-center justify-between p-4 rounded-lg bg-blue-50">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${systemStatus?.model_loaded ? 'bg-blue-500' : 'bg-red-500'}`} />
                  <span className="font-medium text-gray-800">Model Status</span>
                </div>
                <span className={`font-semibold ${systemStatus?.model_loaded ? 'text-blue-600' : 'text-red-600'}`}>
                  {systemStatus?.model_loaded ? 'Loaded' : 'Not Loaded'}
                </span>
              </div>

              <div className="flex items-center justify-between p-4 rounded-lg bg-purple-50">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${systemStatus?.data_loaded ? 'bg-purple-500' : 'bg-red-500'}`} />
                  <span className="font-medium text-gray-800">Data Status</span>
                </div>
                <span className={`font-semibold ${systemStatus?.data_loaded ? 'text-purple-600' : 'text-red-600'}`}>
                  {systemStatus?.data_loaded ? 'Loaded' : 'Not Loaded'}
                </span>
              </div>
            </div>
          </Card>

          {/* Recent Predictions */}
          <Card title="Recent Predictions">
            {stats?.predictions?.recent_predictions?.length > 0 ? (
              <div className="space-y-3 overflow-y-auto max-h-80">
                {stats.predictions.recent_predictions.map((pred, index) => (
                  <div key={index} className="flex items-start gap-4 pb-3 border-b last:border-0">
                    <div className={`p-2 rounded-lg ${
                      pred.risk_level === 'HIGH' ? 'bg-red-100' :
                      pred.risk_level === 'MEDIUM' ? 'bg-yellow-100' :
                      'bg-green-100'
                    }`}>
                      <svg className={`h-5 w-5 ${
                        pred.risk_level === 'HIGH' ? 'text-red-600' :
                        pred.risk_level === 'MEDIUM' ? 'text-yellow-600' :
                        'text-green-600'
                      }`} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-800">
                        {pred.risk_level} Risk - {pred.risk_score.toFixed(2)}
                      </p>
                      <p className="text-sm text-gray-600">
                        Lat: {pred.latitude.toFixed(4)}, Lon: {pred.longitude.toFixed(4)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatDate(pred.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-gray-600">No recent predictions</p>
            )}
          </Card>
        </div>
      </main>

      <Footer />
    </div>
  );
}