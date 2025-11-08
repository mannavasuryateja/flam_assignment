#!/usr/bin/env python3
"""
Demo script to showcase QueueCTL functionality
"""
import json
import subprocess
import sys
import time
from pathlib import Path

PY = sys.executable

def run_cmd(cmd_list):
    """Run a command and display output"""
    print(f"\n{'='*60}")
    print(f"> {' '.join(cmd_list)}")
    print('='*60)
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def main():
    print("\n" + "="*60)
    print("QueueCTL - Demo Example")
    print("="*60)
    
    # Step 1: Show initial status
    print("\n[Step 1] Initial Status")
    run_cmd([PY, "queuectl.py", "status"])
    
    # Step 2: Enqueue some jobs
    print("\n[Step 2] Enqueuing Jobs")
    
    jobs = [
        {"id": "demo_success1", "command": "echo Hello from QueueCTL!", "max_retries": 3},
        {"id": "demo_success2", "command": "echo This job will succeed", "max_retries": 3},
        {"id": "demo_fail", "command": "cmd /c exit 1", "max_retries": 2},
        {"id": "demo_sleep", "command": "timeout /t 2 /nobreak", "max_retries": 3},
    ]
    
    for job in jobs:
        job_json = json.dumps(job)
        run_cmd([PY, "queuectl.py", "enqueue", job_json])
    
    # Step 3: Show pending jobs
    print("\n[Step 3] Pending Jobs")
    run_cmd([PY, "queuectl.py", "list", "--state", "pending"])
    
    # Step 4: Show status
    print("\n[Step 4] Status After Enqueuing")
    run_cmd([PY, "queuectl.py", "status"])
    
    # Step 5: Start workers
    print("\n[Step 5] Starting Workers (will run for 8 seconds)")
    print("Starting 2 workers to process jobs...")
    worker_proc = subprocess.Popen([PY, "queuectl.py", "worker", "start", "--count", "2"])
    
    # Wait for workers to process jobs
    time.sleep(8)
    
    # Stop workers
    print("\nStopping workers...")
    worker_proc.terminate()
    worker_proc.wait(timeout=5)
    
    # Step 6: Show status after processing
    print("\n[Step 6] Status After Processing")
    run_cmd([PY, "queuectl.py", "status"])
    
    # Step 7: Show completed jobs
    print("\n[Step 7] Completed Jobs")
    run_cmd([PY, "queuectl.py", "list", "--state", "completed"])
    
    # Step 8: Show failed jobs (if any)
    print("\n[Step 8] Failed Jobs (retryable)")
    run_cmd([PY, "queuectl.py", "list", "--state", "failed"])
    
    # Step 9: Show DLQ
    print("\n[Step 9] Dead Letter Queue")
    run_cmd([PY, "queuectl.py", "dlq", "list"])
    
    # Step 10: Show configuration
    print("\n[Step 10] Current Configuration")
    run_cmd([PY, "queuectl.py", "config", "show"])
    
    # Step 11: Show job logs example
    print("\n[Step 11] Job Log Paths")
    run_cmd([PY, "queuectl.py", "logs", "demo_success1"])
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    print("\nYou can now:")
    print("  - Check logs in data/logs/ directory")
    print("  - Start web dashboard: python queuectl.py web")
    print("  - Retry DLQ jobs: python queuectl.py dlq retry <job_id>")
    print("="*60)

if __name__ == "__main__":
    main()

