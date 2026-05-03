import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import numpy as np
import pandas as pd
from flask import Blueprint, request

from config import MODELS_DIR
from data_processing.data_loader import data_loader
from ml.district_classifier import DISTRICTS
from utils.response_formatter import error_response, success_response

# Forest/wildlife-habitat reference coordinates per district.
# These sample NDVI from woodland/scrub where elephants actually range,
# not from the urban administrative centre used by DISTRICTS.
_HABITAT_COORDS = {
    'Colombo':      (6.85,  80.07),  # Attidiya / western forest patches
    'Gampaha':      (7.07,  80.15),  # Yagoda / Gampaha forest patches
    'Kalutara':     (6.58,  80.20),  # Ingiriya / Yagirala forest reserve
    'Kandy':        (7.47,  80.82),  # Knuckles Conservation Forest
    'Matale':       (7.95,  80.75),  # Sigiriya / Dambulla dry-zone scrub
    'Nuwara Eliya': (6.97,  80.73),  # Horton Plains fringe
    'Galle':        (6.15,  80.40),  # Kanneliya / Dediyagala forest
    'Matara':       (5.98,  80.65),  # Sinharaja eastern fringe
    'Hambantota':   (6.15,  81.30),  # Bundala NP / Yala fringe
    'Jaffna':       (9.65,  80.12),  # Chundikulam scrubland
    'Kilinochchi':  (9.38,  80.42),  # Iranamadu / Pooneryn scrubland
    'Mannar':       (8.85,  80.02),  # Giants Tank / Wilpattu north
    'Vavuniya':     (8.60,  80.70),  # Maduru Oya fringe / scrubland
    'Mullaitivu':   (9.18,  80.72),  # Mullaitivu coastal dry forest
    'Batticaloa':   (7.72,  81.50),  # Batticaloa lagoon forest patches
    'Ampara':       (7.10,  81.70),  # Gal Oya NP
    'Trincomalee':  (8.50,  81.10),  # Somawathiya NP
    'Kurunegala':   (7.55,  80.30),  # Dumbara valley scrubland
    'Puttalam':     (8.10,  79.95),  # Wilpattu NP south buffer
    'Anuradhapura': (8.40,  80.10),  # Wilpattu NP east / dry-zone forest
    'Polonnaruwa':  (7.90,  80.90),  # Minneriya / Kaudulla NP
    'Badulla':      (7.00,  81.15),  # Lunugala / Uma Oya forests
    'Monaragala':   (6.85,  81.55),  # Lahugala / eastern dry zone
    'Ratnapura':    (6.68,  80.55),  # Sinharaja NP fringe
    'Kegalle':      (7.25,  80.45),  # Kithulgala / Dolosbage forests
}

env_stress_bp = Blueprint('env_stress', __name__)

CACHE_DIR = os.path.join(MODELS_DIR, 'eco_stress')

STRESS_HIGH = 65
STRESS_MEDIUM = 35

DRY_SEASON_MONTHS = {5, 6, 7, 8, 9}

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

BASELINE_YEARS = (2020, 2021, 2022, 2023, 2024)

# NASA POWER grid points covering Sri Lanka (0.5° × 0.625° grid)
_RAINFALL_GRID_LATS = [6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
_RAINFALL_GRID_LONS = [79.375, 80.0, 80.625, 81.25, 81.875, 82.5]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_nearest_grid_point(lat, lon):
    """Return the nearest NASA POWER grid lat/lon to a given point."""
    best_lat = min(_RAINFALL_GRID_LATS, key=lambda x: abs(x - lat))
    best_lon = min(_RAINFALL_GRID_LONS, key=lambda x: abs(x - lon))
    return best_lat, best_lon


def _compute_ndvi_baseline(lat, lon, calendar_month):
    """Average NDVI for a given calendar month across BASELINE_YEARS."""
    values = []
    for year in BASELINE_YEARS:
        v = data_loader.get_ndvi_value(lat, lon, year, calendar_month)
        if v is not None:
            values.append(v)
    return float(np.mean(values)) if values else 0.4


def _compute_rainfall_baseline(grid_lat, grid_lon, calendar_month):
    """Average 30-day monthly rainfall sum at a grid point across BASELINE_YEARS."""
    if data_loader.rainfall_data_raw is None:
        return 0.0

    df = data_loader.rainfall_data_raw
    # Tolerance to handle floating-point equality in CSV values
    mask = (np.abs(df['LAT'] - grid_lat) < 0.01) & (np.abs(df['LON'] - grid_lon) < 0.01)
    point_df = df[mask].copy()

    if point_df.empty:
        # Fall back to national average if grid point not found
        point_df = df.copy()

    point_df['_month'] = point_df['date'].dt.month
    point_df['_year'] = point_df['date'].dt.year

    monthly_totals = []
    for year in BASELINE_YEARS:
        month_mask = (point_df['_year'] == year) & (point_df['_month'] == calendar_month)
        if month_mask.any():
            monthly_totals.append(float(point_df.loc[month_mask, 'rainfall_mm'].sum()))

    return float(np.mean(monthly_totals)) if monthly_totals else 0.0


def _get_current_rainfall_30day(grid_lat, grid_lon, year, month):
    """30-day rainfall sum at a grid point for a specific year/month."""
    if data_loader.rainfall_data_raw is None:
        # Fall back to monthly average from aggregated data
        info = data_loader._monthly_rainfall_avg.get(month, {})
        return float(info.get('rainfall_30day', 0.0))

    df = data_loader.rainfall_data_raw
    mask = (np.abs(df['LAT'] - grid_lat) < 0.01) & (np.abs(df['LON'] - grid_lon) < 0.01)
    point_df = df[mask].copy()

    if point_df.empty:
        point_df = df.copy()

    point_df['_month'] = point_df['date'].dt.month
    point_df['_year'] = point_df['date'].dt.year
    row_mask = (point_df['_year'] == year) & (point_df['_month'] == month)

    if row_mask.any():
        return float(point_df.loc[row_mask, 'rainfall_mm'].sum())

    # Date beyond data range — use climatological baseline
    return _compute_rainfall_baseline(grid_lat, grid_lon, month)


def _compute_stress_score(ndvi_anomaly, rainfall_anomaly, rainfall_baseline, calendar_month):
    """
    Composite stress score 0–100.
      NDVI deficit:     up to 40 pts  (below baseline → more stress)
      Rainfall deficit: up to 40 pts  (below baseline → more stress)
      Dry season:       up to 20 pts
    """
    # NDVI component — negative anomaly means stressed vegetation
    ndvi_component = float(np.clip(-ndvi_anomaly * 100, 0, 40))

    # Rainfall component — normalised by baseline so all districts comparable
    if rainfall_baseline > 1.0:
        deficit_pct = float(np.clip(-rainfall_anomaly / rainfall_baseline, 0.0, 1.0))
    else:
        deficit_pct = 0.0
    rainfall_component = deficit_pct * 40.0

    # Dry season bonus
    dry_component = 20.0 if calendar_month in DRY_SEASON_MONTHS else 0.0

    return float(np.clip(ndvi_component + rainfall_component + dry_component, 0.0, 100.0))


def _stress_label(score):
    if score >= STRESS_HIGH:
        return 'HIGH'
    if score >= STRESS_MEDIUM:
        return 'MEDIUM'
    return 'LOW'


def _haversine_km(lat1, lon1, lat2_arr, lon2_arr):
    """Vectorised haversine distance (km) from a point to an array of points."""
    R = 6371.0
    dlat = np.radians(lat2_arr - lat1)
    dlon = np.radians(lon2_arr - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2_arr)) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _get_gbif_monthly_profile(lat, lon, radius_km=80):
    """
    Return sighting counts per calendar month (1-12) for GBIF records
    within radius_km of (lat, lon).
    """
    counts = {m: 0 for m in range(1, 13)}

    if data_loader.tracking_data is None:
        return counts

    df = data_loader.tracking_data.copy()

    # Need lat, lon, and a parsed month
    lat_col = 'latitude' if 'latitude' in df.columns else None
    lon_col = 'longitude' if 'longitude' in df.columns else None
    if lat_col is None or lon_col is None:
        return counts

    df = df.dropna(subset=[lat_col, lon_col])

    # Parse dates to get month
    if 'Date' in df.columns:
        dates = pd.to_datetime(df['Date'], errors='coerce')
    else:
        return counts

    df = df[dates.notna()].copy()
    df['_month'] = pd.to_datetime(df['Date'], errors='coerce').dt.month

    # Vectorised distance filter
    dists = _haversine_km(lat, lon,
                          df[lat_col].to_numpy(dtype=float),
                          df[lon_col].to_numpy(dtype=float))
    nearby = df[dists <= radius_km]

    for m, grp in nearby.groupby('_month'):
        counts[int(m)] = len(grp)

    return counts


def _process_district_stress(args):
    """Worker: compute stress metrics for one district (used in ThreadPoolExecutor)."""
    district_name, coords, year, month = args
    # Use habitat coordinate if available; fall back to administrative centre.
    hab = _HABITAT_COORDS.get(district_name)
    lat, lon = (hab[0], hab[1]) if hab else (coords['lat'], coords['lon'])

    current_ndvi = data_loader.get_ndvi_value(lat, lon, year, month)
    baseline_ndvi = _compute_ndvi_baseline(lat, lon, month)
    ndvi_anomaly = current_ndvi - baseline_ndvi

    grid_lat, grid_lon = _get_nearest_grid_point(lat, lon)
    current_rain = _get_current_rainfall_30day(grid_lat, grid_lon, year, month)
    baseline_rain = _compute_rainfall_baseline(grid_lat, grid_lon, month)
    rainfall_anomaly = current_rain - baseline_rain

    score = _compute_stress_score(ndvi_anomaly, rainfall_anomaly, baseline_rain, month)

    return {
        'district': district_name,
        'lat': lat,
        'lon': lon,
        'current_ndvi': round(float(current_ndvi), 4),
        'baseline_ndvi': round(float(baseline_ndvi), 4),
        'ndvi_anomaly': round(float(ndvi_anomaly), 4),
        'current_rainfall_30day': round(float(current_rain), 2),
        'baseline_rainfall_30day': round(float(baseline_rain), 2),
        'rainfall_anomaly': round(float(rainfall_anomaly), 2),
        'dry_season': month in DRY_SEASON_MONTHS,
        'stress_score': round(score, 1),
        'stress_label': _stress_label(score),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@env_stress_bp.route('/environmental-stress/summary', methods=['GET'])
def get_stress_summary():
    """
    GET /api/environmental-stress/summary?date=YYYY-MM-DD&regenerate=true

    Returns Environmental Stress Score for all 25 districts.
    Cached per year-month (NDVI is monthly so daily granularity adds nothing).
    """
    try:
        date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
        regenerate = request.args.get('regenerate', 'false').lower() == 'true'

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return error_response('Invalid date format. Use YYYY-MM-DD', 400)

        year, month = date_obj.year, date_obj.month

        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(CACHE_DIR, f'summary_{year}_{month:02d}.json')

        if not regenerate and os.path.exists(cache_path):
            with open(cache_path) as f:
                return success_response(json.load(f), 'Environmental stress summary retrieved (cached)')

        # Pre-warm NDVI raster cache for the current month to avoid race condition
        for name, coords in DISTRICTS.items():
            hab = _HABITAT_COORDS.get(name)
            lat_w = hab[0] if hab else coords['lat']
            lon_w = hab[1] if hab else coords['lon']
            data_loader.get_ndvi_value(lat_w, lon_w, year, month)

        args_list = [
            (name, coords, year, month)
            for name, coords in DISTRICTS.items()
        ]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_process_district_stress, args_list))

        results.sort(key=lambda d: d['stress_score'], reverse=True)

        scores = [d['stress_score'] for d in results]
        national_avg = round(float(np.mean(scores)), 1) if scores else 0.0

        payload = {
            'date': date_str,
            'month': month,
            'year': year,
            'districts': results,
            'national_avg_stress': national_avg,
            'most_stressed_district': results[0]['district'] if results else None,
            'least_stressed_district': results[-1]['district'] if results else None,
            'high_stress_count': sum(1 for d in results if d['stress_label'] == 'HIGH'),
            'medium_stress_count': sum(1 for d in results if d['stress_label'] == 'MEDIUM'),
            'low_stress_count': sum(1 for d in results if d['stress_label'] == 'LOW'),
        }

        with open(cache_path, 'w') as f:
            json.dump(payload, f)

        return success_response(payload, 'Environmental stress summary retrieved')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(f'Failed to compute stress summary: {e}', 500)


@env_stress_bp.route('/environmental-stress/seasonal-profile', methods=['GET'])
def get_seasonal_profile():
    """
    GET /api/environmental-stress/seasonal-profile?district=Kandy&regenerate=true

    Returns 12-month ecological profile for a district:
    average NDVI, average rainfall, and GBIF sighting count per calendar month.
    Cached per district (static data; bust with regenerate=true).
    """
    try:
        district = request.args.get('district', '').strip()
        regenerate = request.args.get('regenerate', 'false').lower() == 'true'

        if not district:
            return error_response('district parameter is required', 400)

        if district not in DISTRICTS:
            return error_response(
                f"Unknown district '{district}'. Valid options: {sorted(DISTRICTS.keys())}", 400
            )

        os.makedirs(CACHE_DIR, exist_ok=True)
        safe_name = district.replace(' ', '_')
        cache_path = os.path.join(CACHE_DIR, f'profile_{safe_name}.json')

        if not regenerate and os.path.exists(cache_path):
            with open(cache_path) as f:
                return success_response(json.load(f), 'Seasonal profile retrieved (cached)')

        coords = DISTRICTS[district]
        hab = _HABITAT_COORDS.get(district)
        lat, lon = (hab[0], hab[1]) if hab else (coords['lat'], coords['lon'])
        grid_lat, grid_lon = _get_nearest_grid_point(lat, lon)

        gbif_counts = _get_gbif_monthly_profile(lat, lon)

        profile = []
        all_years = list(BASELINE_YEARS) + [2025]
        for m in range(1, 13):
            ndvi_vals = [data_loader.get_ndvi_value(lat, lon, y, m) for y in all_years]
            ndvi_vals = [v for v in ndvi_vals if v is not None]
            avg_ndvi = round(float(np.mean(ndvi_vals)), 4) if ndvi_vals else 0.4

            rain_vals = []
            for y in all_years:
                r = _get_current_rainfall_30day(grid_lat, grid_lon, y, m)
                if r > 0:
                    rain_vals.append(r)
            avg_rain = round(float(np.mean(rain_vals)), 2) if rain_vals else 0.0

            profile.append({
                'month': m,
                'month_name': MONTH_NAMES[m - 1],
                'avg_ndvi': avg_ndvi,
                'avg_rainfall_30day': avg_rain,
                'gbif_sighting_count': gbif_counts.get(m, 0),
                'is_dry_season': m in DRY_SEASON_MONTHS,
            })

        payload = {
            'district': district,
            'lat': lat,
            'lon': lon,
            'profile': profile,
        }

        with open(cache_path, 'w') as f:
            json.dump(payload, f)

        return success_response(payload, 'Seasonal profile retrieved')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(f'Failed to compute seasonal profile: {e}', 500)


@env_stress_bp.route('/environmental-stress/stress-correlation', methods=['GET'])
def get_stress_correlation():
    """
    GET /api/environmental-stress/stress-correlation

    Returns monthly time series (2020–latest NDVI month):
    national average NDVI anomaly vs. GBIF sighting count.
    Includes Pearson r correlation coefficient.
    Cached; invalidated when new NDVI months become available.
    """
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(CACHE_DIR, 'correlation_cache.json')

        ndvi_month_count = len(data_loader.ndvi_files)

        # Serve cache only if NDVI coverage hasn't expanded
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                cached = json.load(f)
            if cached.get('ndvi_month_count') == ndvi_month_count:
                return success_response(cached, 'Stress correlation retrieved (cached)')

        if not data_loader.ndvi_files:
            return error_response('NDVI data not loaded', 503)

        # Build GBIF lookup: {year: {month: count}} across all Sri Lanka
        gbif_lookup = {}
        if data_loader.tracking_data is not None:
            df = data_loader.tracking_data.copy()
            lat_col = 'latitude' if 'latitude' in df.columns else None
            if lat_col and 'Date' in df.columns:
                df['_date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df[df['_date'].notna()]
                df['_year'] = df['_date'].dt.year
                df['_month'] = df['_date'].dt.month
                for (y, m), grp in df.groupby(['_year', '_month']):
                    gbif_lookup.setdefault(int(y), {})[int(m)] = len(grp)

        # Compute national average NDVI per month key
        district_centres = [(c['lat'], c['lon']) for c in DISTRICTS.values()]

        series = []
        for key in sorted(data_loader.ndvi_files.keys()):
            try:
                year_str, month_str = key.split('-')
                year, month = int(year_str), int(month_str)
            except ValueError:
                continue

            ndvi_vals = [data_loader.get_ndvi_value(lat, lon, year, month)
                         for lat, lon in district_centres]
            ndvi_vals = [v for v in ndvi_vals if v is not None]
            national_ndvi = float(np.mean(ndvi_vals)) if ndvi_vals else 0.4

            # Baseline: same calendar month average across BASELINE_YEARS
            baseline_vals = []
            for by in BASELINE_YEARS:
                bv = [data_loader.get_ndvi_value(lat, lon, by, month)
                      for lat, lon in district_centres]
                bv = [v for v in bv if v is not None]
                if bv:
                    baseline_vals.append(float(np.mean(bv)))
            baseline_ndvi = float(np.mean(baseline_vals)) if baseline_vals else national_ndvi
            ndvi_anomaly = round(national_ndvi - baseline_ndvi, 4)

            gbif_count = gbif_lookup.get(year, {}).get(month, 0)

            series.append({
                'year_month': key,
                'year': year,
                'month': month,
                'national_avg_ndvi': round(national_ndvi, 4),
                'ndvi_anomaly': ndvi_anomaly,
                'gbif_count': gbif_count,
            })

        # Pearson r between NDVI anomaly and GBIF count
        pearson_r = None
        if len(series) >= 3:
            anomalies = np.array([s['ndvi_anomaly'] for s in series])
            counts = np.array([s['gbif_count'] for s in series], dtype=float)
            if anomalies.std() > 0 and counts.std() > 0:
                r = float(np.corrcoef(anomalies, counts)[0, 1])
                pearson_r = None if math.isnan(r) else round(r, 3)

        payload = {
            'series': series,
            'pearson_r': pearson_r,
            'ndvi_month_count': ndvi_month_count,
            'note': (
                'Negative Pearson r indicates vegetation stress (low NDVI) '
                'is associated with more elephant sightings near settlements.'
            ),
        }

        with open(cache_path, 'w') as f:
            json.dump(payload, f)

        return success_response(payload, 'Stress correlation retrieved')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(f'Failed to compute stress correlation: {e}', 500)
