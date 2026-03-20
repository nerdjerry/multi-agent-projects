"""
Project 02 — Automated GitHub PR Code Reviewer
Agents: Vulnerability Scanner, Performance Reviewer, Test Coverage Auditor, Lead Reviewer
"""
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from state import PRReviewerState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared LLM — GPT-4o with 128k context to handle large diffs
# ---------------------------------------------------------------------------
_llm = ChatOpenAI(model="gpt-4o", temperature=0)
_llm_lead = ChatOpenAI(model="gpt-4o", temperature=0)

# ---------------------------------------------------------------------------
# Agent 1 — Vulnerability Scanner (Security)
# ---------------------------------------------------------------------------
_SECURITY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a security-focused code reviewer specializing in OWASP Top 10. "
        "Review the provided git diff for security vulnerabilities only.\n\n"
        "Check for:\n"
        "- OWASP Top 10 vulnerabilities (injection, XSS, CSRF, broken auth, etc.)\n"
        "- Hardcoded secrets, API keys, passwords, or tokens\n"
        "- SQL injection patterns\n"
        "- Insecure dependencies or imports\n"
        "- Insecure deserialization\n"
        "- Missing input validation\n\n"
        "For each finding include: severity (High/Medium/Low), file and line reference, "
        "a clear description of the vulnerability, and a recommended fix.\n"
        "If no issues found, say so explicitly. Be concise and precise.",
    ),
    ("human", "Git diff to review:\n\n```diff\n{diff}\n```"),
])


def agent_vulnerability_scanner(state: PRReviewerState) -> dict:
    """Agent 1: Scan diff for security vulnerabilities."""
    chain = _SECURITY_PROMPT | _llm
    response = chain.invoke({"diff": state["diff"]})
    return {"security_report": response.content.strip()}


# ---------------------------------------------------------------------------
# Agent 2 — Performance Reviewer
# ---------------------------------------------------------------------------
_PERF_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a performance-focused code reviewer. "
        "Review the provided git diff for performance issues only.\n\n"
        "Check for:\n"
        "- N+1 query patterns\n"
        "- Unnecessary nested loops (O(n²) or worse where avoidable)\n"
        "- Missing database index hints or full-table scans\n"
        "- Unbounded data structures (growing lists/dicts with no limit)\n"
        "- Synchronous calls where async would significantly help\n"
        "- Repeated expensive computations that could be cached\n\n"
        "For each finding include: severity (High/Medium/Low), file and line reference, "
        "description, and recommended fix.\n"
        "If no issues found, say so explicitly. Be concise and precise.",
    ),
    ("human", "Git diff to review:\n\n```diff\n{diff}\n```"),
])


def agent_performance_reviewer(state: PRReviewerState) -> dict:
    """Agent 2: Flag performance issues in the diff."""
    chain = _PERF_PROMPT | _llm
    response = chain.invoke({"diff": state["diff"]})
    return {"perf_report": response.content.strip()}


# ---------------------------------------------------------------------------
# Agent 3 — Test Coverage Auditor
# ---------------------------------------------------------------------------
_COVERAGE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a test coverage auditor. "
        "Review the provided git diff for missing or inadequate test coverage.\n\n"
        "Check for:\n"
        "- New functions, classes, or methods with no associated tests\n"
        "- Missing edge cases: null/None inputs, empty collections, boundary values\n"
        "- External calls (HTTP, DB, filesystem) that are not mocked in tests\n"
        "- Error paths and exception handling that are untested\n"
        "- Tests that exist but do not assert meaningful outcomes\n\n"
        "For each finding include: severity (High/Medium/Low), what is missing, "
        "and what test cases should be added.\n"
        "If coverage looks adequate, say so explicitly. Be concise and precise.",
    ),
    ("human", "Git diff to review:\n\n```diff\n{diff}\n```"),
])


def agent_coverage_auditor(state: PRReviewerState) -> dict:
    """Agent 3: Identify test coverage gaps."""
    chain = _COVERAGE_PROMPT | _llm
    response = chain.invoke({"diff": state["diff"]})
    return {"coverage_report": response.content.strip()}


# ---------------------------------------------------------------------------
# Agent 4 — Lead Reviewer (synthesize & deduplicate)
# ---------------------------------------------------------------------------
_LEAD_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a lead code reviewer synthesizing findings from three specialist reviewers.\n\n"
        "Your tasks:\n"
        "1. Merge duplicate findings (same issue found by multiple reviewers → keep once).\n"
        "2. Write a single GitHub-flavored Markdown PR review comment.\n"
        "3. Group findings under headings: ## 🔴 High Severity, ## 🟡 Medium Severity, ## 🟢 Low Severity.\n"
        "4. Start the comment with an overall verdict badge: **Verdict: Approve ✅** | "
        "**Verdict: Request Changes ❌** | **Verdict: Comment 💬**.\n"
        "5. Keep it actionable and developer-friendly. No waffle.\n\n"
        "Output ONLY the Markdown comment text.",
    ),
    (
        "human",
        "Security Report:\n{security_report}\n\n"
        "Performance Report:\n{perf_report}\n\n"
        "Test Coverage Report:\n{coverage_report}",
    ),
])


def agent_lead_reviewer(state: PRReviewerState) -> dict:
    """Agent 4: Synthesize all reports into a single PR comment."""
    chain = _LEAD_PROMPT | _llm_lead
    response = chain.invoke({
        "security_report": state.get("security_report", "No report."),
        "perf_report": state.get("perf_report", "No report."),
        "coverage_report": state.get("coverage_report", "No report."),
    })
    return {"final_comment": response.content.strip()}
