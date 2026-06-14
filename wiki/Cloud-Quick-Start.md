# Cloud Quick Start

This walkthrough takes you from signing in to a **live survey collecting
responses** — and your first analysis report — entirely in the web app. The
fastest path uses the built-in **example study**, so you can see the whole loop
before writing a line of your own.

If you are new to writing surveys as code, skim [[Core Concepts|Core-Concepts]]
first; it explains the model you will see in the project's files.

**What you'll need:** a siamang Cloud account and an organization (a personal one
is fine — see [[Organizations & Team|Cloud-Organizations-and-Team]]).

## 1. Sign in

Open siamang Cloud and sign in. After you sign in you land in your **workspace**.
The top bar shows your organization, a theme toggle, and your account menu.

## 2. Create an organization

An **organization** is your workspace; it owns your projects, your team, and your
plan. If you do not have one yet, click **Create organization** and give it a
name. A personal organization is fine for working solo — you can turn it into a
team later.

> One organization is enough to start. See [[Plans & Billing|Cloud-Subscription-Tiers]]
> for what each plan includes and how team roles work.

## 3. Create a project

Inside the organization, open **Projects** and click **New project**. You get two
choices:

- **Create example study** — seeds a complete **"Work & Wellbeing"** project: a
  full questionnaire (consent, screening, quotas, every question type, skip
  logic, a custom thank-you page), three analysis scripts, and about 300 sample
  responses so the data screens are alive immediately. **Pick this one** for your
  first run.
- **New project** — an empty project with a small starter survey, if you would
  rather start from scratch.

Either way the platform sets up a **Git-backed repository** and a **database** for
you automatically. Open the project to enter its workspace, where the left
sidebar lists Dashboard, Repository, Database, Deployments, Analysis, and more.

## 4. Review the survey in the repository

Open **Repository**. The file tree shows the project's files; open
`survey/questionnaire.py` to read the survey as code in the in-browser editor.
Other files worth a look:

- `siamang.yaml` — the project's configuration: where the survey lives, which
  deployment environments exist, and which analysis scripts to run (see
  [[Project Config (siamang.yaml)|Cloud-siamang-yaml]]).
- `scripts/` — the analysis scripts (cleaning, weighting, tables).

Try a small edit, then click **Save & commit** (or press Ctrl/Cmd+S), write a
short message, and commit. **Validation runs automatically on every commit** and
shows a pass/fail status: a green badge on the file when it is valid, or the
error count if something is wrong. A commit that fails validation tells you
exactly what to fix before anything goes live.

## 5. Deploy and get a public survey URL

Open **Deployments** and click **New deployment**. Choose an environment — the
example project comes with **pilot** (a small cap) and **main** — and deploy. The
platform compiles your latest commit and publishes the survey to an **isolated,
hosted environment**.

When the build finishes, the card shows a **public survey URL**. That link is
what you share with respondents — they open it in any browser and no account is
required.

> Want to click through the survey first without collecting real data? Use
> **Preview** on the Deployments screen. It builds a staging version you can fill
> in yourself; a preview does not accept real responses.

## 6. Open and fill the survey

Click the survey URL. Take the survey as a respondent would: answer the screening
questions, work through the pages, and submit. Submit it a few times to generate
some real responses alongside the sample data.

## 7. Watch responses appear

- **Database** — open it and select the `responses` table. Your submissions show
  up as rows (next to the ~300 seeded sample rows). You can filter, sort, page
  through the data, and **Export** it to CSV, Excel, SPSS (`.sav`), Parquet, or
  SQLite.
- **Dashboard** — the **Data insights** section charts your data live: response
  and respondent counts, responses per day, a **frequency** chart for any
  variable, and a two-way **crosstab**. These update as responses arrive.

On the live Deployment card you will also see a **monitor**: how many responses
have come in (and against the cap), quota progress, and the survey's codebook.

## 8. Run an analysis and open the report

Open **Analysis**. The **Scripts** list shows the analysis steps declared in
`siamang.yaml`. You can:

- Click **Run** on a single script, or
- Click **Run all** to run every analysis step in order (clean → weight →
  tabulate) and combine the results into one report.

Each run appears in **Run history** and finishes **completed** or **failed**.
Click a run to open its detail panel with **Logs** and **Outputs** tabs. The
**Outputs** tab links to anything the run produced — a **report**, new database
tables, and downloadable files.

Open the generated report (Markdown, with an **HTML** download available) to see
your tables and charts. Reports also appear under **Files** and can be opened
from the Repository.

## You did it

You signed in, created a project, deployed a live survey, collected responses,
and produced a report — without managing any servers. From here:

- [[Your First Project|Cloud-Your-First-Project]] — templates and project structure.
- [[Using the Web App|Cloud-Web-App]] — every screen, explained.
- [[Deploying a Survey|Cloud-Deploying-a-Survey]] — environments, preview, sharing,
  and monitoring fieldwork.
- [[Viewing & Exporting Data|Cloud-Viewing-and-Exporting-Data]] — browse responses
  and export your data.
- [[Organizations & Team|Cloud-Organizations-and-Team]] — invite teammates and set
  roles.
- [[Analysis & Reports|Cloud-Analysis-and-Reporting]] — dashboards, runs, and
  reports in depth.
- [[Analysis SDK|Cloud-Analysis-SDK]] — write your own analysis scripts.
- [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] — configure environments
  and tasks.
- [[FAQ & Troubleshooting|Cloud-FAQ-and-Troubleshooting]] — common questions and
  fixes.

## See also

[[siamang Cloud — Overview|Cloud-Overview]] · [[Using the Web App|Cloud-Web-App]] · [[Analysis & Reports|Cloud-Analysis-and-Reporting]] · [[Quickstart]]
