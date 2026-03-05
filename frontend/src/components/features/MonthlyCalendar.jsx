import { useState } from 'react';
import { getMonthName } from '../../utils/dateUtils';
import { getRiskColor } from '../../utils/riskUtils';

export default function MonthlyCalendar({ predictions = [] }) {
  const [currentDate, setCurrentDate] = useState(new Date());

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const monthName = getMonthName(currentDate);

  // Get first day of month and number of days
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Create array of day objects
  const days = [];
  for (let i = 0; i < firstDay; i++) {
    days.push(null);
  }
  for (let day = 1; day <= daysInMonth; day++) {
    days.push(day);
  }

  // Get risk for specific date
  const getRiskForDate = (day) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return predictions.find(p => p.date === dateStr);
  };

  // Navigate months
  const previousMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={previousMonth}
          className="p-2 transition-colors rounded-full hover:bg-gray-100"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </button>

        <h3 className="text-xl font-semibold text-gray-800">
          {monthName} {year}
        </h3>

        <button
          onClick={nextMonth}
          className="p-2 transition-colors rounded-full hover:bg-gray-100"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Week days */}
      <div className="grid grid-cols-7 gap-2 mb-2">
        {weekDays.map(day => (
          <div key={day} className="py-2 text-sm font-semibold text-center text-gray-600">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar days */}
      <div className="grid grid-cols-7 gap-2">
        {days.map((day, index) => {
          if (!day) {
            return <div key={index} className="aspect-square" />;
          }

          const risk = getRiskForDate(day);
          const color = risk ? getRiskColor(risk.risk_level) : '#e5e7eb';
          const hasRisk = !!risk;

          return (
            <div
              key={index}
              className="flex flex-col items-center justify-center p-2 transition-all border-2 rounded-lg cursor-pointer aspect-square hover:shadow-md"
              style={{ 
                borderColor: color,
                backgroundColor: hasRisk ? `${color}15` : 'transparent'
              }}
              title={hasRisk ? `${risk.risk_level} - ${Math.round(risk.risk_score * 100)}%` : 'No data'}
            >
              <span className="text-sm font-semibold text-gray-700">{day}</span>
              {hasRisk && (
                <div 
                  className="w-2 h-2 mt-1 rounded-full"
                  style={{ backgroundColor: color }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="pt-4 mt-6 border-t border-gray-200">
        <div className="flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getRiskColor('HIGH') }} />
            <span className="text-gray-600">High Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getRiskColor('MEDIUM') }} />
            <span className="text-gray-600">Medium Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getRiskColor('LOW') }} />
            <span className="text-gray-600">Low Risk</span>
          </div>
        </div>
      </div>
    </div>
  );
}