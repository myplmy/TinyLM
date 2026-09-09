<#
보고서 패키지의 파일 해시와 현재 원본 일치 여부만 읽는다.
복사/수정/삭제/이동, Python 실행, import, compile, 테스트, GPU 작업을 하지 않는다.
이 스크립트도 패키지 작성 중 실행하지 않았다.
#>
[CmdletBinding()]
param(
    [ValidateSet('ALL','A01','A02','A03','A04','A05','A06','A07','A08','A09','A10','A11','A12','A13','A14','A15')]
    [string]$Action = 'ALL',
    [string]$ProjectRoot = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ReportRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent (Split-Path -Parent $ReportRoot)
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$Manifest = Get-Content -LiteralPath (Join-Path $ReportRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Manifest.schema -ne 'tinylm.report-action-bundle.v1') { throw 'Unsupported manifest schema.' }
$Findings = [System.Collections.Generic.List[object]]::new()
$Failures = [System.Collections.Generic.List[string]]::new()

function Get-SafePath([string]$Base, [string]$Relative) {
    if ([System.IO.Path]::IsPathRooted($Relative)) { throw "Absolute path in manifest: $Relative" }
    $ResolvedBase = [System.IO.Path]::GetFullPath($Base).TrimEnd('\','/')
    $ResolvedPath = [System.IO.Path]::GetFullPath((Join-Path $ResolvedBase $Relative))
    if (-not $ResolvedPath.StartsWith($ResolvedBase + [System.IO.Path]::DirectorySeparatorChar,
                                     [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes declared root: $Relative"
    }
    return $ResolvedPath
}
function Test-RecordedHash([string]$Path, [string]$Expected, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $Failures.Add("MISSING: $Label")
        return
    }
    $Actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) { $Failures.Add("HASH_MISMATCH: $Label") }
}
$Selected = @($Manifest.files)
if ($Action -ne 'ALL') {
    $ActionEntry = $Manifest.actions.PSObject.Properties[$Action].Value
    $Selected = @($Manifest.files | Where-Object { $ActionEntry.payload_files -contains $_.path })
}
foreach ($Entry in $Selected) {
    Test-RecordedHash (Get-SafePath $ReportRoot ('ALL/replacement/' + $Entry.path)) $Entry.replacement_sha256 ('ALL/replacement/' + $Entry.path)
    $CopyActions = @($Entry.actions)
    if ($Action -ne 'ALL') { $CopyActions = @($Action) }
    foreach ($CopyAction in $CopyActions) {
        Test-RecordedHash (Get-SafePath $ReportRoot ($CopyAction + '/replacement/' + $Entry.path)) $Entry.replacement_sha256 ($CopyAction + '/replacement/' + $Entry.path)
    }
    if ($Entry.original_exists) {
        Test-RecordedHash (Get-SafePath $ReportRoot ('ALL/original/' + $Entry.path)) $Entry.original_sha256 ('ALL/original/' + $Entry.path)
        foreach ($CopyAction in $CopyActions) {
            Test-RecordedHash (Get-SafePath $ReportRoot ($CopyAction + '/original/' + $Entry.path)) $Entry.original_sha256 ($CopyAction + '/original/' + $Entry.path)
        }
    }
    $CurrentPath = Get-SafePath $ProjectRoot $Entry.path
    if (Test-Path -LiteralPath $CurrentPath -PathType Leaf) {
        $CurrentHash = (Get-FileHash -LiteralPath $CurrentPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($CurrentHash -eq $Entry.replacement_sha256) {
            $State = 'ALREADY_APPLIED'
        } elseif ($Entry.original_exists -and $CurrentHash -eq $Entry.original_sha256) {
            $State = 'BASELINE_MATCH'
        } else {
            $State = 'CONCURRENT_CHANGE_OR_COLLISION'
            $Failures.Add("REVIEW_CURRENT_SOURCE: $($Entry.path)")
        }
    } elseif (Test-Path -LiteralPath $CurrentPath) {
        $State = 'DIRECTORY_COLLISION'
        $Failures.Add("DIRECTORY_COLLISION: $($Entry.path)")
    } elseif ($Entry.original_exists) {
        $State = 'ORIGINAL_MISSING'
        $Failures.Add("ORIGINAL_MISSING: $($Entry.path)")
    } else {
        $State = 'NEW_PATH_AVAILABLE'
    }
    $Findings.Add([pscustomobject]@{Path=$Entry.path; State=$State})
}
foreach ($Dependency in $Manifest.baseline_dependencies) {
    Test-RecordedHash (Get-SafePath $ProjectRoot $Dependency.path) $Dependency.sha256 ('dependency/' + $Dependency.path)
}
foreach ($Report in $Manifest.protected_reports) {
    Test-RecordedHash (Get-SafePath $ReportRoot $Report.path) $Report.sha256 ('report/' + $Report.path)
}
$Findings | Format-Table -AutoSize
if ($Failures.Count -gt 0) {
    $Failures | ForEach-Object { Write-Output $_ }
    Write-Output 'File review required. This checker changed no file and ran no Python.'
    exit 2
}
Write-Output ("File hashes match for {0} selected payload paths. Runtime status: NOT_EXECUTED." -f $Selected.Count)
exit 0
