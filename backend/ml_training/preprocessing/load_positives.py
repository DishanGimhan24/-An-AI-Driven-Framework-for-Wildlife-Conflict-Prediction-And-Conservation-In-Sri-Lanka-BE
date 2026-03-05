import pandas as pd
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def load_positive_samples():
    """
    Load positive samples from GBIF elephant occurrence data
    """
    print("Loading positive samples from GBIF...")

    # GBIF file paths
    gbif_paths = [
        'Final Dataset/GBIF/occurrence.txt',
        os.path.join(os.path.dirname(__file__), '..', '..', 'Final Dataset', 'GBIF', 'occurrence.txt'),
    ]

    gbif_file = None
    for path in gbif_paths:
        if os.path.exists(path):
            gbif_file = path
            break

    if not gbif_file:
        print("✗ GBIF occurrence.txt not found!")
        return pd.DataFrame()

    # Load GBIF data
    df = pd.read_csv(gbif_file, sep='\t', low_memory=False)

    # Extract relevant columns
    occurrences = pd.DataFrame()
    occurrences['latitude'] = pd.to_numeric(df['decimalLatitude'], errors='coerce')
    occurrences['longitude'] = pd.to_numeric(df['decimalLongitude'], errors='coerce')

    # Date handling
    if 'eventDate' in df.columns:
        occurrences['date'] = pd.to_datetime(df['eventDate'], errors='coerce')
    elif 'year' in df.columns:
        occurrences['year'] = pd.to_numeric(df['year'], errors='coerce')
        occurrences['month'] = pd.to_numeric(df.get('month', 6), errors='coerce')
        occurrences['day'] = pd.to_numeric(df.get('day', 15), errors='coerce')
        occurrences['date'] = pd.to_datetime(
            occurrences[['year', 'month', 'day']],
            errors='coerce'
        )

    # Clean data
    occurrences = occurrences.dropna(subset=['latitude', 'longitude'])
    occurrences = occurrences[
        (occurrences['latitude'] >= 5.9) & (occurrences['latitude'] <= 9.9) &
        (occurrences['longitude'] >= 79.4) & (occurrences['longitude'] <= 82.0)
        ]
    occurrences = occurrences.drop_duplicates(subset=['latitude', 'longitude', 'date'])

    # Fill missing dates
    import numpy as np
    missing_dates = occurrences['date'].isna()
    if missing_dates.any():
        np.random.seed(42)
        random_dates = pd.date_range('2020-01-01', '2024-12-31', periods=missing_dates.sum())
        occurrences.loc[missing_dates, 'date'] = random_dates

    # Create positive samples
    positive_samples = pd.DataFrame()
    positive_samples['latitude'] = occurrences['latitude']
    positive_samples['longitude'] = occurrences['longitude']
    positive_samples['date'] = occurrences['date']
    positive_samples['conflict'] = 1

    print(f"✓ Loaded {len(positive_samples)} positive samples from GBIF")
    print(f"  Date range: {positive_samples['date'].min()} to {positive_samples['date'].max()}")

    return positive_samples


if __name__ == '__main__':
    df = load_positive_samples()
    print(f"\nTotal: {len(df)} samples")
    print(df.head(10))