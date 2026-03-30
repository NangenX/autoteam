# OpenAI Harness Engineering Integration — Design Spec

> **Source:** [alchemiststudiosDOTai/harness-engineering](https://github.com/alchemiststudiosDOTai/harness-engineering)
> Based on [OpenAI: Harness Engineering](https://openai.com/index/harness-engineering/)

**Goal:** Integrate 5 high-value concepts from the OpenAI-inspired Harness Engineering framework into AutoTeam's existing pipeline without structural changes.

**Approach:** Additive — extend existing pipeline steps in-place. One step rename (Linter Pre-Gate → Multi-Gate Check). No architectural flow changes.

**Affected Files:**
- `.claude/skills/autoteam.md` (Claude Code skill)
- `skills/autoteam.md` (Copilot CLI skill)
- `CLAUDE.md` (alignment table update)

---

## Concept 1: Council Multi-Model Voting

### What
Replace single-model QA consensus with multi-model Council voting. Each QA agent independently votes ACCEPT or REJECT. Merge requires 2/3 consensus.

### Current State
- 3 QA agents (Security, Quality, Test) all use `sonnet` / `claude-sonnet-4.6`
- Orchestration aggregates: ALL_CLEAR if zero CRITICAL findings AND overall score ≥ 3.0/5

### Design

**Model Diversification (Copilot CLI only — Claude Code subagents are limited to Claude models):**

| QA Agent | Current Model | Council Model |
|----------|--------------|---------------|
| QA Security | claude-sonnet-4.6 | claude-sonnet-4.6 (unchanged) |
| QA Quality | claude-sonnet-4.6 | gpt-5.1 |
| QA Test | claude-sonnet-4.6 | claude-sonnet-4.6 (unchanged) |

Claude Code: Keep all 3 as `sonnet` subagents. Diversity comes from different system prompts (already distinct). Add vote protocol.

**Vote Protocol:**
Each QA agent appends to their report:

```yaml
## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence>
confidence: HIGH | MEDIUM | LOW
```

**Aggregation Rule:**
```
ALL_CLEAR requires ALL of:
  1. Council vote: ≥ 2/3 ACCEPT
  2. Zero CRITICAL findings
  3. Overall score ≥ 3.0/5
```

If vote is 1/3 ACCEPT (2 REJECT), pipeline enters fix loop regardless of scores.

### Pipeline Impact
- Step 7 (QA × 3): each agent adds vote section
- Step 8 (QA Aggregation): adds council tally to aggregated-report.md
- File ownership: `aggregated-report.md` gains council vote summary

---

## Concept 2: AGENTS.md Auto-Generation

### What
Documentation agent generates `AGENTS.md` for the target project — a machine-readable map that future AI agents (Claude Code, Codex, Copilot) use to understand the project.

### Current State
Documentation agent outputs: `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/API.md` (if API).

### Design

**New output:** `AGENTS.md` at project root.

**Content template:**
```markdown
# AGENTS.md

## Project
<one-paragraph description>

## Harness
- Run all checks: `<detected command — e.g., just check, npm test, pytest>`
- Lint: `<lint command>`
- Tests: `<test command>`

## Structure
<key directories and their purposes, max 15 lines>

## Rules
- <key constraints from adr.md>
- <import boundaries if any>

## How to Contribute
1. Create a branch
2. Make changes
3. Run harness: `<command>`
4. Commit with evidence

## QA Expectations
- Security: OWASP Top 10 compliance
- Quality: No complexity > 15, no duplication > 10 lines
- Tests: All acceptance criteria covered
```

**Detection logic:** Infer harness command from project files:
- `justfile` → `just check`
- `package.json` with `test` script → `npm test`
- `pyproject.toml` → `pytest` or `ruff check . && pytest`
- `Makefile` → `make check` or `make test`
- Fallback: `echo "No harness detected — configure your check command"`

### Pipeline Impact
- Step 9 (Documentation): agent's output list adds `AGENTS.md`
- Documentation agent system prompt: add AGENTS.md generation rules

---

## Concept 3: Work Chunks Evidence Protocol

### What
Every pipeline run produces a structured evidence document (chunk doc) that ships with the commit. Makes the change self-documenting and auditable.

### Current State
Git step creates branch + commit with descriptive message, but no structured evidence artifact.

### Design

**New file:** `.autoteam/workspace/chunk.md` (owned by Orchestration)

**Template:**
```markdown
# Work Chunk: <requirement title>

## Intent
- What behavior/structure changed: <from requirement-card.yaml>

## Preconditions
- Branch base: <base branch>
- Harness status before: <PASS/FAIL/N/A>

## Evidence
- Multi-Gate: <PASS with N gates checked / FAIL at gate X>
- QA Council: <N/3 ACCEPT, scores: security X.X, quality X.X, design X.X, test X.X, functionality X.X>
- QA Rounds: <N rounds to pass>
- Sprint Contract: <MET / NOT_MET / SKIPPED>
- Files created: <count>
- Files modified: <count>
- Test files: <count>

## Rollback
git revert <commit-sha>
```

**Generation:** Orchestration generates chunk.md just before the git commit, pulling data from:
- `requirement-card.yaml` (intent)
- `qa-reports/aggregated-report.md` (QA results)
- `qa-reports/lint-report.md` (gate results)
- `sprint-contract.yaml` (contract status)

**Commit inclusion:** chunk.md is committed alongside the code.

### Pipeline Impact
- Step 10.5 (Git Integration): generate chunk.md before `git add`
- File ownership table: add `chunk.md → Orchestration`

---

## Concept 4: Ratchet Mechanism

### What
For brownfield/legacy projects, allow existing lint violations as a baseline but block new ones. The baseline can only shrink, never grow.

### Current State
Linter Pre-Gate requires zero violations. Fails the entire pipeline for projects with pre-existing issues.

### Design

**Activation:** Auto-detect brownfield project:
- If lint on existing code returns violations > 0 BEFORE Implementation writes code → activate ratchet mode
- Or if requirement contains keywords: "existing project", "legacy", "brownfield", "refactor"

**Ratchet flow:**
1. Before Implementation step: run lint on current codebase → count = `baseline_violations`
2. After Implementation step: run lint again → count = `current_violations`
3. Pass condition: `current_violations <= baseline_violations`
4. Record in `.autoteam/workspace/qa-reports/ratchet-baseline.txt`:
   ```
   baseline: 42
   current: 38
   delta: -4
   status: PASS (reduced by 4)
   ```
5. In fix loop: if Implementation fixes reduce violations below baseline, update baseline downward

**Fail message:**
```
[Multi-Gate] ❌ Ratchet FAIL: baseline=42, current=45 (+3 new violations)
New violations must be fixed before proceeding.
```

### Pipeline Impact
- Step 6.5 (Multi-Gate): add ratchet logic before Gate A
- File ownership: add `ratchet-baseline.txt → Orchestration`

---

## Concept 5: Six Gates Expansion

### What
Expand the single Linter Pre-Gate into a multi-gate check system. Each gate is independent and conditional.

### Current State
Step 6.5 runs only ruff/eslint/go-vet (Gate A: formatting + lint).

### Design

**Gate definitions:**

| Gate | Name | Tool | Detection | Condition |
|------|------|------|-----------|-----------|
| A | Formatting + Lint | ruff/eslint/go-vet | Always | Language detected |
| B | Import Boundaries | import-linter | `pyproject.toml` has `[tool.importlinter]` | Python only |
| C | Structural Rules | ast-grep | `sgconfig.yml` exists | Any language |
| D | Snapshot Testing | pytest --snapshot | `__snapshots__/` dir exists | Python only |
| E | Golden Outputs | `diff` against committed goldens | `tests/goldens/` dir exists | Any |
| F | Numerical Equiv. | tolerance check (numpy `allclose` or manual float compare) | `tests/numerical/` dir exists | Math/ML |

**Execution:**
```
[Step 4.5/8] Multi-Gate Check
  Gate A (Lint):        ✅ PASS (0 violations)
  Gate B (Imports):     ⏭️ SKIPPED (no import-linter config)
  Gate C (AST Rules):   ✅ PASS (0 violations)
  Gate D (Snapshots):   ⏭️ SKIPPED (no __snapshots__/)
  Gate E (Goldens):     ⏭️ SKIPPED (no tests/goldens/)
  Gate F (Numerical):   ⏭️ SKIPPED (no tests/numerical/)
  
  Result: 2/2 active gates PASS
```

**Failure handling:**
- Gate A failure: always blocks (or ratchet if brownfield)
- Gate B-F failure: blocks pipeline, enters fix loop
- All SKIPPED: equivalent to PASS (no gates to fail)

**Step rename:** "Linter Pre-Gate" → "Multi-Gate Check" in pipeline description and user-facing output.

### Pipeline Impact
- Step 6.5: renamed, expanded logic
- `lint-report.md` → renamed to `gate-report.md`
- Report format expanded to show per-gate results

---

## Updated File Ownership Table

| File | Owner |
|------|-------|
| `.autoteam/workspace/requirement-card.yaml` | Product Planner |
| `.autoteam/workspace/adr.md` | Architecture |
| `.autoteam/workspace/interface-contracts.yaml` | Architecture |
| `.autoteam/workspace/discussion/*.md` | Orchestration |
| `.autoteam/workspace/sprint-contract.yaml` | Orchestration |
| `.autoteam/workspace/phase-summary.md` | Orchestration |
| `.autoteam/workspace/qa-reports/gate-report.md` | Orchestration |
| `.autoteam/workspace/qa-reports/ratchet-baseline.txt` | Orchestration |
| `.autoteam/workspace/qa-reports/security-report.md` | QA Security |
| `.autoteam/workspace/qa-reports/quality-report.md` | QA Quality |
| `.autoteam/workspace/qa-reports/test-report.md` | QA Test |
| `.autoteam/workspace/qa-reports/aggregated-report.md` | Orchestration |
| `.autoteam/workspace/fix-instructions.md` | Orchestration |
| `.autoteam/workspace/chunk.md` | Orchestration |
| `.autoteam/workspace/escalation.md` | Implementation |

---

## Updated Pipeline Flow

**Step number mapping (old → new):**

| Old (internal) | New (user-facing) | Name |
|---------------|-------------------|------|
| Step 0 | Step 0 | ORIENT |
| Step 1 | Step 1/8 | Product Planner |
| Step 2 | Step 2/8 | Architecture |
| Step 3 | Step 3/8 | Discussion |
| Step 5.5 | Step 3.5/8 | Sprint Contract |
| Step 4 | Step 4/8 | Implementation |
| Step 6.5 | Step 4.5/8 | Multi-Gate Check (was Linter Pre-Gate) |
| Step 7 | Step 5/8 | QA Council (was QA × 3) |
| Step 8 | Step 5.5/8 | Fix Loop |
| Step 9 | Step 6/8 | Documentation |
| NEW | Step 7/8 | Work Chunk Evidence |
| Step 10.5 | Step 7.5/8 | Git Integration |
| Step 11 | Step 8/8 | Archive + Done |

```
Requirement
  → [Step 0] ORIENT (read codebase)
  → [Step 1/8] Product Planner → requirement-card.yaml
  → [Step 2/8] Architecture → adr.md + interface-contracts.yaml
  → [Step 3/8] Discussion (≤3 rounds)
  → [Step 3.5/8] Sprint Contract (if complex)
  → [Step 4/8] Implementation
  → [Step 4.5/8] Multi-Gate Check (Gates A-F, ratchet if brownfield)
  → [Step 5/8] QA Council (3 agents, multi-model, 2/3 vote)
    → [Step 5.5/8] Fix Loop (≤3 rounds, if council rejects)
  → [Step 6/8] Documentation (README + ARCHITECTURE + API + AGENTS.md)
  → [Step 7/8] Work Chunk Evidence (chunk.md)
  → [Step 7.5/8] Git Integration (branch + commit + chunk)
  → [Step 8/8] Archive + Done
```

---

## Updated Harness Alignment Table (CLAUDE.md)

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

---

## Non-Goals

- No plugin system restructure (`.claude-plugin/plugin.json`)
- No prompt hooks integration (Claude Code-specific, low portability)
- No RPEQ workflow replacement (our 8-step pipeline is more granular)
- No `just check` / `justfile` creation (target project's choice)
