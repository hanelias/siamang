# Your First Project

A **project** is one study: its survey code, its responses, and its analysis, all
in one place. Creating a project sets up a **Git repository** and a **database**
for you automatically — you do not wire up anything yourself.

> New to writing surveys as code? Skim [[Core Concepts|Core-Concepts]] first; it
> explains the model you will see in the project's files.

## Start blank or from the example

When you create a project you choose how it starts:

- **Example study ("Work & Wellbeing")** — a complete, ready-to-run project: a full
  questionnaire (consent, screening, quotas, every question type, skip logic, a
  custom thank-you page), three analysis scripts, and about **300 sample responses**
  so the Database, Dashboard, and Analysis screens are alive immediately.
  **Pick this for your first project** — you can see the whole loop before writing
  anything.
- **Empty project** — a small starter survey you build out from scratch.

## Create a project

**What you'll need:** the **admin** or **owner** role. On the **Free** plan you can
have up to two projects.

**Steps**
1. Open **Projects**.
2. Click **New project**.
3. Enter a **name**, then choose **Example study** or **Empty project**.
4. Click **Create**.

**Result:** the project opens. If you reached your plan's project limit, the button
is disabled with a prompt to upgrade — see [[Plans & Billing|Cloud-Subscription-Tiers]].

## What gets created for you

Behind that one click, the platform provisions:

- a **Git repository** with a starter commit (your survey and scripts),
- a **database** that will hold this project's responses,
- automatic **validation** on every commit (a status dot by the project name), and
- the default branch **`main`**.

## What's in the repository

Open **Repository** to see the project's files:

| Path | What it is |
| :--- | :--- |
| `siamang.yaml` | The project's configuration: the survey entry point, deployment environments, and which analysis scripts to run. See [[Project Config (siamang.yaml)\|Cloud-siamang-yaml]]. |
| `survey/questionnaire.py` | The survey itself, written as Python. |
| `scripts/` | Analysis scripts (in the example: `cleaning.py`, `weights.py`, `tables.py`). |
| `outputs/` | Where analysis runs write tables and files. |
| `reports/` | Generated reports (Markdown / HTML). |
| `README.md` | The project's notes, shown on the Dashboard. |

## Take the example for a spin

If you started from the example study, you can run the whole pipeline right away:

1. **Repository** — open `survey/questionnaire.py` and read the survey as code.
2. **Deployments** — deploy the **pilot** environment and open the public link.
   See [[Deploying a Survey|Cloud-Deploying-a-Survey]].
3. **Database** / **Dashboard** — watch responses (next to the ~300 samples).
4. **Analysis** — click **Run all** and open the report.

The [[Cloud Quick Start|Cloud-Quick-Start]] walks this same loop end to end.

## See also

[[Repository & Editing|Cloud-Repository-and-Editing]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] · [[Deploying a Survey|Cloud-Deploying-a-Survey]] · [[Cloud Quick Start|Cloud-Quick-Start]]
