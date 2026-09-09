# A08 — Muon 레시피의 matrix WD와 실제 update 계측

우선순위: **P1** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A08](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

lr 15배 Muon의 실용적 개선과 기존 LR 격자 결과는 보존한다. AdamW matrix WD=.1, Muon matrix WD=0인 대조는 optimizer 수학 단독의 인과 증거가 아니다.

### 코드 수정안

- `tinylm/cli.py`/`train/trainer.py`: `--matrix-weight-decay`를 두 optimizer에 연결한다. 미지정 기본값은 기존 AdamW .1/Muon 0을 유지한다.
- 행렬 집합은 기존 Muon split_params, 비행렬 그룹과 LR은 model.param_groups에서 얻는다. embedding/norm/LRM의 WD를 행렬 WD와 함께 바꾸지 않는다.
- `--optimizer-audit <새 JSONL>`는 실제 LR/WD, skip/applied, 선택 행렬의 gradient RMS·실제 update RMS·weight RMS를 기록한다. 이름 순서에서 고르게 고른 최대 8개 행렬이므로 전체 행렬 분포라고 부르지 않는다.
- 매 update LR history는 A09에서 사용할 수 있다. 선택 행렬 snapshot은 `--optimizer-audit-every` 간격이며 CPU 복사/계측 시간은 학습 속도에 섞이므로 성능 측정 팔과 분리한다.
- 원본에서 Muon optimizer state가 checkpoint에 저장·복구되지 않던 경로도 정적 확인했다. 새 checkpoint에는 opt_muon을 저장한다. 해당 state가 없는 옛 Muon checkpoint의 정확한 resume를 거절한다. 이는 과거 **처음부터 수행한 full run**의 무효 사유가 아니다.

### 기존 학습 명령에 추가할 인자

| 팔 | 추가 인자 |
|---|---|
| AdamW / matrix WD .1 | `--optimizer adamw --matrix-weight-decay 0.1` |
| AdamW / matrix WD 0 | `--optimizer adamw --matrix-weight-decay 0` |
| Muon / matrix WD .1 | `--optimizer muon --muon-lr-mult 15 --matrix-weight-decay 0.1` |
| Muon / matrix WD 0 | `--optimizer muon --muon-lr-mult 15 --matrix-weight-decay 0` |

네 팔 전부 재학습하라는 표가 아니다. 기존 두 팔이 부모·pool·step·seed·anneal·schedule까지 맞으면 **빠진 두 팔만** 후보가 된다. 새 tag를 사용하고 원래 checkpoint 이름을 출력 대상으로 재사용하지 않는다.

RMS 진단을 원하는 별도 짧은 팔에 `--optimizer-audit runs/audit_20260909/A08_updates.jsonl --optimizer-audit-every 50`을 추가한다. audited resume는 step=0부터 연속 history 규약 때문에 거절한다. 장시간 본학습을 시작하기 전에 사용자가 작은 정상 update 및 Muon save/resume 검증을 수행해야 한다.

### 해석과 남는 조건부 실험

동일 WD 숫자도 LR이 다르면 누적 수축량이 다르다. LR×WD의 실제 궤적을 확인한 뒤, 레시피 승리와 optimizer 단독 효과를 나눠 쓴다. raw gradient norm 일치는 업데이트 정렬이 아니다.

P005b의 QK gain은 fixed 8 대 learnable 8을 먼저 비교해야 한다. fixed 8 대 learnable 20은 초기값과 학습 가능성이 함께 바뀐다. QK gain 자체의 이득은 현재 확정되지 않아 이번 묶음에서는 모델 구조를 바꾸지 않았다. 해당 분기를 선택할 때 초기값·적용 위치·WD·공유 여부를 별도 확정한다.

**인수 기준:** optimizer 그룹에 같은 파라미터가 두 번 들어가지 않음, embedding/LRM WD 보존, 실제 행렬 update 계측, Muon optimizer state 복구. 새 옵션을 쓰지 않는 경로의 회귀 검증도 필요하다. 이번 작업에서는 실행하지 않았다.

### 포함 파일

- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a08_optimizer.py`
- `tinylm/audit_io.py`
- `tinylm/cli.py`
- `tinylm/eval/audit_io.py`
- `tinylm/train/optimizer_audit.py`
- `tinylm/train/trainer.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
