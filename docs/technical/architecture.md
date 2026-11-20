# Architecture

[Project overview](../../README.md) | [Setup and operation](setup-and-operation.md) |
[Adaptation guide](adaptation-guide.md)

This guide is for developers and technical reviewers. The project is a
proof of concept inspired by UiPath REFramework; it is not the UiPath
framework or a general-purpose, production-ready RPA platform.

## The lifecycle

The batch follows the same broad stages familiar from REFramework:

```text
Initialize
  Read settings and the entire input CSV; validate its structure and rows.
  Create a unique run folder and an empty results report.
  Open the browser, log in, and navigate to Banking.
       |
Get transaction data
  Take the next already-loaded row.
       |
Process
  Invalid ID, malformed date, or reversed range? Record a business failure.
  Otherwise enter the available dates and check the Apply Range button.
  If disabled because a date is missing, record a business failure.
  Otherwise click Apply Range, verify Selected, download, clear both fields,
  verify the statement, and record the outcome.
       |
  Continue to the next row, or stop on a run-wide failure / failure threshold.
       |
End
  Report the recorded counts and close the browser when open.
```

The entire CSV is loaded before processing; there is no queue or durable
`GetTransactionData` state. Initialization requires a browser and credentials
even if every row is invalid. The practice site's login is simulated, and
Banking is accessible without it.

## How the pieces connect

```text
settings.csv + transactions.csv
              |
              v
Python: configuration, row validation, results CSV
              ^
              | explicit values and row error messages
              v
Robot batch task: lifecycle, attempts, outcomes, stop decisions
              |
              v
Robot portal resource + Browser Library
              |
              v
Practice website --> downloaded text file --> Python content check
              |
              +--> Robot execution report and possible screenshots
```

- **Robot Framework** runs the task and keywords and writes execution
  reports. The batch task holds the loop and recovery decisions.
- **Browser Library** controls Chromium through Playwright. The portal
  resource contains the demo's selectors and browser actions.
- **Python** loads and validates settings and rows, creates paths, verifies
  statement content, and writes the results CSV.
- The **downloaded statements** are the primary output. The results CSV
  tracks each recorded outcome; Robot's HTML/XML reports describe execution.

The checked-in Python libraries and Robot tasks are project code, not
components supplied by Robot Framework. Robot Framework and Browser Library
are external dependencies.

## Error and retry boundary

Python catches `BusinessRuleError` while validating a row and returns a row
with an explicit error message. Robot checks that value; it does not depend
on catching the Python exception class. Unexpected processing keyword
failures are handled by Robot as non-retryable system failures.

`ConfigurationError` extends `SystemFailure`; `TransientSystemError` is
defined as a category but is not what triggers the current Robot retry.
Instead, the task explicitly recognizes HTTP 502, 503, and 504 when opening
the initial portal page. It uses the configured retry count and delay. An
initialization failure stops the run without assigning it to a transaction;
later session recovery failures are handled per transaction.
Business failures are not retried. See the exact stop, screenshot, and
partial-run behavior in [setup and operation](setup-and-operation.md).

The three-consecutive-system-failure threshold counts both exhausted
temporary portal failures and statement content-check failures. It is a
safeguard for a *potential* outage, not proof the portal is unavailable.
There is no durable restart, cross-run deduplication, or multi-worker queue.

## File map

Documentation is grouped by audience. The `process/` folder holds sample
input and generated output. The `technical/` folder groups the implementation,
configuration, and tests; project metadata and tool configuration remain at
the repository root.

| Category | Files or folders | Purpose |
| --- | --- | --- |
| General documentation | [README.md](../../README.md), [business use cases](../general/use-cases.md) | Project overview and potential business applications. |
| Technical documentation | [Architecture](architecture.md), [setup and operation](setup-and-operation.md), [adaptation guide](adaptation-guide.md) | Design, execution, and guidance for developers. |
| Sample input | [process/input/transactions.csv](../../process/input/transactions.csv) | Example date ranges, including two deliberately invalid rows. |
| Non-secret configuration | [technical/config/settings.csv](../../technical/config/settings.csv), [.env.example](../../.env.example) | Runtime settings and placeholder environment-variable names. The project does not load `.env` files. |
| Robot orchestration | [technical/robot/tasks/process_transactions.robot](../../technical/robot/tasks/process_transactions.robot), [technical/robot/tasks/download_statement.robot](../../technical/robot/tasks/download_statement.robot) | Batch and individual-statement tasks. |
| Portal actions | [technical/robot/resources/demo_portal.resource](../../technical/robot/resources/demo_portal.resource) | Demo selectors, navigation, download, screenshots, and cleanup. |
| Python configuration | [technical/python_code/py_reframework/config.py](../../technical/python_code/py_reframework/config.py) | Settings parsing, validation, and path resolution. |
| Python transaction handling | [technical/python_code/py_reframework/transactions.py](../../technical/python_code/py_reframework/transactions.py) | CSV input, row outcomes, and results reporting. |
| Python portal support | [technical/python_code/py_reframework/portal_support.py](../../technical/python_code/py_reframework/portal_support.py) | Date validation, credential presence, paths, and content verification. |
| Python failure types | [technical/python_code/py_reframework/exceptions.py](../../technical/python_code/py_reframework/exceptions.py) | Business and system exception categories. |
| Tests | [technical/tests/](../../technical/tests/) | Python behavior, local mock-portal workflow, and Robot selector checks. |
| Development configuration | [requirements.txt](../../requirements.txt), [pytest.ini](../../pytest.ini), [.gitignore](../../.gitignore), [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | Dependencies, test configuration, ignored files, and project instructions. |
| Project metadata | [LICENSE](../../LICENSE), [technical/python_code/py_reframework/__init__.py](../../technical/python_code/py_reframework/__init__.py), `.gitkeep` files | License, package marker, and empty-folder placeholders. |

Generated files under the default `process/output/` directory and virtual
environments are excluded from Git. The previous `output/` directory remains
ignored for older generated files. If reports or screenshots are saved
elsewhere, check the ignore rules before committing. Treat downloaded files,
logs, and screenshots as potentially sensitive.

## Selectors and verification

The resource uses the site's `data-testid` attributes where available. Its
login link is selected by role and name within the navigation bar; its
Banking link is scoped to the sidebar and identified by route. Browser
Library's strict matching makes ambiguous actions fail instead of silently
choosing a match. Site changes can still break selectors.

`Apply Demo Date Range` clicks Apply Range for complete dates and verifies
that the visible Selected message contains the requested range. The demo
site's Apply Range button has no action of its own. For an incomplete range,
the button is disabled and the site does not display an error message.
`Download Demo Statement` clears both date fields after downloading and
returns the downloaded path; it does not itself
verify the file. Both current tasks call a Python content check afterward.
Any future caller must do the same, or implement an appropriate check for its
own output.

The local integration tests simulate a portal and check the intended
navigation, retry, failure evidence, and outcomes without depending on the
public website. The mock requires the login sequence for testing; this is
not a claim that the real practice site's Banking page requires login.
See [setup and operation](setup-and-operation.md) for test commands.
