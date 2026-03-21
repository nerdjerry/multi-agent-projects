"""
Project 02 — FastAPI webhook / REST endpoint.

POST /review
  Body (JSON): { "pr_url": "https://github.com/owner/repo/pull/123" }

GET /health
"""
import hashlib
import json
import logging
import os

import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from graph import graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Automated GitHub PR Code Reviewer",
    description="Fan-out/fan-in multi-agent PR review: security, performance, and coverage.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Optional Redis cache — skips reprocessing already-reviewed PRs
# ---------------------------------------------------------------------------
_CACHE_TTL_SECONDS = 3600  # 1 hour

def _get_redis() -> redis.Redis | None:
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable (%s); running without cache.", exc)
        return None


def _cache_key(pr_url: str) -> str:
    return "pr_review:" + hashlib.sha256(pr_url.encode()).hexdigest()


class ReviewRequest(BaseModel):
    pr_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/review")
def review(request: ReviewRequest):
    if "github.com" not in request.pr_url or "/pull/" not in request.pr_url:
        raise HTTPException(
            status_code=400,
            detail="pr_url must be a valid GitHub pull request URL (https://github.com/owner/repo/pull/N).",
        )

    # Check cache first
    cache = _get_redis()
    key = _cache_key(request.pr_url)
    if cache:
        cached = cache.get(key)
        if cached:
            logger.info("Cache hit for %s", request.pr_url)
            try:
                cached_data = json.loads(cached)
            except json.JSONDecodeError as exc:
                logger.warning("Corrupted cache entry for key %s: %s; deleting and recomputing.", key, exc)
                try:
                    cache.delete(key)
                except Exception as del_exc:
                    logger.warning("Failed to delete corrupted cache key %s: %s", key, del_exc)
            else:
                return JSONResponse(cached_data)

    try:
        result = graph.invoke({"pr_url": request.pr_url})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Graph execution failed: %s", exc)
        raise HTTPException(status_code=500, detail="Pipeline execution failed.") from exc

    response_data = {
        "pr_url": request.pr_url,
        "security_report": result.get("security_report"),
        "perf_report": result.get("perf_report"),
        "coverage_report": result.get("coverage_report"),
        "final_comment": result.get("final_comment"),
    }

    # Store in cache
    if cache:
        try:
            cache.setex(key, _CACHE_TTL_SECONDS, json.dumps(response_data))
        except Exception as exc:
            logger.warning("Cache write failed: %s", exc)

    return JSONResponse(response_data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
