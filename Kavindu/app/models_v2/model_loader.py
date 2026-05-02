"""
services/model_loader.py  — FIXED VERSION
Key names corrected to match actual Colab v3 notebook metadata.json output.
"""

import os, json, joblib
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
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

    # Normalise key names
    if "features" not in _meta and "features_full" in _meta:
        _meta["features"] = _meta["features_full"]
    if "offence_types" not in _meta:
        _meta["offence_types"] = (
            _meta.get("offence_types_grouped") or
            _meta.get("offence_groups") or []
        )
    if "seasons" not in _meta:
        try:
            _meta["seasons"] = _models["le_season"].classes_.tolist()
        except Exception:
            _meta["seasons"] = ["Maha", "Transition", "Yala"]
    if "offence_f1_multi" not in _meta:
        _meta["offence_f1_multi"] = _meta.get("multilabel_f1_samples", 0.0)
    if "offence_accuracy_single" not in _meta:
        _meta["offence_accuracy_single"] = _meta.get("offence_accuracy_6cls", 0.0)

    print(f"Models loaded OK — {len(_meta.get('regions',[]))} regions, "
          f"risk acc {_meta.get('risk_accuracy',0)*100:.1f}%")

def get_model(name): return _models[name]
def get_meta():      return _meta

MONTH_LABELS = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
    7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}

def get_season(m): return "Yala" if m in [5,6,7,8,9] else "Maha"

def get_hist_count(region, month_num):
    for e in _meta.get("hist_region_month",[]):
        if e.get("region")==region and e.get("month_num")==month_num:
            return float(e.get("hist_region_month_count",5.0))
    entries=[e for e in _meta.get("hist_region_month",[]) if e.get("region")==region]
    return float(np.mean([e.get("hist_region_month_count",5) for e in entries])) if entries else 5.0

def get_rainfall(region, month_num):
    for e in _meta.get("rainfall_lookup",[]):
        if e.get("region")==region and e.get("month_num")==month_num:
            return float(e.get("rainfall_mm",150))
    return float(_meta.get("sl_monthly_rainfall",{}).get(str(month_num),150))

def get_hotspot_rank(region):
    spots=_meta.get("hotspots",[])
    for i,h in enumerate(spots):
        if h["region"]==region: return i+1,(i+1)/max(len(spots),1)
    return 7,0.5

def get_region_risk_rate(region):
    entries=[e for e in _meta.get("hist_region_month",[]) if e.get("region")==region]
    return 0.25 if not entries else min(1.0,len(entries)/36)

def get_hist_pct_cols(region):
    groups=_meta.get("offence_groups",["Poaching","Illegal Trade","Weapons & Tools",
                                        "Land Encroachment","Resource Extraction","Other"])
    dist=_meta.get("offence_distribution",{})
    if isinstance(dist,list): dist={v:1 for v in dist}
    merge=_meta.get("offence_merge_map",{})
    total=sum(dist.values()) or 1
    gc={g:0 for g in groups}
    for raw,cnt in dist.items():
        g=merge.get(raw,"Other")
        if g in gc: gc[g]+=cnt
    dom=merge.get(_meta.get("region_offence_map",{}).get(region,"Other"),"Other")
    return [min(1.0, gc[g]/total + (0.3 if g==dom else 0.0)) for g in groups]

def build_feature_vector(region, month_num, recent_offences=0, rainfall_override=None):
    season=get_season(month_num)
    is_dry=1 if season=="Yala" else 0
    quarter=(month_num-1)//3+1
    m_sin=float(np.sin(2*np.pi*month_num/12))
    m_cos=float(np.cos(2*np.pi*month_num/12))
    hist=get_hist_count(region,month_num)
    adj=( hist+recent_offences)/2
    same_ly=hist*0.9
    h_rank,h_norm=get_hotspot_rank(region)
    r_risk=get_region_risk_rate(region)
    rain=rainfall_override if rainfall_override is not None else get_rainfall(region,month_num)
    re=[float(e.get("rainfall_mm",150)) for e in _meta.get("rainfall_lookup",[]) if e.get("region")==region]
    avg_rain=float(np.mean(re)) if re else 150.0
    is_dr=1 if rain<avg_rain*0.6 else 0
    rva=rain-avg_rain
    le_r=get_model("le_region")
    le_s=get_model("le_season")
    festival=_meta.get("festival_months",{}).get(str(month_num),0)
    school=_meta.get("school_holidays",{}).get(str(month_num),0)
    tourist=_meta.get("tourist_peak",{}).get(str(month_num),0)
    harvest=_meta.get("harvest_months",{}).get(str(month_num),0)
    dry_harv=is_dry*harvest
    hp=get_hist_pct_cols(region)
    feat=[
        le_r.transform([region])[0], h_rank, h_norm, r_risk,
        m_sin, m_cos, quarter, 2,
        is_dry, le_s.transform([season])[0],
        adj,
        recent_offences, max(0,recent_offences-2), same_ly, adj, adj,
        1 if recent_offences>adj else (-1 if recent_offences<adj*0.7 else 0),
        0.0, 0.0, 0.0,
        max(1,recent_offences),
        rain, is_dr, rva,
        festival, school, tourist, harvest, dry_harv,
        *hp,
        0, hist, *hp[:5],
    ]
    return np.array([feat])
