# FlowTrace Project Status

## Stable Baseline

- Current stable branch: main
- Current stable version: V0.1.3
- Latest stable commit: 6462b61
- V0.1.4 is in progress on feature branches for CLI command profiling and target args reporting.

## Current Tested Commands

```powershell
python -m flowtrace.cli --entry sample_project\main.py
python -m flowtrace.cli --entry sample_project\main.py --static-only
python -m flowtrace.cli --entry sample_project\error_case.py
python -m flowtrace.cli --entry sample_project\import_error_case.py
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
