"""Optional intended-flow comparison support."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .runtime_tracer import RuntimeTraceResult
from .utils import FlowTraceError


@dataclass
class IntendedFlowComparison:
    name: str | None = None
    expected_runtime_order: list[str] = field(default_factory=list)
    actual_runtime_order: list[str] = field(default_factory=list)
    missing_expected_functions: list[str] = field(default_factory=list)
    unexpected_actual_functions: list[str] = field(default_factory=list)
    order_mismatch_summary: str = "No intended flow provided."

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "expected_runtime_order": self.expected_runtime_order,
            "actual_runtime_order": self.actual_runtime_order,
            "missing_expected_functions": self.missing_expected_functions,
            "unexpected_actual_functions": self.unexpected_actual_functions,
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
    if not flow_path.exists():
        raise FlowTraceError(f"Intended flow file does not exist: {flow_path}")

    try:
        data = json.loads(flow_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FlowTraceError(f"Could not parse intended flow JSON: {exc}") from exc

    expected_order = _expected_order(data)
    missing = [name for name in expected_order if name not in actual_order]
    unexpected = [name for name in actual_order if name not in expected_order]
    summary = _order_summary(expected_order, actual_order, missing)

    return IntendedFlowComparison(
        name=data.get("name"),
        expected_runtime_order=expected_order,
        actual_runtime_order=actual_order,
        missing_expected_functions=missing,
        unexpected_actual_functions=unexpected,
        order_mismatch_summary=summary,
    )


def _expected_order(data: dict[str, Any]) -> list[str]:
    value = data.get("expected_runtime_order", [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise FlowTraceError("Intended flow expected_runtime_order must be a list of strings.")
    return value


def _order_summary(expected_order: list[str], actual_order: list[str], missing: list[str]) -> str:
    if missing:
        return f"Missing expected function(s): {', '.join(missing)}"
    actual_positions = [actual_order.index(name) for name in expected_order]
    if actual_positions != sorted(actual_positions):
        return "Expected functions were found but executed in a different relative order."
    unexpected_count = len([name for name in actual_order if name not in expected_order])
    if unexpected_count:
        return f"Expected order matched; {unexpected_count} additional function(s) executed."
    return "Expected order matched exactly."
