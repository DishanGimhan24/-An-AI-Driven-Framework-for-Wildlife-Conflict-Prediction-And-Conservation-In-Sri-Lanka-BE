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
        "name": "Corridor Service",
        "cwd": os.path.dirname(os.path.abspath(__file__)),
        "cmd": [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
        "port": 8000,
    },
    {
        "name": "Collision Risk Service",
        "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "Himashi"),
        "cmd": [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001"],
        "port": 8001,
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
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append((svc["name"], proc))
        time.sleep(1)

    print("\n" + "=" * 60)
    print("ALL SERVICES RUNNING")
    print("=" * 60)
    print(f"  Corridor Service:       http://localhost:8000")
    print(f"  Collision Risk Service:  http://localhost:8001")
    print(f"\n  Corridor docs:          http://localhost:8000/docs")
    print(f"  Collision Risk docs:    http://localhost:8001/docs")
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
    print("\n--- Training Collision Risk Model ---")
    himashi_dir = os.path.join(root_dir, "Himashi")
    result = subprocess.run([sys.executable, "train_model.py"], cwd=himashi_dir)
    if result.returncode != 0:
        print("ERROR: Collision risk model training failed!")
        return False

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
