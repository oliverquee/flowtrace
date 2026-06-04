# FlowTrace Bridge Notes

## Coordination Pattern

- ChatGPT plans/reviews.
- Codex/OpenCode edits code.
- Human runs tests and pushes.
- GitHub is source of truth.

## Strict Rules For Future Agents

- Work on a feature branch.
- Do not commit `.venv`, `__pycache__`, `flowtrace_output`, `sample_project_output`, `.env`, secrets, tokens, or credentials.
- Do not build UI, SaaS, AI integration, editor, database, plugin, or multi-language support unless explicitly requested.
- Keep standard-library-only unless explicitly approved.
- Always run required test commands.
- Commit with a clear message.
- Push the branch.

## Current Safe Workflow

1. Pull main.
2. Create feature branch.
3. Make minimal change.
4. Run tests.
5. Commit and push.
6. Ask ChatGPT to review before merge.
