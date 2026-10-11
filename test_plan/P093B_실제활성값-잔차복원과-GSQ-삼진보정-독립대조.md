# P093B — 실제 활성값 잔차 복원과 GSQ 삼진 보정 : 기존 MLP/LoRA로 A/B를 독립 검증

> 계기: 사용자2026-10-09 LittleBit/GSQ/RCO 검토·A/B 독립 대조·신규 계획/SH/추가구현 요청.
> [P093](P093_구조조건부-직접공유와-완화타잉.md)·[결과086 §4](../test_result/086_20260919_P093-회계상-R1은-남고-D1은-고계산이다.md)·[논문 리뷰08 §8](../docs/methods/08_paper_review2.md).
> 2026-10-10 [결과103](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md): A r8/16과GSQ식B는실제보정후문턱미달, factor는미호출HOLD다. 후속분할/LR·r32/64/실제답·정밀도게이트는준비/실물NOT_RUN이다.

## 1. 왜 — 함수 복원과 양자화 손실을 분리

P093의0.75% 개선은 Gaussian128입력·raw master·rank4/8/16 근사다. 반면 기존 ternary-LoRA의 실제 ordinary CE 학습 이력은 있다([결과001](../test_result/001_20260723222103_dense-tied-300M-기준선-손실격차.md)). 모든 보정층 학습이 미실행이었다고 부르지 않는다.

현재 MLP에는 층별 LoRA 슬롯, LoRA에는 D/U 삼진화와 작은 rank의 per-row 처리가 있다. 새 슬롯·별도 binary kernel을 복제하지 않고 실제 활성값·잔차 초기화·함수 목적·GSQ식 배정/scale·저장검증을 추가한다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 첫 middle4층의 r8/16 잔차가 native 원출력을 복원하는가 | 작은 인자의 표현/최적화 한계 확인 |
| Q2 | 같은 공유 본체의 삼진 배정만 개선하는가 | A와 B의 손실 원인 분리 |
| Q3 | 유효 A 인자를 기존 삼진 LoRA로 보정/복원할 수 있는가 | LittleBit 이진화 강제 없이 검증 |
| Q4 | local 오차·CE·bytes·wall이 어떤가 | 지능/배포 이득과 구분 |

## 3. ★예측 — 정직하게

실제 LN 이후 활성값과 native 함수, residual 초기화는 old Gaussian 근사보다 맞을 수 있다. 하지만 네 층 차이가 고rank에 퍼졌다면 r8/16은 실패할 수 있다. B는 공유 역할 차이를 해결하지 못할 수 있다. 삼진 인자·Gumbel/Lion도 손상/수렴 실패가 가능하다. 음성은 원인 분리 정보로 보존한다.

## 4. 단계 설계 (싼 것 → 비싼 것)

### Stage0W — native slot·초기화·배정·복원 CPU 계약 (완료: 기술0)

CPU tensor fixture로 원형 불변·0-no-op·gradient 소유·weighted-SVD·삼진 group/rank·artifact SHA/20MB를 검증한다. 부모/cache/GPU 실행 없음이다.

### Stage1Wa — A: 실제 활성값 함수 잔차 (완료: 과학적 음성8)

정확 부모 `runs/ckpt/m100s12_ko-en_300M_d16_cla2_norecur_rms4.pt`, source `data_cache/ko-en_600000000/train.bin`이다. 사용자 실행에서16층/untied/CLA2 및 mode/FiLM/LRM/기존LoRA 부재를 확인한다. 첫 middle4층만 바꾸며 attention/prelude/coda/embedding은 고정한다.

native MLP input/output hook을 실제 토큰 창에서 수집한다. calibration/held-out 창을 먼저 고정하고 offset/선택 bytes/활성값 hash를 보존한다. shared core는 master mean 뒤 native 삼진화하고 동결한다. 기존 LoRA r8/r16의 실수 인자에 residual/data-aware SVD 초기화 후 **SwiGLU 출력 목적**으로250update/AdamW LR1e-3/WD0/seed1337을 적용한다. 이는 정상 SFT의 micro/accum/Muon 변경이 아닌 local calibration이다.

### Stage1Wb — B: 공유 삼진 배정·scale (완료: 과학적 음성8)

A 성공에 종속하지 않고 같은 parent/source/offset/참조로 실행한다. shared core의 mask/sign logits와 양수 group scale을 Gumbel-Softmax/Lion으로 보정하고 층별 delta는 없다. hard eval을 보존한다. 공식 whole-model GSQ의 성능 재현이 아닌 GSQ 파라미터화/목적의 소형 구현이다.

### Stage2W — 독립 A/B 대응 판독 (완료: 대응0)

부모/입력/분할/코드 지문이 같아야 비교한다. shared/init/fitted의 local NRMS·층별 오류·grad_max·wall·VRAM와 같은 held-out token창의 전체 CE를 기록한다. A/B 구조와 optimizer가 달라 그 둘의 차이를 단일 알고리즘 효과로 귀속하지 않는다.

### Stage3W — 조건부 GSQ 삼진 인자·native LoRA round-trip (종료: 선결HOLD8·실물NOT_RUN)

A의 사전등록 r16 viability 뒤에만 해당 인자의 현재 `ternary_g` 전/후와 GSQ 배정/scale 보정을 비교한다. export된 D/U를 기존 `LoRA(bits=2)`로 복원해 정합/NRMS/CE를 기록한다. 직접 packed kernel 가속은 아니다. RCO는 후보별 byte/효용 DB가 준비된 후의 별도 단계다.

### Stage0bW — 복구 계약 CPU / 완료0

사용자2026-10-10 선택으로 기존r8/16 실제 음성 이후의 분할·LR·중간점 대조와 별도r32/64 표현력 대조를 모두 준비한다. 기존GSQ 배정B(Stage1Wb)와 후속의 ‘표현력 B’는 다른 질문이다.

### Stage4Wa — dev 선택 r8/16 대조 / 완료·과학적 음성8

같은 정확부모·first-middle4·source32창을 먼저 고정한다.24앞창을 train16창/2048위치, dev4창/512위치, test4창/512위치로 분리하고 마지막8창은 별도wholeCE용이다.4층 관측수를 다른텍스트 수로 부풀리지 않는다.
같은 weighted-SVD 초기인자를 복사해LR1e-3/1e-4·AdamW/WD0·250update를 대조하며0/20/50/100/250회 train/dev 곡선을 보존한다. rank별 LR/종료시점은dev만으로 고르고 test를 optimizer/선택 함수에 넣지 않는다.
부모·shared-only·선택후 각rank의 실제 한영8질문 첫답/종료를 보존한다. local음성이어도 추론자료는 남기며 회수 후 GPT가 의미를 판독한다.

### Stage4Wb — 같은 분할/절차 r32/64 / 완료·과학적 음성8

r8/16 성공에 종속하지 않는다. rank를32/64로만 바꾼 같은 LR/초기화/분할 절차다. r64 FP32 인자8.25MiB의비용을 함께 공개하며 추가표현력이 실제 함수와답안에서효용을내는지본다. independenttest는 최종평가이며 이후rank를낮은test점수만으로고르지않는다.

### Stage4Wc — 대응 자료·원답 CPU 판독 / 완료0

두 report의 parent/window/train/dev/test/코드SHA와실물완료를검산한다. 실제문구판독을 CPU 완료로대체하지않는다.

### Stage5W — 조건부 저장 정밀도·native삼진 미리보기 / 종료·선결보류8

유효한 unquantized capacity rank가 없으면모델시작전HOLD8이다. 통과한각r32/64에서FP32참조·FP16저장왕복(FP32실행)·현재native삼진인자왕복의test/wholeCE/실제8답/byte를비교한다. FP16resident/kernel이나GSQ인자추가최적화/RCO전체는아직아니다. 재구성함수·서버sampler·정상SFT기본을바꾸지않는다.

후속 실물은아직NOT_RUN이다. 시간후보는A/B/precision각0.5h(상한3600초)·CPU각.02h다. 진단parent상주를deployment RSS와혼동하지않으며artifact는projection별20MB이하다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| input/지문/gradient/복원 불일치·비정상 값 | 기술오류9 |
| local held-out NRMS≤0.90·shared 대비 오류감소≥10% | local viability0, 지능/배포 PASS 아님 |
| local 기준 미달 | 과학적 음성8, B는 계속 독립 |
| 전체 CE/속도 | 관측과 분모만. 새로운 calibration/Muon σ 없음으로 과거 자 복사 금지 |
| bytes/상주 | 실제 dtype·진단 parent 상주·export 분리. bits=16 표기가 FP16 master 보증 아님 |

[기준표](../docs/EXPERIMENT_BASELINES.md)·[ruler](../scripts/_rulers.py)가 정본이다. old P093 최소실용 floor를 실제활성값 목적에 사전등록하고 언어손실 σ로 사용하지 않는다. parent forward token과 calibration activation presentations를300M 학습량으로 바꾸지 않는다.

## 6. 비용

| 단계 | 비용 후보/상한 | GPU |
|---|---:|---|
| Stage0W | CPU 약1분 | N |
| Stage1Wa/Stage1Wb | 각각0.5~1h 추정,3600초 cap | Y 사용자 |
| Stage2W | CPU 약1분 | N |
| Stage3W | 0.5~1h 추정,3600초 cap | Y 사용자·조건부 |

init/수집/보정/eval 시간을 나눠 공개한다. 실물 자원 미계측이다. d768/f2048/4층/r16 FP32 인자 한 벌 약2.063MiB 외에 참조/활성/optimizer가 추가다. 진단은 원부모를 보존하므로 active graph의 가상절감과 실제 process RSS를 혼동하지 않는다. projection별 artifact20MB 상한을 지킨다.

## 7. 실행 → 사용자 WSL SH

- `run_P093B_Stage0bW_recovery_contract.sh`
- `run_P093B_Stage4Wa_dev_selected_rank8_16.sh`
- `run_P093B_Stage4Wb_dev_selected_rank32_64.sh`
- `run_P093B_Stage4Wc_recovery_actual_answers.sh`
- `run_P093B_Stage5W_factor_precision_roundtrip.sh` (유효한 unquantized capacity rank 뒤에만)

입력 대기 없음·새 namespace·write-once·phase/final 판정이다. [결과103](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)에 옛5단계의 정확 재현 명령/Git 복구점이 있다. 새5SH는 [복구 driver](../scripts/diag_p093b_calibration_recovery.py)·[dev 선택 helper](../scripts/p093b_calibration_recovery.py)를 사용하며 STATIC_ONLY/새 모델 NOT_RUN이다. 일반300M·기본 모델 변경은 없다.

## 8. 한계 (반드시 함께 기록)

첫4층 함수 보정은 전체훈련·SFT·지능·32/40MiB 배포 목표 성공이 아니다. old pool 노출/누설로 CE도 지식 일반화 증거가 아니다. teacher-captured 입력의 성공이 후보 hidden 분포에 그대로 전이되지 않을 수 있어 full forward를 별도로 본다. 새 binary kernel·전층 RCO·보호자료·원부모 변경은 없다.

## 9. 실행 이력 / 갱신

- 2026-10-09 신규 준비 착수. 기존 MLP/LoRA/삼진 경로를 재사용한다. 실물/GPU/실제 활성값 수집은 NOT_RUN이다.
- preflight: 독립변수 A=층별잔차, B=공유배정; 같은 parent/source/참조. registry 기본/--tag/--plan은 broad runs JSON을 읽으므로 Codex는 금지 경계를 지키며 명시 출력충돌·공개 기록으로 제한 확인한다.
- 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

- 2026-10-10 원형5로그/정본5회수: 실제활성값/SVD초기화가능성은미달. rank8/16의초기소폭이득이250회뒤사라져‘현재조건에서복원문턱을넘는다’는예측은기각한다. B도10%문턱미달,삼진factor는선결HOLD로실물실패가아니다.
- 사용자A+B 선택: train/dev/test·LR/endpoint/r32/64/실제8답·조건부FP16storage/native삼진을새단계로준비했다. 새실물효용·GPT답안판독·배포손익은NOT_RUN이다.

## 10. 2026-10-11 회수와 무학습 반복 원인진단

[결과103 §8~§9](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)에서 Stage0bW/4Wc는완료0,4Wa/4Wb는실제보정종료8,5W는선결HOLD8로회수했다. dev 선택이 늦은 과적합을 줄일 예측은 일부 관측됐지만 모든 rank의 test NRMS/10% 회복선은 여전히 미달이다. 부모도 질문을 반복하므로 r64가 반복을 새로 만들었다는 예측은 성립하지 않는다.

### Stage6aW — 생성·cache·입력 계약 CPU 준비 / STATIC_ONLY

`run_P093B_Stage6aW_generation_contract.sh`는 새 helper/entry의 nucleus 확률·few-shot prefix·원형 재사용·체크포인트 접근 없는 check-only·partial 보존 계약을 검사한다. namespace `p093b_generation_v1_s1337`, CPU0.02h·600초 cap. 새 실물 NOT_RUN이다.

### Stage6bW — 같은 부모/shared/r64의 prompt×decoder 원인진단 / 사용자 GPU NOT_RUN

`run_P093B_Stage6bW_parent_shared_r64_decode.sh`; 새 가중치/optimizer/체크포인트 저장0. parent SHA A402BF1D…·원형 recovery capacity report4C8D5952…·legacy32를 유지한다. 원형 plain-greedy24답은 재사용하며 few-shot 예시는 평가 gold와 다른값을 쓴다. plain/few-shot ×greedy/nucleus(p.95,t1,3seed)를 대응해 새168답, 추가 cache-off plain-greedy24답을 남긴다. 총 새192답이며 같은 문구 재생성을 semantic 승인으로 세지 않는다.

native sampler에는 top_p 인자가 없어 진단 scope에서 multinomial 확률만 nucleus로 바꾸고 복제 generation 루프를 만들지 않는다. 실제24 cache text/finish/count 대응은 전체 logit bitwise 증명과 구분한다. source/코드/원답 지문·종료·실제 질문/답을 콘솔과20MB 이하 shards로 남긴다. 0.25h 추정·1800초 cap이며 partial 원답도 보존한다.

판정: 완결/원형/마스크/추출은 기술계약, 반복·정답·조건·종료·속도는 분리 관찰. cache 불일치 시 구현/정밀도 진단을 먼저 이어가고 반복 억제 학습으로 덮지 않는다. few-shot/nucleus가 좋아져도 새 지식을 학습한 것이 아니다.

## 11. C 반복억제의 조건부 최적안

[논문 검토08 §10](../docs/methods/08_paper_review2.md)에 UL/DITTO 외 ScaleGrad·SimCTG·contrastive decoding·DPO·ORPO·SimPO·전체 출력분포 보존을 검토했다. 우선은 A 원답을 회수한다. C 후보는 지시/종료 SFT 기준선과 reference-free ORPO의 후행 판독 쌍 대조이며 정상복사/유일답/코드/JSON 보호·train/dev/test 분리·토큰/업데이트 대응·망각 검증이 필요하다. C 신규 학습/손실 구현은 미착수, 선택·별도 범위 승인 전 실험을 열지 않는다. 과거 local 문턱과 기본 SFT 레시피를 변경하지 않았다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 12. 사용자 추가 선택 — SFT/ORPO와 표현 진단/SimCTG 우선 보존

사용자는1안과2안을우선채택하고저비용표현진단부터요청했다. 이는새C학습실행승인이아니다. 실제체크포인트/GPU진단은일반질문으로별도범위를확인하며승인전에는CPU회귀와SH준비만한다.

### Stage6cW — 저장 원답의 마지막 hidden 소형 관찰 / 준비·실물NOT_RUN

`run_P093B_Stage6cW_hidden_representation_observation.sh`, 약0.08h추정/전체600초cap. 동일parent/shared/r64·기존8prompt와그prompt+저장원답의48forward만한다. return_hidden으로head logits/KVcache/새답생성을하지않고최종RMSnorm hidden만읽는다. source/토크나이저/보정원형 SHA는같으며optimizer/체크포인트쓰기0이다.

위치수≤256·finite/0norm검사·같은tokenID쌍과다른tokenID쌍의cosine을분리한다. 중심화한단위벡터Gram의eigenvalue정규화로covariance entropy rank를보고하며특정점수로자동‘표현붕괴/오답’을판정하지않는다. 같은token을쓴정상JSON/코드반복의높은유사성과서로다른token도비슷한경우를혼동하지않는다.8개의짧은과제/루프 원답이므로일반LM isotropy나반복의인과를증명하지못한다. 낮은rank가보이면정상문장/다른부모의후속대조가필요하다.

Stage6aW의최신CPU계약뒤6cW표현관찰을6bW긴원답진단보다먼저회수할수있다. 기본SFT/함수복원기준은불변이고C의SimCTG/ORPO 손실은후속설계·별도학습권한을필요로한다.
