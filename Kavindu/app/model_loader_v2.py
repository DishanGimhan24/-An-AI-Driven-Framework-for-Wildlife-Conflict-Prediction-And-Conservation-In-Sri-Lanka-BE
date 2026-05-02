"""
services/model_loader_v2.py — FINAL FIXED VERSION
Matches actual Colab v3 notebook metadata.json structure exactly.
"""

import os, json, joblib
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models_v2")
_models = {}
_meta   = {}

def load_all_models():
    global _models, _meta

    _models["xgb_risk"]       = joblib.load(os.path.join(MODELS_DIR, "xgb_risk_model.pkl"))
    _models["xgb_offence"]    = joblib.load(os.path.join(MODELS_DIR, "xgb_offence_model.pkl"))
    _models["xgb_multilabel"] = joblib.load(os.path.join(MODELS_DIR, "xgb_multilabel_model.pkl"))
    _models["le_region"]      = joblib.load(os.path.join(MODELS_DIR, "le_region.pkl"))
    _models["le_grouped"]     = joblib.load(os.path.join(MODELS_DIR, "le_grouped.pkl"))
    _models["le_season"]      = joblib.load(os.path.join(MODELS_DIR, "le_season.pkl"))
    _models["mlb"]            = joblib.load(os.path.join(MODELS_DIR, "mlb.pkl"))

    with open(os.path.join(MODELS_DIR, "metadata.json")) as f:
        _meta = json.load(f)

    # ── Normalise key names ────────────────────────────────────────────────────
    # features
    if "features" not in _meta:
        _meta["features"] = _meta.get("features_full", [])

    # offence_types (6-class grouped list)
    if "offence_types" not in _meta:
        _meta["offence_types"] = (
            _meta.get("offence_types_grouped") or
            _meta.get("offence_groups") or []
        )

    # seasons — read from the fitted LabelEncoder
    if "seasons" not in _meta:
        try:
            _meta["seasons"] = _models["le_season"].classes_.tolist()
        except Exception:
            _meta["seasons"] = ["Maha", "Transition", "Yala"]

    # accuracy aliases
    if "offence_f1_multi" not in _meta:
        _meta["offence_f1_multi"] = _meta.get("multilabel_f1_samples", 0.0)
    if "offence_accuracy_single" not in _meta:
        _meta["offence_accuracy_single"] = _meta.get("offence_accuracy_6cls", 0.0)

    print(f"✅  Models loaded — {len(_meta.get('regions', []))} regions, "
          f"risk acc {_meta.get('risk_accuracy', 0)*100:.1f}%")


def get_model(name): return _models[name]
def get_meta():      return _meta

MONTH_LABELS = {
    1:"January",  2:"February", 3:"March",    4:"April",
    5:"May",      6:"June",     7:"July",      8:"August",
    9:"September",10:"October", 11:"November", 12:"December"
}

def get_season(m): return "Yala" if m in [5,6,7,8,9] else "Maha"

def get_hist_count(region, month_num):
    for e in _meta.get("hist_region_month", []):
        if e.get("region") == region and e.get("month_num") == month_num:
            return float(e.get("hist_region_month_count", 5.0))
    entries = [e for e in _meta.get("hist_region_month", [])
               if e.get("region") == region]
    return float(np.mean([e.get("hist_region_month_count", 5)
                          for e in entries])) if entries else 5.0

def get_rainfall(region, month_num):
    for e in _meta.get("rainfall_lookup", []):
        if e.get("region") == region and e.get("month_num") == month_num:
            return float(e.get("rainfall_mm", 150))
    return float(_meta.get("sl_monthly_rainfall", {}).get(str(month_num), 150))

def get_hotspot_rank(region):
    spots = _meta.get("hotspots", [])
    for i, h in enumerate(spots):
        if h["region"] == region:
            rank = int(h.get("hotspot_rank", i + 1))
            return rank, rank / max(len(spots), 1)
    return 7, 0.5

def get_region_risk_rate(region):
    entries = [e for e in _meta.get("hist_region_month", [])
               if e.get("region") == region]
    return 0.25 if not entries else min(1.0, len(entries) / 36)

def get_hist_pct(region):
    """
    Return the 6 hist_pct_* feature values in the exact order the model
    was trained with:
      hist_pct_poaching, hist_pct_illegal_trade, hist_pct_weapons_and_tools,
      hist_pct_land_encroachment, hist_pct_resource_extraction, hist_pct_other
    We approximate from the region_offence_map and offence_merge_map.
    """
    PCT_COLS = [
        "hist_pct_poaching",
        "hist_pct_illegal_trade",
        "hist_pct_weapons_and_tools",
        "hist_pct_land_encroachment",
        "hist_pct_resource_extraction",
        "hist_pct_other",
    ]
    GROUP_MAP = {
        "hist_pct_poaching":          "Poaching",
        "hist_pct_illegal_trade":     "Illegal Trade",
        "hist_pct_weapons_and_tools": "Weapons & Tools",
        "hist_pct_land_encroachment": "Land Encroachment",
        "hist_pct_resource_extraction":"Resource Extraction",
        "hist_pct_other":             "Other",
    }

    dist  = _meta.get("offence_distribution", {})
    if isinstance(dist, list):
        dist = {v: 1 for v in dist}
    merge = _meta.get("offence_merge_map", {})
    total = sum(dist.values()) or 1

    group_counts = {g: 0 for g in GROUP_MAP.values()}
    for raw, cnt in dist.items():
        g = merge.get(raw, "Other")
        if g in group_counts:
            group_counts[g] += cnt

    dom_raw = _meta.get("region_offence_map", {}).get(region, "Other")
    dom_grp = merge.get(dom_raw, "Other")

    result = []
    for col in PCT_COLS:
        grp       = GROUP_MAP[col]
        base_rate = group_counts[grp] / total
        boost     = 0.3 if grp == dom_grp else 0.0
        result.append(min(1.0, base_rate + boost))
    return result  # exactly 6 values


def build_feature_vector(region, month_num, recent_offences=0,
                          rainfall_override=None):
    """
    Build exactly 35 features in the same order the model was trained with.
    """
    season   = get_season(month_num)
    is_dry   = 1 if season == "Yala" else 0
    quarter  = (month_num - 1) // 3 + 1
    m_sin    = float(np.sin(2 * np.pi * month_num / 12))
    m_cos    = float(np.cos(2 * np.pi * month_num / 12))

    hist     = get_hist_count(region, month_num)
    adj      = (hist + recent_offences) / 2
    same_ly  = hist * 0.9
    rolling3 = adj
    rolling6 = adj
    trend    = (1 if recent_offences > rolling3
                else (-1 if recent_offences < rolling3 * 0.7 else 0))

    h_rank, h_norm = get_hotspot_rank(region)
    r_risk         = get_region_risk_rate(region)

    rain_mm  = (rainfall_override if rainfall_override is not None
                else get_rainfall(region, month_num))
    rain_entries    = [float(e.get("rainfall_mm", 150))
                       for e in _meta.get("rainfall_lookup", [])
                       if e.get("region") == region]
    avg_rain        = float(np.mean(rain_entries)) if rain_entries else 150.0
    is_drought      = 1 if rain_mm < avg_rain * 0.6 else 0
    rain_vs_avg     = rain_mm - avg_rain

    le_r = get_model("le_region")
    le_s = get_model("le_season")

    festival = int(_meta.get("festival_months", {}).get(str(month_num), 0))
    school   = int(_meta.get("school_holidays",  {}).get(str(month_num), 0))
    tourist  = int(_meta.get("tourist_peak",     {}).get(str(month_num), 0))
    harvest  = int(_meta.get("harvest_months",   {}).get(str(month_num), 0))
    dry_harv = is_dry * harvest

    hist_pcts = get_hist_pct(region)  # exactly 6 values

    feat = [
        # [0-3] location
        le_r.transform([region])[0],
        h_rank, h_norm, r_risk,
        # [4-7] time
        m_sin, m_cos, quarter, 2,
        # [8-9] season
        is_dry, le_s.transform([season])[0],
        # [10] historical average
        adj,
        # [11-13] lag
        recent_offences, max(0, recent_offences - 2), same_ly,
        # [14-16] rolling / trend
        rolling3, rolling6, trend,
        # [17-19] offence-type lags (unknown at API time → 0)
        0.0, 0.0, 0.0,
        # [20] diversity proxy
        max(1, recent_offences),
        # [21-23] weather
        rain_mm, is_drought, rain_vs_avg,
        # [24-28] calendar
        festival, school, tourist, harvest, dry_harv,
        # [29-34] hist_pct features (6 values)
        *hist_pcts,
    ]

    assert len(feat) == 35, f"Feature count error: expected 35, got {len(feat)}"
    return np.array([feat])
