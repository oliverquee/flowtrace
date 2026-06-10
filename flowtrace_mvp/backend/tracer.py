"""Runtime tracing for the local FlowTrace MVP.

MVP definition:
- Arrow/edge value = variables that changed between two executed user-code lines.
- We trace only one pasted Python code string.
- This is local-only. It is not a safe server sandbox for untrusted code.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import sys
import time
import traceback
from types import FrameType
from typing import Any

from .parser import parse_source_nodes

USER_FILENAME = "<flowtrace_user_code>"


class TraceExecutionError(RuntimeError):
    """Raised when traced code fails while still preserving partial trace data."""


def safe_repr(value: Any, max_length: int = 240) -> str:
    """Return a bounded representation suitable for UI display."""

    try:
        text = repr(value)
    except Exception as exc:  # pragma: no cover - defensive only
        text = f"<unrepresentable {type(value).__name__}: {exc}>"
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


def _public_locals(frame: FrameType) -> dict[str, str]:
    """Capture user-facing local variables only."""

    hidden_names = {"__builtins__", "__name__", "__file__", "__package__", "__cached__"}
    captured: dict[str, str] = {}
    for name, value in frame.f_locals.items():
        if name.startswith("__") or name in hidden_names:
            continue
        captured[name] = safe_repr(value)
    return captured


def _changed_vars(before: dict[str, str], after: dict[str, str]) -> dict[str, str]:
    """Return variables whose display value changed or appeared."""

    return {name: value for name, value in after.items() if before.get(name) != value}


def _edge_id(from_line: int, to_line: int, index: int) -> str:
    return f"edge_{from_line}_{to_line}_{index}"


def trace_code(source: str, timeout_seconds: float | None = None) -> dict:
    """Execute source and return nodes, runtime edges, and trace events.

    The trace event for transition A -> B contains values produced by A and
    visible before B executes. This matches Python's line-trace semantics.
    """

    nodes = parse_source_nodes(source)
    node_by_line = {node["line"]: {**node} for node in nodes}
    stdout_buffer = io.StringIO()
    events: list[dict] = []
    edges: list[dict] = []

    previous_line: int | None = None
    previous_snapshot: dict[str, str] = {}
    event_index = 0
    execution_error: dict | None = None
    deadline = time.monotonic() + timeout_seconds if timeout_seconds is not None else None

    def add_transition(from_line: int, to_line: int, frame: FrameType) -> None:
        nonlocal previous_snapshot, event_index
        current_snapshot = _public_locals(frame)
        changed = _changed_vars(previous_snapshot, current_snapshot)
        event = {
            "event_id": event_index,
            "from_line": from_line,
            "to_line": to_line,
            "changed_vars": changed,
            "stdout": stdout_buffer.getvalue(),
            "locals_snapshot": current_snapshot,
        }
        events.append(event)
        edges.append(
            {
                "id": _edge_id(from_line, to_line, event_index),
                "source": f"line_{from_line}",
                "target": f"line_{to_line}",
                "from_line": from_line,
                "to_line": to_line,
                "changed_vars": changed,
                "event_id": event_index,
            }
        )
        previous_snapshot = current_snapshot
        event_index += 1

    def tracer(frame: FrameType, event: str, arg: Any):
        nonlocal previous_line, previous_snapshot, execution_error

        if frame.f_code.co_filename != USER_FILENAME:
            return tracer

        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError(f"Execution timed out after {timeout_seconds:g} seconds.")

        if event == "line":
            current_line = frame.f_lineno
            if current_line in node_by_line:
                node_by_line[current_line]["executed"] = True
            if previous_line is None:
                previous_line = current_line
                previous_snapshot = _public_locals(frame)
                return tracer
            add_transition(previous_line, current_line, frame)
            previous_line = current_line
            return tracer

        if event == "exception":
            exc_type, exc_value, _tb = arg
            execution_error = {
                "line": frame.f_lineno,
                "type": getattr(exc_type, "__name__", str(exc_type)),
                "message": str(exc_value),
            }
            return tracer

        if event == "return" and previous_line is not None:
            # Capture final changes produced by the last executed line.
            final_snapshot = _public_locals(frame)
            changed = _changed_vars(previous_snapshot, final_snapshot)
            if changed:
                event_payload = {
                    "event_id": event_index,
                    "from_line": previous_line,
                    "to_line": previous_line,
                    "changed_vars": changed,
                    "stdout": stdout_buffer.getvalue(),
                    "locals_snapshot": final_snapshot,
                    "terminal": True,
                }
                events.append(event_payload)
                edges.append(
                    {
                        "id": _edge_id(previous_line, previous_line, event_index),
                        "source": f"line_{previous_line}",
                        "target": f"line_{previous_line}",
                        "from_line": previous_line,
                        "to_line": previous_line,
                        "changed_vars": changed,
                        "event_id": event_index,
                        "terminal": True,
                    }
                )
            return tracer

        return tracer

    globals_dict = {
        "__name__": "__main__",
        "__builtins__": builtins.__dict__,
    }

    try:
        compiled = compile(source, USER_FILENAME, "exec")
        with contextlib.redirect_stdout(stdout_buffer):
            sys.settrace(tracer)
            try:
                exec(compiled, globals_dict, globals_dict)
            finally:
                sys.settrace(None)
    except Exception as exc:  # keep partial trace useful
        if execution_error is None:
            execution_error = {"type": type(exc).__name__, "message": str(exc), "line": None}
        execution_error["traceback"] = traceback.format_exc(limit=4)

    executed_lines = {event["from_line"] for event in events} | {event["to_line"] for event in events}
    for line in executed_lines:
        if line in node_by_line:
            node_by_line[line]["executed"] = True

    return {
        "nodes": [node_by_line[node["line"]] for node in nodes],
        "edges": edges,
        "trace_events": events,
        "stdout": stdout_buffer.getvalue(),
        "error": execution_error,
    }
