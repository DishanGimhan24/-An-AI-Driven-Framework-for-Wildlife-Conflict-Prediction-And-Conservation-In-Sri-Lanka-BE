"""predict_v2.py — /api/predict and /api/batch-predict endpoints."""

from fastapi import APIRouter, HTTPException
from prediction_v2 import PredictRequest, PredictResponse, OffenceProb, BatchResponse, BatchRegionRisk
from model_loader_v2 import (
    get_model, get_meta, get_season, get_rainfall,
    get_hotspot_rank, build_feature_vector, MONTH_LABELS
)

router = APIRouter()

EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}


def _warning_level(risk_pct: float) -> str:
    if risk_pct >= 70: return "CRITICAL"
    if risk_pct >= 45: return "HIGH"
    if risk_pct >= 25: return "MEDIUM"
    return "LOW"


def _recommendation(region: str, warning: str, offence: str) -> str:
    msgs = {
        "CRITICAL": f"IMMEDIATE ACTION in {region}. Deploy maximum ranger patrols. "
                    f"Set checkpoints on all access roads. Coordinate with Police Wildlife Unit. "
                    f"Primary threat: {offence}.",
        "HIGH":     f"Elevated threat in {region}. Increase patrol frequency by 50%. "
                    f"Focus on known {offence} routes. Alert neighbouring ranges.",
        "MEDIUM":   f"Moderate risk in {region}. Maintain standard patrols. "
                    f"Monitor {offence} hotspots. Review informant network.",
        "LOW":      f"Low risk period in {region}. Routine patrols sufficient. "
                    f"Use this period for ranger training. Stay alert for opportunistic {offence}.",
    }
    return msgs.get(warning, "")


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    meta = get_meta()
    if req.region not in meta.get("regions", []):
        raise HTTPException(400, f"Unknown region '{req.region}'. "
                                 f"Valid: {sorted(meta['regions'])}")

    feat   = build_feature_vector(req.region, req.month,
                                  req.recent_offence_count, req.rainfall_mm)
    xgb_r  = get_model("xgb_risk")
    xgb_o  = get_model("xgb_offence")
    xgb_ml = get_model("xgb_multilabel")
    le_g   = get_model("le_grouped")
    mlb    = get_model("mlb")

    # Risk
    risk_pct = round(float(xgb_r.predict_proba(feat)[0][1]) * 100, 1)
    warning  = _warning_level(risk_pct)

    # Single-label offence (6 groups)
    grp_probs_raw = xgb_o.predict_proba(feat)[0]
    group_probs   = sorted(
        [OffenceProb(name=le_g.inverse_transform([i])[0],
                     probability=round(float(p)*100, 1))
         for i, p in enumerate(grp_probs_raw)],
        key=lambda x: x.probability, reverse=True
    )

    # Filter out "Other" from being the top actionable offence, unless it's the only one
    valid_offences = [p for p in group_probs if p.name.lower() != "other"]
    single_offence = valid_offences[0].name if valid_offences else group_probs[0].name

    # Multi-label
    ml_probs_raw = xgb_ml.predict_proba(feat)[0]
    multi_probs  = sorted(
        [OffenceProb(name=mlb.classes_[i], probability=round(float(p)*100, 1))
         for i, p in enumerate(ml_probs_raw)],
        key=lambda x: x.probability, reverse=True
    )
    multi_offences = [p.name for p in multi_probs if p.probability >= 50]

    rain_mm   = req.rainfall_mm if req.rainfall_mm is not None else get_rainfall(req.region, req.month)
    h_rank, _ = get_hotspot_rank(req.region)

    from model_loader_v2 import get_model as gm
    import numpy as np
    region_avg = float(np.mean(
        [float(e.get("rainfall_mm", 150)) for e in meta.get("rainfall_lookup", [])
         if e.get("region") == req.region]
    ) or 150)

    return PredictResponse(
        region=req.region,
        month=req.month,
        month_name=MONTH_LABELS[req.month],
        season=get_season(req.month),
        hotspot_rank=h_rank,
        rainfall_mm=round(rain_mm, 1),
        is_drought=rain_mm < region_avg * 0.6,
        risk_level="HIGH" if risk_pct >= 50 else "LOW",
        risk_pct=risk_pct,
        warning=warning,
        warning_emoji=EMOJI[warning],
        single_offence=single_offence,
        group_probs=group_probs,
        multi_offences=multi_offences if multi_offences else [single_offence],
        multi_probs=multi_probs,
        recommendation=_recommendation(req.region, warning, single_offence),
    )


@router.get("/batch-predict/{month}", response_model=BatchResponse)
def batch_predict(month: int):
    """Predict risk for ALL regions for a given month — for the monthly report view."""
    if not 1 <= month <= 12:
        raise HTTPException(400, "Month must be 1–12")
    meta   = get_meta()
    xgb_r  = get_model("xgb_risk")
    xgb_o  = get_model("xgb_offence")
    le_g   = get_model("le_grouped")

    results = []
    for region in meta.get("regions", []):
        feat     = build_feature_vector(region, month)
        risk_pct = round(float(xgb_r.predict_proba(feat)[0][1]) * 100, 1)

        grp_probs_raw = xgb_o.predict_proba(feat)[0]
        probs = sorted(
            [(le_g.inverse_transform([i])[0], p) for i, p in enumerate(grp_probs_raw)],
            key=lambda x: x[1], reverse=True
        )
        valid_probs = [p for p in probs if p[0].lower() != "other"]
        offence = valid_probs[0][0] if valid_probs else probs[0][0]

        warning  = _warning_level(risk_pct)
        results.append(BatchRegionRisk(rank=0, region=region,
                                       risk_pct=risk_pct, warning=warning, offence=offence))

    results.sort(key=lambda x: x.risk_pct, reverse=True)
    for i, r in enumerate(results): r.rank = i + 1

    return BatchResponse(
        month_name=MONTH_LABELS[month],
        season=get_season(month),
        regions=results,
    )
