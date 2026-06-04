"""Write FlowTrace output files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .diagnostics import DiagnosticsResult
from .intended_flow import IntendedFlowComparison
from .runtime_tracer import RuntimeTraceResult
from .static_analyzer import StaticAnalysisResult
from .utils import relative_path


def write_reports(
    output_dir: Path,
    entry_path: Path,
    project_root: Path,
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
    diagnostics: DiagnosticsResult,
    static_graph: dict[str, object],
    runtime_graph: dict[str, object],
    intended_comparison: IntendedFlowComparison,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    static_graph_path = output_dir / "static_graph.json"
    runtime_trace_path = output_dir / "runtime_trace.jsonl"
    runtime_graph_path = output_dir / "runtime_graph.json"
    report_path = output_dir / "report.md"
    flow_path = output_dir / "flow.mmd"

    _write_json(static_graph_path, static_graph)
    runtime_trace_path.write_text(_runtime_jsonl(runtime_result), encoding="utf-8")
    _write_json(runtime_graph_path, runtime_graph)
    report_path.write_text(
        _build_markdown_report(
            entry_path,
            project_root,
            static_result,
            runtime_result,
            diagnostics,
            flow_path,
            intended_comparison,
        ),
        encoding="utf-8",
    )
    flow_path.write_text(_build_mermaid(runtime_graph), encoding="utf-8")
    return [static_graph_path, runtime_trace_path, runtime_graph_path, report_path, flow_path]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _runtime_jsonl(runtime_result: RuntimeTraceResult) -> str:
    if runtime_result.runtime_skipped:
        return json.dumps(
            {
                "event": "runtime_skipped",
                "runtime_attempted": runtime_result.runtime_attempted,
                "runtime_skipped": runtime_result.runtime_skipped,
                "runtime_skipped_reason": runtime_result.runtime_skipped_reason,
                "completed": runtime_result.completed,
            },
            sort_keys=True,
        ) + "\n"
    return "\n".join(json.dumps(event.__dict__, sort_keys=True) for event in runtime_result.events) + "\n"


def _build_markdown_report(
    entry_path: Path,
    project_root: Path,
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
    diagnostics: DiagnosticsResult,
    flow_path: Path,
    intended_comparison: IntendedFlowComparison,
) -> str:
    executed = [event.function for event in runtime_result.events if event.event == "function_enter"]
    lines = [
        "# FlowTrace Report",
        "",
        "## 1. Project summary",
        f"- Project root: `{project_root}`",
        f"- Python files scanned: {len(static_result.files)}",
        f"- Functions found: {len(static_result.functions)}",
        f"- Runtime attempted: {runtime_result.runtime_attempted}",
        f"- Runtime completed: {runtime_result.completed}",
        f"- Runtime skipped: {runtime_result.runtime_skipped}",
        f"- Runtime skipped reason: {runtime_result.runtime_skipped_reason or 'None'}",
        "",
        "## 2. Entry file",
        f"- `{relative_path(entry_path, project_root)}`",
        "",
        "## 3. Files scanned",
        *_items(file.path for file in static_result.files),
        "",
        "## 4. Imports found",
        *_items(_format_import(item) for item in static_result.imports),
        "",
        "## 5. Functions found",
        *_items(f"{item.id}({', '.join(item.args)}) at {item.file}:{item.line}" for item in static_result.functions),
        "",
        "## 6. Functions executed",
        *_items(dict.fromkeys(executed).keys()),
        "",
        "## 7. Functions defined but not executed",
        *_items(diagnostics.functions_defined_but_not_executed),
        "",
        "## 8. Assigned variables never read",
        *_items(
            f"{item.name} at {item.file}:{item.line} in {_scope_label(item.in_function)}"
            for item in diagnostics.assigned_variables_never_read
        ),
        "",
        "## 9. Side-effect calls",
        *_items(
            f"{item.category}: {item.call} at {item.file}:{item.line}"
            for item in diagnostics.side_effect_calls
        ),
        "",
        "## 10. Runtime call order",
        "- Synthetic root: `PROGRAM_START`",
        *_items(f"{index}. {name}" for index, name in enumerate(executed, start=1)),
        "",
        "## 11. Runtime errors",
        *_runtime_error_items(diagnostics.runtime_error_path),
        "",
        "## 12. Mermaid diagram location",
        f"- `{flow_path}`",
        "",
        "## 13. Intended flow comparison",
        f"- Name: `{intended_comparison.name or 'None'}`",
        "- Expected order:",
        *_items(intended_comparison.expected_runtime_order),
        "- Actual order:",
        *_items(intended_comparison.actual_runtime_order),
        "- Missing expected functions:",
        *_items(intended_comparison.missing_expected_functions),
        "- Unexpected actual functions:",
        *_items(intended_comparison.unexpected_actual_functions),
        f"- Order mismatch summary: {intended_comparison.order_mismatch_summary}",
        "",
    ]
    return "\n".join(lines)


def _build_mermaid(runtime_graph: dict[str, object]) -> str:
    lines = ["flowchart TD"]
    edges = runtime_graph.get("edges", [])
    if not edges:
        nodes = runtime_graph.get("nodes", [])
        if not nodes:
            return "flowchart TD\n  empty[\"No runtime calls captured\"]\n"
        for node in nodes:
            node_id = _mermaid_id(node["id"])
            lines.append(f"  {node_id}[\"{node['id']}\"]")
        return "\n".join(lines) + "\n"

    for edge in edges:
        caller_id = _mermaid_id(edge["caller"])
        callee_id = _mermaid_id(edge["callee"])
        lines.append(f"  {caller_id}[\"{edge['caller']}\"] --> {callee_id}[\"{edge['callee']}\"]")
    return "\n".join(lines) + "\n"


def _format_import(item: Any) -> str:
    alias = f" as {item.alias}" if item.alias else ""
    module_prefix = "" if item.module == item.name else f"{item.module}." if item.module else ""
    return f"{module_prefix}{item.name}{alias} at {item.file}:{item.line}"


def _items(values: Any) -> list[str]:
    items = list(values)
    if not items:
        return ["- None"]
    return [f"- {item}" for item in items]


def _runtime_error_items(errors: list[dict[str, str | int | None]]) -> list[str]:
    if not errors:
        return ["- None"]

    grouped: dict[tuple[str | None, str | None], list[dict[str, str | int | None]]] = {}
    for error in errors:
        key = (error.get("error_type"), error.get("error_message"))
        grouped.setdefault(key, []).append(error)

    lines: list[str] = []
    for (error_type, error_message), group in grouped.items():
        lines.append(f"- {_error_label(error_type)}: {error_type}: {error_message} ({len(group)} occurrence(s))")
        for item in group:
            lines.append(f"-   at {item['function']} in {item['file']}:{item['line']}")
        hint = _error_hint(error_type)
        if hint:
            lines.append(f"-   Hint: {hint}")
    return lines


def _error_label(error_type: str | None) -> str:
    if error_type in {"ModuleNotFoundError", "ImportError"}:
        return "Dependency/import error"
    if error_type == "KeyboardInterrupt":
        return "Runtime interrupted"
    return "Runtime error"


def _error_hint(error_type: str | None) -> str | None:
    if error_type in {"ModuleNotFoundError", "ImportError"}:
        return "Install the missing package in the Python environment used to run FlowTrace."
    if error_type == "KeyboardInterrupt":
        return "Target program may have waited for input/auth or was manually stopped."
    return None


def _mermaid_id(value: str) -> str:
    return "n_" + "".join(character if character.isalnum() else "_" for character in value)


def _scope_label(in_function: str | None) -> str:
    return in_function or "<module>"
