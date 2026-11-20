"""Read date-range transactions and record outcomes for a single run."""

import csv
from pathlib import Path

from robot.api.deco import keyword

from .config import load_settings
from .exceptions import BusinessRuleError, ConfigurationError, SystemFailure
from .portal_support import (
    create_run_directory,
    parse_date,
    reserve_statement_path,
    validate_date_range,
)

_INPUT_COLUMNS = ["transaction_id", "start_date", "end_date"]
_RESULT_COLUMNS = _INPUT_COLUMNS + ["status", "attempts", "download_path", "error"]


def _read_transactions(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, strict=True)
            if next(reader, None) != _INPUT_COLUMNS:
                raise ConfigurationError(
                    "Input CSV header must be: transaction_id,start_date,end_date"
                )
            transactions = []
            seen_ids: set[str] = set()
            for row in reader:
                if len(row) != len(_INPUT_COLUMNS):
                    raise ConfigurationError(
                        f"Input CSV line {reader.line_num} must have three columns"
                    )
                transaction_id, start_date, end_date = (value.strip() for value in row)
                error = ""
                if not transaction_id:
                    error = "transaction_id must not be empty"
                elif transaction_id in seen_ids:
                    error = "transaction_id must be unique within the input"
                else:
                    seen_ids.add(transaction_id)
                    try:
                        if start_date and end_date:
                            validate_date_range(start_date, end_date)
                        elif start_date:
                            parse_date(start_date, "start_date")
                        elif end_date:
                            parse_date(end_date, "end_date")
                    except BusinessRuleError as failure:
                        error = str(failure)
                transactions.append(
                    {
                        "transaction_id": transaction_id,
                        "start_date": start_date,
                        "end_date": end_date,
                        "error": error,
                    }
                )
    except (OSError, UnicodeError, csv.Error) as error:
        raise ConfigurationError(f"Cannot read input CSV: {path}") from error
    if not transactions:
        raise ConfigurationError("Input CSV must contain at least one transaction")
    return transactions


def _safe_csv_value(value: str) -> str:
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@keyword
def initialize_batch(config_path: str) -> dict:
    """Validate input and create a unique run folder with a results CSV."""
    settings = load_settings(config_path)
    transactions = _read_transactions(settings.input_csv)
    run_dir = create_run_directory(settings.output_dir)
    try:
        results_path = run_dir / "results.csv"
        with results_path.open("x", encoding="utf-8", newline="") as file:
            csv.writer(file).writerow(_RESULT_COLUMNS)
    except OSError as error:
        raise SystemFailure(f"Cannot create results in: {settings.output_dir}") from error
    return {
        "portal_url": settings.portal_url,
        "download_timeout_seconds": settings.download_timeout_seconds,
        "demo_delay_seconds": settings.demo_delay_seconds,
        "max_retries": settings.max_retries,
        "retry_delay_seconds": settings.retry_delay_seconds,
        "run_dir": str(run_dir),
        "results_path": str(results_path),
        "transactions": transactions,
        "next_statement_number": 1,
    }


@keyword
def reserve_batch_statement_path(batch: dict) -> str:
    number = batch["next_statement_number"]
    path = reserve_statement_path(Path(batch["run_dir"]), number)
    batch["next_statement_number"] = number + 1
    return path


@keyword
def record_transaction_result(
    batch: dict, transaction: dict, status: str, download_path: str = "", error: str = "",
    attempts: int = 1,
) -> None:
    """Append one completed transaction to the results CSV."""
    if status not in {"success", "business_failure", "system_failure"}:
        raise ValueError(f"Invalid transaction status: {status}")
    values = [
        transaction["transaction_id"],
        transaction["start_date"],
        transaction["end_date"],
        status,
        str(attempts),
        download_path,
        error,
    ]
    try:
        with Path(batch["results_path"]).open("a", encoding="utf-8", newline="") as file:
            csv.writer(file).writerow(_safe_csv_value(value) for value in values)
    except OSError as failure:
        raise SystemFailure(f"Cannot write results CSV: {batch['results_path']}") from failure
