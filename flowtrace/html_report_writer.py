"""Write a static local HTML FlowTrace report."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

from .comparison import StaticCallNotObserved, StaticRuntimeComparison, RiskyUnexecutedFunction
from .diagnostics import DiagnosticsResult
from .intended_flow import IntendedFlowComparison
from .runtime_tracer import RuntimeTraceResult, target_args_display
from .static_analyzer import SideEffectRecord, StaticAnalysisResult
from .utils import relative_path


def write_html_report(
    path: Path,
    entry_path: Path,
    project_root: Path,
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
    diagnostics: DiagnosticsResult,
    flow_path: Path,
    intended_comparison: IntendedFlowComparison,
    static_runtime_comparison: StaticRuntimeComparison,
) -> None:
    risk_groups = _side_effects_by_risk(diagnostics.side_effect_calls)
    html_text = _document(
        entry_path,
        project_root,
        static_result,
        runtime_result,
        diagnostics,
        flow_path,
        intended_comparison,
        static_runtime_comparison,
        risk_groups,
    )
    path.write_text(html_text, encoding="utf-8")


def _document(
    entry_path: Path,
    project_root: Path,
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
    diagnostics: DiagnosticsResult,
    flow_path: Path,
    intended_comparison: IntendedFlowComparison,
    comparison: StaticRuntimeComparison,
    risk_groups: dict[str, list[SideEffectRecord]],
) -> str:
    executed = [event.function for event in runtime_result.events if event.event == "function_enter"]
    top_risks = (risk_groups["high"] + risk_groups["medium"] + risk_groups["low"])[:5]
    title = "FlowTrace Report"
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_e(title)}</title>",
            f"<style>{_css()}</style>",
            "</head>",
            "<body>",
            "<main>",
            f"<header><h1>{_e(title)}</h1><p>Static local report. No external resources are loaded.</p></header>",
            _summary_cards(entry_path, project_root, static_result, runtime_result, diagnostics, comparison, risk_groups),
            _section("Recommended next checks", _list(_recommended_next_checks(runtime_result, risk_groups, comparison)), open_=True),
            _section("Project summary", _key_values(_project_summary(project_root, runtime_result)), open_=True),
            _section("Top risks", _side_effect_table(top_risks), open_=True),
            _section("Static vs runtime comparison", _comparison_html(comparison), open_=True),
            _section("High-risk side effects", _side_effect_table(risk_groups["high"]), open_=True),
            _section("Medium-risk side effects", _side_effect_table(risk_groups["medium"]), open_=False),
            _section("Low-risk side effects", _side_effect_table(risk_groups["low"]), open_=False),
            _section("Runtime errors", _runtime_errors_html(diagnostics.runtime_error_path), open_=True),
            _section("Runtime call order", _numbered(executed), open_=False),
            _section("Intended flow comparison", _intended_flow_html(intended_comparison), open_=False),
            _section("Legacy unexecuted function diagnostics", _legacy_unexecuted(runtime_result, diagnostics), open_=False),
            _section("Assigned variables never read", _assignments_html(diagnostics), open_=False),
            _section("Entry file", f"<p><code>{_e(relative_path(entry_path, project_root))}</code></p>", open_=False),
            _section("Files scanned", _list(file.path for file in static_result.files), open_=False),
            _section("Imports found", _list(_format_import(item) for item in static_result.imports), open_=False),
            _section(
                "Functions found",
                _list(f"{item.id}({', '.join(item.args)}) at {item.file}:{item.line}" for item in static_result.functions),
                open_=False,
            ),
            _section("Functions executed", _list(dict.fromkeys(executed).keys()), open_=False),
            _section("Mermaid diagram location", f"<p><code>{_e(str(flow_path))}</code></p>", open_=False),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _summary_cards(
    entry_path: Path,
    project_root: Path,
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
    diagnostics: DiagnosticsResult,
    comparison: StaticRuntimeComparison,
    risk_groups: dict[str, list[SideEffectRecord]],
) -> str:
    values = [
        ("Project root", str(project_root)),
        ("Entry file", relative_path(entry_path, project_root)),
        ("Python files scanned", str(len(static_result.files))),
        ("Functions found", str(len(static_result.functions))),
        ("Runtime attempted", str(runtime_result.runtime_attempted)),
        ("Runtime completed", str(runtime_result.completed)),
        ("Runtime skipped", str(runtime_result.runtime_skipped)),
        ("Target args", "None" if not runtime_result.target_args else repr(runtime_result.target_args)),
        ("Target args display", target_args_display(runtime_result.target_args)),
        ("Runtime error count", str(len(diagnostics.runtime_error_path))),
        ("High-risk side effects", str(len(risk_groups["high"]))),
        ("Medium-risk side effects", str(len(risk_groups["medium"]))),
        ("Low-risk side effects", str(len(risk_groups["low"]))),
        ("Executed static functions", str(len(comparison.executed_static_functions))),
        ("Static-only comparison unavailable", str(comparison.comparison_unavailable)),
        ("Risky unexecuted functions", str(len(comparison.risky_unexecuted_functions))),
    ]
    cards = "".join(f"<div class='card'><span>{_e(label)}</span><strong>{_e(value)}</strong></div>" for label, value in values)
    return f"<section class='summary'><h2>Executive summary</h2><div class='cards'>{cards}</div></section>"


def _section(title: str, body: str, open_: bool) -> str:
    open_attr = " open" if open_ else ""
    return f"<details{open_attr}><summary>{_e(title)}</summary><div class='section-body'>{body}</div></details>"


def _project_summary(project_root: Path, runtime_result: RuntimeTraceResult) -> list[tuple[str, str]]:
    return [
        ("Project root", str(project_root)),
        ("Runtime attempted", str(runtime_result.runtime_attempted)),
        ("Runtime completed", str(runtime_result.completed)),
        ("Runtime skipped", str(runtime_result.runtime_skipped)),
        ("Runtime skipped reason", runtime_result.runtime_skipped_reason or "None"),
        ("Target args", "None" if not runtime_result.target_args else repr(runtime_result.target_args)),
        ("Target args display", target_args_display(runtime_result.target_args)),
    ]


def _comparison_html(comparison: StaticRuntimeComparison) -> str:
    counts = _key_values(
        [
            ("Static functions found", str(len(comparison.static_functions))),
            ("Runtime functions observed", str(len(comparison.runtime_functions))),
            ("Executed static functions", str(len(comparison.executed_static_functions))),
            ("Static functions not executed", str(len(comparison.static_functions_not_executed))),
            ("Runtime functions without static definition", str(len(comparison.runtime_functions_without_static_definition))),
            ("Risky unexecuted functions", str(len(comparison.risky_unexecuted_functions))),
            ("Static resolved calls not observed", str(len(comparison.static_resolved_calls_not_observed))),
        ]
    )
    notes = []
    if comparison.comparison_unavailable_reason:
        notes.append(comparison.comparison_unavailable_reason)
    if comparison.partial_runtime:
        notes.append("Runtime did not complete, so comparison is based on partial runtime trace.")
    return "".join(
        [
            counts,
            _list(notes),
            "<h3>Executed static functions</h3>",
            _comparison_list(comparison.executed_static_functions, comparison),
            "<h3>Static functions not executed</h3>",
            _comparison_list(comparison.static_functions_not_executed, comparison),
            "<h3>Runtime functions without static definition</h3>",
            _comparison_list(comparison.runtime_functions_without_static_definition, comparison),
            "<h3>Risky unexecuted functions</h3>",
            _risky_unexecuted_html(comparison.risky_unexecuted_functions),
            "<h3>Static resolved calls not observed</h3>",
            _static_calls_not_observed_html(comparison.static_resolved_calls_not_observed),
        ]
    )


def _comparison_list(items: list[str], comparison: StaticRuntimeComparison) -> str:
    if comparison.comparison_unavailable:
        return _list(["Runtime was skipped, so execution comparison is unavailable."])
    return _list(items)


def _side_effect_table(items: list[SideEffectRecord]) -> str:
    if not items:
        return "<p>None</p>"
    rows = []
    for item in items:
        risk = _side_effect_risk(item)
        rows.append(
            "<tr>"
            f"<td><span class='badge {risk}'>{_e(risk)}</span></td>"
            f"<td>{_e(item.category)}</td>"
            f"<td><code>{_e(item.call)}</code></td>"
            f"<td><code>{_e(item.file)}:{_e(str(item.line))}</code></td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Risk</th><th>Category</th><th>Call</th><th>Location</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _runtime_errors_html(errors: list[dict[str, str | int | None]]) -> str:
    if not errors:
        return "<p>None</p>"
    grouped: dict[tuple[str | None, str | None], list[dict[str, str | int | None]]] = {}
    for error in errors:
        grouped.setdefault((error.get("error_type"), error.get("error_message")), []).append(error)
    parts = []
    for (error_type, message), group in grouped.items():
        parts.append(f"<h3>{_e(_error_label(error_type))}: {_e(str(error_type))}: {_e(str(message))} ({len(group)} occurrence(s))</h3>")
        parts.append(_list(f"{item['function']} in {item['file']}:{item['line']}" for item in group))
        hint = _error_hint(error_type)
        if hint:
            parts.append(f"<p class='hint'>{_e(hint)}</p>")
    return "".join(parts)


def _intended_flow_html(comparison) -> str:
    return "".join(
        [
            _key_values([("Name", comparison.name or "None"), ("Order mismatch summary", comparison.order_mismatch_summary)]),
            "<h3>Expected order</h3>",
            _list(comparison.expected_runtime_order),
            "<h3>Actual order</h3>",
            _list(comparison.actual_runtime_order),
            "<h3>Missing expected functions</h3>",
            _list(comparison.missing_expected_functions),
            "<h3>Unexpected actual functions</h3>",
            _list(comparison.unexpected_actual_functions),
        ]
    )


def _legacy_unexecuted(runtime_result: RuntimeTraceResult, diagnostics: DiagnosticsResult) -> str:
    count = "N/A (runtime skipped)" if runtime_result.runtime_skipped else str(len(diagnostics.functions_defined_but_not_executed))
    note = "Runtime was skipped, so unexecuted-function diagnostics are unavailable." if runtime_result.runtime_skipped else "Detailed list omitted here to avoid duplication."
    return _key_values([("Preferred section", "Static vs runtime comparison"), ("Count", count)]) + _list([note])


def _assignments_html(diagnostics: DiagnosticsResult) -> str:
    return _list(f"{item.name} at {item.file}:{item.line} in {item.in_function or '<module>'}" for item in diagnostics.assigned_variables_never_read)


def _risky_unexecuted_html(items: list[RiskyUnexecutedFunction]) -> str:
    if not items:
        return "<p>None</p>"
    parts = []
    for item in items:
        parts.append(f"<h4>{_e(item.function_id)} <small>{_e(item.file)}:{_e(str(item.line))}</small></h4>")
        parts.append(_side_effect_table(item.side_effects))
    return "".join(parts)


def _static_calls_not_observed_html(items: list[StaticCallNotObserved]) -> str:
    return _list(f"{item.caller} -> {item.callee} via {item.call} at {item.file}:{item.line}" for item in items)


def _recommended_next_checks(
    runtime_result: RuntimeTraceResult,
    risk_groups: dict[str, list[SideEffectRecord]],
    comparison: StaticRuntimeComparison,
) -> list[str]:
    checks: list[str] = []
    if risk_groups["high"]:
        checks.append("Review high-risk side effects before runtime execution.")
    if runtime_result.runtime_skipped:
        checks.append("Static-only mode was a safe first pass; runtime comparison is unavailable because runtime was skipped.")
        checks.append("Review top risks before using runtime mode.")
    if runtime_result.runtime_attempted and not runtime_result.completed:
        checks.append("Check runtime errors and the partial static-vs-runtime comparison.")
    if runtime_result.runtime_attempted and not runtime_result.target_args:
        checks.append("Pass --target-args for CLI-style projects to trace the intended command path.")
    if comparison.risky_unexecuted_functions:
        checks.append("Review risky unexecuted functions in the static-vs-runtime comparison.")
    if not checks:
        checks.append("No immediate high-priority checks found.")
    return checks


def _key_values(items: Iterable[tuple[str, str]]) -> str:
    rows = "".join(f"<tr><th>{_e(label)}</th><td><code>{_e(value)}</code></td></tr>" for label, value in items)
    return f"<table class='kv'><tbody>{rows}</tbody></table>"


def _list(items: Iterable[object]) -> str:
    values = [str(item) for item in items]
    if not values:
        return "<p>None</p>"
    return "<ul>" + "".join(f"<li>{_e(item)}</li>" for item in values) + "</ul>"


def _numbered(items: Iterable[object]) -> str:
    values = [str(item) for item in items]
    if not values:
        return "<p>None</p>"
    return "<ol>" + "".join(f"<li>{_e(item)}</li>" for item in values) + "</ol>"


def _format_import(item) -> str:
    alias = f" as {item.alias}" if item.alias else ""
    module_prefix = "" if item.module == item.name else f"{item.module}." if item.module else ""
    return f"{module_prefix}{item.name}{alias} at {item.file}:{item.line}"


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


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
body{margin:0;background:#f7f8fb;color:#1f2937;font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px}
header{border-bottom:1px solid #d8dee9;margin-bottom:18px}
h1{margin:0 0 6px;font-size:30px} h2{font-size:20px} h3{font-size:16px;margin-top:18px}
code{font-family:Consolas,Menlo,monospace;background:#eef2f7;padding:1px 4px;border-radius:4px}
.summary{background:#fff;border:1px solid #d8dee9;border-radius:8px;padding:18px;margin-bottom:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.card{border:1px solid #e1e6ef;border-radius:8px;padding:10px;background:#fbfcff}
.card span{display:block;color:#667085;font-size:12px}.card strong{display:block;overflow-wrap:anywhere}
details{background:#fff;border:1px solid #d8dee9;border-radius:8px;margin:12px 0}
summary{cursor:pointer;font-weight:700;padding:12px 14px}.section-body{padding:0 14px 14px}
table{border-collapse:collapse;width:100%;margin:8px 0}th,td{text-align:left;border-bottom:1px solid #edf0f5;padding:7px;vertical-align:top}
.kv th{width:260px;color:#667085}.badge{display:inline-block;border-radius:999px;padding:2px 8px;font-weight:700;font-size:12px}
.high{background:#fee2e2;color:#991b1b}.medium{background:#fef3c7;color:#92400e}.low{background:#dcfce7;color:#166534}
.hint{border-left:4px solid #94a3b8;padding-left:10px;color:#475569}
li{margin:3px 0;overflow-wrap:anywhere}
""".strip()
