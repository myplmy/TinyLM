# W&B WSL 누락 run 확인·backfill 사용법

## 1. 두 shell의 역할이 다르다

| 도구 | 용도 | 인자 없음 |
|---|---|---|
| `scripts/shell/tool_wandb_push.sh <raw-tag>` | 한 full training launcher가 성공 직후 자기 tag 하나를 전송 | 안전하게 중단 |
| `scripts/shell/tool_wandb_backfill.sh [--push]` | 승인 manifest의 P097 4개·P076 3개를 원격과 비교해 누락분만 복구 | network 0인 계획 출력 |

사용자가 실행한 `tool_wandb_push.sh`는 단건 adapter라 raw tag 없이 중단한 것이 정상이다. 여러
누락 run을 복구할 때는 새 backfill shell을 사용한다.

## 2. API key 파일을 WSL 경로로 지정한다

key 값을 명령행에 직접 쓰지 않는다. key 한 줄만 든 파일의 절대 WSL 경로를 환경변수에 둔다.

```bash
export TL_WANDB_KEY_FILE=/absolute/wsl/path/to/wandb_api_key.txt
export TL_WB_PROJECT=tinylm
```

기본 W&B entity가 아닌 팀 entity를 쓸 때만 다음을 추가한다.

```bash
export TL_WB_ENTITY=your-team-or-user
```

도구는 key 내용을 인쇄하거나 저장소에 복사하지 않는다.

## 3. 먼저 계획만 본다 — 원격 조회도 하지 않는다

```bash
./scripts/shell/tool_wandb_backfill.sh
```

정상 신호는 `targets=7`과 일곱 `local tag=... run_id=...` 행, 마지막 `[PLAN ONLY]`다. 이 단계는
local JSON의 자격·exact tag만 검사하고 W&B login·조회·upload를 0건으로 유지한다.

## 4. 누락분만 실제 복구한다

```bash
./scripts/shell/tool_wandb_backfill.sh --push
```

실제 모드는 다음 순서다.

1. explicit key 파일로 login한다.
2. manifest 일곱 run ID만 원격에서 조회한다.
3. `EXISTS`는 건너뛴다.
4. `MISSING`만 기존 `wandb_sync.upload_runs()`로 올린다.
5. 마지막에 `uploaded_missing=N`, `skipped_existing=M`을 출력한다.

같은 명령을 다시 실행해도 이미 있는 run은 재생성하지 않는다. manifest 밖 과거 full run은 조회하지
않으므로 사용자가 의도적으로 삭제한 run을 부활시키지 않는다.

## 5. 실패 판독

| 종료코드 | 뜻 | 조치 |
|---:|---|---|
| 0 | 계획 출력 또는 remote 비교/backfill 완료 | remote config를 local JSON과 대조 |
| 2 | manifest tag가 local eligible JSON 정확히 1개에 대응하지 않음 | 출력된 tag·JSON 중복/부재 확인 |
| 3 | key·entity·network·W&B API·upload 실패 | `[FAIL]` 원문 보존 후 환경/권한 교정 |

W&B는 사본이다. remote 장애가 있어도 `runs/logs/*.json`과 `test_result/` 결과 판정은 손상되지
않으며, remote와 다르면 local JSON·결과문서가 정본이다.
