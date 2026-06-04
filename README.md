# FlowTrace

FlowTrace is a local Python CLI tool that analyzes and runs a target Python script, then writes static and runtime flow reports.

V0.1 is intentionally small and standard-library-only. It parses Python files with `ast`, runs the entry script with `sys.settrace`, captures project-local function calls, and writes reports into `flowtrace_output`.

## Normal Usage

```powershell
python -m flowtrace.cli --entry sample_project\main.py
```

Optional project root and output directory:

```powershell
python -m flowtrace.cli --entry sample_project\main.py --project-root sample_project --output flowtrace_output
```

## Error Case Usage

FlowTrace catches runtime errors from the target script and still writes reports.

```powershell
python -m flowtrace.cli --entry sample_project\error_case.py
```

The generated `report.md` shows `Runtime completed: False` and lists the runtime error path.

## Intended Flow Usage

You can compare the actual runtime order against a small JSON expectation file:

```powershell
python -m flowtrace.cli --entry sample_project\main.py --intended-flow sample_project\intended_flow.json
```

Expected flow format:

```json
{
  "name": "sample_flow",
  "expected_runtime_order": [
    "main.main",
    "main.load_name"
  ]
}
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

FlowTrace V0.1 has no web UI, AI integration, SaaS layer, editor, animation, database, plugin system, paid dependency, or external service integration.

## Limitations

- Static call resolution is best effort only.
- Imported local calls are resolved for simple cases such as `from worker import build_message`.
- Dynamic imports, monkey patching, decorators, aliases through containers, and complex package layouts may not resolve perfectly.
- Runtime tracing only records functions inside the selected project root.
- Intended flow comparison is textual and does not include a visual editor.
