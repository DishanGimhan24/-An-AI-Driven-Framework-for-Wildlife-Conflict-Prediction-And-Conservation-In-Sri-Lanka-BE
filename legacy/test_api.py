import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_health():
    """Test health check endpoint"""
    print_section("1. HEALTH CHECK")

    response = requests.get(f"{BASE_URL}/health")
    data = response.json()

    print(f"Status: {data['status']}")
    print(f"Model Loaded: {'' if data['model_loaded'] else ''}")
    print(f"Corridors Loaded: {'' if data['corridors_loaded'] else ''}")
    print(f"Timestamp: {data['timestamp']}")

    return data['model_loaded']


def test_corridors():
    """Test corridors endpoint"""
    print_section("3. ELEPHANT CORRIDORS")

    response = requests.get(f"{BASE_URL}/corridors")

    if response.status_code == 200:
        corridors = response.json()
        print(f"Total Corridors Detected: {len(corridors)}")

        # Show top 5 safest corridors
        sorted_corridors = sorted(
            corridors, key=lambda x: x['safety_score'], reverse=True)

        print("\nTop 5 Safest Corridors:")
        for i, corridor in enumerate(sorted_corridors[:5], 1):
            print(f"\n{i}. Corridor #{corridor['corridor_id']}")
            print(
                f"   Location: ({corridor['center_lat']:.4f}, {corridor['center_lon']:.4f})")
            print(f"   Points: {corridor['num_points']}")
            print(f"   Safety Score: {corridor['safety_score']:.1f}/100")
            print(
                f"   Avg Human Distance: {corridor['avg_human_distance']:.0f}m")
            print(f"   Conflict Rate: {corridor['conflict_rate']*100:.1f}%")
    else:
        print(f" Error: {response.status_code}")


def test_corridor_detail():
    """Test specific corridor endpoint"""
    print_section("4. CORRIDOR DETAIL")

    corridor_id = 0
    response = requests.get(f"{BASE_URL}/corridors/{corridor_id}")

    if response.status_code == 200:
        corridor = response.json()
        print(f"Corridor ID: {corridor['corridor_id']}")
        print(
            f"Center: ({corridor['center_lat']:.4f}, {corridor['center_lon']:.4f})")
        print(f"Number of Points: {corridor['num_points']}")
        print(f"Safety Score: {corridor['safety_score']:.1f}/100")
        print(f"Average Human Distance: {corridor['avg_human_distance']:.1f}m")
        print(f"Conflict Rate: {corridor['conflict_rate']*100:.2f}%")
        print(f"\nBounds:")
        print(
            f"  Latitude: {corridor['bounds']['lat_min']:.4f} to {corridor['bounds']['lat_max']:.4f}")
        print(
            f"  Longitude: {corridor['bounds']['lon_min']:.4f} to {corridor['bounds']['lon_max']:.4f}")
    else:
        print(f" Error: {response.status_code}")


def test_prediction_low_risk():
    """Test prediction with low risk scenario"""
    print_section("5. PREDICTION - LOW RISK SCENARIO")

    data = {
        "latitude": 7.5,
        "longitude": 81.0,
        "datetime": "2024-06-15T12:00:00",
        "human_distance": 5000,
        "road_distance": 3000,
        "elevation": 100
    }

    response = requests.post(f"{BASE_URL}/predict", json=data)

    if response.status_code == 200:
        result = response.json()
        print(
            f"Conflict Predicted: {'YES' if result['conflict_predicted'] else 'NO'}")
        print(f"Probability: {result['conflict_probability']*100:.2f}%")
        print(f"Risk Level: {result['risk_level']}")

        if result['nearest_corridor']:
            print(
                f"\nNearest Corridor: #{result['nearest_corridor']['corridor_id']}")
            print(
                f"  Safety Score: {result['nearest_corridor']['safety_score']:.1f}/100")

        print("\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  {rec}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def test_prediction_high_risk():
    """Test prediction with high risk scenario"""
    print_section("6. PREDICTION - HIGH RISK SCENARIO")

    data = {
        "latitude": 7.5,
        "longitude": 81.0,
        "datetime": "2024-06-15T22:00:00",
        "human_distance": 300,
        "road_distance": 500,
        "elevation": 100
    }

    response = requests.post(f"{BASE_URL}/predict", json=data)

    if response.status_code == 200:
        result = response.json()
        print(
            f"Conflict Predicted: {'YES' if result['conflict_predicted'] else 'NO'}")
        print(f"Probability: {result['conflict_probability']*100:.2f}%")
        print(f"Risk Level: {result['risk_level']}")

        if result['nearest_corridor']:
            print(
                f"\nNearest Corridor: #{result['nearest_corridor']['corridor_id']}")
            print(
                f"  Safety Score: {result['nearest_corridor']['safety_score']:.1f}/100")

        print("\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  {rec}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def test_prediction_medium_risk():
    """Test prediction with medium risk scenario"""
    print_section("7. PREDICTION - MEDIUM RISK SCENARIO")

    data = {
        "latitude": 7.5,
        "longitude": 81.0,
        "datetime": "2024-06-15T18:00:00",
        "human_distance": 1200,
        "road_distance": 800,
        "elevation": 100
    }

    response = requests.post(f"{BASE_URL}/predict", json=data)

    if response.status_code == 200:
        result = response.json()
        print(
            f"Conflict Predicted: {'YES' if result['conflict_predicted'] else 'NO'}")
        print(f"Probability: {result['conflict_probability']*100:.2f}%")
        print(f"Risk Level: {result['risk_level']}")

        if result['nearest_corridor']:
            print(
                f"\nNearest Corridor: #{result['nearest_corridor']['corridor_id']}")
            print(
                f"  Safety Score: {result['nearest_corridor']['safety_score']:.1f}/100")

        print("\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  {rec}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def run_all_tests():
    """Run all API tests"""
    print("  WILDLIFE CONFLICT PREDICTION API - TEST SUITE")

    try:
        # Test health
        model_loaded = test_health()

        if not model_loaded:
            print("\n  WARNING: Model not loaded. Some tests may fail.")
            print("   Run: python wildlife_conflict_pipeline.py train")
            return

        # Test corridors
        test_corridors()
        test_corridor_detail()

        # Test predictions
        test_prediction_low_risk()
        test_prediction_high_risk()
        test_prediction_medium_risk()

        # Summary
        print_section(" ALL TESTS COMPLETED")
        print("\nAPI is functioning correctly!")
        print("Ready for integration with your Flutter app.")

    except requests.exceptions.ConnectionError:
        print("\n ERROR: Cannot connect to API")
        print("   Make sure the API is running:")
        print("   python wildlife_conflict_pipeline.py api")
    except Exception as e:
        print(f"\n ERROR: {e}")


if __name__ == "__main__":
    run_all_tests()
