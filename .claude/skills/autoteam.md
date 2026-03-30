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

### Step 1 — Input Validation
Validate `<REQUIREMENT>`. If empty/whitespace/nonsensical: stop with `[ERROR] Invalid requirement`.

### Step 2 — Initialize Workspace
- Create `.autoteam/workspace/`, `.autoteam/workspace/qa-reports/`, `.autoteam/workspace/discussion/`
- Delete any existing `.yaml`, `.md` files (except templates starting with `# TEMPLATE`)
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

### Step 6 — Dispatch Implementation
- Read `modules` from `requirement-card.yaml`
- Modules with no `depends_on`: dispatch as **parallel** subagents
- Modules with `depends_on`: dispatch **serially** after dependencies complete
- Each uses the **Implementation** definition (Section 5.3) in NORMAL MODE
- Print: `[Step 4/8] ✓ Implementation complete → all modules written`

### Step 7 — QA Pipeline
Dispatch three QA subagents **in sequence** (not parallel):
1. **QA Security** (Section 5.4) → `security-report.md`
2. **QA Quality** (Section 5.5) → `quality-report.md`
3. **QA Test** (Section 5.6) → `test-report.md`
- Print: `[Step 5/8] ✓ QA Pipeline complete → 3 reports written`

### Step 8 — Aggregate QA Results
- Merge all three reports → `.autoteam/workspace/qa-reports/aggregated-report.md`
- Prefix IDs: SEC-, QUA-, TST-
- Set `ALL_CLEAR: true` only if zero CRITICAL findings
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

### Step 9 — QA Loop Decision
**ALL_CLEAR=true** → go to Step 10

**ALL_CLEAR=false** →
- Discussion Node 2: Implementation confirms fix scope or writes `escalation.md`
- If escalation → re-run Architecture with escalation as input
- Dispatch Implementation in **FIX MODE** (Section 5.3)
- Re-run QA Pipeline (Step 7) + re-aggregate (Step 8)
- **Max 3 QA loops.** After 3 with CRITICAL remaining → stop with `[FAILED]`

### Step 10 — Documentation
- Dispatch **Documentation** subagent (Section 5.7)
- Wait for `docs/README.md` (minimum 10 lines)
- If <10 lines: retry once with model `sonnet`
- Print: `[Step 7/8] ✓ Documentation complete → docs/ written`

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
4. If FIX MODE: read `fix-instructions.md` and list assigned fix IDs
5. Print: `Mode: [NORMAL|FIX] | Module: [name] | Criteria: [N] | Fixes: [IDs or none]`

#### NORMAL MODE (first implementation)
- Implement EXACTLY what interface-contracts specify — every endpoint, field, command, function
- Do NOT add features not in contracts; do NOT remove/rename listed items
- Write unit tests alongside each module (success + error paths per endpoint, each AC has ≥1 test)
- Follow tech stack naming conventions (Python: snake_case, JS: camelCase, Go: PascalCase exports)
- No comments restating what code does; comment only non-obvious logic
- No deprecated APIs; no error handling for impossible scenarios
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
```

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

---

### 5.6 QA Test Agent

**Role:** Verify test coverage maps to acceptance criteria. Run tests. Report gaps.
**Input:** All project files + `.autoteam/workspace/requirement-card.yaml`
**Output:** `.autoteam/workspace/qa-reports/test-report.md`

**Process:**
1. Read acceptance criteria from requirement-card.yaml
2. For each criterion: search tests for a covering test that would fail if criterion violated
   - Covering = invokes code path AND asserts specific behavior (not just "no exception")
3. Run test suite via Bash (pytest, npm test, go test, etc.)
4. Capture: command, exit code, pass/fail counts, failure output
5. Failing tests → CRITICAL; Uncovered criteria → CRITICAL; Weak tests → WARNING; Untested branches → INFO

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

## ALL_CLEAR: [true only if zero CRITICAL]
```

**NOT in scope:** Security, code quality, test organization

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

Status: ✅ SUCCESS
```

### On Failure
```
[AutoTeam] ❌ Pipeline Failed at: <stage name>
Reason: <specific error>
Partial output: <list of files created before failure, or "none">
```
Stop. Do not attempt further stages.
