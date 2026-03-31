# AutoTeam — User Prompt Submit Hook

After every user prompt, check if AutoTeam pipeline is active.

## If pipeline is active

Read `.autoteam/workspace/phase-summary.md` and display:

```
=== AutoTeam Pipeline ===
Phase: <current phase>
Requirement: <brief description>
QA Round: <N>
Critical Findings: <count>
Next Action: <what happens next>
```

## If no active pipeline

Do nothing — normal Claude Code behavior.
