from flask import Blueprint, request, jsonify
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.predictor import predictor
from data_processing.data_loader import data_loader

predict_bp = Blueprint('predict', __name__)

# Prediction log file
PREDICTIONS_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'predictions.csv')


def log_prediction(latitude, longitude, date, risk_score, risk_level, confidence):
    """Log predictions to CSV for analysis"""
    try:
        os.makedirs(os.path.dirname(PREDICTIONS_LOG), exist_ok=True)

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'latitude': latitude,
            'longitude': longitude,
            'date': date,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'confidence': confidence
        }

        # Append to CSV
        df = pd.DataFrame([log_entry])
        if os.path.exists(PREDICTIONS_LOG):
            df.to_csv(PREDICTIONS_LOG, mode='a', header=False, index=False)
        else:
            df.to_csv(PREDICTIONS_LOG, mode='w', header=True, index=False)
    except Exception as e:
        print(f"Warning: Failed to log prediction: {e}")


@predict_bp.route('/predict', methods=['POST'])
def predict():
    """
    Predict conflict risk for a location and date

    Request body:
    {
        "latitude": 7.5,
        "longitude": 80.5,
        "date": "2024-06-15"
    }
    """
    try:
        # Validate request
        data = request.get_json()

        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required',
                'error_code': 'MISSING_BODY'
            }), 400

        # Extract parameters
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        date = data.get('date')

        # Validate required fields
        if latitude is None or longitude is None or date is None:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: latitude, longitude, date',
                'error_code': 'MISSING_FIELDS'
            }), 400

        # Validate data types and ranges
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'Latitude and longitude must be numbers',
                'error_code': 'INVALID_COORDINATES'
            }), 400

        # Validate coordinates are within Sri Lanka bounds
        if not (5.9 <= latitude <= 9.9 and 79.5 <= longitude <= 82.0):
            return jsonify({
                'status': 'error',
                'message': 'Coordinates must be within Sri Lanka (Lat: 5.9-9.9, Lon: 79.5-82.0)',
                'error_code': 'OUT_OF_BOUNDS'
            }), 400

        # Validate date format
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Date must be in YYYY-MM-DD format',
                'error_code': 'INVALID_DATE_FORMAT'
            }), 400

        # Make prediction
        result = predictor.predict(latitude, longitude, date)

        if result is None:
            return jsonify({
                'status': 'error',
                'message': 'Prediction failed - model not loaded or feature extraction error',
                'error_code': 'PREDICTION_FAILED'
            }), 500

        # Add confidence score (from Random Forest probability)
        confidence = result.get('confidence', 0.0)

        # Log prediction
        log_prediction(latitude, longitude, date,
                       result['risk_score'], result['risk_level'], confidence)

        # Return successful response
        return jsonify({
            'status': 'success',
            'data': {
                'location': {
                    'latitude': latitude,
                    'longitude': longitude
                },
                'date': date,
                'risk_score': round(result['risk_score'], 3),
                'risk_level': result['risk_level'],
                'confidence': round(confidence, 3),
                'features': result.get('features', {}),
                'recommendation': get_recommendation(result['risk_level'], confidence)
            }
        }), 200

    except Exception as e:
        print(f"Error in prediction: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'error_code': 'INTERNAL_ERROR'
        }), 500


def get_recommendation(risk_level, confidence):
    """Get recommendation based on risk level and confidence"""
    if risk_level == 'HIGH':
        if confidence > 0.8:
            return "HIGH RISK - Strong confidence. Avoid area, implement immediate preventive measures."
        else:
            return "HIGH RISK - Moderate confidence. Exercise extreme caution, monitor situation closely."
    elif risk_level == 'MEDIUM':
        if confidence > 0.7:
            return "MEDIUM RISK - Stay alert, maintain safe distance from wildlife."
        else:
            return "MEDIUM RISK - Exercise caution, conditions may vary."
    else:  # LOW
        if confidence > 0.7:
            return "LOW RISK - Safe to proceed with normal precautions."
        else:
            return "LOW RISK - Generally safe, but remain aware of surroundings."


@predict_bp.route('/predict/batch', methods=['POST'])
def predict_batch():
    """
    Predict conflict risk for multiple locations

    Request body:
    {
        "locations": [
            {"latitude": 7.5, "longitude": 80.5, "date": "2024-06-15"},
            {"latitude": 7.6, "longitude": 80.6, "date": "2024-06-15"}
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or 'locations' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing "locations" array in request body',
                'error_code': 'MISSING_LOCATIONS'
            }), 400

        locations = data['locations']

        if not isinstance(locations, list) or len(locations) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Locations must be a non-empty array',
                'error_code': 'INVALID_LOCATIONS'
            }), 400

        if len(locations) > 100:
            return jsonify({
                'status': 'error',
                'message': 'Maximum 100 locations per batch request',
                'error_code': 'TOO_MANY_LOCATIONS'
            }), 400

        # Process each location
        results = []
        errors = []

        for idx, loc in enumerate(locations):
            try:
                lat = float(loc.get('latitude'))
                lon = float(loc.get('longitude'))
                date = loc.get('date')

                # Validate bounds
                if not (5.9 <= lat <= 9.9 and 79.5 <= lon <= 82.0):
                    errors.append({
                        'index': idx,
                        'error': 'Coordinates out of Sri Lanka bounds'
                    })
                    continue

                # Make prediction
                result = predictor.predict(lat, lon, date)

                if result:
                    results.append({
                        'index': idx,
                        'location': {'latitude': lat, 'longitude': lon},
                        'date': date,
                        'risk_score': round(result['risk_score'], 3),
                        'risk_level': result['risk_level'],
                        'confidence': round(result.get('confidence', 0.0), 3)
                    })
                else:
                    errors.append({
                        'index': idx,
                        'error': 'Prediction failed'
                    })

            except Exception as e:
                errors.append({
                    'index': idx,
                    'error': str(e)
                })

        return jsonify({
            'status': 'success',
            'data': {
                'predictions': results,
                'total': len(locations),
                'successful': len(results),
                'failed': len(errors),
                'errors': errors if errors else None
            }
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'error_code': 'INTERNAL_ERROR'
        }), 500


@predict_bp.route('/predict/city', methods=['POST'])
def predict_city():
    """
    Predict conflict risk for a specific city

    Request body:
    {
        "district": "Monaragala",
        "city": "Katharagama",
        "date": "2024-06-15"
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
        date_str = data.get('date')

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
        if date_str:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        else:
            # Use today's date as string
            date_str = datetime.now().strftime('%Y-%m-%d')

        # Run prediction using city center (pass date_str, not datetime object)
        result = predictor.predict(lat, lng, date_str)

        if result is None:
            return jsonify({
                'status': 'error',
                'message': 'Prediction failed'
            }), 500

        # Add city info to result
        result['city'] = city_name
        result['district'] = district
        result['coordinates'] = {
            'lat': lat,
            'lng': lng
        }

        # Log prediction
        log_prediction(lat, lng, date_str,
                       result['risk_score'], result['risk_level'], result['confidence'])

        return jsonify({
            'status': 'success',
            'data': result
        }), 200

    except Exception as e:
        print(f"Error predicting city risk: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Prediction failed: {str(e)}'
        }), 500