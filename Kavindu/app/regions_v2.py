"""regions_v2.py — /api/regions and /api/region/{name}/profile endpoints."""

from fastapi import APIRouter, HTTPException
from prediction_v2 import RegionProfile
from model_loader_v2 import get_meta, get_hotspot_rank, MONTH_LABELS

router = APIRouter()


@router.get("/regions")
def list_regions():
    meta = get_meta()
    hotspot_map = {h["region"]: i + 1 for i, h in enumerate(meta.get("hotspots", []))}
    return {
        "regions": sorted(
            [{"name": r, "hotspot_rank": hotspot_map.get(r, 99)}
             for r in meta.get("regions", [])],
            key=lambda x: x["hotspot_rank"]
        ),
        "count": len(meta.get("regions", [])),
    }


@router.get("/region/{region_name}/profile", response_model=RegionProfile)
def region_profile(region_name: str):
    meta = get_meta()
    if region_name not in meta.get("regions", []):
        raise HTTPException(404, f"Region '{region_name}' not found.")

    monthly_hist = {}
    for e in meta.get("hist_region_month", []):
        if e.get("region") == region_name:
            m = int(e.get("month_num", 1))
            monthly_hist[MONTH_LABELS[m]] = float(e.get("hist_region_month_count", 0))

    monthly_sorted = dict(sorted(monthly_hist.items(), key=lambda x: x[1], reverse=True))
    hotspot_data   = next((h for h in meta.get("hotspots", [])
                           if h["region"] == region_name), {})
    h_rank, _      = get_hotspot_rank(region_name)

    return RegionProfile(
        region=region_name,
        hotspot_rank=h_rank,
        total_cases=int(hotspot_data.get("total_cases", 0)),
        high_risk_months=int(hotspot_data.get("high_risk_months", 0)),
        top_offence=hotspot_data.get("top_offence", "Unknown"),
        peak_month=list(monthly_sorted.keys())[0] if monthly_sorted else "Unknown",
        monthly_distribution={k: round(v, 1) for k, v in monthly_sorted.items()},
    )
