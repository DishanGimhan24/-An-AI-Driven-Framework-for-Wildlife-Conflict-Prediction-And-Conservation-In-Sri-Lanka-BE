import geopandas as gpd
from shapely.geometry import Point
import numpy as np
import warnings

# Suppress shapely warnings about invalid geometries
warnings.filterwarnings('ignore', message='invalid value encountered in distance')


def calculate_distance_to_nearest(point_lat, point_lon, gdf):
    """
    Calculate distance from point to nearest feature in geodataframe
    Returns distance in kilometers
    """
    try:
        # Create point geometry
        point = Point(point_lon, point_lat)
        point_gdf = gpd.GeoDataFrame([1], geometry=[point], crs="EPSG:4326")

        # Ensure gdf has CRS
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")

        # Reproject to UTM for accurate distance calculation
        point_utm = point_gdf.to_crs("EPSG:32644")  # UTM Zone 44N for Sri Lanka
        gdf_utm = gdf.to_crs("EPSG:32644")

        # Calculate distances
        distances = gdf_utm.geometry.distance(point_utm.geometry.iloc[0])

        # Filter out invalid distances
        valid_distances = distances[~np.isnan(distances)]

        if len(valid_distances) == 0:
            return 999.0  # Return large distance if no valid geometries

        # Return minimum distance in km
        return valid_distances.min() / 1000
    except Exception as e:
        return 999.0  # Return large distance on error


def point_in_polygon(point_lat, point_lon, gdf):
    """
    Check if point is inside any polygon in geodataframe
    Returns 1 if inside, 0 if outside
    """
    point = Point(point_lon, point_lat)
    point_gdf = gpd.GeoDataFrame([1], geometry=[point], crs="EPSG:4326")

    # Ensure gdf has CRS
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    # Check intersection
    for geom in gdf.geometry:
        if point_gdf.geometry.iloc[0].intersects(geom):
            return 1
    return 0


def calculate_buffer_zone(point_lat, point_lon, gdf, buffer_km=5):
    """
    Check if point is within buffer distance of any feature
    Returns 1 if within buffer, 0 otherwise
    """
    # Ensure gdf has CRS before calculating distance
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    distance = calculate_distance_to_nearest(point_lat, point_lon, gdf)
    return 1 if distance <= buffer_km else 0


def get_density_at_point(point_lat, point_lon, raster_path):
    """
    Extract raster value at point location (for population density)
    Returns density value
    """
    import rasterio
    from rasterio.transform import rowcol

    with rasterio.open(raster_path) as src:
        # Get pixel coordinates
        row, col = rowcol(src.transform, point_lon, point_lat)

        # Check if within bounds
        if 0 <= row < src.height and 0 <= col < src.width:
            # Read value
            value = src.read(1)[row, col]
            return float(value) if value != src.nodata else 0.0
        else:
            return 0.0