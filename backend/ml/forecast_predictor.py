import sys
import os
from datetime import datetime, timedelta
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RISK_THRESHOLD_HIGH, RISK_THRESHOLD_MEDIUM
from ml.predictor import predictor


class ForecastPredictor:
    """Generate 7-day risk forecasts using Random Forest model"""

    def __init__(self):
        self.predictor = predictor

    def forecast_7_days(self, latitude, longitude, start_date):
        """
        Forecast risk for next 7 days with temporal variations
        """
        try:
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_dt = start_date

            forecasts = []

            # Set seed for reproducible variations
            random.seed(int(start_dt.timestamp()))

            # Generate predictions for 7 consecutive days
            for day_offset in range(7):
                forecast_date = start_dt + timedelta(days=day_offset)
                date_str = forecast_date.strftime('%Y-%m-%d')

                # Get base prediction
                result = self.predictor.predict(latitude, longitude, date_str)

                if result:
                    base_risk = result['risk_score']

                    # Add temporal variation (±5-10% based on day)
                    # Simulate weather variability, animal movement patterns
                    variation = random.uniform(-0.08, 0.08)  # -8% to +8%

                    # Apply weekly pattern (mid-week slightly higher risk)
                    day_of_week = forecast_date.weekday()
                    if day_of_week in [2, 3, 4]:  # Wed, Thu, Fri
                        variation += 0.03

                    # Calculate adjusted risk
                    adjusted_risk = base_risk + variation
                    adjusted_risk = max(0.0, min(1.0, adjusted_risk))  # Clamp to 0-1

                    # Recalculate risk level
                    if adjusted_risk >= RISK_THRESHOLD_HIGH:
                        risk_level = "HIGH"
                    elif adjusted_risk >= RISK_THRESHOLD_MEDIUM:
                        risk_level = "MEDIUM"
                    else:
                        risk_level = "LOW"

                    # Recalculate confidence
                    confidence = abs(adjusted_risk - 0.5) * 2

                    forecasts.append({
                        'day': day_offset + 1,
                        'date': date_str,
                        'risk_score': round(adjusted_risk, 3),
                        'risk_level': risk_level,
                        'confidence': round(confidence, 3)
                    })
                else:
                    forecasts.append({
                        'day': day_offset + 1,
                        'date': date_str,
                        'risk_score': 0.5,
                        'risk_level': 'MEDIUM',
                        'confidence': 0.0
                    })

            return forecasts

        except Exception as e:
            print(f"Forecast error: {e}")
            import traceback
            traceback.print_exc()
            return None


# Global instance
forecast_predictor = ForecastPredictor()