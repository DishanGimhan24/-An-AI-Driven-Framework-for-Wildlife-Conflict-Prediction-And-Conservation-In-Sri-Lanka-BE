import json
import os

import joblib

try:
    from tensorflow.keras.models import load_model
except ImportError:
    load_model = None
    print("⚠ TensorFlow not installed — LSTM model will not be available")

from config import RF_MODEL_PATH, SCALER_PATH, METRICS_PATH, MODELS_DIR


class ModelLoader:
    """Load and manage ML models"""

    def __init__(self):
        self.rf_model = None
        self.scaler = None
        self.metrics = None
        self.is_loaded = False

        # LSTM model components
        self.lstm_model = None
        self.lstm_scaler = None
        self.lstm_metrics = None
        self.lstm_loaded = False

    def load_models(self):
        """Load Random Forest model and scaler"""
        try:
            # Load Random Forest model
            if os.path.exists(RF_MODEL_PATH):
                self.rf_model = joblib.load(RF_MODEL_PATH)
                print(f"✓ Random Forest model loaded from {RF_MODEL_PATH}")
            else:
                print(f"⚠ Model not found at {RF_MODEL_PATH}")
                print("  Run ml_training/train_model.py first to train the model")
                return False

            # Load scaler
            if os.path.exists(SCALER_PATH):
                self.scaler = joblib.load(SCALER_PATH)
                print(f"✓ Scaler loaded from {SCALER_PATH}")
            else:
                print(f"⚠ Scaler not found, predictions may be inaccurate")

            # Load metrics
            if os.path.exists(METRICS_PATH):
                with open(METRICS_PATH, 'r') as f:
                    self.metrics = json.load(f)
                print(f"✓ Model metrics loaded")

            self.is_loaded = True

            # Try to load LSTM model as well
            self.load_lstm_model()

            # Connect LSTM predictor to this loader
            from ml.lstm_predictor import lstm_predictor
            lstm_predictor.set_model_loader(self)

            return True

        except Exception as e:
            print(f"✗ Error loading models: {e}")
            return False

    def load_lstm_model(self):
        """Load LSTM model and scaler"""
        if load_model is None:
            print("⚠ TensorFlow not available — skipping LSTM model")
            return False
        try:
            # Load LSTM model
            lstm_model_path = os.path.join(MODELS_DIR, 'lstm_model.keras')
            if os.path.exists(lstm_model_path):
                self.lstm_model = load_model(lstm_model_path)
                print(f"✓ LSTM model loaded from {lstm_model_path}")
            else:
                # Try .h5 format
                lstm_model_path_h5 = os.path.join(MODELS_DIR, 'lstm_model.h5')
                if os.path.exists(lstm_model_path_h5):
                    self.lstm_model = load_model(lstm_model_path_h5)
                    print(f"✓ LSTM model loaded from {lstm_model_path_h5}")
                else:
                    print(f"⚠ LSTM model not found")
                    return False

            # Load LSTM scaler
            lstm_scaler_path = os.path.join(MODELS_DIR, 'lstm_scaler.pkl')
            if os.path.exists(lstm_scaler_path):
                self.lstm_scaler = joblib.load(lstm_scaler_path)
                print(f"✓ LSTM scaler loaded")
            else:
                print(f"⚠ LSTM scaler not found")
                return False

            # Load LSTM metrics
            lstm_metrics_path = os.path.join(MODELS_DIR, 'lstm_metrics.json')
            if os.path.exists(lstm_metrics_path):
                with open(lstm_metrics_path, 'r') as f:
                    self.lstm_metrics = json.load(f)
                print(f"✓ LSTM metrics loaded")

            self.lstm_loaded = True
            return True

        except Exception as e:
            print(f"⚠ Error loading LSTM model: {e}")
            return False

    def get_model(self):
        """Get the loaded Random Forest model"""
        if not self.is_loaded:
            self.load_models()
        return self.rf_model

    def get_scaler(self):
        """Get the loaded scaler"""
        if not self.is_loaded:
            self.load_models()
        return self.scaler

    def get_metrics(self):
        """Get model performance metrics"""
        if not self.is_loaded:
            self.load_models()

        # Combine both model metrics
        all_metrics = {}

        if self.metrics:
            all_metrics['random_forest'] = self.metrics

        if self.lstm_metrics:
            all_metrics['lstm'] = self.lstm_metrics

        return all_metrics if all_metrics else self.metrics

    def get_lstm_model(self):
        """Get the loaded LSTM model"""
        if not self.lstm_loaded:
            self.load_lstm_model()
        return self.lstm_model

    def get_lstm_scaler(self):
        """Get the loaded LSTM scaler"""
        if not self.lstm_loaded:
            self.load_lstm_model()
        return self.lstm_scaler


# Global model loader instance
model_loader = ModelLoader()