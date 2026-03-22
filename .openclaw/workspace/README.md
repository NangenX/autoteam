# Workspace File Protocol

This directory is the **shared communication space** between all agents in the AutoTeam pipeline. Agents read and write files here to coordinate work across pipeline stages.

---

## Purpose

Each file in this workspace serves as a structured handoff artifact between agents. An agent reads the outputs of upstream agents, performs its work, and writes its own output file for downstream agents to consume.

---

## File Ownership Rules

Each file is owned by exactly one agent. Only the owning agent may write to that file.

| File | Owner |
|------|-------|
| `README.md` | Orchestration (protocol doc, never overwritten during pipeline runs) |
| `requirement-card.yaml` | Product Planner |
| `adr.md` | Architecture Agent |
| `interface-contracts.yaml` | Architecture Agent |
| `fix-instructions.md` | QA Aggregator |
| `qa-reports/aggregated-report.md` | QA Aggregator |

**Never modify a file you do not own.** Agents may read any file freely, but writes outside of owned files are strictly prohibited. Violating this rule corrupts pipeline state.

---

## Workspace Lifecycle

- Each pipeline run **clears this workspace** at the start, resetting all non-template files to their template state.
- Template files are preserved across runs and serve as the canonical schema for each artifact.
- Template files are identified by the `# TEMPLATE` comment at the top of each file.

---

## Template Files

Templates define the schema each agent must conform to when writing its output. Agents must not alter the schema — only fill in the values.

Templates are never cleared between runs. If a template file is missing, the pipeline will not start.

---

## General Rules

1. Do not create new files in this directory unless explicitly authorized by the Orchestrator.
2. Do not delete files during a pipeline run.
3. Write atomically — do not leave a file in a partial state.
4. All timestamps must be in ISO 8601 format (e.g., `2026-03-22T14:00:00Z`).
