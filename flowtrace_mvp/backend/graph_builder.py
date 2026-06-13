"""Build the FlowTrace GraphModel from Python source and runtime trace events.

This module is Step 1 of the React Flow graph rebuild. It deliberately avoids
new dependencies and returns a plain dict matching the contract in CLAUDE.md.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from typing import Any, Iterable

GraphDict = dict[str, Any]
USER_NEW_VALUE = "(new)"


class _ReadWriteVisitor(ast.NodeVisitor):
    """Collect variable names read and written inside an AST subtree."""

    def __init__(self) -> None:
        """Create empty read/write name sets."""
        self.reads: set[str] = set()
        self.writes: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802 - ast visitor API
        """Record name usage by context."""
        if isinstance(node.ctx, ast.Load):
            self.reads.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.writes.add(node.id)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:  # noqa: N802 - ast visitor API
        """Treat function arguments as written local names."""
        self.writes.add(node.arg)
        self.generic_visit(node)


def build_graph_model(source_code: str, trace_events: list[dict]) -> GraphDict:
    """Return a GraphModel dict for source code plus tracer events.

    The GraphModel keeps static AST nodes visible while overlaying runtime data
    from trace events. Runtime arrows are compressed by source-target node pair,
    and each compressed edge stores pass-level changed variable details.
    """
    lines = source_code.splitlines()
    tree = ast.parse(source_code, filename="<flowtrace_user_code>")
    statements = list(_iter_statement_nodes(tree))
    nodes = _build_nodes(statements, lines, trace_events)
    line_to_node_id = _first_node_id_by_line(nodes)

    groups = _build_groups(statements, nodes)
    _assign_node_groups(nodes, groups)

    static_edges = _build_static_edges(tree, line_to_node_id)
    runtime_edges = _build_runtime_edges(trace_events, line_to_node_id)
    edges = _merge_edges(static_edges, runtime_edges)

    _apply_group_runtime_stats(groups, nodes)

    return {"nodes": nodes, "edges": edges, "groups": groups}


def _iter_statement_nodes(tree: ast.AST) -> Iterable[ast.stmt]:
    """Yield AST statement nodes in source order, including nested bodies."""

    def visit_body(body: list[ast.stmt]) -> Iterable[ast.stmt]:
        for stmt in body:
            yield stmt
            for nested_body in _child_statement_bodies(stmt):
                yield from visit_body(nested_body)

    if isinstance(tree, ast.Module):
        yield from visit_body(tree.body)


def _child_statement_bodies(stmt: ast.stmt) -> list[list[ast.stmt]]:
    """Return statement-list children for a statement node."""
    bodies: list[list[ast.stmt]] = []
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        bodies.append(stmt.body)
    elif isinstance(stmt, ast.If):
        bodies.extend([stmt.body, stmt.orelse])
    elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
        bodies.extend([stmt.body, stmt.orelse])
    elif isinstance(stmt, ast.Try):
        bodies.append(stmt.body)
        for handler in stmt.handlers:
            bodies.append(handler.body)
        bodies.extend([stmt.orelse, stmt.finalbody])
    elif isinstance(stmt, (ast.With, ast.AsyncWith)):
        bodies.append(stmt.body)
    elif isinstance(stmt, ast.Match):
        for case in stmt.cases:
            bodies.append(case.body)
    return [body for body in bodies if body]


def _build_nodes(statements: list[ast.stmt], lines: list[str], trace_events: list[dict]) -> list[GraphDict]:
    """Create GraphModel node dicts from AST statements."""
    execution_counts = _node_execution_counts(trace_events)
    line_seen: Counter[int] = Counter()
    nodes: list[GraphDict] = []
    for stmt in sorted(statements, key=lambda item: (getattr(item, "lineno", 0), getattr(item, "col_offset", 0))):
        line = int(getattr(stmt, "lineno"))
        line_seen[line] += 1
        node_id = f"n_{line}" if line_seen[line] == 1 else f"n_{line}_{line_seen[line]}"
        execution_count = execution_counts.get(line, 0)
        nodes.append(
            {
                "id": node_id,
                "line": line,
                "code": _source_line(lines, line),
                "type": _node_type(stmt),
                "group_id": None,
                "executed": execution_count > 0,
                "execution_count": execution_count,
            }
        )
    return nodes


def _first_node_id_by_line(nodes: list[GraphDict]) -> dict[int, str]:
    """Map each source line to the first node created for that line."""
    result: dict[int, str] = {}
    for node in nodes:
        result.setdefault(node["line"], node["id"])
    return result


def _node_execution_counts(trace_events: list[dict]) -> Counter[int]:
    """Estimate source-line execution counts from runtime transition events."""
    counts: Counter[int] = Counter()
    for event in trace_events:
        for key in ("from_line", "to_line"):
            line = event.get(key)
            if isinstance(line, int):
                counts[line] += 1
    return counts


def _source_line(lines: list[str], line: int) -> str:
    """Return a stripped source line for a 1-based line number."""
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return f"line {line}"


def _node_type(stmt: ast.stmt) -> str:
    """Map an AST statement to a GraphModel node type."""
    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return "assignment"
    if isinstance(stmt, ast.If):
        return "condition"
    if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
        return "loop_header"
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return "function_def"
    if isinstance(stmt, ast.Return):
        return "return"
    if isinstance(stmt, ast.Expr):
        return "print" if _is_print_expr(stmt) else "call"
    return "call"


def _is_print_expr(stmt: ast.Expr) -> bool:
    """Return True when an expression statement calls print(...)."""
    value = stmt.value
    return isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "print"


def _build_groups(statements: list[ast.stmt], nodes: list[GraphDict]) -> list[GraphDict]:
    """Create loop, if, and function groups from AST statement ranges."""
    groups: list[GraphDict] = []
    node_lines = {node["line"]: node for node in nodes}

    for stmt in statements:
        group_type = _group_type(stmt)
        if group_type is None:
            continue
        start = int(getattr(stmt, "lineno"))
        end = int(getattr(stmt, "end_lineno", start))
        node_ids = [node["id"] for line, node in sorted(node_lines.items()) if start <= line <= end]
        if not node_ids:
            continue
        reads, writes = _read_write_names(stmt)
        groups.append(
            {
                "id": f"g_{group_type}_{start}",
                "type": group_type,
                "label": _group_label(stmt),
                "node_ids": node_ids,
                "execution_count": 0,
                "input_vars": sorted(reads - writes),
                "output_vars": sorted(writes),
                "status": "not_executed",
                "_start_line": start,
                "_end_line": end,
            }
        )
    groups.sort(key=lambda group: (group["_start_line"], group["_end_line"]))
    return groups


def _group_type(stmt: ast.stmt) -> str | None:
    """Return the GraphModel group type for groupable AST statements."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return "function"
    if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
        return "loop"
    if isinstance(stmt, ast.If):
        return "if_block"
    return None


def _group_label(stmt: ast.stmt) -> str:
    """Return a short label for a group header."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return f"def {stmt.name}(...)"
    if isinstance(stmt, (ast.For, ast.AsyncFor)):
        return f"for {_safe_unparse(stmt.target)} in {_safe_unparse(stmt.iter)}"
    if isinstance(stmt, ast.While):
        return f"while {_safe_unparse(stmt.test)}"
    if isinstance(stmt, ast.If):
        return f"if {_safe_unparse(stmt.test)}"
    return stmt.__class__.__name__


def _safe_unparse(node: ast.AST) -> str:
    """Best-effort AST unparse for compact labels."""
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - defensive only
        return node.__class__.__name__


def _read_write_names(node: ast.AST) -> tuple[set[str], set[str]]:
    """Return variable names read and written in an AST subtree."""
    visitor = _ReadWriteVisitor()
    visitor.visit(node)
    return visitor.reads, visitor.writes


def _assign_node_groups(nodes: list[GraphDict], groups: list[GraphDict]) -> None:
    """Assign each node to its innermost containing group when applicable."""
    groups_by_depth = sorted(
        groups,
        key=lambda group: (group["_end_line"] - group["_start_line"], group["_start_line"]),
    )
    for node in nodes:
        line = node["line"]
        for group in groups_by_depth:
            # Header nodes remain outside their own group so they can act as
            # visible collapsed-group entry points in the frontend.
            if group["_start_line"] < line <= group["_end_line"]:
                node["group_id"] = group["id"]
                break


def _build_static_edges(tree: ast.AST, line_to_node_id: dict[int, str]) -> dict[tuple[int, int], GraphDict]:
    """Build a best-effort static control-flow edge map."""
    edges: dict[tuple[int, int], GraphDict] = {}

    def add(source_line: int | None, target_line: int | None) -> None:
        if source_line is None or target_line is None:
            return
        if source_line not in line_to_node_id or target_line not in line_to_node_id:
            return
        key = (source_line, target_line)
        edges.setdefault(
            key,
            {
                "id": f"e_{source_line}_{target_line}",
                "source": line_to_node_id[source_line],
                "target": line_to_node_id[target_line],
                "is_static": True,
                "is_executed": False,
                "execution_count": 0,
                "events": [],
            },
        )

    def walk_body(body: list[ast.stmt], next_after_body: ast.stmt | None = None) -> None:
        for index, stmt in enumerate(body):
            next_stmt = body[index + 1] if index + 1 < len(body) else next_after_body
            stmt_line = getattr(stmt, "lineno", None)
            next_line = getattr(next_stmt, "lineno", None) if next_stmt is not None else None

            if isinstance(stmt, ast.If):
                if stmt.body:
                    add(stmt_line, getattr(stmt.body[0], "lineno", None))
                    walk_body(stmt.body, next_stmt)
                else:
                    add(stmt_line, next_line)
                if stmt.orelse:
                    add(stmt_line, getattr(stmt.orelse[0], "lineno", None))
                    walk_body(stmt.orelse, next_stmt)
                else:
                    add(stmt_line, next_line)
            elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                if stmt.body:
                    add(stmt_line, getattr(stmt.body[0], "lineno", None))
                    walk_body(stmt.body, stmt)
                add(stmt_line, next_line)
                if stmt.orelse:
                    add(stmt_line, getattr(stmt.orelse[0], "lineno", None))
                    walk_body(stmt.orelse, next_stmt)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                add(stmt_line, next_line)
                walk_body(stmt.body, None)
            else:
                add(stmt_line, next_line)
                for nested in _child_statement_bodies(stmt):
                    walk_body(nested, next_stmt)

    if isinstance(tree, ast.Module):
        walk_body(tree.body)
    return edges


def _build_runtime_edges(trace_events: list[dict], line_to_node_id: dict[int, str]) -> dict[tuple[int, int], GraphDict]:
    """Compress runtime transition events into GraphModel edges."""
    edges: dict[tuple[int, int], GraphDict] = {}
    previous_snapshots = _previous_snapshots(trace_events)

    for event in trace_events:
        from_line = event.get("from_line")
        to_line = event.get("to_line")
        if not isinstance(from_line, int) or not isinstance(to_line, int):
            continue
        if from_line not in line_to_node_id or to_line not in line_to_node_id:
            continue

        key = (from_line, to_line)
        edge = edges.setdefault(
            key,
            {
                "id": f"e_{from_line}_{to_line}",
                "source": line_to_node_id[from_line],
                "target": line_to_node_id[to_line],
                "is_static": False,
                "is_executed": True,
                "execution_count": 0,
                "events": [],
            },
        )
        edge["execution_count"] += 1
        edge["events"].append(
            {
                "pass": edge["execution_count"],
                "changed_vars": _before_after_changed_vars(event, previous_snapshots.get(id(event), {})),
                "stdout": event.get("stdout") or None,
                "error": event.get("error"),
            }
        )
    return edges


def _previous_snapshots(trace_events: list[dict]) -> dict[int, dict[str, str]]:
    """Map each event object to the locals snapshot before it occurred."""
    result: dict[int, dict[str, str]] = {}
    previous: dict[str, str] = {}
    for event in trace_events:
        result[id(event)] = previous
        snapshot = event.get("locals_snapshot")
        if isinstance(snapshot, dict):
            previous = snapshot
    return result


def _before_after_changed_vars(event: dict, previous_snapshot: dict[str, str]) -> dict[str, dict[str, str]]:
    """Return changed vars in GraphModel before/after form."""
    changed = event.get("changed_vars") or {}
    formatted: dict[str, dict[str, str]] = {}
    for name, after_value in changed.items():
        formatted[name] = {
            "before": previous_snapshot.get(name, USER_NEW_VALUE),
            "after": after_value,
        }
    return formatted


def _merge_edges(
    static_edges: dict[tuple[int, int], GraphDict],
    runtime_edges: dict[tuple[int, int], GraphDict],
) -> list[GraphDict]:
    """Merge static control edges with compressed runtime observations."""
    merged: dict[tuple[int, int], GraphDict] = {key: dict(value) for key, value in static_edges.items()}
    for key, runtime_edge in runtime_edges.items():
        if key in merged:
            merged[key].update(
                {
                    "is_executed": True,
                    "execution_count": runtime_edge["execution_count"],
                    "events": runtime_edge["events"],
                }
            )
        else:
            merged[key] = runtime_edge
    return [merged[key] for key in sorted(merged)]


def _apply_group_runtime_stats(groups: list[GraphDict], nodes: list[GraphDict]) -> None:
    """Set group execution counts and statuses from child nodes."""
    node_by_id = {node["id"]: node for node in nodes}
    for group in groups:
        child_nodes = [node_by_id[node_id] for node_id in group["node_ids"] if node_id in node_by_id]
        execution_count = max((node["execution_count"] for node in child_nodes), default=0)
        group["execution_count"] = execution_count
        group["status"] = "completed" if execution_count > 0 else "not_executed"
        group.pop("_start_line", None)
        group.pop("_end_line", None)
