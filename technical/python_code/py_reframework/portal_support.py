"""Validate a single statement request for the Robot workflow."""

import os
import re
from datetime import date, datetime
from itertools import count
from pathlib import Path

from robot.api.deco import keyword

from .config import load_settings
from .exceptions import BusinessRuleError, ConfigurationError, SystemFailure


def parse_date(value: str, name: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value, flags=re.ASCII):
        raise BusinessRuleError(f"{name} must use YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise BusinessRuleError(f"{name} must be a valid calendar date") from error


def validate_date_range(start_date: str, end_date: str) -> tuple[str, str]:
    start = parse_date(start_date, "start_date")
    end = parse_date(end_date, "end_date")
    if start > end:
        raise BusinessRuleError("start_date must be on or before end_date")
    return start.isoformat(), end.isoformat()


def validate_portal_credentials() -> None:
    for name in ("PORTAL_USERNAME", "PORTAL_PASSWORD"):
        if not os.environ.get(name, "").strip():
            raise ConfigurationError(f"Environment variable {name} must be set")


def create_run_directory(output_dir: Path) -> Path:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        for number in count(1):
            name = timestamp if number == 1 else f"{timestamp}-{number:02d}"
            run_dir = output_dir / name
            try:
                run_dir.mkdir()
                return run_dir
            except FileExistsError:
                continue
    except OSError as error:
        raise SystemFailure(f"Cannot create run directory in: {output_dir}") from error


def reserve_statement_path(run_dir: Path, number: int) -> str:
    downloads_dir = run_dir / "downloads"
    try:
        downloads_dir.mkdir(parents=True, exist_ok=True)
        path = downloads_dir / f"statement-{number:03d}.txt"
        if path.exists():
            raise SystemFailure(f"Statement path already exists: {path}")
    except OSError as error:
        raise SystemFailure(f"Cannot create download directory: {downloads_dir}") from error
    return str(path)


@keyword
def prepare_statement_request(config_path: str, start_date: str, end_date: str) -> dict:
    """Validate the request and reserve a unique folder for its download."""
    settings = load_settings(config_path)
    start, end = validate_date_range(start_date, end_date)
    validate_portal_credentials()
    run_dir = create_run_directory(settings.output_dir)
    return {
        "portal_url": settings.portal_url,
        "start_date": start,
        "end_date": end,
        "download_path": reserve_statement_path(run_dir, 1),
        "download_timeout_seconds": settings.download_timeout_seconds,
        "demo_delay_seconds": settings.demo_delay_seconds,
    }


@keyword
def check_demo_statement(path: str, start_date: str, end_date: str) -> bool:
    """Return whether the demo download contains the requested date range."""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SystemFailure(f"Cannot read downloaded statement: {path}") from error
    expected = f"Date Range: {start_date} to {end_date}"
    lines = content.splitlines()
    return "BANK STATEMENT" in lines and expected in lines


@keyword
def verify_demo_statement(path: str, start_date: str, end_date: str) -> None:
    """Fail if the demo download does not contain the requested date range."""
    if not check_demo_statement(path, start_date, end_date):
        raise SystemFailure("Downloaded statement does not contain the requested date range")
