# Next Feature Decision

## Current MVP capabilities

The local FlowTrace MVP can:

- Run small pasted Python snippets locally.
- Execute pasted code in a subprocess with a timeout guardrail.
- Show source lines as blocks.
- Mark executed and non-executed lines.
- Show runtime arrows between executed lines.
- Let users click arrows to inspect changed variables.
- Show locals snapshots and stdout at each event.
- Show an ordered execution path.
- Demonstrate assignment, if branch, loop, runtime error, and timeout cases.

## Explicitly deferred

Do not build these until user evidence supports them:

- SaaS
- GitHub import
- AI explanation
- Flowchart editing
- Version comparison
- React rewrite
- Docker sandbox

## Possible next features

### Group/collapse blocks

Useful if users say the demo becomes noisy once scripts get longer.

Signals:

- `I need to collapse setup code.`
- `This is too many lines to scan.`
- `Can I group this function or branch?`

### Intended flow comparison

Useful if users already have an expected workflow and want to compare it against reality.

Signals:

- `I expected this function to run, but it did not.`
- `Can I define the path I thought would happen?`
- `Can it show missing or unexpected steps?`

### Better graph layout

Useful if users understand the value but struggle to visually follow larger traces.

Signals:

- `The arrows are useful but hard to read.`
- `I need a clearer branch/loop layout.`
- `Can the path be more visual?`

### Export/share report

Useful if users want to send findings to a teammate or save review evidence.

Signals:

- `Can I share this with someone?`
- `Can I export this as HTML or Markdown?`
- `I need to attach this to a PR or ticket.`

### Safer sandboxing

Useful if users want to run real or untrusted scripts but hesitate because of local risk.

Signals:

- `I would not paste work code unless it was isolated.`
- `Can this prevent file writes or network calls?`
- `Can I run risky scripts safely?`

## Decision rule

Choose the next feature only after at least:

- 10 user reactions, or
- 3 serious user interviews.

A serious interview means the user discusses a real script, current alternatives, risk, and willingness to try the MVP on an actual workflow.

## Recommended next feature by feedback pattern

### If users say the trace is too noisy

Build:

```text
Group/collapse blocks
```

Reason:

Noise blocks comprehension before any deeper comparison feature matters.

### If users care about expected vs actual behavior

Build:

```text
Intended flow comparison
```

Reason:

This directly extends the core promise: compare what someone thought would happen with what actually happened.

### If users want to share results

Build:

```text
Export/share report
```

Reason:

Sharing makes the MVP useful in code review and team workflows without needing SaaS first.

### If users hesitate because execution feels unsafe

Build:

```text
Safer sandboxing
```

Reason:

Trust becomes the blocker. Without stronger isolation, users may not try real scripts.

### If users mostly ask for visual polish

Build:

```text
Better graph layout
```

Reason:

Only choose this if the current value is understood but readability blocks adoption.

## Default recommendation

If feedback is mixed, do not expand scope yet. Run more demos and collect more evidence.
