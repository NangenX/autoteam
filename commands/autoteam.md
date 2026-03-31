# /autoteam Command

Invoke the AutoTeam autonomous development pipeline.

## Usage

```
/autoteam "your requirement"
```

## Example

```
/autoteam "build a REST API for task management"
/autoteam "create a CLI tool for file encryption"
/autoteam "implement a WebSocket chat server"
```

## What Happens

1. **Human-AI Brainstorming** — Clarify requirements with AI, generate approved plan.md
2. **Product Planner** — Transforms approved plan into structured requirement-card.yaml
3. **Architecture** — Designs the tech stack and interface contracts
4. **Discussion** — Aligns architecture with requirements (up to 3 rounds)
5. **Sprint Contract** — Negotiates implementation scope between Implementation and QA
6. **Implementation** — Writes production code for each module
7. **Multi-Gate Check** — Runs deterministic checks (lint, imports, structure)
8. **QA Pipeline** — Security, Quality, and Test agents verify the code
9. **Documentation** — Generates docs/README.md, docs/ARCHITECTURE.md, AGENTS.md
10. **Git Commit** — Creates branch and commits all changes

## Output

- Files created/modified by Implementation
- QA reports in `.autoteam/workspace/qa-reports/`
- Documentation in `docs/`
- Git branch `autoteam/<date>-<slug>`

## Status

Check pipeline status anytime with:
```
/autoteam:status
```
