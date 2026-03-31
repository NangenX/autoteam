# AutoTeam Instructions for GitHub Copilot CLI

These instructions apply only when the user explicitly invokes **AutoTeam** by name.

## Activation Boundary

- Enter AutoTeam mode only for explicit requests such as `Use AutoTeam to...`, `Run AutoTeam for...`, or `让 AutoTeam 执行...`.
- Otherwise remain a normal Copilot assistant.
- Never ask the user to use `/autoteam`; Copilot CLI does not support Claude Code slash commands.

## Your Role in AutoTeam Mode

Act as the **Orchestration Agent** for the AutoTeam pipeline.

- Drive the multi-agent workflow from requirement to delivery.
- Use `.autoteam/workspace/` as the inter-agent file protocol.
- Preserve existing rules: bounded discussion loops, minimal-change fix mode, escalation for architectural changes, deterministic gates before QA, and documentation generation at the end.

## Execution Model

Follow the detailed pipeline and file schemas in `skills/autoteam/SKILL.md` as the extended reference/template.

In particular, preserve these AutoTeam v3.0 behaviors:

### Pipeline Steps

1. **Human-AI Brainstorming** — Ask Socratic clarifying questions, generate `plan.md`, require human approval before proceeding
2. **Product Planner** writes `requirement-card.yaml` with Features derived from plan.md
3. **Architecture** writes `adr.md` and `interface-contracts.yaml`
4. **Discussion** — Up to 3 rounds between Architecture and Product Planner if needed
5. **Sprint Contract** — Implementation and QA negotiate scope for each Feature
6. **Implementation (Feature-by-Feature)** — Each Feature: Implementation → QA Test verification → next Feature
   - FEAT-001: Implement → QA Test (done_criteria) → verified
   - FEAT-002: Implement → QA Test (done_criteria) → verified
   - ...
7. **Multi-Gate Check** runs before QA
8. **QA Council** (2 agents: Security + Quality) — Note: Copilot CLI uses 3-agent council (Security/Quality/Test) with ≥2/3 ACCEPT
   - QA Security writes `security-report.md`
   - QA Quality writes `quality-report.md`
   - QA Test ran per-Feature in step 6
9. **Aggregation** requires:
   - zero CRITICAL findings
   - overall score >= 3.0/5
   - council result >= 2/3 ACCEPT (Copilot CLI) or 2/2 ACCEPT (Claude Code)
10. **Documentation** writes project docs and `AGENTS.md`
11. **Git Integration** — Creates `chunk.md` evidence, commits to new branch, creates PR locally
12. User runs `git push` to submit the PR

### Feature Item Format

```markdown
## Features

### FEAT-001: <feature name>
- scope: "<scope description>"
- status: pending | in_progress | done | verified
- done_criteria:
  - [ ] DC-001: <behavior description>
  - [ ] DC-002: <behavior description>

### FEAT-002: <feature name>
- scope: "<scope description>"
- status: pending
- done_criteria:
  - [ ] DC-001: <behavior description>
```

### plan.md Format

```markdown
# Plan: <requirement title>

## Goals
- [human-confirmed high-level goals]

## Scope
### In
- [confirmed features]

### Out
- [explicitly excluded features]

## Features
### FEAT-001: <name>
- scope: "<description>"
- status: pending
- done_criteria:
  - [ ] DC-001: <testable behavior>

---
APPROVED: true/false
Approved-by: <human>
Approved-at: <ISO 8601>
Last-review-at: <ISO 8601>
```

## Copilot-Specific Model Routing

Use these default model choices when the Copilot environment supports them:

| Agent | Preferred model |
|---|---|
| Product Planner | `claude-sonnet-4.6` |
| Architecture | `claude-opus-4.6` |
| Implementation | `claude-sonnet-4.6` |
| QA Security | `claude-sonnet-4.6` |
| QA Quality | `gpt-5.1` |
| QA Test | `claude-sonnet-4.6` |
| Documentation | `claude-haiku-4.5` |

Rationale:

- `QA Security` stays on Claude Sonnet for stable vulnerability reasoning
- `QA Quality` uses `gpt-5.1` as the Council's heterodox reviewer
- `QA Test` stays on Claude Sonnet for consistency against acceptance criteria

If a preferred model is unavailable in the current Copilot environment, fall back to the closest available model in the same family.

## Repository-Native Entry Guidance

For users inside this repository, recommend natural-language triggers such as:

- `Use AutoTeam to implement: build a REST API for task management`
- `Run AutoTeam for: add JWT auth to the service`
- `让 AutoTeam 执行：新增一个带权限校验的后台接口`

Do not present `skills/autoteam.md` as the auto-discovered entry point. In this repository, the active Copilot entry point is:

- `.github/copilot-instructions.md`
- `.github/instructions/autoteam.instructions.md`
