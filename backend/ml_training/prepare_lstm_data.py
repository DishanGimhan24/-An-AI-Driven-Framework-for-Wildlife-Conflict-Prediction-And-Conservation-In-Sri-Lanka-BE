import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import glob

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ELEPHANT_TRACKING_DIR, TRAINING_OUTPUT_DIR


def load_tracking_files():
    """Load all elephant tracking Excel files"""
    print("Loading elephant tracking data...")

    # Get all Excel files from tracking directory
    excel_files = glob.glob(os.path.join(ELEPHANT_TRACKING_DIR, '*.xls'))
    excel_files += glob.glob(os.path.join(ELEPHANT_TRACKING_DIR, '*.xlsx'))

    print(f"Found {len(excel_files)} tracking files")

    all_data = []

    for file_path in excel_files:
        try:
            print(f"  Loading {os.path.basename(file_path)}...")
            df = pd.read_excel(file_path)

            # Add source file info
            df['source_file'] = os.path.basename(file_path)

            all_data.append(df)
            print(f"    ✓ {len(df)} records")

        except Exception as e:
            print(f"    ✗ Error: {e}")

    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)

    print(f"\n✓ Total records: {len(combined_df)}")
    print(f"  Columns: {list(combined_df.columns)}")

    return combined_df


def process_tracking_data(df):
    """Process tracking data for LSTM"""
    print("\nProcessing tracking data...")

    # Show first few rows to understand structure
    print("\nSample data:")
    print(df.head())
    print("\nData types:")
    print(df.dtypes)

    # Check for date column
    date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
    print(f"\nPossible date columns: {date_columns}")

    # Check for location columns
    location_columns = [col for col in df.columns if any(x in col.lower() for x in ['lat', 'lon', 'x', 'y'])]
    print(f"Location columns: {location_columns}")

    return df


def create_time_series_features(df):
    """Create time series features from tracking data"""
    print("\nCreating time series features...")

    # This will be customized based on what columns we find
    # For now, just return the processed dataframe

    # Sort by date if date column exists
    date_col = None
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
                date_col = col
                break
            except:
                continue

    if date_col:
        df = df.sort_values(date_col).reset_index(drop=True)
        print(f"✓ Sorted by {date_col}")
        print(f"  Date range: {df[date_col].min()} to {df[date_col].max()}")

    return df


def main():
    """Main processing pipeline"""
    print("=" * 50)
    print("Preparing Real LSTM Training Data")
    print("=" * 50 + "\n")

    # Load tracking files
    df = load_tracking_files()

    # Process data
    df = process_tracking_data(df)

    # Create time series features
    df = create_time_series_features(df)

    # Save processed data
    os.makedirs(TRAINING_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(TRAINING_OUTPUT_DIR, 'real_tracking_data.csv')
    df.to_csv(output_path, index=False)

    print(f"\n✓ Saved to {output_path}")
    print(f"  Shape: {df.shape}")

    print("\n" + "=" * 50)
    print("Processing Complete!")
    print("=" * 50)
    print("\nNext step: Review the data structure and create LSTM features")


if __name__ == '__main__':
    main()