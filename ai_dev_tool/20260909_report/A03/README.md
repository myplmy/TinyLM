# A03 — 문항 ID, 점수 이름, decision margin과 HF 평가

우선순위: **P0** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A03](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

P069/P085에서 수행한 기존 평가를 없던 것으로 보지 않는다. 수정 대상은 모델마다 달라진 skip 이후의 위치 기반 짝짓기, 평균 margin의 과도한 해석, 공식 점수와 로컬 점수의 혼동이다.

### 코드 수정안

- 모든 문항에 ID·item/dataset SHA·checkpoint/tokenizer provenance·skip 사유를 남긴다. paired는 공통 ID를 join하고 내용/정답/채점 규약이 같은지 확인한다.
- `mean_wrong_margin`과 `best_wrong_margin`을 분리한다. 가장 가까운 오답보다 gold 비용이 작을 때 best margin이 양수다.
- 선택비용에 대한 softmax NLL/Brier를 추가하되 calibrated confidence라고 부르지 않는다. 기존 PMI는 **token 평균 NLL의 차**라는 로컬 규약으로 명명한다.
- 자체 평균 우도 정확도는 `local_acc_raw_mean_nll`로 기록한다. 공식 acc_norm 명칭과 기존 W&B v1/TSV를 덮어쓰는 방식을 제거하고, 명시적 업로드는 bench_v2 namespace를 사용한다.
- 특정 local HF snapshot을 실제 tokenizer와 함께 읽는다. 같은 어휘 크기는 tokenizer 동일성의 증거가 아니다. 서로 다른 tokenizer의 gold CE paired 비교를 거절한다.
- BFCL 함수 목록의 조용한 1,500자 절단을 제거했다. 문맥 초과는 기록한다. IFEval은 부분 규칙, HumanEval/BFCL은 syntax/JSON parse이며 공식 pass@1/AST 평가가 아니다.

### 사용 예

```powershell
python scripts/eval_bench_suite.py --task hellaswag --n 0 --models candidate reference --checkpoint "candidate=$AuditCheckpoint" "reference=$AuditReferenceCheckpoint" --tokenizer "candidate=$AuditTokenizer" "reference=$AuditTokenizer" --out-jsonl runs/audit_20260909/A03_hellaswag.jsonl
python scripts/analyze_paired_records.py --a runs/audit_20260909/A03_hellaswag.jsonl --b runs/audit_20260909/A03_hellaswag.jsonl --model-a candidate --model-b reference --task hellaswag --metric best_wrong_margin --out runs/audit_20260909/A03_margin.json
```

HF 비교는 `--models candidate teacher --checkpoint "candidate=..." --hf-model "teacher=<local snapshot>" --tokenizer "candidate=..."`로 지정한다. 별도 인터넷 다운로드나 API 호출은 하지 않는다. HF 모델은 내장 정본 chat 평가를 대신하지 않는 로컬 likelihood 대조다.

### 인수 기준

모델 한쪽만 skip한 문항이 다른 ID와 묶이지 않아야 한다. 평균 margin이 양수여도 최근접 오답 때문에 오답인 사례를 구분해야 한다. 원점수에 ID/hash가 없으면 옛 배열을 추측해서 수선하지 않고 해당 평가만 다시 수행한다. 과거 본학습의 폐기 사유로 확대하지 않는다.

생성 파일에는 원 prompt와 completion/task_id가 남는다. 공식 harness 실행·생성 코드 실행은 이 패키지가 수행하지 않는다. 공식 지표가 필요하면 이 자료를 해당 harness의 실제 버전/형식에 맞춰 별도 검증해야 한다.

### 포함 파일

- `scripts/analyze_paired_records.py`
- `scripts/eval_bench_suite.py`
- `scripts/fetch_bench_data.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a03_a04_paired.py`
- `tinylm/audit_io.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/heldout.py`
- `tinylm/eval/model_adapter.py`
- `tinylm/eval/paired_records.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
