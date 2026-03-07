"""
Quick test script to verify backend setup
Run this after installing dependencies
"""

import os


def check_dependencies():
    """Check if all dependencies are installed"""
    print("Checking dependencies...")

    required = [
        'flask', 'flask_cors', 'pandas', 'numpy',
        'geopandas', 'shapely', 'scikit-learn', 'joblib'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} - MISSING")

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("\nAll dependencies installed ✓")
    return True


def check_dataset():
    """Check if Final Dataset folder exists"""
    print("\nChecking dataset...")

    dataset_path = 'Final Dataset'

    if not os.path.exists(dataset_path):
        print(f"✗ '{dataset_path}' folder not found")
        return False

    required_folders = [
        'Elephant Deaths',
        'elephant distribution',
        'Elephant Tracking',
        'Power Fence',
        'Protected Areas - Protected Planet',
        'Road & Railway data'
    ]

    for folder in required_folders:
        folder_path = os.path.join(dataset_path, folder)
        if os.path.exists(folder_path):
            print(f"✓ {folder}")
        else:
            print(f"⚠ {folder} - not found")

    return True


def check_models():
    """Check if trained models exist"""
    print("\nChecking models...")

    models_path = 'models'

    if not os.path.exists(models_path):
        print(f"⚠ '{models_path}' folder not found")
        print("Create it with: mkdir models")
        return False

    required_files = [
        'random_forest_model.pkl',
        'scaler.pkl',
        'model_metrics.json'
    ]

    all_exist = True
    for file in required_files:
        file_path = os.path.join(models_path, file)
        if os.path.exists(file_path):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - not found")
            all_exist = False

    if not all_exist:
        print("\nTrain the model first:")
        print("python ml_training/train_model.py")
        return False

    return True


def main():
    print("=" * 50)
    print("Wildlife Conflict Prediction - Setup Check")
    print("=" * 50 + "\n")

    deps_ok = check_dependencies()
    dataset_ok = check_dataset()
    models_ok = check_models()

    print("\n" + "=" * 50)
    if deps_ok and dataset_ok and models_ok:
        print("✓ Setup complete! Ready to run:")
        print("  python app.py")
    else:
        print("⚠ Setup incomplete. Fix the issues above.")
    print("=" * 50)


if __name__ == '__main__':
    main()