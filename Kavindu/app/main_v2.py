from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .main import ALL_LOCATIONS, df, predict_for


app = FastAPI(title="Wildlife Offence Prediction API (v2 compatibility)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

REGION_LOCATIONS: Dict[str, List[str]] = defaultdict(list)
for region_name, location_name in ALL_LOCATIONS:
    REGION_LOCATIONS[str(region_name)].append(str(location_name))

RAW_TO_GROUP = {
    "Animal Death/Injury": "Poaching",
    "Animal Parts Trade": "Illegal Trade",
    "Animal Possession": "Illegal Trade",
    "Domestic Animal Trespass": "Other",
    "Drugs/Alcohol": "Illegal Trade",
    "Encroachment/Land": "Land Encroachment",
    "Fire": "Resource Extraction",
    "Hunting/Killing": "Poaching",
    "Illegal Entry": "Land Encroachment",
    "Illegal Fishing": "Resource Extraction",
    "Illegal Logging": "Resource Extraction",
    "Meat/Egg Trade": "Illegal Trade",
    "Mining": "Resource Extraction",
    "Other": "Other",
    "Tusk Theft": "Illegal Trade",
    "Weapons/Traps": "Weapons & Tools",
}

GROUP_ORDER = [
    "Land Encroachment",
    "Illegal Trade",
    "Poaching",
    "Weapons & Tools",
    "Resource Extraction",
    "Other",
]

WARNING_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🟢",
}


class RegionItem(BaseModel):
    name: str
    hotspot_rank: int


class RegionsResponse(BaseModel):
    regions: List[RegionItem]


class PredictRequest(BaseModel):
    region: str
    month: int = Field(ge=1, le=12)
    recent_offence_count: int = Field(default=0, ge=0)
    rainfall_mm: Optional[float] = None


class ProbabilityItem(BaseModel):
    name: str
    probability: float


class PredictResponse(BaseModel):
    region: str
    month: int
    month_name: str
    season: str
    hotspot_rank: int
    rainfall_mm: float
    is_drought: bool
    risk_level: str
    risk_pct: float
    warning: str
    warning_emoji: str
    single_offence: str
    group_probs: List[ProbabilityItem]
    multi_offences: List[str]
    multi_probs: List[ProbabilityItem]
    recommendation: str


def month_name(month: int) -> str:
    return MONTH_NAMES[month - 1]


def season_name(month: int) -> str:
    return "Maha" if month in (10, 11, 12, 1, 2) else "Yala"


def default_rainfall(month: int) -> float:
    return 60.0 if season_name(month) == "Maha" else 42.0


def warning_from_risk(risk_pct: float) -> str:
    if risk_pct >= 70:
        return "CRITICAL"
    if risk_pct >= 45:
        return "HIGH"
    if risk_pct >= 25:
        return "MEDIUM"
    return "LOW"


def risk_level_from_risk(risk_pct: float) -> str:
    if risk_pct >= 60:
        return "HIGH"
    if risk_pct >= 30:
        return "MEDIUM"
    return "LOW"


def offense_group(label: str) -> str:
    return RAW_TO_GROUP.get(label, "Other")


def region_month_rows(region: str, month: int):
    region_rows = df[df["region"] == region]
    month_rows = region_rows[region_rows["month_num"] == month]
    if not month_rows.empty:
        return month_rows
    if not region_rows.empty:
        return region_rows
    month_rows = df[df["month_num"] == month]
    if not month_rows.empty:
        return month_rows
    return df


def historical_group_scores(region: str, month: int) -> Dict[str, float]:
    rows = region_month_rows(region, month)
    scores = {group: 0.0 for group in GROUP_ORDER}

    for row in rows.itertuples(index=False):
        label = str(getattr(row, "top_offence", "Other") or "Other")
        weight = max(float(getattr(row, "total_cases", 0.0) or 0.0), 1.0)
        scores[offense_group(label)] += weight

    if not any(scores.values()):
        for group in GROUP_ORDER:
            scores[group] = 1.0

    return scores


def adjusted_group_scores(region: str, month: int, recent_offence_count: int, is_drought: bool) -> Dict[str, float]:
    scores = historical_group_scores(region, month)

    activity_boost = min(recent_offence_count, 40) * 0.55
    if activity_boost:
        scores["Land Encroachment"] += activity_boost
        scores["Illegal Trade"] += activity_boost * 0.8
        scores["Weapons & Tools"] += activity_boost * 0.55

    if is_drought:
        scores["Poaching"] += 7.0
        scores["Illegal Trade"] += 4.0
        scores["Weapons & Tools"] += 2.5

    return scores


def probability_list(scores: Dict[str, float]) -> List[ProbabilityItem]:
    total = sum(scores.values()) or 1.0
    items = [
        ProbabilityItem(name=name, probability=round((value / total) * 100.0, 1))
        for name, value in scores.items()
    ]
    items.sort(key=lambda item: item.probability, reverse=True)
    return items


def multi_probability_list(group_probs: List[ProbabilityItem], recent_offence_count: int, is_drought: bool) -> List[ProbabilityItem]:
    items: List[ProbabilityItem] = []
    recent_bonus = min(recent_offence_count, 30) * 0.7
    drought_bonus = 8.0 if is_drought else 0.0

    for index, item in enumerate(group_probs):
        priority_bonus = 6.0 if index == 0 else 3.0 if index == 1 else 0.0
        probability = min(99.0, 35.0 + item.probability * 1.35 + recent_bonus + drought_bonus + priority_bonus)
        items.append(ProbabilityItem(name=item.name, probability=round(probability, 1)))

    items.sort(key=lambda item: item.probability, reverse=True)
    return items


def region_predictions(region: str, month: int) -> List[dict]:
    locations = REGION_LOCATIONS.get(region, [])
    if not locations:
        raise HTTPException(status_code=404, detail=f"Unknown region: {region}")

    year = datetime.now().year
    predictions = []
    for location in locations:
        try:
            prediction = predict_for(region, location, year, month)
            predictions.append(prediction)
        except Exception:
            continue

    if not predictions:
        raise HTTPException(status_code=503, detail=f"Could not generate predictions for {region}")

    return predictions


def base_region_score(region: str, month: int) -> float:
    predictions = region_predictions(region, month)
    risks = sorted((float(item["risk_percent"]) for item in predictions), reverse=True)
    top_slice = risks[: min(3, len(risks))]
    top_average = sum(top_slice) / len(top_slice)

    rows = region_month_rows(region, month)
    historical_cases = float(rows["total_cases"].sum()) if "total_cases" in rows else 0.0
    history_boost = min(historical_cases / 18.0, 18.0)

    return max(risks[0], top_average) + history_boost


def risk_pct_for_region(region: str, month: int, recent_offence_count: int, rainfall_mm: float) -> float:
    base_score = base_region_score(region, month)
    recent_boost = min(recent_offence_count, 30) * 0.7
    drought_boost = 8.0 if rainfall_mm < 35.0 else 0.0
    return round(min(99.0, max(1.0, base_score + recent_boost + drought_boost)), 1)


def region_rankings(month: int) -> List[Tuple[str, float]]:
    scores: List[Tuple[str, float]] = []
    for region in sorted(REGION_LOCATIONS):
        try:
            scores.append((region, round(base_region_score(region, month), 1)))
        except HTTPException:
            continue

    scores.sort(key=lambda item: item[1], reverse=True)
    return scores


def recommendation(region: str, warning: str, offence_name: str) -> str:
    if warning == "CRITICAL":
        return (
            f"IMMEDIATE ACTION in {region}. Deploy maximum ranger patrols. "
            f"Set checkpoints on all access roads. Coordinate with Police Wildlife Unit. "
            f"Primary threat: {offence_name}."
        )
    if warning == "HIGH":
        return (
            f"Increase ranger patrol frequency in {region} and prioritize areas linked to {offence_name}. "
            f"Brief local teams before the selected month begins."
        )
    if warning == "MEDIUM":
        return (
            f"Maintain active monitoring in {region} and share an advisory on likely {offence_name} activity."
        )
    return f"Maintain routine patrols in {region} and continue collecting incident intelligence."


@app.get("/api/health")
def health():
    return {"status": "ok", "api": "kavindu-v2"}


@app.get("/api/regions", response_model=RegionsResponse)
def regions():
    ranked_regions = region_rankings(datetime.now().month)
    return RegionsResponse(
        regions=[RegionItem(name=name, hotspot_rank=index + 1) for index, (name, _) in enumerate(ranked_regions)]
    )


@app.post("/api/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    region = request.region.strip()
    if region not in REGION_LOCATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region: {region}")

    rainfall_mm = round(float(request.rainfall_mm if request.rainfall_mm is not None else default_rainfall(request.month)), 1)
    is_drought = rainfall_mm < 35.0
    risk_pct = risk_pct_for_region(region, request.month, request.recent_offence_count, rainfall_mm)
    warning = warning_from_risk(risk_pct)
    risk_level = risk_level_from_risk(risk_pct)

    scores = adjusted_group_scores(region, request.month, request.recent_offence_count, is_drought)
    group_probs = probability_list(scores)
    multi_probs = multi_probability_list(group_probs, request.recent_offence_count, is_drought)
    multi_offences = [item.name for item in multi_probs if item.probability >= 55.0][:5]
    if not multi_offences:
        multi_offences = [item.name for item in multi_probs[:3]]

    ranking_lookup = {name: index + 1 for index, (name, _) in enumerate(region_rankings(request.month))}
    single_offence = group_probs[0].name if group_probs else "Other"

    return PredictResponse(
        region=region,
        month=request.month,
        month_name=month_name(request.month),
        season=season_name(request.month),
        hotspot_rank=ranking_lookup.get(region, len(ranking_lookup) + 1),
        rainfall_mm=rainfall_mm,
        is_drought=is_drought,
        risk_level=risk_level,
        risk_pct=risk_pct,
        warning=warning,
        warning_emoji=WARNING_EMOJI[warning],
        single_offence=single_offence,
        group_probs=group_probs,
        multi_offences=multi_offences,
        multi_probs=multi_probs,
        recommendation=recommendation(region, warning, single_offence),
    )