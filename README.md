# py-reframework

A proposed RPA proof of concept that applies ideas from UiPath REFramework to
Python automation. The first bot will download practice statements for date
ranges supplied in a CSV and record the results in another CSV.

## Status

The project has a development setup, a CSV settings loader, and Python failure
types. No browser automation, transaction queue, retry policy, or export
functionality has been implemented yet.

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

The automation and CSV formats have not been implemented yet. A later
automation may adapt the framework to a portal with structured business data.

## Project layout

- `robot/tasks/`: future high-level Robot Framework tasks.
- `robot/resources/`: future reusable Robot keywords and portal interactions.
- `config/settings.csv`: non-secret settings for the planned bot.
- `src/py_reframework/`: Python configuration and failure types; future data
  and transaction logic.
- `tests/`: automated tests for Python components.
- `output/`: generated results and reports; excluded from Git.

The `.gitkeep` files keep empty folders in Git until they contain project files.

## Configuration and failure types

`config/settings.csv` has `setting,value` columns. It defines the portal URL,
input CSV path, output directory, maximum retries, and delay between retries.
Paths are resolved relative to the settings file's directory. The loader
validates the settings format, URL, paths, and integer ranges (0-10 retries and
0-300 seconds); it does not create paths or check that input data exists.
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

Run the configuration tests from the repository root (pytest configures its own
import path):

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_config.py
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
