from flask import Blueprint, request, jsonify
from datetime import datetime
import os

from data_processing.data_loader import data_loader
from ml.district_classifier import get_district_risk_levels
from ml.rule_based_grid import rule_based_grid
from config import MODELS_DIR

heatmap_bp = Blueprint('heatmap', __name__)


@heatmap_bp.route('/heatmap/grid', methods=['GET'])
def get_heatmap_grid():
    """Get rule-based risk grid for heatmap"""
    try:
        date = request.args.get('date')
        regenerate = request.args.get('regenerate', 'false').lower() == 'true'

        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Check cache
        filename = f"risk_grid_{date}.json"
        grids_dir = os.path.join(MODELS_DIR, 'grids')
        filepath = os.path.join(grids_dir, filename)

        if not regenerate and os.path.exists(filepath):
            import json
            with open(filepath, 'r') as f:
                cached_grid = json.load(f)

            return jsonify({
                'status': 'success',
                'data': cached_grid,
                'cached': True
            }), 200

        # Generate new grid (fast with rule-based)
        print(f"Generating rule-based grid for {date}...")
        grid_data = rule_based_grid.generate_grid(date, grid_size=50)
        rule_based_grid.save_grid(grid_data, filename)

        return jsonify({
            'status': 'success',
            'data': grid_data,
            'cached': False
        }), 200

    except Exception as e:
        print(f"Error in heatmap endpoint: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'message': f'Failed to generate heatmap: {str(e)}'
        }), 500


@heatmap_bp.route('/heatmap/available-dates', methods=['GET'])
def get_available_dates():
    """Get list of dates with pre-computed grids"""
    try:
        grids_dir = os.path.join(MODELS_DIR, 'grids')

        if not os.path.exists(grids_dir):
            return jsonify({
                'status': 'success',
                'data': {'dates': [], 'count': 0}
            }), 200

        grid_files = [f for f in os.listdir(grids_dir)
                      if f.startswith('risk_grid_') and f.endswith('.json')]

        dates = [f.replace('risk_grid_', '').replace('.json', '')
                 for f in grid_files]
        dates.sort()

        return jsonify({
            'status': 'success',
            'data': {'dates': dates, 'count': len(dates)}
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get available dates: {str(e)}'
        }), 500


@heatmap_bp.route('/heatmap/districts', methods=['GET'])
def get_district_heatmap():
    """Get district-level risk classification"""
    try:
        date = request.args.get('date')
        regenerate = request.args.get('regenerate', 'false').lower() == 'true'

        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Per-date cache (25 ML predictions per request otherwise)
        districts_cache_dir = os.path.join(MODELS_DIR, 'districts')
        os.makedirs(districts_cache_dir, exist_ok=True)
        cache_path = os.path.join(districts_cache_dir, f'district_risk_{date}.json')

        if not regenerate and os.path.exists(cache_path):
            import json
            with open(cache_path, 'r') as f:
                cached = json.load(f)
            return jsonify({
                'status': 'success',
                'data': cached,
                'cached': True
            }), 200

        # Get district classifications
        district_risks = get_district_risk_levels(date)

        # Calculate summary
        high_count = sum(1 for d in district_risks if d['risk_level'] == 'HIGH')
        medium_count = sum(1 for d in district_risks if d['risk_level'] == 'MEDIUM')
        low_count = sum(1 for d in district_risks if d['risk_level'] == 'LOW')

        payload = {
            'date': date,
            'districts': district_risks,
            'summary': {
                'total_districts': len(district_risks),
                'high_risk_districts': high_count,
                'medium_risk_districts': medium_count,
                'low_risk_districts': low_count
            }
        }

        import json
        with open(cache_path, 'w') as f:
            json.dump(payload, f)

        return jsonify({
            'status': 'success',
            'data': payload,
            'cached': False
        }), 200

    except Exception as e:
        print(f"Error in district heatmap endpoint: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'message': f'Failed to generate district heatmap: {str(e)}'
        }), 500


@heatmap_bp.route('/heatmap/cities', methods=['GET'])
def get_city_heatmap():
    """
    Get city-level risk heatmap for a district

    Query params:
    - district: District name (required)
    - date: Date in YYYY-MM-DD format (optional, defaults to today)

    Example: /api/heatmap/cities?district=Monaragala&date=2026-01-20
    """
    try:
        district = request.args.get('district')
        date_str = request.args.get('date')

        if not district:
            return jsonify({
                'status': 'error',
                'message': 'District parameter is required'
            }), 400

        # Parse date
        if date_str:
            try:
                pred_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        else:
            pred_date = datetime.now()

        # Get all cities in district
        cities = data_loader.city_loader.get_cities_by_district(district)

        if not cities:
            return jsonify({
                'status': 'error',
                'message': f'No cities found for district: {district}'
            }), 404

        date_str = pred_date.strftime('%Y-%m-%d')
        regenerate = request.args.get('regenerate', 'false').lower() == 'true'

        # Cache per district+date — city predictions can be expensive
        import json
        cities_cache_dir = os.path.join(MODELS_DIR, 'cities')
        os.makedirs(cities_cache_dir, exist_ok=True)
        safe_district = district.replace(' ', '_').replace('/', '_')
        cache_path = os.path.join(cities_cache_dir, f'city_risk_{safe_district}_{date_str}.json')

        if not regenerate and os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cached = json.load(f)
            return jsonify({
                'status': 'success',
                'data': cached,
                'cached': True
            }), 200

        print(f"Generating city-level heatmap for {district} ({len(cities)} cities)...")

        # Predict for each city
        city_predictions = []
        high_risk = 0
        medium_risk = 0
        low_risk = 0

        from ml.predictor import predictor

        for city in cities:
            lat = city['center_lat']
            lng = city['center_lng']

            # Run prediction — pass string not datetime; feature_extractor
            # expects strptime-parseable string.
            result = predictor.predict(lat, lng, date_str)

            if result:
                # Get geometry
                geometry = data_loader.city_loader.get_city_geometry(city['gid'])

                city_data = {
                    'name': city['name'],
                    'gid': city['gid'],
                    'risk_score': result['risk_score'],
                    'risk_level': result['risk_level'],
                    'center': {
                        'lat': lat,
                        'lng': lng
                    }
                }

                # Add geometry if available
                if geometry:
                    city_data['geometry'] = geometry.__geo_interface__

                city_predictions.append(city_data)

                # Count risk levels
                if result['risk_level'] == 'HIGH':
                    high_risk += 1
                elif result['risk_level'] == 'MEDIUM':
                    medium_risk += 1
                else:
                    low_risk += 1

        print(f"✓ Generated predictions for {len(city_predictions)} cities")

        payload = {
            'district': district,
            'date': date_str,
            'total_cities': len(city_predictions),
            'cities': city_predictions,
            'summary': {
                'high_risk_cities': high_risk,
                'medium_risk_cities': medium_risk,
                'low_risk_cities': low_risk
            }
        }

        with open(cache_path, 'w') as f:
            json.dump(payload, f)

        return jsonify({
            'status': 'success',
            'data': payload,
            'cached': False
        }), 200

    except Exception as e:
        print(f"Error generating city heatmap: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to generate city heatmap: {str(e)}'
        }), 500