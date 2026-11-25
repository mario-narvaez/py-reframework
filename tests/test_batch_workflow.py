"""Exercise the Robot batch against a local, deterministic portal."""

import csv
import os
import re
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PAGE = """<!doctype html>
<nav><a href="/login">Login</a></nav>
<button data-testid="sidebar-toggle">Toggle</button>
<aside data-testid="sidebar"><a href="/banking">Banking</a></aside>
<section id="login" hidden>
  <input data-testid="username-input">
  <input data-testid="password-input" type="password">
  <button data-testid="login-button">Login</button>
</section>
<section id="banking" hidden>
  <input data-testid="start-date" type="date">
  <input data-testid="end-date" type="date">
  <button data-testid="apply-date-range" disabled>Apply Range</button>
  <div data-testid="date-range-display" hidden></div>
  <button data-testid="download-statement" disabled>Download</button>
</section>
<script>
let loggedIn = false;
const sidebar = document.querySelector('[data-testid="sidebar"]');
const login = document.getElementById('login');
const banking = document.getElementById('banking');
const startField = document.querySelector('[data-testid="start-date"]');
const endField = document.querySelector('[data-testid="end-date"]');
const apply = document.querySelector('[data-testid="apply-date-range"]');
const display = document.querySelector('[data-testid="date-range-display"]');
const download = document.querySelector('[data-testid="download-statement"]');
let needsClear = false;
let clearedStart = false;
let clearedEnd = false;
function updateRange(event) {
    if (needsClear && event.target.value === '') {
        if (event.target === startField) clearedStart = true;
        if (event.target === endField) clearedEnd = true;
        if (clearedStart && clearedEnd) needsClear = false;
    }
    const complete = Boolean(startField.value && endField.value);
    apply.disabled = !complete;
    download.disabled = true;
    display.hidden = !complete;
    display.textContent = `Selected: ${startField.value} to ${endField.value} (30 days)`;
}
startField.addEventListener('input', updateRange);
endField.addEventListener('input', updateRange);
apply.onclick = () => {
    if (!needsClear) download.disabled = false;
};
document.querySelector('[data-testid="sidebar-toggle"]').onclick = () => {
    sidebar.hidden = !sidebar.hidden;
};
document.querySelector('nav a').onclick = e => {
    e.preventDefault();
    login.hidden = false;
    banking.hidden = true;
};
sidebar.querySelector('a').onclick = e => {
    e.preventDefault();
    if (loggedIn) {
        login.hidden = true;
        banking.hidden = false;
    }
};
document.querySelector('[data-testid="login-button"]').onclick = () => {
    const username = document.querySelector('[data-testid="username-input"]').value;
    const password = document.querySelector('[data-testid="password-input"]').value;
    if (username !== 'admin' || password !== 'admin123') {
        const error = document.createElement('div');
        error.dataset.testid = 'username-error';
        error.textContent = 'Invalid username';
        document.body.appendChild(error);
        return;
    }
    const close = document.createElement('button');
    close.dataset.testid = 'close-success-dialog';
    close.textContent = 'Close';
    close.onclick = () => {
        loggedIn = true;
        close.remove();
    };
    document.body.appendChild(close);
};
document.querySelector('[data-testid="download-statement"]').onclick = () => {
    const start = document.querySelector('[data-testid="start-date"]').value;
    const end = document.querySelector('[data-testid="end-date"]').value;
    needsClear = true;
    clearedStart = false;
    clearedEnd = false;
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
def portal():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/":
                self.send_error(404)
                return
            self.server.requests += 1
            self.server.request_times.append(time.monotonic())
            self.server.cookies.append(self.headers.get("Cookie", ""))
            status = self.server.statuses.pop(0) if self.server.statuses else 200
            body = self.server.page.encode("utf-8")
            self.send_response(status)
            self.send_header("Set-Cookie", "retry-check=seen; Path=/")
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.statuses = []
    server.requests = 0
    server.request_times = []
    server.cookies = []
    server.page = PAGE
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def prepare_batch(
    tmp_path: Path, portal, rows: str, delay: int = 0, username: str = "admin",
    retries: int = 1, password: str = "admin123", credentials_in_config: bool = False,
):
    input_dir = tmp_path / "process" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "transactions.csv").write_text(
        "transaction_id,start_date,end_date\n" + rows, encoding="utf-8"
    )
    config = tmp_path / "settings.csv"
    config_credentials = (username, password) if credentials_in_config else ("", "")
    config.write_text(
        f"setting,value\nportal_url,http://127.0.0.1:{portal.server_port}/\n"
        f"portal_username,{config_credentials[0]}\nportal_password,{config_credentials[1]}\n"
        "input_csv,process/input/transactions.csv\noutput_dir,process/output/runs\n"
        f"max_retries,{retries}\nretry_delay_seconds,{delay}\ndownload_timeout_seconds,10\n"
        "demo_delay_preset,short\n"
        "demo_delay_short_seconds,1\n"
        "demo_delay_medium_seconds,3\n"
        "demo_delay_long_seconds,5\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "code" / "python")
    if credentials_in_config:
        env.pop("PORTAL_USERNAME", None)
        env.pop("PORTAL_PASSWORD", None)
    else:
        env["PORTAL_USERNAME"] = username
        env["PORTAL_PASSWORD"] = password
    command = [
        sys.executable, "-m", "robot", "--outputdir", str(tmp_path / "process" / "output" / "reports" / "robot"),
        "--variable", f"CONFIG_FILE:{config}",
        "--variable", "HEADLESS:True",
        str(ROOT / "code" / "robot" / "tasks" / "process_transactions.robot"),
    ]
    return command, env


def read_results(tmp_path: Path) -> list[dict]:
    reports = list((tmp_path / "process" / "output" / "runs").glob("*/results.csv"))
    assert len(reports) == 1
    with reports[0].open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def successful_keywords(root: ET.Element, name: str) -> list[ET.Element]:
    return [
        keyword for keyword in root.iter("kw")
        if keyword.get("name") == name
        and (status := keyword.find("status")) is not None
        and status.get("status") == "PASS"
    ]


def assert_failure_screenshot(tmp_path: Path, parent_keyword: str) -> None:
    robot_reports = tmp_path / "process" / "output" / "reports" / "robot"
    root = ET.parse(robot_reports / "output.xml").getroot()
    captures = [
        capture
        for parent in successful_keywords(root, parent_keyword)
        for capture in successful_keywords(parent, "Capture Failure Evidence")
    ]
    screenshots = [
        screenshot
        for capture in captures
        for screenshot in successful_keywords(capture, "Take Screenshot")
    ]
    assert screenshots, f"No successful failure screenshot within {parent_keyword}"
    links = [
        match
        for screenshot in screenshots
        for message in screenshot.iter("msg")
        for match in re.findall(r'href="([^"]+\.png)"', message.text or "")
    ]
    assert links, "The failure screenshot was not linked in Robot's output"
    assert any(robot_reports.joinpath(*link.split("/")).is_file() for link in links)


def run_batch(
    tmp_path: Path, portal, rows: str, username: str = "admin", delay: int = 0,
    retries: int = 1, password: str = "admin123", credentials_in_config: bool = False,
) -> tuple[subprocess.CompletedProcess, list[dict]]:
    command, env = prepare_batch(
        tmp_path, portal, rows, delay, username, retries, password, credentials_in_config
    )
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=90)
    return result, read_results(tmp_path)


def test_batch_continues_after_business_failure_and_downloads_each_valid_row(
    tmp_path: Path, portal
) -> None:
    result, rows = run_batch(
        tmp_path, portal,
        "first,2025-01-01,2025-01-31\n"
        "invalid,2025-02-30,2025-03-01\n"
        "last,2025-03-01,2025-03-31\n",
    )
    assert result.returncode != 0
    assert [row["status"] for row in rows] == ["success", "business_failure", "success"]
    paths = [Path(row["download_path"]) for row in rows if row["status"] == "success"]
    assert len(set(paths)) == 2
    assert [path.name for path in paths] == ["statement-001.txt", "statement-002.txt"]
    assert paths[0].parent == paths[1].parent
    assert paths[0].parent.name == "downloads"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", paths[0].parent.parent.name)
    for path, row in zip(paths, (rows[0], rows[2])):
        assert f"Date Range: {row['start_date']} to {row['end_date']}" in path.read_text()
    assert not rows[1]["download_path"]
    assert [row["attempts"] for row in rows] == ["1", "0", "1"]


def test_single_statement_uses_dated_run_download_folder(tmp_path: Path, portal) -> None:
    command, env = prepare_batch(tmp_path, portal, "")
    command[-1:] = [
        "--variable", "START_DATE:2025-01-01",
        "--variable", "END_DATE:2025-01-31",
        str(ROOT / "code" / "robot" / "tasks" / "download_statement.robot"),
    ]
    result = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=90
    )
    assert result.returncode == 0, result.stdout + result.stderr
    downloads = list(
        (tmp_path / "process" / "output" / "runs").glob("*/downloads/statement-001.txt")
    )
    assert len(downloads) == 1
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", downloads[0].parent.parent.name)
    assert "Date Range: 2025-01-01 to 2025-01-31" in downloads[0].read_text()


@pytest.mark.parametrize("task", ["batch", "single"])
def test_tasks_log_in_with_credentials_from_the_settings_file(
    tmp_path: Path, portal, task: str
) -> None:
    command, env = prepare_batch(
        tmp_path, portal, "one,2025-01-01,2025-01-31\n", credentials_in_config=True
    )
    if task == "single":
        command[-1:] = [
            "--variable", "START_DATE:2025-01-01",
            "--variable", "END_DATE:2025-01-31",
            str(ROOT / "code" / "robot" / "tasks" / "download_statement.robot"),
        ]
    result = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=90
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PORTAL_USERNAME" not in env
    output = (
        tmp_path / "process" / "output" / "reports" / "robot" / "output.xml"
    ).read_text(encoding="utf-8")
    assert "admin123" not in output
    assert list((tmp_path / "process" / "output" / "runs").glob("*/downloads/statement-001.txt"))


def test_incomplete_settings_credentials_stop_without_opening_a_browser(
    tmp_path: Path, portal
) -> None:
    result, rows = run_batch(
        tmp_path, portal, "one,2025-01-01,2025-01-31\n", password="", credentials_in_config=True
    )
    assert result.returncode != 0
    assert rows == []
    assert portal.requests == 0
    assert "credentials are missing" in result.stdout


def test_missing_dates_reach_disabled_apply_and_batch_continues(tmp_path: Path, portal) -> None:
    result, rows = run_batch(
        tmp_path, portal,
        "first,2025-01-01,2025-01-31\n"
        "missing-end,2025-03-01,\n"
        "missing-start,,2025-04-30\n"
        "last,2025-05-01,2025-05-31\n",
    )
    assert result.returncode != 0
    assert [row["status"] for row in rows] == [
        "success", "business_failure", "business_failure", "success"
    ]
    assert [row["attempts"] for row in rows] == ["1", "1", "1", "1"]
    assert all("Apply Range was disabled" in row["error"] for row in rows[1:3])
    assert not any(row["download_path"] for row in rows[1:3])
    root = ET.parse(tmp_path / "process" / "output" / "reports" / "robot" / "output.xml").getroot()
    assert len(successful_keywords(root, "Apply Demo Date Range")) == 4
    assert len(successful_keywords(root, "Download Demo Statement")) == 2
    assert len(successful_keywords(root, "Clear Demo Dates")) == 4


@pytest.mark.parametrize(
    "change",
    [
        ("apply.disabled = !complete;", "apply.disabled = true;"),
        ("${startField.value} to ${endField.value}", "${startField.value} to 2024-01-01"),
    ],
)
def test_unexpected_apply_or_selection_failure_stops_as_system_failure(
    tmp_path: Path, portal, change: tuple[str, str]
) -> None:
    portal.page = PAGE.replace(*change)
    result, rows = run_batch(tmp_path, portal, "one,2025-01-01,2025-01-31\n")
    assert result.returncode != 0
    assert [row["status"] for row in rows] == ["system_failure"]
    assert rows[0]["attempts"] == "1"
    assert not rows[0]["download_path"]
    root = ET.parse(tmp_path / "process" / "output" / "reports" / "robot" / "output.xml").getroot()
    assert not successful_keywords(root, "Download Demo Statement")


@pytest.mark.parametrize("task", ["batch", "single"])
def test_tasks_default_to_visible_browser(tmp_path: Path, portal, task: str) -> None:
    command, env = prepare_batch(tmp_path, portal, "one,2025-01-01,2025-01-31\n")
    config = tmp_path / "settings.csv"
    settings = config.read_text(encoding="utf-8").replace("demo_delay_short_seconds,1", "demo_delay_short_seconds,0")
    config.write_text(settings, encoding="utf-8")
    headless_index = command.index("HEADLESS:True")
    del command[headless_index - 1:headless_index + 1]
    if task == "single":
        command[-1:] = [
            "--variable", "START_DATE:2025-01-01",
            "--variable", "END_DATE:2025-01-31",
            str(ROOT / "code" / "robot" / "tasks" / "download_statement.robot"),
        ]
    result = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=90
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = tmp_path / "process" / "output" / "reports" / "robot" / "output.xml"
    root = ET.parse(report).getroot()
    browsers = successful_keywords(root, "New Browser")
    assert len(browsers) == 1
    assert "headless=${False}" in [argument.text for argument in browsers[0].findall("arg")]


def test_batch_continues_after_statement_verification_failure(
    tmp_path: Path, portal
) -> None:
    result, rows = run_batch(
        tmp_path, portal,
        "first,2025-01-01,2025-01-31\n"
        "broken,2025-02-01,2025-02-28\n"
        "last,2025-03-01,2025-03-31\n",
    )
    assert result.returncode != 0
    assert [row["status"] for row in rows] == ["success", "system_failure", "success"]
    assert [row["attempts"] for row in rows] == ["1", "1", "1"]
    assert Path(rows[0]["download_path"]).is_file()
    assert not rows[1]["download_path"]
    assert_failure_screenshot(tmp_path, "Process Statement Attempt")


@pytest.mark.parametrize(("http_status", "delay"), [(502, 0), (503, 5), (504, 0)])
def test_temporary_http_failure_retries_in_a_new_browser_session(
    tmp_path: Path, portal, http_status: int, delay: int
) -> None:
    portal.statuses = [http_status, 200]
    result, rows = run_batch(tmp_path, portal, "one,2025-01-01,2025-01-31\n", delay=delay)
    assert result.returncode == 0, result.stdout + result.stderr
    assert rows[0]["status"] == "success"
    assert rows[0]["attempts"] == "1"
    assert portal.requests == 2
    assert portal.request_times[1] - portal.request_times[0] >= delay
    assert portal.cookies == ["", ""]
    assert "retrying" in result.stdout
    assert "1 succeeded, 0 business failures, 0 system failures" in result.stdout
    assert_failure_screenshot(tmp_path, "Ensure Portal Session")
    root = ET.parse(tmp_path / "process" / "output" / "reports" / "robot" / "output.xml").getroot()
    browser_events = [
        keyword.get("name")
        for keyword in root.iter("kw")
        if keyword.get("owner") == "Browser"
        and keyword.get("name") in {"New Browser", "Close Browser"}
        and (status := keyword.find("status")) is not None
        and status.get("status") == "PASS"
    ]
    assert browser_events == ["New Browser", "Close Browser", "New Browser", "Close Browser"]
    assert successful_keywords(root, "Close Browser")[0].findtext("arg") == "ALL"


def test_zero_retries_stops_initialization_without_assigning_a_row(tmp_path: Path, portal) -> None:
    portal.statuses = [503, 200]
    result, rows = run_batch(
        tmp_path, portal,
        "one,2025-01-01,2025-01-31\ntwo,2025-01-01,2025-01-31\n",
        retries=0,
    )
    assert result.returncode != 0
    assert rows == []
    assert portal.requests == 1
    assert "Initialization failed" in result.stdout


def test_exhausted_initialization_retries_leave_rows_unprocessed(tmp_path: Path, portal) -> None:
    portal.statuses = [503, 503, 200]
    result, rows = run_batch(tmp_path, portal, "one,2025-01-01,2025-01-31\n")
    assert result.returncode != 0
    assert rows == []
    assert portal.requests == 2
    assert "Initialization failed" in result.stdout


def test_three_consecutive_system_failures_stop_the_batch(tmp_path: Path, portal) -> None:
    portal.statuses = [200] + [503] * 4
    result, rows = run_batch(
        tmp_path, portal,
        "one,2025-02-01,2025-02-28\n"
        "invalid,2025-02-30,2025-03-01\n"
        "two,2025-01-01,2025-01-31\n"
        "three,2025-01-01,2025-01-31\n"
        "unprocessed,2025-01-01,2025-01-31\n",
    )
    assert result.returncode != 0
    assert [row["status"] for row in rows] == [
        "system_failure", "business_failure", "system_failure", "system_failure"
    ]
    assert [row["attempts"] for row in rows] == ["1", "0", "2", "2"]
    assert portal.requests == 5
    assert "Stopped after 3 consecutive system failures" in result.stdout
    assert "0 succeeded, 1 business failures, 3 system failures" in result.stdout


def test_success_resets_the_system_failure_streak(tmp_path: Path, portal) -> None:
    portal.statuses = [200, 200, 503, 503, 503, 503]
    result, rows = run_batch(
        tmp_path, portal,
        "first,2025-02-01,2025-02-28\n"
        "success,2025-03-01,2025-03-31\n"
        "broken,2025-02-01,2025-02-28\n"
        "fourth,2025-01-01,2025-01-31\n"
        "fifth,2025-01-01,2025-01-31\n"
        "unprocessed,2025-01-01,2025-01-31\n",
    )
    assert result.returncode != 0
    assert [row["transaction_id"] for row in rows] == ["first", "success", "broken", "fourth", "fifth"]
    assert [row["status"] for row in rows] == [
        "system_failure", "success", "system_failure", "system_failure", "system_failure"
    ]


@pytest.mark.parametrize(
    ("http_status", "username", "password", "expected_error"),
    [
        (403, "admin", "admin123", "Portal returned non-retryable HTTP status 403."),
        (200, "rejected", "admin123", "Demo portal rejected the supplied credentials."),
        (200, "admin", "wrong-password", "Demo portal rejected the supplied credentials."),
    ],
)
def test_permanent_failures_stop_without_retry(
    tmp_path: Path, portal, http_status: int, username: str, password: str, expected_error: str
) -> None:
    portal.statuses = [http_status]
    result, rows = run_batch(
        tmp_path, portal,
        "one,2025-01-01,2025-01-31\ntwo,2025-01-01,2025-01-31\n",
        username=username, password=password,
    )
    assert result.returncode != 0
    assert rows == []
    assert portal.requests == 1
    assert "retrying" not in result.stdout
    output = (
        tmp_path / "process" / "output" / "reports" / "robot" / "output.xml"
    ).read_text(encoding="utf-8")
    failures = [
        message.text for message in ET.fromstring(output).iter("msg")
        if message.get("level") == "FAIL"
    ]
    assert expected_error in failures
    assert password not in output


def test_missing_credentials_stop_without_opening_a_browser(tmp_path: Path, portal) -> None:
    result, rows = run_batch(
        tmp_path, portal, "one,2025-01-01,2025-01-31\n", username=""
    )
    assert result.returncode != 0
    assert rows == []
    assert portal.requests == 0
    assert "retrying" not in result.stdout


def test_interrupted_run_retains_only_completed_results(tmp_path: Path, portal) -> None:
    portal.statuses = [200, 503]
    command, env = prepare_batch(
        tmp_path, portal,
        "broken,2025-02-01,2025-02-28\nnext,2025-01-01,2025-01-31\n",
        delay=30,
    )
    console_path = tmp_path / "console.txt"
    with console_path.open("w", encoding="utf-8") as console:
        process = subprocess.Popen(
            command, cwd=tmp_path, env=env, stdout=console, stderr=subprocess.STDOUT
        )
        try:
            deadline = time.monotonic() + 30
            while process.poll() is None and time.monotonic() < deadline:
                if "retrying after" in console_path.read_text(encoding="utf-8"):
                    break
                time.sleep(0.1)
            assert "retrying after" in console_path.read_text(encoding="utf-8")
            assert [row["transaction_id"] for row in read_results(tmp_path)] == ["broken"]
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=15)
    assert process.returncode != 0
    assert [row["transaction_id"] for row in read_results(tmp_path)] == ["broken"]
