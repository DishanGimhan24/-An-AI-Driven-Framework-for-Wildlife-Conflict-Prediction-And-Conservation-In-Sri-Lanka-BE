# Smart Animal-Vehicle Collision (AVC) Risk Prediction Feature

## Overview
This document describes the complete implementation of the risk prediction feature for the Smart AVC system, which allows users to predict collision risk at specific locations based on environmental distance features.

## Implementation Summary

### ✅ What's Been Implemented

#### 1. **Backend API Updates** (`backend/api.py`)
- **New Endpoint:** `/predict-collision` (POST)
  - Accepts latitude, longitude, and three distance features
  - Loads the trained collision model from `collision_model_system/model/random_forest_collision_model.pkl`
  - Returns risk score (0-100%) and risk level classification
  
- **Model Loading:**
  - Dynamically loads collision model from `collision_model_system`
  - Falls back to legacy model if available for backward compatibility
  - Logs which models are successfully loaded on startup

- **Risk Level Classification:**
  - 0-40%: **Low** Risk
  - 40-70%: **Medium** Risk
  - 70-100%: **High** Risk

- **Legacy Endpoint:** `/predict` (POST)
  - Maintained for backward compatibility with existing clients
  - Uses optional risk model if available

#### 2. **Frontend UI: Interactive Prediction Page** (`frontend/dashboard/src/pages/Prediction.jsx`)

**Features:**
- **Interactive Map (Left Column):**
  - Leaflet-based map centered on Sri Lanka
  - Click anywhere to select a location
  - Selected location shows as a marker
  - Automatically populates latitude and longitude fields

- **Prediction Form (Right Column):**
  - **Location Information:**
    - Latitude (auto-filled from map or manual entry)
    - Longitude (auto-filled from map or manual entry)
  
  - **Distance Features (in meters):**
    - Distance to Forest: Typical range 500-8000m
    - Distance to Water: Typical range 300-5000m
    - Distance to Railway: Typical range 500-10000m
  
  - **Predict Risk Button:**
    - Sends request to backend `/predict-collision` endpoint
    - Shows loading state while processing
    - Handles errors gracefully

- **Risk Assessment Results:**
  - Displays risk score as percentage (0-100%)
  - Shows risk level (Low/Medium/High)
  - Color-coded display:
    - 🟢 Green for Low risk
    - 🟡 Orange for Medium risk
    - 🔴 Red for High risk
  - Provides contextual guidance based on risk level

#### 3. **Styling Updates** (`frontend/dashboard/src/pages/Prediction.css`)
- Modern two-column layout (map + form)
- Responsive design for mobile devices
- Smooth animations and transitions
- Professional color scheme matching the app theme
- Proper visual hierarchy and spacing

### 🔧 Technical Details

**Model Details:**
- Model Type: Random Forest Classifier
- Number of Features: 3
  1. `distance_to_forest` (meters)
  2. `distance_to_railway` (meters)
  3. `distance_to_water` (meters)
- Output: Probability of collision at given location

**API Request Format:**
```json
{
  "latitude": 6.927,
  "longitude": 80.7718,
  "distance_to_forest": 1500,
  "distance_to_water": 800,
  "distance_to_railway": 2000
}
```

**API Response Format:**
```json
{
  "risk_score": 45.32,
  "risk_level": "Medium",
  "latitude": 6.927,
  "longitude": 80.7718,
  "distance_to_forest": 1500,
  "distance_to_water": 800,
  "distance_to_railway": 2000
}
```

## How to Use

### For Users:

1. **Navigate to Prediction Page:**
   - Click on the Prediction menu item in the navigation

2. **Select Location:**
   - Click on the map (left side) to select your location of interest
   - Or manually enter latitude and longitude coordinates

3. **Enter Distance Values:**
   - Distance to Forest (meters)
   - Distance to Water (meters)
   - Distance to Railway (meters)
   - *Typical ranges are shown for reference*

4. **Predict Risk:**
   - Click the "Predict Risk" button
   - Wait for the prediction result
   - View the risk assessment with color-coded risk level

### For Developers:

**Running the Backend:**
```bash
cd backend
python api.py
# API will start on http://127.0.0.1:8000
```

**Running the Frontend:**
```bash
cd frontend/dashboard
npm run dev
# Frontend will start (typically on http://localhost:5173)
```

**Testing the API Endpoint:**
```bash
curl -X POST http://127.0.0.1:8000/predict-collision \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 6.927,
    "longitude": 80.7718,
    "distance_to_forest": 1500,
    "distance_to_water": 800,
    "distance_to_railway": 2000
  }'
```

## File Changes

### Modified Files:
1. **`backend/api.py`**
   - Added collision prediction endpoint
   - Improved model loading with error handling
   - Added Pydantic request models

2. **`frontend/dashboard/src/pages/Prediction.jsx`**
   - Complete rewrite with map integration
   - Interactive location selection
   - Proper form handling and validation

3. **`frontend/dashboard/src/pages/Prediction.css`**
   - New responsive two-column layout
   - Enhanced styling for map and form sections
   - Color-coded risk level display

## Dependencies Used

**Backend:**
- `FastAPI` - Web framework
- `joblib` - Model loading
- `numpy` - Numerical operations
- `pydantic` - Request validation

**Frontend:**
- `react-leaflet` - Map component
- `leaflet` - Mapping library
- `react` - UI framework

All dependencies are already installed in the project.

## Error Handling

The implementation includes comprehensive error handling:

- **Model Loading Failures:**
  - API returns error message if model cannot be loaded
  - Logs warnings during startup
  - Provides fallback options

- **API Errors:**
  - Returns structured error responses
  - Catches prediction exceptions
  - Shows user-friendly error messages

- **Form Validation:**
  - Validates required fields
  - Checks coordinate values
  - Validates distance ranges

## Future Enhancements

Possible improvements for future versions:

1. **Automatic Distance Calculation:**
   - Integrate GIS data to automatically calculate distances from coordinates
   - Use proximity algorithms (Haversine, etc.)

2. **Batch Prediction:**
   - Allow users to upload CSV files with multiple locations
   - Generate risk reports for areas

3. **Historical Data:**
   - Store prediction history
   - Analyze trends over time

4. **Better Map Features:**
   - Heatmap visualization of risk zones
   - Integration with satellite/aerial imagery
   - Overlay of forests, water bodies, railways

5. **Model Improvements:**
   - Train on more recent collision data
   - Include additional features (road type, time of day, etc.)
   - Implement ensemble methods

## Testing

The implementation has been verified for:
- ✅ Model loading and accessibility
- ✅ API endpoint structure and validation
- ✅ Frontend component rendering
- ✅ Map interaction and marker placement
- ✅ Form field population and submission
- ✅ Error handling and user feedback

## Support

For issues or questions:
1. Check that the collision model file exists at `backend/collision_model_system/model/random_forest_collision_model.pkl`
2. Ensure backend API is running on `http://127.0.0.1:8000`
3. Verify frontend is configured to connect to correct backend URL
4. Check browser console for any client-side errors
5. Check terminal for backend error messages

---

**Last Updated:** March 2026
**Feature Status:** ✅ Complete and Ready for Testing
