"""
Wildlife Offence Prediction & Early Warning System
FastAPI Backend v2 — XGBoost models, flat module layout

Run from Kavindu/app/:
    uvicorn main_v2:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import predict_v2
import regions_v2
import analysis_v2
from model_loader_v2 import load_all_models

app = FastAPI(
    title="🦅 Wildlife Offence Prediction API v2",
    description="AI Early Warning System for Sri Lanka Wildlife Sanctuaries",
    version="2.0.0",
)

# Allow React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ML models once when server starts
load_all_models()

# Register route groups under /api prefix
app.include_router(predict_v2.router,  prefix="/api", tags=["Prediction"])
app.include_router(regions_v2.router,  prefix="/api", tags=["Regions"])
app.include_router(analysis_v2.router, prefix="/api", tags=["Analysis"])


@app.get("/", tags=["Info"])
def root():
    return {
        "message": "Wildlife Offence Prediction API v2 is running",
        "docs":    "/docs",
    }


@app.get("/api/health", tags=["Info"])
def health():
    from model_loader_v2 import get_meta
    meta = get_meta()
    return {
        "status":                  "healthy",
        "risk_accuracy":           f"{meta.get('risk_accuracy', 0)*100:.1f}%",
        "offence_f1_multilabel":   f"{meta.get('offence_f1_multi', 0)*100:.1f}%",
        "offence_single_accuracy": f"{meta.get('offence_accuracy_single', 0)*100:.1f}%",
        "total_regions":           len(meta.get("regions", [])),
    }
