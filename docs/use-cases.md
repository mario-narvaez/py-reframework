# Business use cases

[Back to the project overview](../README.md)

This guide is for business and operations teams. It explains what the demo's
pattern could support; **none of the future examples below is implemented**.

## The pattern in plain language

1. A person or another system prepares a list of items to process.
2. The bot checks each item and carries out the agreed steps.
3. The bot produces the intended output and records the outcome.
4. A person reviews failures and decides what needs attention.

In the current demo, an item is a date range and the intended output is a
practice statement. A results report is separate from the downloaded files.
The practice website uses simulated sign-in, does not require sign-in for
Banking, and produces placeholder text, not real financial records.

In the technical guides, an individual item is called a **transaction**.
Here that means a row to process, not a financial transaction. A business
failure means an item did not meet an agreed rule; a system failure means
the automation encountered a technical problem. A retry is another attempt
after a problem.

## Possible future processes

| Item on the list | Example of a process | Possible primary output |
| --- | --- | --- |
| Invoice number | Find an invoice and download it or collect selected details. | Invoice file or a table of details. |
| Purchase order (PO) number | Find an order and check its status. | A list of order statuses. |
| Deduction or claim ID | Look up a claim and capture its details for review. | A claim review list. |
| Shipment or tracking number | Check where a delivery is in its journey. | A delivery status list. |
| Order number | Retrieve order details or check progress. | Order details or statuses. |
| Vendor ID | Look up a supplier record. | A list of selected supplier details. |
| Customer ID | Retrieve agreed customer information. | A list of selected customer details. |
| Support case number | Check a case's current status. | A case status report. |
| Request ID | Help an operations team review the status of requests. | A list of requests needing attention. |

The output depends on the business need: it might be a downloaded file, a
review list, or a table of information. A separate results report can help
people see what was processed and what needs attention.

## Example: from dates to invoices

Imagine an approved process with a list of fictional invoice numbers:
`INV-1001`, `INV-1002`, and `INV-1003`. The desired result could be one
invoice file per number, plus a report identifying missing invoices or
technical problems.

The *idea* resembles the demo: take one item, find it, perform an action,
and record the result. But the new website, invoice rules, file checks,
access permissions, and exception handling all need to be designed and
tested. This example does not run on the practice site.

## Decisions people still make

Before adapting a bot, the process owner and technical team should agree on:

- Which items are in scope, and what a successful result looks like.
- What to do when an item is missing, invalid, duplicated, or needs review.
- Whether a retry could create a duplicate or change business data.
- Who can access the application, outputs, logs, and screenshots.
- How sensitive information will be protected, retained, and disposed of.
- Who reviews failures and what to do when the process is interrupted.

Do not use real personal information on the demo site. For real processes
involving sensitive information, follow the organization's privacy, access,
and retention requirements before implementation.

An AI assistant can help draft a solution and tests, but a person must review
the requirements, permissions, behavior, security, and results. Do not share
secrets or sensitive business data with an AI tool.
