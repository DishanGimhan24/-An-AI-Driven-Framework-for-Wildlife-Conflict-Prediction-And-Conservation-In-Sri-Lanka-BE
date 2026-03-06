import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score

# ==============================
# 1. LOAD DATA
# ==============================
df = pd.read_csv("../data/collision.csv")

# Encode categoricals
df["animal_type"] = df["animal_type"].astype("category").cat.codes
df["vehicle_type"] = df["vehicle_type"].astype("category").cat.codes

# ==============================
# 2. CREATE SPATIAL BLOCKS (KEY FIX)
# ==============================
# Grid Sri Lanka into spatial blocks (~20–30km)
df["lat_block"] = (df["latitude"] // 0.25).astype(int)
df["lon_block"] = (df["longitude"] // 0.25).astype(int)
df["spatial_block"] = df["lat_block"].astype(str) + "_" + df["lon_block"].astype(str)

# Hold out 20% of blocks for testing
blocks = df["spatial_block"].unique()
np.random.seed(42)
test_blocks = np.random.choice(blocks, size=int(0.2 * len(blocks)), replace=False)

train_df = df[~df["spatial_block"].isin(test_blocks)]
test_df  = df[df["spatial_block"].isin(test_blocks)]

# ==============================
# 3. FEATURES (NO LAT/LON)
# ==============================
features = [
    "rain",
    "water_distance",
    "NDVI",
    "distance_to_forest",
    "animal_type",
    "vehicle_type"
]

X_train_pos = train_df[features]
y_train_pos = np.ones(len(X_train_pos))

X_test_pos  = test_df[features]
y_test_pos  = np.ones(len(X_test_pos))

# ==============================
# 4. BACKGROUND SAMPLES (TRAIN ONLY)
# ==============================
bg = pd.DataFrame({
    "rain": np.random.uniform(df.rain.min(), df.rain.max(), len(X_train_pos)),
    "water_distance": np.random.uniform(300, 5000, len(X_train_pos)),
    "NDVI": np.random.uniform(0.25, 0.7, len(X_train_pos)),
    "distance_to_forest": np.random.uniform(500, 8000, len(X_train_pos)),
    "animal_type": 0,
    "vehicle_type": 0
})

bg = bg.sample(frac=0.5, random_state=42)

X_train = pd.concat([X_train_pos, bg], ignore_index=True)
y_train = np.concatenate([y_train_pos, np.zeros(len(bg))])

# ==============================
# 5. TRAIN MODEL
# ==============================
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    random_state=42
)
model.fit(X_train, y_train)

# ==============================
# 6. EVALUATION (REALISTIC)
# ==============================
# Test against unseen spatial regions
X_test = X_test_pos
y_test = y_test_pos

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

acc = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

print("\n📊 MODEL EVALUATION (Spatial Hold-out)")
print("--------------------------------")
print(f"Accuracy : {round(acc*100, 1)}%")

# ==============================
# 7. SAVE MODEL
# ==============================
joblib.dump(model, "model/risk_model.pkl")
print("✅ Model trained & saved")
