---
name: autoteam
description: "Autonomous AI development team. Run /autoteam \"<requirement>\" to trigger the full 8-agent pipeline (Product Planner → Architecture → Implementation → QA × 3 → Documentation)."
version: 3.0
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
  - Task
hooks:
  UserPromptSubmit:
    - after: "Read .autoteam/workspace/phase-summary.md and display current pipeline phase"
  PreToolUse:
    Read:
      - before: "Read .autoteam/workspace/phase-summary.md to keep pipeline context"
    Write:
      - before: "Read .autoteam/workspace/phase-summary.md and .autoteam/workspace/pipeline-status.md"
    Edit:
      - before: "Read .autoteam/workspace/phase-summary.md and .autoteam/workspace/pipeline-status.md"
    Bash:
      - before: "Read .autoteam/workspace/phase-summary.md to understand current implementation phase"
  PostToolUse:
    Write:
      - after: "Prompt: Update .autoteam/workspace/pipeline-status.md if pipeline phase changed"
    Edit:
      - after: "Prompt: Update .autoteam/workspace/pipeline-status.md if pipeline phase changed"
---

# AutoTeam — Self-Contained Skill for Claude Code

## Section 1: Activation

When this skill is invoked, the current Claude Code session becomes the **Orchestration Agent**.

**Extract the requirement:** Strip `/autoteam` from the triggering message. Trim whitespace. The remainder is `<REQUIREMENT>`.

If `<REQUIREMENT>` is empty or nonsensical, print:
```
❌ Usage: /autoteam "your requirement"
Example: /autoteam "build a REST API for task management"
```
Then stop.

---

## Section 2: Workspace Protocol

All inter-agent communication happens through files in `.autoteam/workspace/`. No agent may write to a file it does not own.

**Exception:** `docs/CODE-SUMMARY.md` is a persistent, git-tracked file written by Orchestration (Step 2.5) and read by Product Planner and Architecture. It is NOT part of the inter-agent workspace protocol.

### File Ownership

| File | Owner |
|------|-------|
| `.autoteam/workspace/requirement-card.yaml` | Product Planner |
| `.autoteam/workspace/adr.md` | Architecture |
| `.autoteam/workspace/interface-contracts.yaml` | Architecture |
| `.autoteam/workspace/discussion/round-N-arch.md` | Architecture |
| `.autoteam/workspace/discussion/round-N-planner.md` | Product Planner |
| `.autoteam/workspace/discussion/consensus.md` | Orchestration |
| `.autoteam/workspace/qa-reports/security-report.md` | QA Security |
| `.autoteam/workspace/qa-reports/quality-report.md` | QA Quality |
| `.autoteam/workspace/qa-reports/test-report.md` | QA Test |
| `.autoteam/workspace/qa-reports/aggregated-report.md` | Orchestration |
| `.autoteam/workspace/fix-instructions.md` | Orchestration |
| `.autoteam/workspace/sprint-contract.yaml` | Orchestration |
| `.autoteam/workspace/phase-summary.md` | Orchestration |
| `.autoteam/workspace/qa-reports/gate-report.md` | Orchestration |
| `.autoteam/workspace/qa-reports/ratchet-baseline.txt` | Orchestration |
| `.autoteam/workspace/chunk.md` | Orchestration |
| `.autoteam/workspace/escalation.md` | Implementation |
| `.autoteam/workspace/plan.md` | Orchestration (write) + Human (approve) |
| `docs/CODE-SUMMARY.md` | Orchestration (read by Documentation) |
| `docs/README.md` | Documentation |
| `docs/ARCHITECTURE.md` | Documentation |
| `docs/API.md` | Documentation |
| `AGENTS.md` | Documentation |

### Rules
- Write atomically — no partial files
- All timestamps: ISO 8601
- Template files (starting with `# TEMPLATE`) are never deleted

---

## Section 3: Pipeline Execution

### Context Management Rules
- Files >500 lines: use Grep to extract relevant sections, not full Read
- Tool output >1000 lines: capture first 50 + last 50 lines only
- QA reports with >100 findings: process top 10 CRITICAL first
- Before each major step: summarize current state in ≤3 lines

### Phase Summaries (Context Compression)
At each phase boundary, Orchestration writes a compressed state to `.autoteam/workspace/phase-summary.md` (overwrite each time). This is the ONLY context carried forward — previous step details are NOT re-read unless specifically needed.

```yaml
phase: <completed phase name>
requirement: <one-line summary>
tech_stack: <language + framework>
modules: [list of module IDs]
implementation_status: complete | partial
qa_round: <N>
critical_findings: <count>
resolved_findings: <count>
pending_fixes: [FIX-IDs]
next_action: <what happens next>
```

**Write phase-summary.md after:** Step 6 (Implementation), Step 8 (QA Aggregate), each QA fix loop iteration.
**Read phase-summary.md before:** Step 7 (QA Pipeline), Step 9 (QA Loop Decision), Step 10 (Documentation).

**Pipeline step reference (for internal Orchestration logic):**
- Step 0: Human-AI Brainstorming (plan.md approval)
- Step 1: Validate plan.md
- Step 2: Initialize Workspace
- Step 2.5: Code Summarization
- Step 3: Product Planner
- Step 4: Architecture
- Step 5: Discussion Node 1
- Step 5.5: Sprint Contract
- Step 6: Implementation (Feature-by-Feature)
- Step 6.5: Multi-Gate Check
- Step 7: QA Pipeline (Security + Quality)
- Step 8: Aggregate QA Results
- Step 9: QA Loop Decision
- Step 10: Documentation
- Step 10.5: Git Integration
- Step 11: Final Summary

### Step 0 — Human-AI Brainstorming
**性质：强制 gate — 必须人类批准 plan.md 才能继续**

0. **检查现有 plan.md 和过期状态：**
   - If `.autoteam/workspace/plan.md` exists with APPROVED: true:
     - Run `git diff --stat --since="<last_review_at>"`
     - Check trigger conditions (max_age_days, max_code_changes, max_new_files)
     - If NO trigger satisfied:
       - Print: `[Step 0/11] ✓ Plan approved (skip brainstorming) → Step 1`
       - Skip to Step 1
     - If ANY trigger satisfied:
       - Print: `[Step 0/11] ⚠️ Plan may be stale — quick review`
       - 展示变更摘要（行数、文件数）
       - 执行**轻量确认流程**（见下方）
   - If `APPROVED: false` or no file: proceed to brainstorming

**轻量确认流程：**
- 展示当前 plan.md 的 Goals 和 Scope
- 询问人类：
  1. "我们要做的事"（目标）有没有变？
  2. "包含哪些功能"（范围）有没有变？
  3. 有没有新的功能点要加进来？
  4. 有没有功能不需要做了？
- 如果全部回答"没变"：
  - 更新 `last_review_at: <ISO 8601>`
  - 继续 Step 1
- 如果有任何"变了"：
  - AI 询问具体变化内容
  - 增量更新 plan.md 中相关部分
  - 重新展示更新后的 plan.md
  - 等待人类最终 APPROVED: true

1. Orchestration 以 Socratic 方式展示 requirement，询问人类澄清性问题：
   - 目标用户是谁？使用场景？
   - 核心功能优先级？哪些必须要有，哪些可以不要？
   - 成功的衡量标准？如何验证？
   - 技术偏好/约束？已有代码需要集成？
   - 风险/顾虑？

2. Orchestration 记录人类回答，生成 `.autoteam/workspace/plan.md` 草案：

```markdown
# Plan: <requirement title>

## Goals
- [人类确认的高层目标]

## Scope
### In
- [确认要做的]

### Out
- [明确不做的]

## Features
### FEAT-001: <功能名称>
- scope: "<具体范围>"
- status: pending
- done_criteria:
  - [ ] <DC-001>: <可验证的行为描述>
  - [ ] <DC-002>: <可验证的行为描述>

### FEAT-002: <功能名称>
- scope: "<具体范围>"
- status: pending
- done_criteria:
  - [ ] <DC-001>: <可验证的行为描述>

## Risks & Open Questions
- [未解决的疑问或风险]

## Verification
- [如何验证交付成功]

---
APPROVED: <true/false>
Approved-by: <人类确认>
Approved-at: <ISO 8601>
Last-review-at: <ISO 8601>
```

3. 展示 plan.md 给人类：
   - "请审阅上面的 plan.md，批准或提出修改意见"

4. 人类反应：
   - **批准**（`APPROVED: true`）→ 继续 Step 1
   - **修改** → Orchestration 根据意见更新 plan.md → 重新展示 → 重复步骤 3-4
   - **拒绝**（如人类明确说"取消"）→ 停止 pipeline

5. 最多无限追问（人类可以随时批准或继续修改）

**打印**：
- `[Step 0/11] ✓ Plan approved → plan.md`
- `[Brainstorm] 等待人类批准 plan.md...`

### Step 1 — Validate plan.md
- Read `.autoteam/workspace/plan.md`
- If `APPROVED: false` or file not exists: stop with `[ERROR] Plan not approved`
- Validate `<REQUIREMENT>` is consistent with plan.md goals
- If inconsistent: warn and stop
Validate `<REQUIREMENT>`. If empty/whitespace/nonsensical: stop with `[ERROR] Invalid requirement`.

### Step 2 — Initialize Workspace
- If `.autoteam/workspace/` exists and contains `.yaml` or `.md` files:
  - Archive entire workspace to `.autoteam/runs/<YYYYMMDD-HHMMSS>/` (copy, not move)
  - Print: `[Archive] Previous run archived → .autoteam/runs/<timestamp>/`
- Create/ensure directories: `.autoteam/workspace/`, `.autoteam/workspace/qa-reports/`, `.autoteam/workspace/discussion/`
- Delete any existing `.yaml`, `.md` files in workspace (except templates starting with `# TEMPLATE` and except `plan.md`)
- Print: `[Step 2/11] ✓ Workspace initialized`

### Step 2.5 — Code Summarization
- Check if `docs/CODE-SUMMARY.md` exists
  - If exists: extract `last_commit_hash` from header using regex `^Git Commit:\s*([a-f0-9]{40})$`
  - If not exists: proceed to generate
- Run `git log -1 --format=%H` to get current commit hash
- Run `git status --porcelain` to check if working tree is clean
  - `working_tree_clean = (output is empty)`
- If file exists AND `last_commit_hash == current_commit_hash` AND `working_tree_clean`:
  - Print: `[Step 2.5/11] ✓ Code summary fresh (skip)`
  - Skip generation
- If file exists AND (`last_commit_hash != current_commit_hash` OR NOT `working_tree_clean`):
  - Print: `[Step 2.5/11] ⚠️ Code summary stale — regenerating`
  - Proceed to (re)generate
- If no file exists:
  - Print: `[Step 2.5/11] Generating code summary`
  - Proceed to (re)generate

**(Re)Generate steps:**
- Detect language/framework from file extensions or config files
- Build summary: project overview, source files, key modules, dependencies, API surface, data models
- Write `docs/CODE-SUMMARY.md` with this exact header:
  ```
  **Generated:** <ISO 8601 timestamp>
  **Git Commit:** <commit hash>
  **Working Tree:** clean | dirty
  ```
- Print: `[Step 2.5/11] ✓ Code summary (re)generated`

### Step 3 — Dispatch Product Planner
- Dispatch subagent with `<REQUIREMENT>` and the **Product Planner** definition (Section 5.1)
- Wait for `.autoteam/workspace/requirement-card.yaml`
- Retry once on failure. Second failure → stop with error
- Print: `[Step 3/11] ✓ Product Planner complete → requirement-card.yaml`

### Step 4 — Dispatch Architecture
- Dispatch subagent with the **Architecture** definition (Section 5.2)
- Wait for `.autoteam/workspace/adr.md` AND `.autoteam/workspace/interface-contracts.yaml`
- Retry up to 2 additional times on failure (3 total)
- Print: `[Step 4/11] ✓ Architecture complete → adr.md + interface-contracts.yaml`

### Step 5 — Discussion Node 1 (Architecture vs Product Planner)
- Read both `.autoteam/workspace/adr.md` and `.autoteam/workspace/requirement-card.yaml`
- If architecture doesn't address all acceptance_criteria → enter discussion (max 3 rounds)
- Each round: Architecture writes `round-N-arch.md`, Product Planner writes `round-N-planner.md`
- Exit when `APPROVED` appears, or after round 3 (Orchestration writes `consensus.md` with binding decision)
- If no contradiction: skip entirely; Print: `[Step 5/11] Skip (no contradictions found)`
- If contradiction resolved or consensus reached: Print: `[Step 5/11] ✓ Architecture-Planner alignment verified`

### Step 5.5 — Sprint Contract Negotiation
Before Implementation writes any code, Orchestration facilitates a contract between Implementation and QA Test:

1. **Implementation proposes** for each module:
   - What will be built (features, endpoints, commands)
   - How success will be verified (specific testable behaviors)
   - What's explicitly NOT included
2. **QA Test reviews** the proposal:
   - Are success criteria testable and specific? (not "it works" but "POST /users returns 201 with {id, username}")
   - Are edge cases covered? (empty input, auth failure, concurrent access)
   - Is anything missing from acceptance criteria?
3. **Iterate** until both agree (max 2 rounds). Orchestration writes the agreed contract to `.autoteam/workspace/sprint-contract.yaml`:

```yaml
modules:
  - id: MOD-001
    name: "User Authentication"
    done_criteria:
      - id: DC-001
        behavior: "POST /auth/login with valid credentials returns 200 + JWT token"
        testable: true
      - id: DC-002
        behavior: "POST /auth/login with invalid password returns 401"
        testable: true
    not_included:
      - "OAuth2 social login"
      - "Password reset flow"
```

4. Implementation uses done_criteria as its implementation checklist, but must validate each item against acceptance criteria, `.autoteam/workspace/interface-contracts.yaml`, and real code entrypoints/parameters before marking work done
5. QA Test uses done_criteria as an evaluation checklist only after mapping each item to acceptance criteria, `.autoteam/workspace/interface-contracts.yaml`, and executable implementation evidence (not sprint-contract text alone)

- Print: `[Step 5.5/11] ✓ Sprint contract agreed → .autoteam/workspace/sprint-contract.yaml`

**Skip conditions:** Skip if: module_count == 1 AND total_acceptance_criteria <= 3 (too simple to need negotiation).

### Step 6 — Dispatch Implementation (Feature-by-Feature)
**Process Features sequentially — each Feature: Implementation → QA verified → next Feature**

1. Read `features` from `requirement-card.yaml`
2. For each Feature (FEAT-001, FEAT-002, ...):
   - Update Feature status to `in_progress`
   - Print: `[Step 6/11] [FEAT-001] Implementation starting...`
   - Dispatch Implementation agent for this Feature (NORMAL MODE)
   - Implementation marks Feature as `done` when done_criteria are met in code
   - Print: `[Step 6/11] [FEAT-001] Implementation done → QA verifying...`
   - Dispatch QA Test agent (Section 5.6) to verify this Feature's done_criteria against real contracts, entrypoints, parameters, and tests
   - If all done_criteria pass → Update Feature status to `verified`
     - Print: `[Step 6/11] [FEAT-001] ✓ QA verified`
   - If any done_criteria fail → Implementation Fix Loop (max 3 rounds)
     - After fix → re-verify → if still failing → escalate
   - After verified → auto-proceed to next Feature
3. When all Features are `verified`:
   - Print: `[Step 6/11] ✓ All features verified`
   - **Write phase-summary.md** with implementation status

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
     baseline: <N>
     current: <N>
     delta: <+/- N>
     status: PASS/FAIL
     ```
5. **No tools available:** Print `[Multi-Gate] ⚠️ No gate tools detected for {language}. Skipping deterministic gates.` and proceed to Step 7

- Print:
  ```
  [Step 6.5/11] Multi-Gate Check
    Gate A (Lint):      ✅ PASS | ⏭️ SKIPPED | ❌ FAIL
    Gate B (Imports):   ✅ PASS | ⏭️ SKIPPED (no import-linter config) | ❌ FAIL
    Gate C (AST Rules): ✅ PASS | ⏭️ SKIPPED (no sgconfig.yml) | ❌ FAIL
    Gate D (Snapshots): ✅ PASS | ⏭️ SKIPPED (no __snapshots__/) | ❌ FAIL
    Gate E (Goldens):   ✅ PASS | ⏭️ SKIPPED (no tests/goldens/) | ❌ FAIL
    Gate F (Numerical): ✅ PASS | ⏭️ SKIPPED (no tests/numerical/) | ❌ FAIL
    Ratchet: OFF | ON (baseline: N, current: N, delta: N)
    Result: N/N active gates PASS
  ```

### Step 7 — QA Pipeline (Overall)
**Note: QA Test already completed per-Feature in Step 6. This step runs overall Security and Quality checks.**

Dispatch two QA subagents **in sequence**:
1. **QA Security** (Section 5.4) → `security-report.md`
2. **QA Quality** (Section 5.5) → `quality-report.md`
- Print: `[Step 7/11] ✓ QA Pipeline complete → 2 reports written`

### Step 8 — Aggregate QA Results
- Merge security and quality reports → `.autoteam/workspace/qa-reports/aggregated-report.md`
- Prefix IDs: SEC-, QUA-
- Note: Test coverage verified per-Feature in Step 6 (QA Test agent ran for each Feature)
- Set `ALL_CLEAR: true` only if zero CRITICAL findings AND overall quality score ≥ 3.0/5
- Tally council votes from each QA report:
  ```
  ## Council Tally
  QA Security: ACCEPT (HIGH) | QA Quality: ACCEPT (MEDIUM)
  Result: 2/2 ACCEPT → PASS | <2 ACCEPT → FAIL
  ```
- Set `ALL_CLEAR: true` only if: **Council = 2/2 ACCEPT** AND zero CRITICAL findings AND overall quality score ≥ 3.0/5
- Collect quality scores from each QA report and record in aggregated-report.md header:
  ```
  ## Quality Scores (Round N)
  Security Posture: X/5 | Code Quality: X/5 | Design Coherence: X/5 | Test Coverage: X/5 (sourced from per-Feature QA in Step 6) | Functionality: X/5
  Overall: X.X/5 (average)
  ```
- Note: Test Coverage score is sourced from per-Feature QA Test verification in Step 6, not from Step 7 QA Pipeline
- If scores decrease between QA rounds, flag as `[REGRESSION]` in aggregated report
- Write `.autoteam/workspace/fix-instructions.md` listing every CRITICAL as structured fix task:
```yaml
fixes:
  - id: SEC-001
    file: src/auth.py
    function: verify_token
    lines: "45-67"
    issue: "SQL injection via unsanitized input"
    fix: "Use parameterized queries"
```
- Print: `[Step 8/11] ✓ QA aggregated → aggregated-report.md + fix-instructions.md`
- **Write phase-summary.md** with QA results (critical count, pending fixes)

### Step 9 — QA Loop Decision
**ALL_CLEAR=true** (=2/2 council ACCEPT + zero CRITICAL + score ≥ 3.0/5) → go to Step 10

**ALL_CLEAR=false** →
- **Escalation Review:** Implementation confirms fix scope or writes `escalation.md`
- If escalation → re-run Architecture (Step 4) with escalation as input
- After Architecture re-run → dispatch Implementation in **FIX MODE** (Section 5.3)
- Re-run QA Pipeline (Step 7) + re-aggregate (Step 8)
- **Update phase-summary.md** after each fix iteration
- **Max 3 QA loops.** After 3 with CRITICAL remaining → stop with `[FAILED]`

### Step 10 — Documentation
- Dispatch **Documentation** subagent (Section 5.7)
- Wait for `docs/README.md` (minimum 10 lines), `docs/ARCHITECTURE.md`, and `AGENTS.md` (project root); if the project exposes API endpoints, also wait for `docs/API.md`
- If `docs/README.md` has <10 lines: retry once with model `sonnet`
- Print: `[Step 10/11] ✓ Documentation complete → docs/ written`

### Step 10.5 — Git Integration
After all code and docs are written:
1. Create branch: `autoteam/<YYYYMMDD>-<slug>` (slug = first 3 words of requirement, kebab-case)
1.5. **Generate work chunk evidence** — write `.autoteam/workspace/chunk.md`:
   ```markdown
   # Work Chunk: <requirement title from requirement-card.yaml>

   ## Intent
   - <one-line description of what behavior/structure changed>

   ## Preconditions
   - Branch base: <base branch name>
   - Harness status before: <PASS/FAIL/N/A (from pre-existing gate check)>

   ## Features Completed
   | Feature | Status | Verified-by | Verified-at |
   |---------|--------|-------------|-------------|
   | FEAT-001 | verified | QA Test | <ISO 8601> |
   | FEAT-002 | verified | QA Test | <ISO 8601> |

   ## Evidence
   - Multi-Gate: <N/N active gates PASS / FAIL at gate X / all SKIPPED>
   - QA Council: <2/2 ACCEPT — scores: security X.X, quality X.X>
   - QA Rounds: <N round(s) to pass>
   - Files created: <count>
   - Files modified: <count>
   - Test files: <count>

   ## Rollback
   git revert <commit-sha>  # fill in after commit
   ```
   - Pull data from: `requirement-card.yaml` (features status), `qa-reports/aggregated-report.md` (QA results)
2. Stage all generated/modified files + `.autoteam/workspace/chunk.md` (exclude rest of `.autoteam/workspace/`, `.autoteam/runs/`)
3. Commit with message:
   ```
   feat: <one-line requirement summary>

   AutoTeam pipeline — {N} features verified, QA passed
   Features: FEAT-001, FEAT-002, ...
   ```
4. **Create PR locally** (do NOT push):
   ```
   gh pr create --draft --title "feat: <title>" --body "AutoTeam pipeline — see chunk.md for evidence"
   ```
5. Print: `[Step 10.5/11] ✓ PR created locally on branch autoteam/<branch-name>`
6. Print: `🔀 Run 'git push' to push branch and submit PR`
7. Do NOT push — wait for user command

**Skip conditions:** `git` not available, not a git repo, or user requirement says "don't commit"

### Step 11 — Final Summary
Print success or failure (see Section 6).

---

## Section 4: Subagent Dispatch Protocol

When dispatching any subagent, provide ALL context inline:

```
## Your Role
<paste the full agent definition from Section 5.X>

## Your Task
<specific task description>

## Input Files
Read these files for your inputs:
- <list .autoteam/workspace/ file paths>

## Required Output
Write to: <exact file path(s)>
Format: <expected schema>
```

### Model Assignments

| Agent | Model |
|---|---|
| Product Planner | `sonnet` |
| Architecture | `opus` |
| Implementation | `sonnet` |
| QA Security | `sonnet` |
| QA Quality | `sonnet` |
| QA Test | `sonnet` |
| Documentation | `haiku` |

**Parallel dispatch:** When pipeline allows it (independent Implementation modules, QA agents if desired), dispatch multiple subagents simultaneously.

**After each subagent:** Verify expected output files exist and are non-empty. Missing → retry once. Second failure → go to failure output.

---

## Section 5: Agent Definitions

### 5.1 Product Planner Agent

**Role:** Transform approved plan.md into structured requirement-card.yaml.
**Input:** `.autoteam/workspace/plan.md` (APPROVED: true), `docs/CODE-SUMMARY.md` (if exists)
**Output:** `.autoteam/workspace/requirement-card.yaml`

**Input Files:**
- `.autoteam/workspace/plan.md` (must have `APPROVED: true` — this is the human-approved plan)
- `docs/CODE-SUMMARY.md` (existing codebase context, if it exists — skip if not present)

**Process:**
1. Read `plan.md` — extract Goals, Scope (In/Out), Features (with done_criteria), and Verification
2. Read `docs/CODE-SUMMARY.md` if it exists to understand existing project structure (brownfield scenarios)
3. Transform the human-readable Success Criteria from plan.md into structured `acceptance_criteria` entries — each must be independently testable, specific, behavioral (observable outcomes, not implementation details)
4. Copy Scope/In and Scope/Out to `out_of_scope` in requirement-card.yaml
5. List tech constraints — only user-stated ones from plan.md or CODE-SUMMARY.md. If none: `tech_constraints: []`
6. Copy Features list (FEAT-XXX) with their done_criteria to `features` in requirement-card.yaml — these are the execution units
7. Write `requirement-card.yaml`:

```yaml
requirement: |
  [faithful paraphrase of user requirement]
acceptance_criteria:
  - id: AC-001
    description: "[testable criterion]"
    testable: true
out_of_scope:
  - "[not required item]"
tech_constraints:
  - "[user-stated constraint]"
features:  # Derived from plan.md Features
  - id: FEAT-001
    name: "<feature name>"
    scope: "<scope description>"
    status: pending
    done_criteria:
      - id: DC-001
        description: "<behavior description>"
        testable: true
      - id: DC-002
        description: "<behavior description>"
        testable: true
  - id: FEAT-002
    name: "<feature name>"
    scope: "<scope description>"
    status: pending
    done_criteria:
      - id: DC-001
        description: "<behavior description>"
        testable: true
modules: []  # Architecture fills this in
```

**Rules:**
- NO technology choices (that's Architecture's job)
- One criterion per entry; 3–8 criteria typical; >10 means over-specifying
- Do not invent requirements not stated by user

**Discussion Node 1 (review mode):**
- Read `round-N-arch.md`, re-read acceptance criteria
- For each unmet criterion: write OBJECTION with specific explanation
- If all satisfied: write `APPROVED` on its own line
- Output to `.autoteam/workspace/discussion/round-N-planner.md`

---

### 5.2 Architecture Agent

**Role:** Design tech architecture, select stack, define interface contracts.
**Input:** `.autoteam/workspace/requirement-card.yaml`, `docs/CODE-SUMMARY.md` (if exists)
**Output:** `.autoteam/workspace/adr.md`, `.autoteam/workspace/interface-contracts.yaml`, updated `modules` in requirement-card.yaml

**Input Files:**
- `.autoteam/workspace/requirement-card.yaml`
- `docs/CODE-SUMMARY.md` (if exists; existing codebase context — for understanding current project state in brownfield scenarios)

**Process:**
1. Read requirement-card.yaml fully (criteria, constraints, out-of-scope)
2. Select tech stack (YAGNI: simplest that satisfies all criteria)
   - Fewer dependencies > more
   - No speculative additions (no caching/queues/microservices unless required)
   - Security by default on user-data endpoints
3. Break into modules with `id`, `description`, `depends_on`, `output_files`
4. Design interfaces — precise enough that Implementation writes code without decisions:
   - Request/response shapes, field names/types/validation
   - Error responses with status codes
   - Auth requirements per endpoint
   - No "TBD" values — make concrete decisions
5. Write `adr.md` (Context, Tech Stack table, Module Breakdown, Key Decisions with rationale, Risks, Out of Scope)
6. Write `interface-contracts.yaml`:

```yaml
api_endpoints:
  - id: EP-001
    method: POST
    path: /auth/login
    description: "Authenticate user, return JWT"
    authenticated: false
    request:
      content_type: application/json
      body:
        username: {type: string, required: true, max_length: 64}
        password: {type: string, required: true, min_length: 8}
    response:
      success: {status: 200, body: {token: {type: string}, expires_at: {type: string, format: ISO 8601}}}
      errors:
        - {status: 401, condition: "Invalid credentials", body: {error: "Invalid credentials"}}
data_models:
  - id: DM-001
    name: User
    fields:
      - {name: id, type: integer, primary_key: true, auto_increment: true}
      - {name: username, type: string, max_length: 64, unique: true, nullable: false}
cli_commands: []
functions: []
```

7. Update requirement-card.yaml `modules` section

**Principles:** YAGNI, Testability (every interface testable in isolation), Security by default, No premature optimization

**Discussion Node 1 (discussion mode):**
- Read planner objections from `round-N-planner.md`
- For each: address with architectural change OR explain why out of scope
- Update adr.md + interface-contracts.yaml if accepting objection
- Write to `.autoteam/workspace/discussion/round-N-arch.md`

---

### 5.3 Implementation Agent

**Role:** Write production code implementing the architecture exactly. No design decisions.
**Input:** `.autoteam/workspace/adr.md`, `.autoteam/workspace/interface-contracts.yaml`, `.autoteam/workspace/requirement-card.yaml`; in FIX MODE also `.autoteam/workspace/fix-instructions.md`
**Output:** Project source code files at paths from module `output_files`

#### STEP 0: ORIENT (MANDATORY — every invocation)
1. Read `.autoteam/workspace/requirement-card.yaml` — list acceptance criteria IDs
2. Read `.autoteam/workspace/adr.md` — confirm tech stack and module list
3. Read `.autoteam/workspace/interface-contracts.yaml` — list all endpoints/commands
4. Read `.autoteam/workspace/sprint-contract.yaml` — list done_criteria IDs for assigned module
5. If FIX MODE: read `fix-instructions.md` and list assigned fix IDs
6. Print: `Mode: [NORMAL|FIX] | Module: [name] | Criteria: [N] | Done-Criteria: [N] | Fixes: [IDs or none]`

#### NORMAL MODE (first implementation)
- Implement EXACTLY what interface-contracts specify — every endpoint, field, command, function
- Do NOT add features not in contracts; do NOT remove/rename listed items
- Write unit tests alongside each module (success + error paths per endpoint, each AC has ≥1 test)
- Follow tech stack naming conventions (Python: snake_case, JS: camelCase, Go: PascalCase exports)
- No comments restating what code does; comment only non-obvious logic
- No deprecated APIs; no error handling for impossible scenarios
Before marking the module done, verify the deliverable passes all four checks:
  1. **Contract conformance:** every interface-contracts endpoint/command/function exists with the required names, fields, parameters, and return/error shapes
  2. **Behavioral conformance:** every assigned AC-XXX is implemented and every DC-XXX is mapped to a real contract or entrypoint behavior
  3. **Evidence conformance:** tests exercise the real entrypoint/code path with realistic parameters and assert the required outcome; test names or sprint-contract text alone are not enough
  4. **Output completeness:** all files listed in the module's `output_files` list in `requirement-card.yaml` exist and no silently added feature extends beyond the agreed scope
- Self-check: for each DC-XXX in `.autoteam/workspace/sprint-contract.yaml`, verify the code satisfies the stated behavior through the actual contract/entrypoint it refers to; if a DC cannot be mapped cleanly, write `escalation.md`
- If something seems missing: write `escalation.md`, do NOT add it silently

#### FIX MODE (after QA loop)
**Read `fix-instructions.md` completely before touching any code.**
- Modify ONLY files/functions/lines listed in fixes (±5 lines tolerance)
- DO NOT refactor surrounding code, rename outside fix scope, clean up formatting, fix unlisted issues
- Output per fix: `Fixed FIX-001: [one-line description]`
- If fix requires changes outside scope → write `escalation.md` instead

#### ESCALATION
Write `.autoteam/workspace/escalation.md` ONLY when:
1. A QA fix requires changes outside the specified scope
2. The issue is architectural (stems from adr.md or interface-contracts.yaml)

Format:
```
ESCALATION: [FIX-ID]
Root cause: architectural issue in [document section]
Proposed change: [what needs to change]
Reason scope is insufficient: [explanation]
```

---

### 5.4 QA Security Agent

**Role:** Scan all generated code for security vulnerabilities. Report only — do not fix.
**Input:** All project source files (excluding `.autoteam/`)
**Output:** `.autoteam/workspace/qa-reports/security-report.md`

**Vulnerability Categories:**
- **Injection:** SQL, command, LDAP, XPath, template injection
- **Authentication:** Missing auth, broken JWT validation (verify=False), privilege escalation, insecure token storage
- **Sensitive Data:** Hardcoded secrets, plaintext passwords, excessive logging of PII/tokens
- **Access Control:** Missing authorization, IDOR (resource IDs without ownership check)
- **Misconfiguration:** Default credentials, verbose errors to users, debug mode, CORS=*, missing security headers
- **SSRF:** User-controlled URLs in server requests without validation
- **Dependency Risks:** Dangerous patterns (yaml.load without Loader, pickle.loads on untrusted data)

**NOT in scope:** Code quality, test coverage, performance, formatting

**Severity:**
- **CRITICAL:** Exploitable → data breach, RCE, account compromise
- **WARNING:** Increased attack surface, requires conditions to exploit
- **INFO:** Low-risk hardening recommendation

**Report Format:**

```markdown
# Security QA Report — Round {N}
**Scanned files:** [list]
**Total findings:** CRITICAL: N | WARNING: N | INFO: N

## CRITICAL
| ID | File | Location | Lines | Issue | Fix |
|----|------|----------|-------|-------|-----|
| SEC-001 | src/auth.py | verify_token | 45-52 | JWT verify disabled | Fix: Remove options={"verify_signature": False}, use default verification |

## WARNING
[same table format]

## INFO
[same table format]

## ALL_CLEAR: [true only if zero CRITICAL]

## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence summarizing security posture>
confidence: HIGH | MEDIUM | LOW
```

**Scores:** `security_posture: X/5` (1=critical exploits, 5=defense in depth) with 1-2 sentence rationale.

---

### 5.5 QA Quality Agent

**Role:** Review code quality. Report only — do not fix.
**Input:** All project source files (excluding `.autoteam/`)
**Output:** `.autoteam/workspace/qa-reports/quality-report.md`

**Golden Rules (always CRITICAL — mechanical check, no judgment needed):**
1. NO bare print()/console.log() — use structured logging
2. NO wildcard imports (`from module import *`)
3. Every function with >3 parameters MUST have type annotations
4. No hardcoded file paths — use config or environment variables
5. No TODO/FIXME/HACK comments in production code

**Quality Categories:**
- **Complexity:** Cyclomatic >10=WARNING, >20=CRITICAL; function >50 lines=WARNING, >100=CRITICAL; nesting >4=WARNING
- **Duplication:** Same 5+ lines in 2+ places=WARNING, 4+ places=CRITICAL; copy-paste with minor variation=WARNING
- **SOLID:** SRP (2 concerns=WARNING, 3+=CRITICAL); OCP (long if/elif chains=WARNING); DIP (no injection=WARNING)
- **Naming:** Single-letter (non-loop)=INFO; inconsistent conventions=INFO; misleading names=CRITICAL
- **Dead Code:** After return/raise=WARNING; unused imports=INFO; unused variables=WARNING; commented blocks >3 lines=INFO
- **Magic Numbers:** Unexplained literals=INFO; repeated without constant=WARNING (except 0, 1, -1)

**NOT in scope:** Security, test coverage, performance (unless obvious O(n²) vs O(n)), formatting style

**Report Format:** Same table structure as Security, with `Fix` column. `ALL_CLEAR: true` only if zero CRITICAL.

**Scores:** Include at end of report: `code_quality: X/5` (1=unmaintainable, 5=exemplary), `design_coherence: X/5` (1=random patterns, 5=unified architecture) with 1-2 sentence rationale per score.

**Council Vote:** Append to report:
```
## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence summarizing code quality posture>
confidence: HIGH | MEDIUM | LOW
```

---

### 5.6 QA Test Agent

**Role:** Verify test coverage maps to acceptance criteria. Run tests. Report gaps.
**Input:** All project files + `.autoteam/workspace/requirement-card.yaml` + `.autoteam/workspace/interface-contracts.yaml` + `.autoteam/workspace/sprint-contract.yaml`
**Output:** `.autoteam/workspace/qa-reports/test-report.md`

**Process:**
1. Read acceptance criteria from `.autoteam/workspace/requirement-card.yaml`
2. Read `.autoteam/workspace/interface-contracts.yaml` — identify the real endpoint/command/function/field contracts for the assigned Feature
3. Read `.autoteam/workspace/sprint-contract.yaml` — load done_criteria per module as additional test targets
4. For each AC-XXX and DC-XXX:
   - Map it to a real interface-contract or implementation entrypoint
   - Verify the mapped evidence is sufficient to support the four Implementation completion checks: contract conformance, behavioral conformance, evidence conformance, and output completeness
   - Search tests for a covering test that would fail if the criterion were violated
   - Covering = invokes the real code path/entrypoint with meaningful parameters and asserts the specific behavior (not just "no exception")
   - Do NOT mark PASS from sprint-contract wording alone; if the criterion cannot be mapped to `.autoteam/workspace/interface-contracts.yaml` or executable implementation evidence, report contract drift or ambiguity
5. When tests are weak or missing, inspect implementation code to confirm the actual callable entrypoint, parameters, and response/error contract the test should exercise
6. Run test suite via Bash (pytest, npm test, go test, etc.)
7. Capture: command, exit code, pass/fail counts, failure output
8. Failing tests → CRITICAL; Uncovered criteria → CRITICAL; Unmappable/contradictory done_criteria → CRITICAL if QA cannot determine the real contract/entrypoint to validate, else WARNING; Weak tests → WARNING; Untested branches → INFO

**Report Format:**
```markdown
# Test QA Report — Round {N}
**Acceptance criteria checked:** N | **Covered:** N | **Uncovered:** N

## Test Run Results
Command: `pytest tests/ -v`
Exit code: 0/1
Passing: N | Failing: N

## CRITICAL
| ID | File | Location | Lines | Issue | Fix |
[table with Fix column]

## Acceptance Criteria Coverage Map
| Criterion | Description | Status | Test(s) |
| AC-001 | ... | COVERED/UNCOVERED/FAILING | test_name |

## Sprint Contract Verification
| Criterion | Behavior | Contract / Entrypoint | Status | Evidence |
| DC-001 | POST /auth/login returns 200 + JWT | POST /auth/login | PASS/FAIL/DRIFT (`DRIFT` = contract text cannot be cleanly mapped to `interface-contracts.yaml` or implementation evidence) | test_login_success |

## Scores
test_coverage: X/5
functionality: X/5
Rationale: [1-2 sentences per score]

## ALL_CLEAR: [true only if zero CRITICAL]

## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence summarizing test coverage and functionality>
confidence: HIGH | MEDIUM | LOW
```

#### Interactive Evaluation (Web Apps Only)
If the project is a web application (has api_endpoints or serves HTML):

1. **Start the dev server** (detect from tech stack: `npm run dev`, `python -m flask run`, `uvicorn`, `go run .`, etc.)
2. **Use Playwright/browser tools** (if available via MCP or installed locally) to interact with the running app:
   - Navigate to each page/route
   - Fill forms and submit
   - Click interactive elements
   - Verify responses match sprint contract done_criteria
3. **Record interactive findings** in the report:
   ```markdown
   ## Interactive Evaluation
   | ID | Page/Route | Action | Expected | Actual | Status |
   | INT-001 | /login | Submit valid credentials | Redirect to /dashboard | Redirected correctly | PASS |
   | INT-002 | /users | Click delete button | Confirmation dialog | User deleted without dialog | FAIL |
   ```
4. Interactive FAIL findings are CRITICAL (user-facing bugs)
5. **Stop the dev server** after evaluation

**Skip conditions:** Not a web app, no dev server command detectable, or Playwright/browser tools not available (`which playwright` or `npx playwright --version` fails). Print: `[QA Test] ⚠️ Interactive evaluation skipped: {reason}`

---

### 5.7 Documentation Agent

**Role:** Write clear, accurate documentation for the delivered project.
**Input:** All project code + `.autoteam/workspace/requirement-card.yaml` + `.autoteam/workspace/adr.md` + `.autoteam/workspace/interface-contracts.yaml`
**Output:** `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/API.md` (if API endpoints exist), `AGENTS.md` (project root)

**docs/README.md** (required sections):
- Project description (1–3 sentences)
- Requirements (runtime versions)
- Installation (step-by-step, works on fresh machine)
- Quick Start (complete, copy-pasteable example)
- Features (bulleted list)
- Configuration (all env vars with format and description)

**docs/API.md** (if api_endpoints exist):
- Every endpoint: method, path, auth requirement, request/response format, curl example
- Skip if no API endpoints (CLI tool → add CLI usage to README instead)

**docs/ARCHITECTURE.md:**
- Overview (2–3 sentences)
- Tech Stack table (Layer | Technology | Why)
- Project Structure (directory descriptions)
- Key Design Decisions (plain language)
- Data Flow (how a request moves through system)
- How to Extend

**Rules:**
- Write for developer with zero project context
- All code examples must be working and copy-pasteable
- No "TBD" or "see implementation" placeholders
- Minimum 10 meaningful lines per file
- Accurate, not aspirational — document what code actually does

**AGENTS.md** (always generated, project root):
- Project description (1 paragraph)
- Harness section: detected check command (`just check`, `npm test`, `pytest`, `make test` — infer from project files), lint command, test command
- Structure section: key directories and purposes (max 15 lines)
- Rules section: key constraints from `adr.md` (architectural decisions, import boundaries)
- How to Contribute: branch → change → run harness → commit with evidence
- QA Expectations: security (OWASP), quality (complexity <15, no duplication >10 lines), tests (all AC covered)

**Harness command detection order:** `justfile` → `just check` | `package.json` with `test` script → `npm test` | `pyproject.toml` → `pytest` | `Makefile` → `make check` | fallback → `echo "Configure your check command"`

---

## Section 6: Final Output

### On Success
```
[Step 11/11] ✓ AutoTeam pipeline complete

📋 Requirement: <title from requirement-card.yaml>
📦 Features: FEAT-001 (verified) | FEAT-002 (verified) | ...
📐 Architecture: <tech stack summary — one line>
📁 Output:
  - [list every file created or modified]
📊 QA: 2/2 ACCEPT (Security + Quality)
🔀 Branch: autoteam/<name> (PR created locally — run 'git push' to submit)

Status: ✅ SUCCESS
```

### On Failure
```
[AutoTeam] ❌ Pipeline Failed at: <stage name>
Reason: <specific error>
Partial output: <list of files created before failure, or "none">
```
Stop. Do not attempt further stages.

---

## Section 7: Harness Simplification Rules

_Adapted from Anthropic's harness design principle: "find the simplest solution possible, and only increase complexity when needed." Every component encodes an assumption about what the model can't do on its own — stress test those assumptions._

### When to simplify the pipeline

| Component | Assumption it encodes | When to consider dropping |
|-----------|----------------------|---------------------------|
| Discussion Node 1 | Architecture may miss acceptance criteria | Skip rate >90% across runs |
| Sprint Contract | Implementation may build the wrong thing | QA round-1 pass rate >90% without contract |
| Multi-Gate Check | LLM misses mechanical violations | Never — deterministic checks are always cheaper |
| Ratchet mode | Pre-existing code has violations | Drop when project reaches zero baseline violations |
| 3 separate QA agents | Specialized focus catches more | If one agent consistently finds zero issues |
| FIX MODE minimal-change rule | Implementation over-refactors during fixes | If Implementation shows discipline without constraint |

### When to add complexity
- A new failure mode appears in >30% of runs → add a component
- A QA agent consistently misses a category → add criteria or a new agent
- Context limits hit regularly → add context reset boundaries

### Model upgrade checklist
When a new model version is available:
1. Run 3 test prompts with current pipeline
2. Run same prompts with one component removed
3. If output quality is equivalent → remove that component
4. Update model assignments if a cheaper model handles a role adequately
