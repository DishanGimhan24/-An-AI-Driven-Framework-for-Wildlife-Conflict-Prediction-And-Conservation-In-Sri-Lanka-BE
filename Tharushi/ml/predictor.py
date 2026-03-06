

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RISK_THRESHOLD_HIGH, RISK_THRESHOLD_MEDIUM
from data_processing.feature_extractor import feature_extractor
from ml.model_loader import model_loader

import warnings

class Predictor:
    """Make predictions using trained model"""

    def __init__(self):
        self.model_loader = model_loader
        self.feature_extractor = feature_extractor

    def predict(self, latitude, longitude, date):
        """
        Predict conflict risk for given location and date
        """
        try:
            # Check if model is loaded
            if not self.model_loader.is_loaded:
                print("Model not loaded, attempting to load...")
                self.model_loader.load_models()

                if not self.model_loader.is_loaded:
                    print("Failed to load model")
                    return None

            # Extract features
            features = self.feature_extractor.extract_features(latitude, longitude, date)

            if features is None:
                print("Feature extraction failed")
                return None

            # Get expected feature names from metrics
            if self.model_loader.metrics and 'feature_names' in self.model_loader.metrics:
                expected_features = self.model_loader.metrics['feature_names']

                # Use expected features instead of get_feature_names()
                feature_array = [features.get(name, 0) for name in expected_features]
            else:
                # Fallback to get_feature_names()
                feature_names = self.feature_extractor.get_feature_names()
                feature_array = [features.get(name, 0) for name in feature_names]

            # Scale features
            import numpy as np
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='X does not have valid feature names')
                feature_array_scaled = self.model_loader.scaler.transform(np.array([feature_array]))

            # Make prediction
            risk_proba = self.model_loader.rf_model.predict_proba(feature_array_scaled)[0]
            risk_score = risk_proba[1]  # Probability of conflict

            # Calculate confidence - how far from decision boundary (0.5)
            confidence = abs(risk_score - 0.5) * 2

            # Get risk level
            if risk_score >= RISK_THRESHOLD_HIGH:
                risk_level = "HIGH"
            elif risk_score >= RISK_THRESHOLD_MEDIUM:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            return {
                "risk_score": float(risk_score),
                "risk_level": risk_level,
                "confidence": float(confidence),
                "features": features
            }

        except Exception as e:
            print(f"Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return None


# Global predictor instance
predictor = Predictor()