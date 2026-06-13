# Codex Status

## Branch

```text
feature/mvp-runtime-edge-values
```

## Starting commit hash

```text
87a4a3c3a0ee16b4655e7d58f44230d36c22f1d4
```

## Scope

Frontend-only demo polish plus status update.

Allowed paths:

```text
flowtrace_mvp/static/app.js
docs/CODEX_STATUS.md
```

The old `flowtrace/` CLI/report implementation was not modified.

## Files changed

```text
flowtrace_mvp/static/app.js
docs/CODEX_STATUS.md
```

## Implementation summary

- Added before -> after formatting for changed variables in the edge inspector.
- The inspector now formats changed variables as:

```text
x: (new) -> 5
y: (new) -> 7
total: 1 -> 3
```

- Existing empty-state text remains when an edge has no changed variables.
- Existing sample selector, edge selection, execution path row selection, stdout display, runtime error display, timeout display, non-executed branch styling, source/target node highlighting, and first-changed-variable edge labels were preserved.

## Commands run

### `python -m compileall flowtrace_mvp`

Status: PASS

Output summary:

```text
Listing 'flowtrace_mvp'...
Listing 'flowtrace_mvp\\backend'...
Listing 'flowtrace_mvp\\docs'...
Listing 'flowtrace_mvp\\samples'...
Listing 'flowtrace_mvp\\static'...
Listing 'flowtrace_mvp\\tests'...
```

### `python -m pytest flowtrace_mvp/tests`

Status: PASS

Output summary:

```text
platform win32 -- Python 3.14.5, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\FlowTrace
plugins: anyio-4.13.0
collected 6 items

flowtrace_mvp\tests\test_tracer.py ......                                [100%]

6 passed in 1.11s
```

## Manual browser check results

Status: PASS

Used local uvicorn plus headless Microsoft Edge against:

```text
http://127.0.0.1:8000
```

Output summary:

```json
{
  "assignment_status": "Trace complete.",
  "first_edge_has_x_new_to_5": true,
  "second_edge_has_y_new_to_7": true,
  "selected_edge_count": 1,
  "source_node_highlight_count": 1,
  "target_node_highlight_count": 1,
  "path_row_click_has_y_new_to_7": true,
  "path_row_selected_count": 1,
  "loop_status": "Trace complete.",
  "loop_has_before_after_total": true,
  "loop_inspector": "total: 0 -> 1",
  "loop_selected_edge_count": 1,
  "loop_source_node_highlight_count": 1,
  "loop_target_node_highlight_count": 1,
  "runtime_error_status": "Trace completed with ZeroDivisionError.",
  "runtime_error_clear": true,
  "timeout_status": "Trace completed with TimeoutError.",
  "timeout_clear": true
}
```

Checks:

- Assignment first edge shows `x: (new) -> 5`: PASS
- Assignment second edge shows `y: (new) -> 7`: PASS
- Loop sample shows a before -> after transition such as `total: 1 -> 3`: PASS
- Edge click selects the edge: PASS
- Edge click highlights source node: PASS
- Edge click highlights target node: PASS
- Edge click updates inspector correctly: PASS
- Execution path row click selects the matching edge: PASS
- Execution path row click updates inspector correctly: PASS
- Runtime error sample still shows error clearly: PASS
- Timeout sample still shows timeout clearly: PASS

## Bugs found

- The edge inspector showed changed variable snapshots as `x = 5` instead of transition diffs.

## Fixes applied

- Added `formatTransitionChanges(edge)` in `flowtrace_mvp/static/app.js`.
- The formatter compares `edge.changed_vars` against the previous trace event's `locals_snapshot`.
- Missing previous values are shown as `(new)`.
- ASCII `->` is used.

## Remaining risks

- This remains a local MVP, not a full sandbox.
- Timeout is a guardrail, not a security boundary.
- Runtime tracing remains line/event based and does not explain all Python semantics.

## Demo-ready status

The browser MVP is demo-ready with before -> after variable transitions in the edge inspector.
