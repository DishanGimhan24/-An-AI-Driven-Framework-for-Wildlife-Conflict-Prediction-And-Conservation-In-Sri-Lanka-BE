"""schemas/prediction_v2.py — All Pydantic models for API request/response."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class PredictRequest(BaseModel):
    region:               str   = Field(..., example="Polonnaruwa")
    month:                int   = Field(..., ge=1, le=12, example=8)
    recent_offence_count: int   = Field(default=0, ge=0, example=3)
    rainfall_mm:          Optional[float] = Field(default=None, ge=0, example=42.0)


class OffenceProb(BaseModel):
    name:        str
    probability: float   # 0–100


class PredictResponse(BaseModel):
    region:               str
    month:                int
    month_name:           str
    season:               str
    hotspot_rank:         int
    rainfall_mm:          float
    is_drought:           bool
    risk_level:           str       # "HIGH" | "LOW"
    risk_pct:             float     # 0–100
    warning:              str       # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    warning_emoji:        str
    single_offence:       str       # top grouped offence category
    group_probs:          List[OffenceProb]
    multi_offences:       List[str] # all groups predicted YES
    multi_probs:          List[OffenceProb]
    recommendation:       str


class HotspotItem(BaseModel):
    rank:             int
    region:           str
    total_cases:      int
    high_risk_months: int
    top_offence:      str


class RegionProfile(BaseModel):
    region:               str
    hotspot_rank:         int
    total_cases:          int
    high_risk_months:     int
    top_offence:          str
    peak_month:           str
    monthly_distribution: Dict[str, float]


class BatchRegionRisk(BaseModel):
    rank:       int
    region:     str
    risk_pct:   float
    warning:    str
    offence:    str


class BatchResponse(BaseModel):
    month_name: str
    season:     str
    regions:    List[BatchRegionRisk]
