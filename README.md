# QueueCTL - CLI Background Job Queue System

A production-grade, CLI-based background job queue system with worker processes, automatic retries with exponential backoff, and Dead Letter Queue (DLQ) support.

## 🎯 Features

- ✅ **Job Management**: Enqueue, list, and monitor background jobs
- ✅ **Worker Processes**: Run multiple workers in parallel
- ✅ **Automatic Retries**: Exponential backoff retry mechanism
- ✅ **Dead Letter Queue**: Permanent storage for failed jobs
- ✅ **Persistent Storage**: SQLite database for job persistence
- ✅ **Job States**: pending → processing → completed/failed → dead
- ✅ **Configuration**: Configurable retry count and backoff base
- ✅ **Job Logging**: Captures stdout/stderr for each job execution
- ✅ **Web Dashboard**: Optional minimal web interface for monitoring

## 📋 Requirements

- Python 3.7+
- Windows, Linux, or macOS

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd queuectl
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install as CLI Tool (Optional)

```bash
pip install -e .
```

After installation, you can use `queuectl` directly from anywhere. Otherwise, use `python queuectl.py` or `python core/main.py`.

## 💻 Usage Examples

### Enqueue a Job

```bash
# Basic job
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'

# Job with custom retry count
queuectl enqueue '{"id":"job2","command":"sleep 5","max_retries":5}'

# Job with priority and timeout
queuectl enqueue '{"id":"job3","command":"python script.py"}' --priority 10 --timeout 30
```

### Start Workers

```bash
# Start 1 worker (default)
queuectl worker start

# Start multiple workers
queuectl worker start --count 3

# Stop workers (Ctrl+C or in another terminal)
queuectl worker stop
```

### Check Status

```bash
# Overall status summary
queuectl status

# List all jobs
queuectl list

# List jobs by state
queuectl list --state pending
queuectl list --state failed
queuectl list --state completed
queuectl list --state dead
```

### Dead Letter Queue (DLQ)

```bash
# List all dead jobs
queuectl dlq list

# Retry a dead job (moves back to pending, resets attempts)
queuectl dlq retry job1
```

### Configuration

```bash
# Set configuration values
queuectl config set max_retries 5
queuectl config set backoff_base 3
queuectl config set poll_interval_ms 1000
queuectl config set default_timeout_secs 120

# Get a configuration value
queuectl config get max_retries

# Show all configuration
queuectl config show
```

### View Job Logs

```bash
# Get log file paths for a job
queuectl logs job1
```

### Web Dashboard

```bash
# Start web dashboard (default: http://127.0.0.1:8000)
queuectl web

# Custom host and port
queuectl web --host 0.0.0.0 --port 8080
```

## 📦 Job Specification

Each job must contain at least the following fields:

```json
{
  "id": "unique-job-id",
  "command": "echo 'Hello World'",
  "state": "pending",
  "attempts": 0,
  "max_retries": 3,
  "created_at": "2025-11-04T10:30:00Z",
  "updated_at": "2025-11-04T10:30:00Z"
}
```

### Optional Fields

- `priority`: Lower number = higher priority (default: 100)
- `timeout_secs`: Per-job timeout in seconds
- `run_at`: ISO8601 scheduled time (UTC) for delayed execution

## 🔄 Job Lifecycle

| State | Description |
|-------|-------------|
| **pending** | Waiting to be picked up by a worker |
| **processing** | Currently being executed by a worker |
| **completed** | Successfully executed |
| **failed** | Failed, but retryable (will retry after backoff delay) |
| **dead** | Permanently failed (moved to DLQ after max retries) |

### State Transitions

```
pending → processing → completed (success)
pending → processing → failed → pending → processing → ... (retries)
pending → processing → failed → dead (max retries exceeded)
```

## ⚙️ System Architecture

### Components

1. **JobStore** (`core/db.py`): SQLite-based persistent storage for jobs
2. **WorkerManager** (`core/worker.py`): Manages worker processes
3. **ConfigStore** (`core/config.py`): Configuration management
4. **CLI** (`core/main.py`): Command-line interface using Click

### Data Persistence

- **Database**: SQLite (`data/queuectl.db`)
- **Logs**: Job stdout/stderr stored in `data/logs/`
- **Schema**: Jobs, job_runs, and config tables

### Worker Process

Each worker:
1. Polls for available jobs (configurable interval)
2. Atomically claims the next eligible job (prevents duplicate processing)
3. Executes the command with timeout support
4. Captures stdout/stderr to log files
5. Records execution metrics
6. Handles retries with exponential backoff
7. Moves to DLQ after max retries

### Retry Mechanism

**Exponential Backoff Formula**: `delay = base ^ attempts` seconds

- **Attempt 1**: `2^0 = 1` second
- **Attempt 2**: `2^1 = 2` seconds
- **Attempt 3**: `2^2 = 4` seconds
- **Attempt 4**: `2^3 = 8` seconds

Configurable via `backoff_base` (default: 2).

### Concurrency & Locking

- Workers use atomic SQL UPDATE to claim jobs (prevents race conditions)
- Each job can only be claimed by one worker at a time
- Worker name is stored in the job record during processing

## 🧪 Testing Instructions

### Manual Testing

1. **Basic Job Completion**:
   ```bash
   queuectl enqueue '{"id":"test1","command":"echo success"}'
   queuectl worker start --count 1
   # Wait a few seconds, then check status
   queuectl status
   queuectl list --state completed
   ```

2. **Failed Job with Retries**:
   ```bash
   queuectl enqueue '{"id":"test2","command":"cmd /c exit 1","max_retries":3}'
   queuectl worker start --count 1
   # Wait for retries (observe exponential backoff)
   queuectl list --state failed
   queuectl status
   ```

3. **Multiple Workers**:
   ```bash
   # Enqueue multiple jobs
   queuectl enqueue '{"id":"job1","command":"sleep 2"}'
   queuectl enqueue '{"id":"job2","command":"sleep 2"}'
   queuectl enqueue '{"id":"job3","command":"sleep 2"}'
   
   # Start 3 workers
   queuectl worker start --count 3
   # Jobs should process in parallel
   ```

4. **DLQ Testing**:
   ```bash
   # Enqueue a job that will fail
   queuectl enqueue '{"id":"fail_job","command":"invalid_command_xyz","max_retries":2}'
   queuectl worker start --count 1
   # Wait for max retries to be exhausted
   queuectl dlq list
   queuectl dlq retry fail_job
   ```

5. **Persistence Test**:
   ```bash
   # Enqueue jobs
   queuectl enqueue '{"id":"persist1","command":"echo test"}'
   # Stop workers, restart application
   queuectl status  # Jobs should still be there
   ```

### Automated Test Scripts

Run the provided test scripts:

```bash
# Comprehensive validation script (recommended)
.\venv\Scripts\Activate.ps1
python validate.py

# Windows PowerShell test script
.\venv\Scripts\Activate.ps1
.\test_commands.ps1

# Or use the Python test script
python tests/test_scenarios.py
```


## 📁 Project Structure

```
queuectl/
├── core/
│   ├── __init__.py
│   ├── main.py          # CLI entry point
│   ├── db.py            # JobStore & database operations
│   ├── worker.py        # Worker processes
│   ├── config.py        # Configuration management
│   └── web.py           # Web dashboard
├── data/
│   ├── queuectl.db      # SQLite database
│   └── logs/            # Job output logs
├── tests/
│   └── test_scenarios.py
├── queuectl.py          # Direct entry point
├── setup.py             # Package setup
├── requirements.txt     # Dependencies
└── README.md            # This file
```


## ✅ Checklist

- [x] All required commands functional
- [x] Jobs persist after restart
- [x] Retry and backoff implemented correctly
- [x] DLQ operational
- [x] CLI user-friendly and documented
- [x] Code is modular and maintainable
- [x] Includes test scripts verifying main flows
- [x] Comprehensive README

