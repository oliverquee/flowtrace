# Codex Status

## Branch

```text
feature/mvp-runtime-edge-values
```

## Starting commit hash

```text
740f9a1267d4d8aa1e4330881fcaa9205ece952c
```

## Scope

Worked only inside:

```text
flowtrace_mvp/
docs/CODEX_STATUS.md
```

The old `flowtrace/` CLI/report implementation was not modified.

## Files changed

```text
docs/CODEX_STATUS.md
flowtrace_mvp/static/app.js
flowtrace_mvp/static/index.html
flowtrace_mvp/static/style.css
```

## Implementation summary

- Added five built-in frontend samples:
  - Assignment
  - If branch
  - Loop
  - Runtime error
  - Timeout
- Added a sample selector and load button.
- Expanded the edge inspector to show:
  - event id
  - from line
  - to line
  - source code for from line
  - source code for to line
  - changed variables
  - locals snapshot
  - stdout at that moment
  - terminal edge flag
  - loop-back edge flag
- Added an execution path panel with ordered runtime event rows.
- Clicking an execution path row selects the matching edge and updates the inspector.
- Added visual classes for executed nodes, non-executed nodes, selected edges, loop-back edges, and terminal edges.
- Preserved the existing API response shape.

## Commands run

### `python -m compileall flowtrace_mvp`

Status: PASS

Output summary:

```text
Listing 'flowtrace_mvp'...
Listing 'flowtrace_mvp\\backend'...
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

6 passed in 1.12s
```

### `python -m uvicorn flowtrace_mvp.backend.app:app --reload`

Status: PASS

Output summary:

```text
HTTP status: 200
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [34284] using StatReload
INFO:     Started server process [34964]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Server was stopped after startup confirmation.

## Manual browser check results

Used installed Microsoft Edge in headless mode through the Chrome DevTools Protocol against:

```text
http://127.0.0.1:8000
```

Status: PASS

Output summary:

```json
{
  "title": "FlowTrace MVP",
  "sample_count": 5,
  "assignment": {
    "status": "Trace complete.",
    "blocks": 3,
    "arrows": 2,
    "stdout": "7\n",
    "error": ""
  },
  "edge_click_inspector_contains_y7": true,
  "path_row_click_inspector_contains_y7": true,
  "if_branch": {
    "status": "Trace complete.",
    "blocks": 5,
    "arrows": 3,
    "non_executed_nodes": 1,
    "stdout": "big\n",
    "error": ""
  },
  "loop": {
    "status": "Trace complete.",
    "blocks": 4,
    "arrows": 8,
    "loop_edges": 3,
    "stdout": "3\n",
    "error": ""
  },
  "runtime_error": {
    "status": "Trace completed with ZeroDivisionError.",
    "blocks": 3,
    "arrows": 1,
    "non_executed_nodes": 1
  },
  "timeout": {
    "status": "Trace completed with TimeoutError.",
    "blocks": 2,
    "arrows": 0,
    "error": "Execution timed out after 5 seconds."
  }
}
```

Checklist:

- Page loads: PASS
- Each sample loads: PASS
- Run Trace works for Assignment: PASS
- Run Trace works for If branch: PASS
- Run Trace works for Loop: PASS
- Runtime error sample shows error clearly: PASS
- Timeout sample returns timeout error clearly: PASS
- Clicking an edge updates the inspector: PASS
- Clicking an execution path row selects the edge: PASS
- Stdout appears when present: PASS
- Non-executed else branch remains visually distinct from executed path: PASS

## Bugs found

- The previous single-sample UI was too thin for demos.
- The old edge inspector only showed changed variables, so users could not see source-line context, locals snapshots, stdout-at-event, or edge flags.
- There was no ordered execution path panel.
- Selected edges and loop-back/terminal edges were not visually distinct enough.

## Fixes applied

- Added multiple built-in samples in frontend JavaScript.
- Added sample selector UI in HTML.
- Added richer edge inspector rendering.
- Added execution path panel and row-to-edge selection.
- Added CSS states for executed, non-executed, selected, loop-back, and terminal elements.

## Remaining risks

- This is still a local MVP, not a sandboxed execution environment.
- Timeout is a guardrail, not a full security boundary.
- The UI is intentionally plain HTML/CSS/JS and not yet a full editor.
- Runtime tracing remains line/event based and does not explain complex Python semantics.

## Demo-ready status

The local browser MVP is demo-ready for V0.1.2 clarity checks.

Run:

```powershell
python -m uvicorn flowtrace_mvp.backend.app:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```
