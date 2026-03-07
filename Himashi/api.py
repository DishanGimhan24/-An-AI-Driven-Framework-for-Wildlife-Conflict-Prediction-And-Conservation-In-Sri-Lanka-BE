from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
import numpy as np
import os
import uvicorn

# =========================
# 1. CREATE APP
# =========================
app = FastAPI(title="Elephant Risk Prediction API")

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
# 3. LOAD TRAINED MODEL
# =========================
# NOTE: path = backend/model/risk_model.pkl
MODEL_PATH = os.getenv("MODEL_PATH", "model/risk_model.pkl")
model = joblib.load(MODEL_PATH)

# =========================
# 4. PREDICTION ENDPOINT
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

    # -------------------------
    # 4.1 Prepare feature array
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
    # 4.2 Model prediction
    # -------------------------
    risk_score = model.predict_proba(features)[0][1]

    # -------------------------
    # 4.3 Risk level logic
    # -------------------------
    if risk_score >= 0.7:
        risk_level = "HIGH"
    elif risk_score >= 0.4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # -------------------------
    # 4.4 Return response
    # -------------------------
    return {
        "risk_score": round(float(risk_score), 3),
        "risk_level": risk_level
    }

# =========================
# 5. ROOT TEST ENDPOINT
# =========================
@app.get("/")
def root():
    return {"status": "API is running"}


# =========================
# 6. RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
