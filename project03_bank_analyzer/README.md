# Project 03 — Personal Bank Statement Financial Analyzer

Takes CSV bank statements (up to 3 months). Pandas preprocesses and cleans the data before LLM agents touch it. Four agents then categorize transactions, detect anomalies, benchmark against 50/30/20, and write a financial health report.

## Architecture

**LangGraph pattern:** Sequential chain with Pandas preprocessing node.

```
CSV → [Pandas Loader] → [Agent 1] → [Agent 2] → [Agent 3] → [Agent 4] → Report
```

| Step | Role |
|---|---|
| Pandas Loader | Load, clean, normalize columns (date/description/amount) |
| Agent 1 — Transaction Categorizer | Tags each transaction with a category (batched, 20 rows/call) |
| Agent 2 — Anomaly Detector | Statistical (Pandas) + pattern (LLM) two-pass detection |
| Agent 3 — Budget Auditor | Pandas aggregates; LLM interprets vs 50/30/20 rule |
| Agent 4 — Report Writer | Writes health report under 400 words |

## Setup

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key

pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## CSV Format

The loader auto-detects column names. Common bank export formats are supported. At minimum the CSV must have columns for:
- **Date** (any recognizable date format)
- **Description** (merchant / narration)
- **Amount** (positive or negative numbers — negatives are auto-converted to positive)

## State Shape

| Field | Type | Owner |
|---|---|---|
| `raw_csv_path` | string | Input |
| `transactions` | list | Pandas Loader |
| `categorized` | list | Agent 1 |
| `anomalies` | dict | Agent 2 |
| `budget_analysis` | dict | Agent 3 |
| `report` | string | Agent 4 |
