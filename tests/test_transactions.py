import csv
from pathlib import Path

import pytest

from py_reframework.exceptions import ConfigurationError, SystemFailure
from py_reframework.transactions import initialize_batch, record_transaction_result


@pytest.fixture
def paths(tmp_path: Path) -> tuple[Path, Path]:
    config = tmp_path / "settings.csv"
    input_path = tmp_path / "input.csv"
    config.write_text(
        "setting,value\n"
        "portal_url,https://example.com/\n"
        "input_csv,input.csv\n"
        "output_dir,output\n"
        "max_retries,2\n"
        "retry_delay_seconds,5\n"
        "download_timeout_seconds,30\n",
        encoding="utf-8",
    )
    return config, input_path


def test_validates_each_row_and_creates_distinct_run_reports(
    paths: tuple[Path, Path],
) -> None:
    config, input_path = paths
    input_path.write_text(
        "transaction_id,start_date,end_date\n"
        "ok,2025-01-01,2025-01-31\n"
        "bad,2025-02-30,2025-03-01\n"
        "ok,2025-02-01,2025-02-28\n"
        ",2025-02-01,2025-02-28\n",
        encoding="utf-8",
    )
    batch = initialize_batch(str(config))
    assert batch["transactions"][0]["error"] == ""
    assert "calendar date" in batch["transactions"][1]["error"]
    assert "unique" in batch["transactions"][2]["error"]
    assert "empty" in batch["transactions"][3]["error"]
    assert initialize_batch(str(config))["results_path"] != batch["results_path"]

    record_transaction_result(batch, batch["transactions"][0], "success", "statement.txt")
    record_transaction_result(
        batch, batch["transactions"][1], "business_failure", error="Invalid date"
    )
    with Path(batch["results_path"]).open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert [row["status"] for row in rows] == ["success", "business_failure"]
    assert rows[0]["download_path"] == "statement.txt"
    assert rows[1]["download_path"] == ""


@pytest.mark.parametrize(
    "content",
    [
        "id,start_date,end_date\n",
        "transaction_id,start_date,end_date\n",
        "transaction_id,start_date,end_date\none,2025-01-01\n",
        'transaction_id,start_date,end_date\none,"unterminated\n',
    ],
)
def test_rejects_bad_input_before_creating_output(
    paths: tuple[Path, Path], content: str
) -> None:
    config, input_path = paths
    input_path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        initialize_batch(str(config))
    assert not (config.parent / "output").exists()


def test_missing_input_is_a_configuration_failure(paths: tuple[Path, Path]) -> None:
    config, _ = paths
    with pytest.raises(ConfigurationError, match="Cannot read input CSV"):
        initialize_batch(str(config))


def test_results_neutralize_spreadsheet_formulas(paths: tuple[Path, Path]) -> None:
    config, input_path = paths
    input_path.write_text(
        "transaction_id,start_date,end_date\n"
        "  =1+1,=bad,2025-01-01\n",
        encoding="utf-8",
    )
    batch = initialize_batch(str(config))
    transaction = batch["transactions"][0]
    record_transaction_result(batch, transaction, "business_failure", error=transaction["error"])
    with Path(batch["results_path"]).open(encoding="utf-8", newline="") as file:
        row = next(csv.DictReader(file))
    assert row["transaction_id"] == "'=1+1"
    assert row["start_date"] == "'=bad"


def test_result_write_failure_stops_the_run(
    paths: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    config, input_path = paths
    input_path.write_text(
        "transaction_id,start_date,end_date\n"
        "one,2025-01-01,2025-01-31\n",
        encoding="utf-8",
    )
    batch = initialize_batch(str(config))

    def fail_open(*args, **kwargs):
        raise OSError("write failed")

    monkeypatch.setattr(Path, "open", fail_open)
    with pytest.raises(SystemFailure, match="Cannot write results CSV"):
        record_transaction_result(batch, batch["transactions"][0], "success")
