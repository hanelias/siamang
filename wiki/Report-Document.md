# Report Document

`Report` composes narrative prose, [[Reporting Tables|Reporting-Tables]], and
[[Reporting Charts|Reporting-Charts]] into a single document you can export to
Markdown or HTML. It is a thin orchestrator: tables already know how to render
themselves (`to_markdown()`), and charts already know how to save themselves
(`save()`) — `Report` stitches them together in order and links the generated
assets.

```python
from siamang.reporting import Report   # also: from siamang import Report
```

Every builder method returns `self`, so calls chain fluently; `save()` (or
`to_markdown`/`to_html`) is the terminal step.

---

## Constructor

```python
Report(title: str | None = None, description: str | None = None)
```

`title` becomes a top-level `# H1`; `description` is rendered in italics beneath
it. Both are optional.

---

## Narrative methods

Each appends a block and returns `self`.

| Method | Renders as |
| :--- | :--- |
| `heading(text, level=2)` | `## text` (level controls the `#` count). |
| `markdown(md)` | Raw Markdown, verbatim. |
| `text(md)` | Alias for `markdown`. |
| `note(md)` | `> **Note:** md` (a blockquote callout). |
| `value(label, value)` | `**label:** value` (an inline key figure). |
| `divider()` | `---` (horizontal rule). |

---

## Inserts

### `add`

```python
def add(self, component: object, *, caption: str | None = None) -> Report: ...
```

Inserts a `SurveyTable` (any [[Reporting Tables|Reporting-Tables]] type), a
`SurveyChart` (any [[Reporting Charts|Reporting-Charts]] type), or a raw
`pandas.DataFrame`. The optional `caption` is rendered in italics above tables
and as both the image alt-text and an italic caption beneath charts. Any other
type raises `TypeError`.

### `image`

```python
def image(self, path: str | Path, *, caption: str | None = None) -> Report: ...
```

Inserts an existing image file by path (useful for figures produced outside
siamang).

---

## Exporting

### `to_markdown`

```python
def to_markdown(self, asset_dir: str | Path = ".", *, embed_images: bool = False) -> str: ...
```

Renders the whole document to a Markdown string. Charts are materialized to PNG
files named `fig_<index>.png`:

- with `embed_images=False` (default), each chart is written into `asset_dir`
  and linked by relative filename;
- with `embed_images=True`, each chart is encoded inline as a `data:` URI (no
  files written).

### `to_html`

```python
def to_html(self) -> str: ...
```

Renders to HTML (via the `markdown` library with the `tables` extension), always
embedding images inline. Requires the `markdown` package.

### `save`

```python
def save(self, path: str | Path) -> Path: ...
```

Writes the document, choosing the format from the file suffix: `.md`/`.markdown`
(or no suffix) → Markdown with `asset_dir` set to the file's parent; `.html`/`.htm`
→ HTML. A `.pdf` suffix raises `NotImplementedError`; any other suffix raises
`ValueError`. Parent directories are created automatically.

---

## Fluent example: narrative + table + chart

The example assumes the simulated `data` from [[Analysis]] (n=200, seed=123).

```python
from siamang.reporting import Report

report = (
    Report(title="Remote Work & Autonomy", description="Pilot wave, Q2 2026")
    .heading("Overview")
    .text("Perceived autonomy was measured on a 5-point scale.")
    .value("Respondents", len(data.frame))
    .add(data.report.means("autonomy", by="remote_freq"), caption="Table 1. Mean autonomy by remote frequency")
    .add(data.plot.bar("autonomy", by="remote_freq"), caption="Figure 1. Mean autonomy by remote frequency")
    .note("Non-consenting respondents were excluded from the base.")
    .divider()
)

# Write report.md plus fig_*.png into ./out/
report.save("out/autonomy_report.md")
```

The Markdown begins:

```text
# Remote Work & Autonomy

*Pilot wave, Q2 2026*

## Overview

Perceived autonomy was measured on a 5-point scale.

**Respondents:** 200

*Table 1. Mean autonomy by remote frequency*

| Remote Frequency | Mean | SD | Median | N |
|---|---|---|---|---|
| Never | 3.222 | 1.38 | 4.0 | 45 |
...

> **Note:** Non-consenting respondents were excluded from the base.
```

---

## Combining reports: `Report.combine`

```python
@classmethod
def combine(cls, reports: list[Report], *, title: str, toc: bool = True) -> Report: ...
```

Merges several `Report` objects into one document. Each source report's `title`
becomes a `## H2` section heading (its `description` rendered in italics below),
and its blocks are appended in order. With `toc=True` (default), a **Contents**
list of anchor links to each section is inserted at the top. This is ideal for a
"run-all" report that concatenates per-analysis sections.

```python
cleaning = Report(title="Data Cleaning", description="prep").text("49 cases dropped.")
tables   = Report(title="Final Tables").add(data.report.freq("it_role"))

full = Report.combine([cleaning, tables], title="Full Report")
md = full.to_markdown()
# "# Full Report"
# "## Contents"  ->  "- [Data Cleaning](#data-cleaning)" / "- [Final Tables](#final-tables)"
# "## Data Cleaning" ... "## Final Tables" ...
```

Section anchors are slugified from the title (lowercased, non-alphanumerics → `-`),
so `"Data Cleaning"` links to `#data-cleaning`.

---

See also: [[Reporting Tables|Reporting-Tables]] · [[Reporting Charts|Reporting-Charts]] · [[Working with Data|Working-with-Data]] · [[Tutorial Full Pipeline|Tutorial-Full-Pipeline]]
