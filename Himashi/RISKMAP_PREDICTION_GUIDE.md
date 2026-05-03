# RiskMap with Integrated Risk Prediction - Testing Guide

## What's Changed

The RiskMap page now includes an **integrated risk prediction form** in the left control panel. Users can now:
1. Click on the map to select a location
2. Manually enter latitude/longitude
3. Specify distance values
4. Predict collision risk without leaving the RiskMap view

## How to Use

### Step 1: Start Backend & Frontend
```bash
# Terminal 1 - Backend
cd backend
python api.py

# Terminal 2 - Frontend  
cd frontend/dashboard
npm run dev
```

### Step 2: Navigate to Risk Map
- Open the frontend (typically `http://localhost:5173`)
- Click on **"Risk Map"** in the navigation menu
- The map loads with all incident points

### Step 3: Use the Prediction Form

**Option A: Click Map to Select Location**
1. In the left control panel, look for the **"Predict Risk"** section at the top
2. Click anywhere on the map
3. A marker appears at the clicked location
4. Latitude and Longitude fields auto-populate

**Option B: Manual Coordinate Entry**
1. Type latitude (e.g., 6.927)
2. Type longitude (e.g., 80.7718)

### Step 4: Enter Distance Values
- **Distance to Forest (m):** Typical range 500-8000m
- **Distance to Water (m):** Typical range 300-5000m
- **Distance to Railway (m):** Typical range 500-10000m

### Step 5: Predict Risk
1. Click the **"Predict Risk"** button
2. Wait for prediction (loading state shown)
3. Result displays with:
   - Risk Score (percentage 0-100%)
   - Risk Level (Low/Medium/High)
   - Color-coded display (green/orange/red)

## Form Location

The prediction form is in the **left control panel** under:
```
Risk Map Controls
└── Predict Risk (top section)
```

## Features

✅ **Interactive Map Selection** - Click map to auto-fill coordinates  
✅ **Manual Entry** - Type coordinates directly  
✅ **Real-time Validation** - Form checks for missing fields  
✅ **Instant Results** - Shows risk assessment immediately  
✅ **Color-Coded Results** - Visual indicator of risk level  
✅ **Error Handling** - Displays helpful error messages  

## Expected Results

### Low Risk (0-40%)
- High distances from forest, water, railway
- Green result box

### Medium Risk (40-70%)
- Moderate distances
- Orange result box

### High Risk (70-100%)
- Low distances from forest, water, railway
- Red result box

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Form not visible | Scroll down in the left control panel |
| Marker not appearing | Make sure you're clicking on the actual map, not form inputs |
| "Failed to fetch" error | Verify backend API is running on port 8000 |
| Empty prediction result | Ensure all fields are filled (lat, lon, distances) |
| Map not responding to clicks | Try refreshing the page |

## Testing Flow

**Recommended Test Sequence:**

1. Open RiskMap page
2. Click on a red incident point to see details
3. Click on different location on map 
4. Watch Latitude/Longitude auto-populate
5. Enter typical distance values (1000, 800, 2000)
6. Click "Predict Risk"
7. View result colors match expectations

## API Endpoint Used

```
POST http://127.0.0.1:8000/predict-collision
```

Request body:
```json
{
  "latitude": 6.927,
  "longitude": 80.7718,  
  "distance_to_forest": 1500,
  "distance_to_water": 800,
  "distance_to_railway": 2000
}
```

Response:
```json
{
  "risk_score": 45.32,
  "risk_level": "Medium",
  "latitude": 6.927,
  "longitude": 80.7718,
  ...
}
```

## Integration Points

The prediction form is integrated with:
- **Map** - Click handler + marker display
- **Left Control Panel** - Top section in form
- **Backend API** - `/predict-collision` endpoint
- **Collision Model** - Instant predictions using trained model

---

**Ready to test?** Start the backend and frontend, then navigate to the Risk Map!
