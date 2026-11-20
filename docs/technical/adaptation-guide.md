# Adapting the demo to another process

[Project overview](../../README.md) | [Architecture](architecture.md) |
[Setup and operation](setup-and-operation.md) |
[Business use cases](../general/use-cases.md)

This is a design guide for developers and process owners, not a feature
already implemented. The current bot handles date ranges and the demo site's
placeholder text statements. It does not retrieve invoices or purchase
orders, authenticate to an ERP, or extract structured business records.

## Example: downloading invoices

Suppose an authorized portal lets a user search for an invoice number and
download an invoice. A possible input might look like this:

```csv
transaction_id,invoice_number
item-001,INV-1001
item-002,INV-1002
```

These are fictional examples, not input supported by the current bot. The
desired primary output might be one invoice file per item; a separate report
could record the invoice number, outcome, attempts, file path, and error.
The actual schema and business rules must be agreed with the process owner.

The high-level pattern is recognizable:

```text
Current demo:   date-range row  ->  enter dates  ->  download text statement
Possible bot:   invoice row     ->  find invoice ->  download invoice file
Both:           validate item, record its outcome, and report the run
```

This is not just a selector rename. The new portal, input fields, business
rules, authentication, file checks, outputs, and recovery policy may all
need changes.

## Reuse and adaptation map

No project module is guaranteed to work unchanged for every solution. Reuse
must be verified for the target process and its effects on external systems.

| Component | Current role | Invoice or PO adaptation |
| --- | --- | --- |
| Robot Framework and Browser Library | Run keywords, browser actions, and execution reports. | The tools are reusable; dependencies or versions may need changes. |
| [Batch task](../../robot/tasks/process_transactions.robot) | Coordinates date-range rows, retry decisions, outcome recording, and cleanup. | Use the lifecycle as a starting point; adapt process steps and error/recovery decisions. It is not a generic transaction engine. |
| [Portal resource](../../robot/resources/demo_portal.resource) | Implements demo login, navigation, selectors, and downloads. | Replace or adapt authentication, navigation, search, selectors, and download actions for the authorized portal. |
| [Transaction handling](../../src/py_reframework/transactions.py) | Reads the date-range CSV and writes the demo results. | Change the input and result schemas, row validation, and identifiers. Keep or adapt CSV safety as appropriate. |
| [Portal support](../../src/py_reframework/portal_support.py) | Validates dates, checks credentials, creates paths, and verifies demo text. | Replace date and statement-specific checks with invoice or PO rules and output verification. Review path and credential handling. |
| [Configuration loader](../../src/py_reframework/config.py) and [settings](../../config/settings.csv) | Validate this bot's URL, paths, and operational settings. | Update values and adapt the schema and validation for the new process. |
| [Failure types](../../src/py_reframework/exceptions.py) | Define business and system failure categories. | Use the categories as a starting point, but classify and handle the new process's failures explicitly. |
| [Tests](../../tests/) | Check settings, Python behavior, selectors, and the demo workflow with a local mock. | Adapt fixtures and add tests for the new portal, rules, failures, and output. |

For example, an invoice that does not exist might be a business failure if
the process owner agrees. An unavailable portal might be a system failure.
Do not assume every timeout is temporary or every failed lookup means the
invoice is missing.

## Decisions before implementation

1. **Define the item and outcome.** Agree on invoice or PO identifiers,
   duplicates, required fields, expected files or data, and who reviews
   failures. Decide what to do when a record is absent or ambiguous.
2. **Confirm access and security.** Use an authorized environment and
   account. Review login requirements, including any multi-factor
   authentication, credential storage, permissions, and sensitive data in
   downloads, screenshots, and reports. The demo's simulated login is not
   evidence that a real portal will work the same way.
3. **Map the portal.** Verify navigation and stable selectors on the target
   application. The current demo opens Banking through its UI; a different
   site may have a different workflow.
4. **Validate the output.** Agree how to identify a successful download or
   valid extracted record. A text statement date check cannot verify a PDF,
   spreadsheet, or invoice detail page.
5. **Design recovery for the action.** The current batch retries only
   initial-page HTTP 502, 503, and 504 responses, with a bounded delay; it
   stops after three consecutive system failures. Decide which failures are
   retryable in the new process and whether retries or reruns can create
   duplicate downloads or duplicate changes. There is no durable resume or
   cross-run deduplication in the current bot.
6. **Test before use.** Test successful and missing items, bad input,
   authentication failures, safe retries, interruptions, output checks,
   reporting, and sensitive-data handling. Use fictional data and a local
   mock or permitted test environment where practical.

For a **PO status lookup**, the primary output may be a table of statuses
rather than downloaded files. For an **invoice data extraction** bot, the
output schema and extraction logic also need to be designed; collecting
structured data or writing Excel is not implemented here. Add dependencies
such as pandas or openpyxl only if the new solution needs them.

## Working with an AI assistant

An AI assistant can help identify affected components, draft changes, and
create tests. A person should provide non-sensitive requirements and review
the proposed access, selectors, classification, output checks, security,
and results. Never share credentials, real personal information, or
confidential business data with an AI tool.
