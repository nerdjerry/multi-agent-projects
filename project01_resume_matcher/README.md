# Project 01 — AI Resume Matcher & Rewriter

Takes a resume PDF and up to 5 job descriptions. Parses the resume, extracts JD requirements, scores fit per role with gap analysis, then rewrites the resume summary for the best-matching role.

## Architecture

**LangGraph pattern:** Sequential chain.

```
Resume PDF → [Agent 1] → [Agent 2] → [Agent 3] → [Agent 4] → Output
```

| Agent | Role |
|---|---|
| Agent 1 — Resume Extractor | Converts raw PDF text into structured JSON |
| Agent 2 — JD Ingester | Normalizes each job description into a consistent schema |
| Agent 3 — Fit Analyzer | Scores resume vs each JD (0–100), sorts best match first |
| Agent 4 — Summary Rewriter | Rewrites summary ATS-optimized for best-matching role |

## Setup

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key

pip install -r requirements.txt
```

## Run

**REST API:**
```bash
uvicorn api:app --reload
# POST /analyze  (multipart/form-data: resume=<PDF>, job_descriptions=<list>)
```

**Streamlit UI:**
```bash
streamlit run app.py
```

## State Shape

| Field | Type | Owner |
|---|---|---|
| `resume_text` | string | Input |
| `resume_json` | dict | Agent 1 |
| `job_descriptions` | list | Input (raw) → Agent 2 (structured) |
| `fit_scores` | list | Agent 3 |
| `rewritten_summary` | string | Agent 4 |
