# AutoTeam

Autonomous AI development team. 8 specialized agents collaborate to analyze, design, implement, test, and document software from a single requirement.

## Quick Start

**Claude Code:** `/autoteam "your requirement here"`
**Copilot CLI:** "Run autoteam with requirement: your requirement here"

## Team (8 agents, 3 model tiers)

| Agent | Model | Output |
|---|---|---|
| Orchestration | opus | Pipeline control |
| Product Planner | sonnet | requirement-card.yaml |
| Architecture | opus | adr.md + interface-contracts.yaml |
| Implementation | sonnet | Source code |
| QA Security | sonnet | security-report.md |
| QA Quality | sonnet | quality-report.md |
| QA Test | sonnet | test-report.md |
| Documentation | haiku | docs/ |

## Pipeline

Requirement → Product Planner → Architecture → Discussion (≤3 rounds) → Implementation → Linter Pre-Gate → QA×3 → Fix Loop (≤3 rounds) → Documentation → Git Commit → Done

## Workspace

All inter-agent files: `.autoteam/workspace/`
Run archives: `.autoteam/runs/<timestamp>/`
File ownership: see skill files Section 2

## Skill Files

| Platform | File |
|---|---|
| Claude Code | `.claude/skills/autoteam.md` |
| Copilot CLI | `skills/autoteam.md` |

All agent definitions, pipeline steps, QA rules, and dispatch protocols live in the skill files. This file is an index only.

## Harness Engineering Alignment

| Design | Principle |
|---|---|
| `.autoteam/workspace/` file protocol | Repo as Source of Truth |
| Linter Pre-Gate (ruff/eslint/go vet) | Mechanical Enforcement |
| Golden Rules + QA loop | Entropy Management |
| Phase Summaries + STEP 0: ORIENT | Agent Readability |
| Git branch + commit integration | Throughput → Merge |
| Self-contained skills + model routing | Harness Definition |

## Security

- No execution of generated code during pipeline
- No network requests to external services
- No secrets in `.autoteam/workspace/` files
- QA Security checks OWASP Top 10
