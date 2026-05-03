"""
Run All Microservices Locally (without Docker)
Starts both APIs + optional model training pipeline
"""

import subprocess
import sys
import os
import signal
import time

SERVICES = [
    {
        "name": "Dishan Model (Corridor Service)",
        "cwd": os.path.dirname(os.path.abspath(__file__)),
        "cmd": [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
        "port": 8000,
    },
    {
        "name": "Himashi's Model (Collision Risk Service)",
        "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "Himashi"),
        "cmd": [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001"],
        "port": 8001,
    },
    {
        "name": "Tharushi's Model (Wildlife Conflict Prediction)",
        "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "Tharushi"),
        "cmd": [sys.executable, "app.py"],
        "port": 5001,
    },
    {
        "name": "Kavindu's Model (Wildlife Offence Prediction)",
        "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "Kavindu"),
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"],
        "port": 8002,
    },
]

processes = []


def start_services():
    """Start all microservices as subprocesses"""
    for svc in SERVICES:
        print(f"Starting {svc['name']} on port {svc['port']}...")
        proc = subprocess.Popen(
            svc["cmd"],
            cwd=svc["cwd"],
        )
        processes.append((svc["name"], proc))
        time.sleep(1)

    print("\n" + "=" * 60)
    print("ALL SERVICES RUNNING")
    print("=" * 60)
    print(f"  Dishan Model (Corridor):         http://localhost:8000")
    print(f"  Himashi's Model (Collision Risk): http://localhost:8001")
    print(f"  Tharushi's Model (WC Prediction): http://localhost:5001")
    print(f"  Kavindu's Model (Offence Pred):   http://localhost:8002")
    print(f"\n  Dishan docs:    http://localhost:8000/docs")
    print(f"  Himashi docs:   http://localhost:8001/docs")
    print(f"  Tharushi docs:  http://localhost:5001/")
    print(f"  Kavindu docs:   http://localhost:8002/docs")
    print("=" * 60)
    print("Press Ctrl+C to stop all services\n")


def stop_services():
    """Stop all running services"""
    print("\nStopping all services...")
    for name, proc in processes:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"  Stopped {name}")
    print("All services stopped.")


def train_models():
    """Run model training for both services"""
    print("=" * 60)
    print("TRAINING ALL MODELS")
    print("=" * 60)

    # Train corridor/presence model
    print("\n--- Training Corridor & Presence Model ---")
    root_dir = os.path.dirname(os.path.abspath(__file__))
    result = subprocess.run([sys.executable, "run.py"], cwd=root_dir)
    if result.returncode != 0:
        print("ERROR: Corridor model training failed!")
        return False

    # Train collision risk model
    print("\n--- Training Himashi's Collision Risk Model ---")
    himashi_dir = os.path.join(root_dir, "Himashi")
    result = subprocess.run([sys.executable, "train_model.py"], cwd=himashi_dir)
    if result.returncode != 0:
        print("ERROR: Collision risk model training failed!")
        return False

    # Train Tharushi's model
    print("\n--- Training Tharushi's Wildlife Conflict Model ---")
    tharushi_dir = os.path.join(root_dir, "Tharushi")
    tharushi_train = os.path.join(tharushi_dir, "ml_training")
    if os.path.isdir(tharushi_train):
        result = subprocess.run([sys.executable, "-m", "ml_training.train"], cwd=tharushi_dir)
    else:
        print("   Skipping Tharushi training (no ml_training/train.py found)")

    print("\n" + "=" * 60)
    print("ALL MODELS TRAINED SUCCESSFULLY")
    print("=" * 60)
    return True


def main():
    usage = """
Usage:
  python run_services.py serve    - Start all API microservices
  python run_services.py train    - Train all models
  python run_services.py all      - Train models, then start services
"""
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "train":
        train_models()

    elif command == "serve":
        start_services()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_services()

    elif command == "all":
        if train_models():
            start_services()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_services()
        else:
            print("Training failed. Services not started.")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        print(usage)
        sys.exit(1)


if __name__ == "__main__":
    main()
