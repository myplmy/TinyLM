[CmdletBinding()]
param(
    [string]$Base,
    [switch]$ShowCandidates
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Test-BranchRef {
    param([Parameter(Mandatory = $true)][string]$Name)
    git rev-parse --verify --quiet $Name 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

$repoRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) {
    throw 'Not a git repository.'
}

if ($Base) {
    if (-not (Test-BranchRef $Base) -and -not (Test-BranchRef "origin/$Base")) {
        throw "Explicit base branch does not resolve: $Base"
    }
    $Base
    exit 0
}

$configPath = Join-Path $repoRoot '.agents/project.json'
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    $project = Get-Content -LiteralPath $configPath -Raw -Encoding utf8 | ConvertFrom-Json
    $configured = [string]$project.baseBranch
    if ($configured) {
        if (-not (Test-BranchRef $configured) -and -not (Test-BranchRef "origin/$configured")) {
            throw "Configured base branch does not resolve: $configured"
        }
        $configured
        exit 0
    }
}

$candidates = [Collections.Generic.List[string]]::new()
$remoteHead = git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>$null
if ($LASTEXITCODE -eq 0 -and $remoteHead -match '^origin/(.+)$') {
    $candidates.Add($Matches[1])
}

foreach ($name in @('main', 'master', 'develop')) {
    if (Test-BranchRef "refs/heads/$name") {
        $candidates.Add($name)
    }
}

$unique = @($candidates | Sort-Object -Unique)
if ($unique.Count -eq 1) {
    $unique[0]
    exit 0
}

if ($ShowCandidates -or $unique.Count -gt 1) {
    foreach ($name in $unique) {
        $last = git log -1 --oneline $name 2>$null
        [Console]::Error.WriteLine("candidate=$name last=$last")
    }
}

[Console]::Error.WriteLine(
    'Base branch is ambiguous. Pass -Base after the user selects one.'
)
exit 2
