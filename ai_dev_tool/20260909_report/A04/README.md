# A04 — paired 통계와 family 단위 불확실성

우선순위: **P0** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A04](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

같은 300문항을 여러 모델/seed에서 반복 채점한 행을 모두 독립 표본으로 합산하지 않는다. v2.8에서 완료된 감사와 아직 부족한 범위를 구분한다.

### 구현 및 적용

`analyze_paired_records.py`와 `paired_records.py`를 제공한다. 한쪽당 한 checkpoint, 공통 ID, 동일 원문/정답/채점 규약을 요구한다. 중복 ID는 실패다. 정답률 차이에 exact McNemar, 연속 paired 차이에 SD/SE와 참고용 정규근사 CI, 명시한 가족에 cluster bootstrap을 제공한다. n=1의 SE는 0으로 만들지 않는다.

```powershell
python scripts/analyze_paired_records.py --a "$AuditScoresA" --b "$AuditScoresB" --model-a candidate --model-b reference --task stage1_heldout --metric correct --family-map "$AuditFamilyMap" --draws 2000 --out runs/audit_20260909/A04_paired.json
```

family map은 `{"stage1_heldout:E-001":"검수한_원문가족", ...}`처럼 **출력 ID 전체**를 key로 쓰는 JSON이다. relation/task 이름을 독립 source family로 자동 간주하지 않는다. 하나의 가족만 있으면 가족 수준 일반화의 CI를 만들 수 없다.

### 추가 코드 없이 해야 할 실험 개선

- seed마다 paired 효과를 별도로 낸 뒤 seed 간 방향·크기를 보고한다. seed 수 2개를 충분한 학습 분산 추정으로 단정하지 않는다.
- 사전 지정한 주 비교/주 지표를 우선 판정한다. 많은 후보 중 최선을 고른 탐색 결과와 독립 확인 결과를 구분한다.
- v2.8의 4,500/18,000 전체 13-gram 감사와, 일부 400문항 첫 window의 8-token 감사를 같은 전수 검사로 서술하지 않는다. 완료한 범위를 다시 의무 gate로 만들지 않는다.
- 의미 정답성과 독립 source family는 사람이 검수한 표본 및 원장에 연결한다. 문자열 중복 검사 통과로 의미 정답을 인증하지 않는다.
- 통계 유의성과 실용적 개선은 별개다. 주 효과/CI, 전체 요청 수·공통 채점 수·한쪽 전용 ID를 함께 보고한다.

### 완료 기준

질문 수준 불확실성과 학습 seed 불확실성을 분리할 수 있어야 한다. 동일 문항 반복으로 N만 부풀린 유의성은 폐기하되, 모델 자체나 정상적으로 수행한 학습을 폐기하지 않는다.

### 포함 파일

- `scripts/analyze_paired_records.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a03_a04_paired.py`
- `tinylm/audit_io.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/paired_records.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
