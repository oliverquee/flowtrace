"""Write a static local HTML FlowTrace report."""

from __future__ import annotations

import html
import json
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
    node_details: list[dict[str, object]],
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
        node_details,
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
    node_details: list[dict[str, object]],
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
            _section("node-details-data-section", "Node details data", f"<p><code>{_e(str(node_details_path))}</code></p>", open_=False),
            _section("technical-inventory", "Technical inventory", _technical_inventory_html(entry_path, project_root, static_result, flow_path, executed), open_=False),
            _embedded_node_details_json(node_details),
            _embedded_runtime_events_json(runtime_result),
            _node_inspector_script(),
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
        ("node-details-data-section", "Node details data"),
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
        return (
            "<p>Runtime was skipped, so no runtime flowchart is available.</p>"
            + _playback_html(runtime_result)
            + _node_inspector_html()
        )

    nodes = [_node_id(node) for node in runtime_graph.get("nodes", [])]
    edges = [
        (str(edge.get("caller")), str(edge.get("callee")), _edge_count(edge))
        for edge in runtime_graph.get("edges", [])
        if isinstance(edge, dict) and edge.get("caller") and edge.get("callee")
    ]
    if not nodes and not edges:
        return "<p>No runtime flowchart data was captured.</p>" + _playback_html(runtime_result) + _node_inspector_html()

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
    parts.append(_playback_html(runtime_result))
    parts.append(_node_inspector_html())
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
                f"<line class='flow-edge' data-edge-id='{_edge_data_id(caller, callee)}' "
                f"x1='{center_x:.0f}' y1='{start_y}' x2='{center_x:.0f}' y2='{end_y}' "
                "stroke='#475569' stroke-width='1.6' marker-end='url(#arrow)'/>"
            )
            if count > 1:
                label_y = start_y + max(14, (end_y - start_y) / 2)
                svg_parts.append(_edge_count_label(center_x + 8, label_y, count))
        else:
            lane_x = left + box_width + 36
            svg_parts.append(
                f"<path class='flow-edge' data-edge-id='{_edge_data_id(caller, callee)}' "
                f"d='M {center_x:.0f} {start_y} L {lane_x} {start_y} L {lane_x} {end_y + box_height / 2:.0f} "
                f"L {left + box_width} {end_y + box_height / 2:.0f}' fill='none' stroke='#94a3b8' "
                "stroke-width='1.4' marker-end='url(#arrow)'/>"
            )
            if count > 1:
                svg_parts.append(_edge_count_label(lane_x + 6, start_y + 14, count))

    for node in ordered_nodes:
        y = node_y[node]
        svg_parts.append(
            f"<g class='flow-node' data-node-id='{_e(node)}' tabindex='0' role='button' "
            f"aria-label='Inspect {_e(node)}'>"
        )
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


def _edge_data_id(caller: str, callee: str) -> str:
    return _e(f"{caller}->{callee}")


def _playback_html(runtime_result: RuntimeTraceResult) -> str:
    disabled_attr = " disabled" if runtime_result.runtime_skipped else ""
    unavailable = ""
    if runtime_result.runtime_skipped:
        unavailable = "<p class='playback-unavailable'>Runtime playback unavailable: run without --static-only to capture execution events.</p>"
    partial_note = ""
    if runtime_result.runtime_attempted and not runtime_result.completed:
        partial_note = "<p class='hint'>Partial playback: runtime ended with an error.</p>"
    return "".join(
        [
            "<section class='playback-panel' aria-label='Runtime playback'>",
            "<h3>Runtime playback</h3>",
            "<p class='hint'>Runtime playback requires local browser JavaScript.</p>",
            "<p class='hint'>Use Next to step through execution. Click any event row to jump to that step. Click graph nodes to inspect details.</p>",
            unavailable,
            partial_note,
            "<fieldset class='playback-filters'>",
            "<legend>Event filter</legend>",
            f"<label><input type='radio' name='playback-filter' value='all'{disabled_attr}> All events</label>",
            f"<label><input type='radio' name='playback-filter' value='enter'{disabled_attr}> Function enter only</label>",
            f"<label><input type='radio' name='playback-filter' value='errors'{disabled_attr}> Errors only</label>",
            f"<label><input type='radio' name='playback-filter' value='vars'{disabled_attr}> Variable changes only</label>",
            "</fieldset>",
            "<div class='playback-controls'>",
            f"<button type='button' id='playback-first'{disabled_attr}>First</button>",
            f"<button type='button' id='playback-prev'{disabled_attr}>Previous</button>",
            f"<button type='button' id='playback-next'{disabled_attr}>Next</button>",
            f"<button type='button' id='playback-toggle'{disabled_attr}>Play</button>",
            f"<label>Speed <select id='playback-speed'{disabled_attr}>",
            "<option value='1200'>Slow</option>",
            "<option value='700' selected>Normal</option>",
            "<option value='300'>Fast</option>",
            "</select></label>",
            "<span id='playback-counter' class='playback-counter'>0 / 0</span>",
            "</div>",
            "<div id='playback-event-detail' class='event-detail'>Runtime event details will appear here.</div>",
            "<ol id='runtime-event-list' class='runtime-event-list'></ol>",
            "</section>",
        ]
    )


def _node_inspector_html() -> str:
    return "".join(
        [
            "<p class='hint'>Node details panel requires local browser JavaScript. The report remains readable without it.</p>",
            "<div class='node-legend' aria-label='Node legend'>",
            "<span><i class='legend-swatch executed'></i>Executed</span>",
            "<span><i class='legend-swatch not-executed'></i>Not executed</span>",
            "<span><i class='legend-swatch risk-high'></i>High risk</span>",
            "<span><i class='legend-swatch intended-matched'></i>Intended matched</span>",
            "<span><i class='legend-swatch intended-missing'></i>Intended missing</span>",
            "<span><i class='legend-swatch intended-unexpected'></i>Intended unexpected</span>",
            "</div>",
            "<aside id='node-details-panel' class='node-panel' aria-live='polite'>",
            "<p>Select a graph node to inspect details.</p>",
            "</aside>",
        ]
    )


def _embedded_node_details_json(node_details: list[dict[str, object]]) -> str:
    payload = json.dumps(node_details, sort_keys=True)
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return f'<script type="application/json" id="node-details-data">{payload}</script>'


def _embedded_runtime_events_json(runtime_result: RuntimeTraceResult) -> str:
    events = []
    if runtime_result.runtime_skipped:
        events.append(
            {
                "index": 0,
                "event": "runtime_skipped",
                "function": None,
                "file": None,
                "line": None,
                "caller": None,
                "timestamp": None,
                "error_type": None,
                "error_message": runtime_result.runtime_skipped_reason,
                "changed_vars": None,
            }
        )
    else:
        for index, event in enumerate(runtime_result.events):
            events.append(
                {
                    "index": index,
                    "event": event.event,
                    "function": event.function,
                    "file": event.file,
                    "line": event.line,
                    "caller": event.caller,
                    "timestamp": event.timestamp,
                    "error_type": event.error_type,
                    "error_message": event.error_message,
                    "changed_vars": event.changed_vars,
                }
            )
    payload = json.dumps(events, sort_keys=True)
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return f'<script type="application/json" id="runtime-events-data">{payload}</script>'


def _node_inspector_script() -> str:
    return r"""
<script>
(function () {
  "use strict";

  var nodeDataEl = document.getElementById("node-details-data");
  var eventDataEl = document.getElementById("runtime-events-data");
  var panel = document.getElementById("node-details-panel");
  var eventDetail = document.getElementById("playback-event-detail");
  var eventList = document.getElementById("runtime-event-list");
  var counter = document.getElementById("playback-counter");
  var firstButton = document.getElementById("playback-first");
  var prevButton = document.getElementById("playback-prev");
  var nextButton = document.getElementById("playback-next");
  var toggleButton = document.getElementById("playback-toggle");
  var speedSelect = document.getElementById("playback-speed");
  var filterInputs = Array.prototype.slice.call(document.querySelectorAll("input[name='playback-filter']"));
  if (!panel) {
    return;
  }

  var details = [];
  var runtimeEvents = [];
  var filteredEvents = [];
  var nodeDetailsLoaded = true;
  var runtimeEventsLoaded = true;
  try {
    details = nodeDataEl ? JSON.parse(nodeDataEl.textContent || "[]") : [];
  } catch (error) {
    nodeDetailsLoaded = false;
    details = [];
    panel.textContent = "Node details could not be loaded.";
  }
  try {
    runtimeEvents = eventDataEl ? JSON.parse(eventDataEl.textContent || "[]") : [];
  } catch (error) {
    runtimeEventsLoaded = false;
    runtimeEvents = [];
  }

  var byId = new Map();
  details.forEach(function (item) {
    if (item && item.id) {
      byId.set(String(item.id), item);
    }
  });

  var playbackIndex = runtimeEvents.length ? 0 : -1;
  var playbackTimer = null;
  var currentPlaybackNodeId = null;

  function appendText(parent, tagName, text, className) {
    var el = document.createElement(tagName);
    if (className) {
      el.className = className;
    }
    el.textContent = text == null || text === "" ? "None" : String(text);
    parent.appendChild(el);
    return el;
  }

  function appendKeyValue(parent, label, value) {
    var row = document.createElement("div");
    row.className = "node-kv-row";
    appendText(row, "dt", label);
    appendText(row, "dd", value);
    parent.appendChild(row);
  }

  function appendJsonBlock(parent, label, value) {
    appendText(parent, "h4", label);
    if (!value || (Array.isArray(value) && value.length === 0)) {
      appendText(parent, "p", "None");
      return;
    }
    var pre = document.createElement("pre");
    pre.textContent = JSON.stringify(value, null, 2);
    parent.appendChild(pre);
  }

  function hasChangedVars(value) {
    return value && typeof value === "object" && Object.keys(value).length > 0;
  }

  function valueText(value) {
    return value == null ? "None" : String(value);
  }

  function appendVariableChangeTable(parent, changedVars) {
    var table = document.createElement("table");
    table.className = "var-change-table";
    var thead = document.createElement("thead");
    var headRow = document.createElement("tr");
    ["Variable", "Before", "After"].forEach(function (label) {
      appendText(headRow, "th", label);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
    var tbody = document.createElement("tbody");
    Object.keys(changedVars).forEach(function (name) {
      var change = changedVars[name] || {};
      var row = document.createElement("tr");
      appendText(row, "td", name);
      appendText(row, "td", valueText(change.before));
      appendText(row, "td", valueText(change.after));
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    parent.appendChild(table);
  }

  function appendEventVariableChanges(parent, event) {
    if (!event || event.event !== "variable_change" || !hasChangedVars(event.changed_vars)) {
      return;
    }
    var section = document.createElement("div");
    section.className = "var-changes-section";
    appendText(section, "h4", "Changed variables");
    appendVariableChangeTable(section, event.changed_vars);
    parent.appendChild(section);
  }

  function appendNodeVariableChanges(parent, id) {
    var events = runtimeEvents.filter(function (event) {
      return event && event.event === "variable_change" && event.function === id && hasChangedVars(event.changed_vars);
    });
    if (!events.length) {
      return;
    }
    var section = document.createElement("div");
    section.className = "var-changes-section";
    appendText(section, "h4", "Variable changes (" + events.length + " line events)");
    var groups = [];
    events.forEach(function (event) {
      var line = event.line == null ? "None" : String(event.line);
      var group = groups.find(function (item) {
        return item.line === line;
      });
      if (!group) {
        group = {line: line, events: []};
        groups.push(group);
      }
      group.events.push(event);
    });
    groups.forEach(function (group) {
      appendText(section, "p", "Line " + group.line, "var-changes-line-label");
      group.events.forEach(function (event) {
        appendVariableChangeTable(section, event.changed_vars);
      });
    });
    parent.appendChild(section);
  }

  function appendSourceSnippet(parent, snippet) {
    appendText(parent, "h4", "Source snippet");
    if (!snippet || !snippet.available) {
      appendText(parent, "p", snippet && snippet.reason ? snippet.reason : "Source snippet is unavailable.");
      return;
    }
    appendText(parent, "p", String(snippet.file || "Unknown file") + " lines " + snippet.start_line + "-" + snippet.end_line, "source-snippet-meta");
    var table = document.createElement("table");
    table.className = "source-snippet";
    var tbody = document.createElement("tbody");
    (snippet.lines || []).forEach(function (line) {
      var row = document.createElement("tr");
      if (line.is_focus_line) {
        row.className = "focus-line";
      }
      var numberCell = document.createElement("td");
      numberCell.className = "line-number";
      numberCell.textContent = String(line.line_number);
      var textCell = document.createElement("td");
      textCell.className = "line-text";
      textCell.textContent = line.text || "";
      row.appendChild(numberCell);
      row.appendChild(textCell);
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    parent.appendChild(table);
  }

  function roleClass(value) {
    return "role-" + String(value || "none").replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
  }

  function riskClass(value) {
    return "risk-" + String(value || "none").replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
  }

  function edgeId(caller, callee) {
    return String(caller || "") + "->" + String(callee || "");
  }

  function decorateNode(nodeEl, detail) {
    if (!detail) {
      nodeEl.classList.add("node-detail-missing");
      return;
    }
    nodeEl.classList.add(detail.executed ? "node-executed" : "node-not-executed");
    nodeEl.classList.add(riskClass(detail.highest_risk_level));
    nodeEl.classList.add(roleClass(detail.intended_flow_role));
  }

  function renderNodeDetail(id) {
    var detail = byId.get(id);
    panel.textContent = "";
    if (!nodeDetailsLoaded) {
      appendText(panel, "h3", id);
      appendText(panel, "p", "Node details could not be loaded.", "playback-error-text");
      return;
    }
    if (!detail) {
      appendText(panel, "h3", id);
      appendText(panel, "p", "No node details were found for this graph node.");
      return;
    }

    appendText(panel, "h3", detail.label || detail.id);
    var badges = document.createElement("div");
    badges.className = "node-panel-badges";
    appendText(badges, "span", "Risk: " + (detail.highest_risk_level || "none"), riskClass(detail.highest_risk_level));
    appendText(badges, "span", "Executed: " + Boolean(detail.executed), detail.executed ? "executed" : "not-executed");
    appendText(badges, "span", "Intended: " + (detail.intended_flow_role || "none"), roleClass(detail.intended_flow_role));
    panel.appendChild(badges);

    var meta = document.createElement("dl");
    meta.className = "node-kv";
    appendKeyValue(meta, "id", detail.id);
    appendKeyValue(meta, "node_type", detail.node_type);
    appendKeyValue(meta, "file", detail.file);
    appendKeyValue(meta, "line", detail.line);
    appendKeyValue(meta, "args", (detail.args || []).join(", "));
    appendKeyValue(meta, "runtime_first_seen_index", detail.runtime_first_seen_index);
    appendKeyValue(meta, "runtime_call_count", detail.runtime_call_count);
    panel.appendChild(meta);

    appendSourceSnippet(panel, detail.source_snippet);
    appendNodeVariableChanges(panel, id);
    appendJsonBlock(panel, "Incoming static calls", detail.incoming_static_calls);
    appendJsonBlock(panel, "Outgoing static calls", detail.outgoing_static_calls);
    appendJsonBlock(panel, "Incoming runtime calls", detail.incoming_runtime_calls);
    appendJsonBlock(panel, "Outgoing runtime calls", detail.outgoing_runtime_calls);
    appendJsonBlock(panel, "Side effects", detail.side_effects);
    appendJsonBlock(panel, "Diagnostics", detail.diagnostics);
  }

  function selectNode(nodeEl, fromPlayback) {
    document.querySelectorAll(".flow-node.selected").forEach(function (item) {
      item.classList.remove("selected");
    });
    nodeEl.classList.add("selected");
    if (fromPlayback) {
      nodeEl.classList.add("playback-current");
      currentPlaybackNodeId = nodeEl.getAttribute("data-node-id");
    }
    renderNodeDetail(nodeEl.getAttribute("data-node-id"));
  }

  function clearPlaybackHighlights() {
    document.querySelectorAll(".flow-node.playback-current,.flow-node.playback-visited,.flow-node.playback-error").forEach(function (item) {
      item.classList.remove("playback-current", "playback-visited", "playback-error");
    });
    document.querySelectorAll(".flow-edge.playback-current-edge").forEach(function (item) {
      item.classList.remove("playback-current-edge");
    });
  }

  function markVisitedThrough(index) {
    document.querySelectorAll(".flow-node.playback-visited,.flow-node.playback-error").forEach(function (item) {
      item.classList.remove("playback-visited", "playback-error");
    });
    filteredEvents.slice(0, index + 1).forEach(function (event) {
      if (!event || !event.function) {
        return;
      }
      var nodeEl = document.querySelector(".flow-node[data-node-id='" + cssEscape(event.function) + "']");
      if (nodeEl) {
        nodeEl.classList.add("playback-visited");
        if (isErrorEvent(event)) {
          nodeEl.classList.add("playback-error");
        }
      }
    });
  }

  function isErrorEvent(event) {
    return event && (event.event === "function_error" || event.event === "runtime_error" || event.error_type || event.error_message);
  }

  function isEnterEvent(event) {
    return event && event.event === "function_enter";
  }

  function selectedFilter() {
    var selected = filterInputs.find(function (input) {
      return input.checked;
    });
    return selected ? selected.value : "all";
  }

  function chooseDefaultFilter() {
    if (!filterInputs.length) {
      return;
    }
    var defaultValue = runtimeEvents.length > 20 ? "enter" : "all";
    var defaultInput = filterInputs.find(function (input) {
      return input.value === defaultValue;
    }) || filterInputs[0];
    defaultInput.checked = true;
  }

  function eventMatchesFilter(event, filter) {
    if (filter === "enter") {
      return isEnterEvent(event);
    }
    if (filter === "errors") {
      return isErrorEvent(event);
    }
    if (filter === "vars") {
      return event && event.event === "variable_change";
    }
    return true;
  }

  function applyFilter() {
    var filter = selectedFilter();
    filteredEvents = runtimeEvents.filter(function (event) {
      return eventMatchesFilter(event, filter);
    });
    playbackIndex = filteredEvents.length ? 0 : -1;
    renderEventList();
    renderPlaybackStep(playbackIndex);
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(String(value));
    }
    return String(value).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  }

  function updateEventDetail(event, index) {
    if (!eventDetail) {
      return;
    }
    eventDetail.textContent = "";
    appendText(eventDetail, "h4", event ? "Current runtime event" : "No runtime events captured");
    if (!runtimeEventsLoaded) {
      appendText(eventDetail, "p", "Runtime playback data could not be loaded.", "playback-error-text");
      return;
    }
    var meta = document.createElement("dl");
    meta.className = "node-kv";
    appendKeyValue(meta, "step", event ? String(index + 1) + " / " + filteredEvents.length : "0 / 0");
    appendKeyValue(meta, "raw_index", event && event.index);
    appendKeyValue(meta, "event", event && event.event);
    appendKeyValue(meta, "function", event && event.function);
    appendKeyValue(meta, "file", event && event.file);
    appendKeyValue(meta, "line", event && event.line);
    appendKeyValue(meta, "timestamp", event && event.timestamp);
    appendKeyValue(meta, "error_type", event && event.error_type);
    appendKeyValue(meta, "message", event && event.error_message);
    eventDetail.appendChild(meta);
    appendEventVariableChanges(eventDetail, event);
  }

  function updateCounter() {
    if (counter) {
      counter.textContent = filteredEvents.length ? String(playbackIndex + 1) + " / " + filteredEvents.length : "0 / 0";
    }
  }

  function highlightEventRow(index) {
    if (!eventList) {
      return;
    }
    eventList.querySelectorAll(".runtime-event-row.current").forEach(function (row) {
      row.classList.remove("current");
    });
    var row = eventList.querySelector("[data-step-index='" + index + "']");
    if (row) {
      row.classList.add("current");
    }
  }

  function highlightIncomingEdge(event) {
    if (!event || !event.function) {
      return;
    }
    var caller = event.caller || previousEnterFunction(playbackIndex);
    if (!caller) {
      return;
    }
    var id = edgeId(caller, event.function);
    document.querySelectorAll(".flow-edge[data-edge-id='" + cssEscape(id) + "']").forEach(function (edge) {
      edge.classList.add("playback-current-edge");
    });
  }

  function previousEnterFunction(filteredIndex) {
    for (var i = filteredIndex - 1; i >= 0; i -= 1) {
      if (filteredEvents[i] && filteredEvents[i].function && filteredEvents[i].event === "function_enter") {
        return filteredEvents[i].function;
      }
    }
    return null;
  }

  function renderPlaybackStep(index) {
    if (!runtimeEventsLoaded) {
      updateCounter();
      updateEventDetail(null, -1);
      return;
    }
    if (!filteredEvents.length) {
      updateCounter();
      updateEventDetail(null, -1);
      highlightEventRow(-1);
      return;
    }
    playbackIndex = Math.max(0, Math.min(index, filteredEvents.length - 1));
    var event = filteredEvents[playbackIndex];
    clearPlaybackHighlights();
    markVisitedThrough(playbackIndex);
    updateCounter();
    updateEventDetail(event, playbackIndex);
    highlightEventRow(playbackIndex);

    if (event && event.function) {
      var nodeEl = document.querySelector(".flow-node[data-node-id='" + cssEscape(event.function) + "']");
      if (nodeEl) {
        selectNode(nodeEl, true);
        if (isErrorEvent(event)) {
          nodeEl.classList.add("playback-error");
        }
      }
      if (event.event === "function_enter") {
        highlightIncomingEdge(event);
      }
      if (isErrorEvent(event)) {
        highlightIncomingEdge(event);
      }
    }
  }

  function stopPlayback() {
    if (playbackTimer) {
      window.clearInterval(playbackTimer);
      playbackTimer = null;
    }
    if (toggleButton) {
      toggleButton.textContent = "Play";
    }
  }

  function startPlayback() {
    if (!filteredEvents.length || playbackTimer) {
      return;
    }
    if (toggleButton) {
      toggleButton.textContent = "Pause";
    }
    playbackTimer = window.setInterval(function () {
      if (playbackIndex >= filteredEvents.length - 1) {
        stopPlayback();
        return;
      }
      renderPlaybackStep(playbackIndex + 1);
    }, Number(speedSelect && speedSelect.value ? speedSelect.value : 700));
  }

  function renderEventList() {
    if (!eventList) {
      return;
    }
    eventList.textContent = "";
    if (!runtimeEventsLoaded) {
      appendText(eventList, "li", "Runtime playback data could not be loaded.", "playback-error-text");
      return;
    }
    if (!filteredEvents.length) {
      appendText(eventList, "li", "No runtime events match this filter.");
      return;
    }
    filteredEvents.forEach(function (event, index) {
      var row = document.createElement("li");
      row.className = "runtime-event-row";
      row.setAttribute("data-step-index", String(index));
      row.tabIndex = 0;
      var location = event.file ? event.file + (event.line == null ? "" : ":" + event.line) : "None";
      var marker = isErrorEvent(event) ? " [ERROR]" : "";
      row.textContent = String(index + 1) + ". " + (event.event || "event") + marker + " | " + (event.function || "None") + " | " + location;
      if (isErrorEvent(event)) {
        row.classList.add("error");
      }
      row.addEventListener("click", function () {
        stopPlayback();
        renderPlaybackStep(index);
      });
      row.addEventListener("keydown", function (keyboardEvent) {
        if (keyboardEvent.key === "Enter" || keyboardEvent.key === " ") {
          keyboardEvent.preventDefault();
          stopPlayback();
          renderPlaybackStep(index);
        }
      });
      eventList.appendChild(row);
    });
  }

  var nodes = Array.prototype.slice.call(document.querySelectorAll(".flow-node[data-node-id]"));
  nodes.forEach(function (nodeEl) {
    decorateNode(nodeEl, byId.get(nodeEl.getAttribute("data-node-id")));
    nodeEl.addEventListener("click", function () {
      stopPlayback();
      clearPlaybackHighlights();
      selectNode(nodeEl, false);
    });
    nodeEl.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        stopPlayback();
        clearPlaybackHighlights();
        selectNode(nodeEl, false);
      }
    });
  });

  chooseDefaultFilter();
  filterInputs.forEach(function (input) {
    input.addEventListener("change", function () {
      stopPlayback();
      applyFilter();
    });
  });
  filteredEvents = runtimeEvents.slice();
  if (filterInputs.length) {
    filteredEvents = runtimeEvents.filter(function (event) {
      return eventMatchesFilter(event, selectedFilter());
    });
  }
  renderEventList();
  if (firstButton) {
    firstButton.addEventListener("click", function () {
      stopPlayback();
      renderPlaybackStep(0);
    });
  }
  if (prevButton) {
    prevButton.addEventListener("click", function () {
      stopPlayback();
      renderPlaybackStep(playbackIndex - 1);
    });
  }
  if (nextButton) {
    nextButton.addEventListener("click", function () {
      stopPlayback();
      renderPlaybackStep(playbackIndex + 1);
    });
  }
  if (toggleButton) {
    toggleButton.addEventListener("click", function () {
      if (playbackTimer) {
        stopPlayback();
      } else {
        startPlayback();
      }
    });
  }
  if (speedSelect) {
    speedSelect.addEventListener("change", function () {
      if (playbackTimer) {
        stopPlayback();
        startPlayback();
      }
    });
  }

  var startNode = document.querySelector(".flow-node[data-node-id='PROGRAM_START']");
  if (filteredEvents.length && filteredEvents[0].event !== "runtime_skipped") {
    renderPlaybackStep(0);
  } else if (startNode) {
    selectNode(startNode, false);
    updateCounter();
    updateEventDetail(filteredEvents[0] || runtimeEvents[0] || null, 0);
  } else {
    updateCounter();
    updateEventDetail(filteredEvents[0] || runtimeEvents[0] || null, 0);
  }
})();
</script>
""".strip()


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
.flow-node{cursor:pointer;outline:none}
.flow-node rect{transition:fill .12s ease,stroke .12s ease,stroke-width .12s ease}
.flow-node:hover rect,.flow-node:focus rect{fill:#eff6ff;stroke:#2563eb;stroke-width:2.4}
.flow-node.selected rect{fill:#dbeafe;stroke:#1d4ed8;stroke-width:3}
.flow-node.node-not-executed rect{stroke-dasharray:5 3}
.flow-node.playback-visited rect{fill:#ecfdf5}.flow-node.playback-current rect{fill:#fef3c7;stroke:#d97706;stroke-width:3.2}
.flow-node.selected.playback-current rect{fill:#fde68a;stroke:#1d4ed8;stroke-width:3.4}
.flow-node.playback-error rect{fill:#fee2e2;stroke:#dc2626;stroke-width:3.2}
.flow-edge.playback-current-edge{stroke:#d97706;stroke-width:3.4}
.flow-node.risk-high rect{stroke:#dc2626}.flow-node.risk-medium rect{stroke:#d97706}.flow-node.risk-low rect{stroke:#16a34a}
.flow-node.role-matched text{font-weight:700}.flow-node.role-missing rect{fill:#fff7ed}.flow-node.role-unexpected rect{fill:#fef2f2}
.playback-panel{border:1px solid #d8dee9;border-radius:8px;background:#fbfcff;padding:12px;margin-top:12px}
.playback-panel h3{margin:0 0 8px}.playback-unavailable{font-weight:700;color:#92400e}
.playback-filters{border:1px solid #e1e6ef;border-radius:6px;background:#fff;margin:10px 0;padding:8px 10px}
.playback-filters legend{font-weight:700;color:#475569}.playback-filters label{display:inline-flex;align-items:center;gap:5px;margin:3px 12px 3px 0}
.playback-controls{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:10px 0}
.playback-controls button,.playback-controls select{border:1px solid #cbd5e1;border-radius:6px;background:#fff;padding:5px 9px;font:inherit}
.playback-controls button{cursor:pointer}.playback-controls button:disabled,.playback-controls select:disabled,.playback-filters input:disabled{opacity:.55;cursor:not-allowed}
.playback-counter{font-weight:700;color:#475569}
.event-detail{border:1px solid #e1e6ef;border-radius:6px;background:#fff;padding:10px;margin:8px 0}
.event-detail h4{margin:0 0 8px}
.playback-error-text{color:#991b1b;font-weight:700}
.runtime-event-list{max-height:260px;overflow:auto;background:#fff;border:1px solid #e1e6ef;border-radius:6px;padding:8px 8px 8px 30px}
.runtime-event-row{cursor:pointer;border-radius:5px;padding:3px 5px;overflow-wrap:anywhere}
.runtime-event-row:hover,.runtime-event-row:focus{background:#eff6ff;outline:none}.runtime-event-row.current{background:#fef3c7;font-weight:700}
.runtime-event-row.error{color:#991b1b}
.node-legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin:12px 0;color:#475569;font-size:13px}
.node-legend span{display:inline-flex;align-items:center;gap:6px}
.legend-swatch{display:inline-block;width:14px;height:14px;border-radius:3px;border:2px solid #94a3b8;background:#f8fafc}
.legend-swatch.executed{background:#dbeafe;border-color:#1d4ed8}.legend-swatch.not-executed{border-style:dashed}
.legend-swatch.risk-high{border-color:#dc2626}.legend-swatch.intended-matched{background:#dcfce7;border-color:#16a34a}
.legend-swatch.intended-missing{background:#fff7ed;border-color:#d97706}.legend-swatch.intended-unexpected{background:#fef2f2;border-color:#dc2626}
.node-panel{border:1px solid #d8dee9;border-radius:8px;background:#fbfcff;padding:14px;margin-top:12px}
.node-panel h3{margin:0 0 8px;overflow-wrap:anywhere}.node-panel h4{margin:14px 0 6px}
.node-panel-badges{display:flex;flex-wrap:wrap;gap:7px;margin:8px 0 12px}
.node-panel-badges span{border-radius:999px;padding:3px 9px;font-weight:700;font-size:12px;border:1px solid #d8dee9}
.node-panel-badges .risk-high{background:#fee2e2;color:#991b1b}.node-panel-badges .risk-medium{background:#fef3c7;color:#92400e}
.node-panel-badges .risk-low{background:#dcfce7;color:#166534}.node-panel-badges .risk-none{background:#eef2f7;color:#475569}
.node-panel-badges .executed,.node-panel-badges .role-matched{background:#dcfce7;color:#166534}
.node-panel-badges .not-executed,.node-panel-badges .role-none{background:#eef2f7;color:#475569}
.node-panel-badges .role-missing{background:#fff7ed;color:#9a3412}.node-panel-badges .role-unexpected{background:#fee2e2;color:#991b1b}
.node-kv{display:grid;grid-template-columns:minmax(140px,220px) minmax(0,1fr);gap:4px 10px;margin:8px 0}
.node-kv-row{display:contents}.node-kv dt{font-weight:700;color:#667085}.node-kv dd{margin:0;overflow-wrap:anywhere}
.node-panel pre{background:#eef2f7;border-radius:6px;padding:9px;overflow:auto;max-height:260px;white-space:pre-wrap}
.source-snippet-meta{color:#475569;font-size:13px;margin:4px 0 6px}
.source-snippet{display:block;max-height:360px;overflow:auto;border:1px solid #e1e6ef;border-radius:6px;background:#fff;font-family:Consolas,Menlo,monospace;font-size:12px}
.source-snippet tbody{display:table;width:100%;border-collapse:collapse}
.source-snippet td{border-bottom:0;padding:1px 6px;vertical-align:top}
.source-snippet .line-number{width:52px;text-align:right;color:#64748b;background:#f8fafc;user-select:none}
.source-snippet .line-text{white-space:pre;overflow-wrap:normal}
.source-snippet .focus-line .line-number,.source-snippet .focus-line .line-text{background:#fef3c7;color:#111827;font-weight:700}
.var-changes-section{margin:10px 0}
.var-changes-line-label{font-size:12px;color:#667085;margin:8px 0 4px;font-family:Consolas,Menlo,monospace}
.var-change-table{width:100%;border-collapse:collapse;font-family:Consolas,Menlo,monospace;font-size:12px}
.var-change-table th{color:#667085;font-weight:700;padding:4px 6px;border-bottom:1px solid #e1e6ef}
.var-change-table td{padding:3px 6px;border-bottom:1px solid #f1f5f9;overflow-wrap:anywhere}
.var-change-table td:first-child{color:#1d4ed8}
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
.node-panel{break-inside:avoid;page-break-inside:avoid}
}
""".strip()
