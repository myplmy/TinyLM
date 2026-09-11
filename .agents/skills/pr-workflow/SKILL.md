---
name: pr-workflow
description: 사용자가 명시적으로 요청한 branch·commit·push·PR 생성·merge를 안전하게 수행한다. base/head를 확인하고 `git add .`·`-A`를 금지하며, `.agents/project.json`의 제외 경로와 명시 파일 allowlist를 적용한다. Windows PowerShell을 기본 경로로 사용한다.
---

# pr-workflow

> **TinyLM Codex 이식본.** 프로젝트 메타데이터는 [`.agents/project.json`](../../project.json),
> 환경·권한 경계는 [Codex 분리 계약](../../../ai_dev_tool/Codex/README.md)을 따른다.

PR 생성·머지 표준을 강제한다. **scope 사고(`git add -A`로 제외 경로 포함)** 를 원천 차단한다.
프로젝트 고유 값은 [`.agents/project.json`](../../project.json)에서 읽는다.

## 권한 경계

- 조회(`git status`, `git diff`, `gh ... view`)는 관련 진단 범위에서 가능하다.
- branch 생성, staging, commit, push, PR 생성·편집, merge, issue comment/close는
  **사용자의 해당 외부 변경 요청이 있을 때만** 수행한다.
- PR 생성 요청은 merge 승인까지 포함하지 않는다. merge는 별도 명시가 필요하다.
- 이 스킬 자체를 읽었다는 사실은 어떤 Git·GitHub 변경 권한도 부여하지 않는다.
- 현재 사용자 범위와 [AGENTS.md](../../../AGENTS.md)가 항상 우선한다.

## 왜 이 스킬이 필요한가

일부 경로(개인 로컬 설정·대용량 데이터·재생성 산출물·비밀키)는 **영구 untracked**로 두어야 한다. 일반적 PR 관행대로 `git add .`를 쓰면 이들이 우발적으로 포함된다. 이 스킬이 그 관행을 내재화한다.

## 언제 이 스킬을 사용하나

### 반드시 사용
- "PR 만들어" / "pull request 생성" / "PR 올려"
- "merge 수행" / "PR 머지해"
- "브랜치 만들고 푸시" / "현재 작업을 PR로"
- 사용자가 `gh pr create` 커맨드를 초안으로 작성한 경우

### 사용하지 않음
- 로컬 커밋만 원할 때 (push 없이) — 일반 git 커밋으로 진행하되 scope 룰은 동일 적용
- PR 조회만 하는 경우 (`gh pr list`, `gh pr view`)

## 핵심 규약 (비협상)

### 1. Base는 증거로 결정, Head는 현재 branch

Windows 기본 경로는 `scripts/detect_base.ps1`이다. 자세한 계약은
[`references/base_branch_detection.md`](references/base_branch_detection.md)을 따른다.

```powershell
$Base = & .agents/skills/pr-workflow/scripts/detect_base.ps1
if (-not $Base) {
    # 후보와 최근 commit을 보고한 뒤 사용자에게 직접 선택을 묻는다.
    return
}
$Head = git branch --show-current
gh pr create --base $Base --head $Head ...
```

우선순위: 사용자 명시 `-Base` → `.agents/project.json`의 비어 있지 않은 `baseBranch`
→ 원격 default branch와 분기 근거. 현재 설정이 `null`이거나 근거가 충돌하면 임의로
`main` 또는 `master`를 고르지 않는다.

**사용자 문의 절차** (결과가 모호할 때 필수):
1. 후보 branch와 각 `git log -1 --oneline <branch>` 결과를 보고한다.
2. 사용자에게 base 하나를 직접 선택해 달라고 묻는다.
3. 선택값은 현재 작업에 명시 인자로 사용한다. 영구 기록은 사용자가 별도로 요청한 경우에만 한다.

### 2. `git add .` / `-A` 금지

스테이징은 **반드시 명시 경로**로:

```powershell
git add path/to/file1.md path/to/file2.py
```

이유: `.agents/project.json`의 `excludedPaths`에 등재된 경로를 전체 staging이
우발적으로 포함시킬 수 있다.

사용자가 "전체 추가" 요청 시 **거부하고 대안 제시**:
1. `git status --porcelain`으로 변경 목록 확인
2. `excludedPaths` 필터링 (`scripts/safe_stage.ps1` 참조)
3. 필터링 후 남은 파일 목록을 사용자에게 제시 → 확인 후 `git add <paths>`

**영구 제외 경로는 `.agents/project.json`의 `excludedPaths`가 단일 소스**다.
상세: [`references/excluded_paths.md`](references/excluded_paths.md).

### 3. Commit 메시지 포맷

- 제목: 저장소 관례에 맞는 한 줄. 사용자가 한국어 메시지를 요청하면 한국어로 작성
  - ✅ `Docs: generalize workflow skills + add project.json config`
  - ❌ `update some docs`
- 본문: 1줄 공백 후 변경 요약 (bullet)
- 공동 작성자 표기를 넣을 때는 `Co-Authored-By: OpenAI Codex <codex@openai.com>`을 사용한다.
- PowerShell here-string 또는 임시 메시지 파일을 사용한다:

```powershell
$Message = @'
제목 한 줄

- 변경 1
- 변경 2

Co-Authored-By: OpenAI Codex <codex@openai.com>
'@
git commit -m $Message
```

### 4. PR body 포맷

```markdown
## Summary

- 핵심 변경 1~3개 (bullet)
- 기술적 맥락·근거 필요 시 한 줄 추가

## Test plan

- [ ] 테스트 항목 1
- [ ] 테스트 항목 2

Generated with OpenAI Codex
```

**Doc Impact (조건부 섹션)**: `.agents/project.json`의 `docImpactTargets`에 정본 문서가 등재돼 있으면 아래 섹션을 추가하고 각 문서 영향을 평가한다. 배열이 비어 있으면 **섹션 자체를 생략**한다.

```markdown
## Doc Impact

- [ ] <doc 1> — 영향 없음 / 갱신: §X.Y
- [ ] <doc 2> — 영향 없음 / 갱신: §Y
```

영향 있으면 동일 PR에 동기 갱신 커밋을 포함하고 갱신 위치를 기재, 없으면 "영향 없음" 명시. 템플릿 변형은 [`references/pr_body_template.md`](references/pr_body_template.md) 참조.

**체크박스 표기 기준** — 작성 시점에 실제 수행·검증을 마친 항목만 `[x]`, 미수행은 `[ ]`로 둔다.

### 5. gh CLI 경로

PowerShell에서 `Get-Command gh`를 먼저 사용하고 없으면 표준 설치 경로를 확인한다.
상세: [`references/gh_cli_paths.md`](references/gh_cli_paths.md).

## 워크플로우 (전체 흐름)

> **토큰 효율 원칙**: git/gh 호출 출력은 LLM 컨텍스트로 직접 들어간다. 인간 친화 정보(diff stat, fast-forward 메시지, LF→CRLF warning, "Already up to date")는 토큰 손실 — `-q`/`--quiet` 옵션과 stderr 리다이렉션을 적극 활용한다.

### (1) 사전 확인
1. 현재 브랜치 확인: `git branch --show-current` (이것이 PR head)
2. **base 결정**: `.agents/skills/pr-workflow/scripts/detect_base.ps1`. 빈 결과면 후보를
   보고하고 사용자에게 직접 선택을 묻는다. 영구 기록은 별도 요청 시에만 한다.
3. base 최신화가 필요하면 네트워크 변경 범위를 알린 뒤 `git fetch -q origin $Base`
4. `git status --short -uno`로 변경 파악 (`-uno`는 untracked 노이즈 차단)
5. gh auth 상태: `& $Gh auth status` (1회/세션)

### (2) 작업 branch 준비
현재 working branch에서 작업 중이 아니면: `git checkout -b <descriptive-branch-name>`. 이미 적절한 branch면 생략.

### (3) 안전 staging (LF/CRLF warning 억제)
`scripts/safe_stage.ps1` 실행 또는 수동:
1. `git status --porcelain` → 변경 파일 목록
2. `excludedPaths` 필터링
3. 사용자에게 최종 목록 보여주고 확인
4. 사용자가 승인한 명시 경로만 `git add -- <paths>`

**주의 — 금지 패턴**: `git add .` / `git add -A` — 제외 경로가 `.gitignore` 누락 시 우발 staging. 본 스킬 핵심 룰 §2 위반.

### (4) Commit
위 "Commit 메시지 포맷" 준수. PowerShell here-string을 사용한다.

### (5) Push (출력 압축)
```powershell
git push -u --quiet origin <branch-name>
```

### (6) PR 생성
`scripts/create_pr.ps1` 또는 명시적 수동 호출:
```powershell
$Head = git branch --show-current
$Base = & .agents/skills/pr-workflow/scripts/detect_base.ps1
if (-not $Base) { throw 'Base is ambiguous; ask the user before creating a PR.' }
& $Gh pr create --base $Base --head $Head --title '...' --body-file $BodyPath
```

`create_pr.ps1`은 base가 모호하면 외부 변경 없이 실패한다. 사용자 선택 뒤 `-Base <chosen>`을 명시한다.

### (7) Merge (사용자 요청 시) — 헬퍼 스크립트 권장

**권장 (별도 merge 승인 뒤)**:
```powershell
& .agents/skills/pr-workflow/scripts/merge_and_sync.ps1 -PrNumber <NN>
# OK pr=<NN> merged synced base=<branch>
```

이 스크립트는 mergeStateStatus 사전 확인 → PR baseRefName 조회 → 머지 → 로컬 base branch 동기화까지 1회 호출로 처리. 성공 시 1줄, 실패 시 `FAIL pr=<NN> state=<X>` 1줄.

머지 전 확인: `mergeStateStatus == "CLEAN"`, CI 체크가 있다면 통과.

### (8) 보고
사용자에게 PR URL을 보고. 머지된 경우 `(merged)` 추가.

### (9) 이슈 close 코멘트 (해당 PR이 이슈를 해소할 때)

PR이 GitHub 이슈를 해소하면 **머지 후** 그 이슈에 해소 코멘트를 남기고 close한다.

**작성 방법 (비협상)**:
- `gh issue close <N> --comment "..."`의 인라인 문자열로 **긴 코멘트를 한 줄로 밀어넣지 말 것**. GitHub 마크다운은 문단 사이 **빈 줄**이 있어야 렌더되므로, 한 줄 코멘트는 헤딩·리스트가 뭉개진다.
- 반드시 **임시 파일로 작성 → `--body-file`**로 전달:
  ```powershell
  $CloseBody = Join-Path ([IO.Path]::GetTempPath()) 'codex-close-N.md'
  # 승인된 본문을 $CloseBody에 UTF-8로 작성한다.
  gh issue comment <N> --body-file $CloseBody
  gh issue close <N>
  ```

**구조 (§ 헤딩 필수)**: `## ✅ 해소` → `### 구현 PR` → `### 내역` → `### 검증` → `### 잔여/후속`. **PR 번호 링크 + 빈 줄 문단 구분은 생략 불가.**

- **`### 구현 PR` = 이슈를 실제로 해소한 PR을 전부 나열** (한 이슈를 여러 PR로 해소하면 다수 항목):
  ```markdown
  ### 구현 PR
  - #<PR-a> (<요약>)
  - #<PR-b> (<요약>)

  (참고) 부수 PR:
  - #<PR-plan> (plan)
  ```
  구현 PR과 부수 PR(plan/핸드오프)은 `(참고)`로 구분. 단일 PR이면 항목 1개로 축약.
- **`### 내역`** — 번호 리스트로 변경점.
- **`### 검증`** — 회귀 테스트 수치·영향.
- **`### 잔여/후속`** — 남은 항목·분리 이슈 (없으면 "없음").

**PR ↔ 이슈 링크 (필수)**: 이슈만 보고도 어느 PR이 해소했는지 추적 가능해야 한다. `### 구현 PR` 절의 PR 번호 링크가 그 추적 고리이므로 **생략 금지**.

## 에러 복구

### ".gitignore로 무시된 파일이 스테이징 됨"
→ 제외 경로가 `-A`로 끌려들어간 경우. 언스테이징: `git reset HEAD <path>`

### Pre-commit hook 실패
**amend 금지**. 문제 수정 후 **새 커밋** 생성.

### "gh: command not found"
→ PowerShell `Get-Command gh` 확인 후 `C:\Program Files\GitHub CLI\gh.exe` 존재 확인

## 번들 리소스

- `scripts/safe_stage.ps1` — `excludedPaths` 필터링과 명시 경로 staging
- `scripts/detect_base.ps1` — base 결정; 모호하면 빈 결과와 후보 보고
- `scripts/create_pr.ps1` — 명시 승인 뒤 PR 생성
- `scripts/merge_and_sync.ps1` — 별도 승인 뒤 PR 머지와 원격 base 갱신
- `scripts/*.sh` — Git Bash 환경을 사용자가 명시한 경우의 보조 구현. Windows 호환성 증거로 삼지 않는다.
- `references/pr_body_template.md` — PR body 표준 템플릿 모음
- `references/gh_cli_paths.md` — OS·환경별 gh 경로 해결
- `references/excluded_paths.md` — 제외 경로 설정 방법 + 필터링 규칙
- `references/base_branch_detection.md` — base 자동 감지 정책·휴리스틱·사용자 문의 절차

## Do / Don't 요약

### DO
- Base: `detect_base.ps1`로 확인. 모호하면 사용자에게 묻고 현재 호출에 명시한다.
- Head: 현재 branch (`git branch --show-current`)
- Stage: 명시 경로만
- Commit: PowerShell here-string + 필요 시 OpenAI Codex 공동작성자
- gh 경로: PowerShell `Get-Command gh` 우선, 없으면 검증된 표준 설치 경로
- 이슈 close: UTF-8 임시 파일 → `--body-file`, `## 해소 → ### 구현 PR(#번호 링크) → ### 내역 → ### 검증 → ### 잔여` 구조

### DON'T
- `git add -A` / `git add .`
- `git commit --amend` (pre-commit hook 실패 후)
- `--no-verify` / `--no-gpg-sign` (사용자 명시 요청 없이)
- Force push to base branch
- detect_base의 LOW/NONE 결과를 무시하고 임의 base로 fallback — 반드시 사용자 문의
- 이슈 close 코멘트를 긴 인라인 문자열 한 줄로 (마크다운 안 렌더) · PR 번호 링크 생략
