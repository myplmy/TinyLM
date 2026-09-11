[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][string]$BodyFile,
    [string]$Base,
    [string]$Head,
    [switch]$Draft
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $BodyFile -PathType Leaf)) {
    throw "PR body file not found: $BodyFile"
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Base) {
    $Base = & (Join-Path $scriptRoot 'detect_base.ps1')
    if ($LASTEXITCODE -ne 0 -or -not $Base) {
        throw 'Base branch is ambiguous; ask the user and pass -Base.'
    }
}
if (-not $Head) {
    $Head = git branch --show-current
}
if (-not $Head) {
    throw 'Detached HEAD is not a valid PR head.'
}

$ghCommand = Get-Command gh -ErrorAction SilentlyContinue
$gh = if ($ghCommand) {
    $ghCommand.Source
} else {
    'C:\Program Files\GitHub CLI\gh.exe'
}
if (-not (Test-Path -LiteralPath $gh -PathType Leaf) -and $gh -ne 'gh') {
    throw 'gh CLI not found.'
}

$arguments = @(
    'pr', 'create',
    '--base', $Base,
    '--head', $Head,
    '--title', $Title,
    '--body-file', $BodyFile
)
if ($Draft) {
    $arguments += '--draft'
}

& $gh @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'gh pr create failed.'
}
