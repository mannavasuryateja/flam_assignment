# core/worker.py
import multiprocessing as mp
import os
import subprocess
import time
from datetime import datetime

def utcnow() -> str:
    return datetime.utcnow().isoformat() + "Z"

class WorkerProcess(mp.Process):
    def __init__(self, name, store, config, stop_event):
        super().__init__()
        self.name = name
        self.store = store
        self.config = config
        self.stop_event = stop_event

    def run(self):
        poll_ms = int(self.config.get("poll_interval_ms") or 500)
        default_timeout = int(self.config.get("default_timeout_secs") or 60)
        while not self.stop_event.is_set():
            job = self.store.claim_next(self.name)
            if not job:
                time.sleep(poll_ms / 1000.0)
                continue

            job_id = job["id"]
            cmd = job["command"]
            timeout = int(job.get("timeout_secs") or 0) or default_timeout
            stdout_path, stderr_path = self.store.log_paths_for(job_id)

            started = utcnow()
            exit_code = None
            bytes_out = 0
            bytes_err = 0
            try:
                # Capture stdout/stderr for logs
                with open(stdout_path, "ab") as out_f, open(stderr_path, "ab") as err_f:
                    proc = subprocess.run(
                        cmd,
                        shell=True,              # On Windows this uses cmd.exe by default
                        capture_output=True,     # capture first, then append
                        timeout=timeout
                    )
                    if proc.stdout:
                        out_f.write(proc.stdout)
                        bytes_out = len(proc.stdout)
                    if proc.stderr:
                        err_f.write(proc.stderr)
                        bytes_err = len(proc.stderr)
                    exit_code = proc.returncode
            except subprocess.TimeoutExpired as e:
                with open(stderr_path, "ab") as err_f:
                    msg = f"timeout after {timeout}s"
                    err_f.write(msg.encode("utf-8") + b"\n")
                    bytes_err = len(msg) + 1
                exit_code = 124  # conventional timeout code
            except Exception as e:
                with open(stderr_path, "ab") as err_f:
                    msg = f"exception: {e}"
                    err_f.write(msg.encode("utf-8") + b"\n")
                    bytes_err = len(msg) + 1
                exit_code = 1

            finished = utcnow()
            self.store.record_run(job_id, started, finished, exit_code, bytes_out, bytes_err)

            if exit_code == 0:
                self.store.complete(job_id)
            else:
                row = self.store.increment_attempts(job_id)
                base = int(self.config.get("backoff_base") or 2)
                self.store.reschedule_or_dead(job_id, f"exit:{exit_code}", row["attempts"], row["max_retries"], base)

class WorkerManager:
    def __init__(self, store, config):
        self.store = store
        self.config = config
        self.procs = []
        self.stop_event = mp.Event()

    def start(self, count=1):
        for i in range(count):
            name = f"worker-{i}-{os.getpid()}"
            p = WorkerProcess(name, self.store, self.config, self.stop_event)
            p.start()
            self.procs.append(p)

    def stop(self):
        self.stop_event.set()
        for p in self.procs:
            p.join(timeout=10)

    def is_running(self):
        return any(p.is_alive() for p in self.procs)
