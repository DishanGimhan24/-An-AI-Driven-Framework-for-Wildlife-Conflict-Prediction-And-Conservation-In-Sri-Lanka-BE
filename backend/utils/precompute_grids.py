import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.rule_based_grid import rule_based_grid


def precompute_grids():
    """Pre-compute rule-based risk grids"""
    print("=" * 60)
    print("Pre-computing Rule-Based Risk Grids")
    print("=" * 60)

    # Generate grids for today and next 6 days
    today = datetime.now()

    print(f"\nGenerating 7-day grids starting from {today.strftime('%Y-%m-%d')}...")
    print("Grid size: 50x50 (2,500 points)")
    print("Method: Rule-based zone classification")
    print("Estimated time: < 10 seconds\n")

    grids = []

    for day_offset in range(7):
        date = today + timedelta(days=day_offset)
        date_str = date.strftime('%Y-%m-%d')

        print(f"\n--- Day {day_offset + 1}/7: {date_str} ---")

        # Generate grid (instant with rule-based)
        grid_data = rule_based_grid.generate_grid(date_str, grid_size=50)
        filepath = rule_based_grid.save_grid(grid_data)

        grids.append({
            'date': date_str,
            'filepath': filepath,
            'summary': grid_data['summary']
        })

    # Print summary
    print("\n" + "=" * 60)
    print("Grid Generation Complete!")
    print("=" * 60)

    for grid in grids:
        print(f"\n{grid['date']}:")
        print(f"  High Risk: {grid['summary']['high_risk_percentage']}%")
        print(f"  Medium Risk: {grid['summary']['medium_risk_percentage']}%")
        print(f"  Low Risk: {grid['summary']['low_risk_percentage']}%")
        print(f"  Avg Risk: {grid['summary']['avg_risk']}")


if __name__ == '__main__':
    precompute_grids()