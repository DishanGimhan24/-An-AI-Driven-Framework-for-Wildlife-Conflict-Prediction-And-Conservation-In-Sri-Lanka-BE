import os
import sys

import pandas as pd

from load_positives import load_positive_samples
from generate_negatives import generate_negative_samples
from data_processing.feature_extractor import feature_extractor
from data_processing.data_loader import data_loader
from config import TRAINING_DATA_PATH, TRAINING_OUTPUT_DIR


def create_training_data():
    """
    Create complete training dataset with features
    """
    print("=" * 60)
    print("Creating Training Dataset")
    print("=" * 60 + "\n")

    # Load datasets first
    print("Step 1: Loading datasets...")
    data_loader.load_all()
    print()

    # Load positive samples
    print("Step 2: Loading positive samples (conflicts)...")
    positive_df = load_positive_samples()
    print(f"Positive samples: {len(positive_df)}")
    print()

    # Generate negative samples
    print("Step 3: Generating negative samples...")
    n_negatives = len(positive_df)  # Balance the dataset
    negative_df = generate_negative_samples(n_negatives)
    print(f"Negative samples: {len(negative_df)}")
    print()

    # Combine samples
    print("Step 4: Combining samples...")
    all_samples = pd.concat([positive_df, negative_df], ignore_index=True)
    print(f"Total samples: {len(all_samples)}")
    print()

    # Extract features for each sample
    print("Step 5: Extracting features...")
    print("This may take a while...")

    feature_list = []
    labels = []

    for idx, row in all_samples.iterrows():
        if idx % 100 == 0:
            print(f"  Processing sample {idx + 1}/{len(all_samples)}")

        try:
            # Convert date to string
            date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d')

            # Extract features
            features = feature_extractor.extract_features(
                row['latitude'],
                row['longitude'],
                date_str
            )

            feature_list.append(features)
            labels.append(row['conflict'])

        except Exception as e:
            print(f"  ⚠ Error processing sample {idx}: {e}")
            continue

    # Create feature dataframe
    print("\nStep 6: Creating feature dataframe...")
    feature_df = pd.DataFrame(feature_list)
    feature_df['conflict'] = labels

    # Save to CSV
    os.makedirs(TRAINING_OUTPUT_DIR, exist_ok=True)
    feature_df.to_csv(TRAINING_DATA_PATH, index=False)

    print(f"\n✓ Training data saved to: {TRAINING_DATA_PATH}")
    print(f"  Shape: {feature_df.shape}")
    print(f"  Features: {len(feature_df.columns) - 1}")
    print(f"  Positive samples: {feature_df['conflict'].sum()}")
    print(f"  Negative samples: {len(feature_df) - feature_df['conflict'].sum()}")

    # Show feature summary
    print("\nFeature summary:")
    print(feature_df.describe())

    return feature_df


if __name__ == '__main__':
    df = create_training_data()