# User Feedback Questions

## Goal

Use these questions to test whether FlowTrace solves a real inspection pain, not whether people are being polite.

Avoid asking only:

- `Would you use this?`
- `Would you pay for this?`

Those questions are allowed only when paired with behavior-based follow-up.

## Questions that test real pain

1. Tell me about the last time you had to understand a Python script you did not fully trust.
2. What made that script hard to reason about?
3. Did you run it, read it, add print statements, use a debugger, or avoid running it?
4. What was the risk if you misunderstood it?
5. How often does this happen in a normal month?
6. What kinds of code are most painful: automation scripts, data scripts, CLI tools, notebooks, backend jobs, or something else?
7. When you inspect code today, where do you lose time?
8. What side effects are you most worried about: file writes, deletes, API calls, emails, auth prompts, infinite loops, or hidden branches?

## Questions that avoid fake validation

1. Show me a real script you recently struggled to understand. What would you check first?
2. Before seeing FlowTrace, what would you normally do with this script?
3. After seeing this demo, what would you still not trust?
4. What part of the demo felt obvious or unnecessary?
5. What part made you say, `I wish I had this last week`?
6. What would make you stop using it after the first try?
7. What output would you need before sharing this with a teammate?

## Willingness to use

1. What is the next real Python file you would try this on?
2. Would you paste a small local script into this today? Why or why not?
3. What would block you from using it on work code?
4. Would static-only inspection be enough for your first pass?
5. Would you trust local subprocess execution, or would you need stronger isolation?
6. Who else on your team has this problem?
7. What would need to be true for this to become part of your normal review workflow?

## Willingness to pay

Ask behavior-first:

1. Have you paid for tools that help with debugging, code review, observability, or workflow analysis?
2. What did you pay for, and why was it worth it?
3. If FlowTrace saved you one hour per week, who would approve buying it?
4. What would need to be included before you would expense it?
5. Would you pay for this as a local desktop/dev tool, or only if it integrated into your repo workflow?
6. What price range would feel obviously too high for your use case?
7. What proof would you need before paying?

Do not stop at:

```text
Would you pay for this?
```

Follow up with:

```text
What did you pay for recently that was similar in value, and what triggered the purchase?
```

## Current alternatives

1. What do you use today instead?
2. Do you use print statements, a debugger, tests, code review, logs, notebooks, tracing tools, or static analysis?
3. What is annoying about those tools?
4. Which tool would FlowTrace need to beat for you to switch?
5. When do current tools fail you?
6. What do you do when code has side effects you are afraid to trigger?
7. Do you already have a safe way to run suspicious scripts?

## Scoring rubric

### Strong signal

- User names a recent real script and wants to try it.
- User has already spent meaningful time solving this manually.
- User describes a costly mistake, risk, or delay.
- User asks for a specific missing capability tied to a real workflow.
- User offers to share code or run another session.
- User compares it to a paid tool or workflow they already use.

### Medium signal

- User understands the value but cannot name a recent case.
- User says it would help teammates more than themselves.
- User wants export/share/reporting before using it.
- User is interested but blocked by security or sandbox concerns.
- User would use it only for personal/local scripts.

### Weak signal

- User says it is cool but cannot name a use case.
- User asks for broad future features before trying the current MVP.
- User only wants it if it becomes SaaS/GitHub/AI immediately.
- User would not paste any code into it.
- User does not currently inspect or run Python scripts.

### False positive signal

- User says `I would use this` but cannot identify when.
- User says `I would pay` but has no budget, buyer, or comparable purchase.
- User praises the UI but ignores the core arrow/changed-variable workflow.
- User requests many speculative features unrelated to the demo.
- User reacts positively only after being led by the demo script.
