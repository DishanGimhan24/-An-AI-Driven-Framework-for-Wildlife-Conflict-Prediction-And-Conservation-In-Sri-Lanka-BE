import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MODELS_DIR
from data_processing.data_loader import data_loader


class LSTMPredictor:
    """LSTM model predictor for 7-day conflict forecasting"""

    def __init__(self):
        self.model_loader = None

    def set_model_loader(self, model_loader):
        """Set the model loader instance"""
        self.model_loader = model_loader

    @property
    def is_loaded(self):
        """Check if LSTM model is loaded"""
        if self.model_loader is None:
            return False
        return self.model_loader.lstm_loaded

    @property
    def model(self):
        """Get LSTM model from model loader"""
        if self.model_loader is None:
            return None
        return self.model_loader.get_lstm_model()

    @property
    def scaler(self):
        """Get LSTM scaler from model loader"""
        if self.model_loader is None:
            return None
        return self.model_loader.get_lstm_scaler()

    def get_historical_features(self, latitude, longitude, end_date, days=30):
        """
        Get historical features for past 30 days using REAL data
        Creates sequence with 14 features matching training data
        """
        sequence_data = []

        for i in range(days):
            date = end_date - timedelta(days=(days - i - 1))

            # Get features for this date using REAL data
            features = self._extract_features_for_date(latitude, longitude, date)
            sequence_data.append(features)

        return sequence_data

    def _extract_features_for_date(self, latitude, longitude, date):
        """
        Extract 14 features for a specific date and location
        MUST match LSTM training data structure
        """
        # Get rainfall data
        rainfall = data_loader.get_rainfall_for_date(date)

        # Get NDVI
        ndvi = data_loader.get_ndvi_value(latitude, longitude, date.year, date.month)

        # Get previous month NDVI for trend
        prev_date = date - timedelta(days=30)
        ndvi_prev = data_loader.get_ndvi_value(latitude, longitude, prev_date.year, prev_date.month)

        # Calculate derived features
        is_dry = 1 if rainfall['rainfall_7day'] < 5 else 0
        low_veg = 1 if ndvi < 0.3 else 0

        # Return features in EXACT order as training CSV
        features = {
            'month': date.month,
            'day_of_year': date.timetuple().tm_yday,
            'week_of_year': date.isocalendar()[1],
            'season': 1 if 5 <= date.month <= 9 else 0,  # Dry/Wet
            'quarter': (date.month - 1) // 3 + 1,
            'rainfall_daily': rainfall.get('rainfall_7day', 0) / 7,  # Approximate
            'rainfall_7day': rainfall['rainfall_7day'],
            'rainfall_14day': rainfall['rainfall_14day'],
            'rainfall_30day': rainfall['rainfall_30day'],
            'ndvi': ndvi,
            'ndvi_change': ndvi - ndvi_prev,
            'is_dry_period': is_dry,
            'low_vegetation': low_veg,
            'high_risk_combo': is_dry * low_veg
        }

        return features

    def forecast_risk(self, latitude, longitude, start_date, forecast_days=7):
        """
        Forecast conflict risk for next N days

        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_date: Date to start forecast from (datetime or string)
            forecast_days: Number of days to forecast (default 7)

        Returns:
            Dictionary with forecast results
        """

        if not self.is_loaded:
            return {
                'error': 'LSTM model not loaded',
                'forecast': []
            }

        try:
            # Parse date
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')

            # Get 30 days of historical features using REAL data
            sequence_data = self.get_historical_features(latitude, longitude, start_date, days=30)

            # Convert to DataFrame
            sequence_df = pd.DataFrame(sequence_data)

            # Feature order MUST match training data (14 features)
            feature_order = [
                'month', 'day_of_year', 'week_of_year', 'season', 'quarter',
                'rainfall_daily', 'rainfall_7day', 'rainfall_14day', 'rainfall_30day',
                'ndvi', 'ndvi_change',
                'is_dry_period', 'low_vegetation', 'high_risk_combo'
            ]

            # Create input sequence
            X = sequence_df[feature_order].values
            X = X.reshape(1, 30, 14)  # (1 sample, 30 timesteps, 14 features)

            print(f"Input sequence shape: {X.shape}")  # Debug

            # Scale features
            X_reshaped = X.reshape(-1, 14)
            X_scaled = self.scaler.transform(X_reshaped)
            X_scaled = X_scaled.reshape(1, 30, 14)

            # Predict
            predictions = self.model.predict(X_scaled, verbose=0)

            # Format results
            forecast = []

            for day in range(min(forecast_days, predictions.shape[1])):
                forecast_date = start_date + timedelta(days=day + 1)
                risk_score = float(predictions[0][day])

                # Risk level
                if risk_score >= 0.7:
                    risk_level = 'HIGH'
                elif risk_score >= 0.4:
                    risk_level = 'MEDIUM'
                else:
                    risk_level = 'LOW'

                forecast.append({
                    'date': forecast_date.strftime('%Y-%m-%d'),
                    'day': day + 1,
                    'risk_score': round(risk_score, 3),
                    'risk_level': risk_level
                })

            return {
                'location': {
                    'latitude': latitude,
                    'longitude': longitude
                },
                'start_date': start_date.strftime('%Y-%m-%d'),
                'forecast': forecast,
                'forecast_days': len(forecast),
                'model': 'LSTM'
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'error': f'Forecast error: {str(e)}',
                'forecast': []
            }

    def get_metrics(self):
        """Get model performance metrics"""
        if self.model_loader is None:
            return None
        return self.model_loader.lstm_metrics


# Global LSTM predictor instance
lstm_predictor = LSTMPredictor()