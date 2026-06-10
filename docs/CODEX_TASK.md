# Codex Task: Verify FlowTrace MVP Runtime Edge Values

## Context

A new local browser MVP has been added under `flowtrace_mvp/`.

Goal:

```text
Paste Python code -> Run Trace -> See blocks -> Click arrow -> See changed variables
```

This is separate from the older FlowTrace CLI/report system.

## Your job

Do not add new product features. First verify and fix the MVP until it runs locally.

## Required commands

Run from repository root:

```powershell
python -m compileall flowtrace_mvp
python -m pip install fastapi uvicorn pytest
python -m pytest flowtrace_mvp/tests
python -m uvicorn flowtrace_mvp.backend.app:app --reload
```

For the uvicorn command, only confirm the server starts. Stop it after confirming.

## Manual browser check

Open:

```text
http://127.0.0.1:8000
```

Check:

1. Page loads.
2. Sample code appears or can be loaded.
3. Run Trace works.
4. Blocks appear.
5. Arrows appear.
6. Clicking an arrow shows changed variables.
7. Stdout appears for `print` output.

## Expected test behavior

### Assignment

```python
x = 5
y = x + 2
```

Expected changed values include:

```text
x = 5
y = 7
```

### If branch

```python
x = 10
if x > 5:
    y = 'big'
else:
    y = 'small'
```

Expected:

```text
y = 'big'
```

The non-executed branch should not appear in the runtime edge path.

### Loop

```python
total = 0
for i in range(3):
    total += i
```

Expected final changed value:

```text
total = 3
```

## Files you may change

Prefer limiting changes to:

```text
flowtrace_mvp/backend/app.py
flowtrace_mvp/backend/parser.py
flowtrace_mvp/backend/tracer.py
flowtrace_mvp/static/index.html
flowtrace_mvp/static/app.js
flowtrace_mvp/static/style.css
flowtrace_mvp/tests/test_tracer.py
flowtrace_mvp/README.md
docs/CODEX_STATUS.md
```

Do not modify the old `flowtrace/` CLI/report implementation unless absolutely necessary, which should not be necessary.

## Required status update

Create or update:

```text
docs/CODEX_STATUS.md
```

Include:

- Branch name
- Commit hash before your work
- Commands run
- Output summary for each command
- Test pass/fail status
- Bugs found
- Files changed
- Exact error messages
- Fixes applied
- Remaining issues
- Whether the MVP is runnable

## Commit

After verification/fixes, commit with:

```text
verify: test MVP runtime edge-value demo
```
