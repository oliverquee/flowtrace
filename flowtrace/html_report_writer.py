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
    node_details_path: Path,
    runtime_graph: dict[str, object],
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
        node_details_path,
        runtime_graph,
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
    node_details_path: Path,
    runtime_graph: dict[str, object],
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
            '<body id="top">',
            "<main>",
            f"<header><h1>{_e(title)}</h1><p>Static local report. No external resources are loaded.</p>{_quick_status_badges(runtime_result, comparison, risk_groups)}</header>",
            _table_of_contents(),
            _summary_cards(entry_path, project_root, static_result, runtime_result, diagnostics, comparison, risk_groups),
            _section("recommended-next-checks", "Recommended next checks", _list(_recommended_next_checks(runtime_result, risk_groups, comparison)), open_=True),
            _section("project-summary", "Project summary", _key_values(_project_summary(project_root, runtime_result)), open_=True),
            _section("top-risks", "Top risks", _side_effect_table(top_risks), open_=True),
            _section("static-vs-runtime-comparison", "Static vs runtime comparison", _comparison_html(comparison), open_=True),
            _section("runtime-flowchart", "Runtime flowchart", _runtime_flowchart_html(runtime_result, runtime_graph), open_=True),
            _section("high-risk-side-effects", "High-risk side effects", _side_effect_table(risk_groups["high"]), open_=True),
            _section("medium-risk-side-effects", "Medium-risk side effects", _side_effect_table(risk_groups["medium"]), open_=False),
            _section("low-risk-side-effects", "Low-risk side effects", _side_effect_table(risk_groups["low"]), open_=False),
            _section("runtime-errors", "Runtime errors", _runtime_errors_html(diagnostics.runtime_error_path), open_=True),
            _section("runtime-call-order", "Runtime call order", _numbered(executed), open_=False),
            _section("intended-flow-comparison", "Intended flow comparison", _intended_flow_html(intended_comparison), open_=False),
            _section("legacy-unexecuted-function-diagnostics", "Legacy unexecuted function diagnostics", _legacy_unexecuted(runtime_result, diagnostics), open_=False),
            _section("assigned-variables-never-read", "Assigned variables never read", _assignments_html(diagnostics), open_=False),
            _section("node-details-data", "Node details data", f"<p><code>{_e(str(node_details_path))}</code></p>", open_=False),
            _section("technical-inventory", "Technical inventory", _technical_inventory_html(entry_path, project_root, static_result, flow_path, executed), open_=False),
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
    return f"<section id='executive-summary' class='summary'><h2>Executive summary</h2><div class='cards'>{cards}</div>{_back_to_top()}</section>"


def _section(section_id: str, title: str, body: str, open_: bool) -> str:
    open_attr = " open" if open_ else ""
    return f"<details id='{_e(section_id)}'{open_attr}><summary>{_e(title)}</summary><div class='section-body'><h2>{_e(title)}</h2>{body}{_back_to_top()}</div></details>"


def _table_of_contents() -> str:
    links = [
        ("executive-summary", "Executive summary"),
        ("recommended-next-checks", "Recommended next checks"),
        ("project-summary", "Project summary"),
        ("top-risks", "Top risks"),
        ("static-vs-runtime-comparison", "Static vs runtime comparison"),
        ("runtime-flowchart", "Runtime flowchart"),
        ("high-risk-side-effects", "High-risk side effects"),
        ("medium-risk-side-effects", "Medium-risk side effects"),
        ("low-risk-side-effects", "Low-risk side effects"),
        ("runtime-errors", "Runtime errors"),
        ("runtime-call-order", "Runtime call order"),
        ("intended-flow-comparison", "Intended flow comparison"),
        ("assigned-variables-never-read", "Assigned variables never read"),
        ("node-details-data", "Node details data"),
        ("technical-inventory", "Technical inventory"),
    ]
    items = "".join(f"<li><a href='#{_e(anchor)}'>{_e(label)}</a></li>" for anchor, label in links)
    return f"<nav class='toc' aria-label='Report sections'><h2>Table of contents</h2><ul>{items}</ul></nav>"


def _quick_status_badges(
    runtime_result: RuntimeTraceResult,
    comparison: StaticRuntimeComparison,
    risk_groups: dict[str, list[SideEffectRecord]],
) -> str:
    if runtime_result.runtime_skipped:
        runtime_status = "skipped"
    elif not runtime_result.runtime_attempted:
        runtime_status = "not attempted"
    elif runtime_result.completed:
        runtime_status = "completed"
    else:
        runtime_status = "error"

    if comparison.comparison_unavailable:
        comparison_status = "unavailable"
    elif comparison.partial_runtime:
        comparison_status = "partial"
    else:
        comparison_status = "available"

    badges = [
        ("Runtime", runtime_status),
        ("Risk", f"{len(risk_groups['high'])} high-risk"),
        ("Comparison", comparison_status),
        ("HTML", "static local/no external resources"),
    ]
    return "<div class='status-badges'>" + "".join(
        f"<span class='status-badge'><strong>{_e(label)}:</strong> {_e(value)}</span>" for label, value in badges
    ) + "</div>"


def _technical_inventory_html(
    entry_path: Path,
    project_root: Path,
    static_result: StaticAnalysisResult,
    flow_path: Path,
    executed: list[str],
) -> str:
    sections = [
        _subsection("Entry file", f"<p><code>{_e(relative_path(entry_path, project_root))}</code></p>"),
        _subsection("Files scanned", _list(file.path for file in static_result.files)),
        _subsection("Imports found", _list(_format_import(item) for item in static_result.imports)),
        _subsection(
            "Functions found",
            _list(f"{item.id}({', '.join(item.args)}) at {item.file}:{item.line}" for item in static_result.functions),
        ),
        _subsection("Functions executed", _list(dict.fromkeys(executed).keys())),
        _subsection("Mermaid diagram location", f"<p><code>{_e(str(flow_path))}</code></p>"),
    ]
    return "".join(sections)


def _subsection(title: str, body: str) -> str:
    return f"<details class='subsection'><summary>{_e(title)}</summary><div class='section-body'><h3>{_e(title)}</h3>{body}</div></details>"


def _back_to_top() -> str:
    return "<p class='back-top'><a href='#top'>Back to top</a></p>"


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


def _runtime_flowchart_html(runtime_result: RuntimeTraceResult, runtime_graph: dict[str, object]) -> str:
    if runtime_result.runtime_skipped:
        return "<p>Runtime was skipped, so no runtime flowchart is available.</p>"

    nodes = [_node_id(node) for node in runtime_graph.get("nodes", [])]
    edges = [
        (str(edge.get("caller")), str(edge.get("callee")), _edge_count(edge))
        for edge in runtime_graph.get("edges", [])
        if isinstance(edge, dict) and edge.get("caller") and edge.get("callee")
    ]
    if not nodes and not edges:
        return "<p>No runtime flowchart data was captured.</p>"

    unique_edges = {(caller, callee) for caller, callee, _count in edges}
    outgoing_counts: dict[str, int] = {}
    for caller, callee in unique_edges:
        outgoing_counts[caller] = outgoing_counts.get(caller, 0) + 1
    has_branching = any(count > 1 for count in outgoing_counts.values())
    total_edge_count = sum(count for _caller, _callee, count in edges)

    parts = [
        "<p class='flow-meta'>"
        f"Runtime nodes: <strong>{_e(len(nodes))}</strong> | "
        f"Runtime edges: <strong>{_e(total_edge_count)}</strong> | "
        f"Unique edges: <strong>{_e(len(unique_edges))}</strong> | "
        "Diagram mode: <strong>simple static SVG</strong>"
        "</p>",
        "<p class='hint'>Diagram is a simplified runtime flow view.</p>",
    ]
    if has_branching:
        parts.append("<p class='hint'>Branching flow is simplified.</p>")
    if runtime_result.runtime_attempted and not runtime_result.completed:
        parts.append("<p class='hint'>Runtime did not complete; this flowchart is based on partial trace data.</p>")
    parts.append(_runtime_flowchart_svg(nodes, edges))
    return "".join(parts)


def _runtime_flowchart_svg(nodes: list[str], edges: list[tuple[str, str, int]]) -> str:
    ordered_nodes = _ordered_flow_nodes(nodes, edges)
    if not ordered_nodes:
        return "<p>No runtime flowchart data was captured.</p>"

    row_height = 58
    box_width = 360
    box_height = 42
    left = 28
    top = 20
    width = box_width + 170
    height = top * 2 + max(1, len(ordered_nodes)) * row_height
    center_x = left + box_width / 2

    node_y = {node: top + index * row_height for index, node in enumerate(ordered_nodes)}
    edge_counts: dict[tuple[str, str], int] = {}
    for caller, callee, count in edges:
        edge_counts[(caller, callee)] = edge_counts.get((caller, callee), 0) + count
    svg_parts = [
        "<div class='flowchart-wrap'>",
        (
            f"<svg class='runtime-flowchart' viewBox='0 0 {width} {height}' "
            "role='img' aria-label='Simplified runtime flowchart' xmlns='http://www.w3.org/2000/svg'>"
        ),
        "<defs><marker id='arrow' markerWidth='10' markerHeight='10' refX='8' refY='3' orient='auto' markerUnits='strokeWidth'>"
        "<path d='M0,0 L0,6 L9,3 z' fill='#475569'/></marker></defs>",
    ]

    for (caller, callee), count in sorted(edge_counts.items()):
        if caller not in node_y or callee not in node_y or caller == callee:
            continue
        start_y = node_y[caller] + box_height
        end_y = node_y[callee]
        if node_y[callee] > node_y[caller]:
            svg_parts.append(
                f"<line x1='{center_x:.0f}' y1='{start_y}' x2='{center_x:.0f}' y2='{end_y}' "
                "stroke='#475569' stroke-width='1.6' marker-end='url(#arrow)'/>"
            )
            if count > 1:
                label_y = start_y + max(14, (end_y - start_y) / 2)
                svg_parts.append(_edge_count_label(center_x + 8, label_y, count))
        else:
            lane_x = left + box_width + 36
            svg_parts.append(
                f"<path d='M {center_x:.0f} {start_y} L {lane_x} {start_y} L {lane_x} {end_y + box_height / 2:.0f} "
                f"L {left + box_width} {end_y + box_height / 2:.0f}' fill='none' stroke='#94a3b8' "
                "stroke-width='1.4' marker-end='url(#arrow)'/>"
            )
            if count > 1:
                svg_parts.append(_edge_count_label(lane_x + 6, start_y + 14, count))

    for node in ordered_nodes:
        y = node_y[node]
        svg_parts.append("<g>")
        svg_parts.append(f"<title>{_e(node)}</title>")
        svg_parts.append(f"<rect x='{left}' y='{y}' width='{box_width}' height='{box_height}' rx='6' fill='#f8fafc' stroke='#94a3b8'/>")
        for line_index, line in enumerate(_label_lines(node)):
            text_y = y + 18 + line_index * 15
            svg_parts.append(
                f"<text x='{left + 14}' y='{text_y}' font-family='Consolas, Menlo, monospace' "
                f"font-size='12' fill='#0f172a'>{_e(line)}</text>"
            )
        svg_parts.append("</g>")

    svg_parts.extend(["</svg>", "</div>"])
    return "".join(svg_parts)


def _node_id(node: object) -> str:
    if isinstance(node, dict):
        return str(node.get("id", ""))
    return str(node)


def _edge_count(edge: dict[object, object]) -> int:
    try:
        return max(1, int(edge.get("count", 1)))
    except (TypeError, ValueError):
        return 1


def _edge_count_label(x: float, y: float, count: int) -> str:
    return (
        f"<text x='{x:.0f}' y='{y:.0f}' font-family='Consolas, Menlo, monospace' "
        f"font-size='11' fill='#475569'>x{_e(count)}</text>"
    )


def _label_lines(label: str) -> list[str]:
    max_chars = 38
    compact = label.strip()
    if len(compact) <= max_chars:
        return [compact]
    first = compact[:max_chars]
    second = compact[max_chars : max_chars * 2 - 1]
    if len(compact) > max_chars * 2 - 1:
        second = second.rstrip(".") + "..."
    return [first, second]


def _ordered_flow_nodes(nodes: list[str], edges: list[tuple[str, str, int]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(node: str) -> None:
        if node and node not in seen:
            seen.add(node)
            ordered.append(node)

    for caller, callee, _count in edges:
        add(caller)
        add(callee)
    for node in nodes:
        add(node)
    return ordered


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
    status_class = f"flow-status {comparison.status}"
    return "".join(
        [
            f"<p><span class='{_e(status_class)}'>Status: {_e(comparison.status)}</span></p>",
            f"<p class='hint'><strong>Summary:</strong> {_e(comparison.summary)}</p>",
            _key_values(
                [
                    ("Name", comparison.name or "None"),
                    ("Validation result", "ok" if comparison.validation_ok else "failed"),
                    ("Comparison available", str(comparison.comparison_available)),
                    ("Comparison unavailable reason", comparison.comparison_unavailable_reason or "None"),
                    ("Partial runtime", str(comparison.partial_runtime)),
                    ("First mismatch index", str(comparison.first_mismatch_index) if comparison.first_mismatch_index is not None else "None"),
                ]
            ),
            _list(["Runtime did not complete; intended-flow comparison is based on partial runtime trace."] if comparison.partial_runtime else []),
            "<h3>Validation errors</h3>",
            _list(comparison.validation_errors),
            "<h3>Expected order</h3>",
            _list(comparison.expected_runtime_order),
            "<h3>Actual order</h3>",
            _list(comparison.actual_runtime_order),
            "<h3>Matched functions</h3>",
            _list(comparison.matched_functions),
            "<h3>Missing expected functions</h3>",
            _list(comparison.missing_expected_functions),
            "<h3>Unexpected actual functions</h3>",
            _list(comparison.unexpected_actual_functions),
            "<h3>Order mismatches</h3>",
            _order_mismatch_table(comparison.order_mismatches),
        ]
    )


def _order_mismatch_table(items) -> str:
    if not items:
        return "<p>None</p>"
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{_e(item.expected_index)}</td>"
            f"<td><code>{_e(item.expected_function)}</code></td>"
            f"<td>{_e(item.actual_index if item.actual_index is not None else 'None')}</td>"
            f"<td><code>{_e(item.actual_function if item.actual_function is not None else 'None')}</code></td>"
            f"<td>{_e(item.message)}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Expected index</th><th>Expected</th><th>Actual index</th><th>Actual</th><th>Message</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


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
a{color:#1d4ed8;text-decoration:none}a:hover{text-decoration:underline}
code{font-family:Consolas,Menlo,monospace;background:#eef2f7;padding:1px 4px;border-radius:4px}
.status-badges{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 16px}
.status-badge{border:1px solid #d8dee9;border-radius:999px;background:#fff;padding:4px 10px;font-size:13px}
.flow-status{display:inline-block;border:1px solid #d8dee9;border-radius:999px;padding:3px 10px;font-weight:700;font-size:13px}
.flow-status.matched{background:#dcfce7;color:#166534}.flow-status.mismatch{background:#fef3c7;color:#92400e}
.flow-status.invalid{background:#fee2e2;color:#991b1b}.flow-status.unavailable{background:#e0f2fe;color:#075985}
.toc{background:#fff;border:1px solid #d8dee9;border-radius:8px;padding:14px 18px;margin-bottom:14px}
.toc h2{margin-top:0}.toc ul{columns:2;list-style:none;padding:0;margin:0}.toc li{break-inside:avoid;margin:5px 0}
.summary{background:#fff;border:1px solid #d8dee9;border-radius:8px;padding:18px;margin-bottom:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.card{border:1px solid #e1e6ef;border-radius:8px;padding:10px;background:#fbfcff}
.card span{display:block;color:#667085;font-size:12px}.card strong{display:block;overflow-wrap:anywhere}
details{background:#fff;border:1px solid #d8dee9;border-radius:8px;margin:12px 0}
summary{cursor:pointer;font-weight:700;padding:12px 14px}.section-body{padding:0 14px 14px}
.subsection{background:#fbfcff;margin:8px 0}.back-top{font-size:13px;margin-top:14px}
table{border-collapse:collapse;width:100%;margin:8px 0}th,td{text-align:left;border-bottom:1px solid #edf0f5;padding:7px;vertical-align:top}
.kv th{width:260px;color:#667085}.badge{display:inline-block;border-radius:999px;padding:2px 8px;font-weight:700;font-size:12px}
.high{background:#fee2e2;color:#991b1b}.medium{background:#fef3c7;color:#92400e}.low{background:#dcfce7;color:#166534}
.hint{border-left:4px solid #94a3b8;padding-left:10px;color:#475569}
.flow-meta{color:#475569;font-size:13px}
.flowchart-wrap{overflow-x:auto;border:1px solid #e1e6ef;border-radius:8px;background:#fff;margin-top:10px}
.runtime-flowchart{display:block;min-width:530px;max-width:100%;height:auto}
li{margin:3px 0;overflow-wrap:anywhere}
@media print{
body{background:#fff;color:#111827;font-size:12px}
main{max-width:none;padding:12px}
header,.summary,.toc,details,.card,table{break-inside:avoid;page-break-inside:avoid}
details{border-color:#cbd5e1}
details:not([open])>.section-body{display:block}
summary{cursor:default}
a{color:#111827;text-decoration:none}
.back-top{display:none}
.toc ul{columns:2}
.flowchart-wrap{overflow:visible}
.runtime-flowchart{min-width:0;width:100%}
}
""".strip()
