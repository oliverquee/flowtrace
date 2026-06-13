# FlowTrace Build Status

## Current step
Step 2 - /api/graph endpoint complete

## Progress
- [x] Step 1: graph_builder.py
- [x] Step 2: /api/graph endpoint
- [ ] Step 3: Frontend scaffold
- [ ] Step 4: CodeNode.jsx
- [ ] Step 5: FlowEdge.jsx
- [ ] Step 6: InspectorPanel.jsx
- [ ] Step 7: GroupNode.jsx
- [ ] Step 8: App.jsx

## Last Codex output
Patched and verified Step 2 backend readiness for the upcoming Vite frontend.

What was checked:
- `/api/graph` response shape remains unchanged.
- `/health` is registered as a GET endpoint and returns `{"status": "ok"}`.
- CORS allows the existing local MVP origins and Vite dev origins on port 5173.
- `TraceRequest` accepts `code` only.
- `TraceRequest` accepts `code` plus optional `stdin`.
- Existing `/api/graph` tests still pass.
- Existing `/api/trace` tests still pass.

Fix applied:
- Added Vite frontend origins to CORS.
- Added the `/health` readiness endpoint.
- Added optional `stdin` to the API request model without wiring it into runner execution.
- Added dependency-free backend tests for readiness behavior.

Verification:
- `python -m compileall flowtrace_mvp` passed.
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

Step 1 and Step 2 are verified. Do not start Step 3 until explicitly requested.

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

Codex completed the Step 2 readiness patch and did not start Step 3.
