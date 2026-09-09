# A11 — 실제 dense MLP와 정본 그룹으로 집약 진단

우선순위: **P1** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A11](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

과거 MLP 0개에서 실패하도록 바뀐 것은 유효 측정의 완료가 아니다. 당시 0개의 원인이 prefix 하나였다고 확정하지 않고, 누락될 수 있는 경로를 함께 닫는다.

### 코드 수정안

- checkpoint 자체 cfg와 model state를 읽고 선두 compile prefix를 정규화한다.
- dense 부모임을 확인하고 `mid_mlps.0..n_middle−1` 및 gate/up/down projection을 명시적으로 확인한다.
- 학생 소속은 `config.mlp_group_members`에서 얻어 그룹별 member/key를 출력한다. 집약 소속과 forward 방문 순서를 같은 개념으로 간주하지 않는다.
- tensor를 층 수만큼 stack하지 않고 평균/단위벡터 합을 누적해 shrink ratio와 평균 pair cosine을 계산한다.
- 빈 그룹·누락 projection·shape 불일치·0 norm·측정 0개를 실패로 처리한다.

```powershell
python scripts/diag_group_agg.py --checkpoint "$AuditDenseParent" --group 8 --out runs/audit_20260909/A11_group8.json
python scripts/diag_group_agg.py --checkpoint "$AuditDenseParent" --student-checkpoint "$AuditStudentCheckpoint" --out runs/audit_20260909/A11_student_cfg.json
```

첫 예시의 group은 실제 비교하려는 학생 값으로 바꾼다. 불균등 경계는 `--split 4`처럼 명시한다. 두 번째는 실제 학생 cfg를 읽으며 group/split override를 함께 받지 않는다.

### 지원 범위와 남는 실험

현재 구현 범위는 **middle 깊이·투영 shape가 같은 dense→tied** 집약이다. 다른 깊이의 부모 이식이나 별도 cyclic 재배치 파일은 이 mapping이라고 추측하지 않고 거절한다. 현재 정본 init_utils의 같은 깊이 분기와 맞는 집합을 우선 재진단한다.

축소비는 초기 latent weight 기하이며 양자화 후 기능/학습 성능을 뜻하지 않는다. 결과를 보고 A1 평균과 A4 노름 보정 등 필요한 초기화 팔만 열어야 한다. 이 도구가 부모를 재학습하거나 집약 모델을 저장하지는 않는다.

**인수 기준:** 기대 그룹/projection의 전수 대응 및 같은/반대 방향 tensor의 수작업 대조. 유효 결과를 얻기 전에 본학습부터 다시 돌리지 않는다.

### 포함 파일

- `scripts/diag_group_agg.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a11_group.py`
- `tinylm/audit_io.py`
- `tinylm/eval/audit_io.py`
- `tinylm/model/checkpoint_io.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
