# py-reframework

A proposed RPA proof of concept that applies ideas from UiPath REFramework to
Python automation, with the goal of creating a readable starting point for
future business automations. The first bot will download practice statements
for date ranges supplied in a CSV and record the results in another CSV.

## Status

The project can download and verify one simulated statement for a supplied
date range. The CSV transaction loop, results CSV, and retry policy have not
been implemented yet.

## From this demo to other solutions

The demo is a starting point for the same transaction-processing pattern used
in many business automations: initialize, get an item, process it, record the
outcome, and finish. For this portal, an item is a date range. For a different
solution, an item could be identified by one of the following:

| Identifier | Example of a future automation |
| --- | --- |
| Invoice number | Find an invoice and extract its details or download it. |
| Purchase order (PO) number | Find a purchase order and capture its status. |
| Deduction or claim ID | Look up a deduction or claim and record its details. |
| Shipment or tracking number | Check a delivery status. |
| Order number | Retrieve order details or status. |
| Vendor ID | Look up a vendor record. |
| Customer ID | Retrieve customer information. |
| Support case number | Check a case's current status. |

These are possible future adaptations, **not features of the demo portal or
implemented solutions**. The first bot's downloaded text file contains no
actual transaction records. The full multi-item lifecycle and outcome recording
are planned, not yet implemented.

### What can be reused or adapted?

| Component | Current role | For another solution |
| --- | --- | --- |
| Robot Framework and Browser Library | Run keywords, interact with the browser, and provide execution reports. | The same tools can be used without rewriting them; project dependencies or versions may need changes. |
| [Failure types](src/py_reframework/exceptions.py) | Define business and system failure categories. | The categories can be a starting point; classification and handling need review for each process. |
| [Configuration loader](src/py_reframework/config.py) and [settings](config/settings.csv) | Read and validate this bot's settings. | Reuse the approach; update values and adapt the schema and validation if requirements differ. |
| [Robot task](robot/tasks/download_statement.robot) | Orchestrates one statement download. | Adapt the steps and inputs; a generic transaction loop is not implemented yet. |
| [Portal resource](robot/resources/demo_portal.resource) | Contains demo login, selectors, and download actions. | Replace or adapt login, navigation, selectors, and actions for the target application. |
| [Statement support](src/py_reframework/portal_support.py) | Validates date ranges and verifies the demo statement. | Replace or adapt validation and output checks for invoices, orders, or other records. |
| [Tests](tests/) | Check current settings, validation, and selectors. | Adapt and add tests for the new application's rules and failure paths. |

No project module is guaranteed to work unchanged for every solution. Reuse
must be verified, especially when an automation changes external data: retries
and restart rules for an update may differ from those for a download. CSV
transaction processing, outcome recording, and recovery are intended reusable
building blocks, but are not yet implemented or proven across solutions.

An AI assistant can help identify the changes, draft portal keywords and
validation, and create tests. A person should review the requirements, access
permissions, selectors, security, and test results; do not share secrets or
sensitive business data with an AI tool.

## Proposed approach

- Use Robot Framework tasks for the automation lifecycle and Browser Library
  for Playwright-based web interaction.
- Build project-specific Python modules for data validation, transaction
  outcomes, and CSV or Excel export.
- Define configuration, business versus system failures, bounded retries,
  logging, and recovery explicitly rather than assuming Robot Framework
  provides REFramework-equivalent behavior out of the box.

## First automation

The selected target is the
[Automation Practice Web Application](https://hash-chandra.github.io/demowebapp/).
It is a free practice site with public demo credentials; no account registration
is needed.

The proposed workflow is:

1. Read start and end dates from an input CSV, treating each date range as a
   transaction.
2. Log in using the site's demo credentials and open the Banking page.
3. Enter the dates and download a statement for each transaction.
4. Record the outcome and downloaded filename in a results CSV.

The site's login is simulated, and the Banking page can be accessed without
logging in. Its statement is a text file containing the selected dates and
placeholder text, not actual transaction records or a CSV. This makes the
site useful for practicing the workflow, but it does not demonstrate
consolidation of real business records. Use only the site's demo credentials,
not real passwords or personal information.

The single-statement workflow is implemented; the input and results CSV
formats are not yet implemented. A later automation may adapt the framework to
a portal with structured business data.

## Project layout

- `robot/tasks/`: high-level Robot Framework tasks.
- `robot/resources/`: reusable Robot keywords and portal interactions.
- `config/settings.csv`: non-secret settings for the bot.
- `src/py_reframework/`: Python configuration, validation, and failure types.
- `tests/`: automated tests for Python components.
- `output/`: generated results and reports; excluded from Git.

The `.gitkeep` files keep empty folders in Git until they contain project files.

## Configuration and failure types

`config/settings.csv` has `setting,value` columns. It defines the portal URL,
input CSV path, output directory, maximum retries, delay between retries, and
download timeout.
Paths are resolved relative to the settings file's directory. The loader
validates the settings format, URL, paths, and integer ranges (0-10 retries and
0-300 seconds for retry delay, 1-300 seconds for download timeout); it does not
create paths or check that input data exists.
`max_retries` means additional attempts after the first attempt. The settings
do not implement retries by themselves.

Python code can call `load_settings` from `py_reframework.config` and use the
returned `Settings` object. `ConfigurationError` is a `SystemFailure`;
`BusinessRuleError` represents an invalid transaction, and
`TransientSystemError` identifies a potentially retryable technical failure.
These types do not yet define how Robot handles failures across its Python
boundary.

For Python commands outside pytest, make `src` available for imports in the
current PowerShell session:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
```

Run the Python tests from the repository root (pytest configures its own
import path):

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_config.py tests\test_portal_support.py
```

## Run one demo statement

After completing the development setup, run the following in PowerShell from
the repository root. The credentials below are the site's public demo values;
never use real credentials or personal information on this practice site.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
$env:PORTAL_USERNAME = 'admin'
$env:PORTAL_PASSWORD = 'admin123'
.\.venv\Scripts\python.exe -m robot --outputdir output\robot `
    --variable START_DATE:2025-01-01 --variable END_DATE:2025-01-31 `
    robot\tasks\download_statement.robot
```

Replace the dates with a valid `YYYY-MM-DD` range. The task runs headlessly by
default; add `--variable HEADLESS:False` before the task path to see the browser.
Each run saves the statement in a unique folder under the configured output
directory, so it does not overwrite previous downloads. Robot reports are
written to `output/robot/`; inspect `log.html` for the saved path and
execution details. A failed task returns a nonzero exit code.

Browser Library is configured to take screenshots on its keyword failures;
the task also attempts a screenshot on other failures if a browser is open.
Screenshots, reports, and downloaded files can contain sensitive information
and should be handled accordingly. The bot uses Browser's secret-input
keyword to avoid logging credentials, but debug logs and screenshots require
care. Automatic retries and a results CSV are not implemented.

## Portal selectors

The portal resource uses the site's `data-testid` attributes where available.
For navigation links without test IDs, the login link is identified by its
role and name within the navigation bar; the Banking link is scoped to the
sidebar and identified by its route. These selectors describe the elements,
not fixed screen coordinates. Browser Library uses strict matching by default:
an ambiguous action fails instead of silently choosing a match. Selectors can
still break if the site changes, so verify them when updating the workflow.

Run the local selector checks after installing Chromium:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
.\.venv\Scripts\python.exe -m robot --outputdir output\selector-tests tests\robot\selector_contract.robot
```

## Development setup

These commands are for PowerShell on Windows with Python 3.11 or newer and
Windows x64. From the repository root, create a virtual environment and install
the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The Browser Library batteries package includes the Node.js runtime, so a
separate Node.js installation is not needed. Install its Chromium browser:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv\ms-playwright')
.\.venv\Scripts\python.exe -m Browser.entry install chromium
```

Set `PLAYWRIGHT_BROWSERS_PATH` in each new terminal before running future
browser automation, so it uses the browser installed in this virtual
environment. The installation downloads browser files. See the
[Browser Library installation guide](https://robotframework-browser.org/docs/start/installation/)
for other platforms and setup options.

Verify the tools:

```powershell
.\.venv\Scripts\python.exe -m robot --version
.\.venv\Scripts\python.exe -m pytest --version
.\.venv\Scripts\python.exe -m pip check
```

The `.env.example` file lists placeholder credential names. The project does
not load `.env` files yet; do not put real passwords or personal data in the
demo portal or commit credentials.
