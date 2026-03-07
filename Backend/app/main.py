from typing import List, Dict, Tuple
import json
import joblib
import pandas as pd
import numpy as np
import os
import shutil
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from catboost import CatBoostClassifier
from datetime import datetime
import uuid
from bson.objectid import ObjectId

from .database import connect_to_mongo, close_mongo_connection, get_db
from .models import ReportCreate, LoginRequest, Token, AssignTeamRequest, CreateOfficerRequest, UpdateOfficerRequest
from .auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta


# -------------------------------------------------
# Paths
# -------------------------------------------------
RISK_MODEL_PATH = "artifacts/model/risk_model_v4.cbm"
TYPE_MODEL_PATH = "artifacts/model/type_model_v3.joblib"
META_PATH = "artifacts/model/model_meta_v4.json"
DATASET_PATH = "artifacts/data/ml_dataset_expanded_forecastsafe.csv"

# -------------------------------------------------
# App
# -------------------------------------------------
# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Wildlife Offence Prediction & Early Warning API (v4)")

# Serve the static uploads directory
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("LOADED: Backend/app/main.py (v4 CatBoost risk + v3 type + hotspots + risk level)")

# -------------------------------------------------
# Load meta (training schema)
# -------------------------------------------------
with open(META_PATH, "r") as f:
    meta = json.load(f)

CATEGORICAL_COLS = meta["categorical_features"]
NUMERIC_COLS = meta["numeric_features"]
ALL_FEATURES = CATEGORICAL_COLS + NUMERIC_COLS

# -------------------------------------------------
# Load models
# -------------------------------------------------
# Risk model: CatBoost .cbm
risk_model = CatBoostClassifier()
risk_model.load_model(RISK_MODEL_PATH)

# Type model: sklearn pipeline joblib
type_model = joblib.load(TYPE_MODEL_PATH)

# -------------------------------------------------
# Load dataset for history lookup
# -------------------------------------------------
df = pd.read_csv(DATASET_PATH)

df["year"] = pd.to_numeric(df.get("year"), errors="coerce").fillna(0).astype(int)
df["month_num"] = pd.to_numeric(df.get("month_num"), errors="coerce").fillna(0).astype(int)
df["total_cases"] = pd.to_numeric(df.get("total_cases"), errors="coerce").fillna(0.0).astype(float)
df["has_offence"] = pd.to_numeric(df.get("has_offence"), errors="coerce").fillna(0).astype(int).clip(0, 1)
df["top_offence"] = df.get("top_offence", "None").fillna("None").astype(str)
df["region"] = df.get("region", "Unknown").fillna("Unknown").astype(str)
df["location"] = df.get("location", "Unknown").fillna("Unknown").astype(str)

_lookup: Dict[Tuple[str, str, int, int], dict] = {}
for r in df.itertuples(index=False):
    _lookup[(r.region, r.location, int(r.year), int(r.month_num))] = {
        "total_cases": float(r.total_cases),
        "has_offence": int(r.has_offence),
        "top_offence": str(r.top_offence),
    }

ALL_LOCATIONS = sorted(
    df[["region", "location"]].drop_duplicates().itertuples(index=False, name=None),
    key=lambda x: (x[0], x[1])
)

# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def sri_lanka_season(m: int) -> str:
    if m in (12, 1, 2):
        return "NE_monsoon"
    if m in (5, 6, 7, 8, 9):
        return "SW_monsoon"
    if m in (3, 4):
        return "Inter_MarApr"
    return "Inter_OctNov"

def month_cyc(m: int):
    return float(np.sin(2 * np.pi * m / 12)), float(np.cos(2 * np.pi * m / 12))

def prev_month(y: int, m: int, back: int):
    for _ in range(back):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return y, m

def get_row(region: str, location: str, y: int, m: int) -> dict:
    return _lookup.get((region, location, y, m), {
        "total_cases": 0.0,
        "has_offence": 0,
        "top_offence": "None",
    })

def compute_history(region: str, location: str, year: int, month: int) -> dict:
    past = {i: get_row(region, location, *prev_month(year, month, i)) for i in range(1, 8)}

    return {
        "lag_cases_1": past[1]["total_cases"],
        "lag_cases_2": past[2]["total_cases"],
        "lag_cases_3": past[3]["total_cases"],
        "lag_has_1": past[1]["has_offence"],
        "lag_has_2": past[2]["has_offence"],
        "lag_has_3": past[3]["has_offence"],
        "lag_top_1": past[1]["top_offence"],
        "lag_top_2": past[2]["top_offence"],
        "lag_top_3": past[3]["top_offence"],
        "roll_3_cases": float(np.mean([past[i]["total_cases"] for i in (1, 2, 3)])),
        "roll_6_cases": float(np.mean([past[i]["total_cases"] for i in range(1, 7)])),
        "trend_3": float(past[1]["total_cases"] - past[4]["total_cases"]),
        "trend_6": float(past[1]["total_cases"] - past[7]["total_cases"]),
    }

def risk_level_from_percent(risk_percent: float) -> str:
    if risk_percent < 30:
        return "Low"
    if risk_percent < 60:
        return "Medium"
    return "High"

def predict_for(region: str, location: str, year: int, month: int) -> dict:
    month_sin, month_cos = month_cyc(month)
    season = sri_lanka_season(month)
    hist = compute_history(region, location, year, month)

    row = {
        "region": region,
        "location": location,
        "season": season,
        "month_num": month,
        "month_sin": month_sin,
        "month_cos": month_cos,
        **hist,
    }

    X = pd.DataFrame([row])[ALL_FEATURES]

    risk_prob = float(risk_model.predict_proba(X)[0][1])
    risk_percent = round(risk_prob * 100, 2)
    risk_level = risk_level_from_percent(risk_percent)

    type_probs = type_model.predict_proba(X)[0]
    classes = type_model.named_steps["model"].classes_
    top3_idx = np.argsort(type_probs)[-3:][::-1]
    top3 = [str(classes[i]) for i in top3_idx]

    predicted_type = top3[0]
    if risk_level in ("Medium", "High") and predicted_type == "None":
        for t in top3:
            if t != "None":
                predicted_type = t
                break

    return {
        "location_id": f"{region}|{location}",
        "risk_percent": risk_percent,
        "risk_level": risk_level,
        "predicted_offence_type": predicted_type,
        "top3_offence_types": top3,
    }

# -------------------------------------------------
# Schemas
# -------------------------------------------------
class PredictRequest(BaseModel):
    region: str
    location: str
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)

class PredictResponse(BaseModel):
    location_id: str
    risk_percent: float
    risk_level: str
    predicted_offence_type: str
    top3_offence_types: List[str]

class HotspotItem(BaseModel):
    rank: int
    region: str
    location: str
    risk_percent: float
    risk_level: str
    predicted_offence_type: str

class HotspotsResponse(BaseModel):
    year: int
    month: int
    top_k: int
    items: List[HotspotItem]

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/regions")
def regions():
    return {"regions": sorted(df["region"].dropna().unique().tolist())}

@app.get("/locations")
def locations(region: str):
    sub = df[df["region"] == region]
    return {"locations": sorted(sub["location"].dropna().unique().tolist())}

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if not ((df["region"] == req.region) & (df["location"] == req.location)).any():
        raise HTTPException(status_code=404, detail="Region/location not found. Use dropdowns from /regions and /locations.")

    out = predict_for(req.region, req.location, req.year, req.month)
    return PredictResponse(**out)

@app.get("/hotspots", response_model=HotspotsResponse)
def hotspots(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    top_k: int = Query(10, ge=1, le=100),
):
    results = []
    for region, location in ALL_LOCATIONS:
        out = predict_for(region, location, year, month)
        results.append({
            "region": region,
            "location": location,
            "risk_percent": out["risk_percent"],
            "risk_level": out["risk_level"],
            "predicted_offence_type": out["predicted_offence_type"],
        })

    results.sort(key=lambda r: r["risk_percent"], reverse=True)
    results = results[:top_k]

    items = []
    for i, r in enumerate(results, start=1):
        items.append(HotspotItem(
            rank=i,
            region=r["region"],
            location=r["location"],
            risk_percent=r["risk_percent"],
            risk_level=r["risk_level"],
            predicted_offence_type=r["predicted_offence_type"],
        ))

    return HotspotsResponse(year=year, month=month, top_k=top_k, items=items)

@app.post("/api/reports")
async def create_community_report(report: ReportCreate):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")
        
    report_dict = report.dict()
    report_dict["reference_id"] = f"REP-{uuid.uuid4().hex[:8].upper()}"
    report_dict["status"] = "pending"
    report_dict["source"] = "community"
    report_dict["created_at"] = datetime.utcnow()
    
    result = await db["reports"].insert_one(report_dict)
    
    # ObjectId is not JSON serializable by default, so we convert it to string
    report_dict["_id"] = str(report_dict["_id"])
    
    return {
        "report_id": str(result.inserted_id),
        "reference_id": report_dict["reference_id"],
        "status": report_dict["status"],
        "message": "Report submitted successfully",
        "data": report_dict
    }

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Generate unique filename securely to avoid overwriting or injections
    ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Synchronously save file contextually
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"image_url": f"/uploads/{filename}"}

@app.get("/api/reports")
async def get_all_reports():
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")
        
    cursor = db["reports"].find().sort("created_at", -1)
    reports = await cursor.to_list(length=100)
    
    users_cursor = db["users"].find({}, {"email": 1, "phone": 1, "name": 1})
    users = await users_cursor.to_list(length=1000)
    user_map = {u["email"]: u for u in users}
    
    formatted_reports = []
    for r in reports:
        r["_id"] = str(r["_id"])
        tl = r.get("team_lead")
        if tl and tl in user_map:
            r["team_lead_name"] = user_map[tl].get("name")
            r["team_lead_phone"] = user_map[tl].get("phone")
        formatted_reports.append(r)
        
    return {"reports": formatted_reports}

class StatusUpdate(BaseModel):
    status: str

@app.patch("/api/reports/{report_id}/status")
async def update_report_status(report_id: str, payload: StatusUpdate):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")
        
    try:
        obj_id = ObjectId(report_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Report ID format")
        
    result = await db["reports"].update_one(
        {"_id": obj_id},
        {"$set": {"status": payload.status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Report not found or status identical")
        
    return {"message": "Status updated successfully", "status": payload.status}

@app.post("/api/auth/login", response_model=Token)
async def login(req: LoginRequest):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")
        
    user = await db["users"].find_one({"email": req.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")
        
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user account")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "role": user.get("role", "officer")},
        expires_delta=access_token_expires
    )
    
    return {
        "token": access_token,
        "user": {
            "name": user.get("name", "Unknown"),
            "email": user["email"],
            "role": user.get("role", "officer")
        }
    }

@app.get("/api/officers")
async def get_officers(region: str = Query(None)):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")

    query = {"is_active": {"$ne": False}}
    if region:
        query["region"] = region

    cursor = db["users"].find(query, {"password_hash": 0})
    officers = await cursor.to_list(length=200)

    for o in officers:
        o["_id"] = str(o["_id"])

    return {"officers": officers}

@app.get("/api/officers/suggest")
async def suggest_team(region: str = Query(...), offence_type: str = Query("")):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")

    cursor = db["users"].find({"is_active": {"$ne": False}, "role": "officer"}, {"password_hash": 0})
    all_officers = await cursor.to_list(length=200)
    for o in all_officers:
        o["_id"] = str(o["_id"])

    # Count active (non-resolved) report assignments per officer
    active_reports_cursor = db["reports"].find(
        {"status": {"$nin": ["resolved", "closed"]}, "assigned_team": {"$exists": True, "$ne": []}},
        {"assigned_team": 1}
    )
    active_reports = await active_reports_cursor.to_list(length=1000)

    workload: dict = {}
    for report in active_reports:
        for email in report.get("assigned_team", []):
            workload[email] = workload.get(email, 0) + 1

    region_officers = [o for o in all_officers if o.get("region") == region]
    other_officers = [o for o in all_officers if o.get("region") != region]

    region_officers.sort(key=lambda o: workload.get(o["email"], 0))
    other_officers.sort(key=lambda o: workload.get(o["email"], 0))

    suggestions = region_officers[:3]
    if len(suggestions) < 3:
        suggestions += other_officers[:3 - len(suggestions)]

    for s in suggestions:
        s["active_assignments"] = workload.get(s["email"], 0)

    suggested_lead = suggestions[0]["email"] if suggestions else None

    return {"suggestions": suggestions, "suggested_lead": suggested_lead}


@app.patch("/api/reports/{report_id}/assign")
async def assign_team(report_id: str, payload: AssignTeamRequest):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")

    try:
        obj_id = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Report ID format")

    update_fields = {
        "assigned_team": payload.assigned_team,
        "team_lead": payload.team_lead,
    }

    result = await db["reports"].update_one(
        {"_id": obj_id},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "message": "Team assigned successfully",
        "assigned_team": payload.assigned_team,
        "team_lead": payload.team_lead,
    }

# -------------------------------------------------
# Admin: Officer Management
# -------------------------------------------------

@app.get("/api/admin/officers")
async def admin_list_officers():
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")

    cursor = db["users"].find({}, {"password_hash": 0})
    officers = await cursor.to_list(length=500)
    for o in officers:
        o["_id"] = str(o["_id"])
    return {"officers": officers}

@app.post("/api/admin/officers", status_code=201)
async def admin_create_officer(payload: CreateOfficerRequest):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")

    existing = await db["users"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="An officer with this email already exists")

    doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": get_password_hash(payload.password),
        "role": payload.role,
        "region": payload.region,
        "badge_number": payload.badge_number,
        "phone": payload.phone,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }

    result = await db["users"].insert_one(doc)
    return {"message": "Officer created successfully", "id": str(result.inserted_id)}

@app.patch("/api/admin/officers/{officer_id}")
async def admin_update_officer(officer_id: str, payload: UpdateOfficerRequest):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")

    try:
        obj_id = ObjectId(officer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid officer ID")

    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "email" in updates:
        conflict = await db["users"].find_one({"email": updates["email"], "_id": {"$ne": obj_id}})
        if conflict:
            raise HTTPException(status_code=400, detail="Email already in use by another officer")

    result = await db["users"].update_one({"_id": obj_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Officer not found")

    return {"message": "Officer updated successfully"}

@app.patch("/api/admin/officers/{officer_id}/toggle")
async def admin_toggle_officer(officer_id: str):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database disconnected")

    try:
        obj_id = ObjectId(officer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid officer ID")

    officer = await db["users"].find_one({"_id": obj_id})
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")

    new_status = not officer.get("is_active", True)
    await db["users"].update_one({"_id": obj_id}, {"$set": {"is_active": new_status}})

    return {"message": f"Officer {'activated' if new_status else 'deactivated'}", "is_active": new_status}
