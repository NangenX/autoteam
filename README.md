# AutoTeam

An autonomous AI development team that runs entirely inside Claude Code. Type one command, get working code.

```
/autoteam "build a REST API for task management"
```

Seven specialized agents — Product Planner, Architecture, Implementation, three QA layers, and Documentation — collaborate automatically to deliver production-ready code from a single requirement.

---

## How It Works

```
/autoteam "requirement"
        ↓
  Orchestration (Opus)
        ↓
  Product Planner ──→ requirement-card.yaml
        ↓
  Architecture ──→ adr.md + interface-contracts.yaml
        ↓  ← [Discussion: Arch ↔ Planner, up to 3 rounds]
  Implementation ──→ source code
        ↓
  QA Security ──→ security-report.md
  QA Quality  ──→ quality-report.md
  QA Test     ──→ test-report.md
        ↓  ← [Fix loop: up to 3 rounds, minimal-change rule]
  Documentation ──→ docs/
        ↓
  ✅ Done
```

Agents communicate exclusively through files in `.openclaw/workspace/`. No agent can modify another agent's output. If a fix requires an architectural change, Implementation escalates — it cannot unilaterally change what Architecture decided.

---

## Quick Start

### 1. Clone into your project

```bash
git clone https://github.com/NangenX/autoteam.git
cd autoteam
```

### 2. Open with Claude Code

```bash
claude
```

### 3. Run a requirement

```
/autoteam "create a CLI tool that converts CSV to JSON"
```

The pipeline runs end-to-end and delivers source code + docs in the current directory.

---

## Team

| Agent | Model | Responsibility |
|---|---|---|
| Orchestration | claude-opus-4-6 | Pipeline controller, discussion mediator, quality gate |
| Product Planner | claude-sonnet-4-6 | Requirement → structured acceptance criteria |
| Architecture | claude-opus-4-6 | Tech stack + interface contracts |
| Implementation | claude-sonnet-4-6 | Writes code; fixes QA findings (minimal-change rule) |
| QA Security | claude-sonnet-4-6 | OWASP Top 10, injection, auth vulnerabilities |
| QA Quality | claude-sonnet-4-6 | Complexity, duplication, SOLID violations |
| QA Test | claude-sonnet-4-6 | Test coverage against acceptance criteria |
| Documentation | claude-haiku-4-5 | README, API docs, architecture summary |

---

## Key Design Decisions

**Minimal-change fix rule** — When QA finds issues, Implementation fixes only the specific file/function/lines listed in `fix-instructions.md`. No opportunistic refactoring. This prevents fixes from introducing new problems and keeps the codebase from drifting in unexpected directions.

**File ownership** — Each agent owns exactly one set of output files and cannot write to anything else. Orchestration owns all coordination files. This is the primary integrity guarantee of the workspace.

**Bounded loops** — Both the Architecture discussion phase and the QA fix loop are capped at 3 rounds. After 3 rounds, Orchestration makes a binding decision and the pipeline advances. No infinite loops.

**Escalation path** — If a QA fix requires changing an interface or architecture decision, Implementation writes `escalation.md` instead of expanding scope. Orchestration decides whether to re-engage Architecture.

**Separation of QA concerns** — Security, code quality, and test coverage are separate agents with hard scope boundaries. Each agent ignores the other agents' domains. This prevents duplicate findings and ensures each layer is thorough within its scope.

---

## Project Structure

```
.
├── .claude/
│   └── skills/
│       └── autoteam.md          # /autoteam entry point
├── .openclaw/
│   ├── settings.json            # Auto-loads agent definitions
│   ├── agents/                  # Agent system prompts
│   │   ├── orchestration.md
│   │   ├── product-planner.md
│   │   ├── architecture.md
│   │   ├── implementation.md
│   │   ├── qa-security.md
│   │   ├── qa-quality.md
│   │   ├── qa-test.md
│   │   └── documentation.md
│   └── workspace/               # Agent communication (per-run, gitignored)
│       ├── requirement-card.yaml
│       ├── adr.md
│       ├── interface-contracts.yaml
│       ├── fix-instructions.md
│       ├── discussion/
│       └── qa-reports/
├── docs/
│   └── superpowers/specs/
│       └── 2026-03-22-autoteam-design.md  # Full design spec
└── CLAUDE.md                    # Project context for Claude Code
```

---

## Extending the Team

**Add a QA layer** — Create `qa-performance.md` in `.openclaw/agents/`, assign it `qa-reports/performance-report.md`, dispatch it in `orchestration.md` Step 7, include it in aggregation with a `PER-` prefix.

**Swap a model** — Change the `model:` field in any agent definition file. The pipeline is model-agnostic at the file protocol level.

**Add an agent** — Create the definition file, declare its output files, add a dispatch step to `orchestration.md`, and add the new files to the workspace ownership table.

See `docs/superpowers/specs/2026-03-22-autoteam-design.md` for the full architecture spec.

---

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- An Anthropic API key with access to Claude Opus 4, Sonnet 4, and Haiku models
