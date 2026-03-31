# /autoteam:status Command

Show the current AutoTeam pipeline status.

## Usage

```
/autoteam:status
```

## What It Shows

- **Current phase** — Which pipeline step is active or last completed
- **Requirement** — The original requirement being worked on
- **QA Round** — Current QA iteration number
- **Critical Findings** — Number of unresolved CRITICAL issues
- **Pending Fixes** — List of fix IDs awaiting resolution

## Reading the Status

Check `.autoteam/workspace/phase-summary.md` for the full compressed state.

For detailed QA results, see:
- `.autoteam/workspace/qa-reports/aggregated-report.md` — Combined QA summary
- `.autoteam/workspace/qa-reports/security-report.md` — Security findings
- `.autoteam/workspace/qa-reports/quality-report.md` — Quality findings
- `.autoteam/workspace/qa-reports/test-report.md` — Test coverage
