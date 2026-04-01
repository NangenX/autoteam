# Pipeline Review Todo List

Generated from pipeline review on 2026-04-01.

## CRITICAL Issues

### [ ] Issue 1: Step numbering denominator wrong (14 steps but /11)
- **Location:** Lines 114-129 vs all print statements
- **Problem:** Pipeline step reference defines 14 steps (0, 1, 2, 2.5, 3, 4, 5, 5.5, 6, 6.5, 7, 8, 9, 10, 10.5, 11) but all print statements use `[Step X/11]`
- **Fix:** Change denominator to 14, or reconsider the numbering scheme

### [ ] Issue 2: Step 2.5 prints as [Step 0.5/8]
- **Location:** Lines 249, 261
- **Problem:** Code Summarization section is "Step 2.5" but prints `[Step 0.5/8]`
- **Fix:** Change to `[Step 2.5/11]` (or /14)

### [ ] Issue 3: Working tree dirty logic uses AND instead of OR
- **Location:** Line 248
- **Problem:** `last_commit_hash == current_commit_hash AND working_tree_clean` skips regeneration even when tree is dirty
- **Fix:** Change to `last_commit_hash != current_commit_hash OR working_tree_dirty` triggers regeneration

### [ ] Issue 4: gh pr create --body syntax invalid
- **Location:** Line 484
- **Problem:** `gh pr create --body "..."` is invalid syntax
- **Fix:** Use `--body-text` instead of `--body`, or use heredoc

### [ ] Issue 5: Missing flow after Architecture re-run
- **Location:** Lines 430-432
- **Problem:** "If escalation → re-run Architecture" doesn't specify next step
- **Fix:** Explicitly state: after Architecture re-run → Implementation FIX MODE → Step 7

### [ ] Issue 6: Discussion Node 2 referenced but not defined
- **Location:** Line 429
- **Problem:** Step 9 mentions "Discussion Node 2" but only Discussion Node 1 exists
- **Fix:** Rename to "Implementation escalation review" or define Discussion Node 2

### [ ] Issue 7: Multiple output files missing from ownership table
- **Location:** Section 2
- **Problem:** docs/ARCHITECTURE.md, docs/AGENTS.md, docs/API.md, docs/README.md not listed
- **Fix:** Add Documentation Agent as owner for all docs/ files

### [ ] Issue 8: round-N-*.md ownership wrong
- **Location:** Line 64
- **Problem:** Ownership says Orchestration, but Architecture writes round-N-arch.md and Product Planner writes round-N-planner.md
- **Fix:** Change to: round-N-arch.md → Architecture; round-N-planner.md → Product Planner

### [ ] Issue 9: Sprint Contract skip condition malformed
- **Location:** Line 317
- **Problem:** "If only 1 module with ≤3 acceptance criteria" is syntactically broken
- **Fix:** Rewrite as clear boolean: `Skip if: module_count == 1 AND total_acceptance_criteria <= 3`

## MODERATE Issues

### [ ] Issue 10: Discussion Node skip prints success
- **Location:** Lines 280-281
- **Problem:** When Discussion is skipped, still prints `[Step 5/11] ✓ Architecture-Planner alignment verified`
- **Fix:** Print `[Step 5/11] Skip (no contradictions)` instead

### [ ] Issue 11: Step 0 skip message ambiguous
- **Location:** Lines 139-140
- **Problem:** Message shows "Step 0...skip" but then says "Skip to Step 1"
- **Fix:** Clarify: `[Step 0/11] ✓ Plan approved (skip brainstorming) → Step 1`

### [ ] Issue 14: Council 2/2 but Test Coverage score from QA Test
- **Location:** Lines 401-402
- **Problem:** Council is 2/2 (Security + Quality) but Quality Scores includes Test Coverage from QA Test
- **Fix:** Clarify that QA Test runs per-Feature (Step 6) and its coverage score feeds into Step 8 but doesn't vote in council

## MINOR Issues

### [ ] Issue 12: Step 2.5 missing from pipeline step reference
- **Location:** Lines 114-129
- **Fix:** Add Step 2.5 to the reference list

### [ ] Issue 13: Step 0.5 referenced but not defined
- **Location:** Lines 249, 261
- **Fix:** Remove Step 0.5 references, use Step 2.5 consistently

### [ ] Issue 15: Step 8 test coverage gap
- **Location:** Lines 394-411
- **Fix:** Add note: "Test coverage score sourced from per-Feature QA Test verification in Step 6"

### [ ] Issue 16: QA Quality missing sprint-contract input
- **Location:** Section 5.5
- **Fix:** Add `.autoteam/workspace/sprint-contract.yaml` to QA Quality input

### [ ] Issue 17: Inconsistent path prefixes
- **Location:** Line 276
- **Fix:** Add `.autoteam/workspace/` prefix to `adr.md` and `requirement-card.yaml`

### [ ] Issue 18: Step label inconsistency
- **Location:** Line 241 vs 115
- **Fix:** Consistent naming

### [ ] Issue 19: Documentation Agent doesn't own CODE-SUMMARY.md
- **Location:** Section 5.7
- **Fix:** Clarify Documentation Agent only reads (not owns) docs/CODE-SUMMARY.md
