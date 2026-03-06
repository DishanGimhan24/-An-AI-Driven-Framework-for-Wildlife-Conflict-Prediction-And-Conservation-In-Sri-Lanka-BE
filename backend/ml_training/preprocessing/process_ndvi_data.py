import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import glob
import rasterio
from rasterio.sample import sample_gen

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import NDVI_DIR, TRAINING_OUTPUT_DIR


def list_ndvi_files():
    """List all NDVI raster files"""
    print("Finding NDVI raster files...\n")

    tif_files = glob.glob(os.path.join(NDVI_DIR, '*.tif'))

    if len(tif_files) == 0:
        print("⚠ No .tif files found in NDVI directory")
        print(f"  Looking in: {NDVI_DIR}")
        return []

    print(f"Found {len(tif_files)} NDVI files\n")

    # Parse filenames
    ndvi_files = []

    for filepath in tif_files:
        filename = os.path.basename(filepath)

        try:
            # Format: NDVI_SriLanka_2020-01.tif or NDVI_SriLanka_2023_03.tif
            # Remove .tif extension
            name_without_ext = filename.replace('.tif', '')

            # Split by underscore
            parts = name_without_ext.split('_')

            # Last part should be date (either YYYY-MM or YYYY with next part being MM)
            date_part = parts[-1]

            # Try different formats
            if '-' in date_part:
                # Format: 2020-01
                year, month = date_part.split('-')
                year = int(year)
                month = int(month)
            elif len(date_part) == 4 and date_part.isdigit():
                # Format: YYYY_MM (year is last part, month might be in previous part or missing)
                year = int(date_part)
                # Check if there's a month part before
                if len(parts) >= 3 and parts[-2].isdigit() and len(parts[-2]) <= 2:
                    month = int(parts[-2])
                else:
                    month = 1  # default to January
            elif len(date_part) == 2 and date_part.isdigit():
                # Format: YYYY_MM where MM is last part
                month = int(date_part)
                # Year should be in previous part
                if len(parts) >= 2 and len(parts[-2]) == 4:
                    year = int(parts[-2])
                else:
                    continue
            else:
                print(f"  ⚠ Could not parse: {filename}")
                continue

            ndvi_files.append({
                'filepath': filepath,
                'filename': filename,
                'year': year,
                'month': month
            })
            print(f"  ✓ {filename} -> {year}-{month:02d}")

        except Exception as e:
            print(f"  ⚠ Could not parse: {filename} ({e})")

    # Sort by year and month
    ndvi_files = sorted(ndvi_files, key=lambda x: (x['year'], x['month']))

    print(f"\n✓ Parsed {len(ndvi_files)} NDVI files")

    return ndvi_files


def sample_ndvi_at_location(filepath, lat, lon):
    """Extract NDVI value at specific location from raster"""
    try:
        with rasterio.open(filepath) as src:
            # Get the raster's CRS and bounds
            # print(f"    CRS: {src.crs}, Bounds: {src.bounds}")

            # Sample at location (lon, lat order for rasterio)
            coords = [(lon, lat)]

            # Use sample_gen to extract values
            for val in src.sample(coords):
                ndvi = val[0]

                # Check for valid NDVI range (-1 to 1)
                # Also check for nodata values
                if src.nodata is not None and ndvi == src.nodata:
                    return None

                if -1 <= ndvi <= 1 and ndvi != 0:
                    return float(ndvi)
                elif ndvi > 1 and ndvi < 10000:
                    # Some NDVI rasters are scaled (0-10000)
                    ndvi_scaled = (ndvi / 10000.0) * 2 - 1  # Convert to -1 to 1
                    if -1 <= ndvi_scaled <= 1:
                        return float(ndvi_scaled)

    except Exception as e:
        # print(f"    Error sampling {filepath}: {e}")
        pass

    return None


def create_ndvi_monthly_lookup(ndvi_files):
    """Create monthly NDVI lookup table with grid sampling"""
    print("\nCreating NDVI lookup table...")

    # Create sample grid across Sri Lanka
    print("  Creating sample grid...")

    # Use a smaller grid first to test
    lat_range = np.arange(6.0, 9.5, 0.5)  # Coarser grid for testing
    lon_range = np.arange(79.5, 81.5, 0.5)

    sample_locations = []
    for lat in lat_range:
        for lon in lon_range:
            sample_locations.append({'latitude': lat, 'longitude': lon})

    print(f"  Generated {len(sample_locations)} sample points")

    # Sample NDVI for each month
    records = []

    for ndvi_file in ndvi_files:
        print(f"  Processing {ndvi_file['filename']}...")

        valid_samples = 0

        # Try to get raster info
        try:
            with rasterio.open(ndvi_file['filepath']) as src:
                print(f"    Raster info: CRS={src.crs}, Shape={src.shape}, Bounds={src.bounds}")
                print(f"    NoData={src.nodata}, dtype={src.dtypes[0]}")

                # Sample some values to check range
                sample_vals = []
                for loc in sample_locations[:5]:
                    for val in src.sample([(loc['longitude'], loc['latitude'])]):
                        if val[0] != src.nodata:
                            sample_vals.append(val[0])

                if sample_vals:
                    print(f"    Sample values: min={min(sample_vals)}, max={max(sample_vals)}")
        except Exception as e:
            print(f"    Error reading raster: {e}")

        for loc in sample_locations:
            lat = loc['latitude']
            lon = loc['longitude']

            ndvi = sample_ndvi_at_location(ndvi_file['filepath'], lat, lon)

            if ndvi is not None:
                records.append({
                    'year': ndvi_file['year'],
                    'month': ndvi_file['month'],
                    'latitude': lat,
                    'longitude': lon,
                    'ndvi': ndvi
                })
                valid_samples += 1

        print(f"    ✓ {valid_samples} valid samples")

    # Create DataFrame
    ndvi_df = pd.DataFrame(records)

    print(f"\n✓ Created NDVI lookup with {len(ndvi_df)} records")

    if len(ndvi_df) > 0:
        print(f"  NDVI range: {ndvi_df['ndvi'].min():.3f} to {ndvi_df['ndvi'].max():.3f}")
    else:
        print("  ⚠ WARNING: No valid NDVI values extracted!")
        print("  This might be due to:")
        print("    - Coordinate system mismatch")
        print("    - Raster is scaled differently")
        print("    - NoData values not handled correctly")

    return ndvi_df


def save_processed_ndvi(df, file_list):
    """Save processed NDVI data"""
    os.makedirs(TRAINING_OUTPUT_DIR, exist_ok=True)

    # Save lookup table
    output_path = os.path.join(TRAINING_OUTPUT_DIR, 'ndvi_processed.csv')
    df.to_csv(output_path, index=False)

    print(f"\n✓ Saved NDVI lookup to {output_path}")
    print(f"  Shape: {df.shape}")

    # Save file list for reference
    file_list_df = pd.DataFrame(file_list)
    file_list_path = os.path.join(TRAINING_OUTPUT_DIR, 'ndvi_files.csv')
    file_list_df.to_csv(file_list_path, index=False)

    print(f"✓ Saved NDVI file list to {file_list_path}")


def main():
    """Main processing"""
    print("=" * 50)
    print("Processing NDVI Data")
    print("=" * 50 + "\n")

    # List NDVI files
    ndvi_files = list_ndvi_files()

    if len(ndvi_files) == 0:
        print("\n⚠ No NDVI files to process")
        return

    # Create lookup table
    ndvi_df = create_ndvi_monthly_lookup(ndvi_files)

    # Save even if empty (for debugging)
    save_processed_ndvi(ndvi_df, ndvi_files)

    print("\n" + "=" * 50)
    print("NDVI Processing Complete!")
    print("=" * 50)


if __name__ == '__main__':
    main()