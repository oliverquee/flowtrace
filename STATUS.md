# FlowTrace Build Status

## Current step
Step 8 - App.jsx wiring complete

## Progress
- [x] Step 1: graph_builder.py
- [x] Step 2: /api/graph endpoint
- [x] Step 3: Frontend scaffold
- [x] Step 4: CodeNode.jsx
- [x] Step 5: FlowEdge.jsx
- [x] Step 6: InspectorPanel.jsx
- [x] Step 7: GroupNode.jsx
- [x] Step 8: App.jsx

## Last Codex output
Built and verified the Step 8 React Flow demo app wiring.

What was checked:
- `App.jsx` preloads a transcript-style Python sample.
- `Run Trace` posts to `http://localhost:8000/api/graph`.
- The backend GraphModel is converted into React Flow nodes and edges.
- Dagre lays the graph out top-down.
- CodeNode, FlowEdge, GroupNode, and InspectorPanel are wired together.
- Clicking an edge opens the inspector with before/after changed values.
- Stdout and backend/API errors are shown clearly.
- Backend-not-reachable error messaging was verified.

Fix applied:
- Replaced the placeholder app with the wired React Flow demo.
- Added app layout CSS for the top bar, editor panel, graph canvas, stdout, and messages.
- Added a FlowEdge click hitbox so selecting graph edges reliably opens the inspector.
- Added `flowtrace_mvp/DEMO.md`.

Verification:
- `npm run build` passed.
- `python -m pytest flowtrace_mvp/tests` passed with 24 tests.
- Manual browser check passed on `http://127.0.0.1:5173`.
- Sample graph rendered in 875 ms during the browser check.

## Last ChatGPT baseline output
Added an initial `flowtrace_mvp/backend/graph_builder.py` and `flowtrace_mvp/tests/test_graph_builder.py` baseline for Step 1.

The builder is intended to:
- parse Python source with `ast`
- create one GraphModel node per AST statement
- create loop, if_block, and function groups
- overlay existing tracer `trace_events`
- compress repeated runtime edges
- convert changed variables into `{ before, after }` event payloads

This baseline was committed through GitHub without local execution. Codex must run tests, correct edge cases, and mark Step 1 complete only if verification passes.

## Known issues
The current plain HTML MVP shows a linear trace list, not the intended graph/circuit view. The next build must create a proper GraphModel before frontend graph rendering.

All planned build steps are verified complete.

## Notes
Assumptions in the Step 1 baseline:
- `trace_events` are the existing tracer events from `flowtrace_mvp/backend/tracer.py`.
- Static edges are best-effort control-flow edges, not true data-dependency arrows.
- Runtime edges are compressed by `(from_line, to_line)`.
- Node execution counts are estimated from trace transition line appearances.
- Group `input_vars` and `output_vars` are AST read/write estimates.
- Group collapse behavior will be handled later in the React Flow frontend steps.
- If multiple AST statements start on the same source line, the first keeps `n_<line>` and later nodes receive suffixes such as `n_<line>_2`.
- `/api/graph` is intentionally a thin adapter over `run_trace_subprocess` plus `build_graph_model`; it does not execute pasted code in the FastAPI process.
- API tests call endpoint functions directly because this environment's FastAPI TestClient path requires an extra `httpx2` package, and no new dependencies were approved for Step 2.
- Vite frontend origins are allowed by CORS: `http://127.0.0.1:5173` and `http://localhost:5173`.
- `/health` exists for simple backend readiness checks.
- `stdin` is accepted by the request model but is not wired into runner execution yet.
- Step 3 used Vite defaults and did not add a custom `vite.config.js`.
- React Flow, Dagre, CodeNode, FlowEdge, InspectorPanel, and GroupNode are wired into `App.jsx`.
- Group nodes are rendered as summary nodes, but collapsed groups do not yet hide or re-route their child nodes.
- Group expand/collapse changes group visual state and does not crash the app.
- Source/target node highlighting is not implemented yet; selected edge highlighting is implemented.

Codex completed Step 8 and the planned React Flow demo build.
