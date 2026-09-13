# TinyLM Codex Windows launcher for compact_state.py.
$ErrorActionPreference = "Stop"
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = $utf8NoBom
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom

try {
    $payload = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($payload)) {
        exit 0
    }
    $hookPath = Join-Path -Path $PSScriptRoot -ChildPath "compact_state.py"
    $hookOutput = $payload | & python -I -B $hookPath
    if ($LASTEXITCODE -ne 0) {
        throw "compact_state.py exited with code $LASTEXITCODE"
    }
    if ($null -ne $hookOutput) {
        [Console]::Out.WriteLine(($hookOutput -join [Environment]::NewLine))
    }
}
catch {
    $failure = @{
        continue = $false
        stopReason = "TinyLM compact state wrapper failed; compaction or continuation was stopped."
        systemMessage = "TinyLM compact state wrapper failed; inspect the hook before continuing."
    } | ConvertTo-Json -Compress
    [Console]::Out.WriteLine($failure)
}

exit 0
