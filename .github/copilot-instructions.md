# GitHub Copilot Instructions for AutoTeam

By default, act as a normal Copilot coding assistant in this repository.

Only enter **AutoTeam mode** when the user explicitly asks for AutoTeam by name, for example:

- `Use AutoTeam to implement: ...`
- `Run AutoTeam for: ...`
- `Let AutoTeam handle this requirement: ...`
- `让 AutoTeam 执行这个需求：...`
- `用 AutoTeam 跑一下这个需求：...`

If the user asks ordinary coding questions, debugging questions, or repository questions without explicitly invoking AutoTeam, stay in normal assistant mode.

When AutoTeam mode is explicitly requested:

1. Read `.github/instructions/autoteam.instructions.md`.
2. Use `skills/autoteam.md` as the extended reference/template if more pipeline detail is needed.
3. Do **not** emit or expect the `/autoteam` slash command; that syntax is for Claude Code, not Copilot CLI.
4. Keep AutoTeam behavior scoped to the current request. Do not assume every later message should use the pipeline unless the user keeps referring to AutoTeam.
