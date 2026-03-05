import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Dataset paths
DATASET_DIR = os.path.join(BASE_DIR, 'Final Dataset')

# Dataset folder paths
ELEPHANT_DEATHS_DIR = os.path.join(DATASET_DIR, 'Elephant Deaths')
ELEPHANT_DISTRIBUTION_DIR = os.path.join(DATASET_DIR, 'elephant distribution')
ELEPHANT_TRACKING_DIR = os.path.join(DATASET_DIR, 'Elephant Tracking')
NDVI_DIR = os.path.join(DATASET_DIR, 'NDVI - Google Earth Engine')
POPULATION_DIR = os.path.join(DATASET_DIR, 'Population - WorldPop')
POWER_FENCE_DIR = os.path.join(DATASET_DIR, 'Power Fence')
PROTECTED_AREAS_DIR = os.path.join(DATASET_DIR, 'Protected Areas - Protected Planet')
RAINFALL_DIR = os.path.join(DATASET_DIR, 'Rainfall data - Nasa Power API')
ROAD_RAILWAY_DIR = os.path.join(DATASET_DIR, 'Road & Railway data')
WILDBOAR_DIR = os.path.join(DATASET_DIR, 'Wildboar')

# Training output paths
# Training output paths
TRAINING_OUTPUT_DIR = os.path.join(BASE_DIR, 'ml_training', 'outputs')
PREPROCESSING_OUTPUT_DIR = os.path.join(BASE_DIR, 'ml_training', 'preprocessing', 'outputs')
TRAINING_DATA_PATH = os.path.join(TRAINING_OUTPUT_DIR, 'training_data.csv')
PLOTS_DIR = os.path.join(TRAINING_OUTPUT_DIR, 'plots')

# Model paths
MODELS_DIR = os.path.join(BASE_DIR, 'models')
RF_MODEL_PATH = os.path.join(MODELS_DIR, 'random_forest_model.pkl')
LSTM_MODEL_PATH = os.path.join(MODELS_DIR, 'lstm_model.h5')
SCALER_PATH = os.path.join(MODELS_DIR, 'scaler.pkl')
LSTM_SCALER_PATH = os.path.join(MODELS_DIR, 'lstm_scaler.pkl')
METRICS_PATH = os.path.join(MODELS_DIR, 'model_metrics.json')

# Flask config
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5001
DEBUG = True

# ML config
RANDOM_STATE = 42
TEST_SIZE = 0.15
VALIDATION_SIZE = 0.15

# Risk thresholds
RISK_THRESHOLD_HIGH = 0.7
RISK_THRESHOLD_MEDIUM = 0.4

# GADM city/division level data
GADM_GEOJSON_PATH = os.path.join(DATASET_DIR, 'GeoJSON', 'gadm41_LKA_2.json')
CITY_CACHE_PATH = os.path.join(BASE_DIR, 'cache', 'city_data.json')