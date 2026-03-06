import pandas as pd
import joblib
from sklearn.cluster import DBSCAN

# Load original data
df = pd.read_csv("../data/collision.csv")

df["animal_type"] = df["animal_type"].astype("category").cat.codes
df["vehicle_type"] = df["vehicle_type"].astype("category").cat.codes

# ⚠️ MUST MATCH TRAINING FEATURES
features = [
    "rain",
    "water_distance",
    "NDVI",
    "distance_to_forest",
    "animal_type",
    "vehicle_type"
]

# Load saved model
model = joblib.load("model/risk_model.pkl")

# Risk score (0–1)
df["risk_score"] = model.predict_proba(df[features])[:, 1]

# Risk level
def risk_level(s):
    if s >= 0.7:
        return "HIGH"
    elif s >= 0.4:
        return "MEDIUM"
    return "LOW"

df["risk_level"] = df["risk_score"].apply(risk_level)

# Cluster ONLY HIGH risk points
high = df[df["risk_level"] == "HIGH"].copy()

if len(high) > 0:
    coords = high[["latitude", "longitude"]].values
    db = DBSCAN(eps=0.02, min_samples=5).fit(coords)
    high["cluster_id"] = db.labels_
else:
    high["cluster_id"] = []

# Merge cluster_id back
df = df.merge(
    high[["latitude", "longitude", "cluster_id"]],
    on=["latitude", "longitude"],
    how="left"
)

# Save output for frontend
df.to_csv("../frontend/dashboard/public/risk_map_data.csv", index=False)
print("✅ risk_map_data.csv generated for frontend")
