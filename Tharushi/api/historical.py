import math
import os

import pandas as pd
from flask import Blueprint, request

from config import ELEPHANT_DEATHS_DIR
from data_processing.data_loader import data_loader
from utils.response_formatter import success_response, error_response

historical_bp = Blueprint('historical', __name__)

# District centre coordinates (used to reverse-geocode lat/lon → district name)
_DISTRICT_COORDS = {
    'Colombo': (6.9271, 79.8612), 'Gampaha': (7.0914, 80.0155),
    'Kalutara': (6.5854, 79.9607), 'Kandy': (7.2906, 80.6337),
    'Matale': (7.4675, 80.6234), 'Nuwara Eliya': (6.9497, 80.7891),
    'Galle': (6.0535, 80.2210), 'Matara': (5.9549, 80.5550),
    'Hambantota': (6.1429, 81.1212), 'Jaffna': (9.6615, 80.0255),
    'Kilinochchi': (9.3958, 80.3989), 'Mannar': (8.9810, 79.9044),
    'Vavuniya': (8.7514, 80.4971), 'Mullaitivu': (9.2671, 80.8142),
    'Batticaloa': (7.7310, 81.6747), 'Ampara': (7.2917, 81.6747),
    'Trincomalee': (8.5874, 81.2152), 'Kurunegala': (7.4863, 80.3623),
    'Puttalam': (8.0362, 79.8283), 'Anuradhapura': (8.3114, 80.4037),
    'Polonnaruwa': (7.9403, 81.0188), 'Badulla': (6.9934, 81.0550),
    'Monaragala': (6.8728, 81.3507), 'Ratnapura': (6.7056, 80.3847),
    'Kegalle': (7.2513, 80.3464),
}


def _nearest_district(lat, lon):
    """Return the closest district name for a lat/lon point."""
    best, best_d = None, float('inf')
    for name, (dlat, dlon) in _DISTRICT_COORDS.items():
        d = math.hypot(lat - dlat, lon - dlon)
        if d < best_d:
            best_d, best = d, name
    return best


@historical_bp.route('/conflicts', methods=['GET'])
def get_historical_conflicts():
    """Get historical conflict data"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        district = request.args.get('district')

        if data_loader.tracking_data is None:
            return error_response("Historical data not available", 404)

        df = data_loader.tracking_data.copy()

        # Fix date format: 2009.01.12 -> 2009-01-12
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str).str.replace('.', '-', regex=False)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

            # Filter by date
            if start_date:
                df = df[df['Date'] >= pd.to_datetime(start_date)]

            if end_date:
                # Use end of day so records timestamped on end_date are included
                df = df[df['Date'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

        # Remove rows with invalid dates
        df = df.dropna(subset=['Date'])

        # Assign district from lat/lon if not already present
        lat_col = 'latitude' if 'latitude' in df.columns else ('Latitude' if 'Latitude' in df.columns else None)
        lon_col = 'longitude' if 'longitude' in df.columns else ('Longitude' if 'Longitude' in df.columns else None)

        if 'District' not in df.columns and lat_col and lon_col:
            df['District'] = df.apply(
                lambda row: _nearest_district(row[lat_col], row[lon_col])
                if pd.notna(row[lat_col]) and pd.notna(row[lon_col]) else 'Unknown',
                axis=1
            )

        # Apply district filter
        if district and 'District' in df.columns:
            df = df[df['District'].str.lower() == district.strip().lower()]

        # Convert dates to string for JSON
        if 'Date' in df.columns and len(df) > 0:
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        conflicts = df.to_dict('records')

        print(f"✓ Historical conflicts: {len(conflicts)} records (district={district})")

        return success_response({
            'conflicts': conflicts,
            'count': len(conflicts),
            'start_date': start_date,
            'end_date': end_date,
            'district': district
        }, "Historical conflicts retrieved")

    except Exception as e:
        print(f"Historical conflicts error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(f"Internal error: {str(e)}", 500)


@historical_bp.route('/conflict-stats', methods=['GET'])
def get_conflict_stats():
    """Get statistical summary of conflicts"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        district = request.args.get('district')

        if data_loader.tracking_data is None:
            return error_response("Historical data not available", 404)

        df = data_loader.tracking_data.copy()

        # Fix date format: 2009.01.12 -> 2009-01-12
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str).str.replace('.', '-', regex=False)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

            # Filter by date
            if start_date:
                df = df[df['Date'] >= pd.to_datetime(start_date)]

            if end_date:
                df = df[df['Date'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

        # Assign district and apply filter (mirrors /conflicts logic)
        lat_col = 'latitude' if 'latitude' in df.columns else ('Latitude' if 'Latitude' in df.columns else None)
        lon_col = 'longitude' if 'longitude' in df.columns else ('Longitude' if 'Longitude' in df.columns else None)

        if 'District' not in df.columns and lat_col and lon_col:
            df['District'] = df.apply(
                lambda row: _nearest_district(row[lat_col], row[lon_col])
                if pd.notna(row[lat_col]) and pd.notna(row[lon_col]) else 'Unknown',
                axis=1
            )

        if district and 'District' in df.columns:
            df = df[df['District'].str.lower() == district.strip().lower()]

        # Remove rows with invalid dates
        df = df.dropna(subset=['Date'])

        # Total conflicts
        total_conflicts = len(df)

        # Monthly breakdown
        monthly_data = []
        if len(df) > 0:
            df['year_month'] = df['Date'].dt.to_period('M')
            monthly_counts = df.groupby('year_month').size().reset_index(name='count')
            monthly_counts['year_month'] = monthly_counts['year_month'].astype(str)
            monthly_data = monthly_counts.to_dict('records')

        # Calculate avg per month
        avg_per_month = 0
        if len(df) > 0:
            date_range = (df['Date'].max() - df['Date'].min()).days
            months = max(1, date_range / 30)
            avg_per_month = round(total_conflicts / months, 1)

        # Count unique districts if available
        districts_affected = 0
        by_district = {}

        print(f"✓ Stats calculated: {total_conflicts} conflicts, {len(monthly_data)} months")

        return success_response({
            'total_conflicts': total_conflicts,
            'total_injuries': 0,
            'total_property_damage': 0,
            'districts_affected': districts_affected,
            'avg_per_month': avg_per_month,
            'monthly_data': monthly_data,
            'by_district': by_district,
            'start_date': start_date,
            'end_date': end_date
        }, "Statistics retrieved")

    except Exception as e:
        print(f"Conflict stats error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(f"Internal error: {str(e)}", 500)