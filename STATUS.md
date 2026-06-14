# FlowTrace Build Status

## Current step
Step 7 - GroupNode.jsx complete

## Progress
- [x] Step 1: graph_builder.py
- [x] Step 2: /api/graph endpoint
- [x] Step 3: Frontend scaffold
- [x] Step 4: CodeNode.jsx
- [x] Step 5: FlowEdge.jsx
- [x] Step 6: InspectorPanel.jsx
- [x] Step 7: GroupNode.jsx
- [ ] Step 8: App.jsx

## Last Codex output
Built and verified the Step 7 `GroupNode.jsx` collapsible group node component.

What was checked:
- `GroupNode.jsx` is a stateless React Flow node.
- It uses top target and bottom source handles.
- It renders loop, function, and if-block group icons and dashed borders.
- It shows run count, input/output variables, status badge, and expand/collapse button.
- Expansion remains parent-controlled through `isExpanded` and `onToggle(id)`.
- No API calls, App wiring, or Step 8 work were added.

Fix applied:
- Added `flowtrace_mvp/frontend/src/components/GroupNode.jsx`.
- Added minimal GroupNode CSS while preserving existing custom properties and global scaffold styling.

Verification:
- `npm run build` passed.
- `python -m pytest flowtrace_mvp/tests` passed with 24 tests.

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

Step 1, Step 2, Step 3, Step 4, Step 5, Step 6, and Step 7 are verified. Do not start Step 8 until explicitly requested.

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
- React Flow and Dagre are installed but not wired into app logic yet.
- `CodeNode.jsx` is implemented but not wired into `App.jsx` yet; wiring is deferred to a later step.
- `FlowEdge.jsx` is implemented but not wired into `App.jsx` yet; wiring is deferred to a later step.
- `InspectorPanel.jsx` is implemented but not wired into `App.jsx` yet; wiring is deferred to a later step.
- `GroupNode.jsx` is implemented but not wired into `App.jsx` yet; wiring is deferred to Step 8.

Codex completed the Step 7 GroupNode component and did not start Step 8.
