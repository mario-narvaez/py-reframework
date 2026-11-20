"""Load and validate non-secret settings from a CSV file."""

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .exceptions import ConfigurationError


@dataclass(frozen=True)
class Settings:
    portal_url: str
    input_csv: Path
    output_dir: Path
    max_retries: int
    retry_delay_seconds: int
    download_timeout_seconds: int


_REQUIRED_SETTINGS = {
    "portal_url",
    "input_csv",
    "output_dir",
    "max_retries",
    "retry_delay_seconds",
    "download_timeout_seconds",
}


def _read_settings(path: Path) -> dict[str, str]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, strict=True)
            if next(reader, None) != ["setting", "value"]:
                raise ConfigurationError("Settings CSV must have header: setting,value")

            settings: dict[str, str] = {}
            for row in reader:
                if len(row) != 2:
                    raise ConfigurationError(
                        f"Settings CSV line {reader.line_num} must have two columns"
                    )
                name, value = (column.strip() for column in row)
                if name not in _REQUIRED_SETTINGS:
                    raise ConfigurationError(
                        f"Unknown setting at line {reader.line_num}: {name!r}"
                    )
                if name in settings:
                    raise ConfigurationError(f"Duplicate setting: {name}")
                if not value:
                    raise ConfigurationError(f"Setting must not be empty: {name}")
                settings[name] = value
    except (OSError, UnicodeError, csv.Error) as error:
        raise ConfigurationError(f"Cannot read settings CSV: {path}") from error

    missing = _REQUIRED_SETTINGS - settings.keys()
    if missing:
        raise ConfigurationError(f"Missing settings: {', '.join(sorted(missing))}")
    return settings


def _validate_url(value: str) -> str:
    try:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.fragment
            or any(char.isspace() for char in value)
        ):
            raise ValueError("Invalid portal URL")
        _ = url.port
    except ValueError as error:
        raise ConfigurationError(
            "portal_url must be a valid HTTP(S) URL without credentials or a fragment"
        ) from error
    return value


def _bounded_integer(name: str, value: str, maximum: int, minimum: int = 0) -> int:
    if not value.isascii() or not value.isdecimal():
        raise ConfigurationError(
            f"{name} must be an integer between {minimum} and {maximum}"
        )
    digits = value.lstrip("0") or "0"
    if len(digits) > len(str(maximum)):
        raise ConfigurationError(
            f"{name} must be an integer between {minimum} and {maximum}"
        )
    number = int(digits)
    if not minimum <= number <= maximum:
        raise ConfigurationError(
            f"{name} must be an integer between {minimum} and {maximum}"
        )
    return number


def _resolve_path(name: str, value: str, base: Path) -> Path:
    if "\0" in value:
        raise ConfigurationError(f"{name} contains an invalid path")
    try:
        return (base / value).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise ConfigurationError(f"{name} contains an invalid path") from error


def load_settings(path: str | Path) -> Settings:
    """Read settings; relative input and output paths are based on the CSV directory."""
    try:
        config_path = Path(path).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise ConfigurationError("Invalid settings CSV path") from error
    values = _read_settings(config_path)
    return Settings(
        portal_url=_validate_url(values["portal_url"]),
        input_csv=_resolve_path("input_csv", values["input_csv"], config_path.parent),
        output_dir=_resolve_path("output_dir", values["output_dir"], config_path.parent),
        max_retries=_bounded_integer("max_retries", values["max_retries"], 10),
        retry_delay_seconds=_bounded_integer(
            "retry_delay_seconds", values["retry_delay_seconds"], 300
        ),
        download_timeout_seconds=_bounded_integer(
            "download_timeout_seconds", values["download_timeout_seconds"], 300, 1
        ),
    )
