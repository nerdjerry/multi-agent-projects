# 🤖 Multi-Agent AI Projects

> A collection of four production-ready multi-agent systems built with **LangGraph**, **LangChain**, and **OpenAI** — each solving a real-world problem with autonomous, collaborating AI agents.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-blueviolet)
![LangChain](https://img.shields.io/badge/LangChain-latest-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-black?logo=openai)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-FF4B4B?logo=streamlit)

---

## 🗺️ What Is This?

This repository is a hands-on exploration of **multi-agent AI architecture** patterns. Each project is a self-contained Python application where multiple specialized AI agents collaborate — passing structured state between themselves — to complete tasks that would be too complex or impractical for a single prompt.

Two core LangGraph patterns are demonstrated across the four projects:

| Pattern | Description | Projects |
|---|---|---|
| **Sequential Chain** | Agents run one after another, each enriching the shared state | 01, 03 |
| **Fan-out → Fan-in** | Agents run in parallel, then a lead agent synthesizes all results | 02, 04 |

---

## 📦 Projects at a Glance

### 🗂️ [Project 01 — AI Resume Matcher & Rewriter](./project01_resume_matcher)

Upload a resume PDF and up to five job descriptions. The pipeline extracts and structures your resume, scores it against each role, identifies skill gaps, and rewrites your summary to be ATS-optimized for the best-matching position.

```
Resume PDF → [Extract] → [Parse JDs] → [Score & Rank] → [Rewrite Summary]
```

**Key tech:** PyMuPDF · FastAPI · Streamlit  
**Interface:** REST API + Streamlit UI

---

### 🔍 [Project 02 — Automated GitHub PR Code Reviewer](./project02_pr_reviewer)

Paste a GitHub PR URL and get an instant, structured code review. Three specialist agents analyze the diff in parallel — one for security vulnerabilities, one for performance issues, and one for test coverage — then a lead agent merges their findings into a single GitHub-flavored Markdown comment.

```
PR URL → [Fetch Diff] → [Security] ↘
                      → [Performance] → [Lead Reviewer] → Structured Comment
                      → [Coverage]   ↗
```

**Key tech:** PyGithub · FastAPI · Redis  
**Interface:** REST API

---

### 🏦 [Project 03 — Personal Bank Statement Analyzer](./project03_bank_analyzer)

Upload up to three months of CSV bank statements. A Pandas preprocessing node cleans and normalizes the data before four LLM agents categorize every transaction, detect anomalies, audit your budget against the 50/30/20 rule, and produce a plain-English financial health report.

```
CSV → [Pandas Loader] → [Categorize] → [Anomalies] → [Budget Audit] → [Report]
```

**Key tech:** Pandas · Streamlit  
**Interface:** Streamlit UI

---

### 📈 [Project 04 — AI Stock Research & Investment Brief Generator](./project04_stock_research)

Enter any stock ticker. Three research agents run in parallel — pulling financial fundamentals, scanning recent news for sentiment, and computing technical indicators (RSI, MACD, SMA) — before a brief-writer synthesizes everything into a concise investment brief with a clear **Buy / Hold / Watch / Avoid** signal.

```
Ticker → [Fundamentals] ↘
       → [Sentiment]     → [Brief Writer] → Investment Brief
       → [Technicals]   ↗
```

**Key tech:** yfinance · NewsAPI · TA-Lib (optional) · FastAPI · Streamlit  
**Interface:** REST API + Streamlit UI

---

## 🏗️ Repository Structure

```
multi-agent-projects/
├── project01_resume_matcher/
│   ├── agents.py          # All four agent functions
│   ├── graph.py           # LangGraph pipeline definition
│   ├── state.py           # Typed state schema
│   ├── api.py             # FastAPI endpoints
│   ├── app.py             # Streamlit UI
│   └── requirements.txt
├── project02_pr_reviewer/
│   └── ...                # Same structure
├── project03_bank_analyzer/
│   └── ...
└── project04_stock_research/
    └── ...
```

Each project is **fully independent** — its own `requirements.txt`, `.env.example`, and README.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- Additional keys for specific projects (see each project's README)

### Run Any Project

```bash
# 1. Navigate to the project
cd project01_resume_matcher   # or 02, 03, 04

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY (and any other required keys)

# 3. Install dependencies
pip install -r requirements.txt

# 4a. Launch the REST API (projects 01, 02, 04)
uvicorn api:app --reload

# 4b. Or launch the Streamlit UI (projects 01, 03, 04)
streamlit run app.py
```

> Each project folder contains its own `README.md` with detailed setup instructions, example requests, and state documentation.

---

## 🧠 Why LangGraph?

LangGraph gives you **explicit, debuggable control** over multi-step AI workflows:

- **Typed state** — every agent reads from and writes to a shared, validated state object
- **Conditional edges** — route between agents based on intermediate results
- **Parallel fan-out** — run independent agents concurrently and collect all results before continuing
- **Easy observability** — the graph structure is inspectable and can be visualized

---

## 🔑 Environment Variables

| Variable | Required by | Description |
|---|---|---|
| `OPENAI_API_KEY` | All projects | Your OpenAI API key |
| `GITHUB_TOKEN` | Project 02 | GitHub personal access token for fetching PR diffs |
| `NEWS_API_KEY` | Project 04 | [NewsAPI](https://newsapi.org/) key — without it the sentiment agent falls back to yfinance headlines, which cover fewer sources |

> **Security note:** Never commit your `.env` file or hard-code secrets in source files. `.env` is already listed in `.gitignore`; keep it that way. Rotate any key that is accidentally exposed.

---

## 📄 License

This repository is open-source. Feel free to use, adapt, and build on these projects.
