import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import warnings

warnings.filterwarnings('ignore')
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)
from flask import Flask, jsonify
from flask_cors import CORS

from api.forecast import forecast_bp
from api.predict import predict_bp
from api.stats import stats_bp
from api.historical import historical_bp
from config import FLASK_HOST, FLASK_PORT, DEBUG
from data_processing.data_loader import data_loader
from ml.model_loader import model_loader
from api.heatmap import heatmap_bp
from api.cities import cities_bp

# Create Flask app
app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(predict_bp, url_prefix='/api')
app.register_blueprint(historical_bp, url_prefix='/api')
app.register_blueprint(forecast_bp, url_prefix='/api')
app.register_blueprint(heatmap_bp, url_prefix='/api')
app.register_blueprint(stats_bp, url_prefix='/api')
app.register_blueprint(cities_bp, url_prefix='/api')


@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'message': 'Wildlife Conflict Prediction API',
        'status': 'running',
        'version': '1.0.0'
    })


@app.route('/api/health')
def health():
    """Detailed health check"""
    return jsonify({
        'api': 'running',
        'model_loaded': model_loader.is_loaded,
        'data_loaded': data_loader.elephant_distribution is not None
    })


@app.route('/api/status')
def status():
    """System status and loaded data info"""
    status_info = {
        'model': {
            'loaded': model_loader.is_loaded,
            'metrics': model_loader.get_metrics() if model_loader.is_loaded else None
        },
        'datasets': {
            'elephant_distribution': data_loader.elephant_distribution is not None,
            'protected_areas': data_loader.protected_areas is not None,
            'power_fences': data_loader.power_fences is not None,
            'roads': data_loader.roads is not None,
            'railways': data_loader.railways is not None,
            'rainfall_data': data_loader.rainfall_data is not None,
            'tracking_data': data_loader.tracking_data is not None
        }
    }

    return jsonify(status_info)


if __name__ == '__main__':
    # Load all data before starting server
    data_loader.load_all()

    # Run Flask app
    print(f"Starting Flask server on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG)