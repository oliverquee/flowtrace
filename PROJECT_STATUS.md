# FlowTrace Project Status

## Stable Baseline

- Current stable branch: main
- Current stable version: V0.4
- Latest stable commit: bf62e11

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
```

## Real Project Test

Gmail automation project static-only scan works.

## In Progress

- V0.5: Local interactive HTML node inspection is in progress on a feature branch. This is not yet claimed as stable.

## Known Limitations

- Python only
- Static analysis is best-effort
- Runtime mode executes target code
- Static-only skips runtime behavior
- Import resolution is simple
- Markdown is curated; JSON is raw

## Safety Notes

Use `--static-only` first for real projects.
