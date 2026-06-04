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


def run_with_trace(entry_path: Path, project_root: Path, target_args: list[str] | None = None) -> RuntimeTraceResult:
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
        elif event == "exception":
            exc_type, exc_value, _traceback = arg
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


def target_args_display(target_args: list[str]) -> str:
    if not target_args:
        return "None"
    return " ".join(shlex.quote(arg) for arg in target_args)
