# A06 — 동일 배포 모델의 품질·실제 KV·메모리·속도

우선순위: **P0** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A06](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

현재 작은 LUT 모델의 메모리와 큰 int8 unpack-cache 모델의 속도를 같은 행에 넣을 수 없다. 끝 시점 RSS는 실행 중 최고점도, 엔진을 제외한 모델 메모리도 아니다.

### 코드 수정안

`eval_deployment_artifact.py`가 한 번 변환한 **같은 모델 객체**로 다음을 수행한다.

1. checkpoint/tokenizer/code hash, cfg, 실제 초기 tensor 값 hash, visit schedule과 변환 옵션으로 artifact ID 생성.
2. A02 manifest를 적용한 clean bpb와, 실제 KV dtype을 쓰는 cached held-out 선택 평가.
3. 같은 객체의 대표 prompt 생성, cache/uncached 생성 ID 대조, prefill/decode 시간.
4. Parameter/Buffer뿐 아니라 plain tensor 속성과 실제 KV를 storage 단위로 중복 제거해 합산. 구/신 cache가 반환 경계에서 동시에 살아 있는 양도 기록.
5. 실행 구간 RSS 표본 최고점과 CUDA allocator peak를 따로 기록.

`transformer.forward(logits_last_only=True)`와 `sample(..., logits_last_only=True)`는 **추론에서 마지막 위치의 head만 계산하는 선택 기능**이다. 기본값 False는 종전 전체 로짓 경로다. A06의 `--last-head`에서만 켠다. 학습에서는 거절하며, 전체 head와 마지막 로짓/KV가 맞는 작은 회귀 테스트를 제공했다. 이 옵션으로 prefill의 전체 어휘 로짓 저장을 줄일 수 있으나, 실제 메모리/속도 이득은 미실측이다.

### 입력과 명령

`--prompts`는 대표 한국어/영어/정보 회수 맥락의 `id/text` JSONL이다. 최대 context 길이를 만들 충분히 긴 실제 prompt가 필요하다. 문자열을 무의미하게 반복해 길이를 채우지 않는다. prompt 길이는 context−max_new+1로 선택해 마지막 cached forward에서 요청 context에 도달한다.

짧은 경로 확인 예:

```powershell
python scripts/eval_deployment_artifact.py --checkpoint "$AuditCheckpoint" --tokenizer "$AuditTokenizer" --tag candidate_lut --out-dir runs/audit_20260909/A06_lut_pilot --device cpu --drop-latent --lut --emb-quant int8 --emb-chunk 4096 --lut-out-chunk 256 --kv-dtype bf16 --contexts 256 1024 --max-new 32 --prompts "$AuditPrompts" --quality-n 20 --skip-bpb --check-no-cache --last-head
```

최종 표를 만들 때는 `--quality-n 0`으로 바꾸고 `--skip-bpb`를 제거한 뒤 `--bpb-exclusion-manifest <A02 manifest>`를 넣는다. 기본 SQuAD 4,000문서와 manifest corpus가 일치해야 한다. 별도 한국어 원문은 `--bpb-text-jsonl`로 지정하고 그 corpus용 manifest를 사용한다.

### 필요한 비교

같은 checkpoint에서 원 배포 경로 → LUT/per-row → embedding 양자화 → last-head를 한 요인씩 바꾼다. 출력 폴더와 artifact ID는 각각 달라야 한다. int8 unpack-cache는 별도 비용점으로 남긴다. 처음부터 모든 조합을 학습할 필요는 없다.

캐시 품질은 cached MC에서 확인하고, uncached bpb를 KV 정밀도의 품질 검증으로 오해하지 않는다. 두 실행의 quality.jsonl/bpb.jsonl은 A04 분석기로 같은 문항을 비교할 수 있다. 지표별 채점 profile을 맞춘다.

### 판정 범위와 남는 작업

- `artifact.json`은 **현재 Python 구현에서 재구성한 in-memory packed 모델**의 증거다. 독립 C/C++ 산출물 포맷/exporter를 완성했다는 뜻은 아니다.
- 모델+실제 KV+입출력의 **forward 반환 경계** 최고점은 측정한다. 그 안에서 생성·소멸한 CPU workspace 전체의 최고점은 포괄하지 못한다. 따라서 경계 합이 40MiB를 넘으면 초과 근거가 되지만, 아래라고 PASS를 발급하지 않는다.
- RSS는 엔진·allocator·계측을 포함하고 표본 사이 peak를 놓칠 수 있다. CUDA peak도 선택한 uncached 대조를 포함할 수 있어 필드에 명시한다. 3차 리뷰의 엔진 제외 예산을 전체 Python RSS≤40MiB로 바꾸지 않는다.
- prefill/decode forward 속도는 sampling/계측을 제외한다. 전체 instrumented wall 속도도 병기한다. 실제 제품 속도라고 그대로 채택하지 않는다.
- quality forward 메모리와 cached generation 메모리를 분리하며, 40MiB 경계 판정은 generation 구간으로 한다.
- workspace가 남은 병목이면 native 실행기 allocator 계측 또는 그 실행기의 workspace 상한 계약이 필요하다. tiled prefill/영구 버퍼 재사용은 그 결과를 보고 설계한다. 불필요한 새 실행기 전체를 이 패키지에 임의 추가하지 않았다.

**인수 기준:** 같은 artifact의 품질·상주·workspace의 확인 범위·속도를 한 행으로 작성하고, 40MiB 충족 여부가 불명확하면 불명확으로 남긴다. 기존 본학습 전량 재실행은 하지 않는다.

### 포함 파일

- `scripts/analyze_paired_records.py`
- `scripts/common_bpb.py`
- `scripts/eval_deployment_artifact.py`
- `scripts/fetch_bench_data.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a06_runtime.py`
- `tinylm/audit_io.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/bpb_corpus.py`
- `tinylm/eval/heldout.py`
- `tinylm/eval/model_adapter.py`
- `tinylm/eval/paired_records.py`
- `tinylm/eval/runtime_audit.py`
- `tinylm/infer/generate.py`
- `tinylm/model/transformer.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
