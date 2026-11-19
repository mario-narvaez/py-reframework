# py-reframework

A proposed RPA proof of concept that applies ideas from UiPath REFramework to
Python automation. The first bot will download practice statements for date
ranges supplied in a CSV and record the results in another CSV.

## Status

The project has a basic development setup. No automation, transaction queue,
retry policy, configuration loader, or export functionality has been
implemented yet.

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
- `src/py_reframework/`: future Python data and transaction logic.
- `tests/`: future automated tests.
- `output/`: generated results and reports; excluded from Git.

The `.gitkeep` files keep empty folders in Git until they contain project files.

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
