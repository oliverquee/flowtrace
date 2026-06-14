# FlowTrace MVP Demo

## What the demo does
FlowTrace lets you paste Python code, run it locally through the FastAPI backend, and see a React Flow graph of the static structure plus runtime path. Clicking an edge opens the inspector with pass-level changed variables, stdout, and errors.

## Start backend
From the repo root:

```powershell
D:\FlowTrace\.venv\Scripts\python.exe -m uvicorn flowtrace_mvp.backend.app:app --reload
```

## Start frontend
From `D:\FlowTrace\flowtrace_mvp\frontend`:

```powershell
npm run dev
```

## URL
Open:

```text
http://localhost:5173
```

## Expected demo flow
1. Confirm the transcript-style Python sample is preloaded.
2. Click `Run Trace`.
3. Confirm the graph appears in the center canvas.
4. Confirm executed nodes are bright and skipped nodes are dimmed.
5. Confirm active runtime edges are blue and static/inactive edges are dashed gray.
6. Confirm repeated loop edges show a count badge such as `3x`.
7. Click an edge.
8. Confirm the inspector opens and shows before/after changed values.
9. Confirm stdout appears below the graph.
10. Click a group expand/collapse button and confirm the app does not crash.

## Screenshot placeholder
Add screenshot here after a manual demo capture:

```text
[screenshot placeholder]
```

## Known limits
- Group nodes are rendered as summary nodes, but Step 8 does not yet hide/re-route child nodes when a group is collapsed.
- Group expand/collapse currently changes the group visual state only.
- The demo calls the local backend at `http://localhost:8000/api/graph`.
- This is local-only and not a sandbox for untrusted code.
