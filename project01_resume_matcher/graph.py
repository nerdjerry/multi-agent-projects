"""
Project 01 — LangGraph sequential pipeline.

Resume PDF → [Agent 1] → [Agent 2] → [Agent 3] → [Agent 4] → Output
"""
from langgraph.graph import StateGraph, END

from state import ResumeMatcherState
from agents import (
    agent_resume_extractor,
    agent_jd_ingester,
    agent_fit_analyzer,
    agent_summary_rewriter,
)


def build_graph() -> StateGraph:
    builder = StateGraph(ResumeMatcherState)

    builder.add_node("resume_extractor", agent_resume_extractor)
    builder.add_node("jd_ingester", agent_jd_ingester)
    builder.add_node("fit_analyzer", agent_fit_analyzer)
    builder.add_node("summary_rewriter", agent_summary_rewriter)

    builder.set_entry_point("resume_extractor")
    builder.add_edge("resume_extractor", "jd_ingester")
    builder.add_edge("jd_ingester", "fit_analyzer")
    builder.add_edge("fit_analyzer", "summary_rewriter")
    builder.add_edge("summary_rewriter", END)

    return builder.compile()


# Compiled graph — import this in api.py and app.py
graph = build_graph()
