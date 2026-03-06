import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geopandas as gpd
import pandas as pd
import rasterio
import numpy as np
from datetime import datetime
from config import (
    ELEPHANT_DISTRIBUTION_DIR,
    PROTECTED_AREAS_DIR,
    POWER_FENCE_DIR,
    ROAD_RAILWAY_DIR,
    POPULATION_DIR,
    RAINFALL_DIR,
    NDVI_DIR,
    ELEPHANT_TRACKING_DIR
)
from data_processing.city_loader import CityLoader
from config import GADM_GEOJSON_PATH, CITY_CACHE_PATH


class DataLoader:
    """Load and cache all datasets"""

    def __init__(self):
        self.elephant_distribution = None
        self.protected_areas = None
        self.power_fences = None
        self.roads = None
        self.railways = None
        self.rainfall_data = None
        self.ndvi_files = {}  # Store NDVI file paths by year-month
        self.tracking_data = None
        self.city_loader = CityLoader(GADM_GEOJSON_PATH, CITY_CACHE_PATH)

    def load_all(self):

        # Load shapefiles
        self.load_elephant_distribution()
        self.load_protected_areas()
        self.load_power_fences()
        self.load_roads_railways()

        self.load_cities()

        # Load CSV/raster data
        self.load_rainfall_data()
        self.load_ndvi_files()
        self.load_tracking_data()

    def load_elephant_distribution(self):
        """Load elephant distribution shapefile"""
        shapefile_path = os.path.join(ELEPHANT_DISTRIBUTION_DIR, 'Survey-ElephantDistribution.shp')
        if os.path.exists(shapefile_path):
            try:
                self.elephant_distribution = gpd.read_file(shapefile_path)
                # Standardize CRS to WGS84
                if self.elephant_distribution.crs != "EPSG:4326":
                    self.elephant_distribution = self.elephant_distribution.to_crs("EPSG:4326")
            except Exception as e:
                print(f"⚠ Error loading elephant distribution: {e}")
        else:
            print(f"⚠ Elephant distribution shapefile not found at {shapefile_path}")

    def load_protected_areas(self):
        """Load protected areas shapefiles"""
        # Try multiple possible shapefile names
        possible_files = [
            'WDPA_WDOECM_Dec2025_Public_LKA_shp.shp',
            'WDPA_WDOECM_Dec2025_Public_LKA_shp_0.shp',
            'WDPA_WDOECM_Dec2025_Public_LKA_shp_1.shp',
            'WDPA_WDOECM_Dec2025_Public_LKA_shp_2.shp'
        ]

        # Look in Resources_in_English subfolder
        search_dir = os.path.join(PROTECTED_AREAS_DIR, 'Resources_in_English')

        if not os.path.exists(search_dir):
            search_dir = PROTECTED_AREAS_DIR

        for filename in possible_files:
            shapefile_path = os.path.join(search_dir, filename)
            if os.path.exists(shapefile_path):
                try:
                    self.protected_areas = gpd.read_file(shapefile_path)
                    # Standardize CRS to WGS84
                    if self.protected_areas.crs != "EPSG:4326":
                        self.protected_areas = self.protected_areas.to_crs("EPSG:4326")
                    return
                except Exception as e:
                    print(f"⚠ Error loading {filename}: {e}")

        print(f"Protected areas shapefile not found in {search_dir}")

    def load_power_fences(self):
        """Load power fence shapefiles from all provinces"""
        fence_gdfs = []

        if not os.path.exists(POWER_FENCE_DIR):
            print(f"Power fence directory not found")
            return

        # Load all province folders
        for province_folder in os.listdir(POWER_FENCE_DIR):
            province_path = os.path.join(POWER_FENCE_DIR, province_folder)

            if not os.path.isdir(province_path):
                continue

            # Find .shp files
            for file in os.listdir(province_path):
                if file.endswith('.shp'):
                    shapefile_path = os.path.join(province_path, file)
                    try:
                        gdf = gpd.read_file(shapefile_path)
                        # Convert to WGS84 before appending
                        if gdf.crs is None:
                            gdf = gdf.set_crs("EPSG:4326")
                        elif gdf.crs != "EPSG:4326":
                            gdf = gdf.to_crs("EPSG:4326")

                        fence_gdfs.append(gdf)
                    except Exception as e:
                        print(f"  ⚠ Error loading {file}: {e}")

        if fence_gdfs:
            # Now all have same CRS, safe to concatenate
            self.power_fences = gpd.GeoDataFrame(
                pd.concat(fence_gdfs, ignore_index=True),
                crs="EPSG:4326"
            )
        else:
            print(f"⚠ No power fence data loaded")

    def load_roads_railways(self):
        """Load road and railway shapefiles"""
        # Load roads
        roads_path = os.path.join(ROAD_RAILWAY_DIR, 'gis_osm_roads_free_1.shp')
        if os.path.exists(roads_path):
            try:
                self.roads = gpd.read_file(roads_path)
                # Standardize CRS to WGS84
                if self.roads.crs != "EPSG:4326":
                    self.roads = self.roads.to_crs("EPSG:4326")
            except Exception as e:
                print(f"⚠ Error loading roads: {e}")
        else:
            print(f"⚠ Roads shapefile not found")

        # Load railways
        railways_path = os.path.join(ROAD_RAILWAY_DIR, 'gis_osm_railways_free_1.shp')
        if os.path.exists(railways_path):
            try:
                self.railways = gpd.read_file(railways_path)
                # Standardize CRS to WGS84
                if self.railways.crs != "EPSG:4326":
                    self.railways = self.railways.to_crs("EPSG:4326")
            except Exception as e:
                print(f"⚠ Error loading railways: {e}")
        else:
            print(f"⚠ Railways shapefile not found")

    def load_rainfall_data(self):
        """Load and merge all rainfall CSV files (2020-2025) - NASA POWER format"""
        if not os.path.exists(RAINFALL_DIR):
            print(f"⚠ Rainfall directory not found")
            return

        csv_files = [f for f in os.listdir(RAINFALL_DIR) if f.endswith('.csv')]

        if not csv_files:
            print(f"⚠ No rainfall CSV files found")
            return

        dfs = []
        for csv_file in sorted(csv_files):
            csv_path = os.path.join(RAINFALL_DIR, csv_file)
            try:
                # Read entire file to find where data starts
                with open(csv_path, 'r') as f:
                    lines = f.readlines()

                # Find line with actual column headers (contains LAT,LON,YEAR)
                header_line = 0
                for i, line in enumerate(lines):
                    if 'LAT' in line and 'LON' in line and 'YEAR' in line:
                        header_line = i
                        break

                # Read CSV from header line onwards
                df = pd.read_csv(csv_path, skiprows=header_line)

                # NASA POWER format has: LAT, LON, YEAR, DOY, PRECTOTCORR
                if 'YEAR' in df.columns and 'DOY' in df.columns:
                    # Convert YEAR + DOY to actual date
                    df['date'] = pd.to_datetime(
                        df['YEAR'].astype(int).astype(str) + '-' + df['DOY'].astype(int).astype(str),
                        format='%Y-%j',
                        errors='coerce'
                    )
                else:
                    continue

                # Rainfall column
                if 'PRECTOTCORR' in df.columns:
                    df['rainfall_mm'] = pd.to_numeric(df['PRECTOTCORR'], errors='coerce')
                    # Replace -999 (missing data) with 0
                    df.loc[df['rainfall_mm'] == -999, 'rainfall_mm'] = 0.0
                    df.loc[df['rainfall_mm'] < 0, 'rainfall_mm'] = 0.0  # Remove any negative values
                else:
                    print(f"  ⚠ {csv_file} missing PRECTOTCORR column")
                    continue

                # Remove rows with invalid dates
                df = df.dropna(subset=['date'])

                # Keep LAT, LON for reference
                if 'LAT' in df.columns and 'LON' in df.columns:
                    df = df[['date', 'LAT', 'LON', 'rainfall_mm']]
                else:
                    df = df[['date', 'rainfall_mm']]

                dfs.append(df)
            except Exception as e:
                print(f"  ⚠ Error loading {csv_file}: {e}")
                import traceback
                traceback.print_exc()

        if dfs:
            all_data = pd.concat(dfs, ignore_index=True)

            # Aggregate by date (average across all grid points for Sri Lanka)
            self.rainfall_data = all_data.groupby('date', as_index=False).agg({
                'rainfall_mm': 'mean'  # Average rainfall across all locations
            })

            self.rainfall_data = self.rainfall_data.sort_values('date').reset_index(drop=True)
        else:
            print(f"⚠ No rainfall data loaded")

    def load_ndvi_files(self):
        """Map NDVI .tif files by year-month for quick access"""
        if not os.path.exists(NDVI_DIR):
            print(f"⚠ NDVI directory not found")
            return

        tif_files = [f for f in os.listdir(NDVI_DIR) if f.endswith('.tif')]

        if not tif_files:
            print(f"⚠ No NDVI .tif files found")
            return

        # Parse filenames like: NDVI_SriLanka_2023_03.tif
        for tif_file in tif_files:
            try:
                parts = tif_file.replace('.tif', '').split('_')
                if len(parts) >= 4:
                    year = int(parts[2])
                    month = int(parts[3])
                    key = f"{year}-{month:02d}"
                    self.ndvi_files[key] = os.path.join(NDVI_DIR, tif_file)
            except:
                continue

        print(f"✓ NDVI files indexed: {len(self.ndvi_files)} months available")
        if len(self.ndvi_files) > 0:
            print(f"  Range: {min(self.ndvi_files.keys())} to {max(self.ndvi_files.keys())}")

    def load_tracking_data(self):
        """Load elephant tracking data - prioritize GBIF data"""

        # Try loading GBIF data first
        gbif_path = os.path.join(os.path.dirname(ELEPHANT_TRACKING_DIR), 'GBIF', 'occurrence.txt')

        if os.path.exists(gbif_path):
            try:
                print("Loading GBIF occurrence data...")
                df = pd.read_csv(gbif_path, sep='\t', low_memory=False)

                # Filter for Sri Lanka and valid coordinates
                if 'decimalLatitude' in df.columns and 'decimalLongitude' in df.columns:
                    df = df.dropna(subset=['decimalLatitude', 'decimalLongitude'])
                    df = df[
                        (df['decimalLatitude'] >= 5.9) & (df['decimalLatitude'] <= 9.9) &
                        (df['decimalLongitude'] >= 79.4) & (df['decimalLongitude'] <= 82.0)
                        ]

                    # Standardize column names
                    df = df.rename(columns={
                        'decimalLatitude': 'latitude',
                        'decimalLongitude': 'longitude',
                        'eventDate': 'Date',
                        'stateProvince': 'Location'
                    })

                    self.tracking_data = df
                    return
            except Exception as e:
                print(f"⚠ Error loading GBIF data: {e}")

        # Fallback to Excel tracking files
        if not os.path.exists(ELEPHANT_TRACKING_DIR):
            print(f"⚠ Tracking directory not found")
            return

        excel_files = [f for f in os.listdir(ELEPHANT_TRACKING_DIR) if f.endswith(('.xls', '.xlsx'))]

        if not excel_files:
            print(f"⚠ No tracking Excel files found")
            return

        dfs = []
        for excel_file in excel_files:
            excel_path = os.path.join(ELEPHANT_TRACKING_DIR, excel_file)
            try:
                df = pd.read_excel(excel_path)
                dfs.append(df)
            except Exception as e:
                print(f"  ⚠ Error loading {excel_file}: {e}")

        if dfs:
            self.tracking_data = pd.concat(dfs, ignore_index=True)
        else:
            print(f"⚠ No tracking data loaded")

    def get_ndvi_value(self, lat, lon, year, month):
        """Extract NDVI value from raster at given location and time"""
        key = f"{year}-{month:02d}"

        if key not in self.ndvi_files:
            # Return default if file not available
            return 0.4

        try:
            raster_path = self.ndvi_files[key]
            with rasterio.open(raster_path) as src:
                # Get row, col from coordinates
                row, col = src.index(lon, lat)

                # Check if within bounds
                if 0 <= row < src.height and 0 <= col < src.width:
                    value = src.read(1)[row, col]

                    # Handle nodata values
                    if value == src.nodata or np.isnan(value) or value < -1:
                        return 0.4

                    # NDVI is typically stored as scaled integer (e.g., 0-10000)
                    # Convert to standard NDVI range (-1 to 1)
                    if value > 1:
                        # Likely scaled by 10000
                        value = value / 10000.0

                    # Clip to valid NDVI range
                    value = np.clip(value, -1.0, 1.0)

                    return float(value)
                else:
                    return 0.4
        except Exception as e:
            # Return default on error
            return 0.4

    def get_rainfall_for_date(self, target_date, days_back=30):
        """Get rainfall data for a specific date and past N days"""
        if self.rainfall_data is None or len(self.rainfall_data) == 0:
            return {
                'rainfall_7day': 0.0,
                'rainfall_14day': 0.0,
                'rainfall_30day': 0.0,
                'is_dry_period': 1
            }

        target_date = pd.to_datetime(target_date)

        # Filter data for the period
        date_7_ago = target_date - pd.Timedelta(days=7)
        date_14_ago = target_date - pd.Timedelta(days=14)
        date_30_ago = target_date - pd.Timedelta(days=30)

        df = self.rainfall_data

        # Calculate rainfall sums
        mask_7 = (df['date'] > date_7_ago) & (df['date'] <= target_date)
        mask_14 = (df['date'] > date_14_ago) & (df['date'] <= target_date)
        mask_30 = (df['date'] > date_30_ago) & (df['date'] <= target_date)

        rainfall_7day = df.loc[mask_7, 'rainfall_mm'].sum() if mask_7.any() else 0.0
        rainfall_14day = df.loc[mask_14, 'rainfall_mm'].sum() if mask_14.any() else 0.0
        rainfall_30day = df.loc[mask_30, 'rainfall_mm'].sum() if mask_30.any() else 0.0

        # Determine if dry period (less than 5mm in last 7 days)
        is_dry_period = 1 if rainfall_7day < 5.0 else 0

        return {
            'rainfall_7day': float(rainfall_7day),
            'rainfall_14day': float(rainfall_14day),
            'rainfall_30day': float(rainfall_30day),
            'is_dry_period': is_dry_period
        }

    def load_cities(self):
        """Load city/division data from GADM"""
        print("\nLoading city data...")
        success = self.city_loader.load_cities(use_cache=True)
        if success:
            print(f"✓ City data loaded: {len(self.city_loader.get_all_districts())} districts")
        else:
            print("⚠ Failed to load city data")

# Global data loader instance
data_loader = DataLoader()

# Test if run directly
if __name__ == '__main__':
    print("=" * 60)
    print("Testing Data Loader")
    print("=" * 60 + "\n")

    data_loader.load_all()

    print("\n" + "=" * 60)
    print("Testing feature extraction")
    print("=" * 60 + "\n")

    # Test NDVI extraction
    test_lat, test_lon = 7.5, 80.5
    test_year, test_month = 2024, 6

    ndvi = data_loader.get_ndvi_value(test_lat, test_lon, test_year, test_month)
    print(f"NDVI at ({test_lat}, {test_lon}) for {test_year}-{test_month}: {ndvi:.4f}")

    # Test rainfall extraction
    if data_loader.rainfall_data is not None and len(data_loader.rainfall_data) > 0:
        # Use a date that exists in the data
        test_date = data_loader.rainfall_data['date'].iloc[len(data_loader.rainfall_data) // 2]
        print(f"\nRainfall for {test_date.date()}:")
        rainfall = data_loader.get_rainfall_for_date(test_date)
        for key, val in rainfall.items():
            print(f"  {key}: {val:.2f}")
    else:
        print("\n⚠ No rainfall data available for testing")

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(
        f"✓ Elephant zones: {len(data_loader.elephant_distribution) if data_loader.elephant_distribution is not None else 0}")
    print(f"✓ Protected areas: {len(data_loader.protected_areas) if data_loader.protected_areas is not None else 0}")
    print(f"✓ Power fences: {len(data_loader.power_fences) if data_loader.power_fences is not None else 0}")
    print(f"✓ Roads: {len(data_loader.roads) if data_loader.roads is not None else 0}")
    print(f"✓ Railways: {len(data_loader.railways) if data_loader.railways is not None else 0}")
    print(f"✓ Rainfall dates: {len(data_loader.rainfall_data) if data_loader.rainfall_data is not None else 0}")
    print(f"✓ NDVI months: {len(data_loader.ndvi_files)}")
    print(f"✓ Tracking records: {len(data_loader.tracking_data) if data_loader.tracking_data is not None else 0}")

    print("\n" + "=" * 60)
    print("Data Loader Test Complete!")
    print("=" * 60)