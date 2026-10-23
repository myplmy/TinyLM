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

### Stage3nbW — 2026-10-23 진단기 팔 교체 시 남은 GPU 할당의 원인 분리

Stage3nW는 fixed FP32 한 update와 BF16 fixed6update 뒤 다음 팔 입장에서 GPU 할당이
남아 중단됐다. OOM·모델 발산·두 설정 등가성 음성으로 판정하지 않는다. 모델/optimizer
객체 참조와 cuBLAS 작업공간을 구별하는 무학습 matmul canary부터 최대30초 수행한다.
원본 CP와 Stage3nW의 partial은 보존한다. 작업공간 정리 API 지원·정리 전후 실제 byte와
객체 소멸을 확인한 뒤에만 새 namespace에서 같은 수치/비용 대조를 재개한다.
새 진단은 메모리 허용턱을 높이지 않고, 프로세스 자기 문맥 이외의 작업과 잔존 모델은
계속 거부한다. 과거 partial 결과를 성공으로 바꾸지 않는다.

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

## 2026-10-21 신규 준비 — Stage3i/3j/3k: 문맥교과 MTP와 검산풀이 본대조

### 1. 왜

과거8M×4epoch 네팔은실제로완료됐다.같은실험을새방법처럼재실행하지않는다.이번독립변수는명시문맥/교정턴마스크를고정한교과에서의MTP보조목적과,다른독립교과에서의직접답/검산trace다.원8M·부모·코드는불변이며기존부모영향제거선택을존중해MTP는scratch/parent×NTP/MTP네팔을지원한다.

### 2. 질문

1. 지문이있는같은22528행에서NTP/MTP의실제답·손실·시간·망각은어떻게다른가?
2. 동일4096root/128updates에서정답만지도한경우와코드로검산한중간단계를지도한경우가어떻게다른가?
3. 잘못된옛assistant턴이CE/MTP목표에들어가지않는가?

### 3. 예측

명시문맥이과거교사전용근거결손을피하지만추출QA편중을해결하지는않는다.MTP의작은CE개선이일반대화개선으로전이되지않을수있다.trace는중간계산을지도하지만목표토큰이6.44배여서계산·표현효과를단독귀속할수없다.모델이훈련문항도못맞히면같은처방을확대하지않는다.

### 4. 단계 설계

Stage3iW0 CPU 회귀 뒤 V2 준비본을 만들었으나, 평가 정답과 공식 TRAIN 정답을 구분하는 metadata가 모호해 V3(3iWd/e/f)로 별도 준비했다. 원형 V2는 보존하며 학습에 사용하지 않는다. MTP는 각32업데이트 비용 뒤4pass704업데이트, 직접답/검산풀이 대조는 각32비용 뒤4pass128업데이트다. 다음 주도 실행에서 이 두 본대조를 우선한다. 부모는 P090B chat32/SHA12E18658…이며 새595M float 부모가 아니다. 미검수 Luna 초안은 자동 편입하지 않는다.

MTP22,528행은 **기존 Broad 명시문맥 교과를 재사용**한 것이며 새로운22,528개 원천을 확보했다는 뜻이 아니다. 기존 NTP 팔과는 본체 부모·native replay 목적·LR이 다를 수 있어, 같은 목적함수 아래 NTP 대조를 새로 두어야 한다. 새 namespace나 마스크 연결을 새로운 일반지능 방법론으로 포장하지 않는다.

공통m8×a16·seq1024·checkpointON·compiledefault·Adam5e-5/Muon2e-4·clip1·4pass를명시한다.옛8M의LR1e-4에서이번LR도바뀌므로옛8M과의차이는묶음비교이며새네팔내MTP효과만대응비교한다.최종test/development문항을교사/GPT로고쳐train에넣지않는다.

### 5. 판정

마스크/턴경계/분모/실제row순회가실패하면학습금지.비용표본을품질점수로세지않는다.주판정은첫자유답의내용·종료·조건교환과원문보존이며고정8질문은canary다.새특정상대분해능은미측정이므로다중seed전일반효과확정금지. MTP추론은과거숫자경로음성을유지하고별도정합측정이필요하다.

### 6. 비용

|교과|고유train 실제x|assistant/pass|행/pass|4pass update|계산slot상한|
|---|---:|---:|---:|---:|---:|
|문맥MTP|5405444|552609|22528|704|92274688|
|직접답|199563|19880|4096|128|16777216|
|검산풀이|307799|128116|4096|128|16777216|

slot은실제지도토큰이나고유지식량이아니다.기존동형704회약25.5분을참고하되MTP/초기compile/새교과시간은cost32실측뒤재산정한다.각본런상한4h·네MTP팔최대16h,reasoning두팔각1h상한으로40h이내편성을목표로하되미측정완료시간을보장하지않는다.

이번 대조는 기존 P101A SFT/MTP 학습기를 재사용하며, native 원문 CE는 전후 평가에만 사용한다. Broad 교과의 추가 native replay gradient를 넣은 목적함수와는 다르므로, 두 결과를 자료만 바뀐 동일 조건으로 비교하지 않는다.

### 7. 실행

`scripts/diag_p101a_clean_bilingual.py --family mtp|direct|trace --mode prepare|calibrate|train --arm parent_ntp|parent_mtp|scratch_ntp|scratch_mtp --execute`.
Reasoning은 parent_ntp만 허용한다. 현재 준비 디렉터리는 `p101a_sft_mtp_cleanbilingual_v3_s1337`, `p101a_sft_mtp_verified_direct_v3_s1337`, `p101a_sft_mtp_verified_trace_v3_s1337`로 분리한다. 네 팔 MTP와 직접답/검산풀이는 서로 다른 SH에 둔다. V2는 metadata 정정 전의 준비 이력으로만 남긴다.

### 8. 한계

Reasoning은읽을수있는짧은코드검산풀이이며학습된잠재thinking/자율진위판정기능이아니다.문맥교과는일반대화전량이나75M완성이아니다.기존검증된SFT엔진을재사용하되기능추가를한것과지능효과를관측한것을구분한다.

### 9. 실제 준비

Stage3i CPU4회귀와 세 코퍼스의 실제 tokenizer/assistant/EOT/mask 준비를 완료했다. 루트 분할은 기존 검산 producer가 언어·표현·교환형을 같은 root에 묶고 원질문은 정답 trace를 포함하지 않는다. 별도 첫답 평가기는 CPU5회귀를 통과했다. MTP는512 DEV의 annotation 문자일치(내용 진실성 아님), Reasoning은 별도1024 TEST의 코드 검산 최종값을 주지표로 기록한다. trace 문법 준수는 최종값 정오와 분리하고 첫답만 저장하며, 검수용 질문·기준답·실제답은 `review_request`의 읽기 쉬운 문서로 내보낸다. 각 본학습·새 벤치마크는 아직 NOT_RUN이며 결과092§15이 실제 준비 로그를 소유한다.

### 2026-10-21 실제 비용 회수와 다음 실행

[결과092§16](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md): 부모MTP/직접답/풀이의32회 비용을 실제 완료했다. 각각 본업데이트만 약1642/282/314초 외삽이며 전체 평가·저장/나머지 세MTP팔은 아직 미측정이다. 실제 모델 환경은 기존 tinylm_env.sh를 source해야 하며 누락한 직접명령의 compile 실패는 따로 보존했다. 새 cost 읽기 검산 helper로 같은 코드·자료·팔·배치·LR의 성공 report만 재사용한다. 없음은 최초측정, 불일치는 해당본학습 HOLD이며 기존report를 지우지 않는다. SH두개는 본실행 NOT_RUN이므로 활성 상태를 유지한다.

### 2026-10-22 17시까지 승인된 본실행 — 실행 전 고정

사용자가 현재 대화에서 CPU/GPU를 2026-10-22 17:00 KST(08:00 UTC)까지 허가했다.
현재 WIP 10~16이 이전 읽기전용 지시 뒤에 추가된 새 권한과 작업 범위를 소유한다.
기존 Stage3jW/3kW와 코퍼스 V3를 재사용하며 학습기·학습 조건·과거 음성 판정은 바꾸지 않는다.
MTP 네 팔은 아직 본실행한 적이 없고 각 부모 계열 안에서 보조 목적 유무만 비교한다.
22,528행은 전체 위키웹 정제본이나 새 Luna 번역본이 아니며 NOT_ADMITTED 후보는 넣지 않는다.

|점검|실행 전 근거와 제한|
|---|---|
|자료·분모|동일 chat32, train x 5,405,444/assistant 552,609를 4pass: x 21,621,776/target 2,210,436, 704업데이트. 패딩 slot 92,274,688과 구분|
|조건|micro8×accum16, ckpt-on, seq1024, Adam5e-5/Muon2e-4, 같은 seed·본체 초기화, 부모 P090B 불변|
|중복·태그|레지스트리 조건 조회 및 태그 충돌 없음 확인. 기존 비용32와 실제704를 혼동하지 않음|
|코드·회귀|기존 clean-bilingual 4회귀 통과. cost 회귀의 direct-file import 실패는 module 실행으로 재확인하며 모델 품질 실패로 세지 않음|
|자원|실제 4070Ti SUPER 16GB/여유 약14.7GiB. MTP 네 팔 총 약3시간은 추정이며 시간·VRAM을 실제 기록|
|종료|단순 상대4시간 cap에 의존하지 않고 총괄 프로세스 전체에 외부 timeout을 적용. 신규 GPU 작업은 16:30 KST 이전 종료하도록 남은 시간으로 제한하여 정리·보고 시간을 확보|
|평가|첫 자유답·종료·부모 대비 원문손실·DEV annotation 일치. DEV는 학습 중 확인한 집합이므로 독립 일반화 성능으로 승격하지 않음. reasoning은 분리된 TEST1024 사용|
|판정|단일 seed 실험 관측. 같은 초기화 내 NTP/MTP만 직접 대응 비교. 일반 대화·벤치마크는 별도 실행 뒤 보고|

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
새 학습 결과가 없던 시점의 계획이며 실제 완료·실패·시간 초과는 후속 실행 이력에 별도로 누적한다.

### 실행 중 발견한 자료 주장 정정 — V3 동결 대조와 별도 V4 후보

[결과092§18](../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)은
PUBLIC정본0-based192/198 두 행의 첫 assistant가 명시 주석 없이 지도된 사실을 소유한다.
‘오답 모두 제외’는 실제 주석 마스크 범위보다 넓은 주장이었다. 이미 시작한 네 팔의 자료를
중간 교체하지 않고 알려진 잡음이 있는 동일 조건 대조로만 회수하며 품질 채택은 하지 않는다.
새V4는 두 행의첫답456targets/pass만 제외한 별도 후보이고, 실제 대화·분할·입력량을 보존한다.
기존 report/PINS/학습 엔진의 의미를 소급 바꾸지 않는다. 버전형 소비자·마스크 검산·새 비용
입장권을 연결하기 전에는 V4로 학습하지 않는다. 입력 한영 균형과 지도 target14.5%/85.5%는
다른 분모이며 향후 자료 구성 대조에서 별도로 통제한다.

### Stage3jWb — 동일 DEV512 부모 첫답 기준선, 재학습 없음

네 팔 비교와 별도로 원 P090B 부모에 **같은 MTP DEV512**를 한 번 평가한다. 기존
`diag_p101a_clean_eval.py --family mtp --arm parent_baseline`을 재사용하며 학습0·재시도0·
FP32 MATH·cacheON·MTP추론OFF·max_new128을 유지한다. 다른 직접답 교과의 TEST1024 부모
평가와는 질문 집합이 다르므로 중복실험이 아니다. 같은512/원문SHA/순서에서 부모·NTP·MTP
첫답/종료를 대조하고 DEV/독립TEST를 혼동하지 않는다. 약8~15분 추정, cap1800초·16:30이전
종료의 현재 권한으로만 실행한다. 출력은 기존 도구의 독립 parent_baseline namespace이며
이미 있으면 재실행·덮어쓰기하지 않는다. 기존 학습 자료/조건/문턱은 바꾸지 않는다.

### Stage3iWh — 별도 V4 자료의 실제 CPU 소비 계약

`scripts/diag_p101a_supervision_v4.py`는 고정한 기존 학습/평가 함수를 직접 재사용한다.
원 V3 파일·원래 ARMS·학습/손실 루프를 수정하거나 복제하지 않는다. CPU 단계에서 실제
수리 V4의 전체22528/512행·x/y/owner 지문·두 교정행의 첫턴 제외·둘째턴/EOT·h1~4와
4pass704의 실제 활성 분모를 검산한다. 모델/CP/GPU0이며 새 토크나이저 학습도 하지 않는다.
소스 전후/실제 import 경로/원 engine.CODE 전체를 고정한 소비 영수증을 별도로 남긴다.

상태는 실험용 소비 검증이지 전량 의미 검수/생산 채택이 아니다. V4 원 report의
NOT_ADMITTED를 그대로 보존한다. 향후 GPU 소비에는 같은 코드/자료의 새 cost32와
CPU계약SHA·정확한 팔/단계·현재 기한·실지출을 묶은 별도 권한이 필요하다. 이번 연결부의
하드 기한은 현재10월22일17시이며 이를 넘는 새 실행 승인을 자동으로 만들지 않는다.
V3 한 팔과 V4 한 팔을 비교하거나 비용을 재라벨해 쓰지 않는다. 오늘은 CPU계약부터
확인하며 V4 추가 학습은 필수 MTP/풀이/방문/평가 작업의 남은 시간 뒤 별도 판단한다.

### Stage3kW 실행 직전 시간 추정 정정

2026-10-22 09:04 KST에 원래 부모의 DEV512 평가가 14.6분으로 끝났다. 질문을 반복하며
출력 128토큰까지 도달하는 답이 많으므로, 다른 TEST1024의 부모 기준선 상한을 기존
1800초에서 3600초로 늘린다. 표본·출력 길이·캐시·정밀도·학습 조건은 그대로이며
실제 답안을 먼저 본 뒤 유리한 질문만 남기는 변경이 아니다. 직접답/검산풀이 두 학습과
세 평가를 합친 전체 예상은 약1.3시간으로 정정한다. 전체 실행에는 외부 상한을 함께
두며 현재 승인 17시 및 모델 종료 목표16:30 KST를 넘기지 않는다.

동일4096개 훈련 루트를 각4회, micro8×accum16의 128업데이트로 비교한다. 두 팔의
입력량과 답 지도량이 다르므로 결과는 ‘검산풀이를 포함한 교육 구성’의 효과이고
동일 토큰 예산에서 추론 능력만 개선된 증거는 아니다. 기존 비용32의 실제 코드·자료
일치 검산 후에만 학습하며 준비된 동일 태그의 본결과가 있으면 재실행하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage3iWi — 같은 micro 배치의 말미 패딩 축소 합성 CPU 회귀

현재 본실험의 고정1024·비용 서명·원자료는 바꾸지 않는다. 별도 작은 무작위 CPU 모델에서
기존 pad_records를 재사용해 동일8개 micro·128개 대화의 순서와 h1~4 분모를 유지한 채
고정1024 대 최장 길이의128배수만 비교한다. CLA1/R1·CLA2/R1·CLA2/R2와 checkpoint-on,
빈 PAD 행·EOT/assistant 경계·prefix hidden·손실·기울기 누적을 검사한다.
정밀도 허용은 기존 관련 회귀의 ATOL/RTOL을 참조하고 실제 차이도 남긴다.

새 파일은 `scripts/test_p101a_padding_crop.py` 하나이며 공용 학습기/기본폭/ARMS/PINS는
바꾸지 않는다. CPU 시험의 모델은 tiny 무작위 fixture뿐이고 실제 CP 로딩/저장·학습 update·
GPU·compile 성능·실물93M gradient·장기 품질은 범위 밖이다. CPU 상한600초이며 원형 로그
`P101A_Stage3iWi_padding_crop_cpu`로 보존한다. PASS여도 현재 GPU 학습을 축소 폭으로
전환하지 않는다. 첫 전체 폭 감사의 모호한 epoch는 별도4개 실제 sampler membership
영수증으로 보완했고 이론 slot 절감을 실제 가속비로 쓰지 않는다.

### Stage3lW: 풀이 학생의 표현·출력지시 연결 CPU 진단 (2026-10-22 사전 계획)

- 질문: 코드 교과 TEST97.95%와 고정 일반8문항0점 사이의 차이가 문제 표면/최종행 지시에도 민감한가? 학습이나 정답 주입 없이 같은 사실에서 원래 표현·구어 표현·구어+원 최종행 요구를 대응 비교한다.
- A는 원 TEST만 재채점(이미 완료, 새 원인 분리 없음), B는 같은 사실의3표현×닫힌 두 학생×8문항(권장·이번), C는 다양한 새 자연어 교과를 재학습(변경축/비용 큼, 이번 진단 후 결정)이다.
- 두 덧셈/조회1/갱신1의4ROOT를 TEST ROOT 사전식 순서에서 정오를 보지 않고 골라 한영8행으로 만든다. 모든 조건·대상·숫자·기록순서를 보존하며 답을 프롬프트에 넣지 않는다. 평가에 이미 본 TEST의 진단이지 새 blind 성능이 아니다.
- 기존 닫힌 학습/첫답/자료/CP/tokenizer/code SHA를 입장 전에 검산한다. 원래 평가기의 존재 가드를 완화하지 않고 별도 namespace를 쓴다. 모델은 순차 CPU로드, FP32 MATH/greedy/cacheON/새토큰128/MTP추론OFF/재시도0/OMP2다.
- 엄격 최종행, 숫자만 정답, 단계 검산, 자연어 미판독을 분리한다. 접두 불일치를 곧 내용 오답으로 판정하지 않는다. ORIGINAL CPU/GPU 답 차이는 표현 효과가 아닌 수치/경로 차이로 별도 기록한다.
- 두 신규 파일을 총괄이 읽고 합성/mock21회귀로 검증한 뒤 원답48요청을 최대900초 CPU로 수집한다. 실제 호출은 외부 timeout TERM900s/kill15s로도 감싼다. 내부 C++ 신호 지연 및 강제종료 때 미닫힌 partial 가능성을 숨기지 않는다.
- 학습0/CP저장0/CUDA초기화금지, 기존 GPU 재귀학습 코드/CP 불변. 새 raw/사람용 질문·답 문서를20MB미만으로 저장한다. 기한 초과는 완료로 승격하지 않는다.
- 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage3m0W/Stage3mW: 지도량을 맞춘 입력 표현 연결의 단일 추가 팔 (2026-10-22 사전 계획)

**목적과 기존 중복 검토.** Stage3kW는 code trace의 제한과제 개선을,3lW는 같은사실의구어체
실패를 실제 확인했다. 과거 P106D fixed/view도 표현/조건변경을 다뤘으므로 그 발상을
처음이라고 주장하지 않는다. 이번은 이미 닫힌 trace128 통제군을 재학습하지 않고,
같은4096ROOT/assistant원문/4pass/128updates에서 user표현만 일부 바꾼 한 팔이다.
숫자·조건·정답·풀이를 바꾸거나 감독량을 늘린 옛 대조와 구분한다.

**대안.** A(권장)는50%원형+50%사실보존 자연어 입력을 같은행수로 대체해 한 팔만 추가한다.
B는 closed trace를 장시간 더 학습하지만 노출/업데이트와표현축이섞인다.
C는전체자유대화자료를새로만들어범위는넓으나현재입력연결원인을분리하지못한다.
A는 관측된 형식밖 연결 취약성을 최소 변경으로 가르며 일반 지능 도약을 보장하지 않는다.

**데이터·평가 동결.** 기존trace TRAIN4096의순서/ROOT/언어/task/assistant를 그대로쓰고,
ROOT해시로원형/자연어를배정한다. 자연어는숫자/주체/질문대상/갱신/기록순서를보존하며
교사·GPT가정답을추정하지않고기존truth/validate_steps로검산한다.
학습3~4개표현과다른TEST표현을사전에정하고한국어조사오류를만들지않는다.
새TEST128ROOT(덧셈64/조회32/갱신32)는기존TRAIN/DEV/TEST및예약사용자질문과
겹치지않는코드가용ROOT에서고정seed로뽑는다. 관측한3lW의4ROOT도제외한다.
각ROOT를한영·구조형/새자연어형/새자연어+기존최종행요구로평가할경우768행이다.
같은TEST를 closed trace와새학생에대응입력하며최종값/단계/형식/미판독을나눈다.
새TEST의정답·실패는학습이나교정에사용하지않는다.

**기존 학습기 재사용.** 새작은어댑터/회귀파일만허용하고원학습기·모델·MTP·재귀코드를
고치지않는다. 같은P090B/seed1337/micro8×accum16/ckptON/seq1024/
LR5e-5/Muon2e-4/compile기본/4pass128을보존한다.
출력target문자·h1지도량은원trace와정확히같아야한다. input x길이는달라질수있어별도계측한다.
새namespace·코드/부모/자료SHA·별도cost32가필수이며기존trace비용을재사용하지않는다.

**시간·권한.** 코드검토/합성회귀→CPU자료/target/누설검산→GPUcost32→현재남은창/
최대wall검산→한팔학습→CPU두모델새첫답회수다. 신규GPU약15~30분은미실측추정이며
cost/평가시간을보고계산한다. 현재재귀/라우터와GPU동시실행을금지한다.
17시사용자기한/16:30모델종료·기록reserve를지키며안맞으면런처만남기고미실행으로보고한다.
학습CP1개외원CP/원문/닫힌원답수정0,다운로드/설치0,미검수Luna후보입장0이다.

**승인 범위와 판정.** 현재사용자의주도적준비/CPU·GPU승인안에서조건부로준비한다.
소스동결/정적·CPU시험은실제모델PASS가아니며코드과제의개선도일상대화성공이아니다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage3n0W/Stage3nW — 2026-10-23 말미 패딩 축소의 실물 등가·GPU 비용

**기존 근거와 새 부분.** Stage3iWi의 합성 CPU7회귀와 원 배치별 slot 계산은 완료했다.
동적 `pad_records`도 이미 구현돼 있다. 이번 새 부분은 같은 실제 chat32 부모·같은 원천
128개/8×16 micro 순서·h1 감독분모에서 고정1024 대 최장길이128배수의 실물 gradient,
한 update, GPU 시간·메모리 대조다. PAD를 없앤 것을 새 지식량이나 데이터 효율 증가로
주장하지 않는다. 기존704 팔의 소스·비용·최종값은 수정하지 않는다.

**선택과 독립변수.** A는 기존 고정폭 유지(새 비용0, 미측정 질문 잔류), B는 순서·실제
원문·마스크를 보존한 오른쪽 PAD만 축소(이번 우선 선택), C는 길이별 재정렬/packing까지
수행(더 큰 이득 가능하나 sampler·문서 경계 교란)이다. B에서는 fixed_width만 변하며
MTP는off, 부모 P090B·LR5e-5/Muon2e-4·ckptON·micro8/accum16·clip1은 유지한다.

**단계와 판정.** 정확 부모/tokenizer/corpus/source SHA를 확인하고 FP32 MATH의 실제
손실·모든 gradient·동일 optimizer 한 update를 비교한다. 수치 허용은 기존 관련 회귀의
ATOL/RTOL을 명시 참조하고 실제 최대 차이·상대 차이도 남긴다. 실패하면 시간을 재더라도
채택하지 않는다. 이어 같은 초기상태로 독립 BF16 eager ABBA 네 블록을 측정하고 warmup,
전체 update, backbone/head 범위, 실제 x/assistant/PAD slot, peak allocated/reserved를
나눈다. 기본 compile 결과나 장기 품질 이득으로 바꾸지 않는다. 외부 CCE/Liger의 통합은
별도 후보이며 이 PAD 대조를 fused CE라고 부르지 않는다.

**비용·보존.** 정확성·시간 각 최대1200초의 독립 진단으로 시작하고 실제 소요에 따라
다음 compile/학습 비용을 판단한다. 재귀·교사·벤치 GPU와 동시에 실행하지 않는다.
메모리상 임시 optimizer update는 있으나 CP 저장·장기학습·원본 수정은0이다.
명시23일16:30 모델 종료/17시 사용자 종료를 지키고, 새 코드·합성 회귀를 root가 읽고
실행하기 전 실제모델 실행은 하지 않는다. 결과092의 새 절·원로그·write-once report로
보존한다. 현재 상태는 설계이며 GPU 실측은 아직 미실행이다.

총괄의 실행 전 고정: 같은 V3 보고 SHA `7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20`을
사용한다. 알려진192/198첫턴·669둘째턴 감독 결함은 보존하며 이 비용 진단으로 채택하지 않는다.
ABBA는 fixed/crop/crop/fixed이고, 각 블록마다 같은 초기화·seed1337에서 첫2update는warmup,
다음4update만 정상상태 계측한다. 시간 진단 총24임시update와 정확성 두 팔 각1update를
분리한다. dropout0·원문순서·전체update분모·optimizer 초기상태를 맞춘다. 기존 CPU 회귀의
loss ATOL1e-5/RTOL1e-4, 누적 gradient/update ATOL2e-6/RTOL1e-5를 명시적으로 GPU에
미보정 적용하고 실제 차이를 기록한다. 실패 후 허용치를 유리하게 바꾸지 않는다.

### Stage3ncW — cuBLAS 작업공간을 구별한 같은 PAD 대조 재개

Stage3nbW 무모델 canary에서 tensor 삭제/GC/empty_cache 뒤8,519,680B가 남았고
명시 cuBLAS 작업공간 해제 뒤0B가 됐다. 원형 진단의0B 입장턱을 높이지 않는다.
새 `--release-cublas-workspace` opt-in만 별도 workspace_v2 namespace를 사용한다.
모델·각 parameter weakref가 모두 소멸했는지 검산하고 지원되는 작업공간 정리 API를
호출한 뒤 실제0B를 다시 요구한다. 원 V1 기본 동작/partial은 보존한다.
손실/gradient/update 허용값, 원천128개/16×8, FP32 MATH 및 BF16 ABBA2+4는 그대로다.
이번 실제 모델의 잔류도 작업공간뿐인지 각 release의 전후 byte/객체 소멸로 확인한다.
전체 모델 학습기·optimizer·정답·CP를 고치지 않으며 새 전체 source SHA를 고정한 후 실행한다.

### 2026-10-23 후속 판정 경계

최신 사용자 정정에 따라 위 소규모 MTP/검산풀이 기록을 본학습 전 지능·벤치 성과의 채택
근거로 삼지 않는다. 작은 실행은 수치 정합·안전·시간 기술 진단만 하고, 새 방법 효과는
고정한 전체 본학습 완료 후 비교한다. 가속은 그 본학습과 최종 평가까지의 전체 시간 단축을
목표로 한다. 기준표§1/P102A 최신 절이 정본이다. 완료 wrapper의 전문은 날짜별 archive로
보존 후 정리했으며 이는 MTP/추론 방법 전체의 폐기나 품질 승인을 뜻하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
