# AutoTeam — Post-Tool Use Hook

After every Write or Edit operation, prompt to update pipeline status if phase changed.

## After Write tool (if pipeline is active)

If you modified a file in `.autoteam/workspace/`, check if the pipeline phase should be updated:

1. Did you create `requirement-card.yaml`? → Update phase to "Product Planner" complete
2. Did you create `adr.md` or `interface-contracts.yaml`? → Update phase to "Architecture" complete
3. Did you create files in `qa-reports/`? → Update phase to "QA Pipeline" or "Documentation"
4. Did you create `docs/README.md`? → Update phase to "Documentation" complete

If phase changed, prompt user:
```
[AutoTeam] Phase transition detected. Update .autoteam/workspace/pipeline-status.md?
```

## General

Always log significant actions to `.autoteam/workspace/pipeline-status.md` (update the Notes section):
- Tool used
- File affected
- Key outcome
