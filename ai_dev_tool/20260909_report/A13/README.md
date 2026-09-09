# A13 — P082의 N_REF 보존과 검증된 text KD

우선순위: **P1** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A13](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

기존 α 격자, 부모×KD 대조, Qwen/Gemma full 비교는 반복하지 않는다. A05 Fresh SFT 기준을 만든 뒤 학생 tokenizer를 유지하는 정답/짧은 이유 text KD를 먼저 비교한다.

### 제공한 코드

1. `generate_teacher_responses.py`: **특정 local HF snapshot**과 native chat template로 train prompt만 생성한다. 마지막 정본 assistant 답을 교사 입력에서 제거한다. 외부 API/자동 다운로드를 사용하지 않는다. native template이 없는 base 모델을 임의로 instruction teacher로 바꾸지 않는다.
2. `build_kd_text_pairs.py`: 외부에서 검증한 응답만 선택하고 같은 accepted ID의 N_REF/T_VERIFIED를 함께 생성한다. 정본 전체와 교사 선별 일부를 비교하지 않게 한다.
3. A05의 계측/SFT/평가기, A04 paired 분석기를 함께 포함한다. logit KD·on-policy rollout 엔진을 새로 구현한 것은 아니다.

### 수동 명령

```powershell
python scripts/generate_teacher_responses.py --hf-model "$AuditTeacherSnapshot" --train datasets/TinyDataset/SFT/train/sft_fresh_v1_train_1000.canonical.jsonl --max-new 128 --max-input 1024 --out-jsonl runs/audit_20260909/A13_teacher_raw.jsonl
python scripts/build_kd_text_pairs.py --reference-train datasets/TinyDataset/SFT/train/sft_fresh_v1_train_1000.canonical.jsonl --teacher-responses runs/audit_20260909/A13_teacher_raw.jsonl --verification "$AuditVerification" --tokenizer "$AuditTokenizer" --serializer chatml --seq 1024 --max-response-tokens 128 --out-dir runs/audit_20260909/A13_pairs
```

두 명령 사이에 **응답의 의미 정답/짧은 이유를 검증**해야 한다. 생성기가 자기 응답을 correct=true로 인증하지 않는다. 이 단계의 산출물 예:

```json
{"id":"SFTF-V1-000001","response_sha256":"생성 파일의 response_sha256","reference_sha256":"생성 파일의 reference_sha256","correct":true,"verifier":"검수자 또는 고정된 검증기 버전","rationale":"자료의 분류 조건과 답/이유가 일치함"}
```

verification은 JSONL이다. SHA가 다른 답/원문에 재사용되면 제외한다. manifest 존재는 의미 검증의 증명이 아니므로 verifier의 실제 검수 원장을 함께 보존한다.

### 선택/학습 계약

모든 입력은 meta.split=train이어야 한다. 틀리거나 미검증·빈 답·너무 긴 답·문맥 초과는 제외한다. 여러 검증 정답 중 학생 tokenizer에서 짧은 답을 선택한다. 학생 NLL로 최적 응답을 선택했다고 주장하지 않는다.

N_REF.jsonl과 T_VERIFIED.jsonl은 같은 ID 순서이며 train/reference/응답 SHA와 실제 serialized/loss token을 contract.json에 기록한다. 두 팔의 token 수는 자동으로 같아지지 않는다. 같은 ID/step 효과와 같은 loss-token/시간 효과를 구분한다. 전체 N_REF 팔은 선별 효과 확인용 별도 대조로만 쓴다.

현재 Fresh metadata의 exact/형식 불일치는 A05의 reference 감사로 먼저 처리한다. pairing 도구는 정본 답이 자체 규칙에 실패하면 중단한다. train grading을 수정해야 한다면 검수한 별도 train 사본을 준비하고 원본과 provenance를 보존한다.

### KD 인과·비용 정정

- online skip KD의 active fraction이 f이고 α가 고정이면 단순 step 평균 계수는 CE=1−fα, KL=fα이다. α=.5/k4라면 .875/.125. 가변 token/mask/skip이면 실제 적용량으로 다시 집계한다.
- T², KL 방향, token/assistant mask, teacher/candidate 검증 탈락률, 학생 update를 기록한다. 원본 logit KD를 단순 위치 KL로 다른 tokenizer에 붙이지 않는다.
- 총 비용은 교사 생성+검증+학생 학습+평가이며, 실패/탈락 팔을 포함한 실제 비용과 후속 가지의 조건부 예상 비용을 분리한다. P082의 52/139–160/191–280시간을 하나의 같은 실험 합계로 사용하지 않는다.
- 교사 우위가 확인되지 않으면 큰 교사나 assistant를 자동 추가하지 않는다. supervised 기준이 유효해진 뒤에만 학생 오류에 대한 검증된 교정 text를 소량 추가하는 on-policy 팔을 고려한다.

**인수 기준:** 같은 accepted ID의 N_REF 대비 개선, source family 분리, 일반 한국어/영어 유지, 교사 비용 포함 효율. 지금 제공한 코드는 준비 경로이며 KD의 실제 성공이나 소형 학생의 지능 향상을 입증한 결과가 아니다.

### 포함 파일

- `scripts/analyze_paired_records.py`
- `scripts/build_kd_text_pairs.py`
- `scripts/diag_dataset_tokens.py`
- `scripts/eval_sft.py`
- `scripts/generate_teacher_responses.py`
- `scripts/train_sft.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a05_supervision.py`
- `tests/report_20260909/test_a13_teacher.py`
- `tinylm/audit_io.py`
- `tinylm/chat/serialize.py`
- `tinylm/chat/supervision.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/model_adapter.py`
- `tinylm/eval/paired_records.py`
- `tinylm/eval/sft_grading.py`
- `tinylm/model/checkpoint_io.py`
- `tinylm/train/sft.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
