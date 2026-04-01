---
name: autoteam
description: "Autonomous AI development team for Copilot CLI. Triggers a full 8-agent pipeline (Product Planner → Architecture → Implementation → QA × 3 → Documentation) that analyzes, designs, implements, tests, and documents your requirement."
version: 3.0
platform: copilot-cli
---

# AutoTeam — Self-Contained Skill for Copilot CLI

> Reference template only. GitHub Copilot CLI does **not** auto-discover `skills\`. For repo-native AutoTeam usage, put entry rules in `.github/copilot-instructions.md` and pipeline rules in `.github/instructions/autoteam.instructions.md`.

## Section 1: Activation

### How to Invoke

In Copilot CLI, invoke this skill by saying:
- "Run autoteam with requirement: build a REST API for task management"
- "Execute the autoteam pipeline for: ..."

Extract the requirement from the user's message. If no clear requirement is found, ask:
```
Please provide a software requirement.
Example: "build a REST API for task management"
```

When activated, the current session becomes the **Orchestration Agent** and drives the full pipeline using the `task` tool to dispatch subagents.

---

## Section 2: Workspace Protocol

All inter-agent communication happens through files in `.autoteam/workspace/`. No agent may write to a file it does not own.

### File Ownership

| File | Owner |
|------|-------|
| `.autoteam/workspace/requirement-card.yaml` | Product Planner |
| `.autoteam/workspace/adr.md` | Architecture |
| `.autoteam/workspace/interface-contracts.yaml` | Architecture |
| `.autoteam/workspace/discussion/round-N-*.md` | Orchestration |
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

### Rules
- Write atomically — no partial files
- All timestamps: ISO 8601
- Template files (starting with `# TEMPLATE`) are never deleted

---

## Section 3: Pipeline Execution

### Context Management Rules
- Files >500 lines: use grep to extract relevant sections, not full read
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

### Step 1 — Input Validation
Validate requirement. If empty/whitespace/nonsensical: stop with `[ERROR] Invalid requirement`.

### Step 2 — Initialize Workspace
- If `.autoteam/workspace/` exists and contains `.yaml` or `.md` files:
  - Archive entire workspace to `.autoteam/runs/<YYYYMMDD-HHMMSS>/` (copy, not move)
  - Print: `[Archive] Previous run archived → .autoteam/runs/<timestamp>/`
- Create/ensure directories: `.autoteam/workspace/`, `.autoteam/workspace/qa-reports/`, `.autoteam/workspace/discussion/`
- Delete any existing `.yaml`, `.md` files in workspace (except templates starting with `# TEMPLATE` and except `plan.md`)
- Print: `[Step 0/8] ✓ Workspace initialized`

### Step 3 — Dispatch Product Planner
- Use the `task` tool to dispatch the Product Planner (Section 5.1)
- Wait for `.autoteam/workspace/requirement-card.yaml`
- Retry once on failure. Second failure → stop with error
- Print: `[Step 1/8] ✓ Product Planner complete → requirement-card.yaml`

### Step 4 — Dispatch Architecture
- Use the `task` tool to dispatch the Architecture agent (Section 5.2)
- Wait for `.autoteam/workspace/adr.md` AND `.autoteam/workspace/interface-contracts.yaml`
- Retry up to 2 additional times on failure (3 total)
- Print: `[Step 2/8] ✓ Architecture complete → adr.md + interface-contracts.yaml`

### Step 5 — Discussion Node 1 (Architecture vs Product Planner)
- Read both `adr.md` and `requirement-card.yaml`
- If architecture doesn't address all acceptance_criteria → enter discussion (max 3 rounds)
- Each round: dispatch Architecture in discussion mode, then Product Planner in review mode
- Exit when `APPROVED` appears or after round 3 (write `consensus.md` with binding decision)
- If no contradiction: skip entirely
- Print: `[Step 3/8] ✓ Architecture-Planner alignment verified`

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

4. Implementation uses done_criteria as its implementation checklist, but must reconcile each item with acceptance criteria, `interface-contracts.yaml`, and real code entrypoints/parameters before marking work done
5. QA Test uses done_criteria as its evaluation checklist only after mapping each item to acceptance criteria, `interface-contracts.yaml`, and executable implementation evidence (not sprint-contract text alone)

- Print: `[Step 3.5/8] ✓ Sprint contract agreed → sprint-contract.yaml`

**Skip conditions:** If only 1 module with ≤3 acceptance criteria, skip contract (too simple to need negotiation).

### Step 6 — Dispatch Implementation
- Read `modules` from `requirement-card.yaml`
- Modules with no `depends_on`: dispatch as **parallel** task agents
- Modules with `depends_on`: dispatch **serially** after dependencies complete
- Each uses the Implementation definition (Section 5.3) in NORMAL MODE
- Print: `[Step 4/8] ✓ Implementation complete → all modules written`
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
  [Step 4.5/8] Multi-Gate Check
    Gate A (Lint):      ✅ PASS | ⏭️ SKIPPED | ❌ FAIL
    Gate B (Imports):   ✅ PASS | ⏭️ SKIPPED (no import-linter config) | ❌ FAIL
    Gate C (AST Rules): ✅ PASS | ⏭️ SKIPPED (no sgconfig.yml) | ❌ FAIL
    Gate D (Snapshots): ✅ PASS | ⏭️ SKIPPED (no __snapshots__/) | ❌ FAIL
    Gate E (Goldens):   ✅ PASS | ⏭️ SKIPPED (no tests/goldens/) | ❌ FAIL
    Gate F (Numerical): ✅ PASS | ⏭️ SKIPPED (no tests/numerical/) | ❌ FAIL
    Ratchet: OFF | ON (baseline: N, current: N, delta: N)
    Result: N/N active gates PASS
  ```

### Step 7 — QA Pipeline
Dispatch three QA agents **in sequence**:
1. **QA Security** (Section 5.4) → `security-report.md`
2. **QA Quality** (Section 5.5) → `quality-report.md`
3. **QA Test** (Section 5.6) → `test-report.md`
- Print: `[Step 5/8] ✓ QA Pipeline complete → 3 reports written`

### Step 8 — Aggregate QA Results
- Merge all three reports → `.autoteam/workspace/qa-reports/aggregated-report.md`
- Prefix IDs: SEC-, QUA-, TST-
- Set `ALL_CLEAR: true` only if zero CRITICAL findings AND overall quality score ≥ 3.0/5
- Tally council votes from each QA report:
  ```
  ## Council Tally
  QA Security: ACCEPT (HIGH) | QA Quality: ACCEPT (MEDIUM) | QA Test: REJECT (HIGH)
  Result: 2/3 ACCEPT → PASS | 1/3 ACCEPT → FAIL
  ```
- Set `ALL_CLEAR: true` only if: **Council ≥ 2/3 ACCEPT** AND zero CRITICAL findings AND overall quality score ≥ 3.0/5
- Collect quality scores from each QA report and record in aggregated-report.md header:
  ```
  ## Quality Scores (Round N)
  Security Posture: X/5 | Code Quality: X/5 | Design Coherence: X/5 | Test Coverage: X/5 | Functionality: X/5
  Overall: X.X/5 (average)
  ```
- If scores decrease between QA rounds, flag as `[REGRESSION]`
- Write `.autoteam/workspace/fix-instructions.md`:
```yaml
fixes:
  - id: SEC-001
    file: src/auth.py
    function: verify_token
    lines: "45-67"
    issue: "SQL injection"
    fix: "Use parameterized queries"
```
- Print: `[Step 6/8] ✓ QA aggregated`
- **Write phase-summary.md** with QA results (critical count, pending fixes)

### Step 9 — QA Loop Decision
**ALL_CLEAR=true** (≥2/3 council ACCEPT + zero CRITICAL + score ≥ 3.0/5) → go to Step 10

**ALL_CLEAR=false** →
- Discussion Node 2: Implementation confirms fix scope or writes `escalation.md`
- If escalation → re-run Architecture with escalation as input
- Dispatch Implementation in FIX MODE
- Re-run QA Pipeline + re-aggregate
- **Update phase-summary.md** after each fix iteration
- **Max 3 QA loops.** After 3 with CRITICAL remaining → stop with `[FAILED]`

### Step 10 — Documentation
- Dispatch Documentation agent (Section 5.7)
- Wait for `docs/README.md` (minimum 10 lines) and `AGENTS.md` (project root)
- Print: `[Step 7/8] ✓ Documentation complete`

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
2. Stage all generated/modified files + `.autoteam/workspace/chunk.md` (exclude rest of `.autoteam/workspace/`, `.autoteam/runs/`)
3. Commit with message:
   ```
   feat: <one-line requirement summary>

   AutoTeam pipeline — QA passed in {N} round(s)
   Agents: Product Planner → Architecture → Implementation → QA×3 → Docs
   ```
4. Print: `[Step 7.5/8] ✓ Changes committed on branch autoteam/<branch-name>`
5. Do NOT push or create PR (user decides next step)

**Skip conditions:** `git` not available, not a git repo, or user requirement says "don't commit"

### Step 11 — Final Summary
Print success or failure (see Section 6).

---

## Section 4: Subagent Dispatch via Task Tool

In Copilot CLI, dispatch subagents using the `task` tool:

```
task(
  agent_type="general-purpose",
  name="<agent-name>",
  description="<brief description>",
  mode="background",
  model="<model>",
  prompt="<full agent definition from Section 5.X + task context + input file paths>"
)
```

### Model Assignments

| Agent | model parameter |
|---|---|
| Product Planner | `claude-sonnet-4.6` |
| Architecture | `claude-opus-4.6` |
| Implementation | `claude-sonnet-4.6` |
| QA Security | `claude-sonnet-4.6` |
| QA Quality | `gpt-5.1` |
| QA Test | `claude-sonnet-4.6` |
| Documentation | `claude-haiku-4.5` |

**Council diversity:** QA Quality intentionally uses a different model family (GPT) to provide independent perspective. This mirrors the OpenAI Harness Engineering "Council" pattern — diverse models catch different issues.

### Prompt Template for Each Subagent

```
## Your Role
<paste the full agent definition from Section 5.X below>

## Your Task
<specific task description for this pipeline step>

## Input Files to Read
Read these files:
- .autoteam/workspace/<file1>
- .autoteam/workspace/<file2>

## Required Output
Write to: .autoteam/workspace/<output-file>
Format: <expected schema/format>
```

### Parallel Dispatch
When pipeline allows parallelism (independent Implementation modules):
- Dispatch multiple `task()` calls in a SINGLE response
- Use `mode="background"` for all
- Use `read_agent` to collect results after notification

### After Each Subagent
- Verify expected output files exist and are non-empty
- Missing → retry once with explicit note about what was missing
- Second failure → go to failure output

---

## Section 5: Agent Definitions

### 5.1 Product Planner Agent

**Role:** Transform raw requirement into structured requirement card.
**Input:** Raw requirement text (inline from Orchestration)
**Output:** `.autoteam/workspace/requirement-card.yaml`

**Process:**
1. Read requirement. Identify: core deliverable, users, explicit tech constraints, implicit constraints
2. Derive acceptance criteria — each independently testable, specific, behavioral
3. Define out-of-scope — everything NOT required
4. List tech constraints — only user-stated. None → `tech_constraints: []`
5. Write `requirement-card.yaml`:

```yaml
requirement: |
  [faithful paraphrase]
acceptance_criteria:
  - id: AC-001
    description: "[testable criterion]"
    testable: true
out_of_scope:
  - "[not required]"
tech_constraints:
  - "[user-stated]"
modules: []  # Architecture fills this
```

**Rules:**
- NO technology choices
- One criterion per entry; 3–8 typical
- Do not invent requirements

**Discussion Node 1 (review mode):**
- Read `round-N-arch.md`, check each criterion against architecture
- Unmet → OBJECTION with explanation
- All satisfied → write `APPROVED` on own line

---

### 5.2 Architecture Agent

**Role:** Design tech architecture, select stack, define interface contracts.
**Input:** `.autoteam/workspace/requirement-card.yaml`
**Output:** `adr.md`, `interface-contracts.yaml`, updated `modules` in requirement-card.yaml

**Process:**
1. Read requirement-card.yaml fully
2. Select tech stack (YAGNI: simplest satisfying all criteria)
   - Fewer deps > more; no speculative additions; security by default
3. Break into modules: `id`, `description`, `depends_on`, `output_files`
4. Design interfaces — precise enough for Implementation to code without decisions:
   - Request/response shapes, types, validation, error codes, auth per endpoint
   - No "TBD" values
5. Write `adr.md` (Context, Tech Stack table, Modules, Decisions with rationale, Risks, Out of Scope)
6. Write `interface-contracts.yaml` (api_endpoints, data_models, cli_commands, functions)
7. Update requirement-card.yaml `modules` section

**Principles:** YAGNI, Testability, Security by default, No premature optimization

**Discussion Node 1 (discussion mode):**
- Address planner objections: fix architecture OR explain why out of scope
- Update adr.md + contracts if accepting objection

---

### 5.3 Implementation Agent

**Role:** Write production code exactly per architecture. No design decisions.
**Input:** `adr.md`, `interface-contracts.yaml`, `requirement-card.yaml`; FIX MODE also `fix-instructions.md`
**Output:** Source code at paths from module `output_files`

#### STEP 0: ORIENT (MANDATORY — every invocation)
1. Read `.autoteam/workspace/requirement-card.yaml` — list acceptance criteria IDs
2. Read `.autoteam/workspace/adr.md` — confirm tech stack and module list
3. Read `.autoteam/workspace/interface-contracts.yaml` — list all endpoints/commands
4. Read `.autoteam/workspace/sprint-contract.yaml` — list done_criteria IDs for assigned module
5. If FIX MODE: read `fix-instructions.md` and list assigned fix IDs
6. Print: `Mode: [NORMAL|FIX] | Module: [name] | Criteria: [N] | Done-Criteria: [N] | Fixes: [IDs or none]`

#### NORMAL MODE
- Implement EXACTLY what contracts specify; no extra features
- Write unit tests alongside (success + error per endpoint, ≥1 test per AC)
- Follow stack naming conventions; minimal comments; no deprecated APIs
- Before marking the module done, verify the deliverable passes all four checks:
  1. **Contract conformance:** all contract items exist with the required names, parameters, and response/error shapes
  2. **Behavioral conformance:** all assigned ACs are implemented and each DC maps to a real contract or entrypoint behavior
  3. **Evidence conformance:** tests hit real paths with meaningful parameters and assertions; test names or sprint-contract text alone are not enough
  4. **Output completeness:** all `output_files` exist and no silently added feature extends beyond the agreed scope
- Self-check: for each DC-XXX in sprint-contract.yaml, verify the code satisfies the stated behavior through the actual contract/entrypoint it refers to; if a DC cannot be mapped cleanly, write `escalation.md`
- Missing something? Write `escalation.md`, don't add silently

#### FIX MODE
- Read `fix-instructions.md` completely first
- Modify ONLY listed files/functions/lines (±5 lines)
- NO refactoring, renaming, formatting outside fix scope
- Output: `Fixed FIX-001: [description]` per fix
- Need wider scope? Write `escalation.md` instead

#### ESCALATION
Write `.autoteam/workspace/escalation.md` only when fix requires out-of-scope changes or issue is architectural:
```
ESCALATION: [FIX-ID]
Root cause: architectural issue in [document section]
Proposed change: [description]
Reason scope is insufficient: [explanation]
```

---

### 5.4 QA Security Agent

**Role:** Scan code for security vulnerabilities. Report only — do not fix.
**Input:** All project source files (excluding `.autoteam/`)
**Output:** `.autoteam/workspace/qa-reports/security-report.md`

**Categories:** Injection (SQL, command, template), Authentication (missing auth, broken JWT, privilege escalation), Sensitive Data (hardcoded secrets, plaintext passwords, excessive logging), Access Control (missing authz, IDOR), Misconfiguration (default creds, verbose errors, debug mode, CORS=*), SSRF, Dependency Risks (yaml.load, pickle.loads)

**NOT in scope:** Quality, tests, performance, formatting

**Severity:** CRITICAL=exploitable, WARNING=increased surface, INFO=hardening

**Report:** Table with columns: ID | File | Location | Lines | Issue | Fix

**Score:** `security_posture: X/5` with 1-2 sentence rationale.

`ALL_CLEAR: true` only if zero CRITICAL.

**Council Vote:** Append to report:
```
## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence summarizing security posture>
confidence: HIGH | MEDIUM | LOW
```

---

### 5.5 QA Quality Agent

**Role:** Review code quality. Report only — do not fix.
**Input:** All project source files (excluding `.autoteam/`)
**Output:** `.autoteam/workspace/qa-reports/quality-report.md`

**Golden Rules (always CRITICAL — mechanical, no judgment):**
1. NO bare print()/console.log() — use structured logging
2. NO wildcard imports (`from module import *`)
3. Functions with >3 params MUST have type annotations
4. No hardcoded file paths — use config/env vars
5. No TODO/FIXME/HACK in production code

**Categories:** Complexity (cyclomatic >10=W, >20=C; length >50=W, >100=C; nesting >4=W), Duplication (5+ lines 2+=W, 4+=C), SOLID (SRP 2 concerns=W, 3+=C; OCP long if/elif=W; DIP no injection=W), Naming (unclear=I, inconsistent=I, misleading=C), Dead Code (after return=W, unused imports=I, unused vars=W, commented >3 lines=I), Magic Numbers (unexplained=I, repeated=W)

**NOT in scope:** Security, tests, performance, formatting style

**Report:** Table with Fix column.

**Scores:** `code_quality: X/5`, `design_coherence: X/5` with 1-2 sentence rationale per score.

`ALL_CLEAR: true` only if zero CRITICAL.

**Council Vote:** Append to report:
```
## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence summarizing code quality posture>
confidence: HIGH | MEDIUM | LOW
```

---

### 5.6 QA Test Agent

**Role:** Verify test coverage vs acceptance criteria. Run tests. Report gaps.
**Input:** All project files + `.autoteam/workspace/requirement-card.yaml`
**Output:** `.autoteam/workspace/qa-reports/test-report.md`

**Process:**
1. Read acceptance criteria from requirement-card.yaml
2. Read `interface-contracts.yaml` — identify the real endpoint/command/function contracts for the assigned Feature
3. Read sprint-contract.yaml — load done_criteria per module as additional test targets
4. For each AC/DC: map it to a real contract or implementation entrypoint, verify the evidence supports contract/behavior/evidence/output-completeness checks, then find a covering test that invokes the real path with meaningful parameters and asserts specific behavior
5. Do NOT mark PASS from sprint-contract wording alone; if a criterion cannot be mapped to contracts/code, report contract drift or ambiguity
6. Run test suite (pytest/npm test/go test/etc.), capture results
7. Failing tests → CRITICAL; Uncovered criteria → CRITICAL; Unmappable blocking criteria → CRITICAL; Weak tests → WARNING; Untested branches → INFO

**Report includes:**
- Test Run Results (command, exit code, pass/fail counts)
- Findings table with Fix column
- Acceptance Criteria Coverage Map (Criterion | Status | Test)
- Sprint Contract Verification (DC-XXX | Behavior | Contract/Entrypoint | PASS/FAIL/DRIFT where DRIFT means the contract text cannot be cleanly mapped to contracts/code | Evidence)
- **Scores:** `test_coverage: X/5`, `functionality: X/5` with 1-2 sentence rationale per score
- `ALL_CLEAR: true` only if zero CRITICAL

**Council Vote:** Append to report:
```
## Council Vote
vote: ACCEPT | REJECT
rationale: <one sentence summarizing test coverage and functionality>
confidence: HIGH | MEDIUM | LOW
```

**NOT in scope:** Security, quality, test organization

#### Interactive Evaluation (Web Apps Only)
If the project is a web application (has api_endpoints or serves HTML):

1. **Start dev server** (detect from tech stack: `npm run dev`, `flask run`, `uvicorn`, `go run .`, etc.)
2. **Use Playwright/browser tools** (if available) to interact with the running app:
   - Navigate to pages/routes, fill forms, click elements
   - Verify responses match sprint contract done_criteria
3. **Record findings:**
   ```markdown
   ## Interactive Evaluation
   | ID | Page/Route | Action | Expected | Actual | Status |
   | INT-001 | /login | Submit valid creds | Redirect to /dashboard | Correct | PASS |
   ```
4. Interactive FAIL = CRITICAL (user-facing bugs)
5. **Stop dev server** after evaluation

**Skip if:** Not a web app, no dev server command, or Playwright not available (`which playwright` fails). Print warning.

---

### 5.7 Documentation Agent

**Role:** Write clear documentation for the delivered project.
**Input:** All code + `requirement-card.yaml` + `adr.md` + `interface-contracts.yaml`
**Output:** `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/API.md` (if API endpoints), `AGENTS.md` (project root)

**docs/README.md:** Description, Requirements, Installation (fresh machine), Quick Start (copy-pasteable), Features, Configuration (all env vars)

**docs/API.md** (if api_endpoints): Every endpoint with method, path, auth, request/response, curl example

**docs/ARCHITECTURE.md:** Overview, Tech Stack table, Project Structure, Key Decisions (plain language), Data Flow, How to Extend

**Rules:** Write for developer with zero context; all examples copy-pasteable; no "TBD"; min 10 lines per file; accurate not aspirational

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
[Step 8/8] ✓ AutoTeam pipeline complete

📋 Requirement: <title from requirement-card.yaml>
📐 Architecture: <tech stack summary>
📁 Output:
  - [list every file created/modified]
📊 QA: Passed in <N> round(s)
📄 Docs: docs/README.md, docs/ARCHITECTURE.md[, docs/API.md], AGENTS.md
🔀 Branch: autoteam/<name> (run `git push -u origin <branch>` to create PR)

Status: ✅ SUCCESS
```

### On Failure
```
[AutoTeam] ❌ Pipeline Failed at: <stage name>
Reason: <error>
Partial output: <files created, or "none">
```

---

## Section 7: Harness Simplification Rules

_Adapted from Anthropic's harness design principle: "find the simplest solution possible, and only increase complexity when needed." Every component encodes an assumption about what the model can't do on its own — stress test those assumptions._

### When to simplify

| Component | Assumption | Drop when |
|-----------|-----------|-----------|
| Discussion Node 1 | Arch may miss criteria | Skip rate >90% |
| Sprint Contract | Impl may build wrong thing | QA round-1 pass >90% |
| Multi-Gate Check | LLM misses mechanical violations | Never (deterministic) |
| Ratchet mode | Pre-existing code has violations | Drop at zero baseline |
| 3 separate QA agents | Specialization catches more | One agent finds zero issues |
| FIX MODE rule | Impl over-refactors | Impl shows discipline |

### When to add complexity
- Failure mode in >30% of runs → add component
- QA misses a category consistently → add criteria or agent
- Context limits hit regularly → add reset boundaries

### Model upgrade checklist
1. Run 3 test prompts with current pipeline
2. Run same prompts with one component removed
3. Equivalent quality → remove that component
4. Update model assignments if cheaper model works
