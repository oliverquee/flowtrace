"""Build serializable static and runtime graphs."""

from __future__ import annotations

from .diagnostics import DiagnosticsResult
from .runtime_tracer import RuntimeTraceResult, target_args_display
from .static_analyzer import StaticAnalysisResult


PROGRAM_START = "PROGRAM_START"
RUNTIME_SKIPPED = "RUNTIME_SKIPPED"


def build_static_graph(static_result: StaticAnalysisResult, diagnostics: DiagnosticsResult) -> dict[str, object]:
    return {
        "project_root": static_result.project_root,
        "files": [file.path for file in static_result.files],
        "imports": [item.__dict__ for item in static_result.imports],
        "functions": [item.__dict__ for item in static_result.functions],
        "calls": [item.__dict__ for item in static_result.calls],
        "assignments": [item.__dict__ for item in static_result.assignments],
        "variable_reads": [item.__dict__ for item in static_result.variable_reads],
        "returns": [item.__dict__ for item in static_result.returns],
        "side_effects": [item.__dict__ for item in static_result.side_effects],
        "diagnostics": diagnostics.to_dict(),
    }


def build_runtime_graph(runtime_result: RuntimeTraceResult) -> dict[str, object]:
    nodes: dict[str, dict[str, str]] = {
        PROGRAM_START: {"id": PROGRAM_START, "file": "", "kind": "synthetic"}
    }
    edges: dict[tuple[str, str], int] = {}
    call_order: list[str] = []

    if runtime_result.runtime_skipped:
        nodes[RUNTIME_SKIPPED] = {
            "id": RUNTIME_SKIPPED,
            "file": "",
            "kind": "status",
            "reason": runtime_result.runtime_skipped_reason or "",
        }
        edges[(PROGRAM_START, RUNTIME_SKIPPED)] = 1

    for event in runtime_result.events:
        nodes[event.function] = {"id": event.function, "file": event.file}
        if event.event == "function_enter":
            call_order.append(event.function)
            caller = event.caller or PROGRAM_START
            nodes.setdefault(caller, {"id": caller, "file": ""})
            edge_key = (caller, event.function)
            edges[edge_key] = edges.get(edge_key, 0) + 1

    return {
        "entry": runtime_result.entry,
        "project_root": runtime_result.project_root,
        "runtime_attempted": runtime_result.runtime_attempted,
        "runtime_skipped": runtime_result.runtime_skipped,
        "runtime_skipped_reason": runtime_result.runtime_skipped_reason,
        "target_args": runtime_result.target_args,
        "target_args_display": target_args_display(runtime_result.target_args),
        "completed": runtime_result.completed,
        "nodes": list(nodes.values()),
        "edges": [
            {"caller": caller, "callee": callee, "count": count}
            for (caller, callee), count in sorted(edges.items())
        ],
        "call_order": call_order,
        "errors": [event.__dict__ for event in runtime_result.errors],
    }
