import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent.futures import ThreadPoolExecutor
from data.risk_zones import get_risk_level_for_location
from ml.predictor import predictor

# Sri Lanka districts with representative coordinates
DISTRICTS = {
    'Colombo': {'lat': 6.9271, 'lon': 79.8612},
    'Gampaha': {'lat': 7.0914, 'lon': 80.0155},
    'Kalutara': {'lat': 6.5854, 'lon': 79.9607},
    'Kandy': {'lat': 7.2906, 'lon': 80.6337},
    'Matale': {'lat': 7.4675, 'lon': 80.6234},
    'Nuwara Eliya': {'lat': 6.9497, 'lon': 80.7891},
    'Galle': {'lat': 6.0535, 'lon': 80.2210},
    'Matara': {'lat': 5.9549, 'lon': 80.5550},
    'Hambantota': {'lat': 6.1429, 'lon': 81.1212},
    'Jaffna': {'lat': 9.6615, 'lon': 80.0255},
    'Kilinochchi': {'lat': 9.3958, 'lon': 80.3989},
    'Mannar': {'lat': 8.9810, 'lon': 79.9044},
    'Vavuniya': {'lat': 8.7514, 'lon': 80.4971},
    'Mullaitivu': {'lat': 9.2671, 'lon': 80.8142},
    'Batticaloa': {'lat': 7.7310, 'lon': 81.6747},
    'Ampara': {'lat': 7.2917, 'lon': 81.6747},
    'Trincomalee': {'lat': 8.5874, 'lon': 81.2152},
    'Kurunegala': {'lat': 7.4863, 'lon': 80.3623},
    'Puttalam': {'lat': 8.0362, 'lon': 79.8283},
    'Anuradhapura': {'lat': 8.3114, 'lon': 80.4037},
    'Polonnaruwa': {'lat': 7.9403, 'lon': 81.0188},
    'Badulla': {'lat': 6.9934, 'lon': 81.0550},
    'Monaragala': {'lat': 6.8728, 'lon': 81.3507},
    'Ratnapura': {'lat': 6.7056, 'lon': 80.3847},
    'Kegalle': {'lat': 7.2513, 'lon': 80.3464}
}


def get_district_risk_levels(date):
    """Get risk level for each district on the given date.

    Uses the trained ML predictor so that risk varies with season, rainfall,
    NDVI, etc. Falls back to the static geographic zone lookup if a
    prediction fails for a district.

    Districts are predicted in parallel because each is independent and the
    bottleneck is I/O (shapefile distance queries, raster reads) that releases
    the GIL, so threads give a real speedup.
    """
    def _predict_one(item):
        district_name, coords = item
        result = predictor.predict(coords['lat'], coords['lon'], date)

        if result is None:
            fallback = get_risk_level_for_location(coords['lat'], coords['lon'])
            return {
                'district': district_name,
                'risk_level': fallback['risk_level'],
                'risk_score': fallback['risk_score'],
                'zone_name': fallback['zone_name'],
                'coordinates': coords
            }

        return {
            'district': district_name,
            'risk_level': result['risk_level'],
            'risk_score': round(float(result['risk_score']), 3),
            'zone_name': district_name,
            'coordinates': coords
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        district_risks = list(pool.map(_predict_one, DISTRICTS.items()))

    return district_risks