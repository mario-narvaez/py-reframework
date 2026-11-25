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

[technical/config/settings.csv](../../technical/config/settings.csv) uses `setting,value`
columns. It supplies the portal URL, input CSV path, output directory,
maximum retries, retry delay, download timeout, and visible-demo pacing.
Paths are resolved relative to the settings file's directory.

| Setting | Meaning | Valid range / sample value |
| --- | --- | --- |
| `portal_url` | Initial portal page. | HTTP(S) URL without credentials or a fragment. |
| `input_csv` | Transaction input file. | `../../process/input/transactions.csv` |
| `output_dir` | Parent directory for run folders. | `../../process/output/runs` |
| `max_retries` | Additional attempts after the first. | 0-10; sample: 1. |
| `retry_delay_seconds` | Wait before a retry. | 0-300 seconds; sample: 5. |
| `download_timeout_seconds` | Download wait limit. | 1-300 seconds; sample: 30. |
| `demo_delay_preset` | Pacing preset for a visible browser. | `short`, `medium`, or `long`; sample: `short`. |
| `demo_delay_short_seconds` | Short demo pacing. | 0-30 seconds; sample: 1. |
| `demo_delay_medium_seconds` | Medium demo pacing. | 0-30 seconds; sample: 3. |
| `demo_delay_long_seconds` | Long demo pacing. | 0-30 seconds; sample: 5. |

The configuration loader validates the settings format, URL, paths, and
integer ranges. It resolves paths but does not check input existence or create
directories. Batch initialization reads and validates the input, then creates
the output directory and report. Retry settings apply only to the batch's
identified temporary errors described below. Demo delays must be ordered
short <= medium <= long. Existing custom settings files must include the demo
settings too.

Python callers can import `load_settings` from `py_reframework.config` and
use the returned `Settings` object. For Python commands outside pytest, make
the source directory importable in the current session:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'technical\python_code')
```

## Prepare input

Edit [process/input/transactions.csv](../../process/input/transactions.csv), or set `input_csv`
to another CSV. The header must match exactly, with one row per transaction:

```csv
transaction_id,start_date,end_date
period-001,2025-01-01,2025-01-31
period-002,2025-02-01,2025-02-28
period-invalid,2025-03-01,
period-003,2025-04-01,2025-04-30
period-004,2025-05-01,2025-05-31
period-005,2025-06-01,2025-06-30
period-invalid-002,,2025-07-31
```

IDs must be nonempty and unique within the input. Dates must be valid
`YYYY-MM-DD` dates, with the start on or before the end. Two sample rows
deliberately have a missing date: the bot enters the available date, observes
that the website has disabled Apply Range, and records a business failure.
The website does not display an error message for this. Remove or correct
both for an all-successful run. Malformed nonempty dates and reversed ranges
are rejected before browser interaction.

## Run a batch

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'technical\python_code')
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
$env:PORTAL_USERNAME = 'admin'
$env:PORTAL_PASSWORD = 'admin123'
.\.venv\Scripts\python.exe -m robot --outputdir process\output\reports\robot `
    technical\robot\tasks\process_transactions.robot
```

The credentials above are the practice site's public values. By default, the
browser is visible so you can watch it work. To hide the browser window, add
`--variable HEADLESS:True` before the task path. In this headless mode, the
browser still operates the website, downloads statements, and records results.
A visible browser uses the configured demo pacing preset;
headless runs have no added demo pacing. Browser Library's `slowMo` slows
Playwright operations, so it does not guarantee exactly one second per visible
interaction or keep the browser open at the end. This is for observation, not
reliability: readiness checks and timeouts still apply. The preset values are
project choices, not industry standards.

A simple launcher is being considered for the future; it is not implemented.

The batch logs in and opens Banking during initialization. For each eligible
row, it enters the dates, clicks Apply Range, checks the visible Selected
range, downloads the statement, and clears both date fields. The demo site's
Apply Range button has no action of its own, but the bot clicks it as part of
the workflow. An incomplete range cannot be clicked because the site disables
the button; the bot clears the fields and continues to the next row.

### Outputs

Downloaded text statements are the **primary output**. Each run creates a
folder under the configured output directory named with the computer's local
date and time, for example `2026-11-20_13-51-54`. Runs started in the same
second receive suffixes such as `-02` to prevent overwriting.

The batch places `results.csv` in the run folder and numbers downloads in its
`downloads/` subfolder, for example `statement-001.txt` and
`statement-002.txt`. The statement contains the requested dates and
placeholder text, not actual transaction records.

With the sample settings, a batch looks like this:

```text
process/
  input/transactions.csv
  output/
    runs/2026-11-20_13-51-54/
      results.csv
      downloads/
        statement-001.txt
        statement-002.txt
    reports/robot/
      log.html
      report.html
      output.xml
```

The console shows the actual `results.csv` path. Existing files in the former
`output/` directory are not automatically moved or deleted.

The run's `results.csv` is a secondary tracking report:

| Column | Meaning |
| --- | --- |
| `transaction_id`, `start_date`, `end_date` | The input row. |
| `status` | `success`, `business_failure`, or `system_failure`. |
| `attempts` | Processing attempts; rows rejected before browser interaction have zero. |
| `download_path` | Full path for success; empty for a recorded failure. |
| `error` | Error description for a recorded failure. |

To reduce spreadsheet formula risks, values beginning with `=`, `+`, `-`,
or `@`, including after whitespace, are prefixed with an apostrophe in the
report. Treat CSV files as untrusted when opening them in spreadsheet software.

Robot writes `output.xml`, `log.html`, and `report.html` to
`process/output/reports/robot/` for the command above. Inspect `log.html`
for execution details and failure information. A later run using the same
Robot output directory can overwrite those reports; run folders and downloaded
files are unique.

### Failures, retries, and partial runs

- Invalid IDs, malformed dates, and reversed ranges are recorded as
  `business_failure` before browser interaction. Missing dates are entered
  on the website and recorded as a business failure when Apply Range is
  disabled. Business failures are not retried. Processing continues, but the
  task ultimately returns a nonzero exit code if any row fails.
- When the initial portal page returns HTTP 502, 503, or 504, the bot closes
  the browser, waits for the configured delay, and retries up to
  `max_retries` times in a fresh browser session. Other errors, including
  browser timeouts, are not automatically assumed to be temporary.
- If initialization retries are exhausted, the run stops without assigning
  the failure to a row. If retries are exhausted during later session
  recovery, or a downloaded statement fails the existing content check, the
  bot records `system_failure` and proceeds.
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
$env:PYTHONPATH = (Join-Path (Get-Location) 'technical\python_code')
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
$env:PORTAL_USERNAME = 'admin'
$env:PORTAL_PASSWORD = 'admin123'
.\.venv\Scripts\python.exe -m robot --outputdir process\output\reports\robot `
    --variable START_DATE:2025-01-01 --variable END_DATE:2025-01-31 `
    technical\robot\tasks\download_statement.robot
```

Replace the dates with a valid `YYYY-MM-DD` range. The browser is visible by
default; add `--variable HEADLESS:True` before the task path to hide it. The
statement is saved as `downloads/statement-001.txt` inside a dated run folder
under the configured output directory. This task does not create a results CSV;
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
.\.venv\Scripts\python.exe -m robot --outputdir process\output\reports\selector-tests technical\tests\robot\selector_contract.robot
```
