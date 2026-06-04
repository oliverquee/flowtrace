# FlowTrace Project Status

## Stable Baseline

- Current stable branch: main
- Current stable version: V0.1.4
- Latest stable commit: a04a7d9
- V0.1.5 is in progress on feature branches for static-vs-runtime comparison improvements.

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

## Known Limitations

- Python only
- Static analysis is best-effort
- Runtime mode executes target code
- Static-only skips runtime behavior
- Import resolution is simple
- Markdown is curated; JSON is raw

## Safety Notes

Use `--static-only` first for real projects.
