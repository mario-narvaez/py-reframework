import csv
from pathlib import Path

import pytest

from py_reframework.config import load_settings
from py_reframework.exceptions import ConfigurationError, SystemFailure


VALID_SETTINGS = {
    "portal_url": "https://example.com/demo/",
    "input_csv": "../process/input/transactions.csv",
    "output_dir": "../process/output/runs",
    "max_retries": "2",
    "retry_delay_seconds": "5",
    "download_timeout_seconds": "30",
    "demo_delay_preset": "short",
    "demo_delay_short_seconds": "1",
    "demo_delay_medium_seconds": "3",
    "demo_delay_long_seconds": "5",
}


def write_settings(path: Path, settings: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["setting", "value"])
        writer.writerows(settings.items())


def test_loads_settings_and_resolves_paths_relative_to_csv(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "settings.csv"
    write_settings(path, VALID_SETTINGS)

    settings = load_settings(path)

    assert settings.portal_url == "https://example.com/demo/"
    assert settings.input_csv == tmp_path / "process" / "input" / "transactions.csv"
    assert settings.output_dir == tmp_path / "process" / "output" / "runs"
    assert settings.max_retries == 2
    assert settings.retry_delay_seconds == 5
    assert settings.download_timeout_seconds == 30
    assert settings.demo_delay_seconds == 1


def test_repository_settings_load() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "settings.csv"
    settings = load_settings(path)
    assert settings.portal_url == "https://hash-chandra.github.io/demowebapp/"
    assert settings.input_csv == path.parents[2] / "process" / "input" / "transactions.csv"
    assert settings.input_csv.is_file()
    assert settings.output_dir == path.parents[2] / "process" / "output" / "runs"
    assert settings.max_retries == 1
    assert settings.retry_delay_seconds == 5


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("portal_url", "not a URL"),
        ("portal_url", "https://user:password@example.com/"),
        ("portal_url", "https://example.com:invalid/"),
        ("portal_url", "https://example.com/#fragment"),
        ("input_csv", ""),
        ("output_dir", "\0"),
        ("max_retries", "-1"),
        ("max_retries", "11"),
        ("max_retries", "1.5"),
        ("max_retries", "9" * 5000),
        ("retry_delay_seconds", "301"),
        ("download_timeout_seconds", "0"),
        ("download_timeout_seconds", "301"),
        ("demo_delay_preset", "unknown"),
        ("demo_delay_short_seconds", "-1"),
        ("demo_delay_medium_seconds", "1.5"),
        ("demo_delay_long_seconds", "31"),
        ("demo_delay_short_seconds", "4"),
    ],
)
def test_rejects_invalid_values(tmp_path: Path, name: str, value: str) -> None:
    path = tmp_path / "settings.csv"
    write_settings(path, {**VALID_SETTINGS, name: value})
    with pytest.raises(ConfigurationError):
        load_settings(path)


@pytest.mark.parametrize(
    "content",
    [
        "key,value\nportal_url,https://example.com/\n",
        "setting,value\nportal_url,https://example.com/\n",
        "setting,value\nportal_url,https://example.com/\nportal_url,https://example.com/\n",
        "setting,value\nunknown,value\n",
        "setting,value\nportal_url,https://example.com/,extra\n",
        'setting,value\nportal_url,"unterminated\n',
    ],
)
def test_rejects_invalid_csv(tmp_path: Path, content: str) -> None:
    path = tmp_path / "settings.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_settings(path)


def test_missing_file_is_a_system_failure(tmp_path: Path) -> None:
    with pytest.raises(SystemFailure, match="Cannot read settings CSV"):
        load_settings(tmp_path / "missing.csv")


@pytest.mark.parametrize(("retries", "delay"), [("0", "0"), ("10", "300")])
def test_accepts_retry_boundaries(tmp_path: Path, retries: str, delay: str) -> None:
    path = tmp_path / "settings.csv"
    write_settings(
        path, {**VALID_SETTINGS, "max_retries": retries, "retry_delay_seconds": delay}
    )
    settings = load_settings(path)
    assert settings.max_retries == int(retries)
    assert settings.retry_delay_seconds == int(delay)


@pytest.mark.parametrize(("preset", "expected"), [("short", 1), ("medium", 3), ("long", 5)])
def test_selects_configured_demo_delay(tmp_path: Path, preset: str, expected: int) -> None:
    path = tmp_path / "settings.csv"
    write_settings(path, {**VALID_SETTINGS, "demo_delay_preset": preset})
    assert load_settings(path).demo_delay_seconds == expected


def test_rejects_missing_demo_setting(tmp_path: Path) -> None:
    path = tmp_path / "settings.csv"
    settings = VALID_SETTINGS.copy()
    del settings["demo_delay_medium_seconds"]
    write_settings(path, settings)
    with pytest.raises(ConfigurationError, match="demo_delay_medium_seconds"):
        load_settings(path)
