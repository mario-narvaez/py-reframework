import os
import subprocess
import sys
from pathlib import Path

import pytest

from py_reframework.exceptions import BusinessRuleError, ConfigurationError, SystemFailure
from py_reframework.portal_support import prepare_statement_request, verify_demo_statement


@pytest.fixture
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "settings.csv"
    path.write_text(
        "setting,value\n"
        "portal_url,https://example.com/\n"
        "input_csv,input.csv\n"
        "output_dir,output\n"
        "max_retries,2\n"
        "retry_delay_seconds,5\n"
        "download_timeout_seconds,30\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PORTAL_USERNAME", "demo-user")
    monkeypatch.setenv("PORTAL_PASSWORD", "demo-password")
    return path


def test_prepares_distinct_download_locations(config_path: Path) -> None:
    first = prepare_statement_request(str(config_path), "2025-01-01", "2025-01-31")
    second = prepare_statement_request(str(config_path), "2025-01-01", "2025-01-31")
    assert first["portal_url"] == "https://example.com/"
    assert first["download_path"] != second["download_path"]
    assert Path(first["download_path"]).parent.is_dir()


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("", "2025-01-01"),
        ("20250101", "2025-01-01"),
        ("2025-02-29", "2025-03-01"),
        ("2025-02-01", "2025-01-31"),
    ],
)
def test_rejects_invalid_date_ranges(config_path: Path, start: str, end: str) -> None:
    with pytest.raises(BusinessRuleError):
        prepare_statement_request(str(config_path), start, end)
    assert not (config_path.parent / "output").exists()


def test_missing_credentials_fail_before_creating_output(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PORTAL_PASSWORD")
    with pytest.raises(ConfigurationError, match="PORTAL_PASSWORD"):
        prepare_statement_request(str(config_path), "2025-01-01", "2025-01-31")
    assert not (config_path.parent / "output").exists()


def test_verify_statement_content_and_wrong_dates(tmp_path: Path) -> None:
    path = tmp_path / "statement.txt"
    path.write_text(
        "BANK STATEMENT\nDate Range: 2025-01-01 to 2025-01-31\n",
        encoding="utf-8",
    )
    verify_demo_statement(str(path), "2025-01-01", "2025-01-31")
    with pytest.raises(SystemFailure, match="requested date range"):
        verify_demo_statement(str(path), "2025-02-01", "2025-02-28")
    path.write_text(
        "BANK STATEMENT\nDate Range: 2025-01-01 to 2025-01-310\n", encoding="utf-8"
    )
    with pytest.raises(SystemFailure, match="requested date range"):
        verify_demo_statement(str(path), "2025-01-01", "2025-01-31")


def test_missing_statement_is_a_system_failure(tmp_path: Path) -> None:
    with pytest.raises(SystemFailure, match="Cannot read"):
        verify_demo_statement(str(tmp_path / "missing.txt"), "2025-01-01", "2025-01-31")


def test_robot_stops_before_browser_for_invalid_date(config_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robot",
            "--output",
            "NONE",
            "--log",
            "NONE",
            "--report",
            "NONE",
            "--variable",
            f"CONFIG_FILE:{config_path}",
            "--variable",
            "START_DATE:2025-02-30",
            "--variable",
            "END_DATE:2025-03-01",
            str(root / "robot" / "tasks" / "download_statement.robot"),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert "start_date must be a valid calendar date" in result.stdout
    assert not (config_path.parent / "output").exists()
