[CmdletBinding()]
param(
    [string[]]$Path,
    [switch]$Add
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) {
    throw 'Not a git repository.'
}

$configPath = Join-Path $repoRoot '.agents/project.json'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Missing project metadata: $configPath"
}

$project = Get-Content -LiteralPath $configPath -Raw -Encoding utf8 | ConvertFrom-Json
$excluded = @($project.excludedPaths)

function Normalize-RepoPath {
    param([Parameter(Mandatory = $true)][string]$Value)
    return (($Value -replace '\\', '/') -replace '^\./', '').TrimEnd('/')
}

function Test-Excluded {
    param([Parameter(Mandatory = $true)][string]$Value)
    $candidate = Normalize-RepoPath $Value
    foreach ($rawPattern in $excluded) {
        $pattern = Normalize-RepoPath ([string]$rawPattern)
        if ($pattern.Contains('*') -and $candidate -like $pattern) {
            return $true
        }
        if ($candidate -eq $pattern -or $candidate.StartsWith(
            "$pattern/", [StringComparison]::OrdinalIgnoreCase
        )) {
            return $true
        }
    }
    return $false
}

if (-not $Path -or $Path.Count -eq 0) {
    git status --short
    if ($Add) {
        throw 'Staging requires one or more explicit -Path values.'
    }
    exit 0
}

$included = [Collections.Generic.List[string]]::new()
$blocked = [Collections.Generic.List[string]]::new()
foreach ($item in $Path) {
    if (Test-Excluded $item) {
        $blocked.Add($item)
    } else {
        $included.Add($item)
    }
}

foreach ($item in $blocked) {
    [Console]::Error.WriteLine("BLOCKED excluded path: $item")
}
foreach ($item in $included) {
    Write-Output "ALLOW $item"
}

if ($blocked.Count -gt 0) {
    exit 2
}
if ($included.Count -eq 0) {
    throw 'No explicit paths remain to stage.'
}
if ($Add) {
    $pathsToAdd = @($included)
    git add -- $pathsToAdd
    if ($LASTEXITCODE -ne 0) {
        throw 'git add failed.'
    }
}
