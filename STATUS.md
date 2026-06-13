# FlowTrace Build Status

## Current step
Step 1 - GraphModel builder baseline added, awaiting Codex verification/refinement

## Progress
- [ ] Step 1: graph_builder.py
- [ ] Step 2: /api/graph endpoint
- [ ] Step 3: Frontend scaffold
- [ ] Step 4: CodeNode.jsx
- [ ] Step 5: FlowEdge.jsx
- [ ] Step 6: InspectorPanel.jsx
- [ ] Step 7: GroupNode.jsx
- [ ] Step 8: App.jsx

## Last Codex output
None yet for the React Flow graph rebuild.

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

The new Step 1 baseline has not yet been run locally by Codex. Treat it as an implementation draft, not a verified step.

## Notes
Assumptions in the Step 1 baseline:
- `trace_events` are the existing tracer events from `flowtrace_mvp/backend/tracer.py`.
- Static edges are best-effort control-flow edges, not true data-dependency arrows.
- Runtime edges are compressed by `(from_line, to_line)`.
- Node execution counts are estimated from trace transition line appearances.
- Group `input_vars` and `output_vars` are AST read/write estimates.
- Group collapse behavior will be handled later in the React Flow frontend steps.

Codex: run compile/tests, fix failures, update this file, and only then mark Step 1 complete.
