Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "reviewer_start.sh"

if (-not (Test-Path -LiteralPath $scriptPath)) {
  throw "Could not find script at: $scriptPath"
}

$bashCandidates = @(
  "C:\Program Files\Git\bin\bash.exe",
  "C:\Program Files\Git\usr\bin\bash.exe"
)

$bashPath = $bashCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $bashPath) {
  throw "Git Bash was not found. Install Git for Windows or run scripts/reviewer_start.sh from another Bash environment."
}

Write-Host "Running reviewer bootstrap with: $bashPath"
Push-Location $rootDir
try {
  & $bashPath $scriptPath
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}
