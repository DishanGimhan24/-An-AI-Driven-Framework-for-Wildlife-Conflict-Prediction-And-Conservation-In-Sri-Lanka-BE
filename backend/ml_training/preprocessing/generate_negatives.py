import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def generate_negative_samples(n_samples):
    """
    Generate negative samples - ONLY extreme safe zones
    Far from elephant habitats, high population, coastal/urban only
    """
    print(f"Generating {n_samples} negative samples (extreme safe zones)...")

    np.random.seed(42)
    negative_samples = []

    # ONLY major urban/coastal centers - NO overlap with elephant zones
    safe_zones = [
        # Western Province - Urban belt (NO elephants)
        {'name': 'Colombo Metro', 'lat': (6.88, 6.96), 'lon': (79.85, 79.89), 'weight': 0.25},
        {'name': 'Gampaha Urban', 'lat': (7.08, 7.12), 'lon': (79.99, 80.03), 'weight': 0.15},
        {'name': 'Negombo Beach', 'lat': (7.20, 7.23), 'lon': (79.84, 79.87), 'weight': 0.12},
        {'name': 'Kalutara Coastal', 'lat': (6.58, 6.60), 'lon': (79.95, 79.98), 'weight': 0.10},

        # Southern Coast (Dense population, NO elephants)
        {'name': 'Galle Fort', 'lat': (6.03, 6.05), 'lon': (80.21, 80.23), 'weight': 0.12},
        {'name': 'Matara Beach', 'lat': (5.94, 5.96), 'lon': (80.54, 80.56), 'weight': 0.10},

        # Northern Peninsula (Far from elephants)
        {'name': 'Jaffna Peninsula', 'lat': (9.66, 9.69), 'lon': (80.01, 80.04), 'weight': 0.10},

        # Eastern Coast (Urban only)
        {'name': 'Batticaloa Town', 'lat': (7.72, 7.74), 'lon': (81.69, 81.71), 'weight': 0.06},
    ]

    # Generate samples
    for zone in safe_zones:
        zone_samples = int(n_samples * zone['weight'])

        for _ in range(zone_samples):
            lat = np.random.uniform(zone['lat'][0], zone['lat'][1])
            lon = np.random.uniform(zone['lon'][0], zone['lon'][1])

            year = np.random.choice([2020, 2021, 2022, 2023, 2024])
            month = np.random.randint(1, 13)
            day = np.random.randint(1, 29)

            date = pd.Timestamp(year=year, month=month, day=day)

            negative_samples.append({
                'latitude': lat,
                'longitude': lon,
                'date': date,
                'conflict': 0,
                'zone': zone['name']
            })

    # Fill remaining
    remaining = n_samples - len(negative_samples)
    if remaining > 0:
        # Use only Colombo for remaining samples
        colombo_zone = safe_zones[0]
        for _ in range(remaining):
            lat = np.random.uniform(colombo_zone['lat'][0], colombo_zone['lat'][1])
            lon = np.random.uniform(colombo_zone['lon'][0], colombo_zone['lon'][1])

            year = np.random.choice([2020, 2021, 2022, 2023, 2024])
            month = np.random.randint(1, 13)
            day = np.random.randint(1, 29)

            date = pd.Timestamp(year=year, month=month, day=day)

            negative_samples.append({
                'latitude': lat,
                'longitude': lon,
                'date': date,
                'conflict': 0,
                'zone': colombo_zone['name']
            })

    df = pd.DataFrame(negative_samples)

    print(f"✓ Generated {len(df)} extreme safe zone samples")
    print(f"  All in coastal/urban centers ONLY")

    print("\nDistribution:")
    for zone_name, count in df['zone'].value_counts().items():
        print(f"  {zone_name}: {count} samples")

    return df


if __name__ == '__main__':
    df = generate_negative_samples(1287)
    print(f"\nTotal: {len(df)} samples")