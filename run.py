"""
Master Runner - Execute all phases of the pipeline
"""

import sys
import subprocess


def run_phase(phase_name, script_path):
    """Run a single phase script"""
    print(f"\n{'='*70}")
    print(f"RUNNING: {phase_name}")
    print('='*70)

    result = subprocess.run(['python', script_path], capture_output=False)

    if result.returncode != 0:
        print(f"\nERROR: {phase_name} failed!")
        return False

    print(f"\n{phase_name} completed successfully!")
    return True


def main():
    """Run all phases"""
    phases = [
        ("Phase 1: Data Preparation", "data_preparation.py"),
        ("Phase 2: Corridor Detection", "corridor_detection.py"),
        ("Phase 3: Model Training", "model_training.py")
    ]

    for phase_name, script_path in phases:
        success = run_phase(phase_name, script_path)
        if not success:
            print(f"\n{'='*70}")
            print("PIPELINE FAILED")
            print('='*70)
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        print("Starting API server...")
        subprocess.run(['python', 'api.py'])
    else:
        main()
