# AutoTeam Pipeline Status Check Script (PowerShell)

$PhaseSummary = ".autoteam/workspace/phase-summary.md"
$PipelineStatus = ".autoteam/workspace/pipeline-status.md"

if (-not (Test-Path $PhaseSummary) -and -not (Test-Path $PipelineStatus)) {
    Write-Host "No AutoTeam session active. Run /autoteam first."
    exit 1
}

Write-Host "=== AutoTeam Pipeline Status ==="
Write-Host ""

# Read phase summary
if (Test-Path $PhaseSummary) {
    Write-Host "--- Phase Summary ---"
    Get-Content $PhaseSummary
    Write-Host ""
}

# Read pipeline status if exists
if (Test-Path $PipelineStatus) {
    Write-Host "--- Pipeline Status ---"
    Get-Content $PipelineStatus
    Write-Host ""
}

# Check for QA reports
$qaDir = ".autoteam/workspace/qa-reports"
if (Test-Path $qaDir) {
    Write-Host "--- QA Reports Available ---"
    Get-ChildItem $qaDir -File | Select-Object Name
    Write-Host ""
}

# Check current phase from summary
if (Select-String -Path $PhaseSummary -Pattern "phase:" -Quiet) {
    $phase = Select-String -Path $PhaseSummary -Pattern "phase:" | Select-Object -First 1
    $phaseValue = $phase.Line -replace "phase:\s*", ""
    Write-Host "Current Phase: $phaseValue"
}
