# FlowTrace MVP: Runtime Edge Values

This folder is a separate local browser MVP for the new FlowTrace direction.

## Product slice

Paste Python code, run a local trace, see source lines as blocks, click arrows, and inspect variables that changed between two executed lines.

## MVP rule

For this version:

> Arrow value = changed variables between two executed user-code lines.

It does not yet capture invisible intermediate values inside one expression, object mutation diffs, library internals, or full function-level semantic grouping.

## Run locally

From the repository root:

```powershell
python -m pip install fastapi uvicorn pytest
python -m uvicorn flowtrace_mvp.backend.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Test locally

```powershell
python -m pytest flowtrace_mvp/tests
```

## Current scope

Works toward:

- pasted Python code
- simple assignments
- if branches
- basic loops
- stdout capture
- runtime errors with partial trace
- clickable runtime arrows

Not in scope yet:

- SaaS
- auth
- payment
- GitHub import
- executing untrusted code on a server
- Docker sandboxing
- AI explanation
- visual flowchart editing
- version comparison
- multi-language support

## Safety note

This MVP executes pasted Python code locally. Do not run unknown code. For future SaaS usage, runtime execution must be moved into a real sandbox.
