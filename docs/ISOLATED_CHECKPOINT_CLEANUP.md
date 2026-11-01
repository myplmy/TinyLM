# 격리 스모크 체크포인트 정리기

일반 체크포인트는 기존 [정리기](../scripts/cleanup_ckpt.py)와
[checkpoints.tsv](../checkpoints.tsv)가 담당한다. 격리 합성 스모크는
[새 정리기](../scripts/cleanup_isolated_ckpt.py)와
[실행 SH](../run_cleanup_isolated_checkpoints.sh)로 따로 조회한다.
두 정리기의 대상 경로와 판정 원천을 섞지 않는다.

## 1. 지원 범위와 실행 권한

대상은 `runs/validation/codex_smoke/<세션ID>/runs/ckpt/` 바로 아래 파일이다.
Codex 주도 작업 뒤 남은 **합성 스모크** 산출물을 정리하는 도구이며, 본학습 모델을
자동으로 폐기하는 도구는 아니다. 일반 `runs/ckpt/`, HF, 데이터·캐시, 다른 임의 격리폴더나
옛 `test_result/evidence/local/` 실행은 탐색·삭제 대상이 아니다.

인자 없는 실행은 읽기 전용이다. CPU와 파일 메타데이터만 사용하며 torch import,
모델 로딩, GPU 조회·실행, 새 학습은 하지 않는다. 실제 삭제는 사용자가 정확한 목록을
확인해 실행하거나, 별도 삭제 권한을 위임한 경우에만 수행한다. 도구 구현 승인만으로
향후 실제 파일 삭제가 승인되는 것은 아니다.

## 2. 조회와 사용자 확인

저장소에서 다음 명령 하나로 전체 격리 세션의 후보와 보류 이유를 본다.

```bash
./run_cleanup_isolated_checkpoints.sh
```

실행 큐에도 기존 정리기와 같은 `plan=-`의 공용 유지보수 항목으로 등록한다. 큐는
추가 옵션 없이 호출하므로 후보 조회만 하며 삭제 확인이나 자동 삭제를 시작하지 않는다.

원하는 세션만 보려면 화면에 나온 실제 세션 ID를 지정한다. 여러 세션은
`--session-id`를 반복한다. 아래 `새_스모크_ID`는 실제 ID로 바꿔야 한다.

```bash
./run_cleanup_isolated_checkpoints.sh --session-id 새_스모크_ID
./run_cleanup_isolated_checkpoints.sh --session-id 새_스모크_ID --interactive
```

`--interactive`는 한 프로세스 안에서 정확한 경로·개수·크기를 먼저 보여준다. 관련
실험·학습·평가 프로세스를 종료한 상태에서 대문자 `YES`를 입력해야 삭제한다. 다른 입력은
취소한다. `--yes` 같은 무확인 옵션은 지원하지 않는다. 후보가 없으면 확인 없이 종료한다.

## 3. 주도 작업에서 사용할 목록 고정 방식

먼저 새 파일에 조회 목록을 보존한다. `--output`은 다음 감사 폴더 안의 새 `.json`만
허용하며 기존 파일은 덮어쓰지 않는다. 같은 이름을 재사용하지 않는다.

```bash
./run_cleanup_isolated_checkpoints.sh \
  --session-id 새_스모크_ID \
  --output handoff/audit/isolated_checkpoint_cleanup/preview_new_run.json
```

화면의 정확한 경로와 보류 사유를 검토한다. 실제 삭제 승인이 확보된 뒤, 출력된
64자리 `목록 SHA-256`을 다음 명령에 **직접 명시**한다. 아래 SHA 자리도 실제 값으로
교체한다. 검토하지 않은 목록의 SHA를 자동 계산해 곧바로 실행하는 절차로 쓰지 않는다.

```bash
./run_cleanup_isolated_checkpoints.sh --apply \
  --manifest handoff/audit/isolated_checkpoint_cleanup/preview_new_run.json \
  --manifest-sha256 확인한_64자리_SHA256
```

SHA가 없거나 다르면 삭제하지 않는다. 조회 후 정리기 코드, 원로그, 영수증, 결과 JSON,
부모 참조, 후보 파일·폴더 또는 검사한 목록이 달라져도 삭제 전에 중단한다. 이때 기존
manifest를 손으로 고치지 말고 변경 원인을 확인한 뒤 새 목록을 작성해 다시 검토한다.

## 4. 후보 선정과 보호

다음을 모두 만족한 세션의 정확한 출력만 후보가 된다.

1. `TINYLM_CODEX_SMOKE_EXECUTION_V1` / `codex_isolated_smoke_v1` 영수증에 격리 경로와
   세션 ID가 일치하고, 전체·개별 행동·요약이 정상 완료됐다. 실패·중단·시간초과는 보류한다.
2. 실행 당시 소스의 전후 SHA가 같고 원로그의 SHA·크기와 명령·종료 블록이 일치한다.
   **현재 코드와 과거 실행 코드의 SHA가 같을 필요는 없다.** 과거 기록 안의 일관성을 본다.
3. 명령이 `run100m.py train --tiny --data synthetic`이고, 명령에서 계산한 이름과
   실제 결과 JSON의 preset·data·arch·tag·steps·final이 일치한다.
4. 명령이 생성하는 `<이름>.pt`, `<이름>_best.pt`만 허용한다. 파일명 접두사만으로
   합성 자료라고 판단하지 않는다. 알려지지 않은 파일·하위폴더가 있으면 세션 전체를 보류한다.
5. 파일이 실행 시각 구간에 작성된 비어 있지 않은 일반 파일이다. symlink, 다중 hardlink,
   경로 이탈, 연결된 상위폴더, 실행 후 덮어쓴 파일은 보류한다.
6. 기존 `checkpoints.tsv`의 keep/hold와 같은 이름이거나, 다른 런의 `init_from_src` /
   `kd_teacher`에 부모·교사로 기록된 파일이면 짝 파일까지 보류한다. 같은 세션 내부의
   스모크 의존 관계는 전체 명령의 정상 완료를 확인한 경우 허용한다. 여러 격리폴더의
   basename이 같더라도 내부 참조는 그 참조가 기록된 격리폴더 기준으로 해석한다.
   다른 폴더에서 정확한 격리 경로를 참조한 경우에는 해당 세션을 보호한다.
7. 같은 사용자 프로세스의 격리 실행이나 열린 후보 파일을 Linux `/proc`에서 발견하면
   보류한다. 프로세스 확인 권한이 없어 확인할 수 없는 경우도 보류한다.

부모 참조 검사는 일반·격리 `runs/logs/*.json`의 위 두 필드와 기존 TSV를 사용한다.
아직 로그에 남지 않은 미래 실험계획·외부 복사본의 의존 관계까지 증명하지 않는다.
새 연구의 부모로 쓸 세션은 목록에서 제외하고 보존 필요성을 먼저 판단한다. 검사 도중
새 파일을 쓸 수 있는 프로세스를 모두 정지하는 것은 실제 삭제의 선결이다. 도구가 임의의
동시 작성자와 트랜잭션을 맺는다고 보장하지 않는다.

## 5. 삭제 기록과 중단 복구

실제 삭제를 시작하면 `handoff/audit/isolated_checkpoint_cleanup/<UTC시각_식별자>/`에
다음을 보존한다. 같은 정리기 두 개의 동시 삭제는 잠금으로 막는다.

- `plan.json`: 확인한 정확한 후보·입력 해시·파일 identity와 폴더 목록.
- `journal_0001.jsonl` 등: 파일별 `INTENT`와 `DELETED`. 파일당 20MB 미만으로 분할한다.
- `receipt.json`: `COMPLETE` / `PARTIAL_ERROR`, 실제 삭제 개수·논리 크기, 전후 WSL
  파일시스템 여유량과 차이, 오류. 다른 프로세스의 I/O도 여유량 차이에 영향을 줄 수 있다.

각 unlink 직전에도 상위폴더와 파일의 dev/inode·크기·mtime/ctime·링크를 다시 확인한다.
폴더는 `NOFOLLOW`로 열고 같은 폴더 fd에서 파일만 unlink한다. 원로그·결과 JSON·영수증·
판정 보고서·폴더는 지우지 않는다. 오류가 나면 남은 파일로 범위를 넓혀 자동 재시도하지 않는다.
확인된 부분 삭제량을 영수증에 남기고 원인을 검토한다.

강제 종료·전원 장애처럼 프로세스가 `finally`도 실행하지 못하면 최종 영수증이 없을 수 있다.
`INTENT`만 남은 파일은 삭제 완료로 단정하지 말고 실제 존재 여부와 저널을 대조해야 한다.
WSL 여유량 증가는 Windows 호스트의 VHDX 축소나 Z드라이브 여유 증가를 보장하지 않는다.

감사 자료는 모델 텐서 대신 작은 JSON/JSONL이다. 로그·원본 판정과 함께 정확한 경로를
검토해 필요 자료만 명시 staging한다. 자동 Git staging/commit이나 원본 evidence 이동은 없다.

## 6. 검증 범위

[CPU 시험](../scripts/test_cleanup_isolated_ckpt.py)은 임시폴더에서만 삭제·부분 실패와
보호 규칙을 시험한다. 기본 명령으로 실제 격리 경로를 조회할 수 있으나 조회 성공은 실제
대용량 삭제·GPU 스모크·모델 품질의 증거가 아니다.

```bash
python -B -X utf8 scripts/test_cleanup_isolated_ckpt.py
```

2026-10-31 구현 당시 실제 경로에서는 조회만 수행했다. 직전 사용자102의 승인 삭제는
[별도 감사](../handoff/audit/checkpoint_retention_20261031/README.md)가 소유한다.
