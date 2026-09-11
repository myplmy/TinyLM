[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateRange(1, [int]::MaxValue)]
    [int]$PrNumber
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ghCommand = Get-Command gh -ErrorAction SilentlyContinue
$gh = if ($ghCommand) {
    $ghCommand.Source
} else {
    'C:\Program Files\GitHub CLI\gh.exe'
}
if (-not (Test-Path -LiteralPath $gh -PathType Leaf) -and $gh -ne 'gh') {
    throw 'gh CLI not found.'
}

$raw = & $gh pr view $PrNumber --json state,mergeStateStatus,baseRefName
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect PR $PrNumber."
}
$info = $raw | ConvertFrom-Json
if ($info.state -eq 'MERGED') {
    git fetch -q origin $info.baseRefName
    Write-Output "OK pr=$PrNumber already-merged synced base=$($info.baseRefName)"
    exit 0
}
if ($info.state -ne 'OPEN' -or $info.mergeStateStatus -ne 'CLEAN') {
    throw "PR is not merge-ready: state=$($info.state) merge=$($info.mergeStateStatus)"
}

& $gh pr merge $PrNumber --merge --delete-branch
if ($LASTEXITCODE -ne 0) {
    throw "Merge command failed for PR $PrNumber."
}

$state = & $gh pr view $PrNumber --json state --jq .state
if ($state -ne 'MERGED') {
    throw "Merge was not confirmed for PR $PrNumber."
}
git fetch -q origin $info.baseRefName
Write-Output "OK pr=$PrNumber merged synced base=$($info.baseRefName)"
