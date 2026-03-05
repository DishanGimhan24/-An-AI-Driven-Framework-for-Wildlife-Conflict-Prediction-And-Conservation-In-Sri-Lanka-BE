import uvicorn
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import xgboost as xgb
from sklearn.cluster import DBSCAN
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import json
import warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------------


class Config:
    """Configuration parameters"""
    # Paths
    RAW_DATA_PATH = './uploads/final7.csv'
    CLEANED_DATA_PATH = './outputs/elephant_data_cleaned.csv'
    BALANCED_DATA_PATH = './outputs/elephant_data_balanced.csv'
    MODEL_PATH = './outputs/conflict_model.pkl'
    SCALER_PATH = './outputs/scaler.pkl'
    ENCODER_PATH = './outputs/label_encoders.pkl'
    CORRIDOR_MODEL_PATH = './outputs/corridor_model.pkl'

    # Model parameters
    TEST_SIZE = 0.2
    RANDOM_STATE = 42
    TARGET_CONFLICT_RATIO = 0.15

    # Risk thresholds (meters)
    CRITICAL_DISTANCE = 100
    HIGH_RISK_DISTANCE = 500
    MEDIUM_RISK_DISTANCE = 2000

    # API settings
    API_HOST = "0.0.0.0"
    API_PORT = 8000


# ---------------------------------------------------------------------------------
# DATA CLEANING MODULE
# ---------------------------------------------------------------------------------

class DataCleaner:
    """Handles all data cleaning operations"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.df = None

    def load_data(self):
        """Load raw CSV data"""
        print("Loading data...")
        self.df = pd.read_csv(self.filepath, low_memory=False)
        print(f"Loaded {len(self.df):,} records")
        return self

    def remove_duplicates(self):
        """Remove duplicate records"""
        print("Removing duplicates...")
        initial = len(self.df)
        self.df['Datetime_temp'] = pd.to_datetime(
            self.df['Datetime'], errors='coerce')
        self.df = self.df.sort_values('Datetime_temp')
        self.df = self.df.drop_duplicates()
        self.df = self.df.drop_duplicates(
            subset=['EleID', 'latitude', 'longitude', 'Date', 'Time'],
            keep='first'
        )
        removed = initial - len(self.df)
        print(f"Removed {removed:,} duplicates ({removed/initial*100:.1f}%)")
        return self

    def clean_columns(self):
        """Clean and standardize columns"""
        print("Cleaning columns...")

        # Drop empty columns
        empty_cols = [
            col for col in self.df.columns if self.df[col].isnull().all()]
        if empty_cols:
            self.df = self.df.drop(columns=empty_cols)

        # Fix time column
        self.df['Time'] = self.df['Time'].replace('Homey', np.nan)
        self.df['Time'] = self.df.groupby(
            'EleID')['Time'].fillna(method='ffill')

        # Standardize datetime
        self.df['Date_parsed'] = pd.to_datetime(
            self.df['Date'], dayfirst=True, errors='coerce')
        self.df['Datetime_standard'] = pd.to_datetime(
            self.df['Date_parsed'].astype(
                str) + ' ' + self.df['Time'].astype(str),
            errors='coerce'
        )

        print("Columns cleaned")
        return self

    def engineer_features(self):
        """Create engineered features"""
        print("Engineering features...")

        # Temporal features
        self.df['Year'] = self.df['Date_parsed'].dt.year
        self.df['Month'] = self.df['Date_parsed'].dt.month
        self.df['Day'] = self.df['Date_parsed'].dt.day
        self.df['DayOfWeek'] = self.df['Date_parsed'].dt.dayofweek

        # Season
        season_map = {
            12: 'Dry', 1: 'Dry', 2: 'Dry',
            3: 'Inter-Monsoon', 4: 'Inter-Monsoon', 5: 'Inter-Monsoon',
            6: 'Southwest-Monsoon', 7: 'Southwest-Monsoon', 8: 'Southwest-Monsoon',
            9: 'Inter-Monsoon-2', 10: 'Inter-Monsoon-2', 11: 'Inter-Monsoon-2'
        }
        self.df['Season'] = self.df['Month'].map(season_map)

        # Time of day
        self.df['Hour'] = pd.to_datetime(
            self.df['Time'], format='%H:%M', errors='coerce').dt.hour
        self.df['TimeOfDay'] = self.df['Hour'].apply(
            self._categorize_time_of_day)

        # Movement features
        self.df = self.df.sort_values(['EleID', 'Datetime_standard'])
        self.df['TimeDelta_hours'] = self.df.groupby(
            'EleID')['Datetime_standard'].diff().dt.total_seconds() / 3600

        # Risk features
        self.df['HumanProximityRisk'] = pd.cut(
            self.df['HumanDistance'],
            bins=[0, Config.CRITICAL_DISTANCE, Config.HIGH_RISK_DISTANCE,
                  Config.MEDIUM_RISK_DISTANCE, float('inf')],
            labels=['Critical', 'High', 'Medium', 'Low']
        )

        self.df['ConflictRiskScore'] = (
            (1 / (self.df['HumanDistance'] + 1)) * 10000 +
            (self.df['TimeOfDay'].isin(['Night', 'Evening'])).astype(int) * 3
        )

        self.df['ConflictRiskScore_normalized'] = (
            (self.df['ConflictRiskScore'] - self.df['ConflictRiskScore'].min()) /
            (self.df['ConflictRiskScore'].max() -
             self.df['ConflictRiskScore'].min()) * 100
        )

        # Synthetic conflict labels
        conflict_conditions = (
            (self.df['HumanDistance'] < Config.HIGH_RISK_DISTANCE) &
            (self.df['TimeOfDay'].isin(['Night', 'Evening']))
        )
        self.df['ConflictOccurred'] = conflict_conditions.astype(int)

        # Mark as original data
        self.df['is_synthetic'] = 0

        print(
            f"Created {len([c for c in self.df.columns if c not in pd.read_csv(self.filepath, nrows=1).columns])} new features")
        return self

    def _categorize_time_of_day(self, hour):
        """Categorize hour into time of day"""
        if pd.isna(hour):
            return 'Unknown'
        if 0 <= hour < 6:
            return 'Night'
        elif 6 <= hour < 10:
            return 'Early Morning'
        elif 10 <= hour < 14:
            return 'Midday'
        elif 14 <= hour < 18:
            return 'Afternoon'
        elif 18 <= hour < 22:
            return 'Evening'
        else:
            return 'Night'

    def _calculate_distance_moved(self):
        """Calculate haversine distance between consecutive points"""
        distances = []
        for idx in range(len(self.df)):
            if idx == 0 or self.df.iloc[idx]['EleID'] != self.df.iloc[idx-1]['EleID']:
                distances.append(0)
            else:
                dist = self._haversine(
                    self.df.iloc[idx -
                                 1]['latitude'], self.df.iloc[idx-1]['longitude'],
                    self.df.iloc[idx]['latitude'], self.df.iloc[idx]['longitude']
                )
                distances.append(dist)
        return distances

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Calculate haversine distance in meters"""
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def save(self, output_path):
        """Save cleaned data"""
        self.df.to_csv(output_path, index=False)
        print(f"Saved to: {output_path}")
        return self.df

    def run_pipeline(self):
        """Execute complete cleaning pipeline"""
        return (self
                .load_data()
                .remove_duplicates()
                .clean_columns()
                .engineer_features())


# ---------------------------------------------------------------------------------
# DATA SYNTHESIS MODULE
# ---------------------------------------------------------------------------------

class DataSynthesizer:
    """Synthesize additional training data"""

    def __init__(self, df):
        self.df = df.copy()
        self.synthetic_records = []

    def synthesize_high_risk_scenarios(self, n_samples=2000):
        """Generate high-risk conflict scenarios"""
        print(f"Synthesizing {n_samples} high-risk scenarios...")

        # Get template records
        high_risk = self.df[self.df['ConflictRiskScore_normalized'] > 50]
        if len(high_risk) == 0:
            high_risk = self.df.sample(min(100, len(self.df)))

        for i in range(n_samples):
            base = high_risk.sample(1).iloc[0].to_dict()

            # Modify for high risk
            base['latitude'] += np.random.uniform(-0.01, 0.01)
            base['longitude'] += np.random.uniform(-0.01, 0.01)
            base['HumanDistance'] = np.random.uniform(
                20, Config.HIGH_RISK_DISTANCE)
            base['TimeOfDay'] = np.random.choice(['Night', 'Evening'])
            base['ConflictOccurred'] = 1
            base['is_synthetic'] = 1

            # Recalculate risk
            base['ConflictRiskScore'] = (
                (1 / (base['HumanDistance'] + 1)) * 10000 + 10 + 5 + 3
            )
            base['ConflictRiskScore_normalized'] = min(
                (base['ConflictRiskScore'] / 100), 100)

            self.synthetic_records.append(base)

        print(f"Generated {len(self.synthetic_records)} synthetic records")
        return self

    def create_balanced_dataset(self):
        """Combine original and synthetic data"""
        print("Creating balanced dataset...")

        if len(self.synthetic_records) > 0:
            synthetic_df = pd.DataFrame(self.synthetic_records)
            balanced_df = pd.concat([self.df, synthetic_df], ignore_index=True)
        else:
            balanced_df = self.df.copy()

        conflict_ratio = balanced_df['ConflictOccurred'].mean()
        print(f"Balanced dataset created: {len(balanced_df):,} records")
        print(f"   Conflict ratio: {conflict_ratio*100:.2f}%")

        return balanced_df


# ---------------------------------------------------------------------------------
# MODEL TRAINING MODULE
# ---------------------------------------------------------------------------------

class ConflictPredictor:
    """Train and manage conflict prediction models"""

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = None
        self.metrics = {}

    def prepare_data(self, df):
        """Prepare data for training"""
        print("Preparing data for training...")

        # Select features
        numerical_features = [
            'latitude',
            'longitude',
            'Elevation',
            'HumanDistance',
            'RoadDistance',
            'Year',
            'Month',
            'DayOfWeek',
            'Hour'
        ]

        categorical_features = ['Season', 'TimeOfDay']

        # Handle missing values
        df_model = df.copy()
        for col in numerical_features:
            if col in df_model.columns:
                df_model[col] = df_model[col].fillna(df_model[col].median())

        # Encode categorical features
        for col in categorical_features:
            if col in df_model.columns:
                le = LabelEncoder()
                df_model[col +
                         '_encoded'] = le.fit_transform(df_model[col].astype(str))
                self.label_encoders[col] = le

        # Final feature list
        self.feature_columns = numerical_features + \
            [f"{col}_encoded" for col in categorical_features]
        self.feature_columns = [
            col for col in self.feature_columns if col in df_model.columns]

        X = df_model[self.feature_columns]
        y = df_model['ConflictOccurred']

        print(f"Features prepared: {len(self.feature_columns)} features")
        return X, y

    def train(self, X, y):
        """Train the conflict prediction model"""
        print("Training model...")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=Config.TEST_SIZE,
            stratify=y, random_state=Config.RANDOM_STATE
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train XGBoost model
        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=Config.RANDOM_STATE,
            eval_metric='logloss'
        )

        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]

        # Calculate metrics
        self.metrics = {
            'accuracy': (y_pred == y_test).mean(),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }

        print(f"Model trained successfully")
        print(f"   Accuracy: {self.metrics['accuracy']:.3f}")
        print(f"   ROC-AUC: {self.metrics['roc_auc']:.3f}")

        return self

    def save_model(self):
        """Save trained model and preprocessors"""
        print("Saving model...")
        joblib.dump(self.model, Config.MODEL_PATH)
        joblib.dump(self.scaler, Config.SCALER_PATH)
        joblib.dump(self.label_encoders, Config.ENCODER_PATH)
        joblib.dump(self.feature_columns,
                    Config.MODEL_PATH.replace('.pkl', '_features.pkl'))
        print("Model saved")

    def load_model(self):
        """Load trained model and preprocessors"""
        print("Loading model...")
        self.model = joblib.load(Config.MODEL_PATH)
        self.scaler = joblib.load(Config.SCALER_PATH)
        self.label_encoders = joblib.load(Config.ENCODER_PATH)
        self.feature_columns = joblib.load(
            Config.MODEL_PATH.replace('.pkl', '_features.pkl'))
        print("Model loaded")
        return self

    def predict(self, input_data):
        """Make predictions on new data"""
        # Prepare input
        df_input = pd.DataFrame([input_data])

        # Encode categorical features
        for col, encoder in self.label_encoders.items():
            if col in df_input.columns:
                try:
                    df_input[col +
                             '_encoded'] = encoder.transform(df_input[col].astype(str))
                except:
                    df_input[col + '_encoded'] = 0  # Unknown category

        # Select features
        X_input = df_input[self.feature_columns].fillna(0)

        # Scale
        X_scaled = self.scaler.transform(X_input)

        # Predict
        prediction = self.model.predict(X_scaled)[0]
        probability = self.model.predict_proba(X_scaled)[0][1]

        return {
            'conflict_predicted': bool(prediction),
            'conflict_probability': float(probability),
            'risk_level': self._get_risk_level(
                probability,
                input_data['HumanDistance'],
                input_data['TimeOfDay']
            )
        }

    def _get_risk_level(self, probability, human_distance, time_of_day):
        if human_distance < 200 and time_of_day in ['Night', 'Evening']:
            return 'Critical'
        if human_distance < 500:
            return 'High'
        if probability >= 0.6:
            return 'High'
        if probability >= 0.35:
            return 'Medium'
        return 'Low'

# ---------------------------------------------------------------------------------
# CORRIDOR DETECTION MODULE
# ---------------------------------------------------------------------------------


class CorridorDetector:
    """Detect elephant corridors using clustering"""

    def __init__(self):
        self.model = None
        self.corridors = None

    def detect_corridors(self, df, eps=0.01, min_samples=10):
        """Detect corridors using DBSCAN clustering"""
        print("Detecting elephant corridors...")

        # Use GPS coordinates
        coords = df[['latitude', 'longitude']].values

        # Cluster
        self.model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = self.model.fit_predict(coords)

        # Analyze corridors
        self.corridors = []
        for label in set(labels):
            if label == -1:  # Skip noise
                continue

            corridor_points = df[labels == label]
            corridor_info = {
                'corridor_id': int(label),
                'num_points': len(corridor_points),
                'center_lat': float(corridor_points['latitude'].mean()),
                'center_lon': float(corridor_points['longitude'].mean()),
                'bounds': {
                    'lat_min': float(corridor_points['latitude'].min()),
                    'lat_max': float(corridor_points['latitude'].max()),
                    'lon_min': float(corridor_points['longitude'].min()),
                    'lon_max': float(corridor_points['longitude'].max())
                },
                'avg_human_distance': float(corridor_points['HumanDistance'].mean()),
                'conflict_rate': float(corridor_points['ConflictOccurred'].mean()),
                'safety_score': self._calculate_safety_score(corridor_points)
            }
            self.corridors.append(corridor_info)

        print(f"Detected {len(self.corridors)} corridors")
        return self.corridors

    def _calculate_safety_score(self, corridor_points):
        """Calculate safety score for corridor (0-100)"""
        # Higher score = safer
        avg_human_dist = corridor_points['HumanDistance'].mean()
        conflict_rate = corridor_points['ConflictOccurred'].mean()

        safety = (
            (min(avg_human_dist / 5000, 1) * 40) +  # Distance weight
            ((1 - conflict_rate) * 30)
        )
        return float(min(safety, 100))

    def save_corridors(self):
        """Save corridor information"""
        joblib.dump(self.corridors, Config.CORRIDOR_MODEL_PATH)
        print("Corridors saved")

    def load_corridors(self):
        """Load corridor information"""
        self.corridors = joblib.load(Config.CORRIDOR_MODEL_PATH)
        print("Corridors loaded")
        return self.corridors


# ---------------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------------

def run_complete_pipeline():
    """Execute complete ML pipeline"""
    print("\n" + "-"*70)
    print("WILDLIFE CONFLICT PREDICTION - COMPLETE PIPELINE")
    print("-"*70 + "\n")

    # Step 1: Clean Data
    print("STEP 1: DATA CLEANING")
    print("-" * 70)
    cleaner = DataCleaner(Config.RAW_DATA_PATH)
    df_cleaned = cleaner.run_pipeline().save(Config.CLEANED_DATA_PATH)

    # Step 2: Synthesize Data
    print("\n" + "STEP 2: DATA SYNTHESIS")
    print("-" * 70)
    synthesizer = DataSynthesizer(df_cleaned)
    df_balanced = (synthesizer
                   .synthesize_high_risk_scenarios(n_samples=2000)
                   .create_balanced_dataset())
    df_balanced.to_csv(Config.BALANCED_DATA_PATH, index=False)

    # Step 3: Train Conflict Prediction Model
    print("\n" + "STEP 3: MODEL TRAINING")
    print("-" * 70)
    predictor = ConflictPredictor()
    X, y = predictor.prepare_data(df_balanced)
    predictor.train(X, y)
    predictor.save_model()

    # Step 4: Detect Corridors
    print("\n" + "STEP 4: CORRIDOR DETECTION")
    print("-" * 70)
    corridor_detector = CorridorDetector()
    corridors = corridor_detector.detect_corridors(df_balanced)
    corridor_detector.save_corridors()

    print("\n" + "-"*70)
    print("PIPELINE COMPLETE!")
    print("-"*70)
    print(f"\nModel Metrics:")
    print(f"   Accuracy: {predictor.metrics['accuracy']:.3f}")
    print(f"   ROC-AUC: {predictor.metrics['roc_auc']:.3f}")
    print(f"\n  Corridors Detected: {len(corridors)}")
    print("\nAPI is ready to launch with: python wildlife_conflict_api.py")
    print("-"*70 + "\n")


# ---------------------------------------------------------------------------------
# API MODELS (Pydantic)
# ---------------------------------------------------------------------------------

class PredictionInput(BaseModel):
    """Input schema for prediction"""
    latitude: float
    longitude: float
    datetime: str
    human_distance: float
    road_distance: float
    elevation: float


class PredictionOutput(BaseModel):
    """Output schema for prediction"""
    conflict_predicted: bool
    conflict_probability: float
    risk_level: str
    nearest_corridor: Optional[dict] = None


class CorridorInfo(BaseModel):
    """Corridor information schema"""
    corridor_id: int
    num_points: int
    center_lat: float
    center_lon: float
    bounds: dict
    avg_human_distance: float
    conflict_rate: float
    safety_score: float


def auto_calculate_features(lat: float, lon: float, dt: datetime = None,
                            human_distance: float = None, road_distance: float = None,
                            elevation: float = None):
    """
    Auto-calculate features from lat/lon/datetime
    """
    if dt is None:
        dt = datetime.now()

    # Temporal features
    year = dt.year
    month = dt.month
    day = dt.day
    day_of_week = dt.weekday()
    hour = dt.hour

    # Calculate season (Sri Lankan seasons)
    season_map = {
        12: 'Dry', 1: 'Dry', 2: 'Dry',
        3: 'Inter-Monsoon', 4: 'Inter-Monsoon', 5: 'Inter-Monsoon',
        6: 'Southwest-Monsoon', 7: 'Southwest-Monsoon', 8: 'Southwest-Monsoon',
        9: 'Inter-Monsoon-2', 10: 'Inter-Monsoon-2', 11: 'Inter-Monsoon-2'
    }
    season = season_map.get(month, 'Southwest-Monsoon')

    # Calculate time of day
    if hour < 6:
        time_of_day = 'Night'
    elif hour < 10:
        time_of_day = 'Early Morning'
    elif hour < 14:
        time_of_day = 'Midday'
    elif hour < 18:
        time_of_day = 'Afternoon'
    elif hour < 22:
        time_of_day = 'Evening'
    else:
        time_of_day = 'Night'

    defaults = {
        'Elevation': elevation,
        'RoadDistance': road_distance,
        'HumanDistance': human_distance,
    }

    # Calculate risk score
    human_risk = (1 / (defaults['HumanDistance'] + 1)) * 8000
    road_risk = (1 / (defaults['RoadDistance'] + 50)) * 3000
    elevation_risk = 5 if defaults['Elevation'] < 200 else 0
    night_risk = 4 if time_of_day in ['Night', 'Evening'] else 0

    conflict_risk_score = (
        human_risk +
        road_risk +
        elevation_risk +
        night_risk
    )

    conflict_risk_normalized = min(conflict_risk_score / 150, 100)

    return {
        'latitude': lat,
        'longitude': lon,
        'Year': year,
        'Month': month,
        'Day': day,
        'DayOfWeek': day_of_week,
        'Hour': hour,
        'Season': season,
        'TimeOfDay': time_of_day,
        'ConflictRiskScore_normalized': conflict_risk_normalized,
        **defaults
    }
# ---------------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------------


# Initialize FastAPI app
app = FastAPI(
    title="Wildlife Conflict Prediction API",
    description="AI-powered API for predicting human-elephant conflicts in Sri Lanka",
    version="1.0.0"
)

# Global model instances
predictor = ConflictPredictor()
corridor_detector = CorridorDetector()


@app.on_event("startup")
async def load_models():
    """Load models on startup"""
    try:
        predictor.load_model()
        corridor_detector.load_corridors()
        print("Models loaded successfully")
    except Exception as e:
        print(f"  Warning: Could not load models - {e}")
        print("   Run the pipeline first: python wildlife_conflict_pipeline.py")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Wildlife Conflict Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "predict": "/predict",
            "corridors": "/corridors",
            "corridor_detail": "/corridors/{corridor_id}",
            "health": "/health",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": predictor.model is not None,
        "corridors_loaded": corridor_detector.corridors is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/predict", response_model=PredictionOutput)
async def predict_conflict(input_data: PredictionInput):
    """
    Simplified prediction endpoint - only requires GPS coordinates

    Input:
    - latitude: GPS latitude
    - longitude: GPS longitude  
    - datetime: Optional ISO datetime string (defaults to current time)

    All other features are auto-calculated using reasonable defaults.

    Returns same output as /predict endpoint.
    """
    if predictor.model is None:
        raise HTTPException(
            status_code=503, detail="Model not loaded. Run pipeline first.")

    try:
        # Parse datetime if provided
        if input_data.datetime:
            try:
                dt = datetime.fromisoformat(
                    input_data.datetime.replace('Z', '+00:00'))
            except:
                dt = datetime.now()
        else:
            dt = datetime.now()

        # Auto-calculate all features
        full_input = auto_calculate_features(
            input_data.latitude,
            input_data.longitude,
            dt,
            input_data.human_distance,
            input_data.road_distance,
            input_data.elevation
        )

        # Make prediction
        result = predictor.predict(full_input)

        # Find nearest corridor
        nearest_corridor = None
        if corridor_detector.corridors:
            min_dist = float('inf')
            for corridor in corridor_detector.corridors:
                dist = ((corridor['center_lat'] - input_data.latitude)**2 +
                        (corridor['center_lon'] - input_data.longitude)**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest_corridor = corridor

        return PredictionOutput(
            conflict_predicted=result['conflict_predicted'],
            conflict_probability=result['conflict_probability'],
            risk_level=result['risk_level'],
            nearest_corridor=nearest_corridor
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/corridors", response_model=List[CorridorInfo])
async def get_all_corridors():
    """Get information about all detected corridors"""
    if not corridor_detector.corridors:
        raise HTTPException(status_code=404, detail="Corridors not loaded")

    return corridor_detector.corridors


@app.get("/corridors/{corridor_id}", response_model=CorridorInfo)
async def get_corridor_detail(corridor_id: int):
    """Get detailed information about a specific corridor"""
    if not corridor_detector.corridors:
        raise HTTPException(status_code=404, detail="Corridors not loaded")

    for corridor in corridor_detector.corridors:
        if corridor['corridor_id'] == corridor_id:
            return corridor

    raise HTTPException(
        status_code=404, detail=f"Corridor {corridor_id} not found")


# ---------------------------------------------------------------------------------
# COMMAND LINE INTERFACE
# ---------------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "train":
            # Run complete pipeline
            run_complete_pipeline()

        elif command == "api":
            # Start API server
            print("\Starting API server...")
            print(f"   URL: http://{Config.API_HOST}:{Config.API_PORT}")
            print(f"   Docs: http://{Config.API_HOST}:{Config.API_PORT}/docs")
            print("\nPress Ctrl+C to stop\n")

            uvicorn.run(
                "wildlife_conflict_pipeline:app",
                host=Config.API_HOST,
                port=Config.API_PORT,
                reload=False
            )

        elif command == "test":
            # Test prediction
            predictor.load_model()

            test_input = {
                'latitude': 7.5,
                'longitude': 81.0,
                'Elevation': 100,
                'RoadDistance': 1000,
                'HumanDistance': 300,
                'ConflictRiskScore_normalized': 60,
                'Year': 2024,
                'Month': 6,
                'Day': 15,
                'DayOfWeek': 3,
                'Hour': 20,
                'Season': 'Southwest-Monsoon',
                'TimeOfDay': 'Evening'
            }

            result = predictor.predict(test_input)
            print("\n Test Prediction:")
            print(json.dumps(result, indent=2))

        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  train - Run complete training pipeline")
            print("  api   - Start API server")
            print("  test  - Run test prediction")
    else:
        print("\nWildlife Conflict Prediction System")
        print("\nUsage:")
        print("  python wildlife_conflict_pipeline.py train  # Train models")
        print("  python wildlife_conflict_pipeline.py api    # Start API")
        print("  python wildlife_conflict_pipeline.py test   # Test prediction")
