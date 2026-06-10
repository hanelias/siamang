# Data Import and Export

The `siamang.io` layer round-trips survey datasets between siamang's `SurveyData`
and the common research file formats — CSV, Excel, SPSS, Stata, and R — preserving
variable labels, value labels, missing-value codes and kinds, and column formats
wherever the format allows.

```python
from siamang.io import (
    SurveyDataReader,
    CSVReader, CSVWriter,
    ExcelReader, ExcelWriter,
    SPSSReader, SPSSWriter, read_spss,
    StataReader, StataWriter, read_stata,
    RScriptWriter,
    DictionaryReader, DictionaryWriter,
)
```

**Convention:** every reader exposes `read(path, **kwargs) -> SurveyData`; every
writer exposes `write(data, path, **kwargs) -> Path` and returns the `Path` it
wrote. `SurveyData` itself also has high-level `data.export("spss", path=...)` and
`data.export_dictionary(...)` helpers — see [[Working with Data|Working-with-Data]].

---

## `SurveyDataReader` — auto-detect by extension

```python
from siamang.io import SurveyDataReader

data = SurveyDataReader().read("responses.sav")   # picks the reader by suffix
```

A format router that dispatches on the file extension:

| Extension | Backed by |
| :--- | :--- |
| `.csv` | `CSVReader` |
| `.xlsx`, `.xls` | `ExcelReader` |
| `.sav` | `SPSSReader` |
| `.dta` | `StataReader` |

Unknown suffixes raise `ValueError`. Use it when you do not know (or do not care)
which concrete reader applies.

---

## CSV

```python
from siamang.io import CSVReader, CSVWriter

data = CSVReader().read("responses.csv")
CSVWriter().write(data, "out.csv")
```

| Class | Behaviour |
| :--- | :--- |
| `CSVReader.read(path, **kwargs)` | `pd.read_csv(path, **kwargs)` → `SurveyData(frame=...)`. **Metadata is not reconstructed.** |
| `CSVWriter.write(data, path, **kwargs)` | `data.frame.to_csv(path, index=False, **kwargs)`; returns `Path`. |

CSV carries data only. To recover labels and missing-value codes, pair the CSV with
a JSON dictionary (see [Data dictionary](#data-dictionary-codebooks)):

```python
from siamang.io import CSVReader, DictionaryReader

data = CSVReader().read("responses.csv")
data = data.__class__(frame=data.frame, variables=DictionaryReader().read("dict.json"))
```

---

## Excel

```python
from siamang.io import ExcelReader, ExcelWriter

data = ExcelReader().read("responses.xlsx")
ExcelWriter().write(data, "out.xlsx")
```

| Class | Behaviour |
| :--- | :--- |
| `ExcelReader.read(path, **kwargs)` | `pd.read_excel(path, **kwargs)`. |
| `ExcelWriter.write(data, path, **kwargs)` | `data.frame.to_excel(path, index=False, **kwargs)`. |

Like CSV, Excel I/O carries data only. Requires `openpyxl` (bundled by default).

---

## SPSS `.sav`

```python
from siamang.io import SPSSReader, SPSSWriter, read_spss

data = read_spss("trust.sav")              # SPSSReader().read(...)
SPSSWriter().write(data, "trust_out.sav")
```

| Class | Behaviour |
| :--- | :--- |
| `SPSSReader.read(path, **kwargs)` | Reads via `pyreadstat.read_sav(path, user_missing=True)`. Rebuilds a `VariableMap` from `meta.column_names_to_labels`, `meta.variable_value_labels`, `meta.missing_ranges`, and `meta.variable_measure`. |
| `SPSSWriter.write(data, path, **kwargs)` | Writes via `pyreadstat.write_sav` with variable labels, value labels, missing values, and formats. `data.variables` must be set, or columns are written bare. |
| `read_spss(path, **kwargs)` | Convenience for `SPSSReader().read(...)`. |

SPSS round-trips full metadata, so a file edited through siamang opens in SPSS as if
untouched:

```python
import pandas as pd
data = read_spss("input.sav")                       # metadata recovered
data = data.recode_values("age", {-1: pd.NA})       # treat -1 as missing
SPSSWriter().write(data, "output.sav")
```

`pyreadstat` is bundled by default (it powers both SPSS and Stata I/O).

---

## Stata `.dta`

```python
from siamang.io import StataReader, StataWriter, read_stata

data = read_stata("trust.dta")
StataWriter().write(data, "trust_out.dta", version=15)
```

| Class | Behaviour |
| :--- | :--- |
| `StataReader.read(path, **kwargs)` | `pyreadstat.read_dta(path, user_missing=True)` → `SurveyData` with a `VariableMap`. |
| `StataWriter.write(data, path, version=15, **kwargs)` | `pyreadstat.write_dta` with metadata. `version` (default `15`) is forwarded to `pyreadstat.write_dta` as the target Stata version. |
| `read_stata(path, **kwargs)` | Convenience function. |

Same metadata round-trip as SPSS.

---

## R

```python
from siamang.io import RScriptWriter

RScriptWriter().write(data, path="political_trust_R/")
```

Writes a three-file bundle into the target directory and returns the `Path` to
the R script:

- `import_survey.csv` — the responses;
- `import_survey_dictionary.json` — full `VariableMap` serialisation;
- `import_survey.R` — an R script that reads the CSV and dictionary (via
  `jsonlite`), replaces missing-value codes with `NA`, and applies value labels
  with `factor(...)`, leaving the result in an object named `survey_data`.

If `path` ends in `.R` (e.g. `trust.R`), the files are named after its stem
instead (`trust.csv`, `trust_dictionary.json`, `trust.R`).

```r
# In R:
source("political_trust_R/import_survey.R")   # builds the labelled `survey_data`
```

---

## Data dictionary (codebooks)

```python
from siamang.io import DictionaryReader, DictionaryWriter

DictionaryWriter().write(survey.variables, "dict.json")
restored = DictionaryReader().read("dict.json")     # -> VariableMap
```

| Class | Behaviour |
| :--- | :--- |
| `DictionaryWriter.write(variables: VariableMap, path)` | `json.dump(variables.to_dict(), ...)`. |
| `DictionaryReader.read(path)` | `VariableMap.from_dict(json.load(...))`. Raises `ValueError` if the JSON root is not a dict. |

Use a dictionary to store a survey's codebook alongside a CSV export (CSV/Excel
carry no metadata), or to distribute a variable schema independently of the
questionnaire.

---

## Round-tripping labels and missing values

SPSS and Stata are the formats that preserve everything. A typical recode-and-export
cycle:

```python
import pandas as pd
from siamang.io import read_spss, SPSSWriter

data = read_spss("input.sav")
data = data.recode_values("age", {-1: pd.NA}).apply_missing_values()
SPSSWriter().write(data, "output.sav")
```

For CSV-based pipelines, export both the data and a dictionary, and reattach the
dictionary on read:

```python
from siamang.io import CSVWriter, DictionaryWriter, CSVReader, DictionaryReader

CSVWriter().write(data, "out.csv")
DictionaryWriter().write(data.variables, "out_dict.json")

# later …
again = CSVReader().read("out.csv")
again = again.__class__(frame=again.frame, variables=DictionaryReader().read("out_dict.json"))
```

---

See also: [[Working with Data|Working-with-Data]] · [[Analysis]] ·
[[Variables and Measurement|Variables-and-Measurement]] · [[Cookbook]] ·
[[API Reference Index|API-Reference-Index]]
