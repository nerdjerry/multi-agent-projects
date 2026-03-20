"""
Project 01 — FastAPI REST layer.

POST /analyze
  Body (multipart/form-data):
    resume: PDF file upload
    job_descriptions: list of JD text strings (up to 5)

GET /health
"""
import io
import logging
from typing import List

import fitz  # PyMuPDF
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from graph import graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Resume Matcher & Rewriter",
    description="Scores a resume against up to 5 job descriptions and rewrites the summary.",
    version="1.0.0",
)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(..., description="PDF resume file"),
    job_descriptions: List[str] = Form(..., description="List of job description texts (up to 5)"),
):
    if len(job_descriptions) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 job descriptions allowed.")
    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")

    pdf_bytes = await resume.read()
    try:
        resume_text = _extract_pdf_text(pdf_bytes)
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.") from exc

    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="PDF appears to contain no extractable text.")

    initial_state = {
        "resume_text": resume_text,
        "job_descriptions": list(job_descriptions),
    }

    try:
        result = graph.invoke(initial_state)
    except Exception as exc:
        logger.error("Graph execution failed: %s", exc)
        raise HTTPException(status_code=500, detail="Pipeline execution failed.") from exc

    return JSONResponse({
        "resume_json": result.get("resume_json"),
        "fit_scores": result.get("fit_scores"),
        "rewritten_summary": result.get("rewritten_summary"),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
