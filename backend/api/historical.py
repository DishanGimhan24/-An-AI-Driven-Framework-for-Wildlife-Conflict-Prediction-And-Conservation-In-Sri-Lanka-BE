import os

import pandas as pd
from flask import Blueprint, request

from config import ELEPHANT_DEATHS_DIR
from data_processing.data_loader import data_loader
from utils.response_formatter import success_response, error_response

historical_bp = Blueprint('historical', __name__)


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
                df = df[df['Date'] <= pd.to_datetime(end_date)]

        # Remove rows with invalid dates
        df = df.dropna(subset=['Date'])

        # Convert dates to string for JSON
        if 'Date' in df.columns and len(df) > 0:
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        conflicts = df.to_dict('records')

        print(f"✓ Historical conflicts: {len(conflicts)} records")

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
                df = df[df['Date'] <= pd.to_datetime(end_date)]

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