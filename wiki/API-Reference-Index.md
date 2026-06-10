# API Reference Index

A manual index of siamang's public API. Everything listed here is importable from
the top-level `siamang` package (e.g. `import siamang as sg`); the canonical
sub-package import path is shown alongside each symbol. Use this as a navigational
hub — each row links to the wiki page that documents the symbol in depth.

```python
import siamang as sg

sg.__version__        # the installed version (e.g. "0.5.0")
```

The package is organised into seven layers: **core** (survey definition),
**data** (the dataset and its tables), **reporting** (declarative tables and
charts), **frontend** (compilation and theming), **deploy** (publishing),
**io** (file formats), and **config** (settings).

---

## Core — `siamang.core`

Survey definition: variables, question types, structure, logic, and validation.
Re-exported at the top level. Documented in
[[Core Concepts|Core-Concepts]], [[Question Types|Question-Types]],
[[Pages Blocks and Structure|Pages-Blocks-and-Structure]],
[[Visibility and Branching|Visibility-and-Branching]], [[Quotas]], and [[Scripts]].

### Variables and measurement

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `Variable` | `from siamang import Variable` | A measured variable: name, scale, labels, valid range. | [[Variables and Measurement\|Variables-and-Measurement]] |
| `VariableMap` | `from siamang import VariableMap` | An ordered collection of variables — a survey's codebook. | [[Variables and Measurement\|Variables-and-Measurement]] |
| `VarRef` | `from siamang import VarRef` | A reference to a variable, used when building expressions. | [[Variables and Measurement\|Variables-and-Measurement]] |
| `MissingValue` | `from siamang import MissingValue` | A declared missing-value code and its kind. | [[Variables and Measurement\|Variables-and-Measurement]] |
| `Option` | `from siamang import Option` | A single choice option, with optional `show_if`/`hide_if`/`media`. | [[Question Types\|Question-Types]] |
| `Media` | `from siamang import Media` | An image/audio/video attachment for a question or option. | [[Question Types\|Question-Types]] |

### Question types

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `Question` | `from siamang import Question` | Abstract base for all question types. | [[Question Types\|Question-Types]] |
| `SingleChoice` | `from siamang import SingleChoice` | Pick one option (radio / dropdown / buttons). | [[Question Types\|Question-Types]] |
| `MultiChoice` | `from siamang import MultiChoice` | Pick several options, with min/max/exclusive rules. | [[Question Types\|Question-Types]] |
| `LikertScale` | `from siamang import LikertScale` | An N-point agreement/rating scale. | [[Question Types\|Question-Types]] |
| `NumericInput` | `from siamang import NumericInput` | A numeric entry field. | [[Question Types\|Question-Types]] |
| `OpenText` | `from siamang import OpenText` | Free text, single- or multi-line. | [[Question Types\|Question-Types]] |
| `Matrix` | `from siamang import Matrix` | A grid of sub-questions sharing a response scale. | [[Question Types\|Question-Types]] |
| `Ranking` | `from siamang import Ranking` | Order a set of items by preference. | [[Question Types\|Question-Types]] |

### Structure

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `Questionnaire` | `from siamang import Questionnaire` | The top-level survey: pages, variables, scripts, deadline. | [[Pages Blocks and Structure\|Pages-Blocks-and-Structure]] |
| `Page` | `from siamang import Page` | A page of items, with optional `show_if`/`hide_if`/`next_if`. | [[Pages Blocks and Structure\|Pages-Blocks-and-Structure]] |
| `Block` | `from siamang import Block` | A group of items within a page. | [[Pages Blocks and Structure\|Pages-Blocks-and-Structure]] |

### Logic, quotas, and scripts

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `Expression` | `from siamang import Expression` | A typed visibility/branching predicate. | [[Visibility and Branching\|Visibility-and-Branching]] |
| `compare` | `from siamang import compare` | Build a comparison expression (`compare(var, op, value)`). | [[Visibility and Branching\|Visibility-and-Branching]] |
| `AND` / `OR` / `NOT` | `from siamang import AND, OR, NOT` | Combine expressions into composite conditions. | [[Visibility and Branching\|Visibility-and-Branching]] |
| `FilterRule` | `from siamang import FilterRule` | A reusable show/hide rule. | [[Visibility and Branching\|Visibility-and-Branching]] |
| `Quota` | `from siamang import Quota` | A cap on responses for a variable value. | [[Quotas]] |
| `Script` | `from siamang import Script` | Inline JavaScript bound to a lifecycle trigger. | [[Scripts]] |

### Validation

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `ValidationIssue` | `from siamang import ValidationIssue` | A structural error raised by `validate()`. | [[Validation and Linting\|Validation-and-Linting]] |
| `LintWarning` | `from siamang import LintWarning` | A lint finding (code, severity, message, location). | [[Validation and Linting\|Validation-and-Linting]] |

---

## Data — `siamang.data`

The dataset object and its derived tables. Documented in
[[Working with Data|Working-with-Data]], [[Analysis]], and [[Banner Tables|Banner-Tables]].

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `SurveyData` | `from siamang.data import SurveyData` | A frame plus variable metadata; entry point to `.report`, `.plot`, `.analysis`, `.tables`, and `.export`. | [[Working with Data\|Working-with-Data]] |
| `SurveyTables` | `from siamang.data import SurveyTables` | The `data.tables` accessor (banner and summary tables). | [[Banner Tables\|Banner-Tables]] |
| `BannerTable` | `from siamang.data import BannerTable` | A cross-break banner table with Excel/CSV export. | [[Banner Tables\|Banner-Tables]] |

> `SurveyData` is also re-exported at the top level, so `from siamang import SurveyData`
> and `from siamang.data import SurveyData` both work.

---

## Reporting — `siamang.reporting`

Declarative, label-aware tables and charts. Documented in
[[Reporting Tables|Reporting-Tables]], [[Reporting Charts|Reporting-Charts]], and
[[Report Document|Report-Document]].

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `FreqTable` | `from siamang import FreqTable` | A frequency distribution with labels and percentages. | [[Reporting Tables\|Reporting-Tables]] |
| `CrossTable` | `from siamang import CrossTable` | A contingency table with Chi-square / Cramér's V. | [[Reporting Tables\|Reporting-Tables]] |
| `GroupMeanTable` | `from siamang import GroupMeanTable` | Group means with automatic test selection. | [[Reporting Tables\|Reporting-Tables]] |
| `BarChart` | `from siamang import BarChart` | A bar chart of counts or grouped means. | [[Reporting Charts\|Reporting-Charts]] |
| `BoxPlot` | `from siamang import BoxPlot` | Distribution comparison by group. | [[Reporting Charts\|Reporting-Charts]] |
| `HeatMap` | `from siamang import HeatMap` | Group means or a correlation matrix as a heatmap. | [[Reporting Charts\|Reporting-Charts]] |
| `ScatterPlot` | `from siamang import ScatterPlot` | A scatter plot with optional hue. | [[Reporting Charts\|Reporting-Charts]] |
| `Report` | `from siamang import Report` | A composable document of tables and charts. | [[Report Document\|Report-Document]] |

These objects are usually produced via the `data.report.*` and `data.plot.*`
accessors rather than constructed directly.

---

## Frontend — `siamang.frontend`

Compilation of a questionnaire into a deployable bundle, plus the theme system.
Documented in [[Frontend and Theming|Frontend-and-Theming]].

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `UIConfig` | `from siamang import UIConfig` | The visual design system (~66 fields). | [[Frontend and Theming\|Frontend-and-Theming]] |
| `get_preset` | `from siamang import get_preset` | Return a configured `UIConfig` for a named preset. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `FrontendBuilder` | `from siamang.frontend import FrontendBuilder` | Assembles a `SurveyBundle` from schema + runtime + theme + client. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `SurveySchema` | `from siamang.frontend import SurveySchema` | Platform-agnostic compiled survey IR. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `SurveyBundle` | `from siamang.frontend import SurveyBundle` | The compiled files (HTML/CSS/JS) ready to deploy. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `SurveyJSRuntime` | `from siamang.frontend import SurveyJSRuntime` | The default, build-free SurveyJS runtime. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `ReactRuntime` | `from siamang.frontend import ReactRuntime` | A standalone React 18 + Tailwind runtime. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `LocalClientTemplate` | `from siamang.frontend import LocalClientTemplate` | `env.js` for the local backend. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `SupabaseClientTemplate` | `from siamang.frontend import SupabaseClientTemplate` | `env.js` for the Supabase backend. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `ClientEnv` | `from siamang.frontend import ClientEnv` | Frontend-safe config handed to the in-bundle client. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `compile_questionnaire` | `from siamang.frontend import compile_questionnaire` | Compile a `Questionnaire` into a `SurveySchema`. | [[Frontend and Theming\|Frontend-and-Theming]] |
| `compile_css` | `from siamang.frontend import compile_css` | Compile a `UIConfig` into a CSS string. | [[Frontend and Theming\|Frontend-and-Theming]] |

`UIConfig` and `get_preset` are re-exported at the top level (from
`siamang.frontend.theme`); the rest are imported from `siamang.frontend`.

---

## Deploy — `siamang.deploy`

Publishing a survey to a backend/frontend pair. Documented in [[Deployment]].

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `DeployResult` | `from siamang import DeployResult` | The result of `survey.deploy(...)`; carries the URL and `.collect()`. | [[Deployment]] |
| `DeployPipeline` | `from siamang.deploy import DeployPipeline` | The compile → provision → build → publish orchestrator. | [[Deployment]] |
| `BackendConfig` | `from siamang.deploy import BackendConfig` | Backend provisioning result; splits frontend-safe vs. secret config. | [[Deployment]] |
| `BackendAdapter` | `from siamang.deploy import BackendAdapter` | Abstract base for storage backends. | [[Deployment]] |
| `FrontendAdapter` | `from siamang.deploy import FrontendAdapter` | Abstract base for hosting frontends. | [[Deployment]] |
| `backend_factory` | `from siamang.deploy import backend_factory` | Resolve a backend class by name. | [[Deployment]] |
| `frontend_factory` | `from siamang.deploy import frontend_factory` | Resolve a frontend class by name. | [[Deployment]] |
| `list_backends` | `from siamang.deploy import list_backends` | List registered backend names. | [[Deployment]] |
| `list_frontends` | `from siamang.deploy import list_frontends` | List registered frontend names. | [[Deployment]] |

`DeployResult` is the only deploy symbol re-exported at the top level; the rest come
from `siamang.deploy`.

---

## I/O — `siamang.io`

Readers and writers for the common research formats. Documented in
[[Data Import and Export|Data-Import-and-Export]].

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `SurveyDataReader` | `from siamang.io import SurveyDataReader` | Auto-detect reader that dispatches by file extension. | [[Data Import and Export\|Data-Import-and-Export]] |
| `CSVReader` / `CSVWriter` | `from siamang.io import CSVReader, CSVWriter` | CSV I/O (data only). | [[Data Import and Export\|Data-Import-and-Export]] |
| `ExcelReader` / `ExcelWriter` | `from siamang.io import ExcelReader, ExcelWriter` | Excel `.xlsx`/`.xls` I/O (data only). | [[Data Import and Export\|Data-Import-and-Export]] |
| `SPSSReader` / `SPSSWriter` | `from siamang.io import SPSSReader, SPSSWriter` | SPSS `.sav` I/O with full metadata. | [[Data Import and Export\|Data-Import-and-Export]] |
| `read_spss` | `from siamang.io import read_spss` | Convenience for `SPSSReader().read(...)`. | [[Data Import and Export\|Data-Import-and-Export]] |
| `StataReader` / `StataWriter` | `from siamang.io import StataReader, StataWriter` | Stata `.dta` I/O with full metadata. | [[Data Import and Export\|Data-Import-and-Export]] |
| `read_stata` | `from siamang.io import read_stata` | Convenience for `StataReader().read(...)`. | [[Data Import and Export\|Data-Import-and-Export]] |
| `RScriptWriter` | `from siamang.io import RScriptWriter` | Write a CSV + dictionary + `load_data.R` bundle. | [[Data Import and Export\|Data-Import-and-Export]] |
| `DictionaryReader` / `DictionaryWriter` | `from siamang.io import DictionaryReader, DictionaryWriter` | Read/write a `VariableMap` codebook as JSON. | [[Data Import and Export\|Data-Import-and-Export]] |

All I/O symbols are also re-exported at the top level (`from siamang import
read_spss`, etc.).

---

## Config — `siamang.config`

Loading, saving, and overriding `~/.siamang.toml`. Documented in [[Configuration]].

| Symbol | Import | Description | Docs |
| :--- | :--- | :--- | :--- |
| `Config` | `from siamang.config import Config` | In-memory `~/.siamang.toml`: defaults, backends, frontends, profiles. | [[Configuration]] |
| `load` | `from siamang.config import load` | Load and activate a config file (applies env overrides). | [[Configuration]] |
| `save` | `from siamang.config import save` | Write a config to disk (`chmod 600`). | [[Configuration]] |
| `use_profile` | `from siamang.config import use_profile` | Activate a named profile. | [[Configuration]] |
| `current` | `from siamang.config import current` | The currently active config. | [[Configuration]] |
| `check_permissions` | `from siamang.config import check_permissions` | Warn if a config file is group/world-readable. | [[Configuration]] |
| `ConfigError` | `from siamang.config import ConfigError` | Raised on invalid payloads or missing fields. | [[Configuration]] |

The `siamang.config` symbols are not re-exported at the top level.

---

See also: [[Home]] · [[Quickstart]] · [[Tutorial Full Pipeline|Tutorial-Full-Pipeline]] ·
[[Cookbook]] · [[Contributing]]
