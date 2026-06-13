# FlowTrace Project Brain

## What this is
FlowTrace converts Python code into an interactive flow graph.
User pastes code, backend traces it, frontend renders a graph where nodes are code blocks and arrows are execution transitions.
Clicking an arrow shows what variable values changed on that transition.

## Stack
- Backend: Python, FastAPI
- Frontend: React, Vite, React Flow, Dagre
- Coordination: CLAUDE.md and STATUS.md

## Current repo reality
The existing working MVP currently lives under flowtrace_mvp/.
The older flowtrace/ directory is the legacy CLI/report implementation and must not be modified for this React Flow graph build unless STATUS.md explicitly says so.

## Folder structure
flowtrace_mvp/
  backend/
    tracer.py          - existing; do not modify unless STATUS.md says so
    graph_builder.py   - Step 1
    app.py             - Step 2: add endpoint
  frontend/
    src/
      components/
        CodeNode.jsx       - Step 4
        GroupNode.jsx      - Step 7
        FlowEdge.jsx       - Step 5
        InspectorPanel.jsx - Step 6
      App.jsx              - Step 8
      main.jsx
    package.json

## GraphModel JSON contract
Do not change this contract without updating this file and flagging the change as breaking.

Required top-level fields:
- nodes
- edges
- groups

Node shape:
- id: string, example n_1
- line: number
- code: string
- type: assignment | condition | loop_header | function_def | return | call | print
- group_id: string or null
- executed: boolean
- execution_count: number

Edge shape:
- id: string, example e_1_10
- source: node id
- target: node id
- is_static: boolean
- is_executed: boolean
- execution_count: number
- events: list of pass-level runtime observations

Edge event shape:
- pass: number
- changed_vars: object mapping variable name to { before, after }
- stdout: string or null
- error: string or null

Group shape:
- id: string
- type: loop | if_block | function
- label: string
- node_ids: list of node ids
- execution_count: number
- input_vars: list of strings
- output_vars: list of strings
- status: completed | error | not_executed

## Decisions
1. Static graph plus runtime overlay: executed paths highlighted, rest dimmed.
2. One node per AST statement; functions, loops, and if-blocks auto-group.
3. Arrows are runtime transitions; inspector shows changed variable values per pass.
4. Loop arrows are compressed to one edge with count; click to browse passes.
5. Edge click shows latest pass values, selectable passes, and source/target highlight.
6. Collapsed group shows label, input/output vars, run count, and status.
7. Collapsed arrows connect to group box only; expand button shows inner graph.
8. Layout: top-down using Dagre.
9. Library: React Flow.

## UI spec for first public release
- Dark background: #0f0f0f
- Executed node: green left border #22C55E, full opacity
- Non-executed node: gray border, 0.4 opacity
- Loop group border: #F59E0B dashed
- Function group border: #8B5CF6 dashed
- If group border: #06B6D4 dashed
- Active edge: #4A9EFF solid 2px
- Inactive edge: gray dashed 1px
- Edge count badge: small pill at midpoint, example 6x
- Inspector panel: right sidebar 320px, slides in on edge click
- Font: JetBrains Mono for code, Inter/system-ui for UI
- Sample code pre-loaded on first open, with loop and if block visible immediately

## Build sequence
Step 1: graph_builder.py
Step 2: /api/graph endpoint in app.py
Step 3: Frontend scaffold
Step 4: CodeNode.jsx
Step 5: FlowEdge.jsx
Step 6: InspectorPanel.jsx
Step 7: GroupNode.jsx
Step 8: App.jsx wiring

See STATUS.md for current step.
