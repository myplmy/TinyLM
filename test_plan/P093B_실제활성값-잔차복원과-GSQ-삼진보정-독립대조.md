# P093B — 실제 활성값 잔차 복원과 GSQ 삼진 보정 : 기존 MLP/LoRA로 A/B를 독립 검증

> 계기: 사용자2026-10-09 LittleBit/GSQ/RCO 검토·A/B 독립 대조·신규 계획/SH/추가구현 요청.
> [P093](P093_구조조건부-직접공유와-완화타잉.md)·[결과086 §4](../test_result/086_20260919_P093-회계상-R1은-남고-D1은-고계산이다.md)·[논문 리뷰08 §8](../docs/methods/08_paper_review2.md).
> 초기2026-10-10 r8/16·GSQ식B의복원음성과factor선결HOLD는유지한다. 최신2026-10-11 [결과103 §8~§12](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md):dev선택/r8~64실물·표현48·실제반복24답/2186step회수. precision은선결HOLD,고정precision수치원인·C새학습은NOT_RUN이다.

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

이 절의 준비시점 예상은A/B/precision각0.5h(상한3600초)·CPU각.02h였다. 현재실물회수는§10과결과103 §8에기록했으며정밀도는선결HOLD로모델미호출이다. 진단parent상주를deployment RSS와혼동하지않으며artifact는projection별20MB이하다.

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

## 7. 초기 복구 실행 이력 → 현재 완료·Git 보존

- `run_P093B_Stage0bW_recovery_contract.sh`
- `run_P093B_Stage4Wa_dev_selected_rank8_16.sh`
- `run_P093B_Stage4Wb_dev_selected_rank32_64.sh`
- `run_P093B_Stage4Wc_recovery_actual_answers.sh`
- `run_P093B_Stage5W_factor_precision_roundtrip.sh` (유효한 unquantized capacity rank 뒤에만)

위5SH는이제역사적완료이력이다. [결과103 §8](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)의원형969761e/-done/SHA/명령보존뒤사용자승인범위에서삭제했다. 현재큐에서없는파일을다시권하지않는다. [복구 driver](../scripts/diag_p093b_calibration_recovery.py)·[dev 선택 helper](../scripts/p093b_calibration_recovery.py)의실물보정음성과precision선결HOLD를구분하며일반300M·모델기본변경은없다. 새계측/현재다음단계는§10~§16이다.

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

### Stage6aW — 생성·cache·입력 계약 CPU 본체 완료 / wrapper NOT_RUN

`run_P093B_Stage6aW_generation_contract-done.sh`의 CPU 본체10시험은 직접 실행 완료이며 SH/runlog wrapper는 NOT_RUN이다. namespace `p093b_generation_v1_s1337`의 계약 report를 보존해 재실행하지 않는다. nucleus·few-shot·원형 재사용·check-only·partial 보존의 CPU 계약이며 모델 품질/Stage6bW 실행 증거는 아니다.

### Stage6bW — 같은 부모/shared/r64의 prompt×decoder 원인진단 / 사용자 GPU NOT_RUN

`run_P093B_Stage6bW_parent_shared_r64_decode.sh`; 새 가중치/optimizer/체크포인트 저장0. parent SHA A402BF1D…·원형 recovery capacity report4C8D5952…·legacy32를 유지한다. 원형 plain-greedy24답은 재사용하며 few-shot 예시는 평가 gold와 다른값을 쓴다. plain/few-shot ×greedy/nucleus(p.95,t1,3seed)를 대응해 새168답, 추가 cache-off plain-greedy24답을 남긴다. 총 새192답이며 같은 문구 재생성을 semantic 승인으로 세지 않는다.

native sampler에는 top_p 인자가 없어 진단 scope에서 multinomial 확률만 nucleus로 바꾸고 복제 generation 루프를 만들지 않는다. 실제24 cache text/finish/count 대응은 전체 logit bitwise 증명과 구분한다. source/코드/원답 지문·종료·실제 질문/답을 콘솔과20MB 이하 shards로 남긴다. 0.25h 추정·1800초 cap이며 partial 원답도 보존한다.

판정: 완결/원형/마스크/추출은 기술계약, 반복·정답·조건·종료·속도는 분리 관찰. cache 불일치 시 구현/정밀도 진단을 먼저 이어가고 반복 억제 학습으로 덮지 않는다. few-shot/nucleus가 좋아져도 새 지식을 학습한 것이 아니다.

## 11. C 반복억제의 조건부 최적안

[논문 검토08 §10](../docs/methods/08_paper_review2.md)에 UL/DITTO 외 ScaleGrad·SimCTG·contrastive decoding·DPO·ORPO·SimPO·전체 출력분포 보존을 검토했다. 우선은 A 원답을 회수한다. C 후보는 지시/종료 SFT 기준선과 reference-free ORPO의 후행 판독 쌍 대조이며 정상복사/유일답/코드/JSON 보호·train/dev/test 분리·토큰/업데이트 대응·망각 검증이 필요하다. C 신규 학습/손실 구현은 미착수, 선택·별도 범위 승인 전 실험을 열지 않는다. 과거 local 문턱과 기본 SFT 레시피를 변경하지 않았다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 12. 사용자 추가 선택 — SFT/ORPO와 표현 진단/SimCTG 우선 보존

사용자는1안과2안을우선채택하고저비용표현진단부터요청했다. 이는새C학습실행승인이아니다. 실제체크포인트/GPU진단은일반질문으로별도범위를확인하며승인전에는CPU회귀와SH준비만한다.

### Stage6cW — 저장 원답의 마지막 hidden 소형 관찰 / 완료0·표현인과 미확정

`run_P093B_Stage6cW_hidden_representation_observation.sh`, 약0.08h추정/전체600초cap. 동일parent/shared/r64·기존8prompt와그prompt+저장원답의48forward만한다. return_hidden으로head logits/KVcache/새답생성을하지않고최종RMSnorm hidden만읽는다. source/토크나이저/보정원형 SHA는같으며optimizer/체크포인트쓰기0이다.

위치수≤256·finite/0norm검사·같은tokenID쌍과다른tokenID쌍의cosine을분리한다. 중심화한단위벡터Gram의eigenvalue정규화로covariance entropy rank를보고하며특정점수로자동‘표현붕괴/오답’을판정하지않는다. 같은token을쓴정상JSON/코드반복의높은유사성과서로다른token도비슷한경우를혼동하지않는다.8개의짧은과제/루프 원답이므로일반LM isotropy나반복의인과를증명하지못한다. 낮은rank가보이면정상문장/다른부모의후속대조가필요하다.

Stage6aW의최신CPU계약뒤6cW표현관찰을6bW긴원답진단보다먼저회수할수있다. 기본SFT/함수복원기준은불변이고C의SimCTG/ORPO 손실은후속설계·별도학습권한을필요로한다.

## 13. 2026-10-11 Stage6cW 허가된 실물 관찰 완료

[결과103 §10](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)의sameparent/shared/r64·8prompt/저장답포함48forward는GPU0/NOT_RUN 준비상태를**금번한정실물완료0**으로갱신한다. CPU계약10회귀뒤runlog약9초/본체3.533945초,학습·새생성·checkpoint쓰기0이다. oldmode/원형은불변이다.

다른token이모두같은표현으로붕괴하는것은관측되지않았고sameprompt의cosine·covrank 차이는작은관찰이다. ‘SimCTG가필요하다’는인과예측은이번실험으로확증되지않았다. 반대로8shortprompt/정상응답대조없음으로SimCTG를기각하지도않는다. 이미준비된6bW의cache/decoder/fewshot이별도실행선결이다. 사용자1안 ORPO/SFT·2안 표현/SimCTG의추가학습은미실행이다.

실행한6cW SH는재현명령/117f460의원형SHA/mode를보존해-done개명후사용자승인범위의해당1개만삭제했다. 다음권장큐에서는이단계를완료이관하고반복실행으로시간을채우지않는다. 6aW의직접CPU본체/새code contract도완료이며SH wrapper E2E와분리한다.
## 14. 저장 표현 관찰의 재검토

Stage6aW의 CPU 본체10시험은 완료이며 wrapper 실행은 NOT_RUN으로 구분한다. 완료 파일은 `run_P093B_Stage6aW_generation_contract-done.sh`에 보존한다.
Stage6cW의48forward는8질문×3조건×2입력이지48독립질문이 아니다. 동일prompt의168위치/조건은 대응하지만 각 조건의 저장답을 붙인 입력은7/8질문에서 달라 기술 관찰로만 비교한다. 중심화한covariance rank의 상한은문장당N−1이며768차원과 직접 비교하지 않는다.
실제 생성 중의 로짓·EOS·KV·층별 시간 변화를 측정하지 않았으므로 반복 시작 원인검증으로 충분하지 않다. 새 단계는 이 누락을 겨냥한다. 과거 관찰을 실패·인과PASS로 바꾸지 않는다.

## 15. 실제 반복 시작점 — Stage6dW/6eW/6fW

### 조건·변경 축

실제 반복 시작점은 옛8문항의 native greedy sample(max96,temperature0,top_k1,같은seed·cacheON) 24시퀀스로 재현한다. 모델·토크나이저·r64 manifest와3projection SHA를 원형보고서에 묶고 별도 p093b_live_trace_v1_s1337에 저장한다.
새 변수는 읽기 전용 hook 관찰과 동일한 실제 prefix의 cache-OFF 그림자 forward다. native sampler·가중치·초기질문·정밀도·학습 레시피는 바꾸지 않는다. CUDA BF16의 cached/noncached 차이는 bitwise 같음이 아니라 logit차이/argmax 일치로 보고한다.

### 단계·선결·권한

| 단계 | 런처 | 측정 | 비용/실행 |
| --- | --- | --- | --- |
| Stage6dW 완료0 | `run_P093B_Stage6dW_live_trace_contract-done.sh` | hook 불변·선택ID·KV prefix·출력 manifest CPU14회귀 | 실측0.058초. GPU/모델0 |
| Stage6eW 완료·기술8 | `run_P093B_Stage6eW_repetition_onset_live_trace-done.sh` | 옛24답 재현·2186step 로짓/KV/16층·동일prefix cacheOFF | 본체115.916848초. 옛KV불변/6argmax차이,학습/save0·권한종료 |
| Stage6fW 완료·선행기술8 | `run_P093B_Stage6fW_live_trace_readback-done.sh` | 동일코드·실물24시퀀스·shard SHA/행수·기술 판정 회수 | CPU 회수 완료. 추가모델0 |

최대24×96=2304개의 primary token선택과 같은 수의 cache-OFF forward를 기록한다. prefilling은각시퀀스첫step에포함된다. 원형 namespace·runs/HF/cache를 쓰지 않으며 JSONL은20,000,000bytes 이하로 나눈다. 시간초과/부분결과는 보존하고 자동 cleanup/재시작·입력대기를 두지 않는다. 다음 실물 실행은 현재승인의 영구 연장이 아니다.

### 방법·판정·예측

- 반복 후보는 같은 tokenblock이3번 이어지는 경우다. 첫블록·두번째블록 시작(반복 onset)·세번째 완결(확인)을 모두 기록한다. onset 앞뒤3step을 연결하며 정상 숫자/복사/코드의 반복을 품질 불합격이나 재생성 조건으로 삼지 않는다.
- native head의 top10·margin·entropy·EOS확률·기존생성/질문 token집합의 확률질량을 기록한다. logit는 마지막 입력위치에서 다음token을 고르는 값임을 명시한다.
- 실제owner별KV 길이/dtype/bytes·기존prefix 불변·새K/V와직전token의 차이를 기록한다. 각16층의 attention잔차/MLP잔차·출력과직전위치 변화 및 동일prefix shadow 차이를 대응한다.
- 과거24답의 text/finish/count 일치와 모든cached/shadow argmax·KVprefix 정합은 기술판정이다. 반복/나열은 실제답을 별도 읽어 해석한다. 시간·층변화의 동반은 특정층의 인과증명이 아니다.
- 예측: 반복문구가 재현된다면 onset 창에서 copy질량/종료확률/층변화 패턴을 관찰할 수 있다. KV가 정합이면 캐시 누적손상이 관측 반복의 직접 원인이라는 가설은 약해지지만 모델 전체구현·모든입력의 무결성을 증명하지는 않는다. 정상응답 대조나 선택적 개입 없이 SimCTG/ORPO 필요성을 확정하지 않는다.
- hook을 단 관찰 시간은 순수 추론속도 벤치마크로 쓰지 않는다. 피크는 PyTorch tensor allocated/reserved이며 전체VRAM과 혼동하지 않는다.

현재 코드는 CPU 검증 후 실물1회만 수행한다. Stage6bW의prompt×decoder 장행렬이나 새C학습을 대리 실행하는 승인이 아니다.
## 16. 실제 반복 trace 회수·예측 대조·권한 종료

Stage6dW CPU14(0.058초)/0,6eW 실물24답/2186step(115.916848초)/8,6fW SHA/행수판독/8로회수했다. 정확3SH는동일본문-done으로보존하고추가삭제0이다.
[결과103 §12](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)에서옛24원답재현·옛KVprefix불변은맞았으나cached/uncached argmax전부일치예측은6건에서틀렸다. 부모와r64의같은블록위치에서copy선호강화/EOS감소,shared단일token루프에서층출력근접을실제관측했다. 그래도정상응답·동일위상벡터·정밀도개입없음으로인과나특정C손실효용은미확정이다.

새runtime승인은이번약123초실행으로종료했다. 다음은6불일치prefix의FP32/math수치대조범위를사용자와정한뒤준비하며6bW를자동재실행하지않는다. 어느후속도이번권한의영구연장/기본레시피변경이아니다. 기존원형namespace를삭제하고재시작하지않는다.
## 17. 추가 승인 — 반복 피드백·공유 MLP·층상태의 제어 개입

사용자는2026-10-12 반복의원인/결과·공유MLP/재귀기여를진단하도록CPU+GPU를추가허가했다. 새 `p093b_causal_v1_s1337`에서최대600초·학습/체크포인트쓰기0으로준비한다. 원형24답과2186trace는그대로보존한다.

### 원인 가설·방법·한계

[DITTO 원문](https://proceedings.neurips.cc/paper_files/paper/2022/file/148c0aeea1c5da82f4fa86a09d4190da-Paper-Conference.pdf)의수동반복prefix로다음선호를측정하는관점과 [활성값 patch 방법론](https://arxiv.org/pdf/2309.16042)을참고한다. 뒤방법은metric/입력변형에민감하므로단일‘원인층’순위를확정하지않는다. 이번에는정답품질기준선이아니라**같은반복token 대EOS logit차이**·확률/entropy를보고하며교정/학습은하지않는다.

| 개입 | 고정/변경 | 측정·주장 범위 |
| --- | --- | --- |
| 반복 이력1/3/8 | 질문·가중치고정; 이력길이/내용은변함 | 반복피드백의조건부선호변화,길이교락공개 |
| 같은길이order shuffle / prompt token cycle | anchor·길이·마지막token고정; shuffle은token다중집합도고정 | 이력배열/내용개입효과. 문법/의미도변해정상분포STR라고주장하지않음 |
| native/shared/r64 | 모든subject에같은prefix IDs. middle[2..5]만공유/보정 | 해당MLP재매개화의직접효과. 공유가반복에필요한지/정도를분리;전층공유학습효과아님 |
| 마지막위치 activation patch | 같은길이control의같은마지막token 층출력을한층씩이식 | 16층×2donor·실제로output을변경한효과. 정상대조없는상태이식/OOD가능성/후속정확답은별도 |
| 같은상태no-op patch | 수신자자신의상태를16층에넣음 | 로짓불변과hook/weight/config 복구를검증 |
| R1→R2 inference | 같은R1-trained weights를한시적infer_repeat2로변경 | 추가방문기여만. **재귀학습부모의인과효과와동일하지않음** |
| 6같은prefix cache대조 | 실제ID열고정;BF16auto/BF16math/FP32math IEEE | 낮은margin swap의dtype/backend기여. 동일prefixteacherforcing이고자유생성전체동일성아님 |

현재정확parent학습JSON의train_repeat1과dense16은확인했다. 초기화원천 `m100_ko-en_300M_dense`는옛JSON에train_repeat/n_layers가없어전체학습계보무재귀까지단정하지않는다. 추가원천weights는로드하지않는다.

### 표본·실행·예측

기존 `ko_context`의질문copy와shared ‘어떻게’, `ko_math`의값이달라지는9token목록, `en_math`의질문copy를4사례로삼는다. 서로다른원질문은3개다. fixedprefix/4사례×3subject의108baseline·12noop·384single-layer patch·24R2·18precision pair·18native짧은답을묶는다. noop을위해추가재계산하며개입수와forward횟수를같게부르지않는다.
native sample은그대로사용해R1/R2 각16token의총18짧은답을보존한다. R1의9답은기존ID열첫16과text를대조하고,R2는분포mismatch 진단으로구분한다. CODE·원부모/tokenizer/r64의SHA·actualvisit·donor벡터/입력IDs를20MB이하JSONL에보존한다.

예측: 같은길이이력교체로copy선호가줄면반복history가다음선택의한원인인근거다. parent/R1에서도남으면공유MLP·활성재귀가필수원인은아니다. 특정층patch만으로선호가변하면그상태가효과를매개할수있지만전면붕괴/유일원인증명은아니다. FP32/math에서6swap이줄면수치설명은강해지나전체구현검증이나수리성공으로승격하지않는다.

| 단계 | 런처 | 비용/경계 |
| --- | --- | --- |
| Stage7aW | `run_P093B_Stage7aW_causal_contract.sh` | CPU 작은실제아키텍처fixture14·private body0 |
| Stage7bW | `run_P093B_Stage7bW_history_mlp_layer_interventions.sh` | 이번원인진단한정GPU최대600초·학습/save0 |
| Stage7cW | `run_P093B_Stage7cW_causal_readback.sh` | CPU exactreport/CODE/losslessSHA 회수 |

기술0은같은상태no-op·복구/finite·완결측정의통과이지반복수리/학생지능PASS가아니다. 단일token shuffle은원형과같아효과0이예상되고별도표시한다. 작은donor/receiver logit차이의정규화는null로두며반복token/eos를모든틀린문구목록이나온라인품질선별에쓰지않는다. 새로운학습기본/공용sampler/커널·원래출력은변경하지않는다.
### Stage7dW/7eW/7fW — cosine 단독 필요성의 출력불변 통제

층전체벡터patch는의미정보까지바꿔유사도변화만의효과로읽을수없다. 같은추가진단허가범위에서현재768→256 factorized output head의영공간성분만반사하는소형통제를더한다. 기본모델/기존code/weight는수정하지않고새 `p093b_similarity_control_v1_s1337`에최대120초진단을기록한다.

마지막raw잔차x의readout-visible부분을P x,영공간을(I−P)x로두면 x'=P x−(I−P)x다. 학습된final scale을effective head에포함한다. 이상적인산술에서norm과출력projection이같아RMS뒤의전체vocab logits가보존되지만직전같은위상hidden과의cosine은달라질수있다.
이검사는**현재한위치만반사**하고직전위상reference는보존한다. 모든위치에같은직교반사를적용하면cosine도같아지므로그런실험을유사도변화로주장하지않는다. 실제FP32/math logit최대차≤1e-4+1e-5×참조logit절대최대및argmax동일을수치정합으로따로검사한다.

4사례×3subject=12쌍·samephase 마지막token·원형/반사벡터·전체logit차이·실제/분석RMS cos를보존한다. 같은부모/r64/shared·학습/save0·전체자유생성새답0이다.
성공하면‘이마지막층의높은cosine그자체가다음반복token선택에필요하다’는주장의국소반례가된다. **초기층기전·head-visible 정보·반복의유일원인·SimCTG훈련효용은검증하지않는다.** 낮은cosine이항상좋다는품질문턱도만들지않는다.

- `run_P093B_Stage7dW_similarity_cpu_contract.sh`: CPU선형대수5fixture·부모읽기0.
- `run_P093B_Stage7eW_head_nullspace_similarity.sh`: 같은추가허가의소형GPU대조·최대120초.
- `run_P093B_Stage7fW_similarity_readback.sh`: CPU source/CODE/shardSHA 회수.

이번원인진단GPU합계실측과준비/CPU시간은분리보고하며600/120초실행cap을실제사용시간으로쓰지않는다.
## 18. 2026-10-12 원인 개입 회수·예측 대조

[결과103 §13](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md):CPU14/5·제어개입564행과영공간12쌍·본체22.629876/3.449240초/모두0. 새native18짧은답과기존R1앞16token 9/9재현,학습/save0이다. 실행6SH는동일본문-done에보존·추가삭제0이며이진단권한은종료했다.

같은길이shuffle에서parent‘나의’98.8061%→10.0767%로낮아져길이만의설명이부족했다. 그러나문법/의미를바꾸는대조라정상분포전체나학습원천인과는미확정이다. native/R1에도반복이있으므로공유MLP·활성재귀는필수단독원인이아니다. R2는실제28방문/9짧은답의내용실패를남겼고R1-trained 분포mismatch와재귀학습효과를분리했다.

layerpatch는부호가엇갈렸고coda14의큰억제도유일원인이라고부르지않는다. 출력에영향없는최종상태의512차원부분공간을반사해shared‘어떻게’cos.998507→−.525330에도확률.236868635와전체logit/argmax를유지했다. ‘cosine이높아야즉시반복한다’는필요조건예측의국소반례다. head-visible 정보/초기층/전시퀀스원인은남는다.

BF16auto6불일치를재현하고BF16math5/6·FP32/math6/6이일치해수치/계산경로설명을지지했다. old기술8을소급PASS로바꾸지않고새측정0과구분했다. C의정답·종료SFT/ORPO·SimCTG는후속범위/별도학습권한을필요로하며기본학습레시피와75M/300M 목표는불변이다.

## 2026-10-13 — 원시도 HOLD 판독과 새 계약/decoder 준비

[103 §14](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md): Stage6bW는낡은CPUcontract로모델/생성0이다.
‘실제decoder가반복을줄일것’이라는예측은실행되지않아맞다/틀리다판정할수없다.
기본-off MTP이관의 정확generate SHA쌍/AST 동등성을회귀로보증하되 실제cache24쌍은별도소유한다.

| 단계 | 실행·상태 | 비용·판정 |
|---|---|---|
| Stage6aWb | run_P093B_Stage6aWb_generation_current_contract.sh·CPU준비 | .02h,N/current SHA+12회귀 |
| Stage6bWb | run_P093B_Stage6bWb_parent_shared_r64_decode.sh·모델준비 | .25h,Y/same source+부모/shared/r64·cacheOFF24·실제답192 |
| 반복억제 ORPO/SimCTG | 이번학습미구현·보류 | 위원답으로원인진단후추가선택,자동교육없음 |

새tag p093b_generation_v2_s1337; oldcalibration/원CPT/복원선/실제음성불변.
알려지지않은hash변경은거부한다. CPU동등성이실물BF16이나전역KV무결성PASS는아니다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage8 — 같은 원답의 cache·precision 분리

### 왜·질문·예측

[103 §15](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md):
192새생성은완료했고BF16 plaincache3/24쌍이달랐다. 원형/정밀도/실제질문을같게한 새대조다.
FP32/math가현재24쌍의정합을회복할수있지만동일한틀린반복도그대로유지할수있다.
정합회복을반복억제/정답성/전체cache증명으로승격하지않는다.

| 단계 | 계약 | 비용/경계 |
|---|---|---|
| Stage8aW | cb9b335의defaultNTP본문 AST동등성·knownSHA이관·tinyCPU회귀 | GPU0 |
| Stage8bW | 동일원parent/shared/r64·8질문×BF16/FP32×cacheON/OFF=96새원답 | 약3~8분추정/cap600초·학습/save0 |

새tag p093b_cache_precision_v1_s1337, 원calibration report4C8D5952…·부모A402BF1D…·legacy32·r64인자는그대로읽는다.
현재generate API의추가optional verification keyword는defaultNTP본문을바꾸지않는다.
이추가정확SHA만인정하며다른원형source변경은거부한다.
GPU는사용자7의2026-10-14 17시이전한정권한이고그이후SH는사용자실행용이다.
모든token IDs/text/finish/count·실제K1·precision·querycache·원답SHA를20MBshards로보존한다.

- run_P093B_Stage8aW_cache_precision_cpu.sh
- run_P093B_Stage8bW_fp32_cache_pair.sh

현재모델기본BF16/복원선·75M 목표는불변이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage8 실행 회수

Stage8aW CPU17 뒤8bW 실제96답에서 BF16 cache21/24·FP32/math24/24를 확인했다. [결과103 §16~§17](../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md): 정합회복에도 r64 질문나열이 남아 수치오차를 내용반복의 단독원인으로 판정하지 않는다. 새rank/압축/ORPO/SimCTG 학습은 미실행이며 같은원형/원조건·과거음성을 보존한다.
