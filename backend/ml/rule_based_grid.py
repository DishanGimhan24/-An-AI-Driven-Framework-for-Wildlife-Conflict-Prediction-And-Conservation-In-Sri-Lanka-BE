import json
import os
import sys
import numpy as np
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.risk_zones import get_risk_level_for_location
from config import MODELS_DIR


class RuleBasedGrid:
    """Generate risk grid using rule-based zone classification"""

    def __init__(self):
        # Sri Lanka bounds
        self.lat_min = 5.9
        self.lat_max = 9.9
        self.lon_min = 79.4
        self.lon_max = 82.0

    def generate_grid(self, date, grid_size=30):
        """
        Generate rule-based risk grid
        Much faster than ML-based (instant vs minutes)
        """
        print(f"Generating {grid_size}x{grid_size} rule-based grid for {date}...")

        # Create grid points
        lat_points = np.linspace(self.lat_min, self.lat_max, grid_size)
        lon_points = np.linspace(self.lon_min, self.lon_max, grid_size)

        grid_data = []

        # Generate risk for each point
        for lat in lat_points:
            for lon in lon_points:
                result = get_risk_level_for_location(lat, lon)

                grid_data.append({
                    'lat': round(lat, 4),
                    'lon': round(lon, 4),
                    'risk_score': result['risk_score'],
                    'risk_level': result['risk_level'],
                    'zone_name': result['zone_name']
                })

        print(f"✓ Generated {len(grid_data)} grid points")

        return {
            'date': date,
            'grid_size': grid_size,
            'method': 'rule_based',
            'bounds': {
                'lat_min': self.lat_min,
                'lat_max': self.lat_max,
                'lon_min': self.lon_min,
                'lon_max': self.lon_max
            },
            'total_points': len(grid_data),
            'data': grid_data,
            'summary': self._calculate_summary(grid_data)
        }

    def _calculate_summary(self, grid_data):
        """Calculate summary statistics"""
        if not grid_data:
            return {}

        risk_scores = [point['risk_score'] for point in grid_data]

        high_count = sum(1 for p in grid_data if p['risk_level'] == 'HIGH')
        medium_count = sum(1 for p in grid_data if p['risk_level'] == 'MEDIUM')
        low_count = sum(1 for p in grid_data if p['risk_level'] == 'LOW')

        return {
            'avg_risk': round(np.mean(risk_scores), 3),
            'max_risk': round(np.max(risk_scores), 3),
            'min_risk': round(np.min(risk_scores), 3),
            'high_risk_points': high_count,
            'medium_risk_points': medium_count,
            'low_risk_points': low_count,
            'high_risk_percentage': round(high_count / len(grid_data) * 100, 1),
            'medium_risk_percentage': round(medium_count / len(grid_data) * 100, 1),
            'low_risk_percentage': round(low_count / len(grid_data) * 100, 1)
        }

    def save_grid(self, grid_data, filename=None):
        """Save grid to JSON"""
        if filename is None:
            filename = f"risk_grid_{grid_data['date']}.json"

        grids_dir = os.path.join(MODELS_DIR, 'grids')
        os.makedirs(grids_dir, exist_ok=True)

        filepath = os.path.join(grids_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(grid_data, f, indent=2)

        print(f"✓ Grid saved to: {filepath}")
        return filepath


# Global instance
rule_based_grid = RuleBasedGrid()