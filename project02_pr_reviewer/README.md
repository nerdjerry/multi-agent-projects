# Project 02 — Automated GitHub PR Code Reviewer

Takes a GitHub PR URL. Fetches the diff. Runs three reviewer agents in parallel then a lead agent synthesizes one structured PR comment with severity-tiered findings.

## Architecture

**LangGraph pattern:** Fan-out → fan-in (parallel specialist agents).

```
[Fetch Diff] → [Agent 1: Security]     ↘
             → [Agent 2: Performance]   → [Agent 4: Lead Reviewer] → Output
             → [Agent 3: Coverage]     ↗
```

| Agent | Role |
|---|---|
| Agent 1 — Vulnerability Scanner | OWASP Top 10, hardcoded secrets, SQL injection |
| Agent 2 — Performance Reviewer | N+1 queries, nested loops, sync/async, unbounded structures |
| Agent 3 — Test Coverage Auditor | Missing tests, edge cases, unmocked external calls |
| Agent 4 — Lead Reviewer | Merges duplicates, writes GitHub-flavored Markdown comment |

## Setup

```bash
cp .env.example .env
# Edit .env — add OPENAI_API_KEY and GITHUB_TOKEN

pip install -r requirements.txt
```

## Run

```bash
uvicorn api:app --port 8001 --reload
```

**Request:**
```bash
curl -X POST http://localhost:8001/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/42"}'
```

## State Shape

| Field | Type | Owner |
|---|---|---|
| `pr_url` | string | Input |
| `diff` | string | `fetch_diff` node |
| `security_report` | string | Agent 1 |
| `perf_report` | string | Agent 2 |
| `coverage_report` | string | Agent 3 |
| `final_comment` | string | Agent 4 |
