# 영구 제외 경로

PR staging에서 제외할 프로젝트 경로의 단일 소스는 `.agents/project.json`의
`excludedPaths` 배열이다. 스킬·스크립트·이 문서에 프로젝트 목록을 중복 정의하지 않는다.

## 매칭

- 저장소 상대경로를 `/`로 정규화한다.
- 디렉터리 항목은 정확 경로와 그 하위만 제외한다.
- `*`가 있는 항목은 wildcard로 해석한다.
- 비밀 파일과 보호 데이터는 사용자가 일반적으로 "전체 추가"라고 말해도 제외한다.

## Windows 기본 사용

목록 검토만:

```powershell
& .agents/skills/pr-workflow/scripts/safe_stage.ps1 -Path @(
    'path/to/file1.md',
    'path/to/file2.py'
)
```

사용자가 위 명시 목록의 staging을 승인한 뒤에만:

```powershell
& .agents/skills/pr-workflow/scripts/safe_stage.ps1 -Add -Path @(
    'path/to/file1.md',
    'path/to/file2.py'
)
```

`-Add`에 경로를 생략하면 스크립트는 실패한다. `git add .`와 `git add -A`로
우회하지 않는다.

## 예외

사용자가 제외 경로 내부 파일을 의도적으로 포함하라고 명시하면 즉시 강제 추가하지 않는다.
보호 이유, 정확한 파일, 비밀·대용량 여부, `.gitignore` 상태를 보고하고 재확인한다.
승인된 예외는 PR body에 이유를 남긴다.

새 제외 경로가 생기면 `.agents/project.json`만 갱신한다. staging 후에는 항상
`git diff --cached --name-only`로 실제 목록을 확인한다.
