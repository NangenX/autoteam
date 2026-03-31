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

1. **Product Planner** — Transforms your requirement into structured acceptance criteria
2. **Architecture** — Designs the tech stack and interface contracts
3. **Discussion** — Aligns architecture with requirements (up to 3 rounds)
4. **Sprint Contract** — Negotiates implementation scope between Implementation and QA
5. **Implementation** — Writes production code for each module
6. **Multi-Gate Check** — Runs deterministic checks (lint, imports, structure)
7. **QA Pipeline** — Security, Quality, and Test agents verify the code
8. **Documentation** — Generates docs/README.md, docs/ARCHITECTURE.md, AGENTS.md
9. **Git Commit** — Creates branch and commits all changes

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
