# 2026-10-22 동일 배치의 오른쪽 PAD 축소 감사

상태: `READ_ONLY_SOURCE_AUDIT / SPEED_NOT_RUN / GRADIENT_EQUIVALENCE_NOT_RUN`.

이번 범위는 같은128대화 optimizer update, 같은16개 microbatch와 각8개 대화의 순서를 유지하면서 **공통 오른쪽 PAD suffix만 줄이는 표현 변경**이다. 길이 정렬·재배치·bucketing에 의한 membership 변경·packing·실토큰 자르기는 범위 밖이다. 코드·원자료·WIP JSON·체크포인트·설정·기존 결과는 수정하지 않았다. 실제 tokenizer/model/CP/가중치 로딩, GPU, 새로운 시험/실험, 하위 agent를 실행하지 않았다. 쓰기는 이 문서 하나다.

## 1. 결론

현재 경로는 `x=ids[:-1]`, `y=labels[1:]`, assistant-turn owner와 whole-update horizon별 분모를 이미 분리한다. 각 micro의 `L=max(len(rec.x))`에 대해 `Wq=q*ceil(L/q)`로 오른쪽 PAD만 줄이고 `L<=Wq<=1024`, `batch_size=8`을 유지하면, 현재 causal·위치별 trunk와 masked head 구조에서는 **유효 hidden/target/수학적 loss·gradient를 보존할 근거가 있다**. 이것은 GPU 부동소수점 gradient 동등성이나 학습 trajectory의 비트 동일성을 검증했다는 뜻이 아니다.

새 loader/attention/MTP loss를 만들 필요는 없다. [core.pad_records](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:50)는 이미 `fixed_width=None`일 때 micro 최장 x 길이로 동적 PAD를 지원하고, 명시된 `fixed_width`도 실토큰보다 작으면 거부한다. 32/64/128 배수 폭은 이 기존 helper에 넘길 실행 폭의 정책일 뿐이다. 다른 기존 경로의 [train_sft_p090.pad_batch](/home/uranus/tinyLM/scripts/train_sft_p090.py:66)도 최장 길이 기반 PAD를 구현하며, [micro_groups](/home/uranus/tinyLM/scripts/train_sft_p090.py:74)는 optimizer/micro membership을 별도로 유지한다. 이를 MTP로 복사하면 segments 지원을 다시 만들어야 하므로 MTP에는 기존 core를 재사용하는 쪽이 맞다.

`tinylm/`와 `scripts/`의 dynamic-padding/length-bucket 관련 정적 검색에서는 현재 P101A 학습에 연결된 별도 length-bucket sampler나 양자화 폭 정책은 발견하지 못했다. 검색에 나온 다른 bucket은 언어·과제 quota, 평가 집계, view 길이 일치용이지 이 학습 배치를 자동 재배치하는 구현이 아니다. 존재하지 않는 새 "dynamic loader"를 제안하거나 다른 bucket을 이 기능으로 승격하지 않는다.

## 2. 원장 수치의 정확한 의미

직접 읽은 정본은 [CPU context/padding audit](/home/uranus/tinyLM/handoff/audit/WIP_20261022_CONTEXT_PADDING_AUDIT.json)이다. 실물 SHA256=`FBAF73E93E33D09E965CED1778455C1E0299E959680FE342409483C84D315371`, schema=`P101A_V3_CPU_CONTEXT_AND_PADDING_AUDIT_V1`, corpus SHA=`7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20`.

| 표현 | 집계 input slots | 고정1024 대비 slot 절감 | 고정/cropped slot 비 | cropped/실제x 비 |
|---|---:|---:|---:|---:|
| 현재 8×1024 | 23,068,672 | 0% | 1.0000 | 4.2677 |
| 같은 micro, 오른쪽 PAD를32배수까지 | 9,455,872 | 59.0099% | 2.4396 | 1.7493 |
| 같은 micro, 오른쪽 PAD를64배수까지 | 9,819,648 | 57.4330% | 2.3492 | 1.8166 |
| 같은 micro, 오른쪽 PAD를128배수까지 | 10,614,784 | 53.9862% | 2.1733 | 1.9637 |
| 실제 x 토큰 합계 | 5,405,444 | ragged 총량 참조만 | 속도 배수 아님 | 1.0000 |

고정23,068,672 중17,663,228이 PAD slot이며76.5680%다. **4.26767385는 고정 slot/실제 x 총량 비율**이다. 동일8개 묶음에서 가장 긴 행까지는 다른 짧은 행도 PAD해야 하므로, PAD-only 직사각형 축소32의 slot 비는4.268이 아니라2.4396이다. 남는 slot/실제 x 비도1.7493이다. 실제 x에는 prompt/user/history와 assistant 입력이 모두 들어가며 assistant target 수와 다른 단위다.

여기서 2.4396도 실제 가속 측정값이나 속도의 엄밀한 상한이 아니다. FFN/QKV/activation 등은 대체로 T에 선형이고 attention은 T·T 관련 비용을 가지며, 커널·대역폭·정렬·checkpoint 재계산·compile·head/optimizer 고정비가 섞인다. slot 총량만으로 전체 wall-time이나 VRAM peak를 환산할 수 없다.

JSON의128배수 실제 폭은 `256:75, 384:1547, 512:721, 640:255, 768:124, 896:80, 1024:14`로 총2816micro, 7종이다. 64/128에서는 여전히1024 폭이 있으므로 **최악 micro의 activation peak가 반드시 감소하지 않는다**. 32는 이 JSON의 `max_full_tokens=970`과 x=ids[:-1] 규약상 최대 실x969, round-up 최대992이지만, peak는 compiler/cache/workspace와 함께 별도 미측정이다. parameter/optimizer state의 저장량이나 모델 압축, 배포 decode KV 감소를 얻는 변경도 아니다.

원장은22528TRAIN/512DEV, TRAIN552609 targets, 176optimizer groups/2816micro를 기록하지만 **어느 epoch의 ordered membership인지 필드가 없다**. [engine.batches](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:81)는 `Random(1337+epoch)`로 매 epoch 다른 shuffle을 한다. 따라서 제시된 cropped slot 수를 그대로4배해서4pass의 정확한 집계로 고정할 수 없다. 고정1024 slots와 실제 x 총량은 동일 행 노출이면 pass마다 일정하지만 micro 최장 길이 분포는 바뀔 수 있다. 여러 quantum 비교는 각 epoch의 똑같은 ordered membership에 대해 계산해야 한다.

이 원장은 V3다. [V4 COUNTS](/home/uranus/tinyLM/scripts/diag_p101a_supervision_v4.py:42)는 x5405444를 유지하되 TRAIN targets를552153으로 선언한다. [수리 계약](/home/uranus/tinyLM/scripts/p101a_supervision_repair.py:256)은 messages/순서/split/x를 바꾸지 않고 `meta.supervised_assistant_turns`만 바꾼다. 이 조건이 실제 대상 corpus에 성립하면 x 기반 폭 정책을 이관할 논리는 있지만, **V3의552609를 V4 loss 분모로 복사하면 안 된다**. 이 감사에서는 V4 corpus/tokenizer를 열어 새 폭 통계를 측정하지 않았다. reasoning direct/trace 등 다른 corpus에도 이 V3 수치를 복사하지 않는다.

## 3. 반드시 고정할 것

현재 [학습 loop](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:234)는128대화의 record별 count를 먼저 합산한 뒤8개 micro씩 backward하고 마지막에 한 번 clip/AdamW/Muon step을 한다. 다음은 모두 폭 변경과 독립적으로 그대로여야 한다.

| 항목 | 보존 조건 | 바꾸면 생기는 차이 |
|---|---|---|
| 데이터 순서·membership | epoch seed, ordered128 IDs, 그 안의 ordered16×8 모두 동일 | optimizer에 동시에 들어가는 gradient 묶음과 부동소수점 누적 순서 변경 |
| 노출·step | 같은 대화 수·실x·유효 label·pass·optimizer704 steps, 마지막 partial 처리 유지 | 학습 budget·MTP 계수 schedule·warmup/decay와 교란 |
| 실행 batch | `batch_size=8`; 부족 행을 채우는 기존 dummy 처리도 유지 | 유효 대화 수는 같아도 kernel/position_chunk/compiled graph 조건 변경 |
| 폭 | `Wq=q*((L+q-1)//q)`, L은 모든 rec.x의 실제 길이 최대 | 마지막 gold 위치나 `y!=-100` 수로 자르면 마스크된 실제 문맥을 지울 수 있음 |
| 모형·정밀도 | cfg.max_seq_len1024, 동일 RoPE/CLA/visit schedule/Q-F 경로, BF16/autocast·checkpoint·compile mode 그대로 | padding만의 변경이 아니게 됨 |
| optimizer | 같은 초기 core·state·parameter groups·LR/weight decay·zero_grad·clip 시점 | 같은 loss라도 다른 학습 경로 |

PAD id가 나타나는 위치를 훑어 길이를 추정하지 않는다. 실제 원문 안의 동일 ID나 중간 특수 토큰과 batch suffix PAD를 혼동할 수 있다. `rec.x`의 길이를 사용하고 원래 `x/y/segments` prefix를 그대로 보존한다. 마스크된 assistant 오답·user·system 토큰도 문맥의 실토큰이면 이번 crop 범위 밖이다.

## 4. shift·label·assistant owner·분모

[encode_record](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:26)는 `Record(ids[:-1],labels[1:],segments[1:])`를 만든다. labels는 이미 한 칸 shifted다. [SFT encoder 계약](/home/uranus/tinyLM/tinylm/data/sft.py:126)과 같이 **다시 한 칸 밀면 안 된다**. `pad_records`는 x suffix를 pad_id, y suffix를IGNORE=-100, segment suffix를0으로 채운다. cropped prefix의 세 배열은 원형과 정확히 같고 `len(x)==len(y)==len(segments)`이어야 한다. 마지막 raw token이 x에 없더라도 마지막 y의 EOT target은 기존 next-token label로 남는다.

assistant-turn owner는 `segments`의 양의 ID다. [clean.masked_record](/home/uranus/tinyLM/scripts/diag_p101a_clean_bilingual.py:36)는 제외 target을-100으로 만들면서 owner도0으로 만든다. PAD 축소가 이를 다시 encode하거나 allowlist를 무시해 owner/label을 복원하면 V4 수리를 되돌리는 별도 오류다.

기존 목적함수는 update 전체의 `D_h=sum_{128 records} count_record(rec)[h]`로

`L_update = sum_micro S_1(micro)/D_1 + sum_h w_h(update) * sum_micro S_h(micro)/D_h`

이다. [count_record](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:85)는 PAD 없는 record 리스트에서 세고, [normalized_loss](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:146)는 whole-update 분모를 쓴다. 따라서 D_h는 폭을 바꿔도 그대로다. `B*Wq`, padding 후 tensor.numel(), micro 개별 유효수로 나누거나16개 micro mean을 다시 평균내면 안 된다. 예컨대 supervised10개와100개 micro를 각각 평균낸 뒤1/2로 합하는 것은 전체110토큰 평균과 다르다. D_h=0인 보조 horizon의 기존 skip 조건과0계수인 head를 호출하지 않는 기존 active schedule도 유지한다.

## 5. MTP h별 창이 보존되는 이유와 경계

[horizon_targets](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:66)는 이미 shifted y의 `unfold(h)`를 써서 hidden[t]에서 raw[t+h]를 예측한다. 유효 창은 h개 label이 모두IGNORE가 아니고 h개 segment가 동일한 양의 owner인 경우뿐이다.

- 보존할 h는1/2/3/4 전부다. 전체 T가 Wq로 작아지면 target 배열의 끝은 `Wq-h+1`이지만, 잘라낸 suffix에 걸치는 기존 창은 PAD의IGNORE/owner0 때문에 이미 invalid였다.
- Wq가 최대 실제 x 길이 L 이상이면 마지막 실제 y/EOT를 끝점으로 하는 유효 창은 남는다. h-1개의 추가 **실입력**을 만들어 붙이거나 y를 h만큼 다시 shift할 필요가 없다.
- assistant A→user→assistant B나 수정 전 답→수정 답 경계는 기존 owner/IGNORE로 차단한다. 같은 정답 토큰이라고 owner를 합치거나 PAD owner를 이전 turn ID로 채우면 안 된다.
- helper는 폭<h이면 empty target을 반환한다. 이번32/64/128 폭은 h<=4보다 크지만 일반 dynamic PAD 재사용 시의 빈 horizon 계약은 그대로다.
- EOT는 현재 assistant span의 유효 target일 수 있다. crop 판단을 last content token으로 하거나 EOT를 일괄 제거하면 목표가 달라진다.

[components](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:117)는 이미 유효 target 위치의 features만 gather해서 vocab head/CE를 계산한다. B=8, chunk2048이면 position_chunk256이 고정이다. 같은 B/순서/유효 mask를 유지하고 끝의 all-invalid 구간만 줄이면 살아 있는 position-chunk의 gather 순서와 head row 수를 유지할 수 있다. PAD 축소가 새로 거대한1024×vocab PAD logits를 없애는 것처럼 비용을 세면 중복 계산이다. 주된 후보 절감은 trunk/attention/activation 및 checkpoint 재계산이다.

단, `components`의 graph-safe0은 `hidden.sum()*0.`이다. 기존 PAD hidden에 NaN/Inf가 있다면 수학적0이라는 논의 자체가 성립하지 않는다. 유효·PAD hidden을 포함한 finite 상태를 전제로 하며, crop으로 NaN 발생 구간을 가렸다고 안정성이 증명되는 것도 아니다.

## 6. PAD attention·CLA·RoPE의 보존 조건

[Attention.forward](/home/uranus/tinyLM/tinylm/model/modules.py:107)는 training/prefill의 q_len==kv_len에서 `is_causal=True`인 SDPA를 사용한다. 별도 PAD attention mask는 없다. **그래도 오른쪽 PAD만 제거할 수 있는 이유**는 다음과 같다.

1. 유효 위치t가 읽는 key는0..t다. t보다 오른쪽인 PAD key를 보지 않으므로 suffix를 지워도 유효 query의 수학적 softmax 분모·V 합은 같다.
2. PAD query는 유효 history를 볼 수 있지만, 그 출력이 미래→과거로 전달되지 않고 해당 label은IGNORE다. RMSNorm은 [feature 마지막 축의 mean](/home/uranus/tinyLM/tinylm/model/modules.py:35)이고 MLP/linear는 위치별이어서 PAD 위치의 값을 다른 유효 위치의 통계에 섞지 않는다. [TLinear](/home/uranus/tinyLM/tinylm/model/ternary.py:364)의 기본 F.linear와 weight-group quantization도 token 총량으로 정규화하지 않는다.
3. [transformer.forward](/home/uranus/tinyLM/tinylm/model/transformer.py:759)의 return_hidden 경로는 use_cache/past_kv와 혼용을 거부한다. past_len=0이고 [RoPE slice](/home/uranus/tinyLM/tinylm/model/transformer.py:782)는 `[:T]`에 해당하므로 남은 token의 절대 위치0..L-1은 바뀌지 않는다. cfg.max_seq_len이나 RoPE buffer를 micro 폭으로 재구축하지 않는다.
4. CLA의 [self.owner](/home/uranus/tinyLM/tinylm/model/transformer.py:71)는 **layer K/V 소유권**이며 assistant segment owner와 다른 개념이다. [kv_bank](/home/uranus/tinyLM/tinylm/model/transformer.py:851)는 같은 forward에서 layer owner(반복 시 owner+visit)로 K/V를 재사용한다. 동일 schedule/owner와 같은 Wq 길이의 Q/K/V를 함께 쓰면 유효 prefix가 귀납적으로 보존된다. 원래1024 K/V를 cropped Q에만 붙이거나 이전 micro의 bank를 가져오는 방식은 이 논리가 아니다.

이 증명 범위는 현재 causal prefix와 위치별 연산이다. left PAD/left crop/packing/비인과 attention, sequence 전체 pooling·BatchNorm·PAD를 포함한 auxiliary loss가 있으면 재검토해야 한다. 현재 router 자체는 [token별 softmax](/home/uranus/tinyLM/tinylm/model/transformer.py:831)이지만 [_balance](/home/uranus/tinyLM/tinylm/model/transformer.py:967)는 B,T 평균을 쓴다. 현재 return_hidden는 aux 전에 반환하지만, 별도 router auxiliary를 학습에 더한다면 PAD 수 변화가 그 목적함수를 바꿀 수 있다. segments는 attention 경계 mask가 아니므로 packing의 대화 간 누출을 막아주지도 않는다.

## 7. RNG·dropout·checkpoint·수치 동등성

정적으로 읽은 현재 trunk/MLP에는 dropout 호출이 없고 attention은 dropout_p를 넘기지 않는다. 설치된 torch [functional.py SDPA signature](/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages/torch/nn/functional.py:5934)의 기본값은0.0이다. parameter 초기화의 randn과 PAD shape의 forward RNG는 다른 문제이며 동일 초기 core는 그대로 필요하다.

그러나 "같은 seed"만으로 임의의 stochastic 모형에서 crop 동등성이 확보되지는 않는다. dropout·stochastic-depth·shape-dependent random op가 추가되면 B×T 크기가 바뀌어 RNG 소비량/행별 mask/뒤 micro의 RNG 시작점이 달라질 수 있다. 기본 backbone [checkpoint](/home/uranus/tinyLM/tinylm/model/transformer.py:893)는 non-reentrant이고, 설치된 [checkpoint 기본 preserve_rng_state](/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages/torch/utils/checkpoint.py:493)는True다. 반면 [head checkpoint](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:138)는 `preserve_rng_state=False`를 명시한다. 현재 head가 deterministic라는 전제를 벗어나면 이를 안전 보증으로 사용할 수 없다. 이번 감사에서 RNG 정책을 바꾸지 않았다.

수학적 목적함수가 같아도 T 변경은 GEMM flatten 크기, SDPA backend/tile, BF16 반올림, reduction tree, compiled backward를 바꿀 수 있다. 실제 유효 hidden/logits/CE/gradient의 허용 오차 내 일치와 비트 동일은 서로 다른 주장이다. gradient의 작은 차이가 clip 경계 및 AdamW/Muon 상태를 거쳐 이후 trajectory를 바꿀 수도 있다. 기존 [head checkpoint·분모·누적 gradient 시험](/home/uranus/tinyLM/scripts/test_p101a_sft_mtp.py:77)은 관련 contract를 읽어 확인했지만 **고정1024 대 여러 Wq의 전체 CLA compiled gradient 동등성 시험은 아니다**. 이번에 어떤 테스트도 실행하지 않았다.

## 8. torch.compile graph 증가와 비용

[현재 학습](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:216)은 `torch.compile(base,mode='default')`이고 `dynamic=`을 지정하지 않는다. 이것을 "항상 하나의 완전 dynamic graph" 또는 "폭마다 반드시 하나의 graph" 어느 쪽으로도 단정할 수 없다.

설치 파일을 import 없이 읽으면 [torch/version.py](/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages/torch/version.py:3)는 `2.10.0+cu130`이며, [_dynamo/config.py](/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages/torch/_dynamo/config.py:118)는 기본 `assume_static_by_default=True`, `automatic_dynamic_shapes=True`다. 주석은 첫 frame static, shape guard 실패 후 변동 차원을 dynamic으로 재compile하는 동작을 설명한다. 같은 파일의 [기본 recompile_limit](/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages/torch/_dynamo/config.py:67)은8, accumulated256, fail-on-limit=False다. **이는 설치 소스 기본값 관측이지 실행 프로세스의 override/실제 graph 수를 읽은 것이 아니다.**

| 표현 선택 | 의미/slot 관점 | compile·운영 관점 | 이번 판단 |
|---|---|---|---|
| A 고정1024 유지 | 기존 조건·원장 그대로, slot 절감0 | 기존 단일 T 조건 유지 | 현재 진행/완료 baseline의 정본은 유지 |
| B 동일 membership +128배수 | slot53.9862% 절감 후보 | 이 원형7폭. 실제 specialization/graph 수는 미측정 | 의미 검토 후 도입을 논할 때 가장 보수적인 폭 제한 후보 |
| C 동일 membership +64/32배수 | slot57.4330/59.0099% 절감 후보 | 더 많은 폭 가능. exact-max는 기존 helper로 가능하지만 최대 수백 폭까지 커질 수 있음 | 추가 slot 이득과 compile 불확실성을 함께 표기. 자동 승자 선정 불가 |

이 표는 선택지·영향 분석이지 새 실험 등록이나 도입 승인/실행 계획이 아니다. 현재로서는 A의 기존 증거를 보존하고, 소스상 의미 보존의 비교 출발점은 B로 보는 것이 보수적이다. B가 실제로 더 빠르다거나 C가 컴파일 폭 때문에 반드시 느리다는 뜻은 아니다. 32가64보다 절약하는 slot은363776으로64집계의약3.70%이며, 이 작은 추가량과 warmup 비용을 분리해야 한다.

7폭이 기본 recompile_limit8 이하라는 이유만으로 안전을 선언하지 않는다. guards, train/eval, quant refresh 상태, graph break, backward, runtime override 등으로 폭 수와 specialization 수가 일대일이 아닐 수 있다. 현재32의 이 원형 최대992를 일반1024 context의 모든 자료에 고정해 해석하지도 않는다. 고정-width별 graph를 별도 dictionary로 새로 만들거나 `dynamic=True`, compiler cache limit, backend를 조용히 바꾸면 "PAD 폭만 변경"이라는 독립변수 범위를 벗어난다.

head/CE는 `core.components(base,...)`로 compiled backbone 밖에서 호출된다. positional valid gather/boolean 검사·CPU count 변환·checkpoint head 비용까지 모두 compile이 제거해 준다고 가정하지 않는다. 실제 비용에는 첫 compile/재compile, warm steady-state, checkpoint forward/backward, raw 계측·optimizer·validation·저장을 구분해 넣어야 한다. 어떤 compile warmup도 추가 optimizer update나 중복 대화 노출로 섞어서는 안 된다.

## 9. 이번 감사가 닫은 것과 남긴 것

확인한 것은 기존 helper 재사용 위치, 동일 membership에서 crop을 정의할 정확한 축, 현재 소스의 causal/owner/shift/분모/MTP 창 보존 조건, 루트 CPU 원장의 slot 산술과 적용 범위다. 실입력·label prefix, owner, D_h, 노출, cfg/route, RNG 전제 중 하나라도 바뀌면 padding-only 비교가 아니다.

실제 속도/VRAM peak, 유효 hidden·logit·loss·gradient 동등성, compiled graph 수/캐시·recompile 비용, optimizer 한 step 이후 및 장기 trajectory, 품질은 모두 `NOT_RUN`이다. 새 코드·명령·실험을 추가하지 않았다. [V4 source pins와 metadata 계약](/home/uranus/tinyLM/scripts/diag_p101a_supervision_v4.py:127)은 원 engine을 바꾸면 기각하도록 되어 있으므로, 나중에 도입 권한을 얻어도 원 source/default/cost32/완료 arm을 덮거나 기존 검증에 새 정책을 소급 표시하면 안 된다. 학습 중 한 팔만 바꾸는 것도 이번 감사가 승인한 행동이 아니다.

`impact-analysis`는 코드·데이터·시험·정본·기술부채와 GPU/소유권/비교조건/증거 수준을 나누는 데 사용했다. 구현과 실측이 없는 현재 단계의 정본 영향은 이 감사 문서뿐이며 기준표·계획·결과·COMPASS·registry를 임의 갱신하지 않았다. **이론 PAD 비율4.268 또는 cropped slot 비2.440을 실제 가속으로 보고하지 않는 것**이 이번 검토의 핵심 경계다.
