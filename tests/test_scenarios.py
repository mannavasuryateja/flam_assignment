# tests/test_scenarios.py
"""
Quick manual test runner for the main flows.
Run with the venv activated:
  python tests/test_scenarios.py
"""
import json
import subprocess
import sys
from time import sleep
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run(cmd):
    print(">", cmd)
    return subprocess.run(cmd, shell=True)

def main():
    # enqueue success and failure
    ok = json.dumps({"id":"job_success","command":"echo success","max_retries":2})
    bad = json.dumps({"id":"job_fail","command":"cmd /c exit 2","max_retries":2})
    run(f'{PY} core/main.py enqueue "{ok}"')
    run(f'{PY} core/main.py enqueue "{bad}"')

    # start worker in background (Windows-safe)
    p = subprocess.Popen([PY, "core/main.py", "worker", "start", "--count", "2"])
    sleep(6)  # allow processing and retry

    # status + dlq
    run(f"{PY} core/main.py status")
    run(f"{PY} core/main.py dlq list")

    # stop workers
    p.terminate()

if __name__ == "__main__":
    main()
