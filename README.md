# py-reframework

A proposed RPA proof of concept that applies ideas from UiPath REFramework to
Python automation. The first bot will download practice statements for date
ranges supplied in a CSV and record the results in another CSV.

## Status

The project is at the architecture stage. No automation, transaction queue,
retry policy, or export functionality has been implemented yet.

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
