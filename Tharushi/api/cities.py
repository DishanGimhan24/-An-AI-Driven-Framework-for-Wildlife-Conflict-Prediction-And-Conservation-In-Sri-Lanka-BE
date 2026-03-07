from flask import Blueprint, request, jsonify
from datetime import datetime
from data_processing.data_loader import data_loader

cities_bp = Blueprint('cities', __name__)


@cities_bp.route('/cities', methods=['GET'])
def get_cities():
    """
    Get cities by district

    Query params:
    - district: District name (required)

    Example: /api/cities?district=Monaragala
    """
    try:
        district = request.args.get('district')

        if not district:
            return jsonify({
                'status': 'error',
                'message': 'District parameter is required'
            }), 400

        # Get cities
        cities = data_loader.city_loader.get_cities_by_district(district)

        if not cities:
            return jsonify({
                'status': 'error',
                'message': f'No cities found for district: {district}'
            }), 404

        # Format response
        city_list = [
            {
                'name': city['name'],
                'gid': city['gid'],
                'center': {
                    'lat': city['center_lat'],
                    'lng': city['center_lng']
                }
            }
            for city in cities
        ]

        return jsonify({
            'status': 'success',
            'data': {
                'district': district,
                'total_cities': len(city_list),
                'cities': city_list
            }
        }), 200

    except Exception as e:
        print(f"Error getting cities: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get cities: {str(e)}'
        }), 500


@cities_bp.route('/districts', methods=['GET'])
def get_districts():
    """
    Get all available districts

    Example: /api/districts
    """
    try:
        districts = data_loader.city_loader.get_all_districts()

        return jsonify({
            'status': 'success',
            'data': {
                'total': len(districts),
                'districts': districts
            }
        }), 200

    except Exception as e:
        print(f"Error getting districts: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get districts: {str(e)}'
        }), 500


@cities_bp.route('/city/details', methods=['GET'])
def get_city_details():
    """
    Get detailed info about a specific city including geometry

    Query params:
    - gid: City GID (required)

    Example: /api/city/details?gid=LKA.14.5_1
    """
    try:
        gid = request.args.get('gid')

        if not gid:
            return jsonify({
                'status': 'error',
                'message': 'GID parameter is required'
            }), 400

        # Get city data
        city = data_loader.city_loader.get_city_by_gid(gid)

        if not city:
            return jsonify({
                'status': 'error',
                'message': f'City not found: {gid}'
            }), 404

        # Get geometry
        geometry = data_loader.city_loader.get_city_geometry(gid)

        response_data = {
            'name': city['name'],
            'district': city['district'],
            'gid': city['gid'],
            'center': {
                'lat': city['center_lat'],
                'lng': city['center_lng']
            }
        }

        # Add geometry if available
        if geometry:
            response_data['geometry'] = geometry.__geo_interface__

        return jsonify({
            'status': 'success',
            'data': response_data
        }), 200

    except Exception as e:
        print(f"Error getting city details: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get city details: {str(e)}'
        }), 500