# AutoTeam Session Initialization Script (PowerShell)
# Creates the .autoteam/workspace/ directory structure

$WorkspaceDir = ".autoteam/workspace"
$RunsDir = ".autoteam/runs"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

# Check if workspace exists and has content
if (Test-Path $WorkspaceDir) {
    $hasContent = Get-ChildItem $WorkspaceDir -File | Where-Object { $_.Name -match '\.(yaml|md)$' -and $_.Name -notmatch '^#TEMPLATE' }
    if ($hasContent) {
        # Archive existing workspace
        $ArchiveDir = "$RunsDir/$Timestamp"
        New-Item -ItemType Directory -Force -Path $ArchiveDir | Out-Null
        Copy-Item -Path "$WorkspaceDir/*" -Destination "$ArchiveDir/" -Recurse -ErrorAction SilentlyContinue
        Write-Host "[Archive] Previous run archived -> $ArchiveDir/"
    }
}

# Create directory structure
New-Item -ItemType Directory -Force -Path "$WorkspaceDir/qa-reports" | Out-Null
New-Item -ItemType Directory -Force -Path "$WorkspaceDir/discussion" | Out-Null

# Clean up old workspace files recursively (except templates)
Get-ChildItem $WorkspaceDir -Recurse -File | Where-Object {
    $_.Name -match '\.(yaml|md)$' -and $_.Name -notmatch '^#TEMPLATE'
} | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "[AutoTeam] Session initialized"
Write-Host "  Workspace: $WorkspaceDir/"
Write-Host "  QA Reports: $WorkspaceDir/qa-reports/"
Write-Host "  Discussion: $WorkspaceDir/discussion/"
