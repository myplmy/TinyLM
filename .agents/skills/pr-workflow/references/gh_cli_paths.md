# gh CLI 경로 해결

TinyLM Codex의 기본 셸은 Windows PowerShell이다. `gh`를 찾았다는 사실과 인증되어
외부 변경을 수행할 권한은 서로 다르다.

## PowerShell 탐색 순서

```powershell
$GhCommand = Get-Command gh -ErrorAction SilentlyContinue
$Gh = if ($GhCommand) {
    $GhCommand.Source
} else {
    'C:\Program Files\GitHub CLI\gh.exe'
}
if (-not (Test-Path -LiteralPath $Gh -PathType Leaf) -and $Gh -ne 'gh') {
    throw 'gh CLI not found.'
}
```

Git Bash 경로는 사용자가 그 셸을 명시한 경우에만 참고한다. POSIX 스크립트의 존재는
Windows 호환성 증거가 아니다.

## 인증

```powershell
& $Gh auth status
```

인증이 없으면 `gh auth login`을 자동 시작하지 않는다. 대화형 로그인과 계정 선택은
사용자에게 위임하고 완료 뒤 알려 달라고 요청한다.

## 자주 쓰는 읽기 명령

| 작업 | 명령 |
|---|---|
| PR 목록 | `& $Gh pr list --state all --limit 10` |
| PR 상세 | `& $Gh pr view <N> --json state,mergeable,mergeStateStatus` |
| 이슈 목록 | `& $Gh issue list` |

PR 생성·편집·merge와 issue 변경은 읽기 명령과 별도 권한이다. base는
`detect_base.ps1`의 근거 또는 사용자의 명시값을 사용하고 하드코딩하지 않는다.
