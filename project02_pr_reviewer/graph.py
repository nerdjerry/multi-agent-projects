"""
Project 02 — LangGraph fan-out / fan-in pipeline.

[Fetch Diff] → [Agent 1: Security]     ↘
             → [Agent 2: Performance]   → [Agent 4: Lead Reviewer] → Output
             → [Agent 3: Coverage]     ↗
"""
import logging
import os
import re

import requests
from github import Github
from langgraph.graph import StateGraph, END

from state import PRReviewerState
from agents import (
    agent_vulnerability_scanner,
    agent_performance_reviewer,
    agent_coverage_auditor,
    agent_lead_reviewer,
)

logger = logging.getLogger(__name__)


def _fetch_full_diff(owner: str, repo_name: str, pr_number: int) -> str | None:
    """Fetch the complete PR diff via GitHub's diff media type.

    Returns the raw unified diff string, or None if the request fails so the
    caller can fall back to assembling per-file patches.
    """
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3.diff"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_number}"
    try:
        resp = requests.get(api_url, headers=headers, timeout=30)
        resp.raise_for_status()
        diff = resp.text
        return diff if diff.strip() else None
    except Exception as exc:
        logger.warning("Full diff fetch failed (%s); falling back to per-file patches.", exc)
        return None


def fetch_diff(state: PRReviewerState) -> dict:
    """Fetch the PR diff from GitHub using PyGithub."""
    pr_url = state["pr_url"]

    # Parse owner/repo/PR number from URL
    # Supports: https://github.com/owner/repo/pull/123
    match = re.match(
        r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
        pr_url,
    )
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")

    owner = match.group("owner")
    repo_name = match.group("repo")
    pr_number = int(match.group("number"))

    # Prefer the full diff from the GitHub API (avoids truncation of large files)
    diff = _fetch_full_diff(owner, repo_name, pr_number)

    if diff is None:
        # Fall back to assembling diff from per-file patches via PyGithub
        token = os.getenv("GITHUB_TOKEN")
        gh = Github(token) if token else Github()
        repo = gh.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)

        diff_parts = []
        for f in pr.get_files():
            patch = getattr(f, "patch", None)
            if patch:
                diff_parts.append(f"--- a/{f.filename}\n+++ b/{f.filename}\n{patch}")
        diff = "\n\n".join(diff_parts)

    if not diff.strip():
        diff = "(No text diff available — diff may be binary or empty.)"

    return {"diff": diff}


def build_graph() -> StateGraph:
    builder = StateGraph(PRReviewerState)

    builder.add_node("fetch_diff", fetch_diff)
    builder.add_node("vulnerability_scanner", agent_vulnerability_scanner)
    builder.add_node("performance_reviewer", agent_performance_reviewer)
    builder.add_node("coverage_auditor", agent_coverage_auditor)
    builder.add_node("lead_reviewer", agent_lead_reviewer)

    builder.set_entry_point("fetch_diff")

    # Fan-out: fetch_diff → all three specialist agents in parallel
    builder.add_edge("fetch_diff", "vulnerability_scanner")
    builder.add_edge("fetch_diff", "performance_reviewer")
    builder.add_edge("fetch_diff", "coverage_auditor")

    # Fan-in: all three specialist agents → lead reviewer
    builder.add_edge("vulnerability_scanner", "lead_reviewer")
    builder.add_edge("performance_reviewer", "lead_reviewer")
    builder.add_edge("coverage_auditor", "lead_reviewer")

    builder.add_edge("lead_reviewer", END)

    return builder.compile()


# Compiled graph — import this in api.py
graph = build_graph()
