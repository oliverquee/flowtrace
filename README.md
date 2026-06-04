# FlowTrace

FlowTrace is a local Python CLI tool that analyzes and runs a target Python script, then writes static and runtime flow reports.

V0.1 is intentionally small and standard-library-only. It parses Python files with `ast`, runs the entry script with `sys.settrace`, captures project-local function calls, and writes reports into `flowtrace_output`.

## Usage

```powershell
python -m flowtrace.cli --entry sample_project\main.py
```

Optional project root and output directory:

```powershell
python -m flowtrace.cli --entry sample_project\main.py --project-root sample_project --output flowtrace_output
```

## Outputs

- `flowtrace_output/static_graph.json`
- `flowtrace_output/runtime_trace.jsonl`
- `flowtrace_output/runtime_graph.json`
- `flowtrace_output/report.md`
- `flowtrace_output/flow.mmd`

## V0.1 Scope

- Reads a Python entry file.
- Uses the entry file parent as the project root unless `--project-root` is provided.
- Parses `.py` files inside the project root.
- Detects imports, functions, arguments, calls, assignments, variable reads, return statements, and obvious side-effect calls.
- Runs the entry script with runtime tracing.
- Captures project-local function enter, exit, error, and caller to callee relationships.
- Handles runtime errors and still writes reports.

## Constraints

FlowTrace V0.1 has no web UI, AI integration, animation, database, paid dependency, or external service integration.
