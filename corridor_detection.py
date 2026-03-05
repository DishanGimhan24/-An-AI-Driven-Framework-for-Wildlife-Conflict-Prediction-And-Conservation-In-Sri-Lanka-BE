"""
Phase 1: Corridor Network Detection
Identifies elephant movement corridors as network of nodes and paths
"""

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import json
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("PHASE 1: CORRIDOR NETWORK DETECTION")
print("="*70)

# ============================================================================
# 1. LOAD ELEPHANT DATA
# ============================================================================

print("\n[1/6] Loading elephant GPS data...")
df = pd.read_csv('./outputs/elephant_data.csv')
df['Datetime_standard'] = pd.to_datetime(df['Datetime_standard'])
df = df.sort_values(['EleID', 'Datetime_standard'])

print(f"   Loaded: {len(df):,} elephant GPS points")
print(f"   Elephants: {df['Name'].nunique()}")
print(
    f"   Date range: {df['Datetime_standard'].min()} to {df['Datetime_standard'].max()}")

# ============================================================================
# 2. CREATE NODES (DBSCAN CLUSTERING WITH HAVERSINE)
# ============================================================================

print("\n[2/6] Creating nodes (high-use zones)...")

# Prepare coordinates for clustering (convert to radians for haversine)
coords_radians = np.radians(df[['latitude', 'longitude']].values)

# DBSCAN with haversine metric
# eps in radians: 0.5km / 6371km = 0.0000785 radians (approx 500m radius)
# Using 500m as cluster radius for tighter, more precise zones
eps_km = 0.5
eps_radians = eps_km / 6371.0

dbscan = DBSCAN(
    eps=eps_radians,
    min_samples=5,  # Lower threshold for more clusters
    metric='haversine',
    algorithm='ball_tree'
)
df['node_id'] = dbscan.fit_predict(coords_radians)

# Remove noise points (node_id = -1)
df_clustered = df[df['node_id'] != -1].copy()
noise_count = (df['node_id'] == -1).sum()

print(f"   Clustering parameters:")
print(f"      eps: {eps_km}km ({eps_radians:.6f} radians)")
print(f"      min_samples: 5")
print(f"   Clusters found: {df['node_id'].max() + 1}")
print(f"   Noise points: {noise_count:,} ({noise_count/len(df)*100:.1f}%)")
print(f"   Clustered points: {len(df_clustered):,}")

# Calculate node characteristics
nodes = []
for node_id in sorted(df_clustered['node_id'].unique()):
    node_data = df_clustered[df_clustered['node_id'] == node_id]

    # Get active hours (top 3)
    active_hours = node_data['Hour'].value_counts().head(3).index.tolist()

    # Calculate actual radius using haversine
    center_lat = node_data['latitude'].mean()
    center_lon = node_data['longitude'].mean()

    def haversine_dist(lat1, lon1, lat2, lon2):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    # Calculate average distance from center (radius)
    distances = node_data.apply(
        lambda row: haversine_dist(
            center_lat, center_lon, row['latitude'], row['longitude']),
        axis=1
    )

    node = {
        'node_id': int(node_id),
        'center_lat': float(center_lat),
        'center_lon': float(center_lon),
        'radius_meters': float(distances.mean()),
        'elephant_count': int(node_data['Name'].nunique()),
        'sighting_count': int(len(node_data)),
        'elephants': node_data['Name'].unique().tolist(),
        'active_hours': [int(h) for h in active_hours],
        'avg_ndvi': float(node_data['NDVI_normalized'].mean()),
        'avg_human_distance': float(node_data['HumanDistance'].mean()),
        'protected': int(node_data['Protected'].mode()[0]) if len(node_data) > 0 else 0,
        'land_cover': float(node_data['LandCover2'].mode()[0]) if len(node_data) > 0 else 10.0
    }
    nodes.append(node)

print(f"   Nodes created: {len(nodes)}")

# ============================================================================
# 3. BUILD CORRIDORS (EDGES BETWEEN NODES)
# ============================================================================

print("\n[3/6] Building corridors (paths between nodes)...")

# Track transitions for each elephant
corridors_dict = {}

for elephant_name in df_clustered['Name'].unique():
    elephant_data = df_clustered[df_clustered['Name']
                                 == elephant_name].sort_values('Datetime_standard')

    # Get sequence of nodes visited
    node_sequence = elephant_data['node_id'].tolist()
    times = elephant_data['Hour'].tolist()

    # Build transitions
    for i in range(len(node_sequence) - 1):
        from_node = node_sequence[i]
        to_node = node_sequence[i + 1]

        # Skip if same node
        if from_node == to_node:
            continue

        # Create corridor key (bidirectional: use sorted order)
        corridor_key = tuple(sorted([from_node, to_node]))

        if corridor_key not in corridors_dict:
            corridors_dict[corridor_key] = {
                'elephants': set(),
                'crossing_count': 0,
                'times': []
            }

        corridors_dict[corridor_key]['elephants'].add(elephant_name)
        corridors_dict[corridor_key]['crossing_count'] += 1
        corridors_dict[corridor_key]['times'].append(times[i])

# Filter corridors - use minimum 1 elephant for more coverage
min_usage = 1
filtered_corridors = {k: v for k, v in corridors_dict.items()
                      if len(v['elephants']) >= min_usage}

print(f"   Total unique transitions: {len(corridors_dict)}")
print(
    f"   Filtered corridors (used by {min_usage}+ elephants): {len(filtered_corridors)}")

# Create corridor objects
corridors = []
for corridor_key, corridor_data in filtered_corridors.items():
    from_node, to_node = corridor_key

    # Get node locations
    from_node_data = next(
        (n for n in nodes if n['node_id'] == from_node), None)
    to_node_data = next((n for n in nodes if n['node_id'] == to_node), None)

    if from_node_data is None or to_node_data is None:
        continue

    # Calculate distance using haversine
    def haversine(lat1, lon1, lat2, lon2):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    distance = haversine(
        from_node_data['center_lat'], from_node_data['center_lon'],
        to_node_data['center_lat'], to_node_data['center_lon']
    )

    # Most common hours
    from collections import Counter
    hour_counts = Counter(corridor_data['times'])
    active_hours = [h for h, c in hour_counts.most_common(5)]

    corridor = {
        'corridor_id': f"{from_node}-{to_node}",
        'from_node': int(from_node),
        'to_node': int(to_node),
        'path': [
            {'lat': from_node_data['center_lat'],
                'lon': from_node_data['center_lon']},
            {'lat': to_node_data['center_lat'],
                'lon': to_node_data['center_lon']}
        ],
        'distance_meters': float(distance),
        'usage_count': len(corridor_data['elephants']),
        'crossing_count': corridor_data['crossing_count'],
        'elephants': list(corridor_data['elephants']),
        'active_hours': active_hours,
        'bidirectional': True
    }
    corridors.append(corridor)

print(f"   Corridors created: {len(corridors)}")

# ============================================================================
# 4. CALCULATE CORRIDOR SAFETY SCORES
# ============================================================================

print("\n[4/6] Calculating corridor safety scores...")

for corridor in corridors:
    # Get nodes along corridor
    from_node = next(n for n in nodes if n['node_id'] == corridor['from_node'])
    to_node = next(n for n in nodes if n['node_id'] == corridor['to_node'])

    # Safety based on:
    # 1. Average human distance along corridor (40%) - farther from humans = safer for elephants
    # 2. Protected area status (30%) - protected areas = safer
    # 3. Low usage = less conflict potential (30%)

    avg_human_dist = (from_node['avg_human_distance'] +
                      to_node['avg_human_distance']) / 2
    protected_score = (from_node['protected'] + to_node['protected']) / 2
    # More usage = more risk
    usage_penalty = min(corridor['usage_count'] / 10, 1)

    safety_score = (
        (min(avg_human_dist / 5000, 1) * 40) +  # Far from humans
        (protected_score * 30) +                  # In protected area
        ((1 - usage_penalty) * 30)                # Lower usage
    )

    corridor['safety_score'] = float(min(safety_score, 100))
    corridor['avg_human_distance'] = float(avg_human_dist)

# Sort corridors by usage
corridors = sorted(corridors, key=lambda x: x['usage_count'], reverse=True)

print(f"   Safety scores calculated")

# ============================================================================
# 5. ROAD CROSSING ANALYSIS
#    Detect where corridors cross roads, how often, when, and danger level
# ============================================================================

print("\n[5/6] Detecting road crossings along corridors...")

# Load full raw elephant data (includes RoadName, RoadDistance, Season, HumanDistance)
df_raw = pd.read_csv('./outputs/elephant_data.csv')
df_raw['Datetime_standard'] = pd.to_datetime(df_raw['Datetime_standard'], errors='coerce')

# Season map
season_map = {
    12: 'Dry', 1: 'Dry', 2: 'Dry',
    3: 'Inter-Monsoon', 4: 'Inter-Monsoon', 5: 'Inter-Monsoon',
    6: 'Southwest-Monsoon', 7: 'Southwest-Monsoon', 8: 'Southwest-Monsoon',
    9: 'Inter-Monsoon-2', 10: 'Inter-Monsoon-2', 11: 'Inter-Monsoon-2'
}
df_raw['Month'] = df_raw['Datetime_standard'].dt.month
df_raw['Season'] = df_raw['Month'].map(season_map).fillna('Unknown')
df_raw['Hour'] = df_raw['Datetime_standard'].dt.hour

# Filter to only points near a road (RoadDistance < 500m)
road_threshold_m = 500
df_near_road = df_raw[df_raw['RoadDistance'] < road_threshold_m].copy()
print(f"   GPS points within {road_threshold_m}m of a road: {len(df_near_road):,}")

# Compute: which road IDs appear most globally (proxy for traffic volume)
road_global_counts = df_raw['RoadName'].value_counts()

def point_to_segment_distance_m(plat, plon, alat, alon, blat, blon):
    """Approx distance in metres from point P to segment A-B using haversine."""
    from math import radians, sin, cos, sqrt, atan2
    def hav(la1, lo1, la2, lo2):
        R = 6371000
        la1, lo1, la2, lo2 = map(radians, [la1, lo1, la2, lo2])
        a = sin((la2-la1)/2)**2 + cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1-a))

    ab = hav(alat, alon, blat, blon)
    if ab < 1:   # degenerate segment
        return hav(plat, plon, alat, alon)

    # Project P onto infinite line A->B in degree-space (fast approx)
    dx, dy = blon - alon, blat - alat
    t = ((plon - alon)*dx + (plat - alat)*dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    clat = alat + t*dy
    clon = alon + t*dx
    return hav(plat, plon, clat, clon)

# Corridor buffer: GPS point is "on corridor" if within CORRIDOR_BUFFER_M of its line
CORRIDOR_BUFFER_M = 2000   # 2 km

all_road_crossings = []   # flat list for the top-level network key

for corridor in corridors:
    from_node_data = next(n for n in nodes if n['node_id'] == corridor['from_node'])
    to_node_data   = next(n for n in nodes if n['node_id'] == corridor['to_node'])

    alat, alon = from_node_data['center_lat'], from_node_data['center_lon']
    blat, blon = to_node_data['center_lat'],   to_node_data['center_lon']

    # Find near-road points that lie along this corridor
    crossing_events = []
    for _, row in df_near_road.iterrows():
        dist = point_to_segment_distance_m(
            row['latitude'], row['longitude'], alat, alon, blat, blon)
        if dist < CORRIDOR_BUFFER_M:
            crossing_events.append(row)

    if not crossing_events:
        corridor['road_crossings'] = []
        continue

    ce_df = pd.DataFrame(crossing_events)

    # Group by RoadName → each unique road ID is one crossing point
    road_crossings = []
    for road_id, grp in ce_df.groupby('RoadName'):
        hours = grp['Hour'].dropna().astype(int).tolist()
        seasons = grp['Season'].dropna().tolist()
        night_count = sum(1 for h in hours if h < 6 or h >= 18)
        night_ratio = night_count / len(hours) if hours else 0

        hour_dist = {}
        for h in hours:
            hour_dist[str(h)] = hour_dist.get(str(h), 0) + 1

        season_dist = {}
        for s in seasons:
            season_dist[s] = season_dist.get(s, 0) + 1

        avg_human_dist = float(grp['HumanDistance'].mean()) if 'HumanDistance' in grp else 5000
        crossing_count = len(grp)
        elephant_count = grp['Name'].nunique() if 'Name' in grp else 1

        # --- Road danger classification ---
        # traffic_exposure: how frequently this road ID appears globally
        global_hits = int(road_global_counts.get(road_id, 1))
        max_hits    = int(road_global_counts.max()) if len(road_global_counts) > 0 else 1
        traffic_score = min(global_hits / max_hits, 1.0)   # 0-1

        # Road type label based on traffic percentile
        pct = traffic_score
        if pct > 0.7:
            road_type = "Major Road"
        elif pct > 0.3:
            road_type = "Secondary Road"
        else:
            road_type = "Minor Road"

        # Danger score (0-100)
        # 40% night crossings, 30% human proximity, 20% crossing frequency, 10% traffic
        human_proximity_score = max(0, 1 - avg_human_dist / 5000)
        freq_score = min(crossing_count / 30, 1.0)
        danger_score = (
            night_ratio * 40 +
            human_proximity_score * 30 +
            freq_score * 20 +
            traffic_score * 10
        )

        if danger_score >= 55:
            danger_level = "High"
        elif danger_score >= 30:
            danger_level = "Medium"
        else:
            danger_level = "Low"

        # Peak crossing hours (top 3)
        peak_hours = sorted(hour_dist, key=hour_dist.get, reverse=True)[:3]
        peak_hours_int = [int(h) for h in peak_hours]

        # Peak season
        peak_season = max(season_dist, key=season_dist.get) if season_dist else 'Unknown'

        # Most common time-of-day label
        def time_label(h):
            if h < 6 or h >= 22: return 'Night'
            if h < 10: return 'Early Morning'
            if h < 14: return 'Midday'
            if h < 18: return 'Afternoon'
            return 'Evening'

        tol_dist = {}
        for h in hours:
            lbl = time_label(h)
            tol_dist[lbl] = tol_dist.get(lbl, 0) + 1
        peak_time_of_day = max(tol_dist, key=tol_dist.get) if tol_dist else 'Unknown'

        crossing = {
            'crossing_id': f"{corridor['corridor_id']}_road_{int(road_id)}",
            'corridor_id': corridor['corridor_id'],
            'road_osm_id': int(road_id),
            'road_type': road_type,
            'crossing_lat': float(grp['latitude'].mean()),
            'crossing_lon': float(grp['longitude'].mean()),
            # Stats
            'crossing_count': crossing_count,
            'elephant_count': elephant_count,
            'elephants': grp['Name'].unique().tolist() if 'Name' in grp else [],
            # Timing
            'hour_distribution': hour_dist,
            'season_distribution': season_dist,
            'night_ratio': float(round(night_ratio, 3)),
            'peak_hours': peak_hours_int,
            'peak_season': peak_season,
            'peak_time_of_day': peak_time_of_day,
            # Road danger
            'avg_human_distance': float(round(avg_human_dist, 1)),
            'traffic_exposure': float(round(traffic_score, 3)),
            'danger_score': float(round(danger_score, 1)),
            'danger_level': danger_level,
        }
        road_crossings.append(crossing)
        all_road_crossings.append(crossing)

    # Sort by danger score descending within corridor
    road_crossings.sort(key=lambda x: x['danger_score'], reverse=True)
    corridor['road_crossings'] = road_crossings

total_crossings = sum(len(c['road_crossings']) for c in corridors)
high_danger   = sum(1 for rc in all_road_crossings if rc['danger_level'] == 'High')
medium_danger = sum(1 for rc in all_road_crossings if rc['danger_level'] == 'Medium')
low_danger    = sum(1 for rc in all_road_crossings if rc['danger_level'] == 'Low')

print(f"   Road crossings detected: {total_crossings}")
print(f"     High danger : {high_danger}")
print(f"     Medium danger: {medium_danger}")
print(f"     Low danger  : {low_danger}")

# ============================================================================
# 6. SAVE CORRIDOR NETWORK
# ============================================================================

print("\n[6/6] Saving corridor network...")


def convert_to_json_serializable(obj):
    """Convert numpy types to Python types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    return obj


# Create network structure
network = {
    'metadata': {
        'total_nodes': len(nodes),
        'total_corridors': len(corridors),
        'total_road_crossings': total_crossings,
        'road_crossing_danger': {'High': high_danger, 'Medium': medium_danger, 'Low': low_danger},
        'elephants_tracked': int(df['Name'].nunique()),
        'date_range': {
            'start': str(df['Datetime_standard'].min()),
            'end': str(df['Datetime_standard'].max())
        },
        'clustering': {
            'algorithm': 'DBSCAN with haversine metric',
            'eps_km': eps_km,
            'min_samples': 5
        },
        'generated_at': str(pd.Timestamp.now())
    },
    'nodes': convert_to_json_serializable(nodes),
    'corridors': convert_to_json_serializable(corridors),
    'road_crossings': convert_to_json_serializable(all_road_crossings)
}

# Save as JSON
with open('./outputs/corridor_network.json', 'w') as f:
    json.dump(network, f, indent=2)
print(f"   Saved: corridor_network.json")

# Save summary CSV for easy viewing
nodes_df = pd.DataFrame(nodes)
nodes_df.to_csv('./outputs/corridor_nodes.csv', index=False)
print(f"   Saved: corridor_nodes.csv")

corridors_df = pd.DataFrame(corridors)
corridors_df = corridors_df.drop(
    columns=['path', 'elephants'], errors='ignore')
corridors_df.to_csv('./outputs/corridor_paths.csv', index=False)
print(f"   Saved: corridor_paths.csv")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "="*70)
print("CORRIDOR NETWORK COMPLETE")
print("="*70)

print(f"\nClustering Improvements:")
print(f"  - Using haversine distance (proper geographic distance)")
print(f"  - eps = {eps_km}km for tighter clusters")
print(f"  - min_samples = 5 for more coverage")

print(f"\nNodes (High-use zones):")
print(f"  Total nodes: {len(nodes)}")
print(
    f"  Avg elephants per node: {np.mean([n['elephant_count'] for n in nodes]):.1f}")
print(
    f"  Avg sightings per node: {np.mean([n['sighting_count'] for n in nodes]):.0f}")

print(f"\nCorridors (Movement paths):")
print(f"  Total corridors: {len(corridors)}")
if corridors:
    print(
        f"  Avg usage per corridor: {np.mean([c['usage_count'] for c in corridors]):.1f} elephants")
    print(
        f"  Avg crossings per corridor: {np.mean([c['crossing_count'] for c in corridors]):.0f}")

if corridors:
    print(f"\nTop 5 Most Used Corridors:")
    for i, corridor in enumerate(corridors[:5], 1):
        print(
            f"  {i}. {corridor['corridor_id']}: {corridor['usage_count']} elephants, {corridor['crossing_count']} crossings")

    print(f"\nTop 5 Safest Corridors:")
    safe_corridors = sorted(
        corridors, key=lambda x: x['safety_score'], reverse=True)[:5]
    for i, corridor in enumerate(safe_corridors, 1):
        print(
            f"  {i}. {corridor['corridor_id']}: Safety score {corridor['safety_score']:.1f}/100")
