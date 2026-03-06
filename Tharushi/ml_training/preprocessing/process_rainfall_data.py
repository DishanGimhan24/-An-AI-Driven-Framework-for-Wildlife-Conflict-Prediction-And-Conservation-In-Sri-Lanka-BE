import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import glob

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import RAINFALL_DIR, TRAINING_OUTPUT_DIR


def load_rainfall_csv():
    """Load rainfall CSV files from NASA Power API"""
    print("Loading rainfall data...\n")

    csv_files = glob.glob(os.path.join(RAINFALL_DIR, '*.csv'))

    if len(csv_files) == 0:
        print("⚠ No CSV files found in rainfall directory")
        print(f"  Looking in: {RAINFALL_DIR}")
        return None

    print(f"Found {len(csv_files)} CSV files\n")

    all_rainfall = []

    for filepath in csv_files:
        try:
            print(f"  Loading {os.path.basename(filepath)}...")

            # Skip header lines (NASA Power format has header info)
            # Data starts at line with "LAT,LON,YEAR,DOY,PRECTOTCORR"
            with open(filepath, 'r') as f:
                lines = f.readlines()

            # Find data start line
            data_start = 0
            for i, line in enumerate(lines):
                if 'LAT,LON,YEAR,DOY,PRECTOTCORR' in line or 'LAT,LON,YEAR' in line:
                    data_start = i
                    break

            # Read from data start
            df = pd.read_csv(filepath, skiprows=data_start)

            all_rainfall.append(df)
            print(f"    ✓ {len(df)} records")

        except Exception as e:
            print(f"    ✗ Error: {e}")

    if len(all_rainfall) == 0:
        return None

    # Combine all years
    combined = pd.concat(all_rainfall, ignore_index=True)

    print(f"\n✓ Total rainfall records: {len(combined)}")
    print(f"  Columns: {list(combined.columns)}")

    return combined


def process_rainfall_data(df):
    """Process rainfall data to usable format"""
    print("\nProcessing rainfall data...")

    processed = pd.DataFrame()

    # Extract columns
    processed['latitude'] = pd.to_numeric(df['LAT'], errors='coerce')
    processed['longitude'] = pd.to_numeric(df['LON'], errors='coerce')
    processed['year'] = pd.to_numeric(df['YEAR'], errors='coerce')
    processed['day_of_year'] = pd.to_numeric(df['DOY'], errors='coerce')
    processed['rainfall_mm'] = pd.to_numeric(df['PRECTOTCORR'], errors='coerce')

    # Create date from year and day_of_year
    processed['date'] = pd.to_datetime(
        processed['year'].astype(int).astype(str) + '-01-01'
    ) + pd.to_timedelta(processed['day_of_year'] - 1, unit='D')

    # Replace missing values (-999) with NaN
    processed['rainfall_mm'] = processed['rainfall_mm'].replace(-999, np.nan)

    # Remove negative values
    processed.loc[processed['rainfall_mm'] < 0, 'rainfall_mm'] = 0

    # Remove invalid data
    processed = processed.dropna(subset=['date', 'rainfall_mm'])

    # Sort by date
    processed = processed.sort_values('date').reset_index(drop=True)

    print(f"  ✓ Processed {len(processed)} rainfall records")
    print(f"  Date range: {processed['date'].min()} to {processed['date'].max()}")
    print(f"  Rainfall range: {processed['rainfall_mm'].min():.2f} to {processed['rainfall_mm'].max():.2f} mm/day")

    return processed


def aggregate_to_daily(df):
    """Aggregate rainfall to daily Sri Lanka average"""
    print("\nAggregating to daily averages...")

    # Average across all locations for each day (Sri Lanka-wide average)
    daily = df.groupby('date').agg({
        'rainfall_mm': 'mean',
        'latitude': 'mean',
        'longitude': 'mean'
    }).reset_index()

    # Add rolling averages
    daily['rainfall_7day'] = daily['rainfall_mm'].rolling(7, min_periods=1).mean()
    daily['rainfall_30day'] = daily['rainfall_mm'].rolling(30, min_periods=1).mean()

    print(f"  ✓ {len(daily)} daily records")

    return daily


def save_processed_rainfall(df):
    """Save processed rainfall data"""
    os.makedirs(TRAINING_OUTPUT_DIR, exist_ok=True)

    output_path = os.path.join(TRAINING_OUTPUT_DIR, 'rainfall_processed.csv')
    df.to_csv(output_path, index=False)

    print(f"\n✓ Saved processed rainfall to {output_path}")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")


def main():
    """Main processing"""
    print("=" * 50)
    print("Processing Rainfall Data")
    print("=" * 50 + "\n")

    # Load rainfall CSVs
    rainfall_df = load_rainfall_csv()

    if rainfall_df is None:
        print("\n⚠ No rainfall data to process")
        return

    # Process data
    processed = process_rainfall_data(rainfall_df)

    if len(processed) == 0:
        print("\n⚠ No valid rainfall data after processing")
        return

    # Aggregate to daily
    daily = aggregate_to_daily(processed)

    # Save
    save_processed_rainfall(daily)

    print("\n" + "=" * 50)
    print("Rainfall Processing Complete!")
    print("=" * 50)


if __name__ == '__main__':
    main()