"""Build enriched node details for future clickable graph review."""

from __future__ import annotations

from .diagnostics import DiagnosticsResult
from .graph_builder import PROGRAM_START, RUNTIME_SKIPPED
from .intended_flow import IntendedFlowComparison
from .runtime_tracer import RuntimeTraceResult
from .static_analyzer import FunctionRecord, SideEffectRecord, StaticAnalysisResult


def build_node_details(
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
    runtime_graph: dict[str, object],
    diagnostics: DiagnosticsResult,
    intended_comparison: IntendedFlowComparison,
) -> list[dict[str, object]]:
    functions_by_id = {function.id: function for function in static_result.functions}
    modules_by_id = _module_nodes(static_result)
    runtime_nodes = _runtime_node_ids(runtime_graph)
    all_ids = sorted(set(functions_by_id) | set(modules_by_id) | runtime_nodes | {PROGRAM_START})

    runtime_order, runtime_counts = _runtime_order(runtime_result)
    static_incoming, static_outgoing = _static_call_maps(static_result)
    runtime_incoming, runtime_outgoing = _runtime_call_maps(runtime_graph)
    side_effects_by_scope = _side_effects_by_scope(diagnostics.side_effect_calls)
    intended_roles = _intended_roles(intended_comparison)

    return [
        _node_record(
            node_id=node_id,
            function=functions_by_id.get(node_id),
            module=modules_by_id.get(node_id),
            runtime_graph=runtime_graph,
            runtime_order=runtime_order,
            runtime_counts=runtime_counts,
            static_incoming=static_incoming,
            static_outgoing=static_outgoing,
            runtime_incoming=runtime_incoming,
            runtime_outgoing=runtime_outgoing,
            side_effects=side_effects_by_scope.get(node_id, []),
            diagnostics=_diagnostics_for_node(node_id, diagnostics),
            intended_flow_role=intended_roles.get(node_id, "none"),
        )
        for node_id in all_ids
        if node_id
    ]


def _node_record(
    node_id: str,
    function: FunctionRecord | None,
    module: dict[str, object] | None,
    runtime_graph: dict[str, object],
    runtime_order: dict[str, int],
    runtime_counts: dict[str, int],
    static_incoming: dict[str, list[dict[str, object]]],
    static_outgoing: dict[str, list[dict[str, object]]],
    runtime_incoming: dict[str, list[dict[str, object]]],
    runtime_outgoing: dict[str, list[dict[str, object]]],
    side_effects: list[SideEffectRecord],
    diagnostics: dict[str, object],
    intended_flow_role: str,
) -> dict[str, object]:
    side_effect_dicts = [item.__dict__ for item in side_effects]
    return {
        "id": node_id,
        "label": _label(node_id),
        "node_type": _node_type(node_id, function, module, runtime_graph),
        "file": function.file if function else (str(module.get("file", "")) if module else _runtime_file(node_id, runtime_graph)),
        "line": function.line if function else (module.get("line") if module else None),
        "args": function.args if function else [],
        "executed": runtime_counts.get(node_id, 0) > 0,
        "runtime_first_seen_index": runtime_order.get(node_id),
        "runtime_call_count": runtime_counts.get(node_id, 0),
        "incoming_static_calls": static_incoming.get(node_id, []),
        "outgoing_static_calls": static_outgoing.get(node_id, []),
        "incoming_runtime_calls": runtime_incoming.get(node_id, []),
        "outgoing_runtime_calls": runtime_outgoing.get(node_id, []),
        "side_effects": side_effect_dicts,
        "highest_risk_level": _highest_risk_level(side_effects),
        "diagnostics": diagnostics,
        "intended_flow_role": intended_flow_role,
    }


def _module_nodes(static_result: StaticAnalysisResult) -> dict[str, dict[str, object]]:
    return {
        f"{file.module}.<module>": {"file": file.path, "line": 1}
        for file in static_result.files
        if file.module
    }


def _runtime_node_ids(runtime_graph: dict[str, object]) -> set[str]:
    nodes: set[str] = set()
    for item in runtime_graph.get("nodes", []):
        if isinstance(item, dict) and item.get("id"):
            nodes.add(str(item["id"]))
    return nodes


def _runtime_order(runtime_result: RuntimeTraceResult) -> tuple[dict[str, int], dict[str, int]]:
    first_seen: dict[str, int] = {}
    counts: dict[str, int] = {}
    index = 0
    for event in runtime_result.events:
        if event.event != "function_enter":
            continue
        index += 1
        counts[event.function] = counts.get(event.function, 0) + 1
        first_seen.setdefault(event.function, index)
    return first_seen, counts


def _static_call_maps(static_result: StaticAnalysisResult) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    incoming: dict[str, list[dict[str, object]]] = {}
    outgoing: dict[str, list[dict[str, object]]] = {}
    for call in static_result.calls:
        if not call.in_function or not call.resolved_function_id:
            continue
        record = {
            "caller": call.in_function,
            "callee": call.resolved_function_id,
            "call": call.name,
            "file": call.file,
            "line": call.line,
        }
        outgoing.setdefault(call.in_function, []).append(record)
        incoming.setdefault(call.resolved_function_id, []).append(record)
    return incoming, outgoing


def _runtime_call_maps(runtime_graph: dict[str, object]) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    incoming: dict[str, list[dict[str, object]]] = {}
    outgoing: dict[str, list[dict[str, object]]] = {}
    for edge in runtime_graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        caller = str(edge.get("caller", ""))
        callee = str(edge.get("callee", ""))
        if not caller or not callee:
            continue
        record = {"caller": caller, "callee": callee, "count": edge.get("count", 1)}
        outgoing.setdefault(caller, []).append(record)
        incoming.setdefault(callee, []).append(record)
    return incoming, outgoing


def _side_effects_by_scope(side_effects: list[SideEffectRecord]) -> dict[str, list[SideEffectRecord]]:
    grouped: dict[str, list[SideEffectRecord]] = {}
    for item in side_effects:
        scope = item.in_function or _module_id_for_file(item.file)
        grouped.setdefault(scope, []).append(item)
    return grouped


def _diagnostics_for_node(node_id: str, diagnostics: DiagnosticsResult) -> dict[str, object]:
    assigned_unread = [
        item.__dict__
        for item in diagnostics.assigned_variables_never_read
        if item.in_function == node_id or (item.in_function is None and _module_id_for_file(item.file) == node_id)
    ]
    imports_unused = [
        item.__dict__
        for item in diagnostics.imports_unused
        if _module_id_for_file(item.file) == node_id
    ]
    runtime_errors = [
        item for item in diagnostics.runtime_error_path if item.get("function") == node_id
    ]
    return {
        "defined_but_not_executed": node_id in diagnostics.functions_defined_but_not_executed,
        "no_runtime_callers": node_id in diagnostics.functions_with_no_runtime_callers,
        "imports_unused": imports_unused,
        "assigned_variables_never_read": assigned_unread,
        "runtime_errors": runtime_errors,
    }


def _intended_roles(comparison: IntendedFlowComparison) -> dict[str, str]:
    roles = {name: "expected" for name in comparison.expected_runtime_order}
    for name in comparison.matched_functions:
        roles[name] = "matched"
    for name in comparison.missing_expected_functions:
        roles[name] = "missing"
    for name in comparison.unexpected_actual_functions:
        roles[name] = "unexpected"
    return roles


def _node_type(
    node_id: str,
    function: FunctionRecord | None,
    module: dict[str, object] | None,
    runtime_graph: dict[str, object],
) -> str:
    if node_id == PROGRAM_START:
        return "program_start"
    if node_id == RUNTIME_SKIPPED:
        return "runtime_skipped"
    if module or node_id.endswith(".<module>"):
        return "module"
    if function:
        return "function"
    if node_id in _runtime_node_ids(runtime_graph):
        return "unknown_runtime"
    return "function"


def _runtime_file(node_id: str, runtime_graph: dict[str, object]) -> str:
    for item in runtime_graph.get("nodes", []):
        if isinstance(item, dict) and item.get("id") == node_id:
            return str(item.get("file", ""))
    return ""


def _module_id_for_file(file_path: str) -> str:
    module = file_path.rsplit(".", 1)[0].replace("/", ".").replace("\\", ".")
    return f"{module}.<module>"


def _label(node_id: str) -> str:
    if node_id == PROGRAM_START:
        return "PROGRAM_START"
    if node_id == RUNTIME_SKIPPED:
        return "RUNTIME_SKIPPED"
    return node_id.rsplit(".", 1)[-1] if "." in node_id and not node_id.endswith(".<module>") else node_id


def _highest_risk_level(side_effects: list[SideEffectRecord]) -> str:
    risks = [_side_effect_risk(item) for item in side_effects]
    if "high" in risks:
        return "high"
    if "medium" in risks:
        return "medium"
    if "low" in risks:
        return "low"
    return "none"


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
