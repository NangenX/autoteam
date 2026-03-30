---
name: autoteam
description: "Autonomous AI development team. Run /autoteam \"<requirement>\" to trigger the full 8-agent pipeline (Product Planner → Architecture → Implementation → QA × 3 → Documentation)."
version: 2.0
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
| `.autoteam/workspace/escalation.md` | Implementation |

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

### Step 1 — Input Validation
Validate `<REQUIREMENT>`. If empty/whitespace/nonsensical: stop with `[ERROR] Invalid requirement`.

### Step 2 — Initialize Workspace
- If `.autoteam/workspace/` exists and contains `.yaml` or `.md` files:
  - Archive entire workspace to `.autoteam/runs/<YYYYMMDD-HHMMSS>/` (copy, not move)
  - Print: `[Archive] Previous run archived → .autoteam/runs/<timestamp>/`
- Create/ensure directories: `.autoteam/workspace/`, `.autoteam/workspace/qa-reports/`, `.autoteam/workspace/discussion/`
- Delete any existing `.yaml`, `.md` files in workspace (except templates starting with `# TEMPLATE`)
- Print: `[Step 0/8] ✓ Workspace initialized`

### Step 3 — Dispatch Product Planner
- Dispatch subagent with `<REQUIREMENT>` and the **Product Planner** definition (Section 5.1)
- Wait for `.autoteam/workspace/requirement-card.yaml`
- Retry once on failure. Second failure → stop with error
- Print: `[Step 1/8] ✓ Product Planner complete → requirement-card.yaml`

### Step 4 — Dispatch Architecture
- Dispatch subagent with the **Architecture** definition (Section 5.2)
- Wait for `.autoteam/workspace/adr.md` AND `.autoteam/workspace/interface-contracts.yaml`
- Retry up to 2 additional times on failure (3 total)
- Print: `[Step 2/8] ✓ Architecture complete → adr.md + interface-contracts.yaml`

### Step 5 — Discussion Node 1 (Architecture vs Product Planner)
- Read both `adr.md` and `requirement-card.yaml`
- If architecture doesn't address all acceptance_criteria → enter discussion (max 3 rounds)
- Each round: Architecture writes `round-N-arch.md`, Product Planner writes `round-N-planner.md`
- Exit when `APPROVED` appears, or after round 3 (Orchestration writes `consensus.md` with binding decision)
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

4. Implementation uses done_criteria as its implementation checklist
5. QA Test uses done_criteria as its evaluation checklist (in addition to acceptance criteria)

- Print: `[Step 3.5/8] ✓ Sprint contract agreed → sprint-contract.yaml`

**Skip conditions:** If only 1 module with ≤3 acceptance criteria, skip contract (too simple to need negotiation).

### Step 6 — Dispatch Implementation
- Read `modules` from `requirement-card.yaml`
- Modules with no `depends_on`: dispatch as **parallel** subagents
- Modules with `depends_on`: dispatch **serially** after dependencies complete
- Each uses the **Implementation** definition (Section 5.3) in NORMAL MODE
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
Dispatch three QA subagents **in sequence** (not parallel):
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
- Print: `[Step 6/8] ✓ QA aggregated → aggregated-report.md + fix-instructions.md`
- **Write phase-summary.md** with QA results (critical count, pending fixes)

### Step 9 — QA Loop Decision
**ALL_CLEAR=true** (≥2/3 council ACCEPT + zero CRITICAL + score ≥ 3.0/5) → go to Step 10

**ALL_CLEAR=false** →
- Discussion Node 2: Implementation confirms fix scope or writes `escalation.md`
- If escalation → re-run Architecture with escalation as input
- Dispatch Implementation in **FIX MODE** (Section 5.3)
- Re-run QA Pipeline (Step 7) + re-aggregate (Step 8)
- **Update phase-summary.md** after each fix iteration
- **Max 3 QA loops.** After 3 with CRITICAL remaining → stop with `[FAILED]`

### Step 10 — Documentation
- Dispatch **Documentation** subagent (Section 5.7)
- Wait for `docs/README.md` (minimum 10 lines)
- If <10 lines: retry once with model `sonnet`
- Print: `[Step 7/8] ✓ Documentation complete → docs/ written`

### Step 10.5 — Git Integration
After all code and docs are written:
1. Create branch: `autoteam/<YYYYMMDD>-<slug>` (slug = first 3 words of requirement, kebab-case)
2. Stage all generated/modified files (exclude `.autoteam/workspace/`, `.autoteam/runs/`)
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

**Role:** Transform raw requirement into structured requirement card.
**Input:** Raw requirement text (provided inline by Orchestration)
**Output:** `.autoteam/workspace/requirement-card.yaml`

**Process:**
1. Read requirement. Identify: core deliverable, users, explicit tech constraints, implicit constraints
2. Derive acceptance criteria — each must be independently testable, specific, behavioral (observable outcomes, not implementation details)
3. Define out-of-scope — everything NOT required (features, NFRs, deployment, CI/CD, frontend if API-only)
4. List tech constraints — only user-stated ones. If none: `tech_constraints: []`
5. Write `requirement-card.yaml`:

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
**Input:** `.autoteam/workspace/requirement-card.yaml`
**Output:** `.autoteam/workspace/adr.md`, `.autoteam/workspace/interface-contracts.yaml`, updated `modules` in requirement-card.yaml

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
**Input:** `adr.md`, `interface-contracts.yaml`, `requirement-card.yaml`; in FIX MODE also `fix-instructions.md`
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
- Self-check: for each DC-XXX in sprint-contract.yaml, verify the code satisfies the stated behavior
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
```(1=critical exploits, 5=defense in depth) with 1-2 sentence rationale.

---

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
**Input:** All project files + `.autoteam/workspace/requirement-card.yaml`
**Output:** `.autoteam/workspace/qa-reports/test-report.md`

**Process:**
1. Read acceptance criteria from requirement-card.yaml
2. Read sprint-contract.yaml — load done_criteria per module as additional test targets
3. For each criterion: search tests for a covering test that would fail if criterion violated
   - Covering = invokes code path AND asserts specific behavior (not just "no exception")
4. Run test suite via Bash (pytest, npm test, go test, etc.)
5. Capture: command, exit code, pass/fail counts, failure output
6. Failing tests → CRITICAL; Uncovered criteria → CRITICAL; Weak tests → WARNING; Untested branches → INFO

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
| Criterion | Behavior | Status | Evidence |
| DC-001 | POST /auth/login returns 200 + JWT | PASS/FAIL | test_login_success |

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
**Input:** All project code + `requirement-card.yaml` + `adr.md` + `interface-contracts.yaml`
**Output:** `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/API.md` (if API endpoints exist)

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

---

## Section 6: Final Output

### On Success
```
[Step 8/8] ✓ AutoTeam pipeline complete

📋 Requirement: <title from requirement-card.yaml>
📐 Architecture: <tech stack summary — one line>
📁 Output:
  - [list every file created or modified]
📊 QA: Passed in <N> round(s)
📄 Docs: docs/README.md, docs/ARCHITECTURE.md[, docs/API.md]
🔀 Branch: autoteam/<branch-name> (run `git push -u origin <branch>` to create PR)

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
|-----------|----------------------|--------------------------|
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
