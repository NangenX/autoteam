#!/bin/bash
# AutoTeam Pipeline Status Check Script

PHASE_SUMMARY=".autoteam/workspace/phase-summary.md"
PIPELINE_STATUS=".autoteam/workspace/pipeline-status.md"

if [ ! -f "$PHASE_SUMMARY" ]; then
    echo "No AutoTeam session active. Run /autoteam first."
    exit 1
fi

echo "=== AutoTeam Pipeline Status ==="
echo ""

# Read phase summary
if [ -f "$PHASE_SUMMARY" ]; then
    echo "--- Phase Summary ---"
    cat "$PHASE_SUMMARY"
    echo ""
fi

# Read pipeline status if exists
if [ -f "$PIPELINE_STATUS" ]; then
    echo "--- Pipeline Status ---"
    cat "$PIPELINE_STATUS"
    echo ""
fi

# Check for QA reports
if [ -d ".autoteam/workspace/qa-reports" ]; then
    echo "--- QA Reports Available ---"
    ls -la .autoteam/workspace/qa-reports/ 2>/dev/null || echo "No reports yet"
    echo ""
fi

# Check current phase from summary
if grep -q "phase:" "$PHASE_SUMMARY" 2>/dev/null; then
    PHASE=$(grep "phase:" "$PHASE_SUMMARY" | head -1 | sed 's/phase: *//')
    echo "Current Phase: $PHASE"
fi
