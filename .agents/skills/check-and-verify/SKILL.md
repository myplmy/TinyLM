---
name: check-and-verify
description: PR 또는 Issue의 Test plan 체크박스를 분류하고, 사용자 승인 아래 실제 증거를 검증한 뒤 별도 외부 쓰기 승인을 받은 PASS 항목만 갱신한다. "PR 체크박스 검증", "test plan 검증", "머지 전 체크박스 점검" 요청에 사용한다.
---

# check-and-verify

> **TinyLM Codex 이식본.** 프로젝트 메타데이터는 [`.agents/project.json`](../../project.json),
> 환경 경계는 [Codex 분리 계약](../../../ai_dev_tool/Codex/README.md)을 따른다.

PR / Issue body의 Test plan 체크박스를 **실제로 검증**하고 통과 항목만 체크한다.

## 왜 이 스킬이 필요한가

PR 머지 전 Test plan 체크박스 검증은 수작업이면 (1) 항목을 빠뜨리거나 (2) 검증 없이 전부 체크하는 실수가 난다. 이 스킬은 체크박스를 추출·분류하고, 자동 실행 가능한 항목을 **사용자 승인 하에** 실제로 돌린 뒤, 통과한 항목만 갱신한다 — 검증과 기록을 한 흐름으로 묶는다.

## 언제 사용하나

### 사용
- PR / Issue의 Test plan 체크박스를 검증·갱신해야 할 때
- PR 머지 직전 테스트 항목 실행 확인이 필요할 때

### 사용하지 않음
- 체크박스가 없는 PR / 단순 문서 PR (검증할 항목 자체가 없음)
- PR body 작성·머지 자체 — 그건 `pr-workflow`

## 승인 모델 (비협상)

이 스킬은 **두 번의 사용자 승인**을 거친다. 자동으로 명령을 돌리거나 PR body를 수정하지 않는다.

1. **실행 전 항목별 승인** — 정확한 명령과 영향을 제시하고 사용자가 실행할 항목을 고르게 한다. 고르지 않은 항목은 실행하지 않는다.
2. **PATCH 전 일괄 승인** — 실행 결과 보고 후 체크박스 갱신 여부를 별도로 확인한다. 승인 시에만 `gh ... edit`으로 body를 갱신한다.

실행·외부 쓰기 권한은 짧은 일반 질문으로 직접 묻는다. 선택지가 많으면 한 차수 최대 3개로 나눈다.

## 워크플로우

### 1. 입력 식별 — PR / Issue 자동 판별

번호를 받으면 PR인지 Issue인지 판별한다. PR을 먼저 시도하고 실패하면 Issue. PowerShell의
`Get-Command gh`와 `[IO.Path]::GetTempPath()`를 사용하며 저장소 안에 임시 body를 만들지 않는다.
구체 명령은 [`CODEX_WORKFLOW.md`](CODEX_WORKFLOW.md)를 따른다.

### 2. 체크박스 추출·분류

```powershell
python .agents/skills/check-and-verify/scripts/checkbox_tool.py classify $BodyPath
```

JSON 배열을 반환한다 — 원소마다 `index, lineno, checked, text, category, command`.

분류 카테고리:

| category | 판정 근거 | 자동 실행 |
|---|---|---|
| `pytest` | 코드 스팬이 `python -m pytest ...` 또는 `pytest ...` | O — 명령 실행, exit 0 = PASS |
| `script` | 코드 스팬이 `python test/...` 또는 `python scripts/...` | O — 명령 실행, exit 0 = PASS |
| `script+env` | 위 명령에 `NAME=value` env prefix가 붙음 | O — env 포함 한 줄로 실행 |
| `file_check` | 존재/생성/저장 키워드 + 경로형 코드 스팬 | O — 경로 존재 확인 |
| `manual` | 위 어디에도 해당 없음 (수동 확인 항목) | X — 사용자 확인 |

분류는 **휴리스틱**이다. 오분류로 보이는 항목(예: 실제로는 수동인데 `script`로 잡힘)은 사용자에게 알리고 manual로 강등한다.

> 프로젝트의 테스트 명령 관행이 다르면(`test/`·`scripts/` 외 디렉토리, 다른 러너) `scripts/checkbox_tool.py`의 `classify_command` 정규식을 그 관행에 맞게 조정한다.

### 3. 분류 결과 보고

이미 `checked: true`인 항목은 **SKIP** (재실행 안 함). 미체크 항목을 카테고리별로 표로 보고한다.

### 4. 실행 항목 승인 (승인 1)

미체크 + 자동 가능(`pytest`/`script`/`script+env`/`file_check`) 항목의 index와
정확한 명령을 제시하고 사용자가 실행할 항목을 고르게 한다. 항목이 많으면 차수를 나눈다.

### 5. 승인 항목 실행

- **pytest / script / script+env**: 리포 루트에서 `command`를 그대로 실행. exit code 0 = PASS, 그 외 = FAIL. 출력이 길면 마지막 10~20줄만 인용.
- **file_check**: `command`가 경로다.
  - 디렉터리: `Test-Path -LiteralPath <path> -PathType Container` 후 필요 시
    `Get-ChildItem -LiteralPath <path>`로 비어 있지 않은지 확인
  - 파일: `Test-Path -LiteralPath <path> -PathType Leaf`

명령은 체크박스 텍스트에서 추출된 것이므로, 실행 전 사용자가 승인한 항목만 돌린다 (승인 1). 화이트리스트(pytest·프로젝트 스크립트) 밖 명령은 애초에 자동 분류되지 않으므로 임의 명령은 실행되지 않는다.

### 6. 결과 집계 보고

| index | category | result | 요약 |
|---|---|---|---|
| 0 | pytest | PASS | 42 passed |
| 2 | script | FAIL | exit 1 — ImportError |

`result` ∈ PASS / FAIL / SKIP(이미 체크됨·미선택). FAIL 항목은 원인 한 줄 포함.

### 7. manual 항목 처리

`manual` 카테고리 + 미선택 항목을 사용자에게 보고한다. 사용자가 수동으로 완료했다고
명시한 항목만 PATCH 대상에 포함한다.

### 8. 체크박스 갱신 승인 (승인 2)

PATCH 대상 = PASS 항목 + 사용자가 완료 확인한 manual 항목의 index 목록. 변경될 index와
before/after를 보여주고 원격 body 갱신을 직접 승인받는다.

### 9. body 갱신·PATCH

승인 시:

```powershell
python .agents/skills/check-and-verify/scripts/checkbox_tool.py apply `
    $BodyPath "0,2,3" | Set-Content -LiteralPath $UpdatedPath -Encoding utf8

# KIND 에 따라 분기
& $Gh pr edit  $N --body-file $UpdatedPath     # KIND=pr
& $Gh issue edit $N --body-file $UpdatedPath   # KIND=issue
```

`gh pr edit` / `gh issue edit`은 현재 리포 컨텍스트에서 동작하므로 owner/repo를 명시할 필요가 없다. `--body-file`은 파일을 UTF-8로 읽으므로 한글이 안전하다.

### 10. 최종 보고

갱신된 체크박스 수, 남은 FAIL·manual 항목을 보고한다. FAIL이 있으면 머지 부적합 신호로 명확히 전달한다.

## 번들 스크립트

`scripts/checkbox_tool.py` — 네트워크 호출 없는 순수 텍스트 변환 (프로젝트 중립).

- `classify <body_file>` — 체크박스 추출·분류 → JSON (stdout)
- `apply <body_file> <idx,idx,...>` — 지정 인덱스를 `[x]`로 바꾼 body 전문 (stdout)

stdout은 UTF-8로 고정되어 있어 리다이렉트 출력 시 한글이 손상되지 않는다. 콘솔 직접 표시 시 mojibake는 정상 — 파일·파이프 출력은 정확하다.

## gh CLI 경로

PowerShell에서 `Get-Command gh`를 먼저 사용하고, 없으면
`C:\Program Files\GitHub CLI\gh.exe`의 존재를 확인한다. 인증이 없으면 대화형 로그인을
임의 실행하지 않고 사용자에게 위임한다.

## 에러 복구

- **체크박스 0개**: classify가 `[]` 반환 → "검증할 Test plan 항목 없음" 보고 후 종료.
- **명령 FAIL**: 해당 항목은 체크하지 않는다. 원인을 보고하고 사용자가 수정하도록 둔다.
- **`gh ... edit` 실패** (권한·네트워크): updated body 파일 경로를 사용자에게 알리고 수동 갱신 안내.
- **오분류 의심**: manual로 강등하고 사용자 확인. 추측 실행 금지.

## 체크리스트

- [ ] PR / Issue 자동 판별했는가
- [ ] 자동 항목을 실행 전 정확한 명령과 함께 승인받았는가 (승인 1)
- [ ] 이미 체크된 항목을 재실행하지 않았는가 (SKIP)
- [ ] 결과 표(PASS/FAIL/SKIP)를 보고했는가
- [ ] 체크박스 갱신을 별도로 일괄 승인받았는가 (승인 2)
- [ ] PASS 항목만 `[x]`로 갱신했는가 (FAIL 항목 미체크)
