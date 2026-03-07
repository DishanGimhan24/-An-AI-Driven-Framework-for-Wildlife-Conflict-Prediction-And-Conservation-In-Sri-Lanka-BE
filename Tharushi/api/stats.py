from flask import Blueprint, jsonify
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.model_loader import model_loader

stats_bp = Blueprint('stats', __name__)

PREDICTIONS_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'predictions.csv')


@stats_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get system statistics for dashboard

    Returns:
    - Model performance metrics
    - Prediction counts by risk level
    - Recent predictions summary
    """
    try:
        # Get model metrics
        metrics = model_loader.get_metrics()

        # Get prediction statistics
        pred_stats = get_prediction_stats()

        # System status
        status = {
            'model_loaded': model_loader.is_loaded,
            'model_accuracy': metrics.get('test', {}).get('accuracy', 0) if metrics else 0,
            'model_type': 'Random Forest + LSTM',
            'last_updated': datetime.now().isoformat()
        }

        return jsonify({
            'status': 'success',
            'data': {
                'system': status,
                'predictions': pred_stats,
                'model_performance': {
                    'accuracy': round(metrics.get('test', {}).get('accuracy', 0) * 100, 1) if metrics else 0,
                    'precision': round(metrics.get('test', {}).get('precision', 0) * 100, 1) if metrics else 0,
                    'recall': round(metrics.get('test', {}).get('recall', 0) * 100, 1) if metrics else 0,
                    'f1_score': round(metrics.get('test', {}).get('f1_score', 0) * 100, 1) if metrics else 0
                }
            }
        }), 200

    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get statistics: {str(e)}',
            'error_code': 'STATS_ERROR'
        }), 500


def get_prediction_stats():
    """Get statistics from prediction log"""
    try:
        if not os.path.exists(PREDICTIONS_LOG):
            return {
                'total_predictions': 0,
                'high_risk_count': 0,
                'medium_risk_count': 0,
                'low_risk_count': 0,
                'recent_predictions': []
            }

        df = pd.read_csv(PREDICTIONS_LOG)

        # Count by risk level
        risk_counts = df['risk_level'].value_counts().to_dict()

        # Get recent predictions (last 10)
        recent = df.tail(10).to_dict('records')

        # Get predictions from last 7 days
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        last_week = datetime.now() - timedelta(days=7)
        recent_week = df[df['timestamp'] >= last_week]

        return {
            'total_predictions': len(df),
            'high_risk_count': risk_counts.get('HIGH', 0),
            'medium_risk_count': risk_counts.get('MEDIUM', 0),
            'low_risk_count': risk_counts.get('LOW', 0),
            'predictions_last_7_days': len(recent_week),
            'recent_predictions': recent[::-1]  # Reverse to show newest first
        }

    except Exception as e:
        print(f"Error reading prediction log: {e}")
        return {
            'total_predictions': 0,
            'high_risk_count': 0,
            'medium_risk_count': 0,
            'low_risk_count': 0,
            'recent_predictions': []
        }


@stats_bp.route('/stats/summary', methods=['GET'])
def get_summary():
    """Get quick summary stats for dashboard cards"""
    try:
        pred_stats = get_prediction_stats()
        metrics = model_loader.get_metrics()

        return jsonify({
            'status': 'success',
            'data': {
                'high_risk_areas': pred_stats['high_risk_count'],
                'medium_risk_areas': pred_stats['medium_risk_count'],
                'low_risk_areas': pred_stats['low_risk_count'],
                'total_predictions': pred_stats['total_predictions'],
                'model_accuracy': round(metrics.get('test', {}).get('accuracy', 0) * 100, 1) if metrics else 0
            }
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'error_code': 'SUMMARY_ERROR'
        }), 500