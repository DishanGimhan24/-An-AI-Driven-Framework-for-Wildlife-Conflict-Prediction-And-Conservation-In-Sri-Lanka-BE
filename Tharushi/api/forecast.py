from flask import Blueprint, request, jsonify
from datetime import datetime

from data_processing.data_loader import data_loader
from ml.forecast_predictor import forecast_predictor

forecast_bp = Blueprint('forecast', __name__)


@forecast_bp.route('/forecast', methods=['POST'])
def get_forecast():
    """
    Get 7-day risk forecast for a location

    Request body:
    {
        "latitude": 8.35,
        "longitude": 80.4,
        "start_date": "2026-01-19"  // Optional, defaults to today
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        start_date = data.get('start_date')

        # Validate latitude and longitude
        if latitude is None or longitude is None:
            return jsonify({
                'status': 'error',
                'message': 'latitude and longitude are required'
            }), 400

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return jsonify({
                'status': 'error',
                'message': 'Invalid latitude or longitude format'
            }), 400

        # Validate coordinates
        if not (5.5 <= latitude <= 10.0 and 79.0 <= longitude <= 82.5):
            return jsonify({
                'status': 'error',
                'message': 'Coordinates outside Sri Lanka bounds'
            }), 400

        # Use today if no start_date provided
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        # Validate date format
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Generate forecast
        forecasts = forecast_predictor.forecast_7_days(latitude, longitude, start_date)

        if forecasts is None:
            return jsonify({
                'status': 'error',
                'message': 'Forecast generation failed'
            }), 500

        # Return response
        return jsonify({
            'status': 'success',
            'data': {
                'location': {
                    'latitude': latitude,
                    'longitude': longitude
                },
                'start_date': start_date,
                'forecasts': forecasts,
                'summary': {
                    'total_days': len(forecasts),
                    'high_risk_days': sum(1 for f in forecasts if f['risk_level'] == 'HIGH'),
                    'medium_risk_days': sum(1 for f in forecasts if f['risk_level'] == 'MEDIUM'),
                    'low_risk_days': sum(1 for f in forecasts if f['risk_level'] == 'LOW'),
                    'avg_risk_score': sum(f['risk_score'] for f in forecasts) / len(forecasts)
                }
            }
        }), 200

    except Exception as e:
        print(f"Error in forecast endpoint: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500


@forecast_bp.route('/forecast/city', methods=['POST'])
def forecast_city():
    """
    Get risk forecast for a specific city

    Request body:
    {
        "district": "Monaragala",
        "city": "Katharagama",
        "days": 7,
        "start_date": "2024-06-15"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Validate input
        district = data.get('district')
        city_name = data.get('city')
        days = data.get('days', 7)
        start_date_str = data.get('start_date')

        if not district or not city_name:
            return jsonify({
                'status': 'error',
                'message': 'District and city are required'
            }), 400

        # Get city center coordinates
        lat, lng = data_loader.city_loader.get_city_center(district, city_name)

        if lat is None or lng is None:
            return jsonify({
                'status': 'error',
                'message': f'City not found: {city_name} in {district}'
            }), 404

        # Validate date format if provided
        if start_date_str:
            try:
                datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        else:
            # Use today's date as string
            start_date_str = datetime.now().strftime('%Y-%m-%d')

        # Generate forecast (pass date string)
        from ml.forecaster import forecaster
        forecast_result = forecaster.forecast(lat, lng, days, start_date_str)

        if forecast_result is None:
            return jsonify({
                'status': 'error',
                'message': 'Forecast generation failed'
            }), 500

        # Add city info
        forecast_result['city'] = city_name
        forecast_result['district'] = district
        forecast_result['coordinates'] = {
            'lat': lat,
            'lng': lng
        }

        return jsonify({
            'status': 'success',
            'data': forecast_result
        }), 200

    except Exception as e:
        print(f"Error forecasting city: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Forecast failed: {str(e)}'
        }), 500