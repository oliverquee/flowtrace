"""Subprocess runner for local MVP code execution."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

from .parser import parse_source_nodes
from .tracer import trace_code

DEFAULT_TIMEOUT_SECONDS = 5.0


def run_trace_subprocess(source: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run tracing in a separate Python process and return the trace response."""

    command = [sys.executable, "-m", "flowtrace_mvp.backend.runner", "--child"]
    payload = json.dumps({"code": source, "timeout_seconds": timeout_seconds})

    try:
        completed = subprocess.run(
            command,
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _timeout_response(source, timeout_seconds, exc)

    if completed.returncode != 0:
        return _subprocess_error_response(source, completed)

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _invalid_response_error(source, completed)

    if completed.stderr:
        error = result.get("error")
        if isinstance(error, dict):
            error.setdefault("stderr", completed.stderr)
    return result


def _timeout_response(source: str, timeout_seconds: float, exc: subprocess.TimeoutExpired) -> dict[str, Any]:
    return {
        "nodes": parse_source_nodes(source),
        "edges": [],
        "trace_events": [],
        "stdout": exc.stdout or "",
        "error": {
            "type": "TimeoutError",
            "message": f"Execution timed out after {timeout_seconds:g} seconds.",
            "line": None,
            "stderr": exc.stderr or "",
        },
    }


def _subprocess_error_response(source: str, completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "nodes": _parse_nodes_or_empty(source),
        "edges": [],
        "trace_events": [],
        "stdout": completed.stdout,
        "error": {
            "type": "SubprocessError",
            "message": f"Trace subprocess exited with code {completed.returncode}.",
            "line": None,
            "stderr": completed.stderr,
        },
    }


def _invalid_response_error(source: str, completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "nodes": _parse_nodes_or_empty(source),
        "edges": [],
        "trace_events": [],
        "stdout": completed.stdout,
        "error": {
            "type": "SubprocessProtocolError",
            "message": "Trace subprocess did not return valid JSON.",
            "line": None,
            "stderr": completed.stderr,
        },
    }


def _parse_nodes_or_empty(source: str) -> list[dict[str, Any]]:
    try:
        return parse_source_nodes(source)
    except SyntaxError:
        return []


def _child_main() -> int:
    request = json.loads(sys.stdin.read())
    source = str(request.get("code", ""))
    timeout_seconds = float(request.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    try:
        result = trace_code(source, timeout_seconds=timeout_seconds)
    except SyntaxError as exc:
        result = {
            "nodes": [],
            "edges": [],
            "trace_events": [],
            "stdout": "",
            "error": {"type": "SyntaxError", "message": str(exc), "line": exc.lineno},
        }
    sys.stdout.write(json.dumps(result))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if args.child:
        return _child_main()
    parser.error("runner.py is intended to be launched with --child")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
