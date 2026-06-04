# FlowTrace

FlowTrace is a local Python CLI tool that analyzes and runs a target Python script, then writes static and runtime flow reports.

V0.1 is intentionally small and standard-library-only. It parses Python files with `ast`, runs the entry script with `sys.settrace`, captures project-local function calls, and writes reports into `flowtrace_output`.

## Normal Usage

```powershell
python -m flowtrace.cli --entry sample_project\main.py
```

Runtime mode executes the target script. Use it only when you are comfortable with the target code running normally, including side effects such as writing files, sending messages, accessing email APIs, making network calls, prompting for auth, or waiting for input.

Optional project root and output directory:

```powershell
python -m flowtrace.cli --entry sample_project\main.py --project-root sample_project --output flowtrace_output
```

## Static-Only Usage

Use static-only mode for real projects that may send email, create drafts, call Telegram, require auth, write logs, or wait for user input.

```powershell
python -m flowtrace.cli --entry sample_project\main.py --static-only
```

Static-only mode still writes all report files, but marks runtime as skipped.

## Target Args Usage

Pass arguments to the target script without shell execution:

```powershell
python -m flowtrace.cli --entry project\main.py --target-args "scan-inbox --limit 5"
```

## Error Case Usage

FlowTrace catches runtime errors from the target script and still writes reports.

```powershell
python -m flowtrace.cli --entry sample_project\error_case.py
```

The generated `report.md` shows `Runtime completed: False` and lists the runtime error path.

Dependency or import failures are labeled in the report:

```powershell
python -m flowtrace.cli --entry sample_project\import_error_case.py
```

FlowTrace reports `Dependency/import error` and suggests installing the missing package in the Python environment used to run FlowTrace.

If a target run is interrupted, FlowTrace labels it `Runtime interrupted` and notes that the target may have waited for input/auth or was manually stopped.

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

Intended flow comparison ignores module-level runtime events such as `main.<module>` by default. Raw runtime outputs still keep those events.

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
- Supports static-only analysis for safer first passes on real projects.
- Supports simple target argument passthrough with `--target-args`.

## Constraints

FlowTrace V0.1 has no web UI, AI integration, SaaS layer, editor, animation, database, plugin system, paid dependency, or external service integration.

## Limitations

- Static call resolution is best effort only.
- Imported local calls are resolved for simple cases such as `from worker import build_message`.
- Dynamic imports, monkey patching, decorators, aliases through containers, and complex package layouts may not resolve perfectly.
- Runtime tracing only records functions inside the selected project root.
- Runtime mode executes target code and can trigger target side effects.
- Static-only mode skips runtime tracing, so runtime call graphs show a skipped-runtime marker instead of target calls.
- Intended flow comparison ignores module-level events by default.
- Intended flow comparison is textual and does not include a visual editor.
