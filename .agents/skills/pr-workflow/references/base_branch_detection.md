# PR base branch 결정

PR base는 현재 작업이 실제로 분기한 대상이어야 한다. `main`, `master`, `develop` 중
하나를 관행으로 추측하지 않는다. Head는 현재 branch이며 base와 다른 개념이다.

## Windows 기본 도구

```powershell
$Base = & .agents/skills/pr-workflow/scripts/detect_base.ps1 -ShowCandidates
if ($LASTEXITCODE -eq 2 -or -not $Base) {
    # 외부 변경 없이 멈추고 후보·최근 commit을 사용자에게 보여준다.
    return
}
$Head = git branch --show-current
```

명시 base가 이미 승인됐다면:

```powershell
$Base = & .agents/skills/pr-workflow/scripts/detect_base.ps1 -Base '<branch>'
```

## 결정 우선순위

1. 사용자가 현재 작업에 명시한 base
2. `.agents/project.json`의 비어 있지 않은 `baseBranch`
3. `origin/HEAD`와 실제 local 기본 후보의 일치
4. 그 밖의 분기·merge-base 증거

설정값이 `null`이거나 원격 default와 local 후보가 다르면 모호한 상태다. 감지 도구는
후보를 stderr에 출력하고 exit 2로 끝내며 PR을 만들거나 설정을 쓰지 않는다.

## 사용자 확인

모호할 때 다음을 함께 보여주고 base 하나를 직접 선택해 달라고 묻는다.

- 후보 branch 이름
- `git log -1 --oneline <branch>`
- 현재 head
- 가능하면 merge-base 또는 worktree 생성 근거

선택값은 현재 `create_pr.ps1 -Base <chosen>` 호출에만 사용한다. `.git` 메타데이터나
프로젝트 설정에 영구 기록하는 일은 별도 사용자 요청 없이는 하지 않는다.

## 한계

- 오래된 worktree에서는 같은 조상 commit을 포함하는 후보가 늘 수 있다.
- `origin/HEAD` 자체가 낡거나 잘못 설정될 수 있다.
- commit 이력이 없는 저장소는 자동 판정할 근거가 없다.
- 이름이 익숙하다는 것은 분기 증거가 아니다.

이 경우 자동 fallback 대신 사용자 확인이 안전한 정상 종료다.

## 보조 POSIX 구현

`scripts/detect_base.sh`는 사용자가 Git Bash를 명시한 경우에만 쓸 수 있는 보조 구현이다.
Windows 기본 계약과 완료 증거는 `detect_base.ps1`을 기준으로 한다.
