# py-reframework

This project is a **practice automation**, inspired by UiPath's Robotic
Enterprise Framework (REFramework). It demonstrates a repeatable pattern:
take a list of items, process each one, and record what happened.

It combines three tools: **Robot Framework** organizes the steps and creates
execution reports; **Browser Library** opens and operates the website; and
**Python** reads the input list and settings, checks the dates and downloaded
files, and writes the results report. The input and results use CSV files,
which are simple text-based tables.

The goal is to make that pattern understandable to business teams and useful
as a starting point for future automations, with a developer adapting and
testing it for each new process. The pattern aims to reduce repetitive work
and make outcomes easier to review.

## What the demo does

```text
List of date ranges  -->  Practice website  -->  Downloaded statements
                                              + a results report
```

The bot signs in to the [practice website](https://hash-chandra.github.io/demowebapp/)
once during initialization. For each eligible row, it enters the dates,
clicks Apply Range, checks the selected range, downloads a text statement,
and clears the fields. If a date is missing, the website disables Apply
Range; the bot records a failure and moves on. The
**downloaded files are the main output**; a separate results report shows
which items succeeded or failed.

By default, the bot shows its browser so you can watch it work. It can also
run without showing the browser window, known as **headless mode**: it still
visits the website and downloads files. See
[setup and operation](docs/technical/setup-and-operation.md).

If an input is invalid, the bot records the problem and moves on. It retries
some specific temporary website errors, but stops for certain serious
technical problems or after three technical failures without an intervening
success. See [setup and operation](docs/technical/setup-and-operation.md)
for the exact rules.

## What this demo is and is not

- The website is a public practice site. Its sign-in is simulated, and its
  Banking page does not actually require sign-in.
- The downloaded statement contains the selected dates and placeholder
  text, **not real banking transactions or structured business records**.
- The bot does not yet process invoices, purchase orders, employee records,
  or other real business data. Those are possible future adaptations.
- It cannot resume an interrupted batch automatically. Rerunning can
  download an item again, even if an earlier run succeeded.
- The bot is started from PowerShell. A simple launcher is being considered
  as a future improvement, but it has not been implemented.

Use only the site's public demo credentials and fictional sample data. Do
not enter real passwords or personal information on the practice site.

## Where this pattern could help

Instead of dates, an item might be an invoice number, purchase order number,
shipment tracking number, or support case ID. An operations team might use a
similar pattern to review a list of requests, with appropriate privacy controls.

These are **examples, not existing features**. A new process needs its own
requirements, permitted access, validation, portal actions, and tests; changing
a field name alone is not enough.

## Explore the project

| Reader | Guide | What it explains |
| --- | --- | --- |
| Business and operations teams | [Business use cases](docs/general/use-cases.md) | Examples, outputs, and human decisions. |
| Developers and technical reviewers | [Architecture](docs/technical/architecture.md) | The lifecycle, components, file map, and current limits. |
| Operators and developers | [Setup and operation](docs/technical/setup-and-operation.md) | Installation, sample input, commands, results, and troubleshooting. |
| Developers adapting the bot | [Adaptation guide](docs/technical/adaptation-guide.md) | How an invoice or purchase order solution could differ. |

This repository is a proof of concept, not a production-ready automation
platform. A person should review the process, permissions, security, and test
results before using an adaptation with real data.
