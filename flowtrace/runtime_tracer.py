"""Runtime tracing for FlowTrace."""

from __future__ import annotations

import runpy
import shlex
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any

from .utils import flowtrace_source_root, function_id, is_relative_to, relative_path


@dataclass(frozen=True)
class RuntimeEvent:
    event: str
    function: str
    file: str
    line: int
    caller: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    timestamp: float = 0.0
    changed_vars: dict[str, dict[str, str | None]] | None = None

    def __getattribute__(self, name: str) -> Any:
        if name == "__dict__":
            data = object.__getattribute__(self, name).copy()
            if data.get("changed_vars") is None:
                data.pop("changed_vars", None)
            return data
        return object.__getattribute__(self, name)


@dataclass
class RuntimeTraceResult:
    entry: str
    project_root: str
    events: list[RuntimeEvent] = field(default_factory=list)
    errors: list[RuntimeEvent] = field(default_factory=list)
    runtime_attempted: bool = True
    runtime_skipped: bool = False
    runtime_skipped_reason: str | None = None
    target_args: list[str] = field(default_factory=list)
    completed: bool = True


def skipped_runtime_result(
    entry_path: Path,
    project_root: Path,
    reason: str,
    target_args: list[str] | None = None,
) -> RuntimeTraceResult:
    return RuntimeTraceResult(
        entry=str(entry_path),
        project_root=str(project_root),
        runtime_attempted=False,
        runtime_skipped=True,
        runtime_skipped_reason=reason,
        target_args=target_args or [],
        completed=False,
    )


def run_with_trace(
    entry_path: Path,
    project_root: Path,
    target_args: list[str] | None = None,
    capture_variables: bool = False,
) -> RuntimeTraceResult:
    parsed_target_args = target_args or []
    result = RuntimeTraceResult(
        entry=str(entry_path),
        project_root=str(project_root),
        target_args=parsed_target_args,
    )
    previous_trace = sys.gettrace()
    previous_argv = sys.argv[:]
    previous_path = sys.path[:]
    call_stack: list[str] = []
    variable_snapshots: dict[int, dict[str, str]] = {}
    target_is_flowtrace = is_relative_to(entry_path, flowtrace_source_root())

    def tracer(frame: FrameType, event: str, arg: Any) -> Any:
        frame_path = Path(frame.f_code.co_filename).resolve()
        if not _should_trace(frame_path, project_root, target_is_flowtrace):
            return tracer

        function_name = function_id(frame_path, project_root, _qualname(frame))
        file_name = relative_path(frame_path, project_root)

        if event == "call":
            caller = call_stack[-1] if call_stack else None
            call_stack.append(function_name)
            if capture_variables:
                variable_snapshots[id(frame)] = {}
            result.events.append(
                RuntimeEvent(
                    event="function_enter",
                    function=function_name,
                    file=file_name,
                    line=frame.f_lineno,
                    caller=caller,
                    timestamp=time.time(),
                )
            )
        elif event == "line":
            if capture_variables:
                changed_vars = _changed_locals(frame, variable_snapshots.get(id(frame), {}))
                variable_snapshots[id(frame)] = _locals_snapshot(frame)
                if changed_vars:
                    result.events.append(
                        RuntimeEvent(
                            event="variable_change",
                            function=function_name,
                            file=file_name,
                            line=frame.f_lineno,
                            timestamp=time.time(),
                            changed_vars=changed_vars,
                        )
                    )
        elif event == "return":
            result.events.append(
                RuntimeEvent(
                    event="function_exit",
                    function=function_name,
                    file=file_name,
                    line=frame.f_lineno,
                    caller=call_stack[-2] if len(call_stack) > 1 else None,
                    timestamp=time.time(),
                )
            )
            if call_stack and call_stack[-1] == function_name:
                call_stack.pop()
            variable_snapshots.pop(id(frame), None)
        elif event == "exception":
            exc_type, exc_value, _traceback = arg
            variable_snapshots.pop(id(frame), None)
            error_event = RuntimeEvent(
                event="function_error",
                function=function_name,
                file=file_name,
                line=frame.f_lineno,
                caller=call_stack[-2] if len(call_stack) > 1 else None,
                error_type=getattr(exc_type, "__name__", str(exc_type)),
                error_message=str(exc_value),
                timestamp=time.time(),
            )
            result.events.append(error_event)
            result.errors.append(error_event)
        return tracer

    try:
        sys.path = [str(entry_path.parent), str(project_root), *previous_path]
        sys.argv = [str(entry_path), *parsed_target_args]
        sys.settrace(tracer)
        runpy.run_path(str(entry_path), run_name="__main__")
    except BaseException as exc:
        result.completed = False
        if not result.errors:
            result.errors.append(
                RuntimeEvent(
                    event="function_error",
                    function="<module>",
                    file=relative_path(entry_path, project_root),
                    line=0,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    timestamp=time.time(),
                )
            )
    finally:
        sys.settrace(previous_trace)
        sys.argv = previous_argv
        sys.path = previous_path
    return result


def _should_trace(path: Path, project_root: Path, target_is_flowtrace: bool) -> bool:
    if not is_relative_to(path, project_root):
        return False
    if any(part in {".venv", "venv", "env", "site-packages", "__pycache__"} for part in path.parts):
        return False
    if not target_is_flowtrace and is_relative_to(path, flowtrace_source_root()):
        return False
    return True


def _qualname(frame: FrameType) -> str:
    return getattr(frame.f_code, "co_qualname", frame.f_code.co_name)


def _changed_locals(frame: FrameType, previous: dict[str, str]) -> dict[str, dict[str, str | None]]:
    changed: dict[str, dict[str, str | None]] = {}
    current = _locals_snapshot(frame)
    for name, after_value in current.items():
        before_value = previous.get(name)
        if name not in previous or before_value != after_value:
            if _is_sensitive_name(name):
                changed[name] = {"before": "<redacted>", "after": "<redacted>"}
            else:
                changed[name] = {"before": before_value, "after": after_value}
    return changed


def _locals_snapshot(frame: FrameType) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for name, value in frame.f_locals.items():
        if name.startswith("__"):
            continue
        snapshot[name] = "<redacted>" if _is_sensitive_name(name) else _safe_repr(value)
    return snapshot


def _is_sensitive_name(name: str) -> bool:
    sensitive_terms = {
        "password",
        "passwd",
        "secret",
        "token",
        "apikey",
        "api_key",
        "credential",
        "auth",
        "private_key",
    }
    lowered = name.lower()
    return any(term in lowered for term in sensitive_terms)


def _safe_repr(value: object) -> str:
    try:
        text = repr(value)
    except Exception:
        return "<unrepresentable>"
    if len(text) > 200:
        return text[:197] + "..."
    return text


def target_args_display(target_args: list[str]) -> str:
    if not target_args:
        return "None"
    return " ".join(shlex.quote(arg) for arg in target_args)
