# Codex Status

## Branch

```text
feature/mvp-runtime-edge-values
```

## Starting commit hash

```text
a34fd2f4ec15820ba6d5072037bab3b4b20d85a5
```

## Scope

Worked only inside:

```text
flowtrace_mvp/
docs/CODEX_STATUS.md
```

The old `flowtrace/` CLI/report implementation was not modified.

## Files changed

```text
docs/CODEX_STATUS.md
flowtrace_mvp/README.md
flowtrace_mvp/backend/app.py
flowtrace_mvp/backend/runner.py
flowtrace_mvp/backend/tracer.py
flowtrace_mvp/tests/test_tracer.py
```

## Implementation summary

- Added `flowtrace_mvp/backend/runner.py`.
- Routed FastAPI `/api/trace` through the subprocess runner instead of calling `trace_code` directly in the server process.
- The runner accepts pasted code, launches a separate Python subprocess, enforces a default 5 second timeout, captures stdout/stderr, and returns the same response shape: `nodes`, `edges`, `trace_events`, `stdout`, and `error`.
- Kept `trace_code` usable directly for tests.
- Added an internal tracing deadline so runaway line tracing can return a timeout error before producing an oversized trace.
- Updated README safety notes to explain local subprocess execution and the remaining non-sandbox risk.

## Commands run

### `python -m compileall flowtrace_mvp`

Status: PASS

Output summary:

```text
Listing 'flowtrace_mvp'...
Listing 'flowtrace_mvp\\backend'...
Compiling 'flowtrace_mvp\\backend\\app.py'...
Compiling 'flowtrace_mvp\\backend\\runner.py'...
Compiling 'flowtrace_mvp\\backend\\tracer.py'...
Listing 'flowtrace_mvp\\samples'...
Listing 'flowtrace_mvp\\static'...
Listing 'flowtrace_mvp\\tests'...
Compiling 'flowtrace_mvp\\tests\\test_tracer.py'...
```

### `python -m pytest flowtrace_mvp/tests`

Status: PASS

Output summary:

```text
platform win32 -- Python 3.14.5, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\FlowTrace
plugins: anyio-4.13.0
collected 6 items

flowtrace_mvp\tests\test_tracer.py ......                                [100%]

6 passed in 1.07s
```

### `python -m uvicorn flowtrace_mvp.backend.app:app --reload`

Status: PASS for startup confirmation

Output summary:

```text
INFO:     Will watch for changes in these directories: ['D:\\FlowTrace']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [27632] using StatReload
INFO:     Started server process [11196]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
process_running_after_5s=True
```

The server was stopped after startup confirmation.

## Test coverage added

- Runtime exception through subprocess runner.
- Timeout through subprocess runner using `while True: pass`.
- Stdout capture through subprocess runner.
- Existing assignment, if branch, and loop tests still pass.

## Manual checks

### Requested URL

```text
http://127.0.0.1:8000
```

The exact uvicorn startup command starts successfully on port 8000. During repeated manual timeout checks, Windows intermittently reported a stale listener on port 8000 owned by PID `19244`, while process APIs could not inspect or kill that PID:

```text
LocalAddress LocalPort State  OwningProcess
127.0.0.1    8000      Listen 19244
```

This made the 8000 timeout browser/API check unreliable in this session. The code-level timeout behavior was therefore verified through tests, direct runner checks, and a supplemental current-app run on port 8001.

### Supplemental current-app check on port 8001

Status: PASS

Output summary:

```json
{
  "page_status": 200,
  "sample_loaded": true,
  "blocks": 3,
  "arrows": 3,
  "final_changed_vars": {
    "y": "7"
  },
  "stdout": "hello stdout\n",
  "timeout_elapsed": 5.13,
  "timeout_error_type": "TimeoutError",
  "timeout_error_message": "Execution timed out after 5 seconds."
}
```

### Headless browser check on port 8001

Status: PASS

Output summary:

```json
{
  "title": "FlowTrace MVP",
  "blocks": 3,
  "arrows": 2,
  "inspector_after_arrow_click": "line 1 -> line 2event 0x = 5",
  "stdout_after_print": "hello stdout\n"
}
```

## Bugs found

- Pasted code was executed directly in the FastAPI process via `trace_code`.
- The first subprocess timeout implementation relied only on the parent process timeout. The direct runner timeout worked, but HTTP timeout verification exposed that runaway line tracing could still make the local server check unreliable in this Windows session.
- Port 8000 had an intermittent stale listener during manual verification.

## Exact error messages

Port 8000 stale listener symptom:

```text
Invoke-WebRequest : The request was aborted: The operation has timed out.
```

Port ownership check:

```text
LocalAddress LocalPort State  OwningProcess
127.0.0.1    8000      Listen 19244
```

## Fixes applied

- Added subprocess runner with timeout and stderr capture.
- Routed `/api/trace` through `run_trace_subprocess`.
- Added child-side trace deadline for long-running code.
- Added subprocess runner tests for runtime exception, timeout, and stdout.
- Updated README safety note.

## Remaining risks

- This is safer than in-process execution, but it is not a full sandbox.
- Pasted code still runs locally with the user's machine permissions while the subprocess is alive.
- The timeout is a guardrail, not a security boundary.
- Port 8000 had a stale Windows listener during verification; if it reappears, stop the stale process or use another local port for testing.

## Runnable status

The MVP is runnable locally when port 8000 is free:

```powershell
python -m uvicorn flowtrace_mvp.backend.app:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```
