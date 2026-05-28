# Full Pipeline Demo: Remote Work & Algorithmic Management

A complete end-to-end example demonstrating the **siamang** workflow — from survey design to statistical analysis.

## Research Scenario

**Topic**: How digital monitoring and algorithmic management affect job satisfaction and perceived autonomy among IT professionals working remotely.

**Hypotheses**:
1. **The Autonomy-Surveillance Paradox**: While remote work increases subjective workplace autonomy, it is often accompanied by more invasive digital tracking (e.g., keystroke logging, webcam tracking), which in turn reduces job satisfaction.
2. **Professional Stratification**: Different roles within the IT industry (e.g., Software Engineers vs. Product Managers) experience varying levels of remote work flexibility and monitoring pressure.

---

## Files

| File | Description |
|:-----|:------------|
| `full_pipeline_demo.ipynb` | **Jupyter notebook** — full pipeline with all outputs saved inline (tables, stats, plots) |
| `survey_preview.html` | **Interactive HTML survey** — open in browser to see what respondents experience |
| `survey_responses.db` | **SQLite database** — 250 simulated responses stored exactly as in production |
| `fig_outcomes_by_remote.png` | Boxplots: satisfaction & autonomy by remote work frequency |
| `fig_surveillance_heatmap.png` | Heatmap: surveillance tool agreement by remote frequency |
| `banner_satisfaction_by_remote.xlsx` | Banner table export (publication-ready Excel) |

---

## Pipeline Steps (in the notebook)

### 1. Survey Design
- 12 variables with measurement scales, labels, valid ranges
- 10 questions across 6 pages
- Conditional routing: `show_if=consent.eq(1)`, `show_if=AND(consent.eq(1), remote_freq.ge(2))`

### 2. HTML Preview
- Compiled via SurveyJS runtime into a standalone `.html` file
- No server needed — just open in browser
- Includes all conditional logic, validation, progress bar

### 3. Database Storage
- SQLite with 3 tables: `survey_meta`, `responses`, `quota_counters`
- Each response stored as JSON with timestamp
- Same schema used in production local deployments

### 4. Simulation (250 respondents)
- Respects page-level `show_if` conditions
- `consent=0` → all subsequent variables = NaN
- `remote_freq=1` → surveillance variables = NaN
- Generates realistic random data within valid ranges

### 5. Statistical Analysis
- Frequency distributions with labels
- Cross-tabulation with Chi-square test and Cramer's V
- Kruskal-Wallis test for group differences
- Spearman correlations between surveillance and outcomes
- Boxplots and heatmaps (seaborn/matplotlib)
- Banner table export to Excel

---

## Quick Start

```bash
# Install siamang
pip install -e /path/to/siamang

# Run the notebook
jupyter notebook full_pipeline_demo.ipynb

# Or just open the HTML survey in browser
open survey_preview.html

# Query the database directly
sqlite3 survey_responses.db "SELECT COUNT(*) FROM responses;"
```

---

## Database Schema

```sql
CREATE TABLE survey_meta (
    survey_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    schema_json TEXT NOT NULL,
    max_responses INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quota_counters (
    survey_id TEXT NOT NULL,
    variable TEXT NOT NULL,
    value TEXT NOT NULL,
    target INTEGER NOT NULL,
    current INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (survey_id, variable, value)
);
```

---

## References

1. Sewell, Graham, and Barker, James R. *Coercion, Consent, and the Paradox of Cyber-Surveillance in the Contemporary Workplace*. Human Relations, 59(7), 2006.
2. Kalleberg, Arne L. *Good Jobs, Bad Jobs: The Rise of Polarized and Precarious Employment Systems in the United States, 1970s to 2000s*. Russell Sage Foundation, 2011.
