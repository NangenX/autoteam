# AutoTeam

AutoTeam is an autonomous AI development team framework that runs entirely within Claude Code. A single slash command triggers a pipeline of 8 specialized subagents that collaborate to analyze, design, implement, test, and document software — without human intervention between steps.

## Usage

```
/autoteam "your requirement here"
```

Type this command in Claude Code. The Orchestration Agent takes over, runs the full pipeline, and delivers working code plus documentation in the current project directory.

## How It Works

1. **Orchestration** receives the requirement and drives the pipeline.
2. **Product Planner** produces a structured requirement card.
3. **Architecture** designs the solution and defines interface contracts.
4. **Discussion round** (up to 3 rounds): Architecture presents the design; agents may raise concerns; Orchestration mediates and resolves conflicts.
5. **Implementation** writes the code following the approved design.
6. **QA loop** (up to 3 rounds): Three QA agents run in parallel. Orchestration aggregates their reports. If issues are found, Implementation fixes them. Loop repeats until all checks pass or the round limit is reached.
7. **Documentation** writes the README and API docs.
8. Orchestration delivers the final result.

## Team Structure

| Agent | Model | Role |
|---|---|---|
| Orchestration | claude-opus-4-6 | Pipeline controller, discussion mediator, quality gate arbiter |
| Product Planner | claude-sonnet-4-6 | Requirement analysis → `requirement-card.yaml` |
| Architecture | claude-opus-4-6 | Tech design → `adr.md` + `interface-contracts.yaml` |
| Implementation | claude-sonnet-4-6 | Writes production code, owns the minimal-change rule in fix mode |
| QA Security | claude-sonnet-4-6 | OWASP Top 10, injection, auth vulnerabilities → `security-report.md` |
| QA Quality | claude-sonnet-4-6 | Complexity, duplication, SOLID violations → `quality-report.md` |
| QA Test | claude-sonnet-4-6 | Test coverage against acceptance criteria → `test-report.md` |
| Documentation | claude-haiku-4-5 | README, API docs → `docs/` |

## Workspace Protocol

All inter-agent communication happens through files in `.autoteam/workspace/`. No agent may write to a file it does not own. Orchestration mediates all coordination.

| File | Owner |
|---|---|
| `.autoteam/workspace/requirement-card.yaml` | Product Planner |
| `.autoteam/workspace/adr.md` | Architecture |
| `.autoteam/workspace/interface-contracts.yaml` | Architecture |
| `.autoteam/workspace/discussion/*.md` | Orchestration |
| `.autoteam/workspace/qa-reports/security-report.md` | QA Security |
| `.autoteam/workspace/qa-reports/quality-report.md` | QA Quality |
| `.autoteam/workspace/qa-reports/test-report.md` | QA Test |
| `.autoteam/workspace/qa-reports/aggregated-report.md` | Orchestration (QA Aggregator role) |
| `.autoteam/workspace/fix-instructions.md` | Orchestration (QA Aggregator role) |
| `.autoteam/workspace/escalation.md` | Implementation (architectural escalation only) |

## Key Constraints

### Minimal-Change Rule (Implementation, fix mode)
When fixing QA issues, Implementation must make the smallest change that resolves the finding. It must not refactor unrelated code, rename symbols outside the fix scope, or alter interfaces without an architectural escalation.

### QA Loop Limit
The QA → fix → QA cycle runs a maximum of **3 rounds**. After 3 rounds, Orchestration delivers the best available state and reports any unresolved issues to the user.

### Discussion Round Limit
The Architecture discussion phase runs a maximum of **3 rounds**. After 3 rounds, Orchestration makes the final call and the pipeline advances.

### Escalation Path
If Implementation discovers that a QA fix requires an architectural change, it writes `.autoteam/workspace/escalation.md` describing the problem. Orchestration decides whether to re-engage Architecture or override the constraint.

## Model Assignments

| Tier | Model | Assigned To |
|---|---|---|
| Opus | claude-opus-4-6 | Orchestration, Architecture |
| Sonnet | claude-sonnet-4-6 | Product Planner, Implementation, QA Security, QA Quality, QA Test |
| Haiku | claude-haiku-4-5 | Documentation |

Opus is used where broad reasoning and judgment are required. Sonnet handles the bulk of implementation and analysis work. Haiku handles high-volume, low-complexity writing tasks.

## Security Constraints

- Bash tool permissions are scoped to the project directory. No agent may execute shell commands outside the project root.
- No agent may execute generated code during the pipeline run (no `eval`, no spawning the user's own source as a subprocess).
- No agent may make network requests to external services during the pipeline run.
- Secrets and credentials must never be written to `.autoteam/workspace/` files.
- QA Security checks all output against OWASP Top 10 before the pipeline completes.

## Skill Files (Self-Contained)

All agent definitions are embedded directly in the skill files. No external agent definition files are needed.

| Platform | Skill File | Invocation |
|---|---|---|
| Claude Code | `.claude/skills/autoteam.md` | `/autoteam "requirement"` |
| Copilot CLI | `skills/autoteam.md` | Natural language: "run autoteam for: ..." |

## Harness Engineering Alignment

| AutoTeam Design | Harness Principle |
|---|---|
| `.autoteam/workspace/` file protocol | Repo as Source of Truth |
| Self-contained skill with embedded agent defs | Map not Manual (progressive disclosure) |
| QA reports with Fix field + fix-instructions.md | Mechanical Enforcement (lint error = fix instruction) |
| Minimal-change rule in FIX MODE | Backpressure over Prescription |
| 3-round loop limits | Steer with Signals, not Scripts |
| Golden Rules in QA Quality (mechanical CRITICAL checks) | Entropy Management (golden rules encoded in repo) |
| STEP 0: ORIENT in Implementation | Fresh Context (get bearings every invocation) |
| Context Management Rules in Orchestration | Agent Readability (context rot defense) |
