# A15 — 반올림 일치와 연산·gradient·update 등가성 분리

우선순위: **조건부** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A15](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

인쇄된 손실 네 자리가 같다는 사실로 bitwise equality를 주장하지 않는다. 기존 full 학습 성공과 청킹의 유효 결과를 유지하면서, **새로 연결한 경로**의 등가성을 확인하는 도구를 제공한다.

### 신규 도구

`check_training_equivalence.py`는 같은 checkpoint와 작은 train-only canonical batch를 두 번 로드한다. 모델 cfg/입력 hash/tokenizer/seed를 기록하고 forward, assistant mask CE, 모든 존재하는 gradient, fresh optimizer 1 update 후 parameter를 비교한다. Adam moment 상태도 별도로 보고한다.

비교 분기는 ce-chunk, grad-checkpoint, opt-fp32c, opt-bf16이다. 합성 난수로 모델의 절대 품질을 재지 않고 실제 작은 train 예제를 사용한다. 허용 오차 내 일치와 tensor byte 일치를 별도 표시한다. tensor byte 비교는 부호가 다른 0도 같은 bit라고 하지 않는다.

```powershell
python scripts/check_training_equivalence.py --checkpoint "$AuditCheckpoint" --records "$AuditSmallTrain" --tokenizer "$AuditTokenizer" --serializer chatml --seq 128 --max-records 2 --variant ce-chunk --ce-chunk 17 --device cpu --atol 0.000001 --rtol 0.00001 --out runs/audit_20260909/A15_ce_chunk.json
```

예제는 **이미 분리한 짧은 train 자료 사본**이다. max-length를 넘기면 자르지 않고 실패한다. 단계마다 새 출력 경로를 쓰며 실제 dtype/목적에 맞춘 허용오차를 사전에 정한다.

### 정확한 검증 범위

- CE chunk는 dense CE와 같은 선택 label의 손실/gradient를 비교한다.
- gradient checkpoint는 동일 cfg의 해당 옵션만 바꾼다.
- optimizer 비교는 fresh state 1 update다. BF16 moment는 이후 update에서 차이가 커질 수 있으므로 state 차이도 읽어야 한다. 일회 통과가 장기 학습 동등성은 아니다.
- 기본 CPU/autocast off다. CUDA kernel/autocast/외부 teacher의 전체 조합을 검증한 도구가 아니다.
- 측정 tensor 외 optimizer scalar step/저장 layout까지 byte 동일하다고 선언하지 않는다.
- true/false 결과와 관계없이 원래 checkpoint는 저장·수정하지 않고 JSON만 새로 쓴다.

### 사용자의 인수 절차

A05 mask 테스트와 이 작은 비교가 통과한 뒤 실제 GPU의 적정 microbatch에서 확인한다. CUDA/autocast/teacher 경로의 새 최적화를 선택할 때는 그 정확한 조건의 별도 대조가 필요하다. 기존 완료 학습 전량을 다시 돌리는 사유로 확대하지 않는다.

### 포함 파일

- `scripts/check_training_equivalence.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a15_equivalence.py`
- `tinylm/audit_io.py`
- `tinylm/chat/serialize.py`
- `tinylm/chat/supervision.py`
- `tinylm/eval/audit_io.py`
- `tinylm/model/checkpoint_io.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
