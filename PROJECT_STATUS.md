# FlowTrace Project Status

## Stable Baseline

- Current stable branch: main
- Current stable version: V0.7
- Latest stable commit: 013b808

## Current Tested Commands

```powershell
python -m flowtrace.cli --entry sample_project\main.py
python -m flowtrace.cli --entry sample_project\main.py --static-only
python -m flowtrace.cli --entry sample_project\error_case.py
python -m flowtrace.cli --entry sample_project\import_error_case.py
python -m flowtrace.cli --entry sample_project\cli_case.py --target-args "hello --name Pratham"
python -m flowtrace.cli --entry sample_project\cli_case.py --target-args "fail"
python -m flowtrace.cli --entry sample_project\cli_case.py
python -m flowtrace.cli --entry sample_project\cli_case.py --static-only --target-args "hello --name Pratham"
python -m flowtrace.cli --entry sample_project\cli_case.py --target-args "hello --name Pratham" --intended-flow sample_project\cli_case_intended_flow.json
python -m flowtrace.cli --entry sample_project\main.py --capture-variables
```

## Real Project Test

Gmail automation project static-only scan works.

## In Progress





## Known Limitations

- Python only
- Static analysis is best-effort
- Runtime mode executes target code
- Static-only skips runtime behavior
- Import resolution is simple
- Markdown is curated; JSON is raw
- Variable capture is opt-in (--capture-variables), line-granularity, and redacts names matching common secret/credential patterns; values are best-effort repr() and may be truncated.

## Safety Notes

Use `--static-only` first for real projects.
