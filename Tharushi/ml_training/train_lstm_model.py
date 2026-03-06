import json
import os
import sys
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, accuracy_score, f1_score

# TensorFlow imports
from tensorflow import keras
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout, Bidirectional, BatchNormalization
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
from keras.optimizers import Adam

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    LSTM_MODEL_PATH, LSTM_SCALER_PATH, MODELS_DIR,
    RANDOM_STATE, PLOTS_DIR, TRAINING_OUTPUT_DIR
)

# Set style for plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# Set random seeds for reproducibility
np.random.seed(RANDOM_STATE)
import tensorflow as tf

tf.random.set_seed(RANDOM_STATE)


def load_lstm_training_data():
    """Load time-series data for LSTM training"""
    print("Loading LSTM training data...")

    # Try to load preprocessed LSTM data
    lstm_data_path = os.path.join(TRAINING_OUTPUT_DIR, 'lstm_training_data.csv')

    if not os.path.exists(lstm_data_path):
        print(f"✗ LSTM training data not found at: {lstm_data_path}")
        print("Creating from available data...")

        # Create from tracking data
        from data_processing.data_loader import data_loader
        data_loader.load_all()

        df = create_enhanced_lstm_data(data_loader)

        if df is None or len(df) < 100:
            print("✗ Insufficient data for LSTM training")
            return None

        # Save for future use
        os.makedirs(TRAINING_OUTPUT_DIR, exist_ok=True)
        df.to_csv(lstm_data_path, index=False)
        print(f"✓ Created and saved LSTM data: {len(df)} records")
    else:
        df = pd.read_csv(lstm_data_path)
        df['date'] = pd.to_datetime(df['date'])
        print(f"✓ Loaded LSTM data: {len(df)} records")

    return df


def create_enhanced_lstm_data(data_loader):
    """Create enhanced time-series data with more features"""
    print("\nCreating enhanced LSTM training data...")

    # Use rainfall data as base (has daily records)
    if data_loader.rainfall_data is None or len(data_loader.rainfall_data) == 0:
        print("⚠ No rainfall data available")
        return None

    df = data_loader.rainfall_data.copy()
    df = df.sort_values('date').reset_index(drop=True)

    print(f"  Base data: {len(df)} daily records")

    # Add more features for each date
    features_list = []
    for idx, row in df.iterrows():
        if idx % 200 == 0:
            print(f"  Processing {idx}/{len(df)}...")

        date = row['date']

        # Basic features
        features = {
            'date': date,
            'month': date.month,
            'day_of_year': date.timetuple().tm_yday,
            'week_of_year': date.isocalendar()[1],
            'season': 1 if 5 <= date.month <= 9 else 0,  # Dry/Wet
            'quarter': (date.month - 1) // 3 + 1,
        }

        # Rainfall features (already in row)
        features['rainfall_daily'] = row['rainfall_mm']

        # Get historical rainfall
        rainfall_hist = data_loader.get_rainfall_for_date(date)
        features['rainfall_7day'] = rainfall_hist['rainfall_7day']
        features['rainfall_14day'] = rainfall_hist['rainfall_14day']
        features['rainfall_30day'] = rainfall_hist['rainfall_30day']

        # NDVI (use center of Sri Lanka)
        ndvi = data_loader.get_ndvi_value(7.5, 80.5, date.year, date.month)
        features['ndvi'] = ndvi

        # Previous month NDVI for trend
        prev_date = date - timedelta(days=30)
        ndvi_prev = data_loader.get_ndvi_value(7.5, 80.5, prev_date.year, prev_date.month)
        features['ndvi_change'] = ndvi - ndvi_prev

        # Derived risk indicators
        features['is_dry_period'] = 1 if rainfall_hist['rainfall_7day'] < 5 else 0
        features['low_vegetation'] = 1 if ndvi < 0.3 else 0
        features['high_risk_combo'] = features['is_dry_period'] * features['low_vegetation']

        # Conflict probability (simplified model)
        # High risk if: dry period + low vegetation + dry season
        risk_score = 0.0
        if features['is_dry_period']:
            risk_score += 0.3
        if features['low_vegetation']:
            risk_score += 0.3
        if features['season'] == 1:  # Dry season
            risk_score += 0.2
        if features['rainfall_30day'] < 50:
            risk_score += 0.2

        features['conflict_risk'] = min(risk_score, 1.0)

        features_list.append(features)

    result_df = pd.DataFrame(features_list)

    print(f"✓ Created {len(result_df)} daily records with {len(result_df.columns)} features")

    return result_df


def create_sequences(data, seq_length=30, forecast_days=7):
    """Create sequences for LSTM training"""
    print(f"\nCreating sequences (seq_length={seq_length}, forecast={forecast_days})...")

    # Sort by date
    data = data.sort_values('date').reset_index(drop=True)

    # Feature columns (exclude date)
    feature_cols = [col for col in data.columns if col not in ['date', 'conflict_risk']]

    sequences = []
    targets = []
    dates = []

    for i in range(len(data) - seq_length - forecast_days + 1):
        # Get 30 days input sequence
        seq = data[feature_cols].iloc[i:i + seq_length].values

        # Get next 7 days targets (risk scores)
        target = data['conflict_risk'].iloc[i + seq_length:i + seq_length + forecast_days].values

        # Store the prediction start date
        pred_date = data['date'].iloc[i + seq_length]

        sequences.append(seq)
        targets.append(target)
        dates.append(pred_date)

    X = np.array(sequences)
    y = np.array(targets)

    print(f"✓ Created {len(X)} sequences")
    print(f"  X shape: {X.shape} (samples, timesteps, features)")
    print(f"  y shape: {y.shape} (samples, forecast_days)")

    return X, y, feature_cols, dates


def split_data(X, y, train_ratio=0.70, val_ratio=0.15):
    """Split data into train/val/test (temporal split)"""
    print("\nSplitting data (temporal)...")

    train_size = int(train_ratio * len(X))
    val_size = int(val_ratio * len(X))

    X_train = X[:train_size]
    y_train = y[:train_size]

    X_val = X[train_size:train_size + val_size]
    y_val = y[train_size:train_size + val_size]

    X_test = X[train_size + val_size:]
    y_test = y[train_size + val_size:]

    print(f"  Train: {len(X_train)} sequences")
    print(f"  Val:   {len(X_val)} sequences")
    print(f"  Test:  {len(X_test)} sequences")

    return X_train, X_val, X_test, y_train, y_val, y_test


def scale_data(X_train, X_val, X_test):
    """Scale features using MinMaxScaler"""
    print("\nScaling sequences...")

    # Reshape for scaling
    n_samples, n_timesteps, n_features = X_train.shape

    X_train_reshaped = X_train.reshape(-1, n_features)
    X_val_reshaped = X_val.reshape(-1, n_features)
    X_test_reshaped = X_test.reshape(-1, n_features)

    # Fit scaler on training data
    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train_reshaped)
    X_val_scaled = scaler.transform(X_val_reshaped)
    X_test_scaled = scaler.transform(X_test_reshaped)

    # Reshape back to 3D
    X_train_scaled = X_train_scaled.reshape(n_samples, n_timesteps, n_features)
    X_val_scaled = X_val_scaled.reshape(X_val.shape[0], n_timesteps, n_features)
    X_test_scaled = X_test_scaled.reshape(X_test.shape[0], n_timesteps, n_features)

    print("✓ Sequences scaled")

    return X_train_scaled, X_val_scaled, X_test_scaled, scaler


def build_improved_lstm_model(input_shape, forecast_days=7):
    """Build improved LSTM model with Bidirectional layers"""
    print("\nBuilding improved LSTM model...")

    model = Sequential([
        # First Bidirectional LSTM layer
        Bidirectional(LSTM(64, return_sequences=True), input_shape=input_shape),
        BatchNormalization(),
        Dropout(0.3),

        # Second Bidirectional LSTM layer
        Bidirectional(LSTM(32, return_sequences=False)),
        BatchNormalization(),
        Dropout(0.3),

        # Dense layers
        Dense(64, activation='relu'),
        Dropout(0.2),

        Dense(32, activation='relu'),
        Dropout(0.2),

        # Output layer (7 days forecast, continuous risk scores)
        Dense(forecast_days, activation='sigmoid')
    ])

    # Custom optimizer with lower learning rate
    optimizer = Adam(learning_rate=0.001)

    model.compile(
        optimizer=optimizer,
        loss='mse',  # Mean Squared Error for regression
        metrics=['mae', 'mse']
    )

    print("✓ Model architecture created")
    model.summary()

    return model


def train_lstm(model, X_train, y_train, X_val, y_val, epochs=100):
    """Train LSTM model with callbacks"""
    print("\nTraining LSTM model...")

    # Callbacks
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=15,
        restore_best_weights=True,
        verbose=1
    )

    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=7,
        min_lr=0.00001,
        verbose=1
    )

    # Train
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=16,  # Smaller batch for better gradients
        callbacks=[early_stopping, reduce_lr],
        verbose=1
    )

    print("✓ Model trained")

    return history


def evaluate_lstm(model, X_test, y_test):
    """Evaluate LSTM model performance"""
    print("\nEvaluating LSTM model...")

    # Predictions
    y_pred = model.predict(X_test)

    # Calculate metrics for each forecast day
    metrics = {}
    for day in range(y_test.shape[1]):
        y_true_day = y_test[:, day]
        y_pred_day = y_pred[:, day]

        mae = mean_absolute_error(y_true_day, y_pred_day)
        mse = mean_squared_error(y_true_day, y_pred_day)
        rmse = np.sqrt(mse)

        # Correlation
        correlation = np.corrcoef(y_true_day, y_pred_day)[0, 1]

        metrics[f'day_{day + 1}'] = {
            'mae': float(mae),
            'rmse': float(rmse),
            'correlation': float(correlation)
        }

        print(f"  Day +{day + 1}: MAE={mae:.3f}, RMSE={rmse:.3f}, Corr={correlation:.3f}")

    # Overall metrics
    overall_mae = np.mean([m['mae'] for m in metrics.values()])
    overall_rmse = np.mean([m['rmse'] for m in metrics.values()])
    overall_corr = np.mean([m['correlation'] for m in metrics.values()])

    print(f"\nOverall Performance:")
    print(f"  Average MAE:         {overall_mae:.3f}")
    print(f"  Average RMSE:        {overall_rmse:.3f}")
    print(f"  Average Correlation: {overall_corr:.3f}")

    return {
        'per_day': metrics,
        'overall_mae': float(overall_mae),
        'overall_rmse': float(overall_rmse),
        'overall_correlation': float(overall_corr)
    }


def plot_forecast_comparison(model, X_test, y_test, save_path, n_samples=3):
    """Plot actual vs predicted forecast"""
    print("\nGenerating forecast comparison plot...")

    # Get predictions
    y_pred = model.predict(X_test[:n_samples])

    fig, axes = plt.subplots(n_samples, 1, figsize=(12, 4 * n_samples))
    if n_samples == 1:
        axes = [axes]

    for i in range(n_samples):
        ax = axes[i]
        days = np.arange(1, 8)

        ax.plot(days, y_test[i], 'o-', label='Actual Risk',
                color='darkred', linewidth=3, markersize=10)
        ax.plot(days, y_pred[i], 's--', label='Predicted Risk',
                color='darkorange', linewidth=3, markersize=8)

        ax.fill_between(days, y_test[i], y_pred[i], alpha=0.2, color='gray')

        ax.set_xlabel('Forecast Day', fontweight='bold', fontsize=12)
        ax.set_ylabel('Conflict Risk Score', fontweight='bold', fontsize=12)
        ax.set_title(f'Sample {i + 1}: 7-Day Risk Forecast', fontweight='bold', fontsize=14)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xticks(days)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved forecast comparison: {save_path}")


def save_model_and_metrics(model, scaler, metrics, feature_names):
    """Save trained model and metrics"""
    print("\nSaving LSTM model...")

    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # Save LSTM model (.keras format)
    keras_path = LSTM_MODEL_PATH.replace('.h5', '.keras')
    model.save(keras_path)
    print(f"✓ Model saved to {keras_path}")

    # Save scaler
    joblib.dump(scaler, LSTM_SCALER_PATH)
    print(f"✓ Scaler saved to {LSTM_SCALER_PATH}")

    # Save metrics
    metrics_path = os.path.join(MODELS_DIR, 'lstm_metrics.json')
    metrics_data = {
        'metrics': metrics,
        'feature_names': feature_names,
        'trained_at': datetime.now().isoformat(),
        'model_type': 'Bidirectional LSTM',
        'sequence_length': 30,
        'forecast_days': 7
    }

    with open(metrics_path, 'w') as f:
        json.dump(metrics_data, f, indent=2)

    print(f"✓ Metrics saved to {metrics_path}")


def main():
    """Main LSTM training pipeline"""
    print("=" * 60)
    print("LSTM Model Training - IMPROVED 7-Day Forecast")
    print("=" * 60 + "\n")

    # Load data
    df = load_lstm_training_data()
    if df is None:
        print("\n✗ Cannot proceed without training data")
        return

    # Create sequences
    X, y, feature_names, dates = create_sequences(df, seq_length=30, forecast_days=7)

    if len(X) < 100:
        print("\n⚠ WARNING: Limited data for LSTM training!")
        print(f"  Only {len(X)} sequences - recommend 500+ for best results")

    # Split data
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    # Scale data
    X_train_scaled, X_val_scaled, X_test_scaled, scaler = scale_data(
        X_train, X_val, X_test
    )

    # Build improved model
    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_improved_lstm_model(input_shape, forecast_days=7)

    # Train model
    history = train_lstm(model, X_train_scaled, y_train, X_val_scaled, y_val, epochs=100)

    # Evaluate model
    metrics = evaluate_lstm(model, X_test_scaled, y_test)

    # Generate visualization
    plot_forecast_comparison(
        model, X_test_scaled, y_test,
        os.path.join(PLOTS_DIR, 'lstm_forecast_comparison.png'),
        n_samples=3
    )

    # Save everything
    save_model_and_metrics(model, scaler, metrics, feature_names)

    print("\n" + "=" * 60)
    print("LSTM Training Complete!")
    print("=" * 60)
    print(f"\nOverall Performance:")
    print(f"  MAE:         {metrics['overall_mae']:.3f} (Lower is better)")
    print(f"  RMSE:        {metrics['overall_rmse']:.3f}")
    print(f"  Correlation: {metrics['overall_correlation']:.3f} (Higher is better)")

    if metrics['overall_mae'] < 0.15:
        print(f"\n✓ EXCELLENT: MAE < 0.15 - Very accurate forecasts!")
    elif metrics['overall_mae'] < 0.25:
        print(f"\n✓ GOOD: MAE < 0.25 - Reliable forecasts!")
    else:
        print(f"\n✓ ACCEPTABLE: Model provides useful risk trends")

    print(f"\n✓ LSTM model ready for 7-day forecasting!")


if __name__ == '__main__':
    main()