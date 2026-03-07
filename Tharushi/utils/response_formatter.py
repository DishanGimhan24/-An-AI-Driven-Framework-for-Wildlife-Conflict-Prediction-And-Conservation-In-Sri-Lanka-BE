from datetime import datetime

from flask import jsonify


def success_response(data, message="Success"):
    """Format success response"""
    return jsonify({
        'status': 'success',
        'message': message,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }), 200

def error_response(message, status_code=400):
    """Format error response"""
    return jsonify({
        'status': 'error',
        'message': message,
        'timestamp': datetime.now().isoformat()
    }), status_code

def get_risk_level(risk_score, threshold_high=0.7, threshold_medium=0.4):
    """Convert risk score to level"""
    if risk_score >= threshold_high:
        return 'HIGH'
    elif risk_score >= threshold_medium:
        return 'MEDIUM'
    else:
        return 'LOW'