# Smart AVC - Risk Prediction Feature Quick Start Guide

## 🚀 Quick Setup & Testing

### 1. **Start the Backend API**

Open a terminal in the backend directory:
```bash
cd backend
python api.py
```

Expected output:
```
✓ Loaded collision model from c:\Users\User\Desktop\Smart_AVC\backend\collision_model_system\model\random_forest_collision_model.pkl
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2. **Start the Frontend**

Open another terminal in the frontend directory:
```bash
cd frontend/dashboard
npm install  # if dependencies not yet installed
npm run dev
```

Frontend will typically start on `http://localhost:5173`

### 3. **Test the API Endpoint**

Using PowerShell or curl, test the prediction endpoint:

```powershell
$body = @{
    latitude = 6.927
    longitude = 80.7718
    distance_to_forest = 1500
    distance_to_water = 800
    distance_to_railway = 2000
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8000/predict-collision" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body | Select-Object -ExpandProperty Content
```

Expected response:
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

### 4. **Use the Frontend Feature**

1. Open the frontend in your browser (`http://localhost:5173`)
2. Navigate to the **Prediction** page from the menu
3. Click on the map to select a location (or enter coordinates manually)
4. Fill in the distance values:
   - Distance to Forest: 800-2000m
   - Distance to Water: 300-1500m
   - Distance to Railway: 1000-3000m
5. Click **Predict Risk**
6. View the risk assessment result

## 📊 Expected Risk Ranges

For testing with different risk levels:

**Low Risk (0-40%):**
- High distances from forest, water, railway
- Example: forest=5000m, water=4000m, railway=5000m

**Medium Risk (40-70%):**
- Moderate distances
- Example: forest=1500m, water=800m, railway=2000m

**High Risk (70-100%):**
- Low distances from forest, water, railway
- Example: forest=500m, water=300m, railway=500m

## 🐛 Troubleshooting

### Backend Issues:
- **"Model not found"**: Check that collision model exists at `backend/collision_model_system/model/random_forest_collision_model.pkl`
- **CORS errors**: Verify that `allow_origins=["*"]` is set in api.py
- **Port already in use**: Change port or kill process using port 8000

### Frontend Issues:
- **Blank map**: Check network tab for failed tile requests; verify internet connection
- **"Failed to fetch prediction"**: Ensure backend is running on http://127.0.0.1:8000
- **Marker not appearing**: Click map in the light gray area, not on other elements

### API Issues:
```bash
# Check API status
curl http://127.0.0.1:8000/

# Should return:
# {"status":"API is running","collision_model_loaded":true,"risk_model_loaded":false}
```

## 💡 Tips

- Click **anywhere** on the map to update location
- Use **Tab key** to navigate between form fields
- Distance hints show typical ranges for each feature
- Results display **instantly** with color coding
- Try different distances to understand the model's behavior

## 📝 Notes

- The model was trained on distance-based collision data from Sri Lanka
- Geographic coordinates follow the format: latitude (North-South), longitude (East-West)
- All distances should be in meters
- Risk score is a probability percentage (0-100%)

## 🎯 Feature Specifications

| Component | Details |
|-----------|---------|
| **Backend Endpoint** | POST `/predict-collision` |
| **Backend Port** | 8000 |
| **Frontend** | React with Leaflet map |
| **Model Type** | Random Forest Classifier |
| **Features** | 3 (distance-based) |
| **Output Range** | 0-100% risk score |

---

**Ready to test?** Start with step 1 and follow through!
