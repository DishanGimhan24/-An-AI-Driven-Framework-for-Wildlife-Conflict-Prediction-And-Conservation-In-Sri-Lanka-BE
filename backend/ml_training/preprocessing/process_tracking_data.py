import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import glob
from pyproj import Transformer

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import ELEPHANT_TRACKING_DIR, TRAINING_OUTPUT_DIR


def convert_utm_to_latlon(x, y, utm_zone=44, hemisphere='N'):
    """
    Convert UTM coordinates to lat/lon
    Sri Lanka is in UTM Zone 44N
    """
    # Create transformer from UTM to WGS84
    utm_crs = f"EPSG:326{utm_zone}" if hemisphere == 'N' else f"EPSG:327{utm_zone}"
    wgs84_crs = "EPSG:4326"

    transformer = Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)

    # Transform coordinates
    lon, lat = transformer.transform(x, y)

    return lat, lon


def load_and_clean_tracking_file(filepath):
    """Load and clean single tracking Excel file"""
    print(f"  Processing {os.path.basename(filepath)}...")

    try:
        df = pd.read_excel(filepath)

        # Check available columns
        cols = list(df.columns)

        # Initialize cleaned data
        cleaned = pd.DataFrame()

        # Extract ID
        if 'ID' in df.columns:
            cleaned['id'] = df['ID']

        # Extract X, Y coordinates
        if 'X' in df.columns and 'Y' in df.columns:
            cleaned['x_utm'] = pd.to_numeric(df['X'], errors='coerce')
            cleaned['y_utm'] = pd.to_numeric(df['Y'], errors='coerce')

        # Extract Date
        if 'Date' in df.columns:
            cleaned['date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Extract Time if available
        if 'Time' in df.columns:
            cleaned['time'] = df['Time']

        # Add source file
        cleaned['source_file'] = os.path.basename(filepath)

        # Remove rows with missing critical data
        cleaned = cleaned.dropna(subset=['x_utm', 'y_utm', 'date'])

        # Convert UTM to Lat/Lon (Sri Lanka is UTM Zone 44N)
        if len(cleaned) > 0:
            lats = []
            lons = []

            for idx, row in cleaned.iterrows():
                try:
                    lat, lon = convert_utm_to_latlon(row['x_utm'], row['y_utm'], utm_zone=44)
                    lats.append(lat)
                    lons.append(lon)
                except:
                    lats.append(None)
                    lons.append(None)

            cleaned['latitude'] = lats
            cleaned['longitude'] = lons

            # Filter valid Sri Lankan coordinates
            cleaned = cleaned.dropna(subset=['latitude', 'longitude'])
            cleaned = cleaned[
                (cleaned['latitude'] >= 5.9) & (cleaned['latitude'] <= 9.9) &
                (cleaned['longitude'] >= 79.4) & (cleaned['longitude'] <= 82.0)
                ]

        print(f"    ✓ {len(cleaned)} valid records")

        return cleaned

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return pd.DataFrame()


def load_all_tracking_data():
    """Load all tracking Excel files"""
    print("Loading elephant tracking data...\n")

    excel_files = glob.glob(os.path.join(ELEPHANT_TRACKING_DIR, '*.xls'))
    excel_files += glob.glob(os.path.join(ELEPHANT_TRACKING_DIR, '*.xlsx'))

    print(f"Found {len(excel_files)} tracking files\n")

    all_data = []

    for filepath in excel_files:
        cleaned_df = load_and_clean_tracking_file(filepath)
        if len(cleaned_df) > 0:
            all_data.append(cleaned_df)

    if len(all_data) == 0:
        print("\n⚠ No valid tracking data found!")
        return None

    # Combine all data
    combined = pd.concat(all_data, ignore_index=True)

    # Sort by date
    combined = combined.sort_values('date').reset_index(drop=True)

    print(f"\n✓ Total valid tracking points: {len(combined)}")
    print(f"  Date range: {combined['date'].min()} to {combined['date'].max()}")
    print(f"  Lat range: {combined['latitude'].min():.4f} to {combined['latitude'].max():.4f}")
    print(f"  Lon range: {combined['longitude'].min():.4f} to {combined['longitude'].max():.4f}")

    return combined


def save_processed_tracking(df):
    """Save processed tracking data"""
    os.makedirs(TRAINING_OUTPUT_DIR, exist_ok=True)

    output_path = os.path.join(TRAINING_OUTPUT_DIR, 'tracking_processed.csv')
    df.to_csv(output_path, index=False)

    print(f"\n✓ Saved processed tracking to {output_path}")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")


def main():
    """Main processing"""
    print("=" * 50)
    print("Processing Elephant Tracking Data")
    print("=" * 50 + "\n")

    # Load and process all tracking files
    tracking_df = load_all_tracking_data()

    if tracking_df is None:
        return

    # Save processed data
    save_processed_tracking(tracking_df)

    print("\n" + "=" * 50)
    print("Tracking Data Processing Complete!")
    print("=" * 50)


if __name__ == '__main__':
    main()