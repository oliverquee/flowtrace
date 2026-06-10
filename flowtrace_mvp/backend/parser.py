"""AST helpers for the local FlowTrace MVP.

This parser intentionally stays narrow. It creates one visual node per
executable source line and leaves deep semantic grouping for later versions.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SourceNode:
    """A visual block generated from one executable source line."""

    id: str
    line: int
    label: str
    type: str
    executed: bool = False


def _statement_type(node: ast.AST) -> str:
    if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
        return "assignment"
    if isinstance(node, ast.If):
        return "if"
    if isinstance(node, ast.For | ast.AsyncFor | ast.While):
        return "loop"
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return "function"
    if isinstance(node, ast.Return):
        return "return"
    if isinstance(node, ast.Expr):
        return "expression"
    if isinstance(node, ast.Import | ast.ImportFrom):
        return "import"
    return node.__class__.__name__.lower()


def _iter_executable_statement_nodes(tree: ast.AST) -> Iterable[ast.stmt]:
    """Yield executable statement nodes in source order.

    ast.walk does not preserve exact execution order, so we recurse through
    statement lists manually. Function bodies are included because they can run
    later and should appear as drillable lines in the MVP graph.
    """

    def visit_statements(statements: list[ast.stmt]) -> Iterable[ast.stmt]:
        for stmt in statements:
            yield stmt
            nested_lists: list[list[ast.stmt]] = []
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nested_lists.append(stmt.body)
            elif isinstance(stmt, ast.If):
                nested_lists.extend([stmt.body, stmt.orelse])
            elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                nested_lists.extend([stmt.body, stmt.orelse])
            elif isinstance(stmt, ast.Try):
                nested_lists.append(stmt.body)
                for handler in stmt.handlers:
                    nested_lists.append(handler.body)
                nested_lists.extend([stmt.orelse, stmt.finalbody])
            elif isinstance(stmt, ast.With | ast.AsyncWith):
                nested_lists.append(stmt.body)
            elif isinstance(stmt, ast.Match):
                for case in stmt.cases:
                    nested_lists.append(case.body)
            for nested in nested_lists:
                yield from visit_statements(nested)

    if isinstance(tree, ast.Module):
        yield from visit_statements(tree.body)


def parse_source_nodes(source: str) -> list[dict]:
    """Return visual source nodes for a Python code string."""

    lines = source.splitlines()
    tree = ast.parse(source, filename="<flowtrace_user_code>")
    seen_lines: set[int] = set()
    nodes: list[SourceNode] = []

    for stmt in _iter_executable_statement_nodes(tree):
        line = getattr(stmt, "lineno", None)
        if not line or line in seen_lines:
            continue
        seen_lines.add(line)
        label = lines[line - 1].strip() if line - 1 < len(lines) else f"line {line}"
        nodes.append(SourceNode(id=f"line_{line}", line=line, label=label, type=_statement_type(stmt)))

    return [node.__dict__ for node in sorted(nodes, key=lambda item: item.line)]
