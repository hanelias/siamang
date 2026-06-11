# siamang Cloud — Overview

**siamang Cloud** is the hosted home for your surveys. You author a survey as
code, keep it in a project on the platform, and from your browser you deploy it
to a public link, collect responses, run analysis, read dashboards and reports,
and manage your team and plan — all in one place.

## The core idea

Your survey is **code in a hosted project**. Each project is backed by Git, so
the questionnaire, its logic, and your analysis scripts are versioned the way
software is: every change is a commit you can review, and nothing about a study
gets lost between tools.

You bring the survey (written with the `siamang` library); siamang Cloud runs
everything around it:

- **Publishes** your survey to a live, public URL that respondents open in a
  browser — no account needed for them.
- **Collects** responses into managed storage you can browse and export.
- **Validates** your code automatically on every commit and shows a pass/fail
  status, so a broken survey never goes live by accident.
- **Runs analysis** scripts on the collected data and keeps a history of every
  run and its output.
- **Shows dashboards** (frequencies, crosstabs, a respondent summary) for quick
  looks, and **generates reports** (Markdown / HTML) for sharing.
- **Manages your team** (invite people, assign roles) and your **plan**.

You never wire up servers, databases, or hosting. You write the survey and the
analysis; the platform does the rest.

## How it relates to the library

The wiki has two parts. The **library** (`siamang`) is the Python package you
use to write a survey — variables, question types, pages, logic, reports. siamang
**Cloud** is the platform that hosts and runs what you wrote.

You can do everything on your own laptop with the library alone. The Cloud adds
the parts that are awkward to run yourself: a public survey host, managed
response storage, automatic validation on every push, hosted analysis runs with
history, and team collaboration.

| What you want to do | In the library | In the Cloud |
| :--- | :--- | :--- |
| Write the survey | A Python module | The same module, in your project's repo |
| Check it is valid | `siamang validate` on your machine | Automatic on every commit, with a status badge |
| Put it online | Deploy to your own backend | One click → a hosted survey URL |
| Store responses | Local file / your own database | Managed storage you browse and export |
| Analyze data | Run scripts locally | Hosted runs, schedules, run history, reports |
| Work as a team | Files you pass around | Organizations, roles, shared projects |

New to writing surveys as code? Start with [[Core Concepts|Core-Concepts]] and
the [[Quickstart]] on the library side, then come back here.

## What you can do

- Create an **organization** (your workspace) and **projects** inside it.
- Start from a ready-made **example study** or an empty project — either way a
  repo and a database are set up for you.
- Edit your questionnaire in an **in-browser code editor**, or clone the repo and
  push from your own machine.
- **Deploy** a survey to an environment (e.g. a small pilot, then the main run)
  and share its public URL.
- Watch responses arrive in the **Database** and on the **Dashboard**.
- **Export** your data to CSV, Excel, SPSS, Parquet, or SQLite.
- Commit **analysis scripts**, run them, and open the generated **reports**.
- Invite **teammates**, set their roles, and pick the **plan** that fits.

## Next steps

- [[Cloud Quick Start|Cloud-Quick-Start]] — sign in and get your first survey
  live, end to end.
- [[Using the Web App|Cloud-Web-App]] — a tour of every screen.
- [[Analysis & Reports|Cloud-Analysis-and-Reporting]] — dashboards, analysis
  runs, and reports.
- [[Plans & Billing|Cloud-Subscription-Tiers]] — what each plan includes.

## See also

[[Cloud Quick Start|Cloud-Quick-Start]] · [[Using the Web App|Cloud-Web-App]] · [[Core Concepts|Core-Concepts]] · [[Quickstart]]
