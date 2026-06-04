"""Static-vs-runtime comparison helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from .runtime_tracer import RuntimeTraceResult
from .static_analyzer import CallRecord, FunctionRecord, SideEffectRecord, StaticAnalysisResult


@dataclass(frozen=True)
class RiskyUnexecutedFunction:
    function_id: str
    file: str
    line: int
    side_effects: list[SideEffectRecord]


@dataclass(frozen=True)
class StaticCallNotObserved:
    caller: str
    callee: str
    call: str
    file: str
    line: int


@dataclass
class StaticRuntimeComparison:
    static_functions: list[str] = field(default_factory=list)
    runtime_functions: list[str] = field(default_factory=list)
    executed_static_functions: list[str] = field(default_factory=list)
    static_functions_not_executed: list[str] = field(default_factory=list)
    runtime_functions_without_static_definition: list[str] = field(default_factory=list)
    risky_unexecuted_functions: list[RiskyUnexecutedFunction] = field(default_factory=list)
    static_resolved_calls_not_observed: list[StaticCallNotObserved] = field(default_factory=list)
    comparison_unavailable: bool = False
    comparison_unavailable_reason: str | None = None
    partial_runtime: bool = False


def build_static_runtime_comparison(
    static_result: StaticAnalysisResult,
    runtime_result: RuntimeTraceResult,
) -> StaticRuntimeComparison:
    static_functions = sorted(function.id for function in static_result.functions)
    runtime_functions = _runtime_functions(runtime_result)
    static_function_set = set(static_functions)
    runtime_function_set = set(runtime_functions)

    if runtime_result.runtime_skipped:
        return StaticRuntimeComparison(
            static_functions=static_functions,
            runtime_functions=[],
            comparison_unavailable=True,
            comparison_unavailable_reason="Runtime was skipped, so execution comparison is unavailable.",
        )

    static_not_executed = sorted(static_function_set - runtime_function_set)
    function_by_id = {function.id: function for function in static_result.functions}
    side_effects_by_function = _side_effects_by_function(static_result.side_effects)

    return StaticRuntimeComparison(
        static_functions=static_functions,
        runtime_functions=runtime_functions,
        executed_static_functions=sorted(static_function_set & runtime_function_set),
        static_functions_not_executed=static_not_executed,
        runtime_functions_without_static_definition=sorted(runtime_function_set - static_function_set),
        risky_unexecuted_functions=_risky_unexecuted_functions(
            static_not_executed,
            function_by_id,
            side_effects_by_function,
        ),
        static_resolved_calls_not_observed=_static_resolved_calls_not_observed(
            static_result.calls,
            static_function_set,
            runtime_function_set,
        ),
        partial_runtime=runtime_result.runtime_attempted and not runtime_result.completed,
    )


def _runtime_functions(runtime_result: RuntimeTraceResult) -> list[str]:
    seen: set[str] = set()
    functions: list[str] = []
    for event in runtime_result.events:
        if event.event != "function_enter" or event.function.endswith(".<module>"):
            continue
        if event.function not in seen:
            seen.add(event.function)
            functions.append(event.function)
    return functions


def _side_effects_by_function(side_effects: list[SideEffectRecord]) -> dict[str, list[SideEffectRecord]]:
    grouped: dict[str, list[SideEffectRecord]] = {}
    for item in side_effects:
        if item.in_function:
            grouped.setdefault(item.in_function, []).append(item)
    return grouped


def _risky_unexecuted_functions(
    static_not_executed: list[str],
    function_by_id: dict[str, FunctionRecord],
    side_effects_by_function: dict[str, list[SideEffectRecord]],
) -> list[RiskyUnexecutedFunction]:
    risky_functions: list[RiskyUnexecutedFunction] = []
    for function_id in static_not_executed:
        risky_side_effects = [
            item
            for item in side_effects_by_function.get(function_id, [])
            if _side_effect_risk(item) in {"high", "medium"}
        ]
        if not risky_side_effects:
            continue
        function = function_by_id[function_id]
        risky_functions.append(
            RiskyUnexecutedFunction(
                function_id=function_id,
                file=function.file,
                line=function.line,
                side_effects=risky_side_effects,
            )
        )
    return risky_functions


def _static_resolved_calls_not_observed(
    calls: list[CallRecord],
    static_function_set: set[str],
    runtime_function_set: set[str],
) -> list[StaticCallNotObserved]:
    not_observed: list[StaticCallNotObserved] = []
    for call in calls:
        if not call.in_function or not call.resolved_function_id:
            continue
        if call.in_function not in static_function_set or call.resolved_function_id not in static_function_set:
            continue
        if call.in_function in runtime_function_set and call.resolved_function_id not in runtime_function_set:
            not_observed.append(
                StaticCallNotObserved(
                    caller=call.in_function,
                    callee=call.resolved_function_id,
                    call=call.name,
                    file=call.file,
                    line=call.line,
                )
            )
    return not_observed


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
