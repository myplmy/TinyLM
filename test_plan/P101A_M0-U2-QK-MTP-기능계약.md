# P101A — M0 기반 U2 E384·QK gain·MTP 기능 게이트

> 제안 계기: [승인된 A안](../proposal/20260923_TinyLM-M0-C0-E384-QK-MTP-지능향상-제안서-approved-on-going.md) 10절. 독립 suffix 기능 계획. **2026-09-25 현재 Stage0W 기능 PASS, 고정 M0 Stage1W 결합 팔은 max_abs 1.2397766e-05로 원 1e-5 문턱 FAIL; Stage1Wb 사용자 재진단에서 E384만 원 1e-5 문턱 FAIL, QK/MTP는 이 입력의 기능 정합 PASS; Stage1Wc 원인분리는 STATIC_ONLY/NOT_RUN. 학습·GPU·품질은 NOT_RUN.**

## 1. 왜

기존 `--emb-rank`는 E를 바꿀 수 있지만 M0 체크포인트의 함수 보존 이식기는 없었다. 현재는 순수 상태사전의 E-rank 확장·QK gain exact-key helper까지 구현했고, 실제 M0 checkpoint 로드·계속학습 경로는 기본 off 코드로 준비했으나 실행되지 않았다. 기존 QK RMSNorm에는 학습 gain이 없었다. MTP는 S+1 crop에서 미래 타깃·EOS 문서경계를 맞춰야 하며, head·trainer 코드 연결은 정적 상태이며 실제 모델·GPU 게이트는 미실행이다. 신규 C0 1.2B는 한국어/풀 gate HOLD이므로 이 실험에는 넣지 않는다.

## 2. 질문

| # | 질문 | 증거 |
|---|---|---|
| Q1 | E256→E384 선형 입력·출력 함수가 실수 산술에서 보존되고 새 U가 gradient를 받나 | max_abs·gradient |
| Q2 | QK gain off가 기존 모델이고 on의 초기 τ=1이 logits를 유지하나 | tiny model logits, missing key exact, gain gradient·WD0/LR0.1 |
| Q3 | horizon2/4 타깃이 EOS 뒤 문서로 새지 않나 | S+1 crop·타깃/마스크 fixture |

## 3. 예측

Q1은 실수 산술에서 정확히 같을 수 있다. BF16/quantized export는 shape에 따른 반올림으로 다를 수 있다. Q2는 초기 logits가 매우 가깝지만 kernel shape·dtype 변화는 비트 동일성을 보장하지 않는다. Q3의 범위를 넘어 assistant 메시지 경계나 실제 품질을 주장하지 않는다.

## 4. 단계 설계

### Stage0W — 함수·수학 계약, 사용자 실행용 SH

[CPU 수학 게이트](../scripts/diag_p101a_math_contract.py)는 E 확장·엄격 상태키/로컬 RNG·QK τ=1, EOS horizon2/4, 독립 aux projection+공유 어휘를 쓰는 FP32 3-head loss/모든 gradient·유효타깃 분모를 full-logit 기준과 대조한다. [작은 모델 게이트](../scripts/diag_p101a_qk_gain.py)는 사용자 실행으로 strict 이식·기본 off hidden 경로·MTP head 독립성/gradient·배포 payload에서 aux key 제거 후 주 logits 불변을 본다. 두 코드는 [실물 SH](../run_P101A_Stage0W_u2_mtp_function_gate.sh)로 한 로그에 기록한다. QK는 `attn_group=1`에서만 per-layer/head 구현을 허용한다. Codex는 실제 모델 gate를 실행하지 않는다.

### Stage1W — 실제 M0 checkpoint 기능 게이트 준비, continued trainer 기본 off·STATIC_ONLY

[M0 진단기](../scripts/diag_p101a_m0_migration.py)는 로컬 final checkpoint·기존 32k tokenizer·1.2B 정확 캐시 metadata의 고정 SHA와 런 JSON 계약을 먼저 확인한다. `--check-only`는 876,874,091B final, 1,194,000,000-token train 및 6,000,000-token val의 파일 존재·크기·해시를 읽기 전용으로 PASS했다. [사용자 실행 SH](../run_P101A_Stage1W_m0_migration_gate.sh)의 본 경로는 실제 M0 state를 strict 로드해 E384·QK·독립 MTP head로 이식한 뒤 동일 입력 주 logits, 배포용 aux 제거 및 새 rank/aux gradient를 검사한다. **Codex는 checkpoint를 모델로 로딩하지 않았다.** Stage0W 소형 모델과 Stage1W 실제 M0 모델 결과는 `NOT_RUN`이며, continued-training trainer opt-in은 기본 off 코드로 연결했지만 실제 모델/GPU 실행은 NOT_RUN이며 assistant 경계는 미구현이다. 어느 기능 게이트도 100M 학습을 자동 개방하지 않는다. 후속 코드 감사에서 `prepare(exact)`의 `bytes_per_token` 부재 시 meta.json 자동 백필 쓰기를 확인했으므로, 고정 cache에 유한·양수 bpt와 uint16 dtype이 있는지 모델·캐시 진입 전에 fail-closed하도록 보강했다. **이 신규 검사 자체는 보호 자산 읽기 경계 때문에 Codex가 재실행하지 않았으며**, 앞선 check-only PASS는 이 추가 조건을 포함하지 않는다.

### Stage1Wb — 독립 M0 팔별 drift 귀속 완료: E384 FAIL, QK·MTP 기능 정합 PASS

2026-09-24 Stage1W의 결합 E384+QK+MTP 진단은 `max_abs=1.2397766e-05`로 기존 `1e-5` 기능 문턱을 실패했다. 이 결합 구성은 Stage2의 독립 E384/QK/MTP 팔이 아니므로 결합 실패만으로 어느 팔의 오류인지 판정할 수 없다. 같은 고정 M0 부모·legacy tokenizer·입력에서 E384, QK, MTP를 각각 따로 strict 이식하고 주 logits `max_abs`·NRMS·argmax 불일치·해당 새 파라미터 gradient 및 MTP 배포 제거를 기록한다. **기존 문턱은 완화하지 않는다.** 이는 2026-09-24의 실행 전 설계이며 실제 결과는 [결과092 §7](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)에 있다. E384 문턱 실패 때문에 해당 Stage2 학습은 열지 않는다.


### Stage1Wc — E384 FP32 차이 원인분리, 사용자 CPU 모델 진단만

Stage1Wb에서 E384만 `1.23977661e-5 > 1e-5`로 실패했다. [진단기](../scripts/diag_p101a_e384_roundoff.py)와 [별도 SH](../run_P101A_Stage1Wc_e384_roundoff_attribution.sh)는 같은 고정 M0 부모·legacy 32k·기존 입력 seed7과 추가 seed17/31을 **읽기 전용**으로 사용한다. 이식된 기존 E256 weight/U 열이 비트 동일하고 새 U 열이 0인지 확인한 뒤, FP32 입력 임베딩·body hidden·공통 hidden 출력 head·전체 주 로짓 차이를 나눠 보고하고 FP64 수학 지도와 대조한다. 독립변수는 관측 분해뿐이며 학습토큰0, 태그/체크포인트 출력0, GPU0, 약0.3h CPU와 수 GiB host RAM 예상이다. tensor-only 자기시험과 shell 구문은 PASS지만 실제 M0 진단은 사용자 실행 전 `NOT_RUN`이다.

**사전 판정:** 이전 Stage1Wb의 `1e-5`를 그대로 보존한다. Stage1Wc exit0은 수치 계측 완료일 뿐 E384 기능 PASS가 아니다. state old-block/zero-new-U가 실패하면 migration 코드 결함, FP64 거의0·FP32만 차이가 나면 형상 변경에 따른 반올림 가설을 지지하지만 원인별 최소 수정·별도 기능 재게이트 전까지 E384 학습을 열지 않는다. 다른 seed에서 차이가 커지면 문턱을 조용히 완화하지 않고 재설계한다. `check_run_registry.py`의 광범위 `runs/` 스캔은 승인 범위 밖이라 이 무학습 진단에서는 `NOT_RUN`이며 새 학습 태그 preflight는 별도로 한다.
### Stage2W — 100M 이하 분리 학습, 별도 사용자 승인

B0/E-only/QK-only/MTP-only는 동일 SHA의 M0 final 가중치만 이식하고 기존 optimizer를 재사용하지 않는다. `762×8×16×1024=99,876,864` draw로 100M 미만을 지키며 동일 1.2B **기존 cache pool**·legacy 32k tokenizer·고정 val crop·seed·Muon RMS4·LR/WSD를 맞춘다. 기존 M0의 최종 quant anneal 값을 이어받아 새 run에서 어닐을 재시작하지 않고, E384/QK gain/MTP aux만 각 팔의 독립변수로 둔다. MTP는 EOS 문서경계 유효 horizon2/4를 update 전체 분모로 나누고 계수는 5% warmup·80%까지 hold·끝 20% decay한다. 신규 C0 1.2B 학습이 아니며 600M 이상 신규 학습 금지는 유지한다. Stage0W/Stage1W 사용자 기능 로그와 별도 학습 승인 전 실제 학습 런처는 작성하지 않는다. P102A S3의 `--mtp-sample-half`는 전량 MTP 기능·품질 기준선 뒤에만 별도 arm으로 열며, 현재는 기본 off 코드와 CPU HT fixture만 있다.

첫 분리 팔의 태그는 정확히 `p101a_b0_s{seed}`, `p101a_e384_s{seed}`, `p101a_qk_s{seed}`, `p101a_mtp_s{seed}`이고, S3 표본 후속은 `p101a_mtp_ht_s{seed}`만 허용한다. 여러 구조/보조축을 한 팔에 결합하면 현재 단계에서는 거절한다. 결과 JSON에는 arm, M0 parent SHA, legacy tokenizer SHA, cache metadata SHA, 부모 anneal·weight-only init 및 전체/선택 MTP target 수를 남긴다. 이는 계획한 독립변수 추적 계약이지 **학습 실행이나 동일 품질의 증거가 아니다**.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| Stage0 math max_abs>1e-6, EOS 누출 또는 gain parameter/migration 불일치 | 기능 FAIL, Stage1 진행 금지 |
| Stage0 τ=1 logits max_abs≤1e-5와 gain gradient 비영 | 작은 기능 계약만 PASS, 실제 M0 효과 NOT_RUN |
| Stage1 model/parent/tokenizer hash 불일치 | 비교 불가, 학습 명령 금지 |
| Stage1 strict state·동일 입력 주 logits `max_abs>1e-5`·aux/신규 rank gradient 0 | 기능 FAIL(exit1), continued-training 구현/실험을 채택하지 않음 |
| 100M 짧은 loss 개선 | 축 방향만 기록, 한국어 지능·배포 채택 아님 |

## 6. 비용

| 단계 | 예상 | 자원 |
|---|---:|---|
| Stage0W | 약0.1h | CPU 작은 모델, 사용자 실행 |
| Stage1W M0 이식·함수 | 약0.2h, host RAM 수 GiB | 사용자 CPU 모델 실행. 학습·GPU 0 |
| Stage2W | 100M 팔당 기존 M0 후속 길이로 재산정 | 별도 승인 |

## 7. 실행 파일

`run_P101A_Stage0W_u2_mtp_function_gate.sh`와 `run_P101A_Stage1W_m0_migration_gate.sh`를 서로 다른 이름으로 작성했다. 결과번호092, 기능 실패는 exit1이다. 실제 학습 런처는 0개. `P006`·기준표 조건이 정본이며 새 태그·풀 예산은 학습 단계에서 preflight한다.

## 8. 한계

E384의 **실제 모델** checkpoint 이식·MTP head·배포 제거는 코드와 사용자 실행 게이트만 준비됐고 실제 결과는 `NOT_RUN`이다. 계속학습 trainer는 STATIC_ONLY, assistant 경계는 미구현이며 품질·GPU 속도도 미실행이다. 새 QK gain은 기본 off로만 안전하다. Stage0W/Stage1W의 기능 PASS가 나와도 A 권장안 전체나 학습효과의 완료로 승격하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-24: `tinylm/train/p101a_contract.py`, QK gain config/Attention/optimizer opt-in과 CPU 수학 fixture를 구현. E/MTP fixture와 E256→E384 state-dict strict-key·local RNG·tau1 거부 fixture는 PASS. 작은 모델·실제 M0 checkpoint gate는 사용자 실행 전 `NOT_RUN`.

- 2026-09-24 막힘 재감사: Stage0W 모델 로그는 함수·G2 승인 증거이지 기본 off 코딩 금지가 아니다. `mtp_loss_components`/`mtp_weighted_mean`의 S+1 입력·독립 horizon2/4·공유 어휘 gradient·update valid-token 분모가 full-logit CPU fixture와 일치했다. 모델에 독립 aux head·정규화 hidden 반환·배포 payload 제거 코드를 추가하고 작은 사용자 모델 gate를 확장했다. **Codex는 그 모델 gate를 실행하지 않았다.** 실제 M0 이식·전체 trainer·GPU·품질은 NOT_RUN/미구현으로 분리하고 GPT 구현을 계속한다.

- 2026-09-24: 사용자 로컬커밋 `d636321` 뒤, M0 final·tokenizer·cache metadata의 고정 SHA/JSON·train/val 바이트를 모델 없이 직접 검증했다. Stage1W 실제 모델 이식 진단기와 WSL SH를 신설했고 check-only PASS. checkpoint 모델 로딩·동일 주 logits·gradient·배포 strict gate는 사용자 실행 전 `NOT_RUN`이다.

- 2026-09-24 후속: `--p101a-m0` 고정 부모 SHA·동일 legacy tokenizer/cache·weight-only strict 이식, 최종 anneal 보존, `--mtp-aux` update 전체 유효타깃 분모와 loss/gradient를 trainer 기본 off로 연결했다. 순수 CPU MTP 누적 fixture와 codex-safe 정적은 PASS, 실제 M0 모델 게이트·100M 미만 학습·품질은 `NOT_RUN`.

- 2026-09-24 후속: B0/E384/QK/MTP/MTP-HT의 한 축만 달라지는 arm 함수·seed 고정 태그와 parent/tokenizer/cache SHA JSON을 trainer에 fail-closed로 연결했다. 결합 팔 거부·CPU E/QK/MTP fixture PASS. Stage2 사용자 학습 SH는 별도 승인·Stage0/1 실제 기능 PASS 전 0개이며 품질 `NOT_RUN`.

- 2026-09-24 후속: `prepare(exact)`가 기존 cache meta의 `bytes_per_token`이 없으면 사용자 원본에 자동 백필 쓰기를 한다는 경로를 코드에서 발견했다. 고정 M0 자산 verifier가 유한·양수 bpt와 uint16 dtype을 요구하도록 수정했고 missing/bool/NaN/wrong-dtype **합성 fixture는 PASS**했으나, 이 추가 조건은 자산 읽기 허용 밖이라 Codex가 실행하지 않았다. 과거 check-only PASS를 새 조건의 PASS로 승격하지 않는다. 사용자 게이트가 이를 FAIL하면 원본 meta를 임의 수정하지 않고 사유를 회신한다.

- 2026-09-25 사용자 로그 회수: [결과092 §2~3](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)의 Stage0W 두 호출은 PASS. 실제 M0 Stage1W는 결합 E384+QK+MTP 주 logits `max_abs=1.2397766e-05`가 원 `1e-5` 문턱을 넘고 aux/gradient 전에 exit1이었다. ‘초기 함수가 매우 가깝다’는 방향은 맞지만 **사전 기능 문턱은 실패**했으므로 Stage2 HOLD. 결합 팔은 승인된 독립 팔과 달라 `run_P101A_Stage1Wb_m0_arm_attribution.sh`로 원 문턱 유지·독립 팔 귀속을 사용자 재실행한다. 기존 Stage0W/Stage1W 런처는 -done 실패/성공 이력으로 보존한다.

- 2026-09-25 Stage1Wb 후속: [결과092 §7](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)에서 실제 M0 독립 팔 중 E384만 `1.23977661e-5 > 1e-5`로 기능 FAIL, QK/MTP 주 로짓0·top1변경0, MTP aux 제거 차0이다. 작은 NRMS `4.01000563e-7`은 사전등록 문턱을 대신하지 않는다. Stage1Wc 별도 CPU 원인분리 코드·SH는 tensor-only self-test PASS/실제 M0 `NOT_RUN`, E384 Stage2 학습 HOLD. QK/MTP도 GPU·품질 자동 개방은 아니다. 원 Stage1Wb SH는 `-done` 시도 이력으로 개명했다.
