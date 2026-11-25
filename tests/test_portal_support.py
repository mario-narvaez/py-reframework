import os
import subprocess
import sys
from pathlib import Path

import pytest

from py_reframework.exceptions import BusinessRuleError, ConfigurationError, SystemFailure
from py_reframework.portal_support import (
    load_portal_credentials,
    prepare_statement_request,
    verify_demo_statement,
)


@pytest.fixture
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "settings.csv"
    path.write_text(
        "setting,value\n"
        "portal_url,https://example.com/\n"
        "portal_username,\n"
        "portal_password,\n"
        "input_csv,input.csv\n"
        "output_dir,output\n"
        "max_retries,2\n"
        "retry_delay_seconds,5\n"
        "download_timeout_seconds,30\n"
        "demo_delay_preset,short\n"
        "demo_delay_short_seconds,1\n"
        "demo_delay_medium_seconds,3\n"
        "demo_delay_long_seconds,5\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PORTAL_USERNAME", "demo-user")
    monkeypatch.setenv("PORTAL_PASSWORD", "demo-password")
    return path


def test_prepares_distinct_download_locations(config_path: Path) -> None:
    first = prepare_statement_request(str(config_path), "2025-01-01", "2025-01-31")
    second = prepare_statement_request(str(config_path), "2025-01-01", "2025-01-31")
    assert first["portal_url"] == "https://example.com/"
    assert first["demo_delay_seconds"] == 1
    assert first["download_path"] != second["download_path"]
    first_path = Path(first["download_path"])
    assert first_path.name == "statement-001.txt"
    assert first_path.parent.name == "downloads"
    assert first_path.parent.is_dir()


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


def set_config_credentials(config_path: Path, username: str, password: str) -> None:
    content = config_path.read_text(encoding="utf-8")
    content = content.replace("portal_username,\n", f"portal_username,{username}\n")
    content = content.replace("portal_password,\n", f"portal_password,{password}\n")
    config_path.write_text(content, encoding="utf-8")


def test_credentials_come_from_the_settings_when_the_environment_has_none(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PORTAL_USERNAME")
    monkeypatch.delenv("PORTAL_PASSWORD")
    set_config_credentials(config_path, "csv-user", "csv-password")
    prepare_statement_request(str(config_path), "2025-01-01", "2025-01-31")
    assert os.environ["PORTAL_USERNAME"] == "csv-user"
    assert os.environ["PORTAL_PASSWORD"] == "csv-password"


def test_a_complete_environment_pair_takes_precedence(config_path: Path) -> None:
    set_config_credentials(config_path, "csv-user", "csv-password")
    load_portal_credentials(str(config_path))
    assert os.environ["PORTAL_USERNAME"] == "demo-user"
    assert os.environ["PORTAL_PASSWORD"] == "demo-password"


def test_an_incomplete_environment_pair_is_not_completed_from_the_settings(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_config_credentials(config_path, "csv-user", "csv-password")
    monkeypatch.setenv("PORTAL_USERNAME", "   ")
    with pytest.raises(ConfigurationError, match="PORTAL_USERNAME is missing"):
        load_portal_credentials(str(config_path))


def test_credentials_missing_everywhere_fail_before_creating_output(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PORTAL_USERNAME")
    monkeypatch.delenv("PORTAL_PASSWORD")
    set_config_credentials(config_path, "csv-user", "")
    with pytest.raises(ConfigurationError, match="credentials are missing") as failure:
        prepare_statement_request(str(config_path), "2025-01-01", "2025-01-31")
    assert "csv-user" not in str(failure.value)
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
    env["PYTHONPATH"] = str(root / "code" / "python")
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
            str(root / "code" / "robot" / "tasks" / "download_statement.robot"),
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


def test_robot_applies_demo_pacing_only_to_visible_browsers(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    resource = root / "code" / "robot" / "resources" / "demo_portal.resource"
    resource_path = str(resource).replace("\\", "${/}")
    suite = tmp_path / "pacing.robot"
    suite.write_text(
        f"""*** Settings ***
Resource    {resource_path}

*** Test Cases ***
Visible Browser Uses The Chosen Delay
    Set Suite Variable    ${{HEADLESS}}    False
    Set Suite Variable    ${{EXPECTED_HEADLESS}}    ${{False}}
    Set Suite Variable    ${{EXPECTED_DELAY}}    3 seconds
    Open Demo Portal    https://example.com/    3

Headless Browser Has No Added Delay
    Set Suite Variable    ${{HEADLESS}}    ${{True}}
    Set Suite Variable    ${{EXPECTED_HEADLESS}}    ${{True}}
    Set Suite Variable    ${{EXPECTED_DELAY}}    not-set
    Open Demo Portal    https://example.com/    3

*** Keywords ***
New Browser
    [Arguments]    ${{browser}}    ${{headless}}    ${{slowMo}}=not-set
    Should Be Equal    ${{headless}}    ${{EXPECTED_HEADLESS}}
    Should Be Equal    ${{slowMo}}    ${{EXPECTED_DELAY}}

New Context
    [Arguments]    ${{acceptDownloads}}
    No Operation

New Page
    No Operation

Go To
    [Arguments]    ${{url}}
    RETURN    ${{200}}
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "robot", "--outputdir", str(tmp_path / "robot"), str(suite)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
