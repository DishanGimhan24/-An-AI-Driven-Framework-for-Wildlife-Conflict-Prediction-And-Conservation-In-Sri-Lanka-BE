"""
Machine Learning Model Training Script
Trains a Random Forest Classifier for collision prediction based on geographical features.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "dataset"
MODEL_PATH = BASE_DIR / "model"
DATASET_FILE = DATASET_PATH / "collision_data.csv"
MODEL_FILE = MODEL_PATH / "random_forest_collision_model.pkl"

def load_dataset():
    """Load the collision dataset from CSV file."""
    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dataset file not found at {DATASET_FILE}. "
            f"Please place your CSV file in {DATASET_PATH}/"
        )
    
    print(f"Loading dataset from {DATASET_FILE}...")
    df = pd.read_csv(DATASET_FILE)
    
    print(f"Dataset loaded successfully.")
    print(f"Dataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nDataset Info:")
    print(df.info())
    print(f"\nFirst few rows:")
    print(df.head())
    
    return df


def validate_dataset(df):
    """Validate that the dataset has all required columns."""
    required_columns = ['latitude', 'longitude', 'collision', 
                       'distance_to_forest', 'distance_to_railway', 'distance_to_water']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    print(f"✓ Dataset validation passed. All required columns present.")
    print(f"\nDataset Statistics:")
    print(f"Total records: {len(df)}")
    print(f"Collision points (1): {(df['collision'] == 1).sum()}")
    print(f"Non-collision points (0): {(df['collision'] == 0).sum()}")


def prepare_data(df):
    """Prepare features and target variable."""
    feature_columns = ['distance_to_forest', 'distance_to_railway', 'distance_to_water']
    
    X = df[feature_columns]
    y = df['collision']
    
    print(f"\nFeatures prepared (X shape: {X.shape})")
    print(f"Target prepared (y shape: {y.shape})")
    
    return X, y


def train_model(X, y):
    """Train the Random Forest Classifier model."""
    print(f"\nSplitting data into 80% training and 20% testing...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set size: {X_train.shape[0]}")
    print(f"Testing set size: {X_test.shape[0]}")
    
    print(f"\nTraining Random Forest Classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    print(f"✓ Model training completed.")
    
    return model, X_test, y_test


def evaluate_model(model, X_test, y_test):
    """Evaluate the trained model."""
    print(f"\nEvaluating model on test set...")
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n{'='*50}")
    print(f"MODEL ACCURACY: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"{'='*50}")
    
    print(f"\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Non-Collision', 'Collision']))
    
    print(f"\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    print(f"\nTrue Negatives: {cm[0][0]}")
    print(f"False Positives: {cm[0][1]}")
    print(f"False Negatives: {cm[1][0]}")
    print(f"True Positives: {cm[1][1]}")
    
    # Feature importance
    feature_columns = ['distance_to_forest', 'distance_to_railway', 'distance_to_water']
    feature_importance = model.feature_importances_
    
    print(f"\nFeature Importance:")
    for feature, importance in zip(feature_columns, feature_importance):
        print(f"  {feature}: {importance:.4f}")
    
    return accuracy


def save_model(model):
    """Save the trained model to disk."""
    # Ensure model directory exists
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSaving trained model to {MODEL_FILE}...")
    joblib.dump(model, MODEL_FILE)
    print(f"✓ Model saved successfully.")


def main():
    """Main training pipeline."""
    print("="*70)
    print("COLLISION PREDICTION MODEL TRAINING")
    print("="*70)
    
    try:
        # Load and validate dataset
        df = load_dataset()
        validate_dataset(df)
        
        # Prepare data
        X, y = prepare_data(df)
        
        # Train model
        model, X_test, y_test = train_model(X, y)
        
        # Evaluate model
        evaluate_model(model, X_test, y_test)
        
        # Save model
        save_model(model)
        
        print("\n" + "="*70)
        print("TRAINING PIPELINE COMPLETED SUCCESSFULLY")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error during training: {str(e)}")
        raise


if __name__ == "__main__":
    main()
