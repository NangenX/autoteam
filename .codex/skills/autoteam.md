# AutoTeam Skill for Codex CLI

Autonomous AI development team. 8 specialized agents collaborate to analyze, design, implement, test, and document software from a single requirement.

## Activation

Only enter AutoTeam mode when the user explicitly invokes AutoTeam by name:

- `Use AutoTeam to implement: ...`
- `Run AutoTeam for: ...`
- `让 AutoTeam 执行这个需求：...`

Otherwise remain a normal Codex assistant.

## Execution

When AutoTeam is invoked:

1. Read `.github/instructions/autoteam.instructions.md` for orchestration instructions
2. Use `skills/autoteam/SKILL.md` as the extended reference for the full pipeline
3. Follow the 8-agent workflow: Product Planner → Architecture → Discussion → Implementation → Multi-Gate Check → QA Council → Documentation → Git

## Workspace Protocol

All inter-agent files use `.autoteam/workspace/`:
- `requirement-card.yaml` (Product Planner output)
- `adr.md`, `interface-contracts.yaml` (Architecture output)
- `qa-reports/security-report.md`, `quality-report.md`, `test-report.md` (QA Council outputs)
- `docs/README.md`, `docs/ARCHITECTURE.md`, `AGENTS.md` (Documentation outputs)
- `chunk.md` (Git evidence before commit)

## Hook Behavior

After every user prompt, check if `.autoteam/workspace/phase-summary.md` exists to maintain pipeline context.
