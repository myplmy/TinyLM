# 2026-10-22 정 검토 — 이미 구현된 main 대조를 먼저 완료한다

현재 권장안은 기존 직접답/검산풀이 대조와 명시문맥 MTP 네 팔을 실행하고, 남은 시간을 새 평가와 실제 답 판독에 배정하는 것이다. 방문 정책 네 팔과 prefix router까지 한 창에 합치지 않는다. 현재 약 10.5시간 창에서 `3.0+0.7+8.619=12.319시간`은 이미 기록 예산을 초과한다. 3.0/0.7시간 자체도 완료 보증이 아니다.

후행 진행 알림: 총괄이 06:25:56KST에 기존 MTP SH를 `timeout18000`으로 시작했다고 전달했다. 아래 main 부재는 그 직전 감사 시점의 스냅샷이며, 이 담당자가 본학습을 실행하거나 현재의 완료를 주장한 것이 아니다. 실행 완료·중단은 총괄이 새 영수증으로 갱신한다.

## 1. 권한·증거 범위

| 경로 | 동작 | 근거 | 제외 |
|---|---|---|---|
| 이 감사 파일 | 신설 | 총괄의 정확한 파일 위임 | 다른 문서·코드 수정 없음 |
| 지정 SH·관련 소스·계획·결과·정확한 JSON 영수증 | 읽기 | 구현/비용/계보 감사 | 보호 TinyDataset 접근 없음 |
| 비용 재사용 검사기·run registry | 읽기 전용 CPU 실행 | 실험 설계 검산 | 모델/체크포인트 tensor 로딩·GPU·다운로드·Git 쓰기 없음 |

현재 대화의 새 10/22 17시 실행 허가는 총괄이 소유한다. 이 담당자는 CPU 감사만 수행했다. 최신 인계의 과거 권한 만료 기록을 새 허가의 부재로 오해하지 않되, 과거 P078 권한 JSON을 현재 승인으로 재사용하지 않는다. WIP와 정본 문서 연쇄는 총괄 소유이며 이 감사는 결과 정본을 대신하지 않는다.

## 2. 실제 재고: cost 완료와 main 미실행

2026-10-22 KST 06시대, 정확한 report 경로와 예정 CP의 존재를 확인했다. MTP 본 네 팔·직접답/풀이 본 두 팔의 report/CP/first-answer report는 아직 없다. 기존 세 비용 영수증은 CPU 검사기로 현재 조건에 다시 맞춰 모두 종료0이었다.

| 기존 비용 | 업데이트 | 전체초 | 본 업데이트만 외삽초 | reserved MiB | CP 저장 |
|---|---:|---:|---:|---:|---|
| MTP `parent_mtp` | 32 | 141.329128 | 1642.278757 /704회 | 3002 | 없음 |
| direct `parent_ntp` | 32 | 100.891473 | 282.415958 /128회 | 3010 | 없음 |
| trace `parent_ntp` | 32 | 112.186677 | 314.029129 /128회 | 3010 | 없음 |

실측 정본은 `test_result/evidence/<아래 tag>/calibrate_<arm>/report.json`이다. 비용 검사 출력의 SHA는 MTP `3F966E15ACEE203864F1425C60B8C0730ABB6715DEEBF1E10AAAF5A0D821FB0E`, direct `DDE6D78E513017F22E0C4E59ADA495D18E852B5389DDAA855E63D330B5E97CA0`, trace `2304D07853EDF27229197036393140B77A29B42B2A8D792F6B5224188954862B`였다. `model_loads/gpu_calls/writes=0`이다.

MTP의 `scratch_ntp`, `scratch_mtp`, `parent_ntp` 비용은 아직 없다. 이 세 팔에는 새 cost32가 먼저 필요하다. 기존 main 런처가 비용 없음8→최초 측정, 일치0→재사용, 불일치9→해당 본런 금지를 이미 구현한다. 새 비용/학습 엔진을 만들 필요가 없다.

근거: [결과092 §15~16](../../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md), [비용 검산기](../../scripts/check_p101a_clean_cost.py) 18~35·49~65행, [MTP 런처](../../run_P101A_Stage3jW_clean_mtp_four_arm.sh) 10~28행.

## 3. 오늘의 세 대안

| 안 | 실제 범위 | 장점 | 비용·한계 |
|---|---|---|---|
| A 권장 | 기존 직접답/풀이 main 두 팔 + MTP main 네 팔 + 같은 평가 | 코드 정답의 중간상태 지도와 보조 미래토큰 목적을 각각 독립 비교. 기존 구현과 세 성공 비용 재사용 | 레지스트리 약3.7h는 잠정 예약. MTP 미측정 세 비용·전체 생성 평가·문서 여유를 다시 산정해야 함 |
| B | MTP parent NTP/MTP 대응 두 팔 + 직접답/풀이 + 평가 확대 | 배포 계보에 가까운 질문에 먼저 답하고 새 벤치마크 여유 확보 | scratch 상호작용은 미확인으로 남음. 네 팔 완료로 보고할 수 없음. 개별 기존 controller 호출을 총괄이 명시 관리해야 함 |
| C | P078 방문 네 팔704만 완료하고 다른 main 축 보류 | 아직 비어 있는 방문 학습 효과를 직접 확인 | 현재 실제 예측8.619h로 창 대부분 소진. router의1.5h는 미측정이며 후속까지 넣으면 평가·기록 여유가 거의 없음 |

A를 권장하되, 짧은 직접답/풀이 결과를 먼저 확보하고 MTP의 세 새 비용을 본 뒤 잔여 예산을 갱신한다. 시간 위험이 커지면 B로 정확히 축소하고 미실행 scratch 팔을 남긴다. 비용32 통과만으로 main을 완료 처리하지 않는다. 새로운 대조 손실이나 새로운 모델 구조를 이 실행 직전에 섞지 않는다.

## 4. 정확한 기존 실행과 선결

다음은 총괄 또는 사용자가 실행할 기존 진입점이며 이 담당자는 실행하지 않았다.

```bash
cd /home/uranus/tinyLM
./run_P101A_Stage3kW_verified_reasoning_pair.sh
./run_P101A_Stage3jW_clean_mtp_four_arm.sh
```

두 SH는 `scripts/shell/tinylm_env.sh`를 source하고 `tinylm_python`을 사용한다. 10/21 최초 MTP 직접 실행은 이 환경 적용을 빠뜨려 nvcc/Inductor의 Windows mount PermissionError·업데이트0으로 끝났고, helper 적용 후 비용이 성공했다. 같은 실수를 반복하는 새 수동 명령을 만들지 않는다.

| 축 | MTP | 직접답/풀이 |
|---|---|---|
| tag | `p101a_sft_mtp_cleanbilingual_v3_s1337` | `p101a_sft_mtp_verified_direct_v3_s1337` / `p101a_sft_mtp_verified_trace_v3_s1337` |
| 부모 | 고정 P090B300M dense14·dim768, SHA `12E18658…` | 같은 부모 |
| 구조·조건 | chat32, m8×a16, seq1024, ckpt ON, compile default, seed1337 | 동일 |
| optimizer | Adam5e-5/Muon2e-4, clip1 | 동일 |
| 자료·노출 | 22,528 TRAIN·DEV512, 4pass704 | 같은4096 TRAIN root, 4pass128, DEV1024·TEST1024 |
| 독립변수 | 같은 initializer 안에서 NTP 대 assistant-valid MTP(2/3/4) | 최종값만 대 코드로 검산한 짧은 중간상태 지도 |
| 실행 순서 | scratch NTP→scratch MTP→parent NTP→parent MTP | P090B parent baseline→direct→trace |
| 평가 | 각 팔 첫답512, FP32 MATH, MTP 추론 OFF | 부모 및 두 팔 첫답1024, 같은 설정 |

MTP 네 팔 각각의 실제 입력은 `5,405,444×4=21,621,776`, assistant target은 `552,609×4=2,210,436`이다. `704×8×16×1024=92,274,688`은 padded 계산 slot이며 실제 학습 토큰으로 보고하지 않는다. `check_run_registry --steps704 ...`가 출력한92.3M도 이 구분이 필요하다. custom tag는 registry 충돌 조회0이었지만 main 여부는 별도 evidence/CP 경로가 더 직접적인 근거다.

직접답/풀이의 실제 입력은 각각 `199,563×4=798,252`, `307,799×4=1,231,196`; 지도 target은 각각79,520 /512,464다. 풀이 target은 약6.44배이므로 동일 업데이트 비교이며 토큰·시간 고정의 순수 reasoning 이득 비교는 아니다.

선결은 현재 source/code/corpus/tokenizer pin, 해당 팔 비용32, 독립 출력 부재, GPU 유휴 상태, 남은 17시 창이다. 세 기존 cost 재검산은 통과했고 나머지 비용은 미실행이다. raw 답·native 전후·오류·부정 결과까지 회수할 예산을 먼저 예약한다. 이 SH의 개별 hard cap만으로 전역17시 종료가 보장되지 않으므로 총괄이 외부 종료 경계와 단계별 잔여 예산을 관리해야 한다. MTP의 명목19.3h·풀이4.2h hard-cap 합계는 현재 허용창보다 길다.

근거: [clean controller](../../scripts/diag_p101a_clean_bilingual.py) 38~49·53~85·133~187행, [원 엔진](../../scripts/diag_p101a_sft_mtp.py) 98~121·189~317행, [직접답 런처](../../run_P101A_Stage3kW_verified_reasoning_pair.sh) 10~29행, [첫답 평가](../../scripts/diag_p101a_clean_eval.py) 60~98·102~132행.

### 유지해야 할 판정 제한

- MTP 자료는 기존 QA/replay/공개 TRAIN 선택을 재사용한다. 새 teacher·75M 완결·독립 새 지식량으로 부풀리지 않는다.
- 이 MTP 목적에는 별도 native replay gradient가 없다. native CE 전후는 보존 모니터이며 방지 장치가 아니다.
- 현재 optimizer는 frozen factory를 재사용하므로 Muon 행렬 WD0 외 Adam 원 그룹0.1/0이 남는다. 문서의 전역 WD0와 혼동하지 않고, 오늘 기존 비용/본런 중간에 조용히 바꾸지 않는다.
- MTP 첫답512는 이미 학습 중 검증한 DEV이므로 독립 TEST가 아니다. 별도 새 평가가 필요하다.
- scratch는 같은 구조/seed로 학습 가중치를 복사하지 않는다. 약21.6M 입력의 scratch 저성능을 MTP 구조의 보편적 실패로 해석하지 않는다.
- 학습 보조 head는 추가2.25MiB tensor이며, 실제 MTP 추론 가속/정합성은 별도 검증 축이다. 오늘 첫답과 새 공통 우도 비교에서는 heads OFF를 유지한다.

## 5. 방문·셔플·router 구현 감사

방문 학습은 이미 구현됐다. `scripts/p078_route_training.py`의 네 정책은 uniform R2, 고정 seed0 비identity shuffle R2, update별 shuffle R2, 평균 R2를 유지하는1/2/2/3 균형 방문이다. `route_scope`는 backward/생성 세션 동안 route를 잠그고, session/model/receipt에 묶인 KV cache를 검산한다. 별도 코드를 다시 만들지 않는다.

`p078_route_training.learned_router()`의 stub만 보고 router 전체가 없다고 결론내리면 틀리다. 별도 `scripts/p078_prefix_router.py`와 `diag_p078_prefix_router.py`에 prefix 전용 head·TRAIN labels·DEV 선택·TEST 네 정책 비교가 구현돼 있다. 현재 미실행 공백은 **balanced_count 본704 본체**, 실제 TRAIN 상대 CE labels, 학습한 head, 실제 TEST다.

P078 본 네 팔의 실제 예측은31,028.581375초=8.619050h다. 이것은 cost32를 검산해 얻은 main/평가/1800초 기록 reserve이며 완료 보증이 아니다. 원 tuple/list 불일치는 `diag_p078_route_protocol.py`가 검산 내부 JSON 표현만 정규화해 해결한다. 원 학습 소스·route는 고정한다.

`run_P078_Stage2Wc_verified_route_full.sh`는 새 `TL_P078_AUTHORIZATION`/SHA와 fresh `budget-preview`가 선결이다. `run_P078_Stage3Wc_prefix_router_full.sh`는 추가 router 권한/SHA, 정확한 holdout SHA, 닫힌 balanced_count704 CP가 더 필요하다. 부모 R1을 몰래 대신 쓰는 과학 경로는 없다. 기존1.5h는 실제 cost8 전 미측정이다.

router 입력은 미래 정답 없는 prefix의 frozen embedding mean/위치가중mean/last/길이2개, 총770→64→3이다. 지도는 TRAIN에서 R1/R2/R3의 상대 CE이며 정답·불확실성·세계지식 verifier가 아니다. learned/random_quota/untrained/constant_train_mean과 실제 비용·첫답을 함께 비교해야 한다.

근거: [route helper](../../scripts/p078_route_training.py) 48~85·97~106·121~164행, [protocol](../../scripts/diag_p078_route_protocol.py) 34~37·91~110행, [router helper](../../scripts/p078_prefix_router.py) 24~33행, [router body gate](../../scripts/diag_p078_prefix_router.py) 172~207행, [결과066 §9.5](../../test_result/066_20260831_P078-이득은-몰려있지만-어느-크롭인지는-재현되지-않는다.md).

## 6. 새 공통 벤치마크에 연결할 CP와 loader

다음 여섯 기존 연구 CP는 해당 정확 TRAIN report가 `TRAIN_COMPLETE`이고 파일이 존재했다. 여기서는 CP tensor를 읽거나 CP SHA를 새로 계산하지 않았으며 아래 SHA는 닫힌 학습 report 값이다. 새 벤치마크 실행 시 strict loader가 실제 바이트·header·core를 다시 검산해야 한다.

| model id | CP 파일명(`runs/ckpt/` 아래) | report CP SHA |
|---|---|---|
| native595-q | `m100s10_ko-en_p106b_native595_v1_s1337_ternary_native.pt` | `C0610452ABF357868DA1CCDF16D98482D408F2D9D076C634444292023108BDF5` |
| native595-f | `m100s10_ko-en_p106b_native595_v1_s1337_float_native.pt` | `7DF60C47605B654520C510E2758D559213AABCB7ED1090424BDC0D50BC9413BA` |
| old299-broad-q | `m100s10_ko-en_broad4_p106b_native_broad4_recovery_v2_s1337_ternary.pt` | `39A68CA0B712074F2EAE1073DFF3A3C01AA661F356244A86A626E1F74365681F` |
| old299-broad-f | `m100s10_ko-en_broad4_p106b_native_broad4_recovery_v2_s1337_float.pt` | `357D2EA6A9F20918B260E1AA983AFC092F0139481356B2E6DF1EDD71F88D68A2` |
| new595-broad-q | `m100s10_ko-en_broad4_p106b_native595_broad_v1_s1337_ternary.pt` | `F3D1F0FBEDBFC1A336195F2E8C6005127057FF7929C2E21AD37BE252A2DA911C` |
| new595-broad-f | `m100s10_ko-en_broad4_p106b_native595_broad_v1_s1337_float.pt` | `2630B4C2862A41CB677AC9CAA89B0F2DD03234C4FD540FCCA6205AA847CF1C71` |

재사용 권장은 `scripts.interactive_research_infer.resolve_model(id)`와 `selected_runtime(spec)`이다. 이 기존 loader는 여섯 CP의 독립 manifest를 사용하고 과거 family 권한 함수를 호출하지 않는다. 정확 Q/F route와 전체 CPU/GPU core를 검산한 뒤 active dict의 `model/cfg/tokenizer/route`를 제공하므로, 새 benchmark는 이 context 안에서 점수화만 연결하면 된다. generic `load_model`로 float route를 ternary 모델처럼 읽는 경로를 만들지 않는다. 로더 이름이 manual이어도 로딩 context는 비대화형으로 재사용 가능하다.

반면 P090B와 오늘 생성할 MTP/direct/trace의 원래 dense CP는 `tinylm.infer.generate.load_model(arch='dense', ckpt_path=정확경로, device='cuda', mtp_heads='off')`가 현 첫답 평가의 경로다. 저장 cfg로 형상을 만들며 학습 MTP heads만 명시적으로 제외한다.

오늘 생성 예정 CP 이름은 `m100s10_ko-en_32M_dense_chat32_<tag>_<arm>.pt`이다. 파일명의32M은 기존 엔진 명명 관례이므로 실제 입력/지도량과 동일시하지 않는다. 본 CP가 생기기 전의 cost report에는 벤치마크할 학생 CP가 없다.

BabyLM 연결은 우선 P090B·native595 Q/F·new595-broad Q/F와 오늘의 parent NTP/MTP를 같은 원형/점수화 조건으로 비교하는 것이 유용하다. 이 후보를 이미 더 똑똑한 승자로 부르지 않는다. 새 benchmark의 원문 likelihood와 ChatML 첫답은 다른 측정이며 채점 계약을 섞지 않는다. 전체 사전학습 오염·공식 BabyLM 학습제약 준수·공식 harness 동등성은 이 감사에서 확인하지 않았다.

근거: [연구 모델 목록](../../scripts/interactive_research_infer.py) 48~85행, [독립 strict loader](../../scripts/interactive_research_infer.py) 356~450행, [dense loader](../../tinylm/infer/generate.py) 29~57행, [MTP CP 이름](../../scripts/diag_p101a_sft_mtp.py) 52~57행.

## 7. 긍정 가설과 꼭 필요한 반증

1. **MTP 가설:** 이미 제공된 문맥에서 assistant 미래2/3/4 토큰을 함께 감독하면 동일 부모 NTP보다 문맥 답 선택·종료가 개선될 수 있다. 같은 initializer·자료·seed·순서를 고정한 paired 팔, 양 언어 실제 첫답과 native 보존이 필요하다. 손실/보조 head gradient만 좋아진 경우는 이 가설의 성공이 아니다.
2. **중간상태 지도 가설:** 코드가 소유한 계산·상태 관계의 짧은 trace가 unseen root 최종값 정확도를 높일 수 있다. 같은 root 직접답과 parent baseline을 모두 보고, trace 형식과 최종값을 따로 채점한다. 추가 target6.44배·입력1.54배의 대가를 함께 남긴다.
3. **방문 가설:** 평균 방문수가 같아도 순서/개별 방문수 분포가 성능에 영향을 줄 수 있다. 현재 구현의 네 main704가 아직 없으므로 cost 답0/8을 학습효과 음성으로 승격하지 않는다. 이후에는 실제 처리량과 matched evaluation route·cache owner 계약까지 포함해야 한다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 8. 추가 요청 — 로컬 BabyLM 자산과 최소 연결 범위

### 8.1 확인한 자산 범위

보호 `datasets/TinyDataset`를 명시적으로 제외하고 `datasets/`, `HF/`, `data_cache/`의 파일명 및 하위 경로를 case-insensitive 검색했다. BabyLM/BLiMP/MSGS/EWoK 이름의 사용 가능한 파일은 발견하지 못했다. `datasets/bench/`의26개 JSONL에는 PIQA/HellaSwag/ARC·KLUE·KOBEST·GSM·heldout 등 기존 과제만 있었다. `eval_bench_suite.py`에 위 새 과제의 adapter/등록도 없다.

이는 선언한 세 루트의 이름 기반 감사다. 다른 이름으로 저장된 파일·다른 시스템 경로까지 전역 부재를 증명한 것은 아니다. 새 공개 자산 취득·버전/권리/원본 SHA 고정은 총괄 소유이며 이 담당자의 다운로드는0이다.

### 8.2 재사용할 것과 새로 필요한 것

| 영역 | 재사용 | 실제 필요한 새 연결 |
|---|---|---|
| 모델 | `interactive_research_infer.resolve_model/selected_runtime` | 새 benchmark endpoint id와 strict model id를 명시 대응. loader 복제 금지 |
| 수치 | `eval_bench_suite.seq_ce`의 mean/sum/token수 | 최소쌍/문맥-답 원형 adapter, 채점 규약, BOS/EOS/빈 prefix·분리 토큰화 계약 |
| 정밀도 | `diag_p106b_current_benchmark.FP32Forward` | 동일 FP32 MATH·TF32 OFF 적용, route/assert_active·본체 전후 hash 연결 |
| 통계 | `wilson`, `cluster_bootstrap_ci`, `paired_stats` | 원형 단위 ID·언어·현상/가족 단위를 보존해 실제 재표집 단위를 확정 |
| 산출 | `p106b_shards.ShardWriter/verify` | 원본/동결표본/입력 IDs/문항별 후보 점수/skip/시간/모델 pin의 새 manifest |

`seq_ce`는 빈 prompt에 `tok.encode('\n').ids[0]` 한 개를 선행시키고 CUDA BF16 autocast를 켠다(427~443행). 새 공식 계약과 같다고 가정하면 안 된다. 기존 FP32 wrapper를 함께 쓰면 바깥 autocast를 닫고 실제 FP32 logits를 확인할 수 있다. 기존 `run_mc`의 기본 primary는 mean CE이며 PMI 옵션도 있다(566~615행). 새로운 최소쌍 평가에 이를 그대로 연결하지 말고 원시 합/평균과 선택 규칙을 분리한다. 원문 최소쌍 우도에 ChatML 지시문을 몰래 추가하지 않는다.

MSGS/EWoK를 같은 단순 두 문장 likelihood로 평가해도 되는지는 이 로컬 코드 감사로 확인되지 않았다. 원 공식 task/scorer를 먼저 확인하고, 다른 과제의 축약 점수를 공식 BabyLM 종합 점수로 합산하지 않는다.

### 8.3 우선 세 모델과 이미 확인된 점수

다음은 기존 공개 선택형 과제의 점수이며 새 BLiMP/문법 점수는 아직 없다.

| strict 연구 id | 공개 benchmark id | PIQA/HellaSwag/ARC 각256 | 영어 합계 |
|---|---|---|---|
| `native595-f` | `native595_float` |161/72/112|345/768=44.921875% |
| `native595-q` | `native595_ternary` |147/69/108|324/768=42.1875% |
| `new595-broad-f` | `newbroad_float` |156/70/107|333/768=43.359375% |

각각 `test_result/evidence/p106b_native595_public_v1_s1337/evaluate_<benchmark id>/report.json`의 `CURRENT_PUBLIC_MODEL_COMPLETE`와 `summary`를 직접 읽었다. 별도 원답 재검산 `p106b_native595_public_independent_audit_v2_s1337/report.json`의 summaries도 같은 수치다. 그 최종 상태는 `SIX_CLOSED_MODELS_RAW_RECOUNTED_ORIGINAL_FAMILY_READBACK_HOLD`다. 여섯 모델 실제 평가·별도 raw 감사 완료와 원가족 정규 readback 미완료를 함께 유지한다.

이 세 모델은 native Q/F와 동일 float native→Broad 변화라는 비교축을 갖춘다. 새 문법 성능이 세 모델의 기존 MC 순위와 같을지는 미확인이다. 기존 Falcon398/768은 과거 동일 ID의 캐시 결과이므로 fresh BabyLM 준거로 재사용할 수 없다.

### 8.4 구현·실행 비용 추천

| 안 | 새 작업 | 비용 근거·한계 |
|---|---|---|
| A 권장 | 원형과 공식 점수 계약을 확인한 BLiMP 계열부터, source-only 균형 표본과 세 strict 모델의 비교 | 구현/CPU 검산45~90분은 작업량 추정. 첫32쌍(64문장)/모델의 비용을 측정한 뒤 예컨대512쌍/모델로 확대. 이 크기와3모델은 파일럿이며 전체 benchmark 완료가 아님 |
| B | 공식 BabyLM 전체 task/scorer를 설치·획득·연결 | 더 완전하지만 자산·의존성·MSGS/EWoK 계약·전체 비용이 현재 미확인. 오늘 완료시간을 미리 약속할 수 없음 |
| C | 기존26과제 캐시만 추가 재평가 | 데이터 취득 없이 가능하나 새 문법/통사/추론 계기를 추가한 것으로 보고할 수 없음 |

새 파일럿에는 총1시간의 GPU 평가 예약을 먼저 두고 actual cost 후 재입장 여부를 판단하는 안을 권한다. 이는 실측 예상이 아니라 시간 배분안이다. 과거 native Q/F 공개768 MC의 scoring worker는48.425/46.323초, new Broad F1919채점(생성 포함)은200.061초였다. 새 자료의 길이·후보수·정밀도가 달라 이 시간을 단순 문항 비례로 외삽하지 않는다. 신규 비용에서 초기 loader/hash 시간과 순수 문장 scoring 시간을 구분하고, 샘플 선택·문턱을 모델 결과를 본 뒤 바꾸지 않는다.

범위 전체의 새 모델/GPU/가중치 tensor 로딩·다운로드는0이다. 이 담당자가 추가한 파일은 이 감사 문서 하나뿐이다.
