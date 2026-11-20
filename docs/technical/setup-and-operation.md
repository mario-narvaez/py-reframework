# Setup and operation

[Project overview](../../README.md) | [Architecture](architecture.md) |
[Adaptation guide](adaptation-guide.md)

This guide is for operators and developers. Commands assume PowerShell on
Windows, run from the repository root, with Python 3.11 or newer and Windows
x64. The practice site has public demo credentials; use no real passwords
or personal information on it.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The Browser Library batteries package includes the Node.js runtime, so a
separate Node.js installation is not needed. Install Chromium:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
.\.venv\Scripts\python.exe -m Browser.entry install chromium
```

Set `PLAYWRIGHT_BROWSERS_PATH` in each new terminal before running browser
automation. Installation downloads browser files. See the
[Browser Library installation guide](https://robotframework-browser.org/docs/start/installation/)
for other platforms and setup options.

Verify the tools:

```powershell
.\.venv\Scripts\python.exe -m robot --version
.\.venv\Scripts\python.exe -m pytest --version
.\.venv\Scripts\python.exe -m pip check
```

[.env.example](../../.env.example) lists placeholder credential names. The
project does not load `.env` files; the commands below set environment
variables in the current PowerShell session.

## Configuration

[config/settings.csv](../../config/settings.csv) uses `setting,value`
columns. It supplies the portal URL, input CSV path, output directory,
maximum retries, retry delay, and download timeout. Paths are resolved
relative to the settings file's directory.

| Setting | Meaning | Valid range / sample value |
| --- | --- | --- |
| `portal_url` | Initial portal page. | HTTP(S) URL without credentials or a fragment. |
| `input_csv` | Transaction input file. | `../data/transactions.csv` |
| `output_dir` | Parent directory for run folders. | `../output` |
| `max_retries` | Additional attempts after the first. | 0-10; sample: 1. |
| `retry_delay_seconds` | Wait before a retry. | 0-300 seconds; sample: 5. |
| `download_timeout_seconds` | Download wait limit. | 1-300 seconds; sample: 30. |

The configuration loader validates the settings format, URL, paths, and
integer ranges. It resolves paths but does not check input existence or create
directories. Batch initialization reads and validates the input, then creates
the output directory and report. Retry settings apply only to the batch's
identified temporary errors described below.

Python callers can import `load_settings` from `py_reframework.config` and
use the returned `Settings` object. For Python commands outside pytest, make
the source directory importable in the current session:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
```

## Prepare input

Edit [data/transactions.csv](../../data/transactions.csv), or set `input_csv`
to another CSV. The header must match exactly, with one row per transaction:

```csv
transaction_id,start_date,end_date
period-001,2025-01-01,2025-01-31
period-002,2025-02-01,2025-02-28
period-invalid,2025-03-31,2025-03-01
```

IDs must be nonempty and unique within the input. Dates must be valid
`YYYY-MM-DD` dates, with the start on or before the end. The final sample row
deliberately has its start after its end: it demonstrates a business failure
and makes the batch return a nonzero exit code. Remove or correct it for an
all-successful run.

## Run a batch

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
$env:PORTAL_USERNAME = 'admin'
$env:PORTAL_PASSWORD = 'admin123'
.\.venv\Scripts\python.exe -m robot --outputdir output\robot `
    robot\tasks\process_transactions.robot
```

The credentials above are the practice site's public values. The task runs
headlessly by default; add `--variable HEADLESS:False` before the task path to
see the browser.

### Outputs

Downloaded text statements are the **primary output**. Each run creates a
unique folder under the configured output directory, with a separate
`statement-.../statement.txt` for each download. The statement contains
the requested dates and placeholder text, not actual transaction records.

The run's `results.csv` is a secondary tracking report:

| Column | Meaning |
| --- | --- |
| `transaction_id`, `start_date`, `end_date` | The input row. |
| `status` | `success`, `business_failure`, or `system_failure`. |
| `attempts` | Processing attempts; invalid rows have zero. |
| `download_path` | Full path for success; empty for a recorded failure. |
| `error` | Error description for a recorded failure. |

To reduce spreadsheet formula risks, values beginning with `=`, `+`, `-`,
or `@`, including after whitespace, are prefixed with an apostrophe in the
report. Treat CSV files as untrusted when opening them in spreadsheet software.

Robot writes `output.xml`, `log.html`, and `report.html` to `output/robot/`
for the command above. Inspect `log.html` for execution details and failure
information. A later run using the same Robot output directory can overwrite
those reports; run folders and downloaded files are unique.

### Failures, retries, and partial runs

- Invalid IDs or dates are recorded as `business_failure` and are not
  retried. Processing continues, but the task ultimately returns a nonzero
  exit code if any row fails.
- When the initial portal page returns HTTP 502, 503, or 504, the bot closes
  the browser, waits for the configured delay, and retries up to
  `max_retries` times in a fresh browser session. Other errors, including
  browser timeouts, are not automatically assumed to be temporary.
- When those retries are exhausted, or a downloaded statement fails the
  existing content check, the bot records `system_failure` and proceeds.
  Success resets the consecutive system-failure count; invalid business rows
  leave it unchanged. After three consecutive system failures the run stops.
  This includes content-check failures and does not prove a portal-wide outage.
- Unexpected browser errors, rejected credentials, non-retryable HTTP
  responses, and other run-wide failures stop immediately. Any recorded
  failure makes the task return a nonzero exit code. The console summarizes
  recorded outcomes; the Robot log provides more detail.
- Missing or malformed input, configuration errors during initialization,
  and results-write failures stop the run and may leave no row for the
  failure. Previously downloaded files and a partial report can remain,
  including a download that failed verification. Inspect them before
  rerunning.

New run folders prevent overwriting earlier output, but rerunning can
download the same items again. There is no durable restart, cross-run
deduplication, or multi-worker queue.

Browser Library is configured to take screenshots on its keyword failures;
the task also attempts a screenshot on other failures if a browser is open.
Capture can fail, so do not assume every failure has a screenshot. Reports,
screenshots, and downloaded files can contain sensitive information. Browser's
secret-input keyword avoids logging credentials during entry, but debug logs
and screenshots still require care.

## Run one statement

After setup, use the public demo credentials:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
$env:PORTAL_USERNAME = 'admin'
$env:PORTAL_PASSWORD = 'admin123'
.\.venv\Scripts\python.exe -m robot --outputdir output\robot `
    --variable START_DATE:2025-01-01 --variable END_DATE:2025-01-31 `
    robot\tasks\download_statement.robot
```

Replace the dates with a valid `YYYY-MM-DD` range. Add
`--variable HEADLESS:False` before the task path to see the browser. The
statement is saved in a unique folder under the configured output directory;
inspect `log.html` for its path and execution details. The task returns a
nonzero exit code on failure. It does not retry automatically.

## Run tests

The Python tests include local browser integration tests. They require the
installed Chromium browser, but do not depend on the public practice site.
The mock requires the login and Banking navigation sequence for testing;
the real site's Banking page does not require login.

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
.\.venv\Scripts\python.exe -m pytest
```

Run the local selector checks separately:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
.\.venv\Scripts\python.exe -m robot --outputdir output\selector-tests tests\robot\selector_contract.robot
```
