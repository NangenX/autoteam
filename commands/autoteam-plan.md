# /autoteam-plan Command

Trigger the Human-AI Brainstorming phase to generate an approved `plan.md`.

## Usage

```
/autoteam-plan "your requirement"
```

## What Happens

1. **Human-AI Brainstorming** — Orchestration asks clarifying questions about your requirement
2. **Plan Generation** — Orchestration drafts `plan.md` based on your answers
3. **Human Approval** — You review and approve (or request changes to) the plan
4. **Loop** — Until you approve, Orchestration refines the plan based on your feedback

## Output

- `.autoteam/workspace/plan.md` (with `APPROVED: true`)

## What Does plan.md Contain

- **Goals** — High-level objectives confirmed by you
- **Scope** — What's in and out
- **Success Criteria** — Human-readable, verifiable outcomes
- **Risks & Open Questions** — Things to watch or resolve later
- **Verification** — How to prove the goal was achieved

## Subsequent Commands

After approval, run:
```
/autoteam "same requirement"
```
The pipeline will use your approved `plan.md` and skip the brainstorming step.

## When to Use

- **Complex projects** — When you're unsure about scope or priorities
- **Stakeholder alignment** — When multiple people need to agree on what to build
- **Large changes** — When the impact is significant and needs careful planning
- **Greenfield projects** — When starting from scratch with undefined requirements

## Skip Brainstorming

If `plan.md` already exists and is approved, `/autoteam` will automatically skip brainstorming.
