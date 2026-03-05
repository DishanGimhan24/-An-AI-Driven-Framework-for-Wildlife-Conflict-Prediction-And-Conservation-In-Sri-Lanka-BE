"""
Phase 3: REST API
Provides endpoints for corridor information and conflict risk prediction
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from scipy.spatial import cKDTree
import uvicorn

# ============================================================================
# CONFIGURATION
# ============================================================================


class Config:
    MODEL_PATH = './outputs/elephant_presence_model.pkl'
    ENCODERS_PATH = './outputs/label_encoders.pkl'
    FEATURES_PATH = './outputs/feature_columns.pkl'
    LANDCOVER_PATH = './outputs/landcover_columns.pkl'
    CORRIDOR_PATH = './outputs/corridor_network.json'

    API_HOST = "0.0.0.0"
    API_PORT = 8000

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class RiskPredictionInput(BaseModel):
    """Input for risk prediction"""
    latitude: float
    longitude: float
    datetime: Optional[str] = None  # ISO format, defaults to now
    # Optional features - if not provided, will be interpolated from nearest node
    human_distance: Optional[float] = None
    road_distance: Optional[float] = None
    water_distance: Optional[float] = None
    elevation: Optional[float] = None
    land_cover: Optional[int] = None  # 10, 20, 30, 40, 50, 60, 80, 90
    ndvi: Optional[float] = None  # -1 to 1 normalized


class NodeInfo(BaseModel):
    """Node/Zone information"""
    node_id: int
    center_lat: float
    center_lon: float
    radius_meters: float
    elephant_count: int
    sighting_count: int
    active_hours: List[int]
    avg_ndvi: float
    avg_human_distance: float
    safety_score: float = 0.0


class RoadCrossingInfo(BaseModel):
    """Road crossing point on an elephant corridor"""
    crossing_id: str
    corridor_id: str
    road_osm_id: int
    road_type: str
    crossing_lat: float
    crossing_lon: float
    # Usage stats
    crossing_count: int
    elephant_count: int
    elephants: List[str]
    # Timing
    hour_distribution: dict
    season_distribution: dict
    night_ratio: float
    peak_hours: List[int]
    peak_season: str
    peak_time_of_day: str
    # Danger
    avg_human_distance: float
    traffic_exposure: float
    danger_score: float
    danger_level: str


class CorridorInfo(BaseModel):
    """Corridor path information"""
    corridor_id: str
    from_node: int
    to_node: int
    path: List[dict]
    distance_meters: float
    usage_count: int
    crossing_count: int
    active_hours: List[int]
    safety_score: float
    avg_human_distance: float
    road_crossings: Optional[List[dict]] = []


class RiskPredictionOutput(BaseModel):
    """Output for risk prediction"""
    risk_level: str
    elephant_probability: float
    conflict_risk_score: float
    near_corridor: bool
    nearest_node: Optional[dict] = None
    distance_to_node: float
    nearest_corridor: Optional[dict] = None
    distance_to_corridor: Optional[float] = None
    # Shows which node was used for interpolation
    interpolated_from: Optional[dict] = None
    recommendations: List[str]

# ============================================================================
# LOAD MODELS AND DATA
# ============================================================================


print("Loading models and data...")

model = joblib.load(Config.MODEL_PATH)
label_encoders = joblib.load(Config.ENCODERS_PATH)
feature_columns = joblib.load(Config.FEATURES_PATH)
landcover_columns = joblib.load(Config.LANDCOVER_PATH)

with open(Config.CORRIDOR_PATH, 'r') as f:
    corridor_network = json.load(f)

print(
    f"Loaded: Model, {len(corridor_network['nodes'])} nodes, {len(corridor_network['corridors'])} corridors")
print(f"Feature columns: {len(feature_columns)}")
print(f"LandCover columns: {landcover_columns}")

# Build KD-Tree from nodes for fast nearest-neighbor lookup at inference
node_coords = np.array([[n['center_lat'], n['center_lon']]
                       for n in corridor_network['nodes']])
node_kdtree = cKDTree(node_coords)
print(
    f"Built KD-Tree with {len(node_coords)} nodes for environment interpolation")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two points"""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


def distance_to_line_segment(px, py, x1, y1, x2, y2):
    """Calculate shortest distance from point to line segment"""
    # Vector from point 1 to point 2
    dx = x2 - x1
    dy = y2 - y1

    # Avoid division by zero
    if dx == 0 and dy == 0:
        return haversine_distance(px, py, x1, y1)

    # Project point onto line
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

    # Find closest point on line segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    return haversine_distance(px, py, closest_x, closest_y)


def find_nearest_node(lat, lon):
    """Find nearest node and distance to it"""
    min_dist = float('inf')
    nearest = None

    for node in corridor_network['nodes']:
        dist = haversine_distance(
            lat, lon, node['center_lat'], node['center_lon'])
        if dist < min_dist:
            min_dist = dist
            nearest = node

    return nearest, min_dist


def find_nearest_corridor(lat, lon):
    """Find nearest corridor and distance to it"""
    min_dist = float('inf')
    nearest = None

    for corridor in corridor_network['corridors']:
        path = corridor['path']
        if len(path) >= 2:
            dist = distance_to_line_segment(
                lat, lon,
                path[0]['lat'], path[0]['lon'],
                path[1]['lat'], path[1]['lon']
            )
            if dist < min_dist:
                min_dist = dist
                nearest = corridor

    return nearest, min_dist


def categorize_time_of_day(hour):
    """Categorize hour into time of day"""
    if hour < 6:
        return 'Night'
    elif hour < 10:
        return 'Early Morning'
    elif hour < 14:
        return 'Midday'
    elif hour < 18:
        return 'Afternoon'
    elif hour < 22:
        return 'Evening'
    else:
        return 'Night'


def get_season(month):
    """Get Sri Lankan season from month"""
    season_map = {
        12: 'Dry', 1: 'Dry', 2: 'Dry',
        3: 'Inter-Monsoon', 4: 'Inter-Monsoon', 5: 'Inter-Monsoon',
        6: 'Southwest-Monsoon', 7: 'Southwest-Monsoon', 8: 'Southwest-Monsoon',
        9: 'Inter-Monsoon-2', 10: 'Inter-Monsoon-2', 11: 'Inter-Monsoon-2'
    }
    return season_map.get(month, 'Southwest-Monsoon')


def get_interpolated_environment(lat, lon):
    """Get environmental features from nearest known node"""
    _, nearest_idx = node_kdtree.query([lat, lon])
    nearest_node = corridor_network['nodes'][nearest_idx]

    return {
        'node_id': nearest_node['node_id'],
        'ndvi': nearest_node['avg_ndvi'],
        'land_cover': int(nearest_node['land_cover']),
        'human_distance': nearest_node['avg_human_distance'],
        'protected': nearest_node['protected'],
        'center_lat': nearest_node['center_lat'],
        'center_lon': nearest_node['center_lon']
    }


def prepare_features(lat, lon, dt, human_distance, road_distance, water_distance, elevation, land_cover, ndvi):
    """
    Prepare features for model prediction

    - lat/lon used ONLY for interpolation, NOT as model features
    - One-hot encoded LandCover
    - Missing values interpolated from nearest known node
    """

    # Interpolate missing values from nearest node
    interpolated = get_interpolated_environment(lat, lon)

    # Base features (NO lat/lon - model learns habitat patterns only)
    # Use interpolated values when user doesn't provide them
    features = {
        'Hour': dt.hour,
        'Month': dt.month,
        'DayOfWeek': dt.weekday(),
        'NDVI_normalized': ndvi if ndvi is not None else interpolated['ndvi'],
        # No elevation in nodes, use median
        'Elevation': elevation if elevation is not None else 100,
        # No road dist in nodes, use median
        'RoadDistance': road_distance if road_distance is not None else 1525,
        # No water dist in nodes, use median
        'WaterDistance': water_distance if water_distance is not None else 1599,
        'HumanDistance': human_distance if human_distance is not None else interpolated['human_distance'],
        'Protected': interpolated['protected']
    }

    # Use interpolated land cover if not provided
    actual_land_cover = land_cover if land_cover is not None else interpolated['land_cover']

    # One-hot encode LandCover
    for lc_col in landcover_columns:
        lc_value = float(lc_col.replace('LC_', ''))
        features[lc_col] = 1 if lc_value == actual_land_cover else 0

    # Encode categorical features
    season = get_season(dt.month)
    time_of_day = categorize_time_of_day(dt.hour)

    features['Season_encoded'] = label_encoders['Season'].transform([season])[
        0]
    features['TimeOfDay_encoded'] = label_encoders['TimeOfDay'].transform([
                                                                          time_of_day])[0]

    # Create dataframe with correct column order
    df_features = pd.DataFrame([features])

    # Ensure all feature columns exist
    for col in feature_columns:
        if col not in df_features.columns:
            df_features[col] = 0

    return df_features[feature_columns], interpolated


def calculate_conflict_risk(elephant_prob, human_distance, distance_to_node, distance_to_corridor, hour):
    """
    Calculate conflict risk score based on:
    - Distance to known corridors/nodes (PRIMARY factor)
    - Elephant presence probability (from ML model)
    - Proximity to human settlements
    - Time of day (night = higher risk)

    Returns: 0-100 score
    """

    # Distance factor is PRIMARY (0.0 to 1.0)
    # Closer to corridor = higher risk
    min_distance = min(
        distance_to_node, distance_to_corridor) if distance_to_corridor else distance_to_node

    if min_distance < 500:
        distance_factor = 1.0
    elif min_distance < 1000:
        distance_factor = 0.8
    elif min_distance < 2000:
        distance_factor = 0.6
    elif min_distance < 5000:
        distance_factor = 0.3
    else:
        distance_factor = 0.1  # Far from corridors = low risk

    # Human proximity factor (closer to humans = higher CONFLICT risk)
    if human_distance is None:
        human_proximity = 0.5
    elif human_distance < 500:
        human_proximity = 1.0
    elif human_distance < 1000:
        human_proximity = 0.8
    elif human_distance < 2000:
        human_proximity = 0.5
    else:
        human_proximity = 0.3

    # Time factor
    if hour >= 18 or hour <= 6:
        time_factor = 1.3
    elif hour >= 6 and hour < 10:
        time_factor = 1.1
    else:
        time_factor = 1.0

    # Final risk: distance is weighted 50%, elephant_prob 30%, human proximity 20%
    risk_score = (
        (distance_factor * 50) +
        (elephant_prob * 30) +
        (human_proximity * 20)
    ) * time_factor

    return min(risk_score, 100)


def determine_risk_level(elephant_prob, conflict_risk, distance_to_node, distance_to_corridor, near_corridor, hour):
    """
    Determine risk level (High/Medium/Low) based on multiple factors
    """

    # Distance is the PRIMARY factor
    # If far from all known elephant zones, risk is low
    min_distance = min(
        distance_to_node, distance_to_corridor) if distance_to_corridor else distance_to_node

    # Far from any known elephant activity = LOW risk
    if min_distance > 5000:  # More than 5km from any node/corridor
        return "Low"

    # HIGH risk conditions (must be close to corridors)
    if min_distance < 500:  # Within 500m of corridor/node
        if elephant_prob > 0.6:
            return "High"
        if hour >= 18 or hour <= 6:  # Night time
            return "High"

    if min_distance < 1000 and elephant_prob > 0.7:  # Within 1km, high probability
        if hour >= 18 or hour <= 6:
            return "High"

    if conflict_risk > 70:
        return "High"

    # MEDIUM risk conditions
    if min_distance < 2000:  # Within 2km
        if elephant_prob > 0.5:
            return "Medium"

    if min_distance < 3000 and near_corridor:  # Within 3km of active corridor
        return "Medium"

    if conflict_risk > 40:
        return "Medium"

    # Default to LOW
    return "Low"


def generate_recommendations(risk_level, elephant_prob, near_corridor, corridor_active, human_dist, hour, distance_to_corridor):
    """Generate safety recommendations based on risk assessment"""
    recommendations = []

    if risk_level == "High":
        recommendations.append(
            "HIGH RISK: Elephant presence highly likely in this area")
        recommendations.append(
            "Avoid this area if possible, especially after dark")
        recommendations.append(
            "If you must travel, use main roads and stay in vehicles")
        recommendations.append(
            "Emergency contact - Wildlife Dept: +94 11 244 4241")
    elif risk_level == "Medium":
        recommendations.append(
            "MEDIUM RISK: Moderate elephant activity in this area")
        recommendations.append("Stay alert and avoid isolated paths")
        recommendations.append("Travel in groups if possible")
    else:
        recommendations.append(
            "LOW RISK: Minimal elephant activity expected")
        recommendations.append("Maintain general awareness of surroundings")

    if near_corridor:
        recommendations.append(
            f"You are near a known elephant movement corridor ({distance_to_corridor:.0f}m)")

    if corridor_active:
        recommendations.append(
            "This corridor is typically active at this hour")

    if hour >= 18 or hour <= 6:
        recommendations.append("🌙 Night hours - elephants are more active")

    if human_dist is not None and human_dist < 1000:
        recommendations.append(
            f"Close to human settlements ({human_dist:.0f}m) - potential conflict zone")

    return recommendations

# ============================================================================
# FASTAPI APP
# ============================================================================


app = FastAPI(
    title="Elephant Corridor & Risk Prediction API",
    description="Predicts elephant movement corridors and conflict risk in Sri Lanka",
    version="2.1.0"
)

# Add CORS middleware to allow React frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Elephant Corridor & Risk Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "corridors": "/corridors",
            "nodes": "/nodes",
            "road_crossings": "/road-crossings",
            "road_crossings_summary": "/road-crossings/summary",
            "predict_risk": "/predict_risk"
        },
        "corridor_network": {
            "total_nodes": len(corridor_network['nodes']),
            "total_corridors": len(corridor_network['corridors']),
            "total_road_crossings": len(corridor_network.get('road_crossings', []))
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "corridors_loaded": corridor_network is not None,
        "feature_count": len(feature_columns),
        "interpolation_ready": node_kdtree is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/nodes", response_model=List[NodeInfo])
async def get_all_nodes():
    """Get all node/zone information"""
    nodes_with_safety = []
    for node in corridor_network['nodes']:
        node_copy = node.copy()
        safety_score = (
            (min(node['avg_human_distance'] / 5000, 1) * 60) +
            (node['protected'] * 40)
        )
        node_copy['safety_score'] = min(safety_score, 100)
        nodes_with_safety.append(node_copy)
    return nodes_with_safety


@app.get("/nodes/{node_id}", response_model=NodeInfo)
async def get_node_detail(node_id: int):
    """Get specific node details"""
    for node in corridor_network['nodes']:
        if node['node_id'] == node_id:
            node_copy = node.copy()
            safety_score = (
                (min(node['avg_human_distance'] / 5000, 1) * 60) +
                (node['protected'] * 40)
            )
            node_copy['safety_score'] = min(safety_score, 100)
            return node_copy

    raise HTTPException(status_code=404, detail=f"Node {node_id} not found")


@app.get("/corridors", response_model=List[CorridorInfo])
async def get_all_corridors():
    """Get all corridor information"""
    return corridor_network['corridors']


@app.get("/corridors/{corridor_id}", response_model=CorridorInfo)
async def get_corridor_detail(corridor_id: str):
    """Get specific corridor details"""
    for corridor in corridor_network['corridors']:
        if corridor['corridor_id'] == corridor_id:
            return corridor

    raise HTTPException(
        status_code=404, detail=f"Corridor {corridor_id} not found")


@app.get("/road-crossings", response_model=List[RoadCrossingInfo])
async def get_all_road_crossings(
    danger_level: Optional[str] = None,
    corridor_id: Optional[str] = None,
    min_crossings: Optional[int] = None
):
    """
    Get all detected road crossings along elephant corridors.

    Optional filters:
    - danger_level: High | Medium | Low
    - corridor_id: filter to a specific corridor
    - min_crossings: minimum number of elephant crossing events
    """
    crossings = corridor_network.get('road_crossings', [])

    if danger_level:
        crossings = [c for c in crossings if c['danger_level'] == danger_level]
    if corridor_id:
        crossings = [c for c in crossings if c['corridor_id'] == corridor_id]
    if min_crossings is not None:
        crossings = [c for c in crossings if c['crossing_count'] >= min_crossings]

    return sorted(crossings, key=lambda x: x['danger_score'], reverse=True)


@app.get("/road-crossings/summary")
async def get_road_crossings_summary():
    """Summary statistics for all road crossings"""
    crossings = corridor_network.get('road_crossings', [])

    if not crossings:
        return {"total": 0, "by_danger": {}, "by_road_type": {}, "top_dangerous": []}

    by_danger = {}
    by_type = {}
    by_season = {}
    night_crossings = 0

    for c in crossings:
        by_danger[c['danger_level']] = by_danger.get(c['danger_level'], 0) + 1
        by_type[c['road_type']]      = by_type.get(c['road_type'], 0) + 1
        by_season[c['peak_season']]  = by_season.get(c['peak_season'], 0) + 1
        if c['night_ratio'] > 0.5:
            night_crossings += 1

    top5 = sorted(crossings, key=lambda x: x['danger_score'], reverse=True)[:5]

    return {
        "total": len(crossings),
        "by_danger_level": by_danger,
        "by_road_type": by_type,
        "by_peak_season": by_season,
        "primarily_night_crossings": night_crossings,
        "top_5_dangerous": [
            {
                "crossing_id": c['crossing_id'],
                "corridor_id": c['corridor_id'],
                "road_type": c['road_type'],
                "danger_level": c['danger_level'],
                "danger_score": c['danger_score'],
                "night_ratio": c['night_ratio'],
                "crossing_count": c['crossing_count'],
                "peak_season": c['peak_season'],
                "peak_time_of_day": c['peak_time_of_day'],
                "lat": c['crossing_lat'],
                "lon": c['crossing_lon']
            }
            for c in top5
        ]
    }


@app.get("/road-crossings/{crossing_id}", response_model=RoadCrossingInfo)
async def get_road_crossing_detail(crossing_id: str):
    """Get detailed information for a specific road crossing"""
    for c in corridor_network.get('road_crossings', []):
        if c['crossing_id'] == crossing_id:
            return c
    raise HTTPException(status_code=404, detail=f"Road crossing '{crossing_id}' not found")


@app.post("/predict_risk", response_model=RiskPredictionOutput)
async def predict_risk(input_data: RiskPredictionInput):
    """
    Predict elephant conflict risk for a given location and time

    Returns risk level, elephant presence probability, conflict risk score, and recommendations
    """
    try:
        # Parse datetime
        if input_data.datetime:
            try:
                dt = datetime.fromisoformat(
                    input_data.datetime.replace('Z', '+00:00'))
            except:
                dt = datetime.now()
        else:
            dt = datetime.now()

        # Find nearest node and corridor (using lat/lon)
        nearest_node, dist_to_node = find_nearest_node(
            input_data.latitude, input_data.longitude)
        nearest_corridor, dist_to_corridor = find_nearest_corridor(
            input_data.latitude, input_data.longitude)

        # ============================================================================
        # DISTANCE THRESHOLD CHECK - Prevent misleading predictions for distant locations
        # ============================================================================
        MAX_SAFE_DISTANCE = 25000  # 25km threshold

        if dist_to_node > MAX_SAFE_DISTANCE:
            # Location is too far from any elephant activity
            return RiskPredictionOutput(
                risk_level="Low",
                elephant_probability=0.0,
                conflict_risk_score=0.0,
                near_corridor=False,
                nearest_node=nearest_node,
                distance_to_node=float(dist_to_node),
                nearest_corridor=None,
                distance_to_corridor=None,
                interpolated_from=None,
                recommendations=[
                    f"This location is {dist_to_node/1000:.1f}km from the nearest elephant activity zone",
                    "No significant elephant activity recorded in this area",
                    "Risk level: LOW - No wildlife conflict expected",
                    f"Nearest recorded elephant activity is {dist_to_node/1000:.1f}km away in Node #{nearest_node['node_id']}",
                    f"💡 Suggestion: Navigate to lat: {nearest_node['center_lat']:.4f}, lon: {nearest_node['center_lon']:.4f} to see active elephant zones"
                ]
            )

        # Prepare features for prediction (lat/lon used for interpolation, NOT as features)
        features, interpolated = prepare_features(
            input_data.latitude,
            input_data.longitude,
            dt,
            input_data.human_distance,
            input_data.road_distance,
            input_data.water_distance,
            input_data.elevation,
            input_data.land_cover,
            input_data.ndvi
        )

        # Predict elephant probability (NO scaling needed)
        elephant_probability = float(model.predict_proba(features)[0][1])

        # Get human distance (from input or interpolated)
        human_dist = input_data.human_distance if input_data.human_distance is not None else interpolated[
            'human_distance']

        # Calculate conflict risk score
        conflict_risk = calculate_conflict_risk(
            elephant_probability,
            human_dist,
            dist_to_node,
            dist_to_corridor,
            dt.hour
        )

        # Determine risk level
        near_corridor = dist_to_corridor < 500 if dist_to_corridor else False
        corridor_active = dt.hour in nearest_corridor['active_hours'] if nearest_corridor else False

        risk_level = determine_risk_level(
            elephant_probability,
            conflict_risk,
            dist_to_node,
            dist_to_corridor,
            near_corridor,
            dt.hour
        )

        # Generate recommendations
        recommendations = generate_recommendations(
            risk_level,
            elephant_probability,
            near_corridor,
            corridor_active,
            human_dist,
            dt.hour,
            dist_to_corridor
        )

        return RiskPredictionOutput(
            risk_level=risk_level,
            elephant_probability=elephant_probability,
            conflict_risk_score=conflict_risk,
            near_corridor=near_corridor,
            nearest_node=nearest_node,
            distance_to_node=float(dist_to_node),
            nearest_corridor=nearest_corridor,
            distance_to_corridor=float(
                dist_to_corridor) if dist_to_corridor else None,
            interpolated_from={
                'node_id': interpolated['node_id'],
                'center_lat': interpolated['center_lat'],
                'center_lon': interpolated['center_lon']
            },
            recommendations=recommendations
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Prediction error: {str(e)}")

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("STARTING ELEPHANT CORRIDOR & RISK PREDICTION API")
    print("="*70)
    print(f"\nAPI URL: http://{Config.API_HOST}:{Config.API_PORT}")
    print(f"Interactive Docs: http://{Config.API_HOST}:{Config.API_PORT}/docs")
    print(
        f"Alternative Docs: http://{Config.API_HOST}:{Config.API_PORT}/redoc")
    print("\nPress Ctrl+C to stop\n")
    print("="*70 + "\n")

    uvicorn.run(
        "api:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=False
    )
