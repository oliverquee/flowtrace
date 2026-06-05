"""Write FlowTrace output files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .comparison import StaticRuntimeComparison, StaticCallNotObserved, RiskyUnexecutedFunction
from .diagnostics import DiagnosticsResult
from .html_report_writer import write_html_report
from .intended_flow import IntendedFlowComparison
from .node_details import build_node_details
from .runtime_tracer import RuntimeTraceResult, target_args_display
from .static_analyzer import SideEffectRecord, StaticAnalysisResult
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
    static_runtime_comparison: StaticRuntimeComparison,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    static_graph_path = output_dir / "static_graph.json"
    runtime_trace_path = output_dir / "runtime_trace.jsonl"
    runtime_graph_path = output_dir / "runtime_graph.json"
    report_path = output_dir / "report.md"
    html_report_path = output_dir / "report.html"
    flow_path = output_dir / "flow.mmd"
    node_details_path = output_dir / "node_details.json"
    node_details = build_node_details(
        static_result=static_result,
        runtime_result=runtime_result,
        runtime_graph=runtime_graph,
        diagnostics=diagnostics,
        intended_comparison=intended_comparison,
    )

    _write_json(static_graph_path, static_graph)
    runtime_trace_path.write_text(_runtime_jsonl(runtime_result), encoding="utf-8")
    _write_json(runtime_graph_path, runtime_graph)
    _write_json(node_details_path, node_details)
    report_path.write_text(
        _build_markdown_report(
            entry_path,
            project_root,
            static_result,
            runtime_result,
            diagnostics,
            flow_path,
            intended_comparison,
            static_runtime_comparison,
        ),
        encoding="utf-8",
    )
    write_html_report(
        path=html_report_path,
        entry_path=entry_path,
        project_root=project_root,
        static_result=static_result,
        runtime_result=runtime_result,
        diagnostics=diagnostics,
        flow_path=flow_path,
        node_details_path=node_details_path,
        node_details=node_details,
        runtime_graph=runtime_graph,
        intended_comparison=intended_comparison,
        static_runtime_comparison=static_runtime_comparison,
    )
    flow_path.write_text(_build_mermaid(runtime_graph), encoding="utf-8")
    return [static_graph_path, runtime_trace_path, runtime_graph_path, node_details_path, report_path, flow_path, html_report_path]


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
                "target_args": runtime_result.target_args,
                "target_args_display": target_args_display(runtime_result.target_args),
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
    static_runtime_comparison: StaticRuntimeComparison,
) -> str:
    executed = [event.function for event in runtime_result.events if event.event == "function_enter"]
    risk_groups = _side_effects_by_risk(diagnostics.side_effect_calls)
    top_risks = _top_risk_items(risk_groups)
    lines = [
        "# FlowTrace Report",
        "",
        "## 1. Executive summary",
        f"- Project root: `{project_root}`",
        f"- Entry file: `{relative_path(entry_path, project_root)}`",
        f"- Python files scanned: {len(static_result.files)}",
        f"- Functions found: {len(static_result.functions)}",
        f"- Runtime attempted: {runtime_result.runtime_attempted}",
        f"- Runtime completed: {runtime_result.completed}",
        f"- Runtime skipped: {runtime_result.runtime_skipped}",
        f"- Target args: {_target_args_label(runtime_result.target_args)}",
        f"- Target args display: `{target_args_display(runtime_result.target_args)}`",
        f"- Runtime error count: {len(diagnostics.runtime_error_path)}",
        f"- High-risk side effect count: {len(risk_groups['high'])}",
        f"- Medium-risk side effect count: {len(risk_groups['medium'])}",
        f"- Low-risk side effect count: {len(risk_groups['low'])}",
        f"- Defined-but-not-executed function count: {_defined_not_executed_count_label(runtime_result, diagnostics)}",
        f"- Assigned-but-unread variable count: {len(diagnostics.assigned_variables_never_read)}",
        f"- Executed static function count: {len(static_runtime_comparison.executed_static_functions)}",
        f"- Static-only comparison unavailable: {static_runtime_comparison.comparison_unavailable}",
        f"- Risky unexecuted function count: {len(static_runtime_comparison.risky_unexecuted_functions)}",
        f"- Runtime functions without static definition count: {len(static_runtime_comparison.runtime_functions_without_static_definition)}",
        "",
        "## 2. Recommended next checks",
        *_recommended_next_checks(runtime_result, risk_groups, static_runtime_comparison),
        "",
        "## 3. Project summary",
        f"- Project root: `{project_root}`",
        f"- Runtime attempted: {runtime_result.runtime_attempted}",
        f"- Runtime completed: {runtime_result.completed}",
        f"- Runtime skipped: {runtime_result.runtime_skipped}",
        f"- Runtime skipped reason: {runtime_result.runtime_skipped_reason or 'None'}",
        f"- Target args: {_target_args_label(runtime_result.target_args)}",
        f"- Target args display: `{target_args_display(runtime_result.target_args)}`",
        *_runtime_argument_warnings(runtime_result),
        "",
        "## 4. Top risks",
        *_items(_format_side_effect(item) for item in top_risks),
        "",
        "## 5. Static vs runtime comparison",
        *_comparison_summary_items(static_runtime_comparison),
        "",
        "### Executed static functions",
        *_comparison_items(static_runtime_comparison.executed_static_functions, static_runtime_comparison),
        "",
        "### Static functions not executed",
        *_comparison_items(static_runtime_comparison.static_functions_not_executed, static_runtime_comparison),
        "",
        "### Runtime functions without static definition",
        *_comparison_items(
            static_runtime_comparison.runtime_functions_without_static_definition,
            static_runtime_comparison,
        ),
        "",
        "### Risky unexecuted functions",
        *_risky_unexecuted_function_items(static_runtime_comparison.risky_unexecuted_functions),
        "",
        "### Static resolved calls not observed",
        *_static_call_not_observed_items(static_runtime_comparison.static_resolved_calls_not_observed),
        "",
        "## 6. High-risk side effects",
        *_items(_format_side_effect(item) for item in risk_groups["high"]),
        "",
        "## 7. Medium-risk side effects",
        *_items(_format_side_effect(item) for item in risk_groups["medium"]),
        "",
        "## 8. Low-risk side effects",
        *_items(_filtered_low_risk_side_effects(risk_groups["low"])),
        "",
        "## 9. Runtime errors",
        *_runtime_error_items(diagnostics.runtime_error_path),
        "",
        "## 10. Runtime call order",
        "- Synthetic root: `PROGRAM_START`",
        *_items(f"{index}. {name}" for index, name in enumerate(executed, start=1)),
        "",
        "## 11. Intended flow comparison",
        *_intended_flow_items(intended_comparison),
        "",
        "## 12. Legacy unexecuted function diagnostics",
        "- Prefer `## 5. Static vs runtime comparison` for detailed execution comparison.",
        f"- Count: {_defined_not_executed_count_label(runtime_result, diagnostics)}",
        *_defined_not_executed_items(runtime_result, diagnostics, details=False),
        "",
        "## 13. Assigned variables never read",
        *_items(
            f"{item.name} at {item.file}:{item.line} in {_scope_label(item.in_function)}"
            for item in diagnostics.assigned_variables_never_read
        ),
        "",
        "## 14. Entry file",
        f"- `{relative_path(entry_path, project_root)}`",
        "",
        "## 15. Files scanned",
        *_items(file.path for file in static_result.files),
        "",
        "## 16. Imports found",
        *_items(_format_import(item) for item in static_result.imports),
        "",
        "## 17. Functions found",
        *_items(f"{item.id}({', '.join(item.args)}) at {item.file}:{item.line}" for item in static_result.functions),
        "",
        "## 18. Functions executed",
        *_items(dict.fromkeys(executed).keys()),
        "",
        "## 19. Mermaid diagram location",
        f"- `{flow_path}`",
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


def _target_args_label(target_args: list[str]) -> str:
    return "None" if not target_args else repr(target_args)


def _runtime_argument_warnings(runtime_result: RuntimeTraceResult) -> list[str]:
    if runtime_result.runtime_attempted and not runtime_result.target_args:
        return [
            "- Warning: Runtime was attempted without target args. For CLI-style projects, this may only trace startup/import/parser setup."
        ]
    return []


def _recommended_next_checks(
    runtime_result: RuntimeTraceResult,
    risk_groups: dict[str, list[SideEffectRecord]],
    comparison: StaticRuntimeComparison,
) -> list[str]:
    checks: list[str] = []
    if risk_groups["high"]:
        checks.append("- Review high-risk side effects before runtime execution.")
    if runtime_result.runtime_skipped:
        checks.append("- Static-only mode was a safe first pass; runtime comparison is unavailable because runtime was skipped.")
        checks.append("- Review top risks before using runtime mode.")
    if runtime_result.runtime_attempted and not runtime_result.completed:
        checks.append("- Check runtime errors and the partial static-vs-runtime comparison.")
    if runtime_result.runtime_attempted and not runtime_result.target_args:
        checks.append("- Pass `--target-args` for CLI-style projects to trace the intended command path.")
    if comparison.risky_unexecuted_functions:
        checks.append("- Review risky unexecuted functions in the static-vs-runtime comparison.")
    if not checks:
        checks.append("- No immediate high-priority checks found.")
    return checks


def _defined_not_executed_count_label(
    runtime_result: RuntimeTraceResult,
    diagnostics: DiagnosticsResult,
) -> str:
    if runtime_result.runtime_skipped:
        return "N/A (runtime skipped)"
    return str(len(diagnostics.functions_defined_but_not_executed))


def _defined_not_executed_items(
    runtime_result: RuntimeTraceResult,
    diagnostics: DiagnosticsResult,
    details: bool = True,
) -> list[str]:
    if runtime_result.runtime_skipped:
        return ["- Runtime was skipped, so unexecuted-function diagnostics are unavailable."]
    if not details:
        return ["- Detailed list omitted here to avoid duplication."]
    return _items(diagnostics.functions_defined_but_not_executed)


def _comparison_summary_items(comparison: StaticRuntimeComparison) -> list[str]:
    lines = [
        f"- Static functions found count: {len(comparison.static_functions)}",
        f"- Runtime functions observed count: {len(comparison.runtime_functions)}",
        f"- Executed static functions count: {len(comparison.executed_static_functions)}",
        f"- Static functions not executed count: {len(comparison.static_functions_not_executed)}",
        f"- Runtime functions without static definition count: {len(comparison.runtime_functions_without_static_definition)}",
        f"- Risky unexecuted functions count: {len(comparison.risky_unexecuted_functions)}",
        f"- Static resolved calls not observed count: {len(comparison.static_resolved_calls_not_observed)}",
    ]
    if comparison.comparison_unavailable_reason:
        lines.append(f"- {comparison.comparison_unavailable_reason}")
    if comparison.partial_runtime:
        lines.append("- Runtime did not complete, so comparison is based on partial runtime trace.")
    return lines


def _comparison_items(items: list[str], comparison: StaticRuntimeComparison) -> list[str]:
    if comparison.comparison_unavailable:
        return ["- Runtime was skipped, so execution comparison is unavailable."]
    return _items(items)


def _risky_unexecuted_function_items(items: list[RiskyUnexecutedFunction]) -> list[str]:
    if not items:
        return ["- None"]
    lines: list[str] = []
    for item in items:
        lines.append(f"- {item.function_id} at {item.file}:{item.line}")
        for side_effect in item.side_effects:
            lines.append(
                f"-   {side_effect.category}/{_side_effect_risk(side_effect)}/{side_effect.call}/{side_effect.file}:{side_effect.line}"
            )
    return lines


def _static_call_not_observed_items(items: list[StaticCallNotObserved]) -> list[str]:
    if not items:
        return ["- None"]
    return [
        f"- {item.caller} -> {item.callee} via `{item.call}` at {item.file}:{item.line}"
        for item in items
    ]


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


def _intended_flow_items(comparison: IntendedFlowComparison) -> list[str]:
    lines = [
        f"- Status: `{comparison.status}`",
        f"- Name: `{comparison.name or 'None'}`",
        f"- Validation result: {'ok' if comparison.validation_ok else 'failed'}",
        f"- Comparison available: {comparison.comparison_available}",
        f"- Comparison unavailable reason: {comparison.comparison_unavailable_reason or 'None'}",
        f"- Partial runtime: {comparison.partial_runtime}",
        f"- Summary: {comparison.summary}",
        f"- First mismatch index: {comparison.first_mismatch_index if comparison.first_mismatch_index is not None else 'None'}",
        *_items(["Runtime did not complete; intended-flow comparison is based on partial runtime trace."] if comparison.partial_runtime else []),
        "- Validation errors:",
        *_items(comparison.validation_errors),
        "- Expected order:",
        *_items(comparison.expected_runtime_order),
        "- Actual order:",
        *_items(comparison.actual_runtime_order),
        "- Matched functions:",
        *_items(comparison.matched_functions),
        "- Missing expected functions:",
        *_items(comparison.missing_expected_functions),
        "- Unexpected actual functions:",
        *_items(comparison.unexpected_actual_functions),
        "- Order mismatches:",
        *_items(_format_order_mismatch(item) for item in comparison.order_mismatches),
    ]
    return lines


def _format_order_mismatch(item: Any) -> str:
    if hasattr(item, "message"):
        return (
            f"expected_index={item.expected_index}, expected={item.expected_function}, "
            f"actual_index={item.actual_index}, actual={item.actual_function}, message={item.message}"
        )
    return str(item)


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


def _side_effects_by_risk(side_effects: list[SideEffectRecord]) -> dict[str, list[SideEffectRecord]]:
    groups: dict[str, list[SideEffectRecord]] = {"high": [], "medium": [], "low": []}
    for item in side_effects:
        groups[_side_effect_risk(item)].append(item)
    return groups


def _side_effect_risk(item: SideEffectRecord) -> str:
    call = item.call.lower()
    category = item.category

    if category in {"file_delete", "process"}:
        return "high"
    if any(term in call for term in ("send", "send_message", "sendmail", "create_draft", "draft")):
        return "high"
    if any(term in call for term in ("gmail", "telegram", "notify", "webhook")):
        return "high"
    if call.startswith(("requests.post", "requests.get", "httpx.", "urllib.", "socket.")):
        return "high"

    if category == "file_write":
        return "medium"
    if category == "console_output" and call == "input":
        return "medium"
    if call.endswith(".mkdir") or "makedirs" in call:
        return "medium"
    if any(term in call for term in ("db.", "database", "sqlite", "insert", "update_one", "commit")):
        return "medium"
    if any(term in call for term in ("logging.", "logger.", ".log")):
        return "medium"

    return "low"


def _top_risk_items(risk_groups: dict[str, list[SideEffectRecord]]) -> list[SideEffectRecord]:
    ordered = risk_groups["high"] + risk_groups["medium"] + risk_groups["low"]
    return ordered[:5]


def _format_side_effect(item: SideEffectRecord) -> str:
    return f"{item.category}/{_side_effect_risk(item)}/{item.call}/{item.file}:{item.line}"


def _filtered_low_risk_side_effects(items: list[SideEffectRecord]) -> list[str]:
    visible = [_format_side_effect(item) for item in items if not _is_low_value_call(item.call)]
    hidden_count = len(items) - len(visible)
    if hidden_count:
        visible.append(f"Grouped {hidden_count} low-value static call(s) in markdown; see static_graph.json for raw data.")
    return visible


def _is_low_value_call(call: str) -> bool:
    if call in {"len", "str", "int"}:
        return True
    return call in {
        "row.get",
        "dict.get",
        "p.add_argument",
        "parser.add_subparsers",
        "p.set_defaults",
    }


def _mermaid_id(value: str) -> str:
    return "n_" + "".join(character if character.isalnum() else "_" for character in value)


def _scope_label(in_function: str | None) -> str:
    return in_function or "<module>"
