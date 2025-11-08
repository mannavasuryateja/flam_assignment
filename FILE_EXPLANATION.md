# QueueCTL - File Structure Explanation

This document explains what each file in the QueueCTL project contains and its purpose.

## 📁 Root Directory Files

### `queuectl.py`
**Purpose**: Direct entry point script for running QueueCTL without installation
- **What it does**: 
  - Adds the project root to Python path
  - Imports and calls the main CLI function
  - Allows running: `python queuectl.py <command>`
- **Usage**: `python queuectl.py enqueue '{"id":"job1","command":"echo hello"}'`

### `setup.py`
**Purpose**: Python package installation configuration
- **What it does**:
  - Defines package metadata (name, version, description)
  - Lists dependencies (click, fastapi, uvicorn, tabulate)
  - Creates console script entry point: `queuectl` command
- **Usage**: `pip install -e .` (installs package in development mode)

### `requirements.txt`
**Purpose**: Lists all Python package dependencies
- **Contains**:
  - `click==8.1.7` - CLI framework for building commands
  - `fastapi==0.115.2` - Web framework for dashboard
  - `uvicorn==0.30.6` - ASGI server for running FastAPI
  - `tabulate==0.9.0` - Pretty table formatting for output
- **Usage**: `pip install -r requirements.txt`

### `README.md`
**Purpose**: Comprehensive project documentation
- **Contains**:
  - Setup instructions
  - Usage examples
  - Architecture overview
  - Testing instructions
  - Configuration options
  - Troubleshooting guide

### `demo.py`
**Purpose**: Demonstration script showing QueueCTL in action
- **What it does**:
  - Enqueues multiple jobs (successful and failing)
  - Starts workers
  - Shows status, completed jobs, DLQ
  - Demonstrates all major features
- **Usage**: `python demo.py`

### `validate.py`
**Purpose**: Automated validation script for testing core functionality
- **What it does**:
  - Tests all major commands
  - Verifies job enqueueing, processing, retries, DLQ
  - Validates configuration
  - Ensures system works correctly
- **Usage**: `python validate.py`

### `test_commands.ps1`
**Purpose**: PowerShell script for Windows testing
- **What it does**:
  - Runs a series of test commands
  - Tests enqueue, status, workers, DLQ
  - Windows-specific test automation

---

## 📁 `core/` Directory - Main Application Code

### `core/__init__.py`
**Purpose**: Makes `core` a Python package
- **Contains**: Empty file (or minimal package initialization)
- **Purpose**: Allows importing from core module

### `core/main.py`
**Purpose**: CLI command definitions and entry point
- **What it contains**:
  - **CLI Commands**:
    - `enqueue` - Add jobs to queue
    - `worker start/stop` - Manage worker processes
    - `status` - Show job statistics
    - `list` - List jobs by state
    - `dlq list/retry` - Dead Letter Queue operations
    - `config set/get/show` - Configuration management
    - `logs` - Show job log paths
    - `web` - Start web dashboard
  - **Initialization**: Creates JobStore, ConfigStore, WorkerManager instances
  - **Uses**: Click framework for CLI, tabulate for output formatting

### `core/db.py`
**Purpose**: Database operations and job storage
- **What it contains**:
  - **JobStore class**: Main database interface
    - `enqueue()` - Add new jobs
    - `get()` - Get job by ID
    - `list()` - List jobs (optionally filtered by state)
    - `claim_next()` - Atomically claim next job for worker (prevents duplicates)
    - `complete()` - Mark job as completed
    - `reschedule_or_dead()` - Handle retries with exponential backoff or move to DLQ
    - `move_failed_to_pending()` - Move failed jobs ready for retry to pending
    - `increment_attempts()` - Increment retry counter
    - `retry_from_dlq()` - Retry a dead job
    - `stats()` - Get job statistics
    - `record_run()` - Log job execution details
    - `log_paths_for()` - Get log file paths
  - **Database Schema**: SQLite tables for jobs, job_runs, config
  - **Features**: Atomic job claiming, state management, persistence

### `core/worker.py`
**Purpose**: Worker process implementation
- **What it contains**:
  - **WorkerProcess class**: Individual worker process
    - `run()` - Main worker loop
      - Polls for available jobs
      - Executes commands with timeout
      - Captures stdout/stderr to log files
      - Handles success/failure
      - Implements retry logic with exponential backoff
  - **WorkerManager class**: Manages multiple worker processes
    - `start(count)` - Start N worker processes
    - `stop()` - Gracefully stop all workers
    - `is_running()` - Check if workers are active
  - **Features**: Multiprocessing, graceful shutdown, command execution

### `core/config.py`
**Purpose**: Configuration management
- **What it contains**:
  - **ConfigStore class**: Configuration storage
    - `set(key, value)` - Set configuration value
    - `get(key)` - Get configuration value
    - `all()` - Get all configuration
  - **Default values**:
    - `max_retries`: 3
    - `backoff_base`: 2
    - `poll_interval_ms`: 500
    - `default_timeout_secs`: 60
  - **Storage**: SQLite database (same as jobs)

### `core/web.py`
**Purpose**: Web dashboard for monitoring
- **What it contains**:
  - **dashboard_app()**: FastAPI application factory
    - `/` - Main dashboard page showing:
      - Job statistics (pending, processing, completed, failed, dead)
      - Recent jobs list
      - Recent job runs with execution details
  - **Features**: HTML tables, real-time stats, minimal web interface

---

## 📁 `tests/` Directory - Testing

### `tests/test_scenarios.py`
**Purpose**: Test scenarios for manual validation
- **What it does**:
  - Enqueues successful and failing jobs
  - Starts workers
  - Tests retry mechanism
  - Verifies DLQ functionality
- **Usage**: `python tests/test_scenarios.py`

---

## 📁 `data/` Directory - Runtime Data

### `data/queuectl.db`
**Purpose**: SQLite database file
- **Contains**:
  - `jobs` table - All job records
  - `job_runs` table - Execution history
  - `config` table - Configuration values
- **Note**: Created automatically on first run

### `data/logs/` Directory
**Purpose**: Job execution logs
- **Contains**:
  - `{job_id}.stdout.log` - Standard output for each job
  - `{job_id}.stderr.log` - Standard error for each job
- **Example**: `demo_success1.stdout.log` contains "Hello from QueueCTL!"

---

## 📁 `venv/` Directory - Virtual Environment

**Purpose**: Python virtual environment
- **Contains**: 
  - Isolated Python interpreter
  - All installed dependencies
  - Package executables
- **Note**: Should not be committed to version control
- **Usage**: Activate with `.\venv\Scripts\Activate.ps1` (Windows) or `source venv/bin/activate` (Linux/Mac)

---

## 🔄 How Files Work Together

```
User Command
    ↓
queuectl.py (entry point)
    ↓
core/main.py (CLI commands)
    ↓
    ├─→ core/db.py (job storage)
    ├─→ core/worker.py (job processing)
    ├─→ core/config.py (configuration)
    └─→ core/web.py (dashboard)
    ↓
data/queuectl.db (persistence)
data/logs/ (job outputs)
```

### Example Flow:

1. **User runs**: `python queuectl.py enqueue '{"id":"job1","command":"echo hello"}'`
   - `queuectl.py` → `core/main.py` → `enqueue()` command
   - Calls `store.enqueue()` from `core/db.py`
   - Saves to `data/queuectl.db`

2. **User runs**: `python queuectl.py worker start --count 2`
   - `core/main.py` → `worker_start()` command
   - Calls `manager.start(2)` from `core/worker.py`
   - Creates 2 `WorkerProcess` instances
   - Each worker polls `store.claim_next()` from `core/db.py`
   - Executes jobs and updates database

3. **User runs**: `python queuectl.py status`
   - `core/main.py` → `status()` command
   - Calls `store.stats()` from `core/db.py`
   - Displays formatted table using `tabulate`

---

## 📝 Key Design Patterns

1. **Separation of Concerns**:
   - `db.py` - Data layer
   - `worker.py` - Processing layer
   - `main.py` - Presentation layer (CLI)
   - `config.py` - Configuration layer

2. **Atomic Operations**: Job claiming uses SQL UPDATE to prevent race conditions

3. **Persistence**: All data stored in SQLite, survives restarts

4. **Multiprocessing**: Workers run as separate processes for true parallelism

5. **Graceful Shutdown**: Workers finish current jobs before stopping

---

This structure ensures the codebase is maintainable, testable, and follows best practices for a production-grade job queue system.

