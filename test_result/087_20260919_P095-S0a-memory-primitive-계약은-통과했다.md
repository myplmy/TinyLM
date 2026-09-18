# 결과 087 — **P095 S0a causal memory primitive 계약은 통과했다**

> **계획**: [P095 — Scout + 1 MiB LTM의 기능적 학습가능성](../test_plan/P095_Scout-1MiB-LTM-학습가능성.md) **S0aL**  
> **로그**: `test_result/087_log_20260919_P095_S0aL_causal_memory_log_recovery.txt`  
> **실행 파일**: `run_P095_S0aL_causal_memory_log_recovery-done.sh`  
> **실행**: 2026-09-19 · CPU 합성 fixture · exit 0 · 학습 0

## 1. 측정 결과

| 계약 | 관측 | 판정 |
|---|---|---|
| read-before-write | 동일 step write를 즉시 read하지 않음 | PASS |
| prefix invariance | 미래 write 변경이 prefix 출력에 영향 없음 | PASS |
| history dependence | 과거 memory 내용 변경에 후속 read가 반응 | PASS |
| logical payload | 1,048,576 bytes | PASS |
| backward | key/value gradient 존재·finite | PASS |
| 종료코드 | 0 | PASS |

이는 기존 콘솔 PASS의 로그 복구 단계이며 새 과학 단계가 아니다. 학습 JSON은 없다.

## 2. 해석과 한계

- 독립 `CausalScoutMemory` primitive의 인과 순서, 기본 memory 의존성, 논리 payload,
  자동미분 경로는 보존 로그에서 통과했다.
- 단, 로그가 PASS 한 줄만 남겨 실제 payload bytes, read 크기, attention 선택, gradient norm을
  수치로 복원할 수 없다. 그 세부값을 본 결과에 추정해 추가하지 않았다.
- Transformer 통합, fact-context 제거, oracle 누출 차단, metadata/scratch/RSS,
  latency, memory 학습가능성, 일반 LM 품질은 모두 `NOT_RUN`이다.

<!-- TINYLM_CONDITION_SIGNATURE_V1 id=P095-S0aL-causal-memory -->
| field | arm_a | arm_b | evidence |
| --- | --- | --- | --- |
| pool_id | N/A synthetic | N/A synthetic | 학습 없음 |
| actual_pool_tokens | N/A synthetic | N/A synthetic | 학습 없음 |
| pool_override | N/A synthetic | N/A synthetic | 학습 없음 |
| steps | N/A diagnostic | N/A diagnostic | CPU fixture |
| micro_bs | N/A diagnostic | N/A diagnostic | CPU fixture |
| accum | N/A diagnostic | N/A diagnostic | CPU fixture |
| seq | N/A diagnostic | N/A diagnostic | CPU fixture |
| actual_draw_tokens | N/A diagnostic | N/A diagnostic | 학습 없음 |
| sampler_with_replacement | N/A diagnostic | N/A diagnostic | 학습 없음 |
| expected_unique_tokens | N/A diagnostic | N/A diagnostic | 학습 없음 |
| sequential_epoch_claim | false | false | 학습 없음 |
| scheduler | N/A diagnostic | N/A diagnostic | 학습 없음 |
| warmup | N/A diagnostic | N/A diagnostic | 학습 없음 |
| anneal_start | N/A diagnostic | N/A diagnostic | 학습 없음 |
| decay_fraction | N/A diagnostic | N/A diagnostic | 학습 없음 |
| absolute_schedule_horizon | N/A diagnostic | N/A diagnostic | 학습 없음 |
| train_language_expected | N/A synthetic | N/A synthetic | 자연어 학습 없음 |
| train_language_observed | N/A synthetic | N/A synthetic | 자연어 학습 없음 |
| eval_dataset | synthetic causal-memory fixture | synthetic causal-memory fixture | 로그 |
| eval_language | N/A diagnostic | N/A diagnostic | 자연어 평가 없음 |
| tokenizer | N/A diagnostic | N/A diagnostic | 토큰화 없음 |
| grad_ckpt | false | false | 모델 학습 없음 |
| observed_contract | causal order,prefix invariance,history dependence,1MiB,backward | causal order,prefix invariance,history dependence,1MiB,backward | 로그 |
| comparator_tag | P095_S0aL | P095_S0aL | 단일 계약 진단 |
| matched_axes | pool_id,actual_pool_tokens,pool_override,steps,micro_bs,accum,seq,actual_draw_tokens,sampler_with_replacement,expected_unique_tokens,sequential_epoch_claim,scheduler,warmup,anneal_start,decay_fraction,absolute_schedule_horizon,train_language_expected,train_language_observed,eval_dataset,eval_language,tokenizer,grad_ckpt,observed_contract | same | 단일 관측을 양쪽 셀에 기록 |
| changed_axes | NONE | NONE | 비교 실험 아님 |
| unmeasured_axes | NONE | NONE | 미실행 주장은 별도 열거 |
| not_run_claims | TRANSFORMER_INTEGRATION,LEAK_FIXTURE,PHYSICAL_MEMORY,LATENCY,TRAINING,QUALITY | TRANSFORMER_INTEGRATION,LEAK_FIXTURE,PHYSICAL_MEMORY,LATENCY,TRAINING,QUALITY | primitive 한정 |
| permitted_claim | DESCRIPTIVE_ONLY | DESCRIPTIVE_ONLY | primitive 계약 통과만 주장 |
<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->

## 3. 후속

S0b에서 Transformer 통합·reset·determinism·physical byte·latency와 context shortcut/oracle
누출 fixture를 선행해야 한다. S0aL PASS만으로 memory 학습이나 1 MiB 배포
비용을 통과한 것으로 주장하지 않는다.
