from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import numpy as np
import pandas as pd
import os
from pathlib import Path

# =========================
# 1. CREATE APP
# =========================
app = FastAPI(title="Animal-Vehicle Collision Risk Prediction API")

# =========================
# 2. CORS (Frontend connect වෙන්න)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # dev stage එකට ok
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 3. LOAD COLLISION DATA FOR DISTANCE CALCULATIONS
# =========================
collision_data = None
try:
    collision_data_path = Path(__file__).parent / "collision_model_system" / "dataset" / "collision_data.csv"
    if collision_data_path.exists():
        collision_data = pd.read_csv(str(collision_data_path))
        print(f"✓ Loaded collision data from {collision_data_path}")
    else:
        print(f"⚠ Collision data not found at {collision_data_path}")
except Exception as e:
    print(f"⚠ Error loading collision data: {e}")

# =========================
# 4. LOAD TRAINED MODELS
# =========================
# Try to load collision model first (new system)
collision_model = None
risk_model = None

# Path to collision model from collision_model_system
collision_model_path = Path(__file__).parent / "collision_model_system" / "model" / "random_forest_collision_model.pkl"
if collision_model_path.exists():
    collision_model = joblib.load(str(collision_model_path))
    print(f"✓ Loaded collision model from {collision_model_path}")
else:
    print(f"⚠ Collision model not found at {collision_model_path}")

# Path to legacy risk model
legacy_model_path = Path(__file__).parent / "model" / "risk_model.pkl"
if legacy_model_path.exists():
    risk_model = joblib.load(str(legacy_model_path))
    print(f"✓ Loaded legacy risk model from {legacy_model_path}")
else:
    print(f"⚠ Legacy risk model not found at {legacy_model_path}")

# =========================
# 5. REQUEST MODELS
# =========================
class LocationRequest(BaseModel):
    latitude: float
    longitude: float

class CollisionPredictionRequest(BaseModel):
    latitude: float
    longitude: float
    distance_to_forest: float
    distance_to_water: float
    distance_to_railway: float

class LegacyPredictionRequest(BaseModel):
    rain: float
    NDVI: float
    water_distance: float
    distance_to_forest: float
    animal_type: int
    vehicle_type: int

# =========================
# 6. HELPER FUNCTIONS
# =========================
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two lat/lon points using Haversine formula."""
    R = 6371000  # Earth radius in meters
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)
    
    a = np.sin(delta_lat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

def is_within_sri_lanka(latitude, longitude):
    """
    Check if a location is within Sri Lanka's geographic bounds.
    Sri Lanka bounds (comprehensive): 
    - North: 9.8° N (Mullaitivu)
    - South: 5.8° N (Dondra)
    - East: 81.9° E (Silavathura)
    - West: 79.6° E (Pesalai)
    """
    SRI_LANKA_BOUNDS = {
        "north": 9.9,
        "south": 5.8,
        "east": 81.95,
        "west": 79.5
    }
    
    return (
        SRI_LANKA_BOUNDS["south"] <= latitude <= SRI_LANKA_BOUNDS["north"] and
        SRI_LANKA_BOUNDS["west"] <= longitude <= SRI_LANKA_BOUNDS["east"]
    )

def calculate_distances(latitude, longitude):
    """
    Calculate distances from a given location to forest, water, and railway.
    Uses the collision data to estimate nearest distances.
    """
    
    if collision_data is None or len(collision_data) == 0:
        print(f"⚠ No collision data available, returning defaults")
        # Return default values if no data available
        return {
            "distance_to_forest": 1500,
            "distance_to_water": 800,
            "distance_to_railway": 2000
        }
    
    try:
        # Check if required columns exist
        required_cols = ['latitude', 'longitude', 'distance_to_forest', 'distance_to_water', 'distance_to_railway']
        missing_cols = [col for col in required_cols if col not in collision_data.columns]
        
        if missing_cols:
            print(f"⚠ Missing columns in collision data: {missing_cols}")
            print(f"Available columns: {collision_data.columns.tolist()}")
            return {
                "distance_to_forest": 1500,
                "distance_to_water": 800,
                "distance_to_railway": 2000
            }
        
        # Extract coordinate arrays from collision data
        lats = collision_data['latitude'].values
        lons = collision_data['longitude'].values
        forest_dists = collision_data['distance_to_forest'].values
        water_dists = collision_data['distance_to_water'].values
        railway_dists = collision_data['distance_to_railway'].values
        
        # Calculate distances to all data points
        distances = []
        for lat, lon in zip(lats, lons):
            dist = haversine_distance(latitude, longitude, lat, lon)
            distances.append(dist)
        
        distances = np.array(distances)
        
        # Find the closest data point(s) - use 5 nearest neighbors and average
        k = min(5, len(distances))
        nearest_indices = np.argsort(distances)[:k]
        
        # Calculate average distances for the nearest neighbors
        avg_forest = float(np.mean(forest_dists[nearest_indices]))
        avg_water = float(np.mean(water_dists[nearest_indices]))
        avg_railway = float(np.mean(railway_dists[nearest_indices]))
        
        print(f"✓ Calculated distances for ({latitude}, {longitude}): forest={avg_forest}, water={avg_water}, railway={avg_railway}")
        
        return {
            "distance_to_forest": round(avg_forest, 2),
            "distance_to_water": round(avg_water, 2),
            "distance_to_railway": round(avg_railway, 2)
        }
    
    except Exception as e:
        print(f"⚠ Error calculating distances: {e}")
        # Return default values on error
        return {
            "distance_to_forest": 1500,
            "distance_to_water": 800,
            "distance_to_railway": 2000
        }

# =========================
# 7. DISTANCE CALCULATION ENDPOINT
# =========================
@app.post("/calculate-distances")
def calculate_distances_endpoint(request: LocationRequest):
    """
    Calculate distances from a given location to forest, water, and railway.
    
    Expected input:
    {
      latitude: number,
      longitude: number
    }
    
    Returns:
    {
      distance_to_forest: float (meters),
      distance_to_water: float (meters),
      distance_to_railway: float (meters),
      latitude: float,
      longitude: float,
      within_sri_lanka: bool
    }
    """
    
    print(f"\n📍 Received location request: lat={request.latitude}, lng={request.longitude}")
    
    # Check if location is within Sri Lanka
    within_bounds = is_within_sri_lanka(request.latitude, request.longitude)
    print(f"   Within Sri Lanka bounds: {within_bounds}")
    
    if not within_bounds:
        print(f"   ❌ Location outside Sri Lanka, rejecting request")
        return {
            "error": "Risk prediction is only available for locations within Sri Lanka.",
            "within_sri_lanka": False,
            "latitude": request.latitude,
            "longitude": request.longitude
        }
    
    distances = calculate_distances(request.latitude, request.longitude)
    print(f"   ✓ Distances calculated: {distances}")
    
    response = {
        **distances,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "within_sri_lanka": True
    }
    
    print(f"   Returning: {response}\n")
    return response

# =========================
# 8. VALIDATE LOCATION ENDPOINT
# =========================
@app.post("/validate-location")
def validate_location(request: LocationRequest):
    """
    Validate if a location is within Sri Lanka.
    
    Expected input:
    {
      latitude: number,
      longitude: number
    }
    
    Returns:
    {
      within_sri_lanka: bool,
      message: string
    }
    """
    within_bounds = is_within_sri_lanka(request.latitude, request.longitude)
    
    if within_bounds:
        return {
            "within_sri_lanka": True,
            "message": "Location is within Sri Lanka"
        }
    else:
        return {
            "within_sri_lanka": False,
            "message": "Risk prediction is only available for locations within Sri Lanka."
        }

# =========================
# 8. COLLISION PREDICTION ENDPOINT (NEW)
# =========================
@app.post("/predict-collision")
def predict_collision(request: CollisionPredictionRequest):
    """
    Predict collision risk based on distance features.
    
    Expected input:
    {
      latitude: number,
      longitude: number,
      distance_to_forest: number (meters),
      distance_to_water: number (meters),
      distance_to_railway: number (meters)
    }
    
    Returns:
    {
      risk_score: float (0-100),
      risk_level: string ("Low" | "Medium" | "High"),
      latitude: float,
      longitude: float
    }
    """
    
    # Check if location is within Sri Lanka
    if not is_within_sri_lanka(request.latitude, request.longitude):
        return {
            "error": "Risk prediction is only available for locations within Sri Lanka.",
            "risk_score": None,
            "risk_level": None
        }
    
    if collision_model is None:
        return {
            "error": "Collision model not loaded",
            "risk_score": None,
            "risk_level": None
        }
    
    try:
        # Prepare feature array in same order as training
        # Features: ['distance_to_forest', 'distance_to_railway', 'distance_to_water']
        features = np.array([[
            request.distance_to_forest,
            request.distance_to_railway,
            request.distance_to_water
        ]])
        
        # Get probability for collision class (class 1)
        probability = collision_model.predict_proba(features)[0][1]
        risk_score = probability * 100
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "High"
        elif risk_score >= 40:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        return {
            "risk_score": round(float(risk_score), 2),
            "risk_level": risk_level,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "distance_to_forest": request.distance_to_forest,
            "distance_to_water": request.distance_to_water,
            "distance_to_railway": request.distance_to_railway
        }
    
    except Exception as e:
        return {
            "error": f"Prediction failed: {str(e)}",
            "risk_score": None,
            "risk_level": None
        }

# =========================
# 8. LEGACY PREDICTION ENDPOINT (OLD)
# =========================
@app.post("/predict")
def predict(data: dict):
    """
    Expected input from frontend:
    {
      rain: number,
      NDVI: number,
      water_distance: number,
      distance_to_forest: number,
      animal_type: number,
      vehicle_type: number
    }
    """
    
    if risk_model is None:
        return {
            "error": "Risk model not loaded",
            "risk_score": None,
            "risk_level": None
        }

    try:
        # -------------------------
        # Prepare feature array
        # (Order MUST match training)
        # -------------------------
        features = np.array([[
            data["rain"],
            data["water_distance"],
            data["NDVI"],
            data["distance_to_forest"],
            data["animal_type"],
            data["vehicle_type"]
        ]])

        # -------------------------
        # Model prediction
        # -------------------------
        risk_score = risk_model.predict_proba(features)[0][1]

        # -------------------------
        # Risk level logic
        # -------------------------
        if risk_score >= 0.7:
            risk_level = "HIGH"
        elif risk_score >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # -------------------------
        # Return response
        # -------------------------
        return {
            "risk_score": round(float(risk_score), 3),
            "risk_level": risk_level
        }
    
    except Exception as e:
        return {
            "error": f"Prediction failed: {str(e)}",
            "risk_score": None,
            "risk_level": None
        }

# =========================
# 9. ROOT TEST ENDPOINT
# =========================
@app.get("/")
def root():
    return {
        "status": "API is running",
        "collision_model_loaded": collision_model is not None,
        "risk_model_loaded": risk_model is not None
    }

# =========================
# 10. RUN SERVER
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
