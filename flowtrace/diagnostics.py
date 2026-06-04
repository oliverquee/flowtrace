"""Diagnostics derived from static and runtime analysis."""

from __future__ import annotations

from dataclasses import dataclass, field

from .runtime_tracer import RuntimeTraceResult
from .static_analyzer import AssignmentRecord, ImportRecord, SideEffectRecord, StaticAnalysisResult


@dataclass
class DiagnosticsResult:
    functions_defined_but_not_executed: list[str] = field(default_factory=list)
    imports_unused: list[ImportRecord] = field(default_factory=list)
    assigned_variables_never_read: list[AssignmentRecord] = field(default_factory=list)
    side_effect_calls: list[SideEffectRecord] = field(default_factory=list)
    functions_with_no_runtime_callers: list[str] = field(default_factory=list)
    runtime_error_path: list[dict[str, str | int | None]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "functions_defined_but_not_executed": self.functions_defined_but_not_executed,
            "imports_unused": [item.__dict__ for item in self.imports_unused],
            "assigned_variables_never_read": [item.__dict__ for item in self.assigned_variables_never_read],
            "side_effect_calls": [item.__dict__ for item in self.side_effect_calls],
            "functions_with_no_runtime_callers": self.functions_with_no_runtime_callers,
            "runtime_error_path": self.runtime_error_path,
        }


def build_diagnostics(
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
) -> DiagnosticsResult:
    executed_functions = {
        event.function for event in runtime_result.events if event.event == "function_enter"
    }
    incoming_runtime_callers = {
        event.function
        for event in runtime_result.events
        if event.event == "function_enter" and event.caller is not None
    }
    read_names_by_file = _read_names_by_file(static_result)
    read_names_by_scope = _read_names_by_scope(static_result)

    return DiagnosticsResult(
        functions_defined_but_not_executed=[
            function.id for function in static_result.functions if function.id not in executed_functions
        ],
        imports_unused=[
            item
            for item in static_result.imports
            if item.used_name not in read_names_by_file.get(item.file, set())
        ],
        assigned_variables_never_read=[
            item
            for item in static_result.assignments
            if item.name not in read_names_by_scope.get(_scope_key(item.file, item.in_function), set())
        ],
        side_effect_calls=static_result.side_effects,
        functions_with_no_runtime_callers=sorted(executed_functions - incoming_runtime_callers),
        runtime_error_path=[
            {
                "function": event.function,
                "file": event.file,
                "line": event.line,
                "error_type": event.error_type,
                "error_message": event.error_message,
            }
            for event in runtime_result.errors
        ],
    )


def _read_names_by_file(static_result: StaticAnalysisResult) -> dict[str, set[str]]:
    reads: dict[str, set[str]] = {}
    for item in static_result.variable_reads:
        reads.setdefault(item.file, set()).add(item.name)
    return reads


def _read_names_by_scope(static_result: StaticAnalysisResult) -> dict[tuple[str, str | None], set[str]]:
    reads: dict[tuple[str, str | None], set[str]] = {}
    for item in static_result.variable_reads:
        reads.setdefault(_scope_key(item.file, item.in_function), set()).add(item.name)
    return reads


def _scope_key(file: str, in_function: str | None) -> tuple[str, str | None]:
    return (file, in_function)
