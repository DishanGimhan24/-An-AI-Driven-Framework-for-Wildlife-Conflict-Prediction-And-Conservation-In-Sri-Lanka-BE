import json
import os

import geopandas as gpd
import shapefile
from pyproj import CRS
from shapely.geometry import shape


def _read_prj_crs(file_path):
    prj_path = os.path.splitext(file_path)[0] + ".prj"
    if not os.path.exists(prj_path):
        return None

    try:
        with open(prj_path, "r", encoding="utf-8", errors="ignore") as prj_file:
            wkt = prj_file.read().strip()
        if not wkt:
            return None
        return CRS.from_wkt(wkt)
    except Exception:
        return None


def _read_shapefile(file_path):
    last_error = None
    for encoding in ("utf-8", "latin1", None):
        try:
            reader = shapefile.Reader(file_path, encoding=encoding) if encoding else shapefile.Reader(file_path)
            break
        except Exception as error:
            last_error = error
    else:
        raise last_error

    field_names = [field[0] for field in reader.fields[1:]]
    records = []
    geometries = []

    for shape_record in reader.iterShapeRecords():
        records.append(dict(zip(field_names, list(shape_record.record))))
        geometry = None
        if getattr(shape_record.shape, "shapeType", 0) != 0:
            geometry = shape(shape_record.shape.__geo_interface__)
        geometries.append(geometry)

    geodataframe = gpd.GeoDataFrame(records, geometry=geometries)

    crs = _read_prj_crs(file_path)
    if crs is not None:
        geodataframe = geodataframe.set_crs(crs, allow_override=True)
    elif geodataframe.crs is None:
        geodataframe = geodataframe.set_crs("EPSG:4326", allow_override=True)

    return geodataframe


def _read_geojson(file_path):
    with open(file_path, "r", encoding="utf-8") as geojson_file:
        geojson = json.load(geojson_file)

    features = geojson.get("features", [])
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def read_vector_file(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".shp":
        return _read_shapefile(file_path)
    if extension in {".json", ".geojson"}:
        return _read_geojson(file_path)
    raise ValueError(f"Unsupported vector file format: {file_path}")