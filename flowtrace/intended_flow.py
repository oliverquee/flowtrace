"""Optional intended-flow comparison support."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .runtime_tracer import RuntimeTraceResult


@dataclass
class OrderMismatch:
    expected_index: int
    expected_function: str
    actual_index: int | None
    actual_function: str | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "expected_index": self.expected_index,
            "expected_function": self.expected_function,
            "actual_index": self.actual_index,
            "actual_function": self.actual_function,
            "message": self.message,
        }


@dataclass
class IntendedFlowComparison:
    name: str | None = None
    expected_runtime_order: list[str] = field(default_factory=list)
    actual_runtime_order: list[str] = field(default_factory=list)
    validation_ok: bool = True
    validation_errors: list[str] = field(default_factory=list)
    comparison_available: bool = False
    comparison_unavailable_reason: str | None = "No intended flow provided."
    partial_runtime: bool = False
    matched_functions: list[str] = field(default_factory=list)
    missing_expected_functions: list[str] = field(default_factory=list)
    unexpected_actual_functions: list[str] = field(default_factory=list)
    order_mismatches: list[OrderMismatch] = field(default_factory=list)
    first_mismatch_index: int | None = None
    status: str = "unavailable"
    summary: str = "No intended flow provided."
    order_mismatch_summary: str = "No intended flow provided."

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "expected_runtime_order": self.expected_runtime_order,
            "actual_runtime_order": self.actual_runtime_order,
            "validation_ok": self.validation_ok,
            "validation_errors": self.validation_errors,
            "comparison_available": self.comparison_available,
            "comparison_unavailable_reason": self.comparison_unavailable_reason,
            "partial_runtime": self.partial_runtime,
            "matched_functions": self.matched_functions,
            "missing_expected_functions": self.missing_expected_functions,
            "unexpected_actual_functions": self.unexpected_actual_functions,
            "order_mismatches": [item.to_dict() for item in self.order_mismatches],
            "first_mismatch_index": self.first_mismatch_index,
            "status": self.status,
            "summary": self.summary,
            "order_mismatch_summary": self.order_mismatch_summary,
        }


def compare_intended_flow(path: str | Path | None, runtime_result: RuntimeTraceResult) -> IntendedFlowComparison:
    actual_order = [
        event.function
        for event in runtime_result.events
        if event.event == "function_enter" and not event.function.endswith(".<module>")
    ]
    if not path:
        return IntendedFlowComparison(actual_runtime_order=actual_order)

    flow_path = Path(path).resolve()
    data, validation_errors = _load_and_validate(flow_path)
    if validation_errors:
        summary = "Intended-flow validation failed."
        return IntendedFlowComparison(
            actual_runtime_order=actual_order,
            validation_ok=False,
            validation_errors=validation_errors,
            comparison_available=False,
            comparison_unavailable_reason=summary,
            status="invalid",
            summary=summary,
            order_mismatch_summary=summary,
        )

    expected_order = data["expected_runtime_order"]
    name = data.get("name")

    if runtime_result.runtime_skipped:
        reason = "Runtime was skipped, so intended-flow execution comparison is unavailable."
        return IntendedFlowComparison(
            name=name,
            expected_runtime_order=expected_order,
            actual_runtime_order=actual_order,
            comparison_available=False,
            comparison_unavailable_reason=reason,
            status="unavailable",
            summary=reason,
            order_mismatch_summary=reason,
        )

    return _compare_valid_flow(
        name=name,
        expected_order=expected_order,
        actual_runtime_order=actual_order,
        runtime_completed=runtime_result.completed,
    )


def _load_and_validate(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Intended flow file does not exist: {path}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Could not parse intended flow JSON: {exc}"]

    errors: list[str] = []
    if not isinstance(data, dict):
        return {}, ["Intended flow JSON root must be an object."]

    if "name" in data and not isinstance(data["name"], str):
        errors.append("Intended flow name must be a string when provided.")

    if "expected_runtime_order" not in data:
        errors.append("Intended flow expected_runtime_order is required.")
    elif not isinstance(data["expected_runtime_order"], list):
        errors.append("Intended flow expected_runtime_order must be a list.")
    else:
        for index, item in enumerate(data["expected_runtime_order"]):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"expected_runtime_order[{index}] must be a non-empty string.")

    return data, errors


def _compare_valid_flow(
    name: str | None,
    expected_order: list[str],
    actual_runtime_order: list[str],
    runtime_completed: bool,
) -> IntendedFlowComparison:
    missing = [name for name in expected_order if name not in actual_runtime_order]
    unexpected = [name for name in actual_runtime_order if name not in expected_order]
    matched = [name for name in expected_order if name in actual_runtime_order]
    order_mismatches, first_mismatch_index = _order_mismatches(expected_order, actual_runtime_order)
    summary = _summary(expected_order, actual_runtime_order, missing, unexpected, order_mismatches, runtime_completed)
    status = "matched" if not missing and not unexpected and not order_mismatches else "mismatch"

    return IntendedFlowComparison(
        name=name,
        expected_runtime_order=expected_order,
        actual_runtime_order=actual_runtime_order,
        comparison_available=True,
        comparison_unavailable_reason=None,
        partial_runtime=not runtime_completed,
        matched_functions=matched,
        missing_expected_functions=missing,
        unexpected_actual_functions=unexpected,
        order_mismatches=order_mismatches,
        first_mismatch_index=first_mismatch_index,
        status=status,
        summary=summary,
        order_mismatch_summary=summary,
    )


def _order_mismatches(expected_order: list[str], actual_order: list[str]) -> tuple[list[OrderMismatch], int | None]:
    actual_expected_only = [name for name in actual_order if name in expected_order]
    expected_present = [name for name in expected_order if name in actual_order]
    if actual_expected_only == expected_present:
        return [], None

    mismatches: list[OrderMismatch] = []
    first_mismatch_index: int | None = None
    max_len = max(len(expected_present), len(actual_expected_only))
    for index in range(max_len):
        expected_function = expected_present[index] if index < len(expected_present) else ""
        actual_function = actual_expected_only[index] if index < len(actual_expected_only) else None
        if expected_function != actual_function:
            if first_mismatch_index is None:
                first_mismatch_index = index
            actual_index = actual_order.index(actual_function) if actual_function in actual_order else None
            mismatches.append(
                OrderMismatch(
                    expected_index=index,
                    expected_function=expected_function,
                    actual_index=actual_index,
                    actual_function=actual_function,
                    message=f"Expected {expected_function or 'end of expected flow'} but saw {actual_function or 'end of runtime flow'}.",
                )
            )
    return mismatches, first_mismatch_index


def _summary(
    expected_order: list[str],
    actual_order: list[str],
    missing: list[str],
    unexpected: list[str],
    order_mismatches: list[OrderMismatch],
    runtime_completed: bool,
) -> str:
    if expected_order == actual_order:
        return "Expected flow matched exactly."
    if not runtime_completed and missing and _is_prefix_match(expected_order, actual_order):
        return "Expected flow partially matched, but runtime stopped before completing all expected steps."
    if missing:
        return f"Expected function {missing[0]} was missing from runtime trace."
    if order_mismatches:
        return "Expected functions were present but in the wrong order."
    if unexpected:
        return f"Runtime included unexpected function {unexpected[0]}."
    return "Expected flow matched."


def _is_prefix_match(expected_order: list[str], actual_order: list[str]) -> bool:
    actual_expected_only = [name for name in actual_order if name in expected_order]
    return expected_order[: len(actual_expected_only)] == actual_expected_only
