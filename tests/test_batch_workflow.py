"""Exercise the Robot batch against a local, deterministic portal."""

import csv
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PAGE = """<!doctype html>
<nav><a href="/login">Login</a></nav>
<button data-testid="sidebar-toggle">Toggle</button>
<aside data-testid="sidebar"><a href="/banking">Banking</a></aside>
<input data-testid="username-input">
<input data-testid="password-input" type="password">
<button data-testid="login-button">Login</button>
<input data-testid="start-date" type="date">
<input data-testid="end-date" type="date">
<button data-testid="download-statement">Download</button>
<script>
document.querySelectorAll('a').forEach(a => a.onclick = e => e.preventDefault());
document.querySelector('[data-testid="login-button"]').onclick = () => {
    const close = document.createElement('button');
    close.dataset.testid = 'close-success-dialog';
    close.textContent = 'Close';
    close.onclick = () => close.remove();
    document.body.appendChild(close);
};
document.querySelector('[data-testid="download-statement"]').onclick = () => {
    const start = document.querySelector('[data-testid="start-date"]').value;
    const end = document.querySelector('[data-testid="end-date"]').value;
    const content = start === '2025-02-01'
        ? 'invalid statement'
        : `BANK STATEMENT\\nDate Range: ${start} to ${end}\\n`;
    const url = URL.createObjectURL(new Blob([content], {type: 'text/plain'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'statement.txt';
    link.click();
};
</script>
"""


@pytest.fixture
def portal_url():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def run_batch(tmp_path: Path, portal_url: str, rows: str) -> tuple[subprocess.CompletedProcess, list[dict]]:
    (tmp_path / "input.csv").write_text(
        "transaction_id,start_date,end_date\n" + rows, encoding="utf-8"
    )
    config = tmp_path / "settings.csv"
    config.write_text(
        f"setting,value\nportal_url,{portal_url}\n"
        "input_csv,input.csv\noutput_dir,output\n"
        "max_retries,2\nretry_delay_seconds,5\ndownload_timeout_seconds,10\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PORTAL_USERNAME"] = "admin"
    env["PORTAL_PASSWORD"] = "admin123"
    result = subprocess.run(
        [
            sys.executable, "-m", "robot", "--outputdir", str(tmp_path / "robot"),
            "--variable", f"CONFIG_FILE:{config}",
            str(ROOT / "robot" / "tasks" / "process_transactions.robot"),
        ],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=90,
    )
    reports = list((tmp_path / "output").glob("run-*/results.csv"))
    assert len(reports) == 1, result.stdout + result.stderr
    with reports[0].open(encoding="utf-8", newline="") as file:
        return result, list(csv.DictReader(file))


def test_batch_continues_after_business_failure_and_downloads_each_valid_row(
    tmp_path: Path, portal_url: str
) -> None:
    result, rows = run_batch(
        tmp_path, portal_url,
        "first,2025-01-01,2025-01-31\n"
        "invalid,2025-02-30,2025-03-01\n"
        "last,2025-03-01,2025-03-31\n",
    )
    assert result.returncode != 0
    assert [row["status"] for row in rows] == ["success", "business_failure", "success"]
    paths = [Path(row["download_path"]) for row in rows if row["status"] == "success"]
    assert len(set(paths)) == 2
    for path, row in zip(paths, (rows[0], rows[2])):
        assert f"Date Range: {row['start_date']} to {row['end_date']}" in path.read_text()
    assert not rows[1]["download_path"]


def test_batch_records_system_failure_and_stops_before_next_row(
    tmp_path: Path, portal_url: str
) -> None:
    result, rows = run_batch(
        tmp_path, portal_url,
        "first,2025-01-01,2025-01-31\n"
        "broken,2025-02-01,2025-02-28\n"
        "not-processed,2025-03-01,2025-03-31\n",
    )
    assert result.returncode != 0
    assert [row["status"] for row in rows] == ["success", "system_failure"]
    assert [row["transaction_id"] for row in rows] == ["first", "broken"]
    assert Path(rows[0]["download_path"]).is_file()
    assert not rows[1]["download_path"]
