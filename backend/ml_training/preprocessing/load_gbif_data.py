import pandas as pd
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def load_gbif_occurrences(gbif_path):
    """
    Load elephant occurrences from GBIF dataset

    Args:
        gbif_path: Path to GBIF occurrence.txt file

    Returns:
        DataFrame with cleaned occurrence data
    """
    print("Loading GBIF elephant occurrence data...")

    # GBIF uses tab-delimited format
    df = pd.read_csv(gbif_path, sep='\t', low_memory=False)

    print(f"✓ Loaded {len(df)} raw records")
    print(f"  Columns: {df.columns.tolist()[:10]}...")

    # Extract relevant columns
    occurrences = pd.DataFrame()

    # Coordinates
    occurrences['latitude'] = pd.to_numeric(df['decimalLatitude'], errors='coerce')
    occurrences['longitude'] = pd.to_numeric(df['decimalLongitude'], errors='coerce')

    # Date - try multiple date columns
    if 'eventDate' in df.columns:
        occurrences['date'] = pd.to_datetime(df['eventDate'], errors='coerce')
    elif 'year' in df.columns and 'month' in df.columns:
        # Construct date from year/month/day
        occurrences['year'] = pd.to_numeric(df['year'], errors='coerce')
        occurrences['month'] = pd.to_numeric(df['month'], errors='coerce')
        occurrences['day'] = pd.to_numeric(df.get('day', 15), errors='coerce')  # Default to 15 if no day

        occurrences['date'] = pd.to_datetime(
            occurrences[['year', 'month', 'day']].rename(
                columns={'year': 'year', 'month': 'month', 'day': 'day'}
            ),
            errors='coerce'
        )

    # Add basis of record (human observation is more reliable for conflicts)
    occurrences['basis_of_record'] = df.get('basisOfRecord', 'UNKNOWN')

    # Clean data
    print("\nCleaning data...")

    # Remove records without coordinates
    occurrences = occurrences.dropna(subset=['latitude', 'longitude'])
    print(f"  After removing null coordinates: {len(occurrences)} records")

    # Filter to valid Sri Lankan coordinates
    occurrences = occurrences[
        (occurrences['latitude'] >= 5.9) & (occurrences['latitude'] <= 9.9) &
        (occurrences['longitude'] >= 79.4) & (occurrences['longitude'] <= 82.0)
        ]
    print(f"  After filtering to Sri Lanka bounds: {len(occurrences)} records")

    # Remove duplicate coordinates on same date
    occurrences = occurrences.drop_duplicates(subset=['latitude', 'longitude', 'date'])
    print(f"  After removing duplicates: {len(occurrences)} records")

    # Fill missing dates with random dates (for records without dates)
    import numpy as np
    missing_dates = occurrences['date'].isna()
    if missing_dates.any():
        print(f"  Filling {missing_dates.sum()} missing dates...")
        np.random.seed(42)
        random_dates = pd.date_range('2020-01-01', '2024-12-31', periods=missing_dates.sum())
        occurrences.loc[missing_dates, 'date'] = random_dates

    # Sort by date
    occurrences = occurrences.sort_values('date').reset_index(drop=True)

    print(f"\n✓ Final dataset: {len(occurrences)} clean elephant occurrences")
    print(f"  Date range: {occurrences['date'].min()} to {occurrences['date'].max()}")
    print(f"  Lat range: {occurrences['latitude'].min():.4f} to {occurrences['latitude'].max():.4f}")
    print(f"  Lon range: {occurrences['longitude'].min():.4f} to {occurrences['longitude'].max():.4f}")

    return occurrences


def create_positive_samples_from_gbif(gbif_occurrences):
    """
    Create positive conflict samples from GBIF data
    Assumes elephant sightings indicate potential conflict zones
    """
    print("\nCreating positive conflict samples from GBIF data...")

    positive_samples = pd.DataFrame()
    positive_samples['latitude'] = gbif_occurrences['latitude']
    positive_samples['longitude'] = gbif_occurrences['longitude']
    positive_samples['date'] = gbif_occurrences['date']
    positive_samples['conflict'] = 1  # Mark as conflict zone
    positive_samples['source'] = 'GBIF'

    print(f"✓ Created {len(positive_samples)} positive samples from GBIF")

    return positive_samples


def main():
    """Test loading GBIF data"""

    # Update this path to your GBIF occurrence.txt file location
    gbif_file = 'Final Dataset/GBIF/occurrence.txt'

    # location
    possible_paths = [
        'Final Dataset/GBIF/occurrence.txt'
    ]

    for path in possible_paths:
        if os.path.exists(path):
            gbif_file = path
            break

    if not os.path.exists(gbif_file):
        print(f"✗ GBIF file not found!")
        print(f"Please place occurrence.txt in one of these locations:")
        for p in possible_paths:
            print(f"  - {p}")
        return

    # Load GBIF data
    occurrences = load_gbif_occurrences(gbif_file)

    # Show sample
    print("\nSample records:")
    print(occurrences.head(10))

    # Create positive samples
    positive_samples = create_positive_samples_from_gbif(occurrences)

    print("\nPositive samples:")
    print(positive_samples.head(10))


if __name__ == '__main__':
    main()