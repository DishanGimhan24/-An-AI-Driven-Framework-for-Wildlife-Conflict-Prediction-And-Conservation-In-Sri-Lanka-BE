import { getRiskPercentage } from '../../utils/helpers';
import { getRiskBgColor, getRiskColor, getRiskDescription, getRiskText } from '../../utils/riskUtils';

export default function RiskCard({ riskScore, riskLevel, showDescription = true, size = 'md' }) {
  const percentage = getRiskPercentage(riskScore);
  const color = getRiskColor(riskLevel);
  const bgColor = getRiskBgColor(riskLevel);
  const text = getRiskText(riskLevel);
  const description = getRiskDescription(riskLevel);

  const sizes = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  };

  return (
    <div className={`rounded-lg ${sizes[size]}`} style={{ backgroundColor: bgColor }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Risk Level</h3>
        <div 
          className="px-4 py-2 rounded-full text-white font-bold text-sm"
          style={{ backgroundColor: color }}
        >
          {text}
        </div>
      </div>

      {/* Risk Score Circle */}
      <div className="flex justify-center my-6">
        <div className="relative">
          <svg className="transform -rotate-90 w-32 h-32">
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="#E5E7EB"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke={color}
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${percentage * 3.52} 352`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-3xl font-bold" style={{ color }}>
                {percentage}%
              </div>
              <div className="text-xs text-gray-600">Risk Score</div>
            </div>
          </div>
        </div>
      </div>

      {/* Description */}
      {showDescription && (
        <p className="text-sm text-gray-700 text-center">{description}</p>
      )}
    </div>
  );
}