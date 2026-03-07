import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
from config import POPULATION_DIR
from data_processing.data_loader import data_loader
from data_processing.spatial_utils import (
    calculate_distance_to_nearest,
    point_in_polygon,
    calculate_buffer_zone,
    get_density_at_point
)

class FeatureExtractor:
    """Extract features for ML model from location and date"""

    def __init__(self):
        self.data_loader = data_loader

    def extract_features(self, latitude, longitude, date_str):
        """
        Extract all features for a given location and date
        Returns: dict of features
        """
        features = {}

        # Basic features
        features['latitude'] = latitude
        features['longitude'] = longitude

        # Date features
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        features['month'] = date_obj.month
        features['day_of_year'] = date_obj.timetuple().tm_yday
        features['week_of_year'] = date_obj.isocalendar()[1]
        features['season'] = self._get_season(date_obj.month)

        # Spatial features
        features.update(self._extract_spatial_features(latitude, longitude))

        # Environmental features (rainfall, NDVI)
        features.update(self._extract_environmental_features(latitude, longitude, date_obj))

        return features

    def _get_season(self, month):
        """
        Get season for Sri Lanka
        Dry season: May-September (5-9)
        Wet season: October-April (10-4)
        """
        if 5 <= month <= 9:
            return 1  # Dry
        else:
            return 0  # Wet

    def _extract_spatial_features(self, lat, lon):
        """Extract spatial features from shapefiles"""
        features = {}

        # Distance to protected areas
        if self.data_loader.protected_areas is not None and len(self.data_loader.protected_areas) > 0:
            features['dist_to_protected_area_km'] = calculate_distance_to_nearest(
                lat, lon, self.data_loader.protected_areas
            )
            features['in_protected_area'] = point_in_polygon(
                lat, lon, self.data_loader.protected_areas
            )
            features['buffer_zone'] = calculate_buffer_zone(
                lat, lon, self.data_loader.protected_areas, buffer_km=5
            )
        else:
            features['dist_to_protected_area_km'] = 50.0  # Default: far from protected areas
            features['in_protected_area'] = 0
            features['buffer_zone'] = 0

        # Distance to roads
        if self.data_loader.roads is not None:
            features['dist_to_road_km'] = calculate_distance_to_nearest(
                lat, lon, self.data_loader.roads
            )
            features['near_road'] = 1 if features['dist_to_road_km'] < 2 else 0
        else:
            features['dist_to_road_km'] = 999.0
            features['near_road'] = 0

        # Distance to railways
        if self.data_loader.railways is not None:
            features['dist_to_railway_km'] = calculate_distance_to_nearest(
                lat, lon, self.data_loader.railways
            )
            features['near_railway'] = 1 if features['dist_to_railway_km'] < 2 else 0
        else:
            features['dist_to_railway_km'] = 999.0
            features['near_railway'] = 0

        # Distance to electric fences
        if self.data_loader.power_fences is not None:
            features['dist_to_fence_km'] = calculate_distance_to_nearest(
                lat, lon, self.data_loader.power_fences
            )
            features['near_fence'] = 1 if features['dist_to_fence_km'] < 1 else 0
        else:
            features['dist_to_fence_km'] = 999.0
            features['near_fence'] = 0

        # Elephant distribution zone
        if self.data_loader.elephant_distribution is not None:
            features['in_elephant_zone'] = point_in_polygon(
                lat, lon, self.data_loader.elephant_distribution
            )
        else:
            features['in_elephant_zone'] = 0

        # Population density
        population_raster = os.path.join(POPULATION_DIR, 'lka_pd_2020_1km.tif')
        if os.path.exists(population_raster):
            features['population_density'] = get_density_at_point(lat, lon, population_raster)
            features['high_human_presence'] = 1 if features['population_density'] > 100 else 0
        else:
            features['population_density'] = 0.0
            features['high_human_presence'] = 0

        # Interaction features
        features['road_railway_proximity'] = min(
            features['dist_to_road_km'],
            features['dist_to_railway_km']
        )
        features['human_infrastructure_risk'] = (
                features['high_human_presence'] * (1 if features['near_road'] or features['near_railway'] else 0)
        )

        return features

    def _extract_environmental_features(self, lat, lon, date_obj):
        """Extract environmental features (rainfall, NDVI)"""
        features = {}

        # Rainfall features from actual data
        rainfall_info = self.data_loader.get_rainfall_for_date(date_obj, days_back=30)
        features['rainfall_7day'] = rainfall_info['rainfall_7day']
        features['rainfall_14day'] = rainfall_info['rainfall_14day']
        features['rainfall_30day'] = rainfall_info['rainfall_30day']
        features['is_dry_period'] = rainfall_info['is_dry_period']

        # Calculate days since significant rain
        features['days_since_rain'] = self._calculate_days_since_rain(date_obj)

        # NDVI features from actual raster files
        year = date_obj.year
        month = date_obj.month

        # Current month NDVI
        features['ndvi_current'] = self.data_loader.get_ndvi_value(lat, lon, year, month)

        # Previous month NDVI (for trend)
        prev_date = date_obj - timedelta(days=30)
        features['ndvi_previous_month'] = self.data_loader.get_ndvi_value(
            lat, lon, prev_date.year, prev_date.month
        )

        # Vegetation change indicator
        features['vegetation_decreasing'] = 1 if features['ndvi_current'] < features['ndvi_previous_month'] else 0
        features['ndvi_change'] = features['ndvi_current'] - features['ndvi_previous_month']

        # Low vegetation indicator
        features['low_vegetation'] = 1 if features['ndvi_current'] < 0.3 else 0

        # Interaction: dry season + low vegetation = high risk
        features['dry_low_veg_risk'] = features['is_dry_period'] * features['low_vegetation']

        # Interaction: rainfall trend with season (calculate season here)
        season = self._get_season(month)
        features['rainfall_season_interaction'] = features['rainfall_7day'] * (1 if season == 0 else 0.5)

        return features

    def _calculate_days_since_rain(self, target_date):
        """Calculate days since last significant rainfall"""
        if self.data_loader.rainfall_data is None or len(self.data_loader.rainfall_data) == 0:
            return 30  # Default assumption

        df = self.data_loader.rainfall_data
        target_date = pd.to_datetime(target_date)

        # Filter dates before target
        past_data = df[df['date'] < target_date].sort_values('date', ascending=False)

        if len(past_data) == 0:
            return 30

        # Find last day with > 5mm rainfall
        significant_rain = past_data[past_data['rainfall_mm'] > 5.0]

        if len(significant_rain) == 0:
            return 30

        last_rain_date = significant_rain.iloc[0]['date']
        days_since = (target_date - last_rain_date).days

        return min(days_since, 60)  # Cap at 60 days

    def get_feature_names(self):
        """Return list of all feature names in order"""
        return [
            'latitude', 'longitude',
            'month', 'day_of_year', 'week_of_year', 'season',
            'dist_to_protected_area_km', 'in_protected_area', 'buffer_zone',
            'dist_to_road_km', 'near_road',
            'dist_to_railway_km', 'near_railway',
            'dist_to_fence_km', 'near_fence',
            'in_elephant_zone',
            'population_density', 'high_human_presence',
            'road_railway_proximity', 'human_infrastructure_risk',
            'rainfall_7day', 'rainfall_14day', 'rainfall_30day',
            'is_dry_period', 'days_since_rain',
            'ndvi_current', 'ndvi_previous_month', 'vegetation_decreasing',
            'ndvi_change', 'low_vegetation',
            'dry_low_veg_risk', 'rainfall_season_interaction'
        ]


# Global feature extractor instance
feature_extractor = FeatureExtractor()

# Test if run directly
if __name__ == '__main__':
    import pandas as pd

    print("=" * 60)
    print("Testing Feature Extractor")
    print("=" * 60 + "\n")

    # Load data first
    print("Loading datasets...")
    data_loader.load_all()

    # Test feature extraction
    print("\n" + "=" * 60)
    print("Extracting features for test location")
    print("=" * 60 + "\n")

    test_lat, test_lon = 7.5, 80.5
    test_date = "2024-06-15"

    features = feature_extractor.extract_features(test_lat, test_lon, test_date)

    print(f"Location: ({test_lat}, {test_lon})")
    print(f"Date: {test_date}\n")
    print("Features extracted:")
    for key, value in features.items():
        print(f"  {key:35s}: {value}")

    print(f"\n✓ Total features: {len(features)}")

    print("\n" + "=" * 60)
    print("Feature Extractor Test Complete!")
    print("=" * 60)