"""
Project 03 — LangGraph sequential pipeline with Pandas preprocessing.

CSV → [Pandas Loader] → [Agent 1] → [Agent 2] → [Agent 3] → [Agent 4] → Report
"""
from langgraph.graph import StateGraph, END

from state import BankAnalyzerState
from agents import (
    pandas_loader,
    agent_transaction_categorizer,
    agent_anomaly_detector,
    agent_budget_auditor,
    agent_report_writer,
)


def build_graph() -> StateGraph:
    builder = StateGraph(BankAnalyzerState)

    builder.add_node("pandas_loader", pandas_loader)
    builder.add_node("transaction_categorizer", agent_transaction_categorizer)
    builder.add_node("anomaly_detector", agent_anomaly_detector)
    builder.add_node("budget_auditor", agent_budget_auditor)
    builder.add_node("report_writer", agent_report_writer)

    builder.set_entry_point("pandas_loader")
    builder.add_edge("pandas_loader", "transaction_categorizer")
    builder.add_edge("transaction_categorizer", "anomaly_detector")
    builder.add_edge("anomaly_detector", "budget_auditor")
    builder.add_edge("budget_auditor", "report_writer")
    builder.add_edge("report_writer", END)

    return builder.compile()


# Compiled graph — import this in app.py
graph = build_graph()
