# Project instructions

Apply these instructions when working in this repository. Read the relevant
code and documentation before changing them, and keep changes focused on the
requested work. Treat the roadmap below as a guide, not as implemented
functionality or permission to start future phases without being asked.

## Project goal

Build a readable RPA proof of concept that applies UiPath REFramework ideas
using Robot Framework and Python. The first automation uses the free
[Automation Practice Web Application](https://hash-chandra.github.io/demowebapp/)
to practice login, entering a date range, and downloading a statement for each
input CSV row. Record each outcome and downloaded filename in a results CSV.
Keep components understandable and reusable by both people and AI assistants.

The portal's login is simulated and is not required for its Banking page. Its
download is a text file with dates and placeholder text, not structured business
records. Do not represent it as a real transaction export; use only the site's
demo credentials and no real personal information. A later portal may provide
structured data for consolidation.

## Git workflow

- Initial repository setup may be done on `main`. After setup, implement
  features, fixes, and documentation changes on focused branches rather than
  editing `main` directly. Use prefixes such as `feat/`, `fix/`, `docs/`, and
  `refactor/`.
- Keep commits small and coherent, using Conventional Commit prefixes such as
  `feat:`, `fix:`, `docs:`, `test:`, and `chore:`.
- Review changes and use a pull request to merge into `main`. Branch protection
  must be configured on GitHub separately; this file does not enforce it.
- Preserve existing uncommitted work. Do not commit, push, merge, or switch
  branches in a way that risks that work without the user's approval.

## Architecture and configuration

- Use `.robot` tasks and resource files for a readable lifecycle: initialize,
  get transaction data, process each transaction, and finish. Use Robot
  Framework Browser Library for browser interaction.
- Use Python for project-specific data validation, transformation,
  transaction outcomes, recovery decisions, and CSV export. Keep portal
  selectors and navigation separate from reusable business logic.
- Define clear inputs and outputs between Robot keywords and Python libraries.
  Do not assume Robot catches Python exception classes directly; use an
  explicit, testable outcome or error contract at that boundary.
- Select web elements using verified, stable identifiers: prefer accessible
  roles and names or intentional test IDs; scope to a meaningful container
  when needed. Use CSS or XPath when better identifiers are unavailable.
  Avoid screen coordinates, generated attributes, long structural paths, and
  positional selection unless necessary. Keep Browser's strict matching on
  and verify that selectors identify the intended element.
- Prefer CSV for transaction input, output, and non-secret settings when
  appropriate. Keep configuration centralized and validate required settings,
  types, and paths. Avoid hardcoding environment-specific URLs, credentials,
  and operational settings in automation logic.
- Keep credentials in environment variables or a suitable secret manager. A
  local `.env` may be used for development; keep it ignored and provide a
  `.env.example` containing placeholder values only when setup is implemented.
- Excel output is optional, not a v1 requirement. Add pandas or openpyxl only
  when the implemented work needs them.

## Reliability and security

- Explicitly distinguish business-rule failures from system failures.
  Record a business failure and do not retry it automatically. Retry only
  identified transient system failures, with bounded attempts and delays;
  stop and surface non-recoverable failures.
- Capture useful failure evidence, including screenshots when a browser is
  available. Configure and verify Browser Library's failure handling rather
  than assuming every failure is captured automatically. Restrict sensitive
  data in logs, screenshots, and reports.
- Design retry and restart behavior to avoid duplicate or inconsistent
  results. CSV files are not a distributed queue; do not claim durable or
  multi-worker recovery without an implementation and tests.
- Keep generated outputs, reports, screenshots, local secrets, and virtual
  environments out of version control. Ignore generated paths, not all CSV,
  Excel, or image files: sample data and test fixtures may be tracked.

## Testing and documentation

- Add focused pytest tests for Python behavior as it is implemented, including
  validation and failure paths. Test Robot workflows or integration boundaries
  where practical, and validate changes with the smallest relevant test set.
- Keep the README accurate about what is implemented. Add setup, configuration,
  architecture, and execution instructions as those capabilities become
  available; do not present planned features as completed.
- Never hide failures or report success for incomplete work. Make transaction
  outcomes and run-level failures visible.

## Suggested v1 roadmap

1. **Initialization:** Establish repository hygiene and the minimal project
   setup for the selected portal and date-range transactions.
2. **`feat/config-and-exceptions`:** Implement validated configuration,
   logging, and business/system failure types with focused tests.
3. **`feat/portal-scraper`:** Implement a readable Robot workflow for demo
   login, date entry, and statement downloads.
4. **`feat/data-processing`:** Validate date-range inputs and write results CSV.
5. **`feat/resilience-and-tests`:** Complete and verify transaction recovery,
   retries, screenshots, and end-to-end outcomes.
6. **Documentation:** Maintain setup and usage guidance throughout; finish
   architecture diagrams and examples as the implementation stabilizes.

Adjust branch boundaries and ordering as needed. Add tests alongside each
feature rather than postponing all testing to the resilience phase.
