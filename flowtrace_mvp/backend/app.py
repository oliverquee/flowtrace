"""FastAPI app for the local FlowTrace MVP.

Run from repo root:
    python -m uvicorn flowtrace_mvp.backend.app:app --reload

Then open:
    http://127.0.0.1:8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .graph_builder import build_graph_model
from .runner import run_trace_subprocess

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = BASE_DIR / "samples"

app = FastAPI(title="FlowTrace MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TraceRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50_000)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Return the local MVP page."""
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/sample")
def sample() -> dict[str, str]:
    """Return the default sample code."""
    sample_path = SAMPLES_DIR / "simple_assignment.py"
    return {"code": sample_path.read_text(encoding="utf-8")}


@app.post("/api/trace")
def trace(request: TraceRequest) -> dict:
    """Trace pasted code through the subprocess runner."""
    return run_trace_subprocess(request.code)


@app.post("/api/graph")
def graph(request: TraceRequest) -> dict:
    """Return a GraphModel built from the subprocess trace result."""
    result = run_trace_subprocess(request.code)
    graph_model = build_graph_model(request.code, result.get("trace_events", []))
    return {
        "graph": graph_model,
        "stdout": result.get("stdout", ""),
        "error": result.get("error"),
    }
