# FlowTrace MVP Demo Script

## Start the app

From the repository root:

```powershell
python -m uvicorn flowtrace_mvp.backend.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## 60-90 second demo script

### 1. Open with the plain-English problem

Say:

```text
FlowTrace shows what actually happened when small Python code ran. It turns runtime execution into blocks, arrows, and changed variables so you can inspect the path instead of guessing from code alone.
```

Do:

- Open the local app.
- Point out the editor, runtime blocks, arrow inspector, execution path, stdout, and error area.

### 2. Assignment sample

Do:

1. Select `Assignment`.
2. Click `Load sample`.
3. Click `Run Trace`.
4. Click the edge that shows `x = 5`.
5. Click the execution path row that shows `y = 7`.

Say:

```text
For a simple assignment, each arrow shows what changed between executed lines. Here the first transition creates x, and the next transition creates y.
```

Point out:

- Blocks are source lines.
- Arrows are runtime transitions.
- The inspector shows changed variables and locals snapshot.
- Stdout shows the printed result.

### 3. If branch sample

Do:

1. Select `If branch`.
2. Click `Load sample`.
3. Click `Run Trace`.
4. Point to the executed branch.
5. Point to the non-executed `else` branch.

Say:

```text
This shows the actual branch taken at runtime. The else branch still appears as code, but it is visually distinct because it did not execute.
```

Point out:

- The value is `y = 'big'`.
- The non-executed `else` assignment is not part of the runtime edge path.

### 4. Loop sample

Do:

1. Select `Loop`.
2. Click `Load sample`.
3. Click `Run Trace`.
4. Click a loop-back edge.

Say:

```text
Loops produce repeated runtime transitions. The loop-back edge shows the code moving from the loop body back to the loop condition.
```

Point out:

- Loop-back edges are visually marked.
- The final changed value includes `total = 3`.

### 5. Runtime error sample

Do:

1. Select `Runtime error`.
2. Click `Load sample`.
3. Click `Run Trace`.
4. Show the error panel.

Say:

```text
If code fails, FlowTrace still shows the partial path before the error and the error details. That makes failure easier to inspect.
```

Point out:

- The error is shown clearly.
- The later code path is not treated as executed.

### 6. Timeout sample

Do:

1. Select `Timeout`.
2. Click `Load sample`.
3. Click `Run Trace`.
4. Wait for the timeout error.

Say:

```text
The MVP runs pasted code in a local subprocess with a timeout guardrail. This prevents the browser demo from hanging forever on an infinite loop.
```

Point out:

- The timeout is a guardrail.
- It is not a full security sandbox.

## What to say

- `This is local-first and runs on this machine.`
- `The current MVP is for small pasted Python snippets.`
- `The useful moment is clicking an arrow and seeing what changed.`
- `The path shows what actually executed, not just what code exists.`
- `The timeout guardrail helps with runaway code, but it is not a security promise.`

## What not to say yet

- Do not say it is SaaS-ready.
- Do not say it securely runs untrusted code.
- Do not say it works on any project.
- Do not promise GitHub import.
- Do not promise AI explanations.
- Do not promise a full sandbox.
- Do not present it as a replacement for debuggers, profilers, or tests.
- Do not claim it understands all Python semantics.
