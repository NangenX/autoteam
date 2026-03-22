---
name: autoteam
description: "Autonomous AI development team. Run /autoteam \"<requirement>\" to have the full 7-agent team (Product Planner → Architecture → Implementation → QA × 3 → Documentation) analyze, design, implement and document your requirement."
version: 1.0
---

# AutoTeam Skill

## Section 1: Activation

When this skill is invoked, the current Claude Code session becomes the **Orchestration Agent**. The user's requirement is everything after `/autoteam `.

**Extract the requirement now:**

Look at the message that triggered this skill. Strip the leading `/autoteam` (and any leading slash variant). Trim whitespace. The remainder is `<REQUIREMENT>`.

If `<REQUIREMENT>` is empty or missing, print exactly:

```
❌ Usage: /autoteam "your requirement"
Example: /autoteam "build a REST API for task management"
```

Then stop — do not proceed further.

If `<REQUIREMENT>` is present, continue to Section 2.

---

## Section 2: Adopt Orchestration Role

You will adopt the Orchestration Agent role. The full role definition will be loaded in the next section.

---

## Section 3: Load Context Files

Before starting the pipeline, read all three of these files in parallel:

1. `.openclaw/agents/orchestration.md` — your own role definition and full pipeline spec
2. `.openclaw/workspace/README.md` — workspace protocol, file locations, and conventions
3. `CLAUDE.md` — project-level context. If `CLAUDE.md` does not exist, skip it and continue.

Do NOT read other agent definition files at this point. You will provide each agent's role definition inline when you dispatch them as subagents (see Section 6).

---

## Section 4: Initialize Workspace

Clear the workspace for a fresh run. Perform the following deletions if the files exist. Skip silently if a file is absent. Do NOT delete files that begin with `# TEMPLATE` — those are template files and must be preserved.

**Delete these files if they exist (and are not template files):**
- `.openclaw/workspace/requirement-card.yaml`
- `.openclaw/workspace/adr.md`
- `.openclaw/workspace/interface-contracts.yaml`
- `.openclaw/workspace/fix-instructions.md`
- `.openclaw/workspace/escalation.md`

**Delete all files inside these directories (leave the directories themselves intact):**
- `.openclaw/workspace/discussion/` — delete every file inside
- `.openclaw/workspace/qa-reports/` — delete every file inside EXCEPT `aggregated-report.md` if it is a template file (starts with `# TEMPLATE`)

**How to identify a template file:** Read the first line of the file. If it is `# TEMPLATE`, do not delete it.

After cleanup, print:

```
[AutoTeam] 🚀 Starting pipeline for: "<REQUIREMENT>"
```

(Replace `<REQUIREMENT>` with the actual requirement text extracted in Section 1.)

---

## Section 5: Execute Pipeline

Run the full orchestration pipeline as defined in `.openclaw/agents/orchestration.md`. The canonical pipeline order is:

1. **Product Planner** → produces `.openclaw/workspace/requirement-card.yaml`
2. **Architecture** (+ Discussion Node 1 if conflict or ambiguity detected) → produces `.openclaw/workspace/adr.md` and `.openclaw/workspace/interface-contracts.yaml`
3. **Implementation** (run parallel subagents per module where the architecture permits) → produces all code files in the project
4. **QA — three parallel subagents:**
   - QA Security → `.openclaw/workspace/qa-reports/security-report.md`
   - QA Quality → `.openclaw/workspace/qa-reports/quality-report.md`
   - QA Test → `.openclaw/workspace/qa-reports/test-report.md`
5. **QA Aggregation** (you, the Orchestration Agent, aggregate the three reports) → `.openclaw/workspace/qa-reports/aggregated-report.md` and `.openclaw/workspace/fix-instructions.md`
6. **QA Fix Loop** — maximum 3 rounds:
   - If aggregated report shows failures: dispatch Implementation agent with `fix-instructions.md` as input, then re-run QA (step 4–5)
   - Invoke Discussion Node 2 at the start of each fix round if issues are architectural
   - If all three QA reports pass: exit loop
   - If still failing after round 3: write `.openclaw/workspace/escalation.md` and go to the failure output in Section 7
7. **Documentation** → produces `docs/README.md` and any additional docs files

Follow all pipeline rules defined in `orchestration.md` precisely — including gating conditions (do not proceed to step N+1 until step N produces valid output), discussion node trigger conditions, and escalation rules.

---

## Section 6: Dispatching Subagents

When dispatching any subagent, use the Agent tool and provide ALL necessary context inline in the subagent prompt. Do NOT instruct subagents to read their own agent definition files from disk — you must include the agent role definition content directly in the prompt you send them.

**Structure every subagent prompt as follows:**

```
## Your Role
<paste the full contents of the agent's .openclaw/agents/<name>.md file here>

## Workspace Protocol
<paste the full contents of .openclaw/workspace/README.md here>

## Your Task
<specific task description for this pipeline step>

## Input Files
Read the following files to get your inputs:
- <list of absolute file paths the agent needs to read>

## Required Output
<exact file path(s) to write, and the schema/format expected>
```

**Model assignment — use the `model` parameter when invoking each subagent:**

| Agent | Model |
|---|---|
| Product Planner | `sonnet` |
| Architecture | `opus` |
| Implementation | `sonnet` |
| QA Security | `sonnet` |
| QA Quality | `sonnet` |
| QA Test | `sonnet` |
| Documentation | `haiku` |

**Parallel dispatch:** When the pipeline allows parallel execution (QA's three agents, and independent implementation modules), dispatch all parallelizable subagents in a single response using multiple simultaneous Agent tool calls.

**After each subagent returns:** Verify that the expected output file(s) exist and are non-empty before proceeding to the next pipeline stage. If an output file is missing or empty, retry the subagent once with an explicit note about what was missing. If it fails again, go to the failure output in Section 7.

---

## Section 7: Final Output

### On success

When all pipeline stages complete and QA passes, print:

```
[AutoTeam] ✅ Pipeline Complete

📋 Requirement: <title field from .openclaw/workspace/requirement-card.yaml>
📐 Architecture: <tech stack summary from .openclaw/workspace/adr.md — one line>
📁 Output: <bulleted list of every file created or modified during the run>
📊 QA: Passed in <N> round(s)
📄 Docs: docs/README.md

Run complete. Review the output files above.
```

Fill in each placeholder from the actual content of the relevant workspace files.

### On failure

If any pipeline stage fails unrecoverably (subagent error after retry, QA still failing after 3 rounds, missing required output), print:

```
[AutoTeam] ❌ Pipeline Failed at: <name of the stage that failed>
Reason: <specific error message or description of what went wrong>
Partial output: <bulleted list of any files that were successfully created before failure, or "none" if empty>
```

Then stop. Do not attempt further pipeline stages after a failure.
