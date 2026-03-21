"""
Project 01 — Streamlit UI for the AI Resume Matcher & Rewriter.

Run:  streamlit run app.py
"""
import os
import sys

import fitz  # PyMuPDF
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Allow running from inside project directory
sys.path.insert(0, os.path.dirname(__file__))
from graph import graph  # noqa: E402

st.set_page_config(page_title="AI Resume Matcher & Rewriter", layout="wide")
st.title("🧑‍💼 AI Resume Matcher & Rewriter")
st.markdown(
    "Upload your resume PDF and paste up to **5 job descriptions**. "
    "The pipeline will score each role, identify gaps, and rewrite your summary for the best match."
)

# --- Sidebar inputs ---
with st.sidebar:
    st.header("Inputs")
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    st.markdown("---")
    st.subheader("Job Descriptions")
    jds = []
    for i in range(1, 6):
        jd = st.text_area(f"JD {i}", height=120, key=f"jd_{i}")
        if jd.strip():
            jds.append(jd.strip())
    run_button = st.button("🚀 Analyze & Rewrite", type="primary", disabled=(resume_file is None or len(jds) == 0))

# --- Main panel ---
if run_button:
    if resume_file is None:
        st.error("Please upload a PDF resume.")
        st.stop()
    if not jds:
        st.error("Please enter at least one job description.")
        st.stop()

    with st.spinner("Extracting resume text…"):
        pdf_bytes = resume_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        resume_text = "\n".join(page.get_text() for page in doc)

    if not resume_text.strip():
        st.error("Could not extract text from the PDF (it may be scanned/image-only).")
        st.stop()

    with st.spinner("Running multi-agent pipeline… (this may take 30–60 seconds)"):
        result = graph.invoke({
            "resume_text": resume_text,
            "job_descriptions": jds,
        })

    # --- Results ---
    st.success("Pipeline complete!")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Parsed Resume")
        resume_json = result.get("resume_json", {})
        st.write(f"**Name:** {resume_json.get('name', 'N/A')}")
        st.write(f"**Seniority:** {resume_json.get('seniority_level', 'N/A')}")
        st.write(f"**Skills:** {', '.join(resume_json.get('skills', []))}")
        with st.expander("Full resume JSON"):
            st.json(resume_json)

    with col2:
        st.subheader("✏️ Rewritten Summary")
        st.info(result.get("rewritten_summary", "No summary generated."))

    st.subheader("📊 Fit Scores (best match first)")
    fit_scores = result.get("fit_scores", [])
    for idx, score in enumerate(fit_scores):
        with st.expander(
            f"{'🥇' if idx == 0 else f'#{idx+1}'} {score.get('role_title', 'Role')} — Score: {score.get('score', 'N/A')}/100",
            expanded=(idx == 0),
        ):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Matching Skills**")
                for s in score.get("matching_skills", []):
                    st.markdown(f"- ✅ {s}")
            with col_b:
                st.markdown("**Missing Skills**")
                for s in score.get("missing_skills", []):
                    st.markdown(f"- ❌ {s}")
            if score.get("weak_sections"):
                st.markdown("**Weak Sections:** " + ", ".join(score["weak_sections"]))
