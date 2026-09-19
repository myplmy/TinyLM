# 결과 089 — P094는 P022C shadow evidence가 없어 residual을 열지 않았다

- **계획**: [P094](../test_plan/P094_Muon-저정밀-shadow-Q-R-residual과-동적정밀도.md)
- **로그**: `089_log_20260919_P094_R0_p022c_dependency_gate.txt`
- **실행 파일**: `run_P094_R0_p022c_dependency_gate-done.sh`
- **종료**: exit 8 · 사전등록 dependency HOLD · 실행 장애 아님

## 1. 관측

`runs/evidence/P022C_shadow_storage.json`이 존재하지 않았다. R0가 요구한
`schema=p022c.shadow-storage.v1`, `actual_packed=true`, `hidden_fp32_master=false`, 비어 있지 않은
`residual_need_signature` 중 어떤 것도 입증되지 않았으므로 fail-closed로 멈췄다.

## 2. 판정

- ✅ R0 dependency guard는 설계대로 작동했다.
- 🚫 P094 residual R1은 구현·실행하지 않는다.
- P022C C1 compute 음성은 shadow track의 failure signature가 아니다. 실제 packed low-shadow
  observer/storage 증거가 생기기 전까지 HOLD를 유지한다.

<!-- TINYLM_CONDITION_SIGNATURE_V1 id=P094-R0-dependency-hold -->
| field | arm_a | arm_b | evidence |
| --- | --- | --- | --- |
| pool_id | N/A dependency gate | N/A dependency gate | 학습 없음 |
| actual_pool_tokens | N/A | N/A | 데이터 없음 |
| pool_override | N/A | N/A | 데이터 없음 |
| steps | N/A | N/A | GPU 0 gate |
| micro_bs | N/A | N/A | 학습 없음 |
| accum | N/A | N/A | 학습 없음 |
| seq | N/A | N/A | 학습 없음 |
| actual_draw_tokens | N/A | N/A | 학습 없음 |
| sampler_with_replacement | false | false | 데이터 없음 |
| expected_unique_tokens | N/A | N/A | 데이터 없음 |
| sequential_epoch_claim | false | false | 학습 없음 |
| scheduler | N/A | N/A | 학습 없음 |
| warmup | N/A | N/A | 학습 없음 |
| anneal_start | N/A | N/A | 학습 없음 |
| decay_fraction | N/A | N/A | 학습 없음 |
| absolute_schedule_horizon | N/A | N/A | 학습 없음 |
| train_language_expected | N/A | N/A | 데이터 없음 |
| train_language_observed | N/A | N/A | 데이터 없음 |
| eval_dataset | dependency schema | dependency schema | 품질 평가 없음 |
| eval_language | N/A | N/A | 자연어 평가 없음 |
| tokenizer | N/A | N/A | 토큰화 없음 |
| grad_ckpt | false | false | 모델 없음 |
| representation | required evidence schema | missing evidence | 로그 |
| hardware | CPU/WSL | CPU/WSL | 로그 |
| comparator_tag | P022C expected evidence | P094 R0 observation | 파일 존재·schema gate |
| matched_axes | pool_id,actual_pool_tokens,pool_override,steps,micro_bs,accum,seq,actual_draw_tokens,sampler_with_replacement,expected_unique_tokens,sequential_epoch_claim,scheduler,warmup,anneal_start,decay_fraction,absolute_schedule_horizon,train_language_expected,train_language_observed,eval_dataset,eval_language,tokenizer,grad_ckpt,hardware | same | 동일 dependency 환경 |
| changed_axes | representation | representation | expected evidence와 missing observation |
| unmeasured_axes | NONE | NONE | 미실행 주장은 별도 열거 |
| not_run_claims | TRAINING,QUALITY,RESIDUAL_R1 | same | 로그 |
| permitted_claim | NOT_RUN | NOT_RUN | residual 결과 주장 금지 |
<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->

## 3. 후속

P022C shadow observer가 실제 storage evidence를 생성한 뒤 같은 R0를 재실행한다. 현재는 재실행
조건이 바뀌지 않았으므로 새 launcher를 만들지 않는다.

---

## ★부록 — 재현 명령 정본 (`run_P094_R0_p022c_dependency_gate-done.sh` 추출, 2026-09-19)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" scripts/diag_p094_dependency_gate.py    --evidence runs/evidence/P022C_shadow_storage.json
```
