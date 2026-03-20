"""
Project 01 — State definition (TypedDict).
"""
from typing import TypedDict, Any


class ResumeMatcherState(TypedDict, total=False):
    resume_text: str          # input — raw PDF text
    resume_json: dict         # Agent 1 output
    job_descriptions: list    # input as raw strings; overwritten by Agent 2 as structured dicts
    fit_scores: list          # Agent 3 output, sorted descending
    rewritten_summary: str    # Agent 4 output — final result
