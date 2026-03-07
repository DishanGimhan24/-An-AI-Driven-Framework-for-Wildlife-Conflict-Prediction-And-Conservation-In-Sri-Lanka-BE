import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import DatePicker from '../components/common/DatePicker';
import ErrorMessage from '../components/common/ErrorMessage';
import Loading from '../components/common/Loading';
import DistrictSelector from '../components/features/DistrictSelector';
import Footer from '../components/layout/Footer';
import Navbar from '../components/layout/Navbar';
import { useHistorical } from '../hooks/useHistorical';
import { formatDateDisplay, getTodayDate } from '../utils/helpers';

export default function Historical() {
  const [district, setDistrict] = useState('');
  const [startDate, setStartDate] = useState('2009-01-01');
  const [endDate, setEndDate] = useState(getTodayDate());

  const { conflicts, statistics, loading, error, getConflicts, getStats } = useHistorical();

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    await getConflicts(startDate, endDate, district || null);
    await getStats(startDate, endDate);
  };

  // Handle filter button
  const handleFilter = () => {
    loadData();
  };

  // Process monthly trends data
  const getMonthlyTrends = () => {
    if (!statistics?.monthly_data || statistics.monthly_data.length === 0) {
      return [];
    }

    return statistics.monthly_data.map(item => ({
      month: item.year_month,
      Conflicts: item.count
    }));
  };

  // Process district distribution
  const getDistrictData = () => {
    if (!conflicts || conflicts.length === 0) {
      return [];
    }

    // Count conflicts by district
    const districtCounts = {};
    conflicts.forEach(conflict => {
      const dist = conflict.District || conflict.district || 'Unknown';
      districtCounts[dist] = (districtCounts[dist] || 0) + 1;
    });

    // Convert to array and sort
    const sortedDistricts = Object.entries(districtCounts)
      .map(([district, count]) => ({ district, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return sortedDistricts;
  };

  // Elephant deaths by train (mock data based on uploaded PDFs)
  const getElephantDeaths = () => {
    return [
      { year: '2022', Deaths: 45 },
      { year: '2023', Deaths: 54 },
      { year: '2024', Deaths: 43 },
      { year: '2025', Deaths: 8 }
    ];
  };

  const monthlyTrends = getMonthlyTrends();
  const districtData = getDistrictData();
  const elephantDeaths = getElephantDeaths();

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <Navbar />

      <main className="container flex-1 px-4 py-8 mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-800">
            Historical Data & Analytics
          </h1>
          <p className="text-gray-600">
            Analyze past conflict patterns and trends
          </p>
        </div>

        {/* Filters */}
        <Card title="Filters" className="mb-8">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <DistrictSelector
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              label="District (Optional)"
            />

            <DatePicker
              label="Start Date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              max={endDate}
            />

            <DatePicker
              label="End Date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              min={startDate}
              max={getTodayDate()}
            />

            <div className="flex items-end">
              <Button
                onClick={handleFilter}
                variant="primary"
                className="w-full"
                loading={loading}
              >
                Apply Filters
              </Button>
            </div>
          </div>
        </Card>

        {/* Error */}
        {error && <ErrorMessage message={error} className="mb-6" />}

        {/* Loading */}
        {loading ? (
          <Loading text="Loading historical data..." />
        ) : (
          <>
            {/* Summary Stats */}
            <div className="grid grid-cols-1 gap-6 mb-8 md:grid-cols-4">
              <Card>
                <p className="mb-1 text-sm text-gray-600">Total Conflicts</p>
                <p className="text-3xl font-bold text-gray-800">
                  {statistics?.total_conflicts || conflicts.length || 0}
                </p>
                <p className="mt-1 text-xs text-gray-500">Selected period</p>
              </Card>

              <Card>
                <p className="mb-1 text-sm text-gray-600">Elephant Deaths (Train)</p>
                <p className="text-3xl font-bold text-red-600">
                  {elephantDeaths.reduce((sum, item) => sum + item.Deaths, 0)}
                </p>
                <p className="mt-1 text-xs text-gray-500">2022-2025</p>
              </Card>

              <Card>
                <p className="mb-1 text-sm text-gray-600">Districts Affected</p>
                <p className="text-3xl font-bold text-orange-600">
                  {districtData.length}
                </p>
                <p className="mt-1 text-xs text-gray-500">Unique districts</p>
              </Card>

              <Card>
                <p className="mb-1 text-sm text-gray-600">Avg Per Month</p>
                <p className="text-3xl font-bold text-blue-600">
                  {statistics?.avg_per_month || 0}
                </p>
                <p className="mt-1 text-xs text-gray-500">Conflict rate</p>
              </Card>
            </div>

            {/* Charts Row 1 */}
            <div className="grid grid-cols-1 gap-6 mb-8 lg:grid-cols-2">
              {/* Monthly Trends */}
              <Card title="Monthly Conflict Trends">
                {monthlyTrends.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={monthlyTrends}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="month" 
                        tick={{ fontSize: 12 }}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="Conflicts" 
                        stroke="#10b981" 
                        strokeWidth={2}
                        dot={{ fill: '#10b981', r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    No data available
                  </div>
                )}
              </Card>

              {/* Top 5 Districts */}
              <Card title="Top 5 Districts by Conflicts">
                {districtData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={districtData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="district" tick={{ fontSize: 12 }} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="count" fill="#3b82f6" name="Conflicts" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    No data available
                  </div>
                )}
              </Card>
            </div>

            {/* Charts Row 2 */}
            <div className="grid grid-cols-1 gap-6 mb-8 lg:grid-cols-2">
              {/* Elephant Deaths by Train */}
              <Card title="Elephant Deaths by Train Accidents">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={elephantDeaths}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="year" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="Deaths" fill="#ef4444" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              {/* Conflict Distribution by District - Placeholder */}
              <Card title="Conflict Distribution by District">
                {districtData.length > 0 ? (
                  <div className="space-y-3">
                    {districtData.map((item, index) => (
                      <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                        <span className="font-medium text-gray-700">{item.district}</span>
                        <div className="flex items-center gap-3">
                          <div className="w-32 h-2 bg-gray-200 rounded-full">
                            <div 
                              className="h-2 rounded-full bg-primary"
                              style={{ width: `${(item.count / districtData[0].count) * 100}%` }}
                            />
                          </div>
                          <span className="w-12 text-sm font-semibold text-right text-gray-600">
                            {item.count}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    No data available
                  </div>
                )}
              </Card>
            </div>

            {/* Conflicts Table */}
            <Card title={`Recent Conflicts (${conflicts.length} total)`}>
              {conflicts.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-xs font-medium text-left text-gray-500 uppercase">
                          Date
                        </th>
                        <th className="px-6 py-3 text-xs font-medium text-left text-gray-500 uppercase">
                          Location
                        </th>
                        <th className="px-6 py-3 text-xs font-medium text-left text-gray-500 uppercase">
                          Coordinates
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {conflicts.slice(0, 10).map((conflict, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 text-sm text-gray-900 whitespace-nowrap">
                            {conflict.Date ? formatDateDisplay(conflict.Date) : 'N/A'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900 whitespace-nowrap">
                            {conflict.District || conflict.district || 'Unknown'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600 whitespace-nowrap">
                            {conflict.Latitude && conflict.Longitude ? 
                              `${parseFloat(conflict.Latitude).toFixed(4)}, ${parseFloat(conflict.Longitude).toFixed(4)}` :
                              'N/A'
                            }
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  
                  {conflicts.length > 10 && (
                    <div className="py-4 text-sm text-center text-gray-600">
                      Showing 10 of {conflicts.length} conflicts
                    </div>
                  )}
                </div>
              ) : (
                <p className="py-8 text-center text-gray-600">No conflicts found for the selected period</p>
              )}
            </Card>
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}