# A01 — held-out 버전 고정과 v2.8 schema 연결

우선순위: **P0** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A01](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

기존 v2.7 평가 결과는 유지한다. 수정 대상은 새 자료 선택·로딩·캐시의 계약이다. v2.8을 자동 최신 검색이나 300건 전용 파일 패턴에 얹으면 잘못된 파일을 읽거나 평가 전에 실패할 수 있다.

### 코드 수정안

- `tinylm/eval/heldout.py`: v2.7=300건, v2.8=4,500건을 명시적으로 등록한다. 두 schema를 공통 ctx/choices/gold로 연결하고 ID·정답 범위·선택지 중복을 검사한다.
- `scripts/fetch_bench_data.py`: 선택 버전의 cache와 source SHA를 묶어 저장·확인한다. 기존 `stage1_heldout.jsonl`을 덮어쓰거나 자동 사용하지 않는다.
- `scripts/eval_bench_suite.py`: 같은 버전 로더를 사용한다. A03의 ID/채점 수정까지 포함한 동일 통합 파일이다.
- v2.7의 기존 D1/D6 검사를 유지한다. v2.8의 schema 통과를 의미 정답성 PASS로 표시하지 않는다.

### 사용자가 실행할 순서

프로젝트 루트에서 필요한 버전 하나를 선택한다.

```powershell
python scripts/fetch_bench_data.py --only stage1_heldout --heldout-version 2.7
python scripts/eval_bench_suite.py --task stage1_heldout --heldout-version 2.7 --n 0 --models candidate --checkpoint "candidate=$AuditCheckpoint" --tokenizer "candidate=$AuditTokenizer" --out-jsonl runs/audit_20260909/A01_candidate_v27.jsonl
```

v2.8을 채택할 때는 두 명령의 버전을 함께 2.8로 바꾼다. 원본의 SHA를 고정하려면 두 명령에 `--heldout-source-sha256 <SHA256>`도 넣는다. 이 예시는 local held-out을 읽으며 다른 benchmark 다운로드를 요청하지 않는다.

### 인수 기준과 남는 조치

- 선택 버전의 예상 건수, source/cache hash, 고유 ID가 일치해야 한다.
- 메타데이터 없는 cache, source 변경, 잘못된 gold, 중복 선택지는 실패해야 한다. 반쯤 생성된 cache 파일을 자동 복구·덮어쓰기하지 않는다.
- v2.8 의미 검수·source family 감사의 충분성은 A04에서 판단한다. 모델 checkpoint 선택에 금지된 평가셋을 tuning용으로 쓰지 않는다.
- 본학습 재실행은 필요 없다. 승인된 평가 버전으로 필요한 최종 후보의 평가만 갱신한다.

### 포함 파일

- `scripts/eval_bench_suite.py`
- `scripts/fetch_bench_data.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a01_heldout.py`
- `tinylm/audit_io.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/heldout.py`
- `tinylm/eval/model_adapter.py`
- `tinylm/eval/paired_records.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
