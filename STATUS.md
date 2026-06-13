# FlowTrace Build Status

## Current step
Step 1 - GraphModel builder complete

## Progress
- [x] Step 1: graph_builder.py
- [ ] Step 2: /api/graph endpoint
- [ ] Step 3: Frontend scaffold
- [ ] Step 4: CodeNode.jsx
- [ ] Step 5: FlowEdge.jsx
- [ ] Step 6: InspectorPanel.jsx
- [ ] Step 7: GroupNode.jsx
- [ ] Step 8: App.jsx

## Last Codex output
Verified and refined Step 1 locally.

What was checked:
- `build_graph_model(source_code, trace_events)` returns a plain dict with only `nodes`, `edges`, and `groups`.
- Node, edge, edge-event, and group fields match the `CLAUDE.md` GraphModel contract.
- Runtime edges are compressed by source-target pair.
- Loop repeated edges preserve one event per pass and an execution count.
- Changed variables are converted from tracer snapshot form into `{ before, after }`.
- Non-executed branches remain present as nodes with `executed = false`.
- Helper-only group fields are removed before output.

Fix applied:
- Same-line AST statements now create distinct nodes instead of being collapsed by source line.

Verification:
- `python -m compileall flowtrace_mvp` passed.
- `python -m pytest flowtrace_mvp/tests` passed with 14 tests.

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

Step 1 is verified. Do not start Step 2 until explicitly requested.

## Notes
Assumptions in the Step 1 baseline:
- `trace_events` are the existing tracer events from `flowtrace_mvp/backend/tracer.py`.
- Static edges are best-effort control-flow edges, not true data-dependency arrows.
- Runtime edges are compressed by `(from_line, to_line)`.
- Node execution counts are estimated from trace transition line appearances.
- Group `input_vars` and `output_vars` are AST read/write estimates.
- Group collapse behavior will be handled later in the React Flow frontend steps.
- If multiple AST statements start on the same source line, the first keeps `n_<line>` and later nodes receive suffixes such as `n_<line>_2`.

Codex completed Step 1 verification and did not start Step 2.
