import os
import sys
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow import keras

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LSTM_MODEL_PATH, LSTM_SCALER_PATH, PLOTS_DIR
from ml_training.train_lstm_model import (
    load_lstm_training_data, create_sequences, split_data
)

sns.set_style("whitegrid")

# Load model and scaler
keras_path = LSTM_MODEL_PATH.replace('.h5', '.keras')
model = keras.models.load_model(keras_path)
scaler = joblib.load(LSTM_SCALER_PATH)

# Recreate test data
df = load_lstm_training_data()
X, y, _, _ = create_sequences(df, seq_length=30, forecast_days=7)
_, _, X_test, _, _, y_test = split_data(X, y)

# Scale
n_samples, n_timesteps, n_features = X_test.shape
X_test_scaled = scaler.transform(X_test.reshape(-1, n_features)).reshape(X_test.shape)

# Predict
y_pred = model.predict(X_test_scaled)

# Find samples with diverse risk levels
mean_risks = y_test.mean(axis=1)
print(f"Test set risk distribution: min={mean_risks.min():.3f}, max={mean_risks.max():.3f}")
print(f"Samples > 0.3: {(mean_risks > 0.3).sum()}")
print(f"Samples > 0.5: {(mean_risks > 0.5).sum()}")
print(f"Samples > 0.7: {(mean_risks > 0.7).sum()}")

# Pick 3 diverse samples: low risk, medium risk, high risk
low_idx = np.argsort(mean_risks)[len(mean_risks)//10]  # ~10th percentile
med_idx = np.argsort(mean_risks)[len(mean_risks)//2]   # median
high_idx = np.argsort(mean_risks)[-1]                  # highest

selected_indices = [low_idx, med_idx, high_idx]
sample_labels = ['Low-Risk Period', 'Medium-Risk Period', 'High-Risk Period']

# Plot
fig, axes = plt.subplots(3, 1, figsize=(12, 10))
days = np.arange(1, 8)

for i, (idx, label) in enumerate(zip(selected_indices, sample_labels)):
    ax = axes[i]
    actual = y_test[idx]
    predicted = y_pred[idx]

    # Calculate sample metrics
    mae = np.mean(np.abs(actual - predicted))
    corr = np.corrcoef(actual, predicted)[0, 1] if actual.std() > 0 else 0

    ax.plot(days, actual, 'o-', label='Actual Risk',
            color='darkred', linewidth=3, markersize=10)
    ax.plot(days, predicted, 's--', label='Predicted Risk',
            color='darkorange', linewidth=3, markersize=8)

    ax.fill_between(days, actual, predicted, alpha=0.25, color='gray')

    ax.set_xlabel('Forecast Day', fontweight='bold', fontsize=12)
    ax.set_ylabel('Conflict Risk Score', fontweight='bold', fontsize=12)
    ax.set_title(f'Sample {i + 1}: {label}  (MAE={mae:.3f}, Corr={corr:.3f})',
                 fontweight='bold', fontsize=13)
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)

    # Dynamic y-limits based on data
    data_max = max(actual.max(), predicted.max())
    data_min = min(actual.min(), predicted.min())
    padding = max(0.1, data_max * 0.15)
    ax.set_ylim(max(-0.05, data_min - padding), min(1.05, data_max + padding))
    ax.set_xticks(days)

plt.suptitle('LSTM 7-Day Risk Forecast: Performance Across Risk Levels',
             fontsize=16, fontweight='bold', y=1.00)
plt.tight_layout()

output_path = os.path.join(PLOTS_DIR, 'lstm_forecast_comparison_diverse.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Saved: {output_path}")
plt.close()
