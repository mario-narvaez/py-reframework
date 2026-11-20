import csv
from pathlib import Path

import pytest

from py_reframework.config import load_settings
from py_reframework.exceptions import ConfigurationError, SystemFailure


VALID_SETTINGS = {
    "portal_url": "https://example.com/demo/",
    "input_csv": "../data/transactions.csv",
    "output_dir": "../output",
    "max_retries": "2",
    "retry_delay_seconds": "5",
    "download_timeout_seconds": "30",
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
    assert settings.input_csv == tmp_path / "data" / "transactions.csv"
    assert settings.output_dir == tmp_path / "output"
    assert settings.max_retries == 2
    assert settings.retry_delay_seconds == 5
    assert settings.download_timeout_seconds == 30


def test_repository_settings_load() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "settings.csv"
    settings = load_settings(path)
    assert settings.portal_url == "https://hash-chandra.github.io/demowebapp/"


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
