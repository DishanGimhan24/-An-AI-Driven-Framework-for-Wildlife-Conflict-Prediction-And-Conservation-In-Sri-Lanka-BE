"""
Phase 2: ML Model Training
Trains model to predict elephant presence probability at any location/time
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import xgboost as xgb
import joblib
import json
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("PHASE 2: ML MODEL TRAINING")
print("="*70)

# ============================================================================
# 1. LOAD DATA
# ============================================================================

print("\n[1/5] Loading training data...")
df = pd.read_csv('./outputs/cleaned_data.csv')
df['Datetime_standard'] = pd.to_datetime(
    df['Datetime_standard'], errors='coerce')

print(f"   Loaded: {len(df):,} records")
print(
    f"   Positive samples (elephant present): {(df['ElephantPresent'] == 1).sum():,}")
print(
    f"   Negative samples (not present): {(df['ElephantPresent'] == 0).sum():,}")

# ============================================================================
# 2. PREPARE FEATURES
# ============================================================================

print("\n[2/5] Preparing features...")

# Identify one-hot LandCover columns
lc_columns = [col for col in df.columns if col.startswith('LC_')]
print(f"   Found LandCover columns: {lc_columns}")

# Base feature columns
# NO lat/lon - model should learn habitat patterns, not memorize coordinates
# NO DistanceToNearestNode - that's data leakage
feature_columns = [
    'Hour',
    'Month',
    'DayOfWeek',
    'NDVI_normalized',
    'Elevation',
    'RoadDistance',
    'WaterDistance',
    'HumanDistance',
    'Protected'
]

# Add one-hot LandCover columns (instead of numeric LandCover2)
feature_columns.extend(lc_columns)

# Handle categorical features
categorical_features = ['Season', 'TimeOfDay']
label_encoders = {}

for col in categorical_features:
    if col in df.columns:
        le = LabelEncoder()
        df[col + '_encoded'] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le
        feature_columns.append(col + '_encoded')

print(f"   Feature columns ({len(feature_columns)}):")
for col in feature_columns:
    print(f"      - {col}")

# Prepare X and y
X = df[feature_columns].copy()

# Fill NaN values with median for numeric columns
for col in X.columns:
    if X[col].dtype in ['float64', 'int64']:
        X[col] = X[col].fillna(X[col].median())
    else:
        X[col] = X[col].fillna(0)

y = df['ElephantPresent']

print(f"\n   Total features: {len(feature_columns)}")
print(f"   Total samples: {len(X):,}")

# ============================================================================
# 3. TRAIN/TEST SPLIT
# ============================================================================

print("\n[3/5] Splitting data...")

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print(f"   Training set: {len(X_train):,}")
print(f"   Test set: {len(X_test):,}")

# NOTE: No scaling! XGBoost is tree-based and doesn't need it
print(f"   Scaling: SKIPPED (XGBoost doesn't require feature scaling)")

# ============================================================================
# 4. TRAIN MODEL
# ============================================================================

print("\n[4/5] Training XGBoost model...")

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric='logloss',
    use_label_encoder=False
)

# Train with early stopping
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

print("   Model trained")

# ============================================================================
# 5. EVALUATE MODEL
# ============================================================================

print("\n[5/5] Evaluating model...")

# Predictions
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

# Metrics
accuracy = (y_pred == y_test).mean()
roc_auc = roc_auc_score(y_test, y_pred_proba)

print(f"\n   Accuracy: {accuracy:.4f}")
print(f"   ROC-AUC: {roc_auc:.4f}")

print(f"\n   Classification Report:")
report = classification_report(y_test, y_pred, output_dict=True)
print(f"   Precision (Elephant): {report['1']['precision']:.3f}")
print(f"   Recall (Elephant): {report['1']['recall']:.3f}")
print(f"   F1-Score (Elephant): {report['1']['f1-score']:.3f}")

# Confusion matrix
cm = confusion_matrix(y_test, y_pred)
print(f"\n   Confusion Matrix:")
print(f"   [[TN={cm[0, 0]}, FP={cm[0, 1]}]")
print(f"    [FN={cm[1, 0]}, TP={cm[1, 1]}]]")

# Feature importance
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\n   Top 10 Most Important Features:")
for idx, row in feature_importance.head(10).iterrows():
    print(f"   {row['feature']}: {row['importance']:.4f}")

# ============================================================================
# SAVE MODEL
# ============================================================================

print("\n" + "="*70)
print("SAVING MODEL")
print("="*70)

# Save model
joblib.dump(model, './outputs/elephant_presence_model.pkl')
print("   Saved: elephant_presence_model.pkl")

# Save label encoders
joblib.dump(label_encoders, './outputs/label_encoders.pkl')
print("   Saved: label_encoders.pkl")

# Save feature columns
joblib.dump(feature_columns, './outputs/feature_columns.pkl')
print("   Saved: feature_columns.pkl")

# Save LandCover columns list (for API to know which ones exist)
joblib.dump(lc_columns, './outputs/landcover_columns.pkl')
print("   Saved: landcover_columns.pkl")

# Save metrics
metrics = {
    'accuracy': float(accuracy),
    'roc_auc': float(roc_auc),
    'classification_report': {
        k: {kk: float(vv) if isinstance(vv, (int, float)) else vv
            for kk, vv in v.items()} if isinstance(v, dict) else v
        for k, v in report.items()
    },
    'confusion_matrix': cm.tolist(),
    'feature_importance': feature_importance.to_dict('records'),
    'notes': {
        'DistanceToNearestNode': 'EXCLUDED from training (data leakage)',
        'LandCover': 'One-hot encoded',
        'Scaling': 'Not applied (XGBoost)'
    }
}

with open('./outputs/model_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
print("   Saved: model_metrics.json")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*70)
print("MODEL TRAINING COMPLETE")
print("="*70)

print(f"\nModel Performance:")
print(f"  Accuracy: {accuracy:.4f}")
print(f"  ROC-AUC: {roc_auc:.4f}")

print(f"\nModel Files:")
print(f"  1. elephant_presence_model.pkl - Trained XGBoost model")
print(f"  2. label_encoders.pkl - Categorical encoders")
print(f"  3. feature_columns.pkl - Feature list")
print(f"  4. landcover_columns.pkl - LandCover one-hot columns")
print(f"  5. model_metrics.json - Performance metrics")
