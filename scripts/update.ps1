param(
    [Parameter(Position = 0)]
    [string]$Message = "Update project"
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Args)

    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Invoke-Git @("add", ".")

$status = & git status --porcelain
if (-not $status) {
    Write-Host "No changes to commit."
    exit 0
}

Invoke-Git @("commit", "-m", $Message)

$branch = (& git branch --show-current).Trim()
if (-not $branch) {
    throw "Could not determine the current branch."
}

Invoke-Git @("push", "-u", "origin", $branch)

Write-Host "Pushed $branch to origin successfully."
