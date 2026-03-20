# Project 04 — AI Stock Research & Investment Brief Generator

Takes a stock ticker. Runs three research agents in parallel — fundamentals, news sentiment, and technical analysis — then a brief writer synthesizes a one-page investment brief with a clear signal.

## Architecture

**LangGraph pattern:** Fan-out → fan-in (same pattern as Project 02).

```
[Ticker] → [Agent 1: Fundamentals]  ↘
         → [Agent 2: Sentiment]      → [Agent 4: Brief Writer] → Investment Brief
         → [Agent 3: Technical]     ↗
```

| Agent | Role |
|---|---|
| Agent 1 — Financial Data Analyst | Fetches P/E, EPS, revenue growth, debt/equity, FCF via yfinance |
| Agent 2 — News Sentiment Scanner | Fetches last 7 days headlines (NewsAPI / yfinance fallback) |
| Agent 3 — Price Signal Reader | Computes RSI(14), MACD(12,26,9), SMA(50), SMA(200) |
| Agent 4 — Risk & Brief Writer | Synthesizes into Buy / Hold / Watch / Avoid brief |

## Setup

```bash
# Optional: install TA-Lib C library for precise indicator calculations
# Mac:    brew install ta-lib
# Ubuntu: apt-get install libta-lib-dev
# Then:   pip install ta-lib

cp .env.example .env
# Edit .env — add OPENAI_API_KEY and optionally NEWS_API_KEY

pip install -r requirements.txt
```

> **TA-Lib is optional.** The project includes pure-Python fallback implementations of RSI, MACD, and SMA that activate automatically when TA-Lib is not installed.

## Run

**REST API:**
```bash
uvicorn api:app --port 8002 --reload
# GET /brief?ticker=MSFT
```

**Streamlit UI:**
```bash
streamlit run app.py
```

## Notes

- For Indian stocks: append `.NS` (NSE) or `.BO` (BSE) to the ticker. E.g. `RELIANCE.NS`.
- If `NEWS_API_KEY` is not set, the agent falls back to yfinance news headlines.
- TA-Lib NaN values are stripped with `arr[~np.isnan(arr)][-1]` before passing to the LLM.

## State Shape

| Field | Type | Owner |
|---|---|---|
| `ticker` | string | Input |
| `fundamentals_report` | string | Agent 1 |
| `sentiment_report` | string | Agent 2 |
| `technical_report` | string | Agent 3 |
| `investment_brief` | string | Agent 4 |
