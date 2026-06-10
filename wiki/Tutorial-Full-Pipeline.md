# Tutorial: Full Pipeline

This tutorial walks through the worked example in
[`examples/full_pipeline/`](https://github.com/hanelias/siamang/tree/main/examples/full_pipeline)
end to end: define variables, assemble a multi-page questionnaire with conditional
routing, simulate respondents, run tables and charts, and export the results. It
mirrors the `full_pipeline_demo.ipynb` notebook, which ships with every output saved
inline.

The example folder contains:

| File | What it is |
| :--- | :--- |
| `full_pipeline_demo.ipynb` | The notebook this tutorial follows, with all outputs. |
| `survey_preview.html` | A standalone SurveyJS render — open it in a browser to experience the survey. |

Running the notebook also produces local artifacts (a `survey_responses.db` SQLite
store, figure PNGs, a banner XLSX); these are git-ignored, so they are not shipped
in the folder.

---

## The research scenario

**Topic:** how digital monitoring and algorithmic management affect job satisfaction
and perceived autonomy among IT professionals working remotely.

**Hypotheses.** (1) *The autonomy–surveillance paradox*: remote work raises
subjective autonomy but invites invasive tracking (keystroke logging, webcam
monitoring), which depresses satisfaction. (2) *Professional stratification*:
different IT roles experience different levels of remote flexibility and monitoring
pressure.

This drives a survey with a consent gate, demographics, a remote-work measure, a
surveillance-acceptance matrix, and two outcome scales.

---

## 1. Define the 12 variables

Each `Variable` declares a measurement `scale`, a human `label`, and (for
categorical items) value `labels`. Numeric variables add a `dtype` and a
`valid_range`. See [[Variables and Measurement|Variables-and-Measurement]].

```python
import siamang
from siamang import (
    AND, LikertScale, Matrix, NumericInput, OpenText,
    Page, Questionnaire, SingleChoice, Variable, VariableMap,
)

# Consent
consent = Variable("consent", scale="nominal", label="Informed Consent",
                   labels={1: "Yes", 0: "No"})

# Demographics
age = Variable("age", scale="ratio", label="Age (years)", dtype="int", valid_range=(18, 75))
gender = Variable("gender", scale="nominal", label="Gender",
                  labels={1: "Male", 2: "Female", 3: "Non-binary"})
it_role = Variable("it_role", scale="nominal", label="IT Role",
                   labels={1: "Software Engineer", 2: "Data Scientist", 3: "DevOps / SRE",
                           4: "Product Manager", 5: "QA / Tester"})
experience = Variable("experience", scale="ratio", label="Years of Experience",
                      dtype="int", valid_range=(0, 50))

# Remote work
remote_freq = Variable("remote_freq", scale="ordinal", label="Remote Work Frequency",
                       labels={1: "Never (on-site)", 2: "1-2 days/week", 3: "Hybrid (3 days)",
                               4: "Mostly remote (4 days)", 5: "Fully remote"})

# Surveillance acceptance (three ordinal items, shown together as a matrix)
_agree = {1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"}
surv_keystroke = Variable("surv_keystroke", scale="ordinal",
                          label="Keystroke logging acceptance", labels=_agree)
surv_camera = Variable("surv_camera", scale="ordinal",
                       label="Webcam monitoring acceptance", labels=_agree)
surv_git = Variable("surv_git", scale="ordinal",
                    label="Git commit metrics acceptance", labels=_agree)

# Outcomes
satisfaction = Variable("satisfaction", scale="interval", label="Job Satisfaction",
                        labels={1: "Very low", 2: "Low", 3: "Neutral", 4: "High", 5: "Very high"})
autonomy = Variable("autonomy", scale="ordinal", label="Perceived Autonomy",
                    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"})
story = Variable("story", scale="nominal", label="Open-ended comment")
```

Collect them in a `VariableMap` — the survey's codebook:

```python
variables = VariableMap()
variables.add_many([
    consent, age, gender, it_role, experience, remote_freq,
    surv_keystroke, surv_camera, surv_git, satisfaction, autonomy, story,
])
print(f"Defined {len(variables)} variables")   # Defined 12 variables
```

Note the deliberate mix of scales: `nominal` (gender, role), `ordinal` (remote
frequency, surveillance, autonomy), `interval` (satisfaction), and `ratio` (age,
experience). The reporting layer uses these to pick the right statistical test
automatically.

---

## 2. Assemble 5 pages with `show_if`

Wrap each variable in a question, then group questions into pages. The question
types here are `SingleChoice` (with `display` styles: `buttons`, `radio`,
`dropdown`), `NumericInput`, `Matrix`, `LikertScale`, and `OpenText` — see
[[Question Types|Question-Types]].

```python
q_consent = SingleChoice("Do you consent to participate in this study?",
                         var=consent, required=True, display="buttons")
q_age = NumericInput("What is your age?", var=age)
q_gender = SingleChoice("What is your gender?", var=gender, display="radio")
q_role = SingleChoice("What is your primary IT role?", var=it_role, display="dropdown")
q_experience = NumericInput("Years of professional experience?", var=experience)
q_remote = SingleChoice("How often do you work remotely?", var=remote_freq, display="radio")

q_surveillance = Matrix(
    "To what extent do you accept the following monitoring practices?",
    var=[surv_keystroke, surv_camera, surv_git],
    subquestions=["Keystroke logging", "Webcam monitoring", "Git commit metrics"],
    column_labels=["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
)

q_satisfaction = LikertScale("How satisfied are you with your current job?",
                             var=satisfaction, points=5,
                             left_label="Very dissatisfied", right_label="Very satisfied")
q_autonomy = LikertScale("How much autonomy do you have in your daily work?",
                         var=autonomy, points=5, left_label="Very low", right_label="Very high")
q_story = OpenText("Any additional comments about your work experience?",
                   var=story, multiline=True, max_chars=500)
```

The routing lives on the pages. The consent gate is always shown; every later page
is hidden unless `consent == 1`, and the surveillance matrix additionally requires
`remote_freq >= 2` (no point asking on-site staff about remote monitoring). The
typed expressions `consent.eq(1)`, `remote_freq.ge(2)`, and `AND(...)` come from the
Expression DSL — see [[Visibility and Branching|Visibility-and-Branching]].

```python
page_consent = Page(name="consent", title="Informed Consent", items=[q_consent])
page_demo = Page(name="demographics", title="Demographics",
                 items=[q_age, q_gender, q_role, q_experience], show_if=consent.eq(1))
page_remote = Page(name="remote", title="Remote Work",
                   items=[q_remote], show_if=consent.eq(1))
page_surveillance = Page(name="surveillance", title="Workplace Monitoring",
                         items=[q_surveillance], show_if=AND(consent.eq(1), remote_freq.ge(2)))
page_outcomes = Page(name="outcomes", title="Work Outcomes",
                     items=[q_satisfaction, q_autonomy, q_story], show_if=consent.eq(1))

survey = Questionnaire(
    title="Remote Work, Autonomy & Digital Surveillance",
    pages=[page_consent, page_demo, page_remote, page_surveillance, page_outcomes],
    variables=variables,
)
print(f"Pages: {len(survey.pages)}")   # Pages: 5
```

To experience the result, open `survey_preview.html` in a browser — it is the
SurveyJS render of this exact questionnaire, complete with the conditional logic,
validation, and progress bar. See [[Frontend and Theming|Frontend-and-Theming]] for
how that HTML is produced.

---

## 3. Simulate 250+ respondents

`simulate(n, seed)` generates synthetic data that respects every visibility rule:
when `consent=0`, all later variables are `NaN`; when `remote_freq=1`, the
surveillance items are `NaN`. The shipped database holds 250 responses; the notebook
runs 300.

```python
data = survey.simulate(n=300, seed=42)
print(data.frame.shape)              # (300, 12)
data.frame.head(10)
```

`simulate()` returns a [`SurveyData`](Working-with-Data) carrying both the frame and
the variable metadata. A quick overview:

```python
desc = data.describe_variables()     # one row per variable: scale, n, missing, range/levels
```

See [[Simulation]] for the sampling rules in detail.

---

## 4. Frequency tables

The declarative reporting API lives on `data.report.*` and returns rich table
objects with `.to_markdown()`, `.to_frame()`, and `.to_html()`. Labels are applied
automatically from the variable metadata. See [[Reporting Tables|Reporting-Tables]].

```python
print(data.report.freq("it_role").to_markdown())

# sort categories by descending count
print(data.report.freq("remote_freq", sort="freq").to_markdown())
```

---

## 5. Cross-tabulation with a Chi-square test

`crosstab(row, col)` builds a contingency table and, because both variables are
categorical, runs a Chi-square test and Cramér's V automatically. `pct="row"`
switches the cells to row percentages.

```python
print(data.report.crosstab("it_role", "remote_freq").to_markdown())              # counts
print(data.report.crosstab("it_role", "remote_freq", pct="row").to_markdown())   # row %
```

---

## 6. Grouped means with automatic test selection

`means(target, by=group)` reports the mean of `target` within each group and selects
the test from the target's measurement scale: an **ordinal** outcome
(`autonomy`) gets a Kruskal–Wallis test, while an **interval** outcome
(`satisfaction`) gets an ANOVA. This is exactly where the scales defined in step 1
pay off.

```python
print(data.report.means("autonomy", by="remote_freq").to_markdown())       # Kruskal-Wallis
print(data.report.means("satisfaction", by="remote_freq").to_markdown())   # ANOVA
```

---

## 7. Charts

The `data.plot.*` accessor mirrors the reporting tables and returns chart objects;
call `.plot()` to render (in a notebook) or `.save("name.png")` to write a file.
Charts require the optional `charts` extra (`pip install "siamang[charts]"`). See
[[Reporting Charts|Reporting-Charts]].

```python
data.plot.bar("it_role").plot()                          # category counts
data.plot.bar("autonomy", by="remote_freq").plot()       # grouped means

data.plot.boxplot("satisfaction", by="remote_freq",
                  title="Job Satisfaction by Remote Work Frequency").plot()
data.plot.boxplot("autonomy", by="gender", show_points=True).plot()

# surveillance acceptance heatmap; vmin/vmax pin the 1–5 colour scale
data.plot.heatmap(["surv_keystroke", "surv_camera", "surv_git"],
                  by="remote_freq", vmin=1, vmax=5,
                  title="Surveillance Acceptance by Remote Work Frequency").plot()

# Spearman correlation matrix across the ordinal/interval outcomes
data.plot.heatmap(["surv_keystroke", "surv_camera", "surv_git", "satisfaction", "autonomy"],
                  title="Spearman Correlation Matrix").plot()

data.plot.scatter("satisfaction", "autonomy", hue="remote_freq").plot()
```

The notebook saves `fig_outcomes_by_remote.png` and
`fig_surveillance_heatmap.png` from these calls.

---

## 8. Export

Every table renders to a DataFrame, Markdown, or HTML; banner tables export to
Excel. See [[Data Import and Export|Data-Import-and-Export]] for file-format I/O.

```python
xtab = data.report.crosstab("it_role", "remote_freq")
xtab.to_frame()        # pandas DataFrame
xtab.to_markdown()     # publication-ready Markdown
xtab.to_html()         # HTML fragment
```

A banner table (multiple row variables against multiple column variables) exports
straight to a publication-ready spreadsheet — the notebook writes
`banner_satisfaction_by_remote.xlsx`:

```python
banner = data.tables.banner(rows=["satisfaction", "autonomy"],
                            columns=["remote_freq", "gender"], labels=True)
banner.export_xlsx("banner_satisfaction_by_remote.xlsx")
```

See [[Banner Tables|Banner-Tables]].

---

## Where to go from here

- Deploy this survey for real: [[Deployment]] · [[CLI Reference|CLI-Reference]].
- Customise the look: [[Frontend and Theming|Frontend-and-Theming]].
- More recipes: [[Cookbook]].
- The full surface: [[API Reference Index|API-Reference-Index]].

---

See also: [[Quickstart]] · [[Simulation]] · [[Reporting Tables|Reporting-Tables]] ·
[[Reporting Charts|Reporting-Charts]] · [[Working with Data|Working-with-Data]]
