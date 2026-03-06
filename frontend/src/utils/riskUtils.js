import { RISK_COLORS, RISK_LEVELS, RISK_THRESHOLDS } from './constants';

// Get risk level from risk score
export const getRiskLevel = (riskScore) => {
  if (riskScore >= RISK_THRESHOLDS.HIGH) {
    return RISK_LEVELS.HIGH;
  } else if (riskScore >= RISK_THRESHOLDS.MEDIUM) {
    return RISK_LEVELS.MEDIUM;
  } else {
    return RISK_LEVELS.LOW;
  }
};

// Get risk color based on level
export const getRiskColor = (riskLevel) => {
  return RISK_COLORS[riskLevel] || RISK_COLORS.LOW;
};

// Get risk color from score directly
export const getRiskColorFromScore = (riskScore) => {
  const level = getRiskLevel(riskScore);
  return getRiskColor(level);
};

// Get risk background color (lighter shade)
export const getRiskBgColor = (riskLevel) => {
  switch (riskLevel) {
    case RISK_LEVELS.HIGH:
      return '#FEE2E2'; // light red
    case RISK_LEVELS.MEDIUM:
      return '#FEF3C7'; // light yellow
    case RISK_LEVELS.LOW:
      return '#D1FAE5'; // light green
    default:
      return '#F3F4F6'; // gray
  }
};

// Get risk text for display
export const getRiskText = (riskLevel) => {
  switch (riskLevel) {
    case RISK_LEVELS.HIGH:
      return 'High Risk';
    case RISK_LEVELS.MEDIUM:
      return 'Medium Risk';
    case RISK_LEVELS.LOW:
      return 'Low Risk';
    default:
      return 'Unknown';
  }
};

// Get risk description
export const getRiskDescription = (riskLevel) => {
  switch (riskLevel) {
    case RISK_LEVELS.HIGH:
      return 'High probability of conflict. Take immediate precautions.';
    case RISK_LEVELS.MEDIUM:
      return 'Moderate risk. Stay alert and monitor the situation.';
    case RISK_LEVELS.LOW:
      return 'Low risk. Normal activities can continue.';
    default:
      return 'Risk level unknown.';
  }
};

// Sort predictions by risk score (highest first)
export const sortByRiskScore = (predictions) => {
  return [...predictions].sort((a, b) => b.risk_score - a.risk_score);
};

// Filter predictions by risk level
export const filterByRiskLevel = (predictions, riskLevel) => {
  return predictions.filter(p => p.risk_level === riskLevel);
};