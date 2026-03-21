"""
Project 03 — State definition (TypedDict).
"""
from typing import TypedDict


class BankAnalyzerState(TypedDict, total=False):
    raw_csv_path: str       # input
    transactions: list      # Pandas loader output — cleaned dicts
    categorized: list       # Agent 1 output — transactions with category field
    anomalies: dict         # Agent 2 output — statistical and pattern anomaly lists
    budget_analysis: dict   # Agent 3 output — percentages, status, verdict
    report: str             # Agent 4 output — final result
