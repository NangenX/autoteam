# AutoTeam

Autonomous AI development team. 8 specialized agents collaborate to analyze, design, implement, test, and document software from a single requirement.

## Quick Start

**Claude Code:** `/autoteam "your requirement here"`
**Copilot CLI:** "Use AutoTeam to implement: your requirement here" (repo-native via `.github/copilot-instructions.md`)

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

Requirement → Product Planner → Architecture → Discussion (≤3 rounds) → Implementation → Multi-Gate Check → QA Council → Fix Loop (≤3 rounds) → Documentation → Work Chunk → Git Commit → Done

## Workspace

All inter-agent files: `.autoteam/workspace/`
Run archives: `.autoteam/runs/<timestamp>/`
File ownership: see skill files Section 2

## Entry Files

| Platform | File |
|---|---|
| Claude Code | `.claude/skills/autoteam.md` |
| Copilot CLI (repo-native) | `.github/copilot-instructions.md` + `.github/instructions/autoteam.instructions.md` |
| Copilot reference template | `skills/autoteam.md` |

Claude Code reads its skill directly. Copilot CLI should use the `.github/` instruction files; `skills/autoteam.md` is the extended template/reference, not the auto-discovered entry point. This file is an index only.

## Harness Engineering Alignment

| Design | Principle | Source |
|---|---|---|
| `.autoteam/workspace/` file protocol | Repo as Source of Truth | Harness Engineering |
| Multi-Gate Check (Gates A-F) | Mechanical Enforcement | OpenAI Harness |
| Ratchet mechanism (brownfield) | Ratchet Gates | OpenAI Harness |
| Council vote (2/3 multi-model) | Agent-to-Agent Review | OpenAI Harness |
| Work Chunks evidence protocol | Evidence-Based Chunks | OpenAI Harness |
| AGENTS.md auto-generation | Progressive Disclosure | OpenAI Harness |
| Golden Rules + QA loop | Entropy Management | Harness Engineering |
| Phase Summaries + STEP 0: ORIENT | Agent Readability | Harness Engineering |
| Git branch + commit integration | Throughput → Merge | Harness Engineering |
| Self-contained skills + model routing | Harness Definition | Harness Engineering |
| Sprint Contract (Impl ↔ QA negotiation) | Generator-Evaluator Contract | Anthropic Original |
| Structured Grading (5 dimensions, 1-5 scale) | Grading Criteria | Anthropic Original |
| Interactive Evaluation (Playwright) | Live App Evaluation | Anthropic Original |
| Section 7: Simplification Rules | Harness Simplification | Anthropic Original |

## Security

- No execution of generated code during pipeline
- No network requests to external services
- No secrets in `.autoteam/workspace/` files
- QA Security checks OWASP Top 10
