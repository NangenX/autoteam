#!/bin/bash
# AutoTeam Session Initialization Script
# Creates the .autoteam/workspace/ directory structure

set -e

WORKSPACE_DIR=".autoteam/workspace"
RUNS_DIR=".autoteam/runs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Check if workspace exists and has content
if [ -d "$WORKSPACE_DIR" ] && [ "$(ls -A "$WORKSPACE_DIR" 2>/dev/null)" ]; then
    # Archive existing workspace
    ARCHIVE_DIR="$RUNS_DIR/$TIMESTAMP"
    mkdir -p "$ARCHIVE_DIR"
    cp -r "$WORKSPACE_DIR"/* "$ARCHIVE_DIR/" 2>/dev/null || true
    echo "[Archive] Previous run archived → $ARCHIVE_DIR/"
fi

# Create directory structure
mkdir -p "$WORKSPACE_DIR/qa-reports"
mkdir -p "$WORKSPACE_DIR/discussion"

# Clean up old workspace files (except templates)
find "$WORKSPACE_DIR" -maxdepth 1 -type f \( -name "*.yaml" -o -name "*.md" \) ! -name "#TEMPLATE*" -delete 2>/dev/null || true

echo "[AutoTeam] Session initialized"
echo "  Workspace: $WORKSPACE_DIR/"
echo "  QA Reports: $WORKSPACE_DIR/qa-reports/"
echo "  Discussion: $WORKSPACE_DIR/discussion/"
