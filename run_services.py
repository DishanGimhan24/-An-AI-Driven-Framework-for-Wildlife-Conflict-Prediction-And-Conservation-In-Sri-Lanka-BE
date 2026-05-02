#!/usr/bin/env python3
"""
run_services.py — Wildlife System Service Manager
Starts, stops, and monitors all backend microservices.

Usage:
  python run_services.py all          # Start all services simultaneously
  python run_services.py list         # Show all services and their ports
  python run_services.py status       # Show which services are running
  python run_services.py stop         # Stop all running services
  python run_services.py <name>       # Start one service by name

Service names: corridor, himashi, tharushi, kavindu, kavindu-v2, gateway

NOTE — Port assignments:
  corridor    : 8000   (api.py — Corridor & Presence)
  himashi     : 8001   (Himashi/api.py — Collision Risk)
  tharushi    : 5001   (Tharushi/app.py — Flask, Wildlife Conflict)
  kavindu     : 8002   (Kavindu/app/main.py — Offence Prediction v1)
  kavindu-v2  : 8003   (Kavindu/app/main_v2.py — Offence Prediction v2 XGBoost)
  gateway     : 8080   (gateway.py — API Gateway)

  ⚠  kavindu-v2 runs on 8003 (not 8000) to avoid conflict with corridor.
     Update VITE_API_URL=http://localhost:8003/api in your frontend .env
     if you need the PredictPage v2 to talk to kavindu-v2.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ── ANSI terminal colours (macOS / Linux) ───────────────────────────────
class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


def _g(s):  return f"{C.GREEN}{s}{C.RESET}"
def _r(s):  return f"{C.RED}{s}{C.RESET}"
def _y(s):  return f"{C.YELLOW}{s}{C.RESET}"
def _c(s):  return f"{C.CYAN}{s}{C.RESET}"
def _b(s):  return f"{C.BOLD}{s}{C.RESET}"
def _d(s):  return f"{C.DIM}{s}{C.RESET}"


# ── Paths ────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.resolve()
LOGS_DIR = ROOT / "logs"
PID_FILE = ROOT / ".service_pids.json"


# ── Service definitions ──────────────────────────────────────────────────
def _py(*args):
    return [sys.executable, *args]


def _uv(module, port, extra_flags=None):
    cmd = [
        sys.executable, "-m", "uvicorn",
        module,
        "--host", "0.0.0.0",
        f"--port={port}",
        "--reload",
    ]
    if extra_flags:
        cmd.extend(extra_flags)
    return cmd


SERVICES = [
    {
        "name":  "corridor",
        "label": "Dishan — Corridor & Presence API",
        "cmd":   _uv("api:app", 8000),
        "cwd":   ROOT,
        "port":  8000,
        "docs":  "http://localhost:8000/docs",
    },
    {
        "name":  "himashi",
        "label": "Himashi — Collision Risk API",
        "cmd":   _uv("api:app", 8001),
        "cwd":   ROOT / "Himashi",
        "port":  8001,
        "docs":  "http://localhost:8001/docs",
    },
    {
        "name":  "tharushi",
        "label": "Tharushi — Wildlife Conflict Prediction (Flask)",
        "cmd":   _py("app.py"),
        "cwd":   ROOT / "Tharushi",
        "port":  5001,
        "docs":  "http://localhost:5001/",
    },
    {
        "name":  "kavindu",
        "label": "Kavindu v1 — Wildlife Offence Prediction",
        "cmd":   _uv("app.main:app", 8002),
        "cwd":   ROOT / "Kavindu",
        "port":  8002,
        "docs":  "http://localhost:8002/docs",
    },
    {
        "name":  "kavindu-v2",
        "label": "Kavindu v2 — Offence Prediction (XGBoost)",
        "cmd":   _uv("main_v2:app", 8003),
        "cwd":   ROOT / "Kavindu" / "app",
        "port":  8003,
        "docs":  "http://localhost:8003/docs",
    },
    {
        "name":  "gateway",
        "label": "API Gateway (aggregates corridor + himashi)",
        "cmd":   _uv("gateway:app", 8080),
        "cwd":   ROOT,
        "port":  8080,
        "docs":  "http://localhost:8080/docs",
    },
]

SERVICE_MAP = {svc["name"]: svc for svc in SERVICES}


# ── Helpers ──────────────────────────────────────────────────────────────
def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def load_pids() -> dict:
    if PID_FILE.exists():
        try:
            return json.loads(PID_FILE.read_text())
        except Exception:
            pass
    return {}


def save_pids(pids: dict):
    PID_FILE.write_text(json.dumps(pids, indent=2))


def clear_pids():
    if PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)


def ensure_logs():
    LOGS_DIR.mkdir(exist_ok=True)


def log_path(name: str) -> Path:
    return LOGS_DIR / f"{name}.log"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sep(char="─", width=62):
    return char * width


# ── Commands ─────────────────────────────────────────────────────────────
def cmd_list():
    print(f"\n{_b('Available services:')}\n")
    print(f"  {'NAME':<16} {'PORT':<8} {'STATUS':<20} LABEL")
    print(f"  {sep('─', 72)}")
    for svc in SERVICES:
        running = is_port_in_use(svc["port"])
        status  = _g("● running") if running else _d("○ stopped")
        print(f"  {_c(svc['name']):<25} {svc['port']:<8} {status:<29} {svc['label']}")
    print()


def cmd_status():
    pids = load_pids()
    print(f"\n{_b('Service status  ')} {_d(f'({now()})')}\n")
    for svc in SERVICES:
        name    = svc["name"]
        port    = svc["port"]
        port_up = is_port_in_use(port)
        pid     = pids.get(name)
        proc_up = pid_alive(pid) if pid else False

        if port_up and proc_up:
            state = _g(f"● RUNNING   pid {pid}")
        elif port_up:
            state = _y(f"⚡ PORT IN USE (external process — not tracked)")
        elif proc_up:
            state = _y(f"? PROCESS ALIVE but port {port} not responding  pid {pid}")
        else:
            state = _r("○ STOPPED")

        print(f"  {_c(name):<25} :{port}  {state}")
        if port_up:
            print(f"  {' '*25}       {_d(svc['docs'])}")
    print()


def _launch(svc: dict, procs: list, pids: dict) -> bool:
    """Launch a single service. Returns True if started, False if skipped."""
    name  = svc["name"]
    port  = svc["port"]
    label = svc["label"]

    if is_port_in_use(port):
        print(f"  {_y('⚠')}  Port {port} already in use — {_y('skipping')} {name}")
        return False

    ensure_logs()
    log_file = open(log_path(name), "a", buffering=1)
    log_file.write(f"\n{'='*60}\n[{now()}] Starting {label}\n{'='*60}\n")

    proc = subprocess.Popen(
        [str(c) for c in svc["cmd"]],
        cwd=str(svc["cwd"]),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    procs.append({"name": name, "proc": proc, "log": log_file, "svc": svc})
    pids[name] = proc.pid

    print(
        f"  {_g('✓')}  {_b(name):<20} :{port}  "
        f"{_d(f'pid {proc.pid} · log: logs/{name}.log')}"
    )
    return True


def _build_shutdown(procs: list, pids: dict):
    """Return a shutdown function that cleans up all given procs."""
    def _shutdown(sig=None, frame=None):
        print(f"\n{_y('Shutting down...')}")
        for entry in procs:
            entry["proc"].terminate()
            try:
                entry["proc"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                entry["proc"].kill()
            try:
                entry["log"].close()
            except Exception:
                pass
            print(f"  {_r('●')}  Stopped {entry['name']}")
        clear_pids()
        print(_g("\nAll services stopped.\n"))
        sys.exit(0)
    return _shutdown


def cmd_all():
    procs: list = []
    pids:  dict = {}

    print(f"\n{_b('Starting all services...')}\n")

    for svc in SERVICES:
        _launch(svc, procs, pids)

    if not procs:
        print(_r("\nNo services were started (all ports already in use or launch failed)."))
        sys.exit(1)

    save_pids(pids)

    print(f"\n{sep('═')}")
    print(_b("  ALL SERVICES RUNNING"))
    print(sep("═"))
    for svc in SERVICES:
        if svc["name"] in pids:
            marker = _g("●")
            print(f"  {marker}  {svc['label']:<48} http://localhost:{svc['port']}")
    started_count = len(pids)
    skipped_count = len(SERVICES) - started_count
    if skipped_count:
        print(f"\n  {_y(f'{skipped_count} service(s) skipped — port already in use')}")
    print(f"\n  Logs : {_d(str(LOGS_DIR))}")
    print(f"  Press {_b('Ctrl+C')} to stop all services")
    print(sep("═") + "\n")

    shutdown = _build_shutdown(procs, pids)
    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    MAX_RETRIES       = 3
    FAST_CRASH_WINDOW = 30  # seconds
    crash_counts      = {entry["name"]: {"count": 0, "last_crash": 0.0} for entry in procs}
    given_up          = set()

    try:
        while True:
            time.sleep(2)
            # Auto-restart any crashed service (with per-service retry cap)
            for entry in list(procs):
                if entry["proc"].poll() is not None:
                    name = entry["name"]
                    if name in given_up:
                        continue
                    code    = entry["proc"].returncode
                    tracker = crash_counts[name]
                    t       = time.time()
                    if t - tracker["last_crash"] < FAST_CRASH_WINDOW:
                        tracker["count"] += 1
                    else:
                        tracker["count"] = 1
                    tracker["last_crash"] = t

                    if tracker["count"] > MAX_RETRIES:
                        print(_r(
                            f"  ✗  {name} crashed {MAX_RETRIES}x in {FAST_CRASH_WINDOW}s "
                            f"— giving up. Check logs/{name}.log"
                        ))
                        given_up.add(name)
                        pids.pop(name, None)
                        save_pids(pids)
                        continue

                    print(_y(f"  ⚠  {name} exited (code {code}) — restarting ({tracker['count']}/{MAX_RETRIES})..."))
                    log = entry["log"]
                    log.write(f"\n[{now()}] Crashed (code {code}), restarting ({tracker['count']}/{MAX_RETRIES})...\n")
                    new_proc = subprocess.Popen(
                        [str(c) for c in entry["svc"]["cmd"]],
                        cwd=str(entry["svc"]["cwd"]),
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                    entry["proc"]  = new_proc
                    pids[name]     = new_proc.pid
                    save_pids(pids)
                    print(_g(f"  ✓  {name} restarted (pid {new_proc.pid})"))
    except KeyboardInterrupt:
        shutdown()


def cmd_start_one(name: str):
    if name not in SERVICE_MAP:
        names = ", ".join(_c(s["name"]) for s in SERVICES)
        print(_r(f"\nUnknown service: '{name}'"))
        print(f"Available names: {names}\n")
        sys.exit(1)

    svc   = SERVICE_MAP[name]
    procs = []
    pids  = load_pids()

    print(f"\n{_b('Starting service...')}\n")
    started = _launch(svc, procs, pids)
    if not started:
        sys.exit(1)

    save_pids(pids)

    print(f"\n  Docs : {svc['docs']}")
    print(f"  Log  : {_d(str(log_path(name)))}")
    print(f"  Press {_b('Ctrl+C')} to stop\n")

    shutdown = _build_shutdown(procs, pids)
    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
            if procs and procs[0]["proc"].poll() is not None:
                print(_r(f"\n{name} exited unexpectedly. Check logs/{name}.log"))
                pids.pop(name, None)
                save_pids(pids)
                sys.exit(1)
    except KeyboardInterrupt:
        shutdown()


def cmd_stop():
    pids = load_pids()

    if pids:
        print(f"\n{_b('Stopping tracked services...')}\n")
        for name, pid in list(pids.items()):
            if pid_alive(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.4)
                    if pid_alive(pid):
                        os.kill(pid, signal.SIGKILL)
                    print(f"  {_r('●')}  Stopped {name} (pid {pid})")
                except Exception as e:
                    print(f"  {_y('?')}  Could not stop {name} (pid {pid}): {e}")
            else:
                print(f"  {_d('○')}  {name} was already stopped (pid {pid})")
        clear_pids()

    else:
        print(f"\n{_y('No tracked services — falling back to port-based kill...')}\n")
        stopped = 0
        for svc in SERVICES:
            if is_port_in_use(svc["port"]):
                result = subprocess.run(
                    ["lsof", "-ti", f":{svc['port']}"],
                    capture_output=True, text=True,
                )
                for pid_str in result.stdout.strip().splitlines():
                    pid_str = pid_str.strip()
                    if pid_str.isdigit():
                        try:
                            os.kill(int(pid_str), signal.SIGTERM)
                            print(f"  {_r('●')}  Stopped {svc['name']} via port {svc['port']} (pid {pid_str})")
                            stopped += 1
                        except Exception:
                            pass
        if stopped == 0:
            print(_d("  Nothing to stop.\n"))
            return

    print(_g("\nDone.\n"))


# ── Usage / entry point ──────────────────────────────────────────────────
def _usage():
    names = "  ".join(_c(s["name"]) for s in SERVICES)
    return f"""
{_b('Wildlife System Service Manager')}

{_b('Usage:')}
  python run_services.py {_c('all')}           Start all services simultaneously
  python run_services.py {_c('list')}          Show all services and their ports
  python run_services.py {_c('status')}        Show which services are running
  python run_services.py {_c('stop')}          Stop all running services
  python run_services.py {_c('<name>')}        Start one specific service

{_b('Service names:')}
  {names}

{_b('Ports:')}
  corridor   → 8000    himashi  → 8001    tharushi → 5001
  kavindu    → 8002    kavindu-v2 → 8003  gateway  → 8080

{_b('Logs:')}  {_d(str(LOGS_DIR))}
"""


def main():
    if len(sys.argv) < 2:
        print(_usage())
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if   cmd == "all":    cmd_all()
    elif cmd == "list":   cmd_list()
    elif cmd == "status": cmd_status()
    elif cmd == "stop":   cmd_stop()
    else:                 cmd_start_one(cmd)


if __name__ == "__main__":
    main()
