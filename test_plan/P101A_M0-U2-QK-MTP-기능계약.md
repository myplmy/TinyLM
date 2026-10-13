# P101A — M0 기반 U2 E384·QK gain·MTP 기능 게이트

> 제안 계기: [승인된 A안](../proposal/20260923_TinyLM-M0-C0-E384-QK-MTP-지능향상-제안서-approved-on-going.md) 10절. 독립 suffix 기능 계획. **2026-09-25 현재 Stage1Wb E384 원1e-5 기능 FAIL 유지, QK/MTP는 한 입력 정합 PASS. Stage1Wc 사용자 M0 세 seed에서 FP32 입력/body/head 누적 반올림 가설을 지지하고 FP64 공통 head 차≈0; 이는 원인분리 완료이지 E384 기능 PASS가 아니다. 학습·GPU·품질 NOT_RUN.**

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


### Stage1Wc — E384 FP32 차이 원인분리 완료(결과092 §8), 원 기능 FAIL 유지

Stage1Wb에서 E384만 `1.23977661e-5 > 1e-5`로 실패했다. [진단기](../scripts/diag_p101a_e384_roundoff.py)와 [사용자 실행 SH](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)는 고정 M0·legacy 32k·seed7/17/31의 old-block bit-identical/new-U zero, FP32 입력·body·head 및 FP64 수학 지도를 검사했다. 실제 로그 [결과092 §8](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)는 전체 FP32 차 1.14~1.24e-5(세 seed 모두 초과), FP64 공통 head 차 최대 3.55e-15, top1 변경0을 기록한다. 계측 종료코드0은 원1e-5 기능 문턱 PASS가 아니며 학습·GPU·품질은 `NOT_RUN`이다.

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

Stage0W·Stage1W·Stage1Wb·Stage1Wc 사용자 실행 이력과 정확 재현명령은 [결과092](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md) 부록에 보존했다. 실행 완료 `-done` 두 파일은 사용자 지시로 삭제했으며 원본은 Git에서 복구 가능하다. 현재 E384 학습 런처는 0개, 새 수치 remedy가 승인되면 새 단계명을 써야 한다.

## 8. 한계

실제 M0에서는 E384 이식이 원 함수 문턱을 실패했고 QK/MTP 독립 팔은 해당 입력만 정합했다. Stage1Wc 수치 귀속 뒤에도 계속학습 trainer 동적 실행·assistant 경계·품질·GPU 속도는 `NOT_RUN`이며 새 QK gain은 기본 off다. 현재 기능·진단 결과를 A 권장안 전체나 학습효과 완료로 승격하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-24: `tinylm/train/p101a_contract.py`, QK gain config/Attention/optimizer opt-in과 CPU 수학 fixture를 구현. E/MTP fixture와 E256→E384 state-dict strict-key·local RNG·tau1 거부 fixture는 PASS. 작은 모델·실제 M0 checkpoint gate는 사용자 실행 전 `NOT_RUN`.

- 2026-09-24 막힘 재감사: Stage0W 모델 로그는 함수·G2 승인 증거이지 기본 off 코딩 금지가 아니다. `mtp_loss_components`/`mtp_weighted_mean`의 S+1 입력·독립 horizon2/4·공유 어휘 gradient·update valid-token 분모가 full-logit CPU fixture와 일치했다. 모델에 독립 aux head·정규화 hidden 반환·배포 payload 제거 코드를 추가하고 작은 사용자 모델 gate를 확장했다. **Codex는 그 모델 gate를 실행하지 않았다.** 실제 M0 이식·전체 trainer·GPU·품질은 NOT_RUN/미구현으로 분리하고 GPT 구현을 계속한다.

- 2026-09-24: 사용자 로컬커밋 `d636321` 뒤, M0 final·tokenizer·cache metadata의 고정 SHA/JSON·train/val 바이트를 모델 없이 직접 검증했다. Stage1W 실제 모델 이식 진단기와 WSL SH를 신설했고 check-only PASS. checkpoint 모델 로딩·동일 주 logits·gradient·배포 strict gate는 사용자 실행 전 `NOT_RUN`이다.

- 2026-09-24 후속: `--p101a-m0` 고정 부모 SHA·동일 legacy tokenizer/cache·weight-only strict 이식, 최종 anneal 보존, `--mtp-aux` update 전체 유효타깃 분모와 loss/gradient를 trainer 기본 off로 연결했다. 순수 CPU MTP 누적 fixture와 codex-safe 정적은 PASS, 실제 M0 모델 게이트·100M 미만 학습·품질은 `NOT_RUN`.

- 2026-09-24 후속: B0/E384/QK/MTP/MTP-HT의 한 축만 달라지는 arm 함수·seed 고정 태그와 parent/tokenizer/cache SHA JSON을 trainer에 fail-closed로 연결했다. 결합 팔 거부·CPU E/QK/MTP fixture PASS. Stage2 사용자 학습 SH는 별도 승인·Stage0/1 실제 기능 PASS 전 0개이며 품질 `NOT_RUN`.

- 2026-09-24 후속: `prepare(exact)`가 기존 cache meta의 `bytes_per_token`이 없으면 사용자 원본에 자동 백필 쓰기를 한다는 경로를 코드에서 발견했다. 고정 M0 자산 verifier가 유한·양수 bpt와 uint16 dtype을 요구하도록 수정했고 missing/bool/NaN/wrong-dtype **합성 fixture는 PASS**했으나, 이 추가 조건은 자산 읽기 허용 밖이라 Codex가 실행하지 않았다. 과거 check-only PASS를 새 조건의 PASS로 승격하지 않는다. 사용자 게이트가 이를 FAIL하면 원본 meta를 임의 수정하지 않고 사유를 회신한다.

- 2026-09-25 사용자 로그 회수: [결과092 §2~3](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)의 Stage0W 두 호출은 PASS. 실제 M0 Stage1W는 결합 E384+QK+MTP 주 logits `max_abs=1.2397766e-05`가 원 `1e-5` 문턱을 넘고 aux/gradient 전에 exit1이었다. ‘초기 함수가 매우 가깝다’는 방향은 맞지만 **사전 기능 문턱은 실패**했으므로 Stage2 HOLD. 결합 팔은 승인된 독립 팔과 달라 `run_P101A_Stage1Wb_m0_arm_attribution.sh`로 원 문턱 유지·독립 팔 귀속을 사용자 재실행한다. 기존 Stage0W/Stage1W 런처는 -done 실패/성공 이력으로 보존한다.

- 2026-09-25 Stage1Wb 후속: [결과092 §7](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)에서 실제 M0 독립 팔 중 E384만 `1.23977661e-5 > 1e-5`로 기능 FAIL, QK/MTP 주 로짓0·top1변경0, MTP aux 제거 차0이다. 작은 NRMS `4.01000563e-7`은 사전등록 문턱을 대신하지 않는다. Stage1Wc 별도 CPU 원인분리 코드·SH는 tensor-only self-test PASS/실제 M0 `NOT_RUN`, E384 Stage2 학습 HOLD. QK/MTP도 GPU·품질 자동 개방은 아니다. 원 Stage1Wb SH는 `-done` 시도 이력으로 개명했다.

- 2026-09-25 Stage1Wc 사용자 로그 회수: [결과092 §8](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)에서 old E256 block bit-identical·new U zero, 세 seed의 FP32 전체 logits 차 1.1444e-5~1.2398e-5가 원 문턱을 모두 넘었다. FP64 공통 hidden head 차는 3.55e-15 이하라 shape/연산 순서 반올림 가설을 지지한다. §3의 실수산술 동치 예상은 지지됐지만 FP32 기능 문턱은 실패했다. Stage2 E384 학습 HOLD, 새로운 remedy는 원 문턱 완화 없이 별도 사전등록한다.

# P101A — 2026-10-12 SFT MTP와 선택형 검증 추론 후속

## 1. 왜

옛 E384 기능 실패는 독립 MTP 실패가 아니다. 사용자 현재 지시로 미래 타깃의 assistant/턴 마스크를 구현하고, 학습효과와 추론 가속을 별개로 시험한다. 현재 사용자 선택은 고유8M 표본×4epoch의 무부모/부모×NTP/MTP 네 팔이다. 정상75M×4epoch/약300M 본교육 목표는 축소하지 않는다.

## 2. 질문

- Q1: 미래2/3/4 타깃이 같은 assistant 턴 안에만 있고 종료 토큰은 지도되는가?
- Q2: 같은 초기 본체·자료·배치·LR·순서에서 보조 손실이 main NTP val, 실제 질문/멀티턴, 망각, 전체시간의 교환비를 개선하는가?
- Q3: 학습한 헤드를 선택적으로 유지·제거하고 본 모델로 검증하여 greedy 생성2/3/4토큰 블록의 실제 수락/속도/메모리·출력 정합을 관측할 수 있는가?

## 3. 예측

보조 미래 예측은 학습 신호를 늘릴 수 있지만 스텝당 추가 계산과 gradient 간섭으로 이득이 없을 수 있다. 무부모32M은 일반 언어능력 확보를 보증하지 않는다. head 수가 늘면 저장은 선형 증가하지만 수락률·검증/캐시 재구축 비용 때문에 속도는 비단조일 수 있다. 본 모델 검증 없이 초안을 출력하지 않는다.

## 4. 단계 설계

- Stage3aW: 합성 CPU 마스크·turn/EOS·누적분모·손실/gradient·head attach/drop·검증 생성 계약. 실물 모델/GPU 없이 회귀.
- Stage3bW: 현재 공개 capability 자료와 보존된 Gemma 생성물을 읽기 전용으로 선별해 새8M 표본/별도val을 동결한다. 출처 개념 split·한영·QA/JSON/멀티턴·20MB 샤드·실제 x/assistant/horizon 토큰을 남긴다. 동일자료4pass이며 반복을 고유토큰으로 세지 않는다. 부족하면 정확한 부족량을 보고한다.
- Stage3cW: 네 팔의 실제 비용/VRAM을 먼저 재는 짧은 사용자 GPU gate. 품질 판정은 하지 않는다.
- Stage3dWa/Wb/Wc/Wd: scratch NTP/scratch MTP/parent NTP/parent MTP, 각8M×4epoch 약32M actual x. 구조·토크나이저·micro8×accum16·checkpoint-on·compile default·LR1e-4/Muon RMS4 4e-4를 동일하게 둔다. scratch의 공통 본체 RNG/지문이 같고 MTP 초기 헤드는 main U 복사로 RNG를 추가 소비하지 않는다. 부모 두 팔은 같은 chat32 부모 SHA에서 시작한다.
- Stage3eW: main NTP 고정 val·실제 답/형식/종료·멀티턴·일반 언어 손실·추가 계산·유효 처리율을 비교한다. 단일seed 결과를 아키텍처 일반 우열로 쓰지 않는다.
- Stage4aW: 학습 완료 MTP 학생에서 헤드 off/2/3/4 총예측토큰의 검증 greedy 대응. 모든 미수락 초안은 폐기하고 main 예측으로 교체한다. sampling의 분포 보존·FastMTP 원문 재현은 이번 범위가 아니다.

## 5. 판정

기술 gate와 실제 학습효과를 분리한다. 새로운 SFT 조건의 sigma는 미측정이므로 옛 CPT의 고정 자를 복사하지 않는다. main NTP val/실제 답/망각/비용을 별도로 보고한다. 추론은 같은 학생의 NTP 원답과 정확한 token/종료가 맞아야 속도 후보로 판단한다. 낮은 draft 정확성은 검증 비용/속도 문제이며 무검증 출력의 품질손상을 허용하는 근거가 아니다.

## 6. 비용

각학습은 CPU 선별과 GPU 비용 gate 실측 뒤 비용을 재산정한다. 네 팔 총 actual 처리 약128M, aux 지도량은 별도다. E256×dim768 독립 projection 하나는196,608개로FP32 0.75MiB/FP16 0.375MiB이며 공유 어휘는 복제하지 않는다. 총예측2/3/4는 보조1/2/3개, FP32 0.75/1.5/2.25MiB. logits·KV·임시 승격·optimizer·allocator는 이 식 밖이다.

## 7. 실행

Gemma 생산 MTP 비교 다음에 아래 SH 순서로 진행한다. CPU contract 본문29시험은 GPT가 직접 완료했고 wrapper는 NOT_RUN인 -done 이력이다. 선별 뒤 각 비용 팔32업데이트를 먼저 실행하고 시간·VRAM을 확인한다. 각 본학습의1.5h는 미실측 추정이며 비용 report의 전체 update 예상으로 재산정한다. 본학습 hard cap3h, 비용 hard cap30분이고 부분 실행/기존 report를 덮어쓰기하지 않는다.

| 순 | 단계·SH | 선결/판정 |
|---|---|---|
| 완료 | `run_P101A_Stage3aW_sft_mtp_cpu_contract-done.sh` | 본문29 CPU PASS, 실제 모델/학습 아님 |
| 1 | `run_P101A_Stage3bW_sft_mtp_frozen8m_corpus.sh` | 현재 contract SHA, 정확train8M·val0.4M/한영/task quota·개념/질문val 제외·20MB SHA |
| 2 | `run_P101A_Stage3cWa_scratch_ntp_cost.sh` | 같은 complete8M, scratchNTP32update 자원/비용만 |
| 2 | `run_P101A_Stage3cWb_scratch_mtp_cost.sh` | scratchMTP32update; aux2/3/4 gradient와자원 |
| 2 | `run_P101A_Stage3cWc_parent_ntp_cost.sh` | parentNTP32update 자원/비용만 |
| 2 | `run_P101A_Stage3cWd_parent_mtp_cost.sh` | parentMTP32update 자원/비용만 |
| 3 | `run_P101A_Stage3dWa_scratch_ntp_frozen8m.sh` | matching cost·새무부모NTP32M |
| 3 | `run_P101A_Stage3dWb_scratch_mtp_frozen8m.sh` | matching cost·새무부모MTP32M |
| 3 | `run_P101A_Stage3dWc_parent_ntp_frozen8m.sh` | matching cost·고정부모NTP32M |
| 3 | `run_P101A_Stage3dWd_parent_mtp_frozen8m.sh` | matching cost·고정부모MTP32M |
| 4 | `run_P101A_Stage3eW_sft_mtp_four_arm_readback.sh` | 네 성공report·쌍별본체/자료/실제토큰/업데이트 동일 |
| 5 | `run_P101A_Stage4aWa_scratch_mtp_verified_infer.sh` | 저장된scratchMTP 학생·같은body off/2/3/4/FP16·FP32 |
| 5 | `run_P101A_Stage4aWb_parent_mtp_verified_infer.sh` | 저장된parentMTP 학생·같은body off/2/3/4/FP16·FP32 |

8M은 기존 public capability와 sealed Gemma batch에서 선택하며 원천/source/원개념을 보존한다. 같은 대화의 완전 중복은 제외하지만 QA·형식·멀티턴 변형을 각각 새 개념으로 세지 않는다. 고유개념수·실제family share·교사분량은 report에 별도로 남기며 새25%source상한을 검증했다고 주장하지 않는다. whole-row 경계의 소폭 초과와 actual x/assistant/aux/padding 분모를 공개한다. 학습 전후 동일32 native crop CE와실제8질문 첫답/최대3시도·최대4이어쓰기, epoch별SFT val을 남긴다.

기본태그는 `p101a_sft_mtp_v1_s1337`; 새 corpus는 `HF/sft_ready/<tag>/corpus`, report는 `test_result/evidence/<tag>`, 학생4개는 `runs/ckpt/m100s10_ko-en_32M_dense_chat32_<tag>_<arm>.pt`다. 기존 parent/HF/cache/checkpoint 수정·optimizer 재사용·학습 재개는 없다. 이번 Codex TinyLM 실물 모델/GPU 학습·추론 실행은 NOT_RUN이다.

## 8. 한계·원문 차이

현재 경량 projection은 [DeepSeek-V3 §2.2](https://arxiv.org/html/2412.19437v2#S2.SS2)의 순차 Transformer MTP 모듈이나 [FastMTP §3](https://arxiv.org/html/2509.18362v1)의 position-shared self-distillation 전체 재현이 아니다. 검증 생성은 [speculative decoding §2](https://proceedings.mlr.press/v202/leviathan23a.html)의 원칙을 참고하되 첫 범위는 greedy로 제한한다. 코드·FP32 CPU 정합이 모든 GPU/backend/샘플링/장기 배포의 무손실 증명은 아니다.

## 9. 실행 이력

2026-10-12: 사용자2안으로 무부모+부모 네 팔을 확정했다. assistant-turn mask, up2/3/4·optional export/hotplug, head/CE 재계산, main 검증 greedy를 구현했다. 합성CPU29 PASS·13SH argparse route PASS, legacyM0 계약도 회귀했다. [092 §10](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md). 기존기본off·E384/M0 실패는불변이며 actual8M 준비/실물학습/추론가속은NOT_RUN이다.

## 2026-10-13 실행 회수·Stage3f~h / Stage4b 후속

### 1. 왜·예측 대조

[092 §11](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)에서 실제 네 팔4epoch가 완료됐지만 엄격 첫답0~1/8·부모 원문손실 악화가 남았다.
최종 CE 감소를 일반 능력 향상으로 옮기는 예측은 성립하지 않았다. 원형 MTP 추론의 비트/출력 정합 예측도GPU에서 미달했다.

### 2. 질문

| 질문 | 다음 분리 |
|---|---|
| 검증 블록/재구축이 같은 이력에서도 선택을 바꾸는가 | 재학습 없이 BF16/FP32·query1/multiquery/rebuild 로짓과 KV |
| 같은8M에서 LR만 낮추면 망각을 줄이는가 | 부모NTP1epoch 두 LRscale; 실제 답/원문/SFT 손실 동시 |

### 3. 예측과 실패 가능성

낮은 LR은 이동량을 줄일 수 있지만 현재 부모가 지시를 잘 못 따르거나 원천이 편중돼 있으면 답안 효과가 없을 수 있다.
FP32가 정합을 회복해도 속도가 느려지고 정답성이 개선되는 것은 아니다. 단일 seed의 작은 CE 차이에 과거 CPT σ를 적용하지 않는다.

### 4. 단계 설계·현재 상태

| 단계 | 상태 | 조건과 판정 | 시간/GPU |
|---|---|---|---|
| Stage3bW~3eW | 실제 자료·비용·네팔 학습·readback 완료 | 각3296updates/32.006Mx, MTP 일반 효능 미확정 | 원본 회수 |
| Stage4aWa/Wb | 실제추론 음성 | scratch5/8,parent6/8 native 정합; 헤드정밀도 모두동일 실패집합 | 원본 회수 |
| Stage4b0W | CPU회귀/SH STATIC_ONLY | 작은synthetic cache/first-divergence 시험; actual GPU별도 | .02h/N |
| Stage4bWa/Wb | 준비·E2E_NOT_RUN | 같은saved2학생·8질문·native/MTP2/4·BF16/FP32, shadow정합을원답으로판독 | 각.25h/Y |
| Stage3f0W | CPU회귀/SH STATIC_ONLY | 새epochs API기본4 보존·양optimizer0.1scale | .02h/N |
| Stage3fWa/Wb | 준비·E2E_NOT_RUN | 같은8M/parentNTP 각32update 비용·새독립출력 | 각.15h/Y |
| Stage3gWa/Wb | 준비·E2E_NOT_RUN | 같은8M·각824updates/1epoch·새checkpoint; samecodecost필수 | 각.60h/Y, wall상한90분 |
| Stage3hW | 조건부 준비 | 두팔source/body/x/target/update일치, actual8답+native tradeoff판독 | .02h/N |

새팔은 Adam1e-4/Muon4e-4와1e-5/4e-5로 양optimizer를같은배율로 낮춘다. RMS4 비율을 유지한 ‘전체LR scale’ 대조이며 Adam만 바꾸는 실험이 아니다.
1epoch대조가75M×4 본목표나 과거4epoch기준을 대체하지 않는다. 배치8×16·ckptON·compile·seed·source는고정이다.
SFT 실제 x=8,001,524이고 패딩 계산자리824×131072=108,003,328은분리한다.
CPT의 pool≥2× 규칙은 승인된 고정자료 SFT 반복실험의근거로기계 적용하지않는다.

### 5. 실행

`run_P101A_Stage4b0W_mtp_parity_cpu.sh` — CPU synthetic first-divergence/real-id/cache-shadow regression; no checkpoint

`run_P101A_Stage4bWa_scratch_mtp_numeric_paths.sh` — Saved scratch student only; native/MTP same-prefix BF16/FP32 diagnostic; no training

`run_P101A_Stage4bWb_parent_mtp_numeric_paths.sh` — Saved parent student only; diagnose parallel verification versus cache rebuild; no quality adoption

`run_P101A_Stage3f0W_lr_retention_cpu.sh` — CPU one-pass exposure and joint Adam/Muon scale regression

`run_P101A_Stage3fWa_lrhi_onepass_cost.sh` — Fresh frozen8M parentNTP cost32; Adam1e-4 Muon4e-4; not quality gate

`run_P101A_Stage3fWb_lrlo_onepass_cost.sh` — Fresh frozen8M parentNTP cost32; Adam1e-5 Muon4e-5; same RMS4

`run_P101A_Stage3gWa_lrhi_onepass_train.sh` — User-only same frozen8M onepass824updates; micro8 accum16 ckptON; same-code cost prerequisite

`run_P101A_Stage3gWb_lrlo_onepass_train.sh` — User-only same8M onepass lower joint LR; native language retention and raw answers

`run_P101A_Stage3hW_lr_retention_pair.sh` — Both completed onepass arms required; comparable x/targets/parent; no models

### 6. 한계·preflight

신규lrhi/lrlo 두 tag는 registry에실제로그 없음으로 확인했고 현재 inference namespace는별도신설한다.
정의된독립변수 이외에는 바꾸지않고, actualquality를읽은뒤설정을 결정한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4c — 검증 경로의 수치 정합 원인 분리

### 1. 왜·질문·예측

Stage4b는 실제 두 저장 학생을 실행했다. BF16에서는 scratch 18/24·parent 20/24,
FP32/math에서는 각각24/24가 native와 같은 토큰·종료를 보였다.
원본 상위 필드의 K가 모두4인 집계 결함은 내부 profile.k로 교차 확인하고 원형을 보존한다.
기존 shadow는 실제 K가 아닌 항상3query여서 블록 크기별 원인 귀속으로 쓰지 않는다.
학습용 MTP는 이전 네 팔에서 실제 실행됐고, 이번 LR 두 팔은 NTP-only다.

질문은 같은 본체·질문·precision에서 (a) 병렬 query 형상과
(b) 거부 뒤 prefix 전체 재구축 중 어떤 경로가 native의 토큰을 바꾸는가다.
캐시를 유효 길이로 잘라도 병렬 BF16의 반올림은 남을 수 있고,
1query 검증이 정합을 회복해도 가속 이득은 없어질 수 있다.
동일 토큰은 정답성이나 지능 개선의 증거가 아니다.

### 2. 단계·조건·판정

| 단계 | 새 출력·조건 | 판정·실행 경계 |
|---|---|---|
| Stage4c0W | CPU28 회귀 목표; 실제 K 라벨·2/4query·CLA/R2·강제 거부·종료 | 본체/기본 경로 보존·합성 정합, 실물 품질 아님 |
| Stage4cWa | 저장 scratch MTP, 새 v3; 8질문×BF16/FP32×native/3검증방식×K2/4 | 각112행; native 토큰/종료 정합과 wall·재구축/절단/수락 별도 |
| Stage4cWb | 같은 조건의 저장 parent MTP | 같은 팔 내부 비교만; 서로 다른 초기화 우열을 수치 경로에 귀속하지 않음 |

세 검증 방식은 기존 parallel_rebuild(기본 불변), parallel_truncate,
serial_truncate다. 마지막은 native처럼 항상1query로 검증하는 정확성 대조이며
CPU/GPU에서 실측 전 무손실을 주장하지 않는다.
새 namespace는 p101a_mtp_parity_v3_s1337이며 checkpoint·tokenizer는 이전 정확 SHA를
읽기 전용으로 쓴다. 학습/optimizer/체크포인트 저장0, 새 evidence만 기록한다.
한 요청군의 전체 원답·실제 token IDs·종료·K·mode·precision을 보존한다.

### 3. 비용·실행·한계

예상 CPU1분 미만, 저장 학생 두 진단 각각5~15분(미측정); hard cap각900초.
사용자7에 따라 GPT 실행은 2026-10-14 17:00 KST 전까지의 단독 자원 게이트만 허가됐다.
그 이후 SH는 사용자 실행용이며 기본 경로를 자동 채택하지 않는다.

- run_P101A_Stage4c0W_mtp_verify_modes_cpu.sh
- run_P101A_Stage4cWa_scratch_mtp_verify_modes.sh
- run_P101A_Stage4cWb_parent_mtp_verify_modes.sh

동일 source·saved body·tokenizer·seed·max_new64·greedy·stop sequence를 유지한다.
코드 시그니처와 회귀·새 원답은 결과092에 연결하고 원본 Stage4b를 덮어쓰지 않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
