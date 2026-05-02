"""analysis_v2.py — FIXED: handles actual hotspot key structure."""

from fastapi import APIRouter
from prediction_v2 import HotspotItem
from model_loader_v2 import get_meta, MONTH_LABELS

router = APIRouter()


@router.get("/hotspots")
def get_hotspots(top_n: int = 13):
    meta  = get_meta()
    spots = meta.get("hotspots", [])
    spots = spots[:max(1, min(top_n, len(spots)))]
    return [
        HotspotItem(
            rank=int(h.get("hotspot_rank", i + 1)),
            region=h["region"],
            total_cases=int(h.get("total_cases", 0)),
            # high_risk_months and top_offence may not exist in v3 metadata
            high_risk_months=int(h.get("high_risk_months", 0)),
            top_offence=str(h.get("top_offence") or
                           meta.get("region_offence_map", {}).get(h["region"], "Unknown")),
        )
        for i, h in enumerate(spots)
    ]


@router.get("/offence-types")
def offence_types():
    meta  = get_meta()
    dist  = meta.get("offence_distribution", {})
    if isinstance(dist, list):
        dist = {v: 1 for v in dist}
    total = sum(dist.values()) or 1
    return {
        "groups":      meta.get("offence_groups", []),
        "merge_map":   meta.get("offence_merge_map", {}),
        "distribution": {
            k: {"count": v, "pct": round(v / total * 100, 1)}
            for k, v in sorted(dist.items(), key=lambda x: x[1], reverse=True)
        },
    }


@router.get("/calendar")
def monthly_calendar():
    meta = get_meta()
    result = {}
    for m in range(1, 13):
        ms = str(m)
        result[MONTH_LABELS[m]] = {
            "month_num":    m,
            "festival":     int(meta.get("festival_months",    {}).get(ms, 0)),
            "school_hol":   int(meta.get("school_holidays",    {}).get(ms, 0)),
            "tourist_peak": int(meta.get("tourist_peak",       {}).get(ms, 0)),
            "harvest":      int(meta.get("harvest_months",     {}).get(ms, 0)),
            "avg_rainfall": int(meta.get("sl_monthly_rainfall",{}).get(ms, 150)),
        }
    return result
