import json
import os
import geopandas as gpd
from shapely.geometry import shape
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CityLoader:
    """Load and manage city/division level data from GADM"""

    def __init__(self, geojson_path, cache_path):
        self.geojson_path = geojson_path
        self.cache_path = cache_path
        self.cities_gdf = None
        self.district_cities_map = {}
        self.city_lookup = {}

    def load_cities(self, use_cache=True):
        """Load city data from GeoJSON or cache"""
        # Try loading from cache first
        if use_cache and os.path.exists(self.cache_path):
            print("Loading city data from cache...")
            return self._load_from_cache()

        # Load from GeoJSON
        print("Loading city data from GADM GeoJSON...")
        if not os.path.exists(self.geojson_path):
            print(f"⚠ GADM GeoJSON not found at {self.geojson_path}")
            return False

        try:
            # Load GeoJSON
            self.cities_gdf = gpd.read_file(self.geojson_path)

            # Ensure WGS84 CRS
            if self.cities_gdf.crs != "EPSG:4326":
                self.cities_gdf = self.cities_gdf.to_crs("EPSG:4326")

            print(f"✓ Loaded {len(self.cities_gdf)} cities/divisions")

            # Build mappings
            self._build_mappings()

            # Save to cache
            self._save_to_cache()

            return True

        except Exception as e:
            print(f"⚠ Error loading GADM data: {e}")
            return False

    def _build_mappings(self):
        """Build district-to-cities mapping and city lookup"""
        print("Building city mappings...")

        for idx, row in self.cities_gdf.iterrows():
            district = row['NAME_1']  # District name
            city = row['NAME_2']  # City/division name
            gid = row['GID_2']  # Unique ID

            # Calculate centroid
            centroid = row['geometry'].centroid
            center_lat = centroid.y
            center_lng = centroid.x

            city_data = {
                'name': city,
                'district': district,
                'gid': gid,
                'center_lat': center_lat,
                'center_lng': center_lng
            }

            # Add to district mapping
            if district not in self.district_cities_map:
                self.district_cities_map[district] = []
            self.district_cities_map[district].append(city_data)

            # Add to city lookup
            self.city_lookup[gid] = city_data

        print(f"✓ Mapped {len(self.district_cities_map)} districts")
        print(f"✓ Created lookup for {len(self.city_lookup)} cities")

    def get_cities_by_district(self, district):
        """Get all cities in a district"""
        return self.district_cities_map.get(district, [])

    def get_city_by_gid(self, gid):
        """Get city data by GID"""
        return self.city_lookup.get(gid)

    def get_city_geometry(self, gid):
        """Get city geometry (polygon) for map rendering"""
        if self.cities_gdf is None:
            return None

        city_row = self.cities_gdf[self.cities_gdf['GID_2'] == gid]
        if len(city_row) == 0:
            return None

        return city_row.iloc[0]['geometry']

    def get_city_center(self, district, city_name):
        """Get center coordinates for a city by name"""
        cities = self.get_cities_by_district(district)
        for city in cities:
            if city['name'] == city_name:
                return city['center_lat'], city['center_lng']
        return None, None

    def get_all_districts(self):
        """Get list of all districts"""
        return sorted(list(self.district_cities_map.keys()))

    def _save_to_cache(self):
        """Save processed data to cache"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)

            cache_data = {
                'district_cities_map': self.district_cities_map,
                'city_lookup': self.city_lookup
            }

            with open(self.cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)

            print(f"✓ City data cached to {self.cache_path}")

        except Exception as e:
            print(f"⚠ Failed to cache city data: {e}")

    def _load_from_cache(self):
        """Load processed data from cache"""
        try:
            with open(self.cache_path, 'r') as f:
                cache_data = json.load(f)

            self.district_cities_map = cache_data['district_cities_map']
            self.city_lookup = cache_data['city_lookup']

            print(f"✓ Loaded {len(self.district_cities_map)} districts from cache")
            print(f"✓ Loaded {len(self.city_lookup)} cities from cache")

            # Also load GeoJSON for geometry queries
            if os.path.exists(self.geojson_path):
                self.cities_gdf = gpd.read_file(self.geojson_path)
                if self.cities_gdf.crs != "EPSG:4326":
                    self.cities_gdf = self.cities_gdf.to_crs("EPSG:4326")

            return True

        except Exception as e:
            print(f"⚠ Failed to load from cache: {e}")
            return False


# Test
if __name__ == '__main__':
    from  config import GADM_GEOJSON_PATH, CITY_CACHE_PATH

    print("=" * 60)
    print("Testing City Loader")
    print("=" * 60 + "\n")

    loader = CityLoader(GADM_GEOJSON_PATH, CITY_CACHE_PATH)
    loader.load_cities(use_cache=False)

    # Test: Get cities in Monaragala
    print("\nCities in Monaragala:")
    monaragala_cities = loader.get_cities_by_district('Monaragala')
    for city in monaragala_cities[:5]:
        print(f"  - {city['name']}: ({city['center_lat']:.4f}, {city['center_lng']:.4f})")

    # Test: Get all districts
    print("\nAll districts:")
    districts = loader.get_all_districts()
    print(f"  Total: {len(districts)} districts")
    print(f"  Sample: {districts[:5]}")

    print("\n" + "=" * 60)
    print("City Loader Test Complete!")
    print("=" * 60)