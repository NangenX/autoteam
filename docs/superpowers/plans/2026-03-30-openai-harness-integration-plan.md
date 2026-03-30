# OpenAI Harness Engineering Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate 5 OpenAI Harness Engineering concepts (Multi-Gate, Ratchet, Council, AGENTS.md, Work Chunks) into both AutoTeam skill files.

**Architecture:** Additive changes to existing skill files. Each concept maps to specific pipeline steps and agent definitions. Both `.claude/skills/autoteam.md` (Claude Code) and `skills/autoteam.md` (Copilot CLI) receive parallel changes. CLAUDE.md alignment table updated last.

**Tech Stack:** Markdown skill files (no code — all changes are prompt engineering edits)

**Spec:** `docs/superpowers/specs/2026-03-30-openai-harness-integration-design.md`

---

## File Map

| File | Responsibility | Lines (current) |
|------|---------------|-----------------|
| `.claude/skills/autoteam.md` | Claude Code skill — all agent defs, pipeline, protocols | 661 |
| `skills/autoteam.md` | Copilot CLI skill — same content, `task` tool dispatch | 567 |
| `CLAUDE.md` | Project index, alignment table | 62 |

All 5 concepts touch the same two skill files. Each task modifies both files in parallel, then commits.

---

### Task 1: Multi-Gate Check (Six Gates + Ratchet)

Rename "Linter Pre-Gate" → "Multi-Gate Check" and expand with Gates A-F + ratchet mode.

**Files:**
- Modify: `.claude/skills/autoteam.md:30-45` (file ownership table — rename lint-report → gate-report, add ratchet-baseline.txt)
- Modify: `.claude/skills/autoteam.md:156-175` (Step 6.5 — replace Linter Pre-Gate with Multi-Gate Check)
- Modify: `skills/autoteam.md:34-49` (file ownership table — same changes)
- Modify: `skills/autoteam.md:160-179` (Step 6.5 — same changes)

- [ ] **Step 1: Update file ownership table in Claude Code skill**

In `.claude/skills/autoteam.md`, replace:
```
| `.autoteam/workspace/qa-reports/lint-report.md` | Orchestration |
```
with:
```
| `.autoteam/workspace/qa-reports/gate-report.md` | Orchestration |
| `.autoteam/workspace/qa-reports/ratchet-baseline.txt` | Orchestration |
```

- [ ] **Step 2: Replace Step 6.5 in Claude Code skill**

In `.claude/skills/autoteam.md`, replace the entire `### Step 6.5 — Linter Pre-Gate (Deterministic Enforcement)` section (lines ~156-175) with:

```markdown
### Step 6.5 — Multi-Gate Check (Deterministic Enforcement)
Before dispatching QA agents, run all available deterministic gates on generated code:

1. **Detect language** from `adr.md` tech stack
2. **Ratchet detection:** If lint on pre-existing code (before Implementation) found violations > 0, OR requirement contains "brownfield"/"legacy"/"refactor" → activate ratchet mode. Record `baseline_violations` count.
3. **Run gates in order** (skip any whose tooling is not detected):

| Gate | Name | Tool | Detection |
|------|------|------|-----------|
| A | Formatting + Lint | ruff/eslint/go-vet | Language detected |
| B | Import Boundaries | import-linter | `pyproject.toml` has `[tool.importlinter]` |
| C | Structural Rules | ast-grep | `sgconfig.yml` exists in project |
| D | Snapshot Testing | pytest --snapshot | `__snapshots__/` directory exists |
| E | Golden Outputs | `diff` against committed goldens | `tests/goldens/` directory exists |
| F | Numerical Equiv. | tolerance check (numpy `allclose` or float compare) | `tests/numerical/` directory exists |

4. **Gate logic:**
   - Each gate returns PASS, FAIL, or SKIPPED (no config/tool)
   - **Ratchet mode (Gate A only):** PASS if `current_violations <= baseline_violations`
   - **Normal mode:** PASS requires zero violations
   - Any FAIL (non-ratchet) → write findings to `.autoteam/workspace/qa-reports/gate-report.md`
   - Include in fix-instructions.md as GATE-prefixed fixes (deterministic, highest priority)
   - Dispatch Implementation in FIX MODE for gate fixes BEFORE entering QA pipeline
   - Max 2 gate-fix rounds. After 2 with errors remaining → proceed to QA anyway
   - Ratchet results recorded in `.autoteam/workspace/qa-reports/ratchet-baseline.txt`:
     ```
     baseline: 42
     current: 38
     delta: -4
     status: PASS (reduced by 4)
     ```
5. **No tools available:** Print `[Multi-Gate] ⚠️ No gate tools detected for {language}. Skipping deterministic gates.` and proceed to Step 7

- Print:
  ```
  [Step 4.5/8] Multi-Gate Check
    Gate A (Lint):      ✅ PASS (0 violations) | ⏭️ SKIPPED | ❌ FAIL
    Gate B (Imports):   ✅ PASS | ⏭️ SKIPPED (no import-linter config) | ❌ FAIL
    Gate C (AST Rules): ✅ PASS | ⏭️ SKIPPED (no sgconfig.yml) | ❌ FAIL
    Gate D (Snapshots): ✅ PASS | ⏭️ SKIPPED (no __snapshots__/) | ❌ FAIL
    Gate E (Goldens):   ✅ PASS | ⏭️ SKIPPED (no tests/goldens/) | ❌ FAIL
    Gate F (Numerical): ✅ PASS | ⏭️ SKIPPED (no tests/numerical/) | ❌ FAIL
    Ratchet: OFF | ON (baseline: N, current: N, delta: N)
    Result: N/N active gates PASS
  ```
```

- [ ] **Step 3: Update file ownership table in Copilot CLI skill**

Same changes as Step 1, applied to `skills/autoteam.md`.

- [ ] **Step 4: Replace Step 6.5 in Copilot CLI skill**

Same content as Step 2, applied to `skills/autoteam.md`.

- [ ] **Step 5: Update references to `lint-report.md` throughout both files**

Search both skill files for any remaining references to `lint-report.md` or `Linter Pre-Gate` and update:
- `lint-report.md` → `gate-report.md`
- `Linter Pre-Gate` → `Multi-Gate Check`
- `LINT-` prefix → `GATE-` prefix (in fix-instructions references)
- Step output text `[Lint]` → `[Multi-Gate]`

- [ ] **Step 6: Update Section 7 simplification table in both files**

Replace the `Linter Pre-Gate` row with:
```
| Multi-Gate Check | LLM misses mechanical violations | Never — deterministic checks are always cheaper than LLM review |
| Ratchet mode | Pre-existing code has violations | Drop when project reaches zero baseline violations |
```

- [ ] **Step 7: Verify and commit**

Run verification:
```powershell
Select-String 'Multi-Gate' .claude\skills\autoteam.md, skills\autoteam.md | Measure-Object  # expect ≥6 each
Select-String 'ratchet' .claude\skills\autoteam.md, skills\autoteam.md | Measure-Object  # expect ≥4 each
Select-String 'Gate A' .claude\skills\autoteam.md, skills\autoteam.md | Measure-Object  # expect ≥1 each
Select-String 'lint-report' .claude\skills\autoteam.md, skills\autoteam.md | Measure-Object  # expect 0
Select-String 'Linter Pre-Gate' .claude\skills\autoteam.md, skills\autoteam.md | Measure-Object  # expect 0
```

Commit:
```bash
git add .claude/skills/autoteam.md skills/autoteam.md
git commit -m "feat: expand Linter Pre-Gate to Multi-Gate Check (Gates A-F) with ratchet mode

- Gate A: Formatting + Lint (was Linter Pre-Gate)
- Gate B: Import boundaries (import-linter, conditional)
- Gate C: Structural rules (ast-grep, conditional)
- Gate D: Snapshot testing (pytest --snapshot, conditional)
- Gate E: Golden outputs (diff compare, conditional)
- Gate F: Numerical equivalence (tolerance check, conditional)
- Ratchet mode: allow existing violations, block new ones (brownfield)

Source: alchemiststudiosDOTai/harness-engineering (OpenAI Harness)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Council Multi-Model Voting

Add Council vote protocol to QA agents, diversify models in Copilot CLI, update aggregation logic.

**Files:**
- Modify: `.claude/skills/autoteam.md:267-277` (model assignments — no change for Claude Code, just add comment)
- Modify: `.claude/skills/autoteam.md:431-475` (QA Security agent — add vote section to report format)
- Modify: `.claude/skills/autoteam.md:478-501` (QA Quality agent — add vote section)
- Modify: `.claude/skills/autoteam.md:505-548` (QA Test agent — add vote section)
- Modify: `.claude/skills/autoteam.md:184-206` (Step 8 — update aggregation with council tally)
- Modify: `.claude/skills/autoteam.md:208-217` (Step 9 — update ALL_CLEAR with council requirement)
- Modify: `skills/autoteam.md:264-274` (model assignments — diversify models)
- Modify: `skills/autoteam.md` (same QA and aggregation changes)

- [ ] **Step 1: Add Council Vote section to QA Security agent (Claude Code)**

In `.claude/skills/autoteam.md`, in the QA Security report format (after `## ALL_CLEAR: [true only if zero CRITICAL]`), add:

```markdown

## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence summarizing security posture>
confidence: HIGH | MEDIUM | LOW
```

- [ ] **Step 2: Add Council Vote section to QA Quality agent (Claude Code)**

Same addition after `ALL_CLEAR` line in QA Quality report section.

- [ ] **Step 3: Add Council Vote section to QA Test agent (Claude Code)**

Same addition after `ALL_CLEAR` line in QA Test report section.

- [ ] **Step 4: Update Step 8 aggregation logic (Claude Code)**

In `.claude/skills/autoteam.md`, update Step 8 — Aggregate QA Results. After the Quality Scores block, add:

```markdown
- Tally council votes from each QA report:
  ```
  ## Council Tally
  QA Security: ACCEPT (HIGH) | QA Quality: ACCEPT (MEDIUM) | QA Test: REJECT (HIGH)
  Result: 2/3 ACCEPT → PASS | 1/3 ACCEPT → FAIL
  ```
- Set `ALL_CLEAR: true` only if: **Council ≥ 2/3 ACCEPT** AND zero CRITICAL findings AND overall quality score ≥ 3.0/5
```

- [ ] **Step 5: Update Step 9 QA Loop Decision (Claude Code)**

Update the ALL_CLEAR condition text to include council:
```
**ALL_CLEAR=true** (≥2/3 council ACCEPT + zero CRITICAL + score ≥ 3.0/5) → go to Step 10
```

- [ ] **Step 6: Diversify model assignments (Copilot CLI only)**

In `skills/autoteam.md`, update the model assignment table:

```markdown
| Agent | model parameter |
|---|---|
| Product Planner | `claude-sonnet-4.6` |
| Architecture | `claude-opus-4.6` |
| Implementation | `claude-sonnet-4.6` |
| QA Security | `claude-sonnet-4.6` |
| QA Quality | `gpt-5.1` |
| QA Test | `claude-sonnet-4.6` |
| Documentation | `claude-haiku-4.5` |
```

Add note after table:
```markdown
**Council diversity:** QA Quality intentionally uses a different model family (GPT) to provide independent perspective. This mirrors the OpenAI Harness Engineering "Council" pattern — diverse models catch different issues.
```

- [ ] **Step 7: Apply same vote sections to Copilot CLI skill**

Apply Steps 1-5 changes to `skills/autoteam.md` (QA agents, Step 8 aggregation, Step 9 decision).

- [ ] **Step 8: Verify and commit**

Run verification:
```powershell
Select-String 'Council Vote' .claude\skills\autoteam.md | Measure-Object  # expect 3
Select-String 'Council Vote' skills\autoteam.md | Measure-Object  # expect 3
Select-String 'Council Tally' .claude\skills\autoteam.md | Measure-Object  # expect 1
Select-String '2/3 ACCEPT' .claude\skills\autoteam.md | Measure-Object  # expect ≥2
Select-String 'gpt-5.1' skills\autoteam.md | Measure-Object  # expect 1
```

Commit:
```bash
git add .claude/skills/autoteam.md skills/autoteam.md
git commit -m "feat: add Council multi-model voting to QA pipeline

- Each QA agent outputs vote (ACCEPT/REJECT) with rationale and confidence
- Aggregation requires 2/3 council consensus in addition to existing criteria
- Copilot CLI: QA Quality uses gpt-5.1 for model diversity (Council pattern)
- Claude Code: diversity via different system prompts (model limited to Claude)

Source: alchemiststudiosDOTai/harness-engineering (OpenAI Harness)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: AGENTS.md Auto-Generation

Expand Documentation agent to also generate `AGENTS.md` for the target project.

**Files:**
- Modify: `.claude/skills/autoteam.md:575-607` (Documentation agent definition — add AGENTS.md output)
- Modify: `.claude/skills/autoteam.md:220-223` (Step 10 — add AGENTS.md to output list)
- Modify: `.claude/skills/autoteam.md:610-625` (Section 6 success output — add AGENTS.md to docs list)
- Modify: `skills/autoteam.md:502-514` (Documentation agent — same changes)
- Modify: `skills/autoteam.md:223-226` (Step 10 — same)
- Modify: `skills/autoteam.md:520-533` (Section 6 success output — same)

- [ ] **Step 1: Update Documentation agent output line (Claude Code)**

In `.claude/skills/autoteam.md`, change:
```
**Output:** `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/API.md` (if API endpoints exist)
```
to:
```
**Output:** `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/API.md` (if API endpoints exist), `AGENTS.md` (project root)
```

- [ ] **Step 2: Add AGENTS.md generation rules to Documentation agent (Claude Code)**

After the `**Rules:**` section and before the `---` closing the Documentation agent, add:

```markdown

**AGENTS.md** (always generated, project root):
- Project description (1 paragraph)
- Harness section: detected check command (`just check`, `npm test`, `pytest`, `make test` — infer from project files), lint command, test command
- Structure section: key directories and purposes (max 15 lines)
- Rules section: key constraints from `adr.md` (architectural decisions, import boundaries)
- How to Contribute: branch → change → run harness → commit with evidence
- QA Expectations: security (OWASP), quality (complexity <15, no duplication >10 lines), tests (all AC covered)

**Harness command detection order:** `justfile` → `just check` | `package.json` with `test` script → `npm test` | `pyproject.toml` → `pytest` | `Makefile` → `make check` | fallback → `echo "Configure your check command"`
```

- [ ] **Step 3: Update Step 10 output reference (Claude Code)**

In the Step 10 section, update:
```
- Wait for `docs/README.md` (minimum 10 lines)
```
to:
```
- Wait for `docs/README.md` (minimum 10 lines) and `AGENTS.md` (project root)
```

- [ ] **Step 4: Update Section 6 success output (Claude Code)**

Change:
```
📄 Docs: docs/README.md, docs/ARCHITECTURE.md[, docs/API.md]
```
to:
```
📄 Docs: docs/README.md, docs/ARCHITECTURE.md[, docs/API.md], AGENTS.md
```

- [ ] **Step 5: Apply Steps 1-4 to Copilot CLI skill**

Same changes in `skills/autoteam.md`.

- [ ] **Step 6: Verify and commit**

Run verification:
```powershell
Select-String 'AGENTS.md' .claude\skills\autoteam.md | Measure-Object  # expect ≥4
Select-String 'AGENTS.md' skills\autoteam.md | Measure-Object  # expect ≥4
Select-String 'Harness command detection' .claude\skills\autoteam.md | Measure-Object  # expect 1
```

Commit:
```bash
git add .claude/skills/autoteam.md skills/autoteam.md
git commit -m "feat: auto-generate AGENTS.md in Documentation step

- Documentation agent now outputs AGENTS.md at project root
- Contains: project overview, harness commands, structure, rules, QA expectations
- Harness command auto-detected from justfile/package.json/pyproject.toml/Makefile
- Enables future AI agents to immediately understand the project

Source: alchemiststudiosDOTai/harness-engineering (OpenAI Harness)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: Work Chunks Evidence Protocol

Add chunk.md generation to the Git Integration step.

**Files:**
- Modify: `.claude/skills/autoteam.md:30-45` (file ownership table — add chunk.md)
- Modify: `.claude/skills/autoteam.md:225-239` (Step 10.5 Git Integration — add chunk generation)
- Modify: `skills/autoteam.md:34-49` (file ownership table — same)
- Modify: `skills/autoteam.md:228-242` (Step 10.5 — same)

- [ ] **Step 1: Add chunk.md to file ownership table (Claude Code)**

In `.claude/skills/autoteam.md`, add to file ownership table (before the `escalation.md` row):
```
| `.autoteam/workspace/chunk.md` | Orchestration |
```

- [ ] **Step 2: Add chunk generation to Step 10.5 (Claude Code)**

In `.claude/skills/autoteam.md`, update Step 10.5 — Git Integration. Insert before `2. Stage all generated/modified files`:

```markdown
1.5. **Generate work chunk evidence** — write `.autoteam/workspace/chunk.md`:
   ```markdown
   # Work Chunk: <requirement title from requirement-card.yaml>

   ## Intent
   - <one-line description of what behavior/structure changed>

   ## Preconditions
   - Branch base: <base branch name>
   - Harness status before: <PASS/FAIL/N/A (from pre-existing gate check)>

   ## Evidence
   - Multi-Gate: <N/N active gates PASS / FAIL at gate X / all SKIPPED>
   - QA Council: <N/3 ACCEPT — scores: security X.X, quality X.X, design X.X, test X.X, functionality X.X>
   - QA Rounds: <N round(s) to pass>
   - Sprint Contract: <MET / NOT_MET / SKIPPED>
   - Files created: <count>
   - Files modified: <count>
   - Test files: <count>

   ## Rollback
   git revert <commit-sha>  # fill in after commit
   ```
   - Pull data from: `requirement-card.yaml` (intent), `qa-reports/aggregated-report.md` (QA results), `qa-reports/gate-report.md` (gate results), `sprint-contract.yaml` (contract status)
```

Update staging step to include chunk.md:
```
2. Stage all generated/modified files + `.autoteam/workspace/chunk.md` (exclude rest of `.autoteam/workspace/`, `.autoteam/runs/`)
```

- [ ] **Step 3: Apply Steps 1-2 to Copilot CLI skill**

Same changes in `skills/autoteam.md`.

- [ ] **Step 4: Verify and commit**

Run verification:
```powershell
Select-String 'chunk.md' .claude\skills\autoteam.md | Measure-Object  # expect ≥3
Select-String 'chunk.md' skills\autoteam.md | Measure-Object  # expect ≥3
Select-String 'Work Chunk' .claude\skills\autoteam.md | Measure-Object  # expect ≥1
```

Commit:
```bash
git add .claude/skills/autoteam.md skills/autoteam.md
git commit -m "feat: add Work Chunks evidence protocol to Git Integration

- chunk.md generated before each commit with structured evidence
- Contains: intent, preconditions, QA council results, gate results, rollback
- Committed alongside code for auditable change history

Source: alchemiststudiosDOTai/harness-engineering (OpenAI Harness)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: CLAUDE.md + Final Verification

Update alignment table and run comprehensive checks.

**Files:**
- Modify: `CLAUDE.md:44-55` (alignment table — add OpenAI Harness rows)

- [ ] **Step 1: Update CLAUDE.md alignment table**

Replace the current alignment table with the expanded version from the spec (adds Multi-Gate, Ratchet, Council, Work Chunks, AGENTS.md rows with "OpenAI Harness" source).

New table:
```markdown
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
```

- [ ] **Step 2: Update skill version numbers**

In both skill files, update frontmatter:
```yaml
version: 3.0
```

- [ ] **Step 3: Run comprehensive verification**

```powershell
# Feature presence in both files
$cc = ".claude\skills\autoteam.md"
$cp = "skills\autoteam.md"

# Task 1: Multi-Gate + Ratchet
Select-String 'Multi-Gate Check' $cc, $cp  # both files
Select-String 'Gate A' $cc, $cp  # both files
Select-String 'Gate F' $cc, $cp  # both files
Select-String 'ratchet' $cc, $cp  # both files
Select-String 'gate-report.md' $cc, $cp  # both files

# Task 2: Council
Select-String 'Council Vote' $cc, $cp  # 3 each
Select-String 'Council Tally' $cc, $cp  # 1 each
Select-String '2/3 ACCEPT' $cc, $cp  # ≥2 each
Select-String 'gpt-5.1' $cp  # 1

# Task 3: AGENTS.md
Select-String 'AGENTS.md' $cc, $cp  # ≥4 each
Select-String 'Harness command detection' $cc, $cp  # 1 each

# Task 4: Work Chunks
Select-String 'chunk.md' $cc, $cp  # ≥3 each
Select-String 'Work Chunk' $cc, $cp  # ≥1 each

# No stale references
Select-String 'lint-report' $cc, $cp  # 0
Select-String 'Linter Pre-Gate' $cc, $cp  # 0

# CLAUDE.md
Select-String 'OpenAI Harness' CLAUDE.md  # ≥5

# Line counts
(Get-Content $cc).Count  # track growth
(Get-Content $cp).Count  # track growth
(Get-Content CLAUDE.md).Count  # should be ≤70
```

- [ ] **Step 4: Final commit**

```bash
git add CLAUDE.md .claude/skills/autoteam.md skills/autoteam.md
git commit -m "feat: complete OpenAI Harness Engineering integration (v3.0)

Integrates 5 concepts from alchemiststudiosDOTai/harness-engineering:
1. Multi-Gate Check: 6 gates (A-F) replacing single Linter Pre-Gate
2. Ratchet mechanism: brownfield project support
3. Council voting: multi-model QA consensus (2/3 ACCEPT required)
4. AGENTS.md: auto-generated project agent instructions
5. Work Chunks: structured evidence protocol for every commit

Three design sources now unified:
- Harness Engineering (deusyu) — 6 engineering principles
- Anthropic Original — GAN architecture, sprint contracts, grading
- OpenAI Harness (alchemiststudiosDOTai) — gates, council, ratchet, chunks

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task Dependencies

```
Task 1 (Multi-Gate + Ratchet)  ──┐
Task 2 (Council Voting)        ──┤── Task 5 (CLAUDE.md + Verify)
Task 3 (AGENTS.md)             ──┤
Task 4 (Work Chunks)           ──┘
```

Tasks 1-4 are independent and can be executed in any order or in parallel.
Task 5 must run after all others complete.
