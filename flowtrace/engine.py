"""Core analysis engine for FlowTrace."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Symbol:
    kind: str
    name: str
    line: int


@dataclass(frozen=True)
class Call:
    name: str
    line: int


@dataclass(frozen=True)
class TraceResult:
    entry: str
    symbols: list[Symbol]
    calls: list[Call]
    imports: list[str]


class FlowTraceError(Exception):
    """Raised when FlowTrace cannot analyze an entry file."""


def analyze_entry(entry: str | Path) -> TraceResult:
    entry_path = Path(entry)
    if not entry_path.exists():
        raise FlowTraceError(f"Entry file does not exist: {entry_path}")
    if not entry_path.is_file():
        raise FlowTraceError(f"Entry path is not a file: {entry_path}")

    source = entry_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(entry_path))
    except SyntaxError as exc:
        raise FlowTraceError(f"Could not parse {entry_path}: {exc}") from exc

    visitor = _TraceVisitor()
    visitor.visit(tree)
    return TraceResult(
        entry=str(entry_path),
        symbols=visitor.symbols,
        calls=visitor.calls,
        imports=visitor.imports,
    )


def write_outputs(result: TraceResult, output_dir: str | Path = "flowtrace_output") -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / "trace.json"
    markdown_path = output_path / "trace.md"

    json_path.write_text(
        json.dumps(_to_jsonable(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown_path.write_text(_to_markdown(result), encoding="utf-8")
    return [json_path, markdown_path]


class _TraceVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.symbols: list[Symbol] = []
        self.calls: list[Call] = []
        self.imports: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.extend(alias.name for alias in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        self.imports.extend(_format_import_from(module, alias.name) for alias in node.names)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.symbols.append(Symbol(kind="function", name=node.name, line=node.lineno))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.symbols.append(Symbol(kind="async_function", name=node.name, line=node.lineno))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(Symbol(kind="class", name=node.name, line=node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(Call(name=_call_name(node.func), line=node.lineno))
        self.generic_visit(node)


def _format_import_from(module: str, name: str) -> str:
    return f"{module}.{name}" if module else name


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return "<unknown>"


def _to_jsonable(result: TraceResult) -> dict[str, object]:
    return {
        "entry": result.entry,
        "symbols": [asdict(symbol) for symbol in result.symbols],
        "calls": [asdict(call) for call in result.calls],
        "imports": result.imports,
    }


def _to_markdown(result: TraceResult) -> str:
    lines = [
        "# FlowTrace Report",
        "",
        f"Entry: `{result.entry}`",
        "",
        "## Imports",
        *_format_lines(result.imports),
        "",
        "## Symbols",
        *_format_lines(f"{symbol.kind} `{symbol.name}` at line {symbol.line}" for symbol in result.symbols),
        "",
        "## Calls",
        *_format_lines(f"`{call.name}` at line {call.line}" for call in result.calls),
        "",
    ]
    return "\n".join(lines)


def _format_lines(items: Iterable[str]) -> list[str]:
    values = list(items)
    if not values:
        return ["- None"]
    return [f"- {item}" for item in values]
