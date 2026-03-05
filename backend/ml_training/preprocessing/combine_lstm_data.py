import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import TRAINING_OUTPUT_DIR


def load_processed_data():
    """Load all processed data files"""
    print("Loading processed data...\n")

    # Load tracking data
    tracking_path = os.path.join(TRAINING_OUTPUT_DIR, 'tracking_processed.csv')
    if os.path.exists(tracking_path):
        tracking_df = pd.read_csv(tracking_path)
        tracking_df['date'] = pd.to_datetime(tracking_df['date'])
        print(f"✓ Tracking data: {len(tracking_df)} records")
    else:
        print("⚠ Tracking data not found")
        tracking_df = None

    # Load rainfall data
    rainfall_path = os.path.join(TRAINING_OUTPUT_DIR, 'rainfall_processed.csv')
    if os.path.exists(rainfall_path):
        rainfall_df = pd.read_csv(rainfall_path)
        rainfall_df['date'] = pd.to_datetime(rainfall_df['date'])
        print(f"✓ Rainfall data: {len(rainfall_df)} records")
    else:
        print("⚠ Rainfall data not found")
        rainfall_df = None

    # Load NDVI data
    ndvi_path = os.path.join(TRAINING_OUTPUT_DIR, 'ndvi_processed.csv')
    if os.path.exists(ndvi_path):
        ndvi_df = pd.read_csv(ndvi_path)
        print(f"✓ NDVI data: {len(ndvi_df)} records")
    else:
        print("⚠ NDVI data not found")
        ndvi_df = None

    return tracking_df, rainfall_df, ndvi_df


def aggregate_tracking_to_daily(tracking_df):
    """Aggregate tracking points to daily averages"""
    print("\nAggregating tracking to daily...")

    daily = tracking_df.groupby('date').agg({
        'latitude': 'mean',
        'longitude': 'mean',
        'x_utm': 'mean',
        'y_utm': 'mean'
    }).reset_index()

    # Calculate daily movement
    daily['lat_prev'] = daily['latitude'].shift(1)
    daily['lon_prev'] = daily['longitude'].shift(1)

    daily['distance_moved_km'] = np.sqrt(
        (daily['latitude'] - daily['lat_prev']) ** 2 +
        (daily['longitude'] - daily['lon_prev']) ** 2
    ) * 111

    daily['distance_moved_km'] = daily['distance_moved_km'].fillna(0)
    daily = daily.drop(['lat_prev', 'lon_prev'], axis=1)

    print(f"  ✓ {len(daily)} daily records")

    return daily


def merge_rainfall_data(daily_df, rainfall_df):
    """Merge rainfall data to daily tracking"""
    print("\nMerging rainfall data...")

    # Merge on date
    merged = daily_df.merge(
        rainfall_df[['date', 'rainfall_mm', 'rainfall_7day', 'rainfall_30day']],
        on='date',
        how='left'
    )

    # Fill missing rainfall with 0
    merged['rainfall_mm'] = merged['rainfall_mm'].fillna(0)
    merged['rainfall_7day'] = merged['rainfall_7day'].fillna(0)
    merged['rainfall_30day'] = merged['rainfall_30day'].fillna(0)

    print(f"  ✓ Merged {len(merged)} records")

    return merged


def get_nearest_ndvi(lat, lon, year, month, ndvi_df):
    """Get nearest NDVI value for location and time"""

    # Filter by year and month
    ndvi_subset = ndvi_df[
        (ndvi_df['year'] == year) &
        (ndvi_df['month'] == month)
        ]

    if len(ndvi_subset) == 0:
        return None

    # Find nearest location
    ndvi_subset = ndvi_subset.copy()
    ndvi_subset['distance'] = np.sqrt(
        (ndvi_subset['latitude'] - lat) ** 2 +
        (ndvi_subset['longitude'] - lon) ** 2
    )

    # Get closest point
    closest = ndvi_subset.nsmallest(1, 'distance')

    if len(closest) > 0:
        return closest.iloc[0]['ndvi']

    return None


def merge_ndvi_data(daily_df, ndvi_df):
    """Merge NDVI data to daily tracking"""
    print("\nMerging NDVI data...")

    ndvi_values = []

    for idx, row in daily_df.iterrows():
        lat = row['latitude']
        lon = row['longitude']
        date = row['date']
        year = date.year
        month = date.month

        ndvi = get_nearest_ndvi(lat, lon, year, month, ndvi_df)

        if ndvi is None:
            # Use default or previous value
            ndvi = 0.3  # Default vegetation value

        ndvi_values.append(ndvi)

    daily_df['ndvi'] = ndvi_values

    # Previous month NDVI
    daily_df['ndvi_prev_month'] = daily_df['ndvi'].shift(30)
    daily_df['ndvi_prev_month'] = daily_df['ndvi_prev_month'].fillna(daily_df['ndvi'])

    print(f"  ✓ NDVI values added")
    print(f"    Range: {daily_df['ndvi'].min():.3f} to {daily_df['ndvi'].max():.3f}")

    return daily_df


def add_temporal_features(df):
    """Add time-based features"""
    print("\nAdding temporal features...")

    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day_of_year'] = df['date'].dt.dayofyear
    df['day_of_week'] = df['date'].dt.dayofweek

    # Season (Sri Lanka monsoons)
    df['season'] = df['month'].apply(lambda x:
                                     1 if x in [5, 6, 7, 8] else  # Yala monsoon
                                     2 if x in [10, 11, 12, 1] else  # Maha monsoon
                                     0  # Inter-monsoon
                                     )

    print("  ✓ Temporal features added")

    return df


def create_conflict_labels(df):
    """Create conflict labels based on environmental conditions"""
    print("\nCreating conflict labels...")

    # Probability-based labeling
    base_prob = 0.5

    # Higher risk factors
    risk_factors = []

    # Dry season (low rainfall)
    risk_factors.append((df['rainfall_30day'] < 30) * 0.15)

    # Low vegetation
    risk_factors.append((df['ndvi'] < 0.3) * 0.1)

    # High movement
    risk_factors.append((df['distance_moved_km'] > 3) * 0.1)

    # Dry season
    risk_factors.append((df['season'] == 0) * 0.1)

    # Calculate total probability
    conflict_prob = base_prob
    for factor in risk_factors:
        conflict_prob = conflict_prob + factor

    # Generate labels
    np.random.seed(42)
    df['conflict'] = (np.random.random(len(df)) < conflict_prob).astype(int)

    conflict_rate = df['conflict'].mean()
    print(f"  ✓ Conflict labels: {conflict_rate:.1%} positive rate")

    return df


def save_lstm_training_data(df):
    """Save final LSTM training dataset"""
    print("\nSaving LSTM training data...")

    # Select final columns
    final_columns = [
        'date', 'latitude', 'longitude',
        'distance_moved_km',
        'rainfall_mm', 'rainfall_7day', 'rainfall_30day',
        'ndvi', 'ndvi_prev_month',
        'year', 'month', 'day_of_year', 'season',
        'conflict'
    ]

    final_df = df[final_columns].copy()

    # Sort by date
    final_df = final_df.sort_values('date').reset_index(drop=True)

    # Save
    output_path = os.path.join(TRAINING_OUTPUT_DIR, 'lstm_training_data.csv')
    final_df.to_csv(output_path, index=False)

    print(f"✓ Saved to {output_path}")
    print(f"  Shape: {final_df.shape}")
    print(f"  Date range: {final_df['date'].min()} to {final_df['date'].max()}")
    print(f"\nColumns: {list(final_df.columns)}")

    return final_df


def main():
    """Main pipeline"""
    print("=" * 50)
    print("Combining Data for LSTM Training")
    print("=" * 50 + "\n")

    # Load processed data
    tracking_df, rainfall_df, ndvi_df = load_processed_data()

    if tracking_df is None:
        print("\n⚠ No tracking data available")
        return

    # Aggregate tracking to daily
    daily_df = aggregate_tracking_to_daily(tracking_df)

    # Merge rainfall
    if rainfall_df is not None:
        daily_df = merge_rainfall_data(daily_df, rainfall_df)
    else:
        print("  Using default rainfall values")
        daily_df['rainfall_mm'] = 50.0
        daily_df['rainfall_7day'] = 50.0
        daily_df['rainfall_30day'] = 50.0

    # Merge NDVI
    if ndvi_df is not None:
        daily_df = merge_ndvi_data(daily_df, ndvi_df)
    else:
        print("  Using default NDVI values")
        daily_df['ndvi'] = 0.4
        daily_df['ndvi_prev_month'] = 0.4

    # Add features
    daily_df = add_temporal_features(daily_df)
    daily_df = create_conflict_labels(daily_df)

    # Save
    final_df = save_lstm_training_data(daily_df)

    print("\n" + "=" * 50)
    print("Data Combination Complete!")
    print("=" * 50)
    print("\nReady for LSTM training!")
    print("Run: python ml_training/train_lstm_model.py")


if __name__ == '__main__':
    main()