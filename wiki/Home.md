# siamang & siamang Cloud

**siamang** is a *research-as-code* framework for sociological surveys. You define
variables, questionnaires, and logic in **pure Python** — then validate, preview,
simulate, deploy, collect, and analyze, all from a single pipeline. No GUI builders,
no drag-and-drop, no lock-in: a survey is just a Python module you can version,
test, and reuse.

**siamang Cloud** is the managed platform built on the siamang engine: keep your
surveys as code in hosted projects, deploy them with one click, collect responses,
run analysis, and share reports — all from your browser.

> This wiki has **two parts**. Use the sidebar to navigate.
>
> - 📚 **Library** — the `siamang` Python package. Start at **[[Quickstart]]**.
> - ☁️ **siamang Cloud** — the hosted platform. Start at **[[Cloud Overview|Cloud-Overview]]**.

---

## Install & hello survey

```bash
pip install siamang
```

```python
from siamang.core import Variable, LikertScale, SingleChoice, Page, Questionnaire

satisfaction = Variable(
    "satisfaction", scale="ordinal", label="Overall satisfaction",
    labels={1: "Very dissatisfied", 2: "Dissatisfied",
            3: "Neutral", 4: "Satisfied", 5: "Very satisfied"},
)
remote_freq = Variable(
    "remote_freq", scale="ordinal", label="Remote work frequency",
    labels={1: "Never", 2: "1-2 days/week", 3: "3-4 days/week", 4: "Fully remote"},
)

survey = Questionnaire(
    title="Work Attitudes Study",
    pages=[Page("main", items=[
        LikertScale("How satisfied are you with your role?", var=satisfaction, points=5),
        SingleChoice("How often do you work remotely?", var=remote_freq),
    ])],
)

data = survey.simulate(n=200)                       # synthetic respondents
print(data.report.freq("satisfaction").to_markdown())  # publication-ready table
```

```bash
siamang validate my_survey.py
siamang preview  my_survey.py        # local preview at http://127.0.0.1:8000
siamang deploy   my_survey.py --backend supabase --frontend vercel
```

---

## Feature matrix

| Area | Capabilities |
| :--- | :--- |
| **Core** | Variables (nominal/ordinal/interval/ratio), 7 question types, pages & blocks, skip logic (`show_if`/`hide_if`), quotas, validation |
| **Reporting** | Declarative tables (`FreqTable`, `CrossTable`, `GroupMeanTable`) and charts (`BarChart`, `BoxPlot`, `HeatMap`, `ScatterPlot`) with automatic labels and statistical tests; composable `Report` documents |
| **Scripts** | Inline JavaScript for survey-side behaviour — 7 trigger points |
| **Frontend** | SurveyJS and React 18 runtimes, dark mode, auto-save, access codes, 6 theme presets |
| **Deploy** | Local SQLite, Supabase, Google Sheets backends; Local, Vercel, Netlify frontends |
| **Data I/O** | CSV, Excel, SPSS, Stata, R — SPSS/Stata round-trip labels and missing values; CSV/Excel carry data only (labels via the JSON dictionary) |
| **Cloud** | Hosted survey projects, one-click deploy, response collection, live dashboards, scheduled analysis, shareable reports, team roles and plans |

---

## 📚 Library — start here

| Page | What it covers |
| :--- | :--- |
| [[Installation]] | Install, extras (`charts`/`gsheets`/`dev`), requirements |
| [[Quickstart]] | Your first survey end to end |
| [[Core Concepts\|Core-Concepts]] | Research-as-code philosophy and the data model |
| [[Question Types\|Question-Types]] | All 7 question types with examples |
| [[Pages Blocks and Structure\|Pages-Blocks-and-Structure]] | Pages, page kinds, blocks, questionnaires |
| [[Visibility and Branching\|Visibility-and-Branching]] | The Expression DSL (`show_if`, `compare`, `AND`/`OR`) |
| [[Reporting Tables\|Reporting-Tables]] · [[Reporting Charts\|Reporting-Charts]] · [[Report Document\|Report-Document]] | Tables, charts, composable reports |
| [[Deployment]] · [[CLI Reference\|CLI-Reference]] | Backends/frontends and the command line |

See the full list in the sidebar, or the manual **[[API Reference Index\|API-Reference-Index]]**.

## ☁️ siamang Cloud — start here

| Page | What it covers |
| :--- | :--- |
| [[Cloud Overview\|Cloud-Overview]] | What the platform does and who it's for |
| [[Cloud Quick Start\|Cloud-Quick-Start]] | Create a project and deploy your first survey |
| [[Your First Project\|Cloud-Your-First-Project]] | Start from the example or an empty project |
| [[Organizations & Team\|Cloud-Organizations-and-Team]] | Workspaces, inviting people, and roles |
| [[Using the Web App\|Cloud-Web-App]] | The web interface, screen by screen |
| [[Deploying a Survey\|Cloud-Deploying-a-Survey]] | Publish a survey and share its public link |
| [[Viewing & Exporting Data\|Cloud-Viewing-and-Exporting-Data]] | Browse responses and export your data |
| [[Analysis & Reports\|Cloud-Analysis-and-Reporting]] | Run analysis, view reports and dashboards |
| [[Project Config (siamang.yaml)\|Cloud-siamang-yaml]] · [[Analysis SDK\|Cloud-Analysis-SDK]] | Configure projects and write analysis scripts |
| [[Plans & Billing\|Cloud-Subscription-Tiers]] | Plans, limits, and team roles |
| [[FAQ & Troubleshooting\|Cloud-FAQ-and-Troubleshooting]] | Common questions and fixes |

---

*This wiki lives in the [`wiki/`](https://github.com/hanelias/siamang/tree/main/wiki) folder
of the `siamang` repository and is published to the GitHub Wiki. To edit, change the
source files and re-run the sync script — see [`wiki/README.md`](https://github.com/hanelias/siamang/blob/main/wiki/README.md).*
