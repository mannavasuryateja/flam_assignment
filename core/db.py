# core/db.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,                 -- pending | processing | completed | failed | dead
    attempts INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    priority INTEGER NOT NULL DEFAULT 100,  -- lower = higher priority
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    run_at TEXT,                         -- initial schedule (nullable)
    next_run_at TEXT,                    -- next scheduled execution (nullable)
    timeout_secs INTEGER,                -- optional per-job timeout
    worker TEXT,                         -- who is running it
    last_error TEXT                      -- last error or exit code
);

CREATE INDEX IF NOT EXISTS idx_jobs_state_sched
ON jobs(state, next_run_at, priority, created_at);

CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    exit_code INTEGER,
    duration_ms INTEGER NOT NULL,
    bytes_stdout INTEGER NOT NULL,
    bytes_stderr INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

def utcnow() -> str:
    return datetime.utcnow().isoformat() + "Z"

class JobStore:
    def __init__(self, db_path: str, logs_dir: Path):
        self.db_path = db_path
        self.logs_dir = logs_dir
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript(SCHEMA)

    # ---------- CRUD ----------
    def enqueue(self, job):
        now = utcnow()
        job = {
            "id": job["id"],
            "command": job["command"],
            "state": job.get("state", "pending"),
            "attempts": int(job.get("attempts", 0)),
            "max_retries": int(job.get("max_retries", 3)),
            "priority": int(job.get("priority", 100)),
            "created_at": job.get("created_at", now),
            "updated_at": now,
            "run_at": job.get("run_at"),
            "next_run_at": job.get("next_run_at") or job.get("run_at") or now,
            "timeout_secs": int(job.get("timeout_secs", 0)) or None,
            "worker": None,
            "last_error": None,
        }
        with self._conn() as c:
            c.execute("""
                INSERT INTO jobs
                (id, command, state, attempts, max_retries, priority, created_at, updated_at, run_at, next_run_at, timeout_secs, worker, last_error)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                job["id"], job["command"], job["state"], job["attempts"], job["max_retries"],
                job["priority"], job["created_at"], job["updated_at"], job["run_at"],
                job["next_run_at"], job["timeout_secs"], job["worker"], job["last_error"]
            ))
        return job

    def get(self, job_id):
        with self._conn() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None

    def list(self, state=None):
        with self._conn() as c:
            if state:
                rows = c.execute("SELECT * FROM jobs WHERE state=? ORDER BY priority ASC, created_at ASC", (state,))
            else:
                rows = c.execute("SELECT * FROM jobs ORDER BY created_at ASC")
            return [dict(r) for r in rows.fetchall()]

    def stats(self):
        with self._conn() as c:
            out = {"pending": 0, "processing": 0, "completed": 0, "failed": 0, "dead": 0}
            for r in c.execute("SELECT state, COUNT(*) c FROM jobs GROUP BY state"):
                out[r["state"]] = r["c"]
            # totals / metrics
            total = sum(out.values())
            runs = c.execute("SELECT COUNT(*) c FROM job_runs").fetchone()["c"]
            out["total_jobs"] = total
            out["total_runs"] = runs
            return out

    def retry_from_dlq(self, job_id):
        now = utcnow()
        with self._conn() as c:
            c.execute("""
                UPDATE jobs SET state='pending', attempts=0, next_run_at=?, updated_at=?, last_error=NULL
                WHERE id=? AND state='dead'
            """, (now, now, job_id))

    # ---------- Worker coordination ----------
    def claim_next(self, worker_name):
        """Atomically claim the next eligible job."""
        now = utcnow()
        # First, move any failed jobs that are ready to retry back to pending
        self.move_failed_to_pending()
        with self._conn() as c:
            cur = c.cursor()

            cur.execute("""
                UPDATE jobs
                SET state='processing', worker=?, updated_at=?
                WHERE id = (
                SELECT id FROM jobs
                WHERE state='pending'
                    AND (next_run_at IS NULL OR next_run_at <= ?)
                ORDER BY priority ASC, next_run_at ASC, created_at ASC
                LIMIT 1
                )
            """, (worker_name, now, now))

            # ✅ If no job updated, nothing to process
            if cur.rowcount == 0:
                return None

            row = cur.execute("""
                SELECT * FROM jobs
                WHERE worker=? AND state='processing'
                ORDER BY updated_at DESC LIMIT 1
            """, (worker_name,)).fetchone()

            return dict(row) if row else None


    def increment_attempts(self, job_id):
        with self._conn() as c:
            c.execute("UPDATE jobs SET attempts = attempts + 1 WHERE id=?", (job_id,))
            row = c.execute("SELECT attempts, max_retries FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row)

    def complete(self, job_id):
        now = utcnow()
        with self._conn() as c:
            c.execute("UPDATE jobs SET state='completed', updated_at=?, worker=NULL WHERE id=?", (now, job_id))

    def reschedule_or_dead(self, job_id, last_error, attempts, max_retries, backoff_base):
        now = utcnow()
        with self._conn() as c:
            if attempts >= max_retries:
                c.execute("""
                    UPDATE jobs SET state='dead', updated_at=?, last_error=?, worker=NULL
                    WHERE id=?
                """, (now, last_error, job_id))
            else:
                # Set to 'failed' state first, then schedule retry
                delay = backoff_base ** attempts
                next_run = (datetime.utcnow() + timedelta(seconds=delay)).isoformat() + "Z"
                c.execute("""
                    UPDATE jobs
                    SET state='failed', updated_at=?, last_error=?, next_run_at=?, worker=NULL
                    WHERE id=?
                """, (now, last_error, next_run, job_id))
    
    def move_failed_to_pending(self):
        """Move failed jobs that are ready to retry back to pending state."""
        now = utcnow()
        with self._conn() as c:
            c.execute("""
                UPDATE jobs
                SET state='pending', updated_at=?
                WHERE state='failed' AND (next_run_at IS NULL OR next_run_at <= ?)
            """, (now, now))

    # ---------- Logging & metrics ----------
    def log_paths_for(self, job_id):
        stdout = self.logs_dir / f"{job_id}.stdout.log"
        stderr = self.logs_dir / f"{job_id}.stderr.log"
        return stdout, stderr

    def record_run(self, job_id, started_at, finished_at, exit_code, bytes_out, bytes_err):
        dur_ms = int((datetime.fromisoformat(finished_at[:-1]) - datetime.fromisoformat(started_at[:-1])).total_seconds() * 1000)
        with self._conn() as c:
            c.execute("""
                INSERT INTO job_runs(job_id, started_at, finished_at, exit_code, duration_ms, bytes_stdout, bytes_stderr)
                VALUES (?,?,?,?,?,?,?)
            """, (job_id, started_at, finished_at, exit_code, dur_ms, bytes_out, bytes_err))

    def recent_runs(self, limit=20):
        with self._conn() as c:
            rows = c.execute("""
                SELECT * FROM job_runs ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
