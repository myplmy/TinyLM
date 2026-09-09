# A16 read-only package checker. User-run; never installs or executes Python.
param([string]$RepositoryRoot = 'Z:\TinyLM')
$ErrorActionPreference = 'Stop'
$packageRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$replacementRoot = [System.IO.Path]::GetFullPath((Join-Path $packageRoot 'replacement'))
$repositoryPath = [System.IO.Path]::GetFullPath($RepositoryRoot)
$manifest = Get-Content -LiteralPath (Join-Path $packageRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = New-Object 'System.Collections.Generic.List[string]'
function Resolve-ContainedPath([string]$Base, [string]$Relative) {
    $resolved = [System.IO.Path]::GetFullPath((Join-Path $Base $Relative))
    $prefix = $Base.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes declared root: $Relative"
    }
    return $resolved
}
foreach ($entry in $manifest.package_files) {
    $source = Resolve-ContainedPath $replacementRoot $entry.path
    $target = Resolve-ContainedPath $repositoryPath $entry.path
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        $failures.Add("Missing package file: $($entry.path)")
        continue
    }
    $actual = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $entry.sha256) { $failures.Add("Package hash mismatch: $($entry.path)") }
    if (Test-Path -LiteralPath $target) {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
            $failures.Add("Install path is not a file: $($entry.path)")
        } elseif ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
            $failures.Add("Different content already exists at new install path: $($entry.path)")
        }
    }
}
$expected = @($manifest.package_files | ForEach-Object { $_.path.Replace('/', '\') })
foreach ($file in (Get-ChildItem -LiteralPath $replacementRoot -Recurse -File)) {
    $relative = $file.FullName.Substring($replacementRoot.Length + 1)
    if ($relative -notin $expected) { $failures.Add("Unlisted package file: $relative") }
}
foreach ($entry in $manifest.source_files) {
    $source = Resolve-ContainedPath $repositoryPath $entry.path
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        $failures.Add("Missing audited original: $($entry.path)")
    } elseif ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        $failures.Add("Original changed since audit; review compatibility: $($entry.path)")
    }
}
if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Output $_ }
    exit 1
}
Write-Output "A16 package hashes and original baseline match. No Python/runtime/benchmark validation was performed."
exit 0
