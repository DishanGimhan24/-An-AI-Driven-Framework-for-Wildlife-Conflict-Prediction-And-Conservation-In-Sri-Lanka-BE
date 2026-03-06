export default function RiskBadge({ level, size = 'medium' }) {
  // Get badge color based on risk level
  const getBadgeColor = () => {
    switch (level) {
      case 'HIGH':
        return 'bg-red-600 text-white';
      case 'MEDIUM':
        return 'bg-yellow-500 text-white';
      case 'LOW':
        return 'bg-green-600 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  // Get size classes
  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'px-2 py-1 text-xs';
      case 'large':
        return 'px-6 py-3 text-lg';
      case 'medium':
      default:
        return 'px-4 py-2 text-sm';
    }
  };

  return (
    <span 
      className={`inline-block font-bold rounded-full ${getBadgeColor()} ${getSizeClasses()}`}
    >
      {level}
    </span>
  );
}