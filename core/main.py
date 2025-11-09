# core/main.py
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from tabulate import tabulate
import click


CURRENT_DIR = Path(__file__).resolve().parent
ROOT = CURRENT_DIR.parent
DATA_DIR = ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = str(DATA_DIR / "queuectl.db")


from .db import JobStore
from .worker import WorkerManager
from .config import ConfigStore
from .web import dashboard_app


store = JobStore(DB_PATH, LOGS_DIR)
config = ConfigStore(DB_PATH)
manager = WorkerManager(store, config)

@click.group(help="queuectl - CLI background job queue")
def cli():
    pass


@cli.command(help="Enqueue a job (JSON). Example: enqueue '{\"id\":\"job1\",\"command\":\"echo Hello\"}'")
@click.argument("job_json")
@click.option("--priority", type=int, help="Lower is higher priority")
@click.option("--run-at", type=str, help="ISO8601 schedule time (UTC), e.g. 2025-11-04T10:30:00Z")
@click.option("--timeout", type=int, help="Per-job timeout seconds")
@click.option("--max-retries", type=int, help="Overrides default max_retries")
def enqueue(job_json, priority, run_at, timeout, max_retries):
    try:
        job = json.loads(job_json)
    except Exception as e:
        click.echo(f"Invalid JSON: {e}", err=True); sys.exit(2)
    if priority is not None:
        job["priority"] = priority
    if run_at:
        job["run_at"] = run_at
    if timeout is not None:
        job["timeout_secs"] = timeout
    if max_retries is not None:
        job["max_retries"] = max_retries
    created = store.enqueue(job)
    click.echo(tabulate([created], headers="keys"))


@cli.group(help="Worker management")
def worker():
    pass

@worker.command("start", help="Start N workers (foreground). Ctrl+C to stop.")
@click.option("--count", default=1, show_default=True, type=int)
def worker_start(count):
    click.echo(f"Starting {count} worker(s)...")

    def handle(_sig, _frm):
        click.echo("Stopping workers...")
        manager.stop()

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)

    manager.start(count)
    try:
        while manager.is_running():
            time.sleep(0.5)
    except KeyboardInterrupt:
        handle(None, None)

@worker.command("stop", help="Gracefully stop workers (if running in this process)")
def worker_stop():
    manager.stop()
    click.echo("Stop requested")


@cli.command(help="Show summary of all job states & metrics")
def status():
    s = store.stats()
    click.echo(tabulate([s], headers="keys"))

@cli.command("list", help="List jobs (optionally filter by --state)")
@click.option("--state", type=click.Choice(["pending","processing","completed","failed","dead"]), default=None)
def list_cmd(state):
    jobs = store.list(state)
    if jobs:
        click.echo(tabulate(jobs, headers="keys"))
    else:
        click.echo("No jobs found.")


@cli.group(help="Dead Letter Queue operations")
def dlq():
    pass

@dlq.command("list", help="List DLQ jobs")
def dlq_list():
    jobs = store.list("dead")
    click.echo(tabulate(jobs, headers="keys") if jobs else "DLQ empty.")

@dlq.command("retry", help="Retry a DLQ job (moves back to pending, resets attempts)")
@click.argument("job_id")
def dlq_retry(job_id):
    store.retry_from_dlq(job_id)
    click.echo(f"Retry requested for {job_id}")


@cli.group(name="config", help="Configuration management")
def config_cmd():
    pass

@config_cmd.command("set", help="Set a config key")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    config.set(key, value)
    click.echo(f"Set {key} = {value}")

@config_cmd.command("get", help="Get a config key")
@click.argument("key")
def config_get(key):
    click.echo(config.get(key))

@config_cmd.command("show", help="Show all config")
def config_show():
    click.echo(tabulate([config.all()], headers="keys"))


@cli.command(help="Show paths to logs for a job")
@click.argument("job_id")
def logs(job_id):
    out, err = store.log_paths_for(job_id)
    click.echo(f"stdout: {out}\nstderr: {err}")


@cli.command(help="Start the minimal web dashboard")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True, type=int)
def web(host, port):
    import uvicorn
    app = dashboard_app(DB_PATH, LOGS_DIR)
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    
    sys.path.append(str(ROOT))
    cli()
