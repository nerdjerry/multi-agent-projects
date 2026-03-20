"""
Project 01 — AI Resume Matcher and Rewriter
Agents: Resume Extractor, JD Ingester, Fit Analyzer, Summary Rewriter
"""
import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from state import ResumeMatcherState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared LLM instances
# ---------------------------------------------------------------------------
_llm_analytical = ChatOpenAI(model="gpt-4o", temperature=0)
_llm_creative = ChatOpenAI(model="gpt-4o", temperature=0.3)


def _safe_json_loads(raw: str) -> Any:
    """Parse JSON from LLM output, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s\nRaw text: %s", exc, raw[:500])
        return None


# ---------------------------------------------------------------------------
# Agent 1 — Resume Extractor
# ---------------------------------------------------------------------------
_EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a resume parser. Extract structured information from the raw resume text "
        "and return a valid JSON object with the following keys:\n"
        "  name (string), summary (string), skills (list of strings), "
        "  experience (list of objects with keys: company, title, duration, highlights), "
        "  education (list of objects with keys: institution, degree, year), "
        "  seniority_level (string: junior | mid | senior | lead | executive).\n"
        "Return ONLY the JSON object, no markdown, no commentary.",
    ),
    ("human", "Resume text:\n\n{resume_text}"),
])


def agent_resume_extractor(state: ResumeMatcherState) -> dict:
    """Agent 1: Convert raw PDF text into structured JSON."""
    chain = _EXTRACT_PROMPT | _llm_analytical
    response = chain.invoke({"resume_text": state["resume_text"]})
    parsed = _safe_json_loads(response.content)
    if parsed is None:
        parsed = {
            "name": "Unknown",
            "summary": state["resume_text"][:500],
            "skills": [],
            "experience": [],
            "education": [],
            "seniority_level": "unknown",
        }
    return {"resume_json": parsed}


# ---------------------------------------------------------------------------
# Agent 2 — JD Ingester
# ---------------------------------------------------------------------------
_INGEST_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a job description parser. Normalize the given job description into a JSON object "
        "with the following keys:\n"
        "  required_skills (list of strings), "
        "  nice_to_have_skills (list of strings), "
        "  ats_keywords (list of strings), "
        "  experience_years (number), "
        "  seniority_level (string: junior | mid | senior | lead | executive), "
        "  role_title (string).\n"
        "Return ONLY the JSON object, no markdown, no commentary.",
    ),
    ("human", "Job description:\n\n{jd_text}"),
])


def agent_jd_ingester(state: ResumeMatcherState) -> dict:
    """Agent 2: Normalize each job description into a consistent schema."""
    chain = _INGEST_PROMPT | _llm_analytical
    structured_jds = []
    for jd in state["job_descriptions"]:
        raw_jd = jd if isinstance(jd, str) else json.dumps(jd)
        response = chain.invoke({"jd_text": raw_jd})
        parsed = _safe_json_loads(response.content)
        if parsed is None:
            parsed = {
                "required_skills": [],
                "nice_to_have_skills": [],
                "ats_keywords": [],
                "experience_years": 0,
                "seniority_level": "unknown",
                "role_title": "Unknown Role",
            }
        structured_jds.append(parsed)
    return {"job_descriptions": structured_jds}


# ---------------------------------------------------------------------------
# Agent 3 — Fit Analyzer
# ---------------------------------------------------------------------------
_FIT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a career coach and resume expert. Score how well the candidate's resume matches "
        "the given job description.\n"
        "Return a JSON object with these keys:\n"
        "  score (integer 0-100), "
        "  matching_skills (list of strings), "
        "  missing_skills (list of strings), "
        "  weak_sections (list of strings), "
        "  role_title (string).\n"
        "Return ONLY the JSON object, no markdown, no commentary.",
    ),
    (
        "human",
        "Resume (structured):\n{resume_json}\n\nJob Description (structured):\n{jd_json}",
    ),
])


def agent_fit_analyzer(state: ResumeMatcherState) -> dict:
    """Agent 3: Score resume against each JD, sort descending by score."""
    chain = _FIT_PROMPT | _llm_analytical
    resume_str = json.dumps(state["resume_json"], indent=2)
    fit_scores = []
    for jd in state["job_descriptions"]:
        jd_str = json.dumps(jd, indent=2)
        response = chain.invoke({"resume_json": resume_str, "jd_json": jd_str})
        parsed = _safe_json_loads(response.content)
        if parsed is None:
            parsed = {
                "score": 0,
                "matching_skills": [],
                "missing_skills": [],
                "weak_sections": [],
                "role_title": jd.get("role_title", "Unknown"),
            }
        fit_scores.append(parsed)
    fit_scores.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"fit_scores": fit_scores}


# ---------------------------------------------------------------------------
# Agent 4 — Summary Rewriter
# ---------------------------------------------------------------------------
_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert resume writer. Rewrite the candidate's professional summary so it is "
        "ATS-optimized for the target job description. Follow these rules:\n"
        "1. Maximum 4 sentences.\n"
        "2. Natural, human-sounding — not a keyword list.\n"
        "3. Only mention skills the candidate actually has.\n"
        "4. Weave in relevant ATS keywords from the JD naturally.\n"
        "Return ONLY the rewritten summary text, no preamble, no labels.",
    ),
    (
        "human",
        "Candidate's original summary:\n{original_summary}\n\n"
        "Target job description (structured):\n{best_jd}\n\n"
        "Candidate's skills: {skills}",
    ),
])


def agent_summary_rewriter(state: ResumeMatcherState) -> dict:
    """Agent 4: Rewrite the resume summary optimized for the best-matching JD."""
    chain = _REWRITE_PROMPT | _llm_creative
    best_jd = state["fit_scores"][0] if state["fit_scores"] else {}
    original_summary = state["resume_json"].get("summary", "")
    skills = ", ".join(state["resume_json"].get("skills", []))
    response = chain.invoke({
        "original_summary": original_summary,
        "best_jd": json.dumps(best_jd, indent=2),
        "skills": skills,
    })
    return {"rewritten_summary": response.content.strip()}
