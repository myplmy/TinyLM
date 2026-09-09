# A10 — attention sink의 causal null과 방문별 계측

우선순위: **P1** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A10](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

기존 union 중복 수정은 보존한다. 현재 교정할 부분은 모든 query 위치의 평균 mass를 마지막 query의 S/T와 비교한 기준식이다.

### 코드 수정안

`causal_null(T,S) = sum(min(S,t)/t for t=1..T)/T`를 사용한다. T=1024, S=4이면 약 2.5101%다. 전체 query와 tail query를 나누고 각각 같은 위치 집합의 sink/window/union null을 기록한다.

모델의 실제 Attention.last_probs를 forward hook에서 **매 방문마다** 읽고 즉시 해제한다. 재귀/공유 모듈의 마지막 방문만 남기는 방식을 피한다. RoPE/QK-norm/GQA를 도구 밖에서 다시 구현하지 않는다. 미래 위치의 mass·확률 합 오류는 실패다.

```powershell
python scripts/diag_attention_sink.py --checkpoint "$AuditCheckpoint" --val-bin data_cache/ko-en_300000000/val.bin --dtype uint16 --seq 1024 --sink 4 --window 256 --crops 4 --seed 99 --device cpu --out runs/audit_20260909/A10_sink.json
```

bin과 dtype는 실제 checkpoint의 평가 자료/메타데이터에 맞춰야 한다. 예시 bin이 더 큰 학습 stream에 포함된 것으로 확인된 조건이라면 **독립 검증용 bin**으로 바꾼다. 이 도구는 prepare/캐시 생성을 호출하지 않는다. 기존 --models/--preset 배치 대신 위 명시적 checkpoint 명령을 사용한다.

### 인수 기준과 실험 개선

균등 causal 확률을 주면 observed와 같은 query의 null이 일치해야 한다. 약 2% mass를 0.39%와 비교해 5–7배 enrichment라고 판정하지 않는다.

진단은 attention 확률의 어휘/위치 통계다. 물리적 KV 삭제의 기능 검증이 아니며 5%/10% 같은 임의 경계로 cache 압축을 채택하지 않는다. 긴 문맥이 실제 제품 요구일 때만 full KV와 sink+window의 처음/중간/끝 정보 회수·생성을 비교한다. 현재 본학습 재실행은 필요 없다.

### 포함 파일

- `scripts/diag_attention_sink.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a10_attention.py`
- `tinylm/audit_io.py`
- `tinylm/eval/attention_stats.py`
- `tinylm/eval/audit_io.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
