# P093B — 실제 활성값 잔차 복원과 GSQ 삼진 보정 : 기존 MLP/LoRA로 A/B를 독립 검증

> 계기: 사용자2026-10-09 LittleBit/GSQ/RCO 검토·A/B 독립 대조·신규 계획/SH/추가구현 요청.
> [P093](P093_구조조건부-직접공유와-완화타잉.md)·[결과086 §4](../test_result/086_20260919_P093-회계상-R1은-남고-D1은-고계산이다.md)·[논문 리뷰08 §8](../docs/methods/08_paper_review2.md).
> 원래 근사 음성을 보존하는 분리 후속 파일이다. 새 실물은 `NOT_RUN`이다.

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

### Stage0W — native slot·초기화·배정·복원 CPU 계약

CPU tensor fixture로 원형 불변·0-no-op·gradient 소유·weighted-SVD·삼진 group/rank·artifact SHA/20MB를 검증한다. 부모/cache/GPU 실행 없음이다.

### Stage1Wa — A: 실제 활성값 함수 잔차

정확 부모 `runs/ckpt/m100s12_ko-en_300M_d16_cla2_norecur_rms4.pt`, source `data_cache/ko-en_600000000/train.bin`이다. 사용자 실행에서16층/untied/CLA2 및 mode/FiLM/LRM/기존LoRA 부재를 확인한다. 첫 middle4층만 바꾸며 attention/prelude/coda/embedding은 고정한다.

native MLP input/output hook을 실제 토큰 창에서 수집한다. calibration/held-out 창을 먼저 고정하고 offset/선택 bytes/활성값 hash를 보존한다. shared core는 master mean 뒤 native 삼진화하고 동결한다. 기존 LoRA r8/r16의 실수 인자에 residual/data-aware SVD 초기화 후 **SwiGLU 출력 목적**으로250update/AdamW LR1e-3/WD0/seed1337을 적용한다. 이는 정상 SFT의 micro/accum/Muon 변경이 아닌 local calibration이다.

### Stage1Wb — B: 공유 삼진 배정·scale

A 성공에 종속하지 않고 같은 parent/source/offset/참조로 실행한다. shared core의 mask/sign logits와 양수 group scale을 Gumbel-Softmax/Lion으로 보정하고 층별 delta는 없다. hard eval을 보존한다. 공식 whole-model GSQ의 성능 재현이 아닌 GSQ 파라미터화/목적의 소형 구현이다.

### Stage2W — 독립 A/B 대응 판독

부모/입력/분할/코드 지문이 같아야 비교한다. shared/init/fitted의 local NRMS·층별 오류·grad_max·wall·VRAM와 같은 held-out token창의 전체 CE를 기록한다. A/B 구조와 optimizer가 달라 그 둘의 차이를 단일 알고리즘 효과로 귀속하지 않는다.

### Stage3W — 조건부 GSQ 삼진 인자·native LoRA round-trip

A의 사전등록 r16 viability 뒤에만 해당 인자의 현재 `ternary_g` 전/후와 GSQ 배정/scale 보정을 비교한다. export된 D/U를 기존 `LoRA(bits=2)`로 복원해 정합/NRMS/CE를 기록한다. 직접 packed kernel 가속은 아니다. RCO는 후보별 byte/효용 DB가 준비된 후의 별도 단계다.

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

- `run_P093B_Stage0W_native_repair_contract.sh`
- `run_P093B_Stage1Wa_activation_residual.sh`
- `run_P093B_Stage1Wb_gsq_native_assignment.sh`
- `run_P093B_Stage2W_repair_pair_readback.sh`
- `run_P093B_Stage3W_gsq_factor_roundtrip.sh`

입력 대기 없음·새 namespace·write-once·phase/final 판정을 사용한다. 원본로그 번호103 예약, 실물 회수 때 결과문서 작성이다. 기존086을 덮지 않는다.

## 8. 한계 (반드시 함께 기록)

첫4층 함수 보정은 전체훈련·SFT·지능·32/40MiB 배포 목표 성공이 아니다. old pool 노출/누설로 CE도 지식 일반화 증거가 아니다. teacher-captured 입력의 성공이 후보 hidden 분포에 그대로 전이되지 않을 수 있어 full forward를 별도로 본다. 새 binary kernel·전층 RCO·보호자료·원부모 변경은 없다.

## 9. 실행 이력 / 갱신

- 2026-10-09 신규 준비 착수. 기존 MLP/LoRA/삼진 경로를 재사용한다. 실물/GPU/실제 활성값 수집은 NOT_RUN이다.
- preflight: 독립변수 A=층별잔차, B=공유배정; 같은 parent/source/참조. registry 기본/--tag/--plan은 broad runs JSON을 읽으므로 Codex는 금지 경계를 지키며 명시 출력충돌·공개 기록으로 제한 확인한다.
- 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
