# TinyLM Codex Windows launcher for guard_backslash.py.
# Keep hooks.json commandWindows free of embedded double quotes. Codex wraps the
# command with cmd.exe /C on Windows, and embedded quotes can prevent execution.

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

    $guardPath = Join-Path -Path $PSScriptRoot -ChildPath "guard_backslash.py"
    $guardOutput = $payload | & python -I -B $guardPath
    $guardExitCode = $LASTEXITCODE
    if ($guardExitCode -ne 0) {
        throw "guard_backslash.py exited with code $guardExitCode"
    }

    if ($null -ne $guardOutput) {
        [Console]::Out.WriteLine(($guardOutput -join [Environment]::NewLine))
    }
}
catch {
    $warning = @{
        systemMessage = "TinyLM Codex backslash guard wrapper failed; protection was skipped. Review the command manually."
    } | ConvertTo-Json -Compress
    [Console]::Out.WriteLine($warning)
}

exit 0
