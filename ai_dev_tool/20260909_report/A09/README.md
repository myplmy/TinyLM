# A09 — LRM의 실제 WD와 checkpoint 시점 진단

우선순위: **P1** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A09](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

vector LRM full 학습과 ctrl/vector paired 후속은 완료된 것으로 보존한다. WD=0인 실행에 .01 누적 감쇠를 적용한 “13.1배” 해석을 고치는 것이 현재 조치다.

### 교체본 동작

cfg.mlp_lrm_wd와 선택 checkpoint의 step을 읽고, 학습 JSON의 WD가 다르면 거절한다. compile의 선두 _orig_mod. prefix를 정규화하되 충돌은 실패다. tag가 여러 checkpoint에 해당하면 첫 파일을 임의 선택하지 않는다.

WD=0의 WD-only 배율은 1이다. 양수 WD의 정확한 보정은 `step/applied/lrm_lr/lrm_weight_decay`가 있는 LR history와 초기값 1 근거를 요구한다. planned steps를 best checkpoint의 실제 update 수로 대신하지 않는다. 정보가 없으면 raw 값은 출력하지만 역보정은 unresolved/exit 2다.

```powershell
python scripts/diag_lrm_values.py --ckpt "$AuditCheckpoint" --out runs/audit_20260909/A09_vector.json
```

새 A08 history로 양수 WD를 진단할 경우:

```powershell
python scripts/diag_lrm_values.py --ckpt "$AuditCheckpoint" --lr-history "$AuditLrHistory" --initial-one --out runs/audit_20260909/A09_history.json
```

`--initial-one`은 history 시작 때 승수가 1이고 중간 재초기화가 없었다는 **실험 사실의 명시**다. 이식/재개 초기값이 다르면 사용하지 않는다. WD=0 raw 이동량도 초기값이 1일 때의 해석이다.

### 판정 정정

- max|s−1|, WD-only 배율 대비 변화, 원소 수/평균/최솟값/최댓값을 분리한다.
- WD-only 비율은 optimizer 상호작용을 제거한 순수 gradient 인과 기여가 아니다.
- 이동량 1%를 넘었다고 지능 향상 PASS를 주거나, 못 넘었다고 미학습/기존 paired 결론 철회를 자동 선언하지 않는다.
- `check_lr_factor_sync.py`도 함께 교체한다. LR 복제가 없어졌으므로, 옛 함수 두 개의 일치를 강제하는 gate 대신 cfg/history 경로 연결을 검사한다. 수치 검증은 별도 회귀 테스트가 담당한다. 기존 check_static_all 설명 문자열의 “복제 1,992점”은 이 교체본에는 적용되지 않는다.

**인수 기준:** WD 0 배율=1, skip step 제외, checkpoint 이후 history 제외, 누락 history의 무판정. vector 본학습은 다시 돌리지 않는다. 양수 WD의 옛 불완전 history를 이번 도구가 만들어 냈다고 읽지 않는다.

### 포함 파일

- `scripts/check_lr_factor_sync.py`
- `scripts/diag_lrm_values.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a09_lrm.py`
- `tinylm/audit_io.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/lrm_diagnostics.py`
- `tinylm/model/checkpoint_io.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
