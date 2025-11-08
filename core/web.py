# core/web.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from .db import JobStore
from .config import ConfigStore
from pathlib import Path

def dashboard_app(db_path: str, logs_dir: Path):
    store = JobStore(db_path, logs_dir)
    cfg = ConfigStore(db_path)
    app = FastAPI(title="queuectl dashboard")

    def html_table(headers, rows):
        th = "".join(f"<th>{h}</th>" for h in headers)
        trs = []
        for r in rows:
            tds = "".join(f"<td>{r.get(h,'')}</td>" for h in headers)
            trs.append(f"<tr>{tds}</tr>")
        return f"<table border='1' cellpadding='6' cellspacing='0'><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"

    @app.get("/", response_class=HTMLResponse)
    def home():
        stats = store.stats()
        jobs = store.list()
        runs = store.recent_runs()
        body = [
            "<h1>queuectl dashboard</h1>",
            "<h2>Stats</h2>",
            html_table(["pending","processing","completed","failed","dead","total_jobs","total_runs"], [stats]),
            "<h2>Recent jobs</h2>",
            html_table(["id","state","priority","attempts","max_retries","next_run_at","last_error"], jobs[-20:][::-1]),
            "<h2>Recent runs</h2>",
            html_table(["id","job_id","started_at","finished_at","exit_code","duration_ms","bytes_stdout","bytes_stderr"], runs),
        ]
        return "\n".join(body)

    return app
