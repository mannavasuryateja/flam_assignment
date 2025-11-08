#!/usr/bin/env python3
"""
Quick validation script to verify core functionality.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

def run(cmd_list, check=True):
    """Run a command and return the result."""
    cmd_str = " ".join(cmd_list)
    print(f"\n> {cmd_str}")
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR: Command failed with exit code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False
    print(result.stdout)
    return True

def main():
    print("=" * 60)
    print("QueueCTL Validation Script")
    print("=" * 60)
    
    # Test 1: Enqueue a successful job
    print("\n[Test 1] Enqueue successful job")
    job1 = json.dumps({"id": "val_test1", "command": "echo Validation Test 1"})
    if not run([PY, "queuectl.py", "enqueue", job1]):
        return False
    
    # Test 2: Enqueue a failing job
    print("\n[Test 2] Enqueue failing job (will retry)")
    job2 = json.dumps({"id": "val_test2", "command": "cmd /c exit 1", "max_retries": 2})
    if not run([PY, "queuectl.py", "enqueue", job2]):
        return False
    
    # Test 3: Check status
    print("\n[Test 3] Check status")
    if not run([PY, "queuectl.py", "status"]):
        return False
    
    # Test 4: List jobs
    print("\n[Test 4] List pending jobs")
    if not run([PY, "queuectl.py", "list", "--state", "pending"]):
        return False
    
    # Test 5: Config
    print("\n[Test 5] Test configuration")
    if not run([PY, "queuectl.py", "config", "set", "test_key", "test_value"]):
        return False
    if not run([PY, "queuectl.py", "config", "get", "test_key"]):
        return False
    
    # Test 6: Start workers (briefly)
    print("\n[Test 6] Start workers for 5 seconds")
    proc = subprocess.Popen([PY, "queuectl.py", "worker", "start", "--count", "1"])
    time.sleep(5)
    proc.terminate()
    proc.wait(timeout=5)
    
    # Test 7: Check status after processing
    print("\n[Test 7] Check status after processing")
    if not run([PY, "queuectl.py", "status"]):
        return False
    
    # Test 8: List completed jobs
    print("\n[Test 8] List completed jobs")
    if not run([PY, "queuectl.py", "list", "--state", "completed"], check=False):
        pass  # May be empty
    
    # Test 9: DLQ
    print("\n[Test 9] Check DLQ")
    if not run([PY, "queuectl.py", "dlq", "list"], check=False):
        pass  # May be empty
    
    print("\n" + "=" * 60)
    print("Validation complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

