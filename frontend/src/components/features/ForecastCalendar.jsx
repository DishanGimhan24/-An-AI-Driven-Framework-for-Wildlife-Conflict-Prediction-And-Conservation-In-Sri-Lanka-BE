import { formatDateDisplay } from '../../utils/helpers';
import { getRiskColor, getRiskLevel } from '../../utils/riskUtils';

export default function ForecastCalendar({ forecast }) {
  if (!forecast || !forecast.forecast) {
    return (
      <div className="text-center py-8 text-gray-500">
        No forecast data available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        7-Day Risk Forecast
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {forecast.forecast.map((day, index) => {
          const riskLevel = getRiskLevel(day.risk_score);
          const color = getRiskColor(riskLevel);
          
          return (
            <div 
              key={index}
              className="border-2 rounded-lg p-4 hover:shadow-lg transition-shadow"
              style={{ borderColor: color }}
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <p className="text-sm text-gray-600">Day {day.day}</p>
                  <p className="font-semibold text-gray-800">
                    {formatDateDisplay(day.date)}
                  </p>
                </div>
                <div 
                  className="px-3 py-1 rounded-full text-white text-xs font-bold"
                  style={{ backgroundColor: color }}
                >
                  {riskLevel}
                </div>
              </div>

              {/* Risk Score Bar */}
              <div className="mt-3">
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>Risk Score</span>
                  <span>{Math.round(day.risk_score * 100)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="h-2 rounded-full transition-all duration-300"
                    style={{ 
                      width: `${day.risk_score * 100}%`,
                      backgroundColor: color 
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}