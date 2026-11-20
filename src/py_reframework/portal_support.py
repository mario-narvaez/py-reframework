"""Validate a single statement request for the Robot workflow."""

import os
import re
import tempfile
from datetime import date
from pathlib import Path

from robot.api.deco import keyword

from .config import load_settings
from .exceptions import BusinessRuleError, ConfigurationError, SystemFailure


def _parse_date(value: str, name: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value, flags=re.ASCII):
        raise BusinessRuleError(f"{name} must use YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise BusinessRuleError(f"{name} must be a valid calendar date") from error


def validate_date_range(start_date: str, end_date: str) -> tuple[str, str]:
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if start > end:
        raise BusinessRuleError("start_date must be on or before end_date")
    return start.isoformat(), end.isoformat()


def validate_portal_credentials() -> None:
    for name in ("PORTAL_USERNAME", "PORTAL_PASSWORD"):
        if not os.environ.get(name, "").strip():
            raise ConfigurationError(f"Environment variable {name} must be set")


def reserve_statement_path(output_dir: Path) -> str:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        run_dir = Path(tempfile.mkdtemp(prefix="statement-", dir=output_dir))
    except OSError as error:
        raise SystemFailure(f"Cannot create download directory: {output_dir}") from error
    return str(run_dir / "statement.txt")


@keyword
def prepare_statement_request(config_path: str, start_date: str, end_date: str) -> dict:
    """Validate the request and reserve a unique folder for its download."""
    settings = load_settings(config_path)
    start, end = validate_date_range(start_date, end_date)
    validate_portal_credentials()
    return {
        "portal_url": settings.portal_url,
        "start_date": start,
        "end_date": end,
        "download_path": reserve_statement_path(settings.output_dir),
        "download_timeout_seconds": settings.download_timeout_seconds,
    }


@keyword
def verify_demo_statement(path: str, start_date: str, end_date: str) -> None:
    """Check that the demo download contains the requested date range."""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SystemFailure(f"Cannot read downloaded statement: {path}") from error
    expected = f"Date Range: {start_date} to {end_date}"
    lines = content.splitlines()
    if "BANK STATEMENT" not in lines or expected not in lines:
        raise SystemFailure("Downloaded statement does not contain the requested date range")
