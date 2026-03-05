"""
Step 1: Data Cleanup and Synthesis
Prepares elephant GPS tracking data for corridor detection and risk prediction
"""

import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("STEP 1: DATA CLEANUP AND SYNTHESIS")
print("="*70)

# ============================================================================
# 1. LOAD RAW DATA
# ============================================================================

print("\n[1/7] Loading raw data...")
df_raw = pd.read_csv('./uploads/final7.csv', low_memory=False)
print(f"   Loaded: {len(df_raw):,} records")

# ============================================================================
# 2. REMOVE DUPLICATES
# ============================================================================

print("\n[2/7] Removing duplicates...")
initial_count = len(df_raw)

# Sort by datetime to keep earliest records
df_raw['Datetime_temp'] = pd.to_datetime(df_raw['Datetime'], errors='coerce')
df_raw = df_raw.sort_values('Datetime_temp')

# Remove exact duplicates
df_raw = df_raw.drop_duplicates()

# Remove duplicates based on key columns
df_raw = df_raw.drop_duplicates(
    subset=['EleID', 'latitude', 'longitude', 'Date', 'Time'],
    keep='first'
)

removed = initial_count - len(df_raw)
print(f"   Removed: {removed:,} duplicates ({removed/initial_count*100:.1f}%)")
print(f"   Remaining: {len(df_raw):,} records")

# ============================================================================
# 3. CLEAN AND STANDARDIZE
# ============================================================================

print("\n[3/7] Cleaning and standardizing...")

# Drop empty columns
empty_cols = [col for col in df_raw.columns if df_raw[col].isnull().all()]
if empty_cols:
    df_raw = df_raw.drop(columns=empty_cols)
    print(f"   Dropped {len(empty_cols)} empty columns")

# Drop unnamed columns
unnamed_cols = [col for col in df_raw.columns if 'Unnamed' in str(col)]
if unnamed_cols:
    df_raw = df_raw.drop(columns=unnamed_cols)
    print(f"   Dropped {len(unnamed_cols)} unnamed columns")

# Fix time column
df_raw['Time'] = df_raw['Time'].replace('Homey', np.nan)
df_raw['Time'] = df_raw.groupby('EleID')['Time'].fillna(method='ffill')
df_raw['Time'] = df_raw.groupby('EleID')['Time'].fillna(method='bfill')

# Standardize datetime
df_raw['Date_parsed'] = pd.to_datetime(
    df_raw['Date'], dayfirst=True, errors='coerce')
df_raw['Datetime_standard'] = pd.to_datetime(
    df_raw['Date_parsed'].astype(str) + ' ' + df_raw['Time'].astype(str),
    errors='coerce'
)

# Normalize NDVI (scale to -1 to 1)
df_raw['NDVI_normalized'] = (df_raw['NDVI'] / 10000).clip(-1, 1)

# Handle protected areas
df_raw['NAME_ENG'] = df_raw['NAME_ENG'].fillna('Not Protected')
df_raw['DESIG'] = df_raw['DESIG'].fillna('None')

# Fill small gaps in numeric columns with median
numeric_cols = ['Elevation', 'LandCover2',
                'RoadDistance', 'WaterDistance', 'HumanDistance']
for col in numeric_cols:
    if col in df_raw.columns:
        df_raw[col] = df_raw[col].fillna(df_raw[col].median())

print(f"   Cleaned: {len(df_raw.columns)} columns")

# ============================================================================
# 4. FEATURE ENGINEERING
# ============================================================================

print("\n[4/7] Engineering features...")

# Temporal features
df_raw['Year'] = df_raw['Date_parsed'].dt.year
df_raw['Month'] = df_raw['Date_parsed'].dt.month
df_raw['Day'] = df_raw['Date_parsed'].dt.day
df_raw['DayOfWeek'] = df_raw['Date_parsed'].dt.dayofweek
df_raw['Hour'] = pd.to_datetime(
    df_raw['Time'], format='%H:%M', errors='coerce').dt.hour

# Season mapping for Sri Lanka
season_map = {
    12: 'Dry', 1: 'Dry', 2: 'Dry',
    3: 'Inter-Monsoon', 4: 'Inter-Monsoon', 5: 'Inter-Monsoon',
    6: 'Southwest-Monsoon', 7: 'Southwest-Monsoon', 8: 'Southwest-Monsoon',
    9: 'Inter-Monsoon-2', 10: 'Inter-Monsoon-2', 11: 'Inter-Monsoon-2'
}
df_raw['Season'] = df_raw['Month'].map(season_map)

# Time of day categorization


def categorize_time_of_day(hour):
    if pd.isna(hour):
        return 'Unknown'
    elif hour < 6:
        return 'Night'
    elif hour < 10:
        return 'Early Morning'
    elif hour < 14:
        return 'Midday'
    elif hour < 18:
        return 'Afternoon'
    elif hour < 22:
        return 'Evening'
    else:
        return 'Night'


df_raw['TimeOfDay'] = df_raw['Hour'].apply(categorize_time_of_day)

# Label: elephant present (1) at this location/time
df_raw['ElephantPresent'] = 1

print(f"   Created temporal and categorical features")

# ============================================================================
# 5. ONE-HOT ENCODE LANDCOVER
# ============================================================================

print("\n[5/7] One-hot encoding LandCover...")

# LandCover meanings (approximate):
# 10 = Forest, 20 = Shrubland, 30 = Grassland, 40 = Cropland
# 50 = Built-up, 60 = Bare, 80 = Wetland, 90 = Water

landcover_cols = pd.get_dummies(df_raw['LandCover2'], prefix='LC')
df_raw = pd.concat([df_raw, landcover_cols], axis=1)

print(
    f"   Created {len(landcover_cols.columns)} LandCover columns: {landcover_cols.columns.tolist()}")

# ============================================================================
# 6. GENERATE NEGATIVE SAMPLES (ENVIRONMENTAL INTERPOLATION)
# ============================================================================

print("\n[6/7] Generating negative samples with environmental interpolation...")

# Get bounding box of elephant locations
lat_min, lat_max = df_raw['latitude'].min(), df_raw['latitude'].max()
lon_min, lon_max = df_raw['longitude'].min(), df_raw['longitude'].max()

# Build KD-Tree for fast nearest neighbor lookup
coords = df_raw[['latitude', 'longitude']].values
kdtree = cKDTree(coords)

# Environmental columns to interpolate from nearest real point
env_columns = [
    'NDVI_normalized', 'LandCover2', 'Elevation',
    'RoadDistance', 'WaterDistance', 'HumanDistance', 'Protected'
]

# Add one-hot LandCover columns
lc_columns = [col for col in df_raw.columns if col.startswith('LC_')]
env_columns_with_lc = env_columns + lc_columns

# Generate negative samples
n_negative = len(df_raw)
negative_samples = []

print(f"   Generating {n_negative:,} negative samples...")
print(f"   Using environmental interpolation from nearest real points")

np.random.seed(42)
attempts = 0
max_attempts = n_negative * 20

# Haversine for distance check


def haversine_distance(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


while len(negative_samples) < n_negative and attempts < max_attempts:
    attempts += 1

    # Random location within bounding box (with small buffer)
    rand_lat = np.random.uniform(lat_min - 0.05, lat_max + 0.05)
    rand_lon = np.random.uniform(lon_min - 0.05, lon_max + 0.05)

    # Find nearest point using KD-Tree (approximate distance in degrees)
    dist_deg, nearest_idx = kdtree.query([rand_lat, rand_lon])

    # Convert to meters for actual check
    nearest_point = df_raw.iloc[nearest_idx]
    actual_dist = haversine_distance(
        rand_lat, rand_lon,
        nearest_point['latitude'], nearest_point['longitude']
    )

    # Must be >2.5km from any elephant sighting
    if actual_dist < 2500:
        continue

    # INTERPOLATION: Copy environmental features from nearest real point
    nearest_row = df_raw.iloc[nearest_idx]

    # Sample random datetime from dataset
    rand_datetime = df_raw['Datetime_standard'].dropna().sample(1).iloc[0]

    # Create negative sample with REAL environmental features
    negative_sample = {
        'EleID': 0,
        'Name': 'Negative',
        'latitude': rand_lat,
        'longitude': rand_lon,
        'Datetime_standard': rand_datetime,
        'Date_parsed': rand_datetime.date() if pd.notna(rand_datetime) else None,
        'Year': rand_datetime.year if pd.notna(rand_datetime) else 2010,
        'Month': rand_datetime.month if pd.notna(rand_datetime) else 6,
        'Day': rand_datetime.day if pd.notna(rand_datetime) else 15,
        'DayOfWeek': rand_datetime.weekday() if pd.notna(rand_datetime) else 3,
        'Hour': rand_datetime.hour if pd.notna(rand_datetime) else 12,
        'Season': season_map.get(rand_datetime.month if pd.notna(rand_datetime) else 6),
        'TimeOfDay': categorize_time_of_day(rand_datetime.hour if pd.notna(rand_datetime) else 12),

        # INTERPOLATED from nearest real point (not random!)
        'NDVI_normalized': nearest_row['NDVI_normalized'],
        'LandCover2': nearest_row['LandCover2'],
        'Elevation': nearest_row['Elevation'],
        'RoadDistance': nearest_row['RoadDistance'],
        'WaterDistance': nearest_row['WaterDistance'],
        'HumanDistance': nearest_row['HumanDistance'],
        'Protected': nearest_row['Protected'],

        'ElephantPresent': 0  # Negative label
    }

    # Copy one-hot LandCover columns
    for lc_col in lc_columns:
        negative_sample[lc_col] = nearest_row[lc_col]

    negative_samples.append(negative_sample)

    if len(negative_samples) % 2000 == 0:
        print(f"   Generated: {len(negative_samples):,}/{n_negative:,}")

df_negative = pd.DataFrame(negative_samples)
print(
    f"   Created: {len(df_negative):,} negative samples with interpolated environment")

# ============================================================================
# 7. COMBINE AND SAVE
# ============================================================================

print("\n[7/7] Combining and saving...")

# Ensure both dataframes have same columns for concat
common_cols = list(set(df_raw.columns) & set(df_negative.columns))
df_raw_subset = df_raw[common_cols].copy()
df_negative_subset = df_negative[common_cols].copy()

# Combine positive and negative samples
df_final = pd.concat([df_raw_subset, df_negative_subset], ignore_index=True)

# Shuffle
df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

# Ensure one-hot columns exist and are filled
for lc_col in lc_columns:
    if lc_col not in df_final.columns:
        df_final[lc_col] = 0
    df_final[lc_col] = df_final[lc_col].fillna(0).astype(int)

# Save cleaned data
df_final.to_csv('./outputs/cleaned_data.csv', index=False)
print(f"   Saved: cleaned_data.csv ({len(df_final):,} records)")

# Save elephant-only data (for corridor detection)
df_elephants = df_raw.copy()
df_elephants.to_csv('./outputs/elephant_data.csv', index=False)
print(f"   Saved: elephant_data.csv ({len(df_elephants):,} records)")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*70)
print("DATA PREPARATION COMPLETE")
print("="*70)

print(f"\nOriginal data: {initial_count:,} records")
print(f"After cleaning: {len(df_raw):,} records")
print(f"Negative samples: {len(df_negative):,} records")
print(f"Total dataset: {len(df_final):,} records")

print(f"\nNegative Sample Method: ENVIRONMENTAL INTERPOLATION")
print(f"  - Each negative point inherits environment from nearest real GPS point")

print(f"\nLandCover Encoding: ONE-HOT")
print(f"  - Columns: {lc_columns}")
print(f"  - No false ordinal relationships")

print(f"\nElephant distribution:")
for name, count in df_raw['Name'].value_counts().head(10).items():
    print(f"  {name}: {count:,} records")

print(f"\nLabel distribution:")
print(
    f"  Elephant Present (1): {(df_final['ElephantPresent'] == 1).sum():,} ({(df_final['ElephantPresent'] == 1).sum()/len(df_final)*100:.1f}%)")
print(
    f"  Not Present (0): {(df_final['ElephantPresent'] == 0).sum():,} ({(df_final['ElephantPresent'] == 0).sum()/len(df_final)*100:.1f}%)")

print(f"\nFiles created:")
print(f"  1. cleaned_data.csv - Full dataset for ML training")
print(f"  2. elephant_data.csv - Elephant-only data for corridor detection")

print("\n" + "="*70)
print("Ready for Phase 1: Corridor Detection")
print("="*70)
