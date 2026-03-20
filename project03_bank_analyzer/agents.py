"""
Project 03 — Personal Bank Statement Financial Analyzer
Pandas preprocessing node + 4 LLM agents.
"""
import json
import logging
import math
from typing import Any

import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from state import BankAnalyzerState

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o", temperature=0)
_llm_writer = ChatOpenAI(model="gpt-4o", temperature=0.3)

VALID_CATEGORIES = [
    "food", "rent", "utilities", "transport", "entertainment",
    "healthcare", "shopping", "subscriptions", "income", "savings", "other",
]


def _safe_json_loads(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s\nRaw: %s", exc, raw[:500])
        return None


# ---------------------------------------------------------------------------
# Pandas Loader / Preprocessor (not an LLM agent)
# ---------------------------------------------------------------------------
_COLUMN_ALIASES = {
    "date": ["date", "transaction date", "trans date", "value date", "posted date"],
    "description": ["description", "narration", "particulars", "memo", "details",
                    "merchant", "payee", "transaction description"],
    "amount": ["amount", "debit", "credit", "transaction amount", "value"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map whatever column names the bank uses to standard: date, description, amount."""
    lower_cols = {c.lower().strip(): c for c in df.columns}
    mapping = {}
    for target, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols:
                mapping[lower_cols[alias]] = target
                break
    df = df.rename(columns=mapping)
    required = {"date", "description", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Could not identify columns: {missing}. Found: {list(df.columns)}")
    return df[["date", "description", "amount"]].copy()


def pandas_loader(state: BankAnalyzerState) -> dict:
    """Load, clean, and normalize the CSV bank statement."""
    df = pd.read_csv(state["raw_csv_path"])
    df = _normalize_columns(df)
    df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True, errors="coerce")
    df = df.dropna(subset=["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["amount"] = df["amount"].abs()  # normalize debits as positive
    df = df.sort_values("date").reset_index(drop=True)
    transactions = df.to_dict(orient="records")
    # Convert Timestamps to strings for JSON serialisation
    for t in transactions:
        if hasattr(t["date"], "isoformat"):
            t["date"] = t["date"].isoformat()
    return {"transactions": transactions}


# ---------------------------------------------------------------------------
# Agent 1 — Transaction Categorizer (batch: 20 rows per LLM call)
# ---------------------------------------------------------------------------
_CATEGORIZE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a financial transaction categorizer. "
        "Given a batch of bank transactions, assign each one a category.\n\n"
        f"Valid categories: {', '.join(VALID_CATEGORIES)}.\n\n"
        "Return a JSON array where each element is an object with keys: "
        '  "index" (integer, matching the input index), '
        '  "category" (string from the valid list).\n'
        "Return ONLY the JSON array, no markdown, no commentary.",
    ),
    ("human", "Transactions (JSON array):\n{batch}"),
])

_BATCH_SIZE = 20


def agent_transaction_categorizer(state: BankAnalyzerState) -> dict:
    """Agent 1: Tag each transaction with a spending category."""
    chain = _CATEGORIZE_PROMPT | _llm
    transactions = [dict(t) for t in state["transactions"]]
    # Process in batches
    for batch_start in range(0, len(transactions), _BATCH_SIZE):
        batch = [
            {"index": i, "description": transactions[i]["description"],
             "amount": transactions[i]["amount"]}
            for i in range(batch_start, min(batch_start + _BATCH_SIZE, len(transactions)))
        ]
        response = chain.invoke({"batch": json.dumps(batch)})
        result = _safe_json_loads(response.content)
        if result:
            for item in result:
                idx = item.get("index")
                cat = item.get("category", "other")
                if idx is not None and 0 <= idx < len(transactions):
                    transactions[idx]["category"] = cat if cat in VALID_CATEGORIES else "other"
        # Ensure all in this batch have a category
        for i in range(batch_start, min(batch_start + _BATCH_SIZE, len(transactions))):
            transactions[i].setdefault("category", "other")
    return {"categorized": transactions}


# ---------------------------------------------------------------------------
# Agent 2 — Anomaly Detector (two-pass: Pandas stats + LLM pattern)
# ---------------------------------------------------------------------------
_ANOMALY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a financial fraud and anomaly analyst. "
        "Review these categorized bank transactions for unusual patterns "
        "that statistical methods might miss.\n\n"
        "Look for:\n"
        "- Duplicate or near-duplicate transactions (same amount + same vendor in short window)\n"
        "- Sudden price increases for recurring charges (subscription creep)\n"
        "- Unusual one-off large charges\n"
        "- Charges at unusual times (very late night, holidays)\n\n"
        "Return a JSON object with key 'pattern_anomalies' containing a list of objects, "
        "each with: description (string), amount (number), date (string), reason (string).\n"
        "Return ONLY the JSON object, no markdown, no commentary.",
    ),
    ("human", "Categorized transactions (JSON):\n{transactions}"),
])


def agent_anomaly_detector(state: BankAnalyzerState) -> dict:
    """Agent 2: Two-pass anomaly detection (Pandas stats + LLM patterns)."""
    transactions = state["categorized"]
    df = pd.DataFrame(transactions)

    # --- Pandas statistical pass: flag transactions > 2 std devs above category mean ---
    statistical_anomalies = []
    for category in df["category"].unique():
        if category == "income":
            continue
        cat_df = df[df["category"] == category]
        if len(cat_df) < 3:
            continue
        mean = cat_df["amount"].mean()
        std = cat_df["amount"].std()
        if std == 0 or math.isnan(std):
            continue
        flagged = cat_df[cat_df["amount"] > mean + 2 * std]
        for _, row in flagged.iterrows():
            statistical_anomalies.append({
                "description": row["description"],
                "amount": float(row["amount"]),
                "date": str(row["date"]),
                "category": category,
                "reason": f"Amount ${row['amount']:.2f} is > 2σ above {category} mean (${mean:.2f})",
            })

    # --- LLM pattern pass ---
    chain = _ANOMALY_PROMPT | _llm
    response = chain.invoke({"transactions": json.dumps(transactions[:200])})  # cap at 200 rows
    parsed = _safe_json_loads(response.content)
    pattern_anomalies = parsed.get("pattern_anomalies", []) if parsed else []

    return {
        "anomalies": {
            "statistical": statistical_anomalies,
            "pattern": pattern_anomalies,
        }
    }


# ---------------------------------------------------------------------------
# Agent 3 — Budget Auditor (50/30/20 rule)
# ---------------------------------------------------------------------------
_BUDGET_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a personal finance advisor. "
        "You have been given pre-computed spending percentages by category and total income.\n\n"
        "Evaluate the spending against the 50/30/20 rule:\n"
        "  50% = needs (rent, utilities, transport, healthcare, food)\n"
        "  30% = wants (entertainment, shopping, subscriptions)\n"
        "  20% = savings\n\n"
        "Return a JSON object with:\n"
        "  needs_pct (number), wants_pct (number), savings_pct (number),\n"
        "  needs_status (Under/On Track/Over), wants_status, savings_status,\n"
        "  overall_verdict (string, 1 sentence),\n"
        "  category_breakdown (list of {category, amount, pct, flag}).\n"
        "Return ONLY the JSON object, no markdown, no commentary.",
    ),
    (
        "human",
        "Total income: ${total_income:.2f}\n"
        "Total spending: ${total_spending:.2f}\n"
        "Category totals (JSON):\n{category_totals}",
    ),
])

_NEEDS_CATEGORIES = {"rent", "utilities", "transport", "healthcare", "food"}
_WANTS_CATEGORIES = {"entertainment", "shopping", "subscriptions"}


def agent_budget_auditor(state: BankAnalyzerState) -> dict:
    """Agent 3: Pandas aggregates totals; LLM interprets vs 50/30/20 rule."""
    transactions = state["categorized"]
    df = pd.DataFrame(transactions)

    # Pandas aggregation — LLM never does the arithmetic
    total_income = float(df[df["category"] == "income"]["amount"].sum())
    spending_df = df[df["category"] != "income"]
    category_totals = spending_df.groupby("category")["amount"].sum().to_dict()
    total_spending = float(spending_df["amount"].sum())

    if total_income == 0:
        total_income = total_spending  # fallback if no income rows

    category_list = [
        {"category": cat, "amount": float(amt),
         "pct": round(float(amt) / total_income * 100, 1) if total_income > 0 else 0}
        for cat, amt in category_totals.items()
    ]

    chain = _BUDGET_PROMPT | _llm
    response = chain.invoke({
        "total_income": total_income,
        "total_spending": total_spending,
        "category_totals": json.dumps(category_list, indent=2),
    })
    parsed = _safe_json_loads(response.content)
    if parsed is None:
        parsed = {
            "needs_pct": 0, "wants_pct": 0, "savings_pct": 0,
            "needs_status": "Unknown", "wants_status": "Unknown", "savings_status": "Unknown",
            "overall_verdict": "Could not compute budget analysis.",
            "category_breakdown": category_list,
        }
    return {"budget_analysis": parsed}


# ---------------------------------------------------------------------------
# Agent 4 — Report Writer
# ---------------------------------------------------------------------------
_REPORT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a personal finance coach writing a monthly financial health report. "
        "Be direct, clear, and jargon-free. Under 400 words.\n\n"
        "Structure the report as:\n"
        "1. **Health Score** (0–100) with one sentence explaining it.\n"
        "2. **Key Findings** (3–5 bullet points).\n"
        "3. **Anomalies to Review** (list from provided anomaly data).\n"
        "4. **Top 5 Action Items** (specific, actionable).\n"
        "5. **Bottom Line** (one closing sentence).\n\n"
        "Do not exceed 400 words. No asterisks for bullet points — use plain dashes.",
    ),
    (
        "human",
        "Budget Analysis:\n{budget_analysis}\n\n"
        "Anomalies:\n{anomalies}\n\n"
        "Total transactions analyzed: {tx_count}",
    ),
])


def agent_report_writer(state: BankAnalyzerState) -> dict:
    """Agent 4: Synthesize all findings into a financial health report."""
    chain = _REPORT_PROMPT | _llm_writer
    anomalies = state.get("anomalies", {})
    all_anomalies = anomalies.get("statistical", []) + anomalies.get("pattern", [])
    response = chain.invoke({
        "budget_analysis": json.dumps(state.get("budget_analysis", {}), indent=2),
        "anomalies": json.dumps(all_anomalies[:20], indent=2),  # cap at 20 for prompt size
        "tx_count": len(state.get("categorized", [])),
    })
    return {"report": response.content.strip()}
