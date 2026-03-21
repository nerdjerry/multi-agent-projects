"""
Project 02 — State definition (TypedDict).
"""
from typing import TypedDict


class PRReviewerState(TypedDict, total=False):
    pr_url: str              # input
    diff: str                # written by fetch_diff node
    security_report: str     # Agent 1 output
    perf_report: str         # Agent 2 output
    coverage_report: str     # Agent 3 output
    final_comment: str       # Agent 4 output — final result
