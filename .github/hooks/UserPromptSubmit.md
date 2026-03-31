# AutoTeam Copilot CLI Hook — User Prompt Submit

After every user prompt in Copilot CLI, check if AutoTeam pipeline is active.

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

Do nothing — normal Copilot CLI behavior.
