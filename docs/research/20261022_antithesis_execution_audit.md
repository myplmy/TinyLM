# 2026-10-22 실행 전 독립 반증 감사

작성: 반 담당. 권한은 지정 문서 신설과 코드·문서 읽기뿐이다. 모델/실물 가중치 로딩·GPU·학습·다운로드·설치·Git·보호 TinyDataset 접근과 기존 코드 수정은 하지 않았다. 아래는 소스 감사이며 시험을 새로 실행한 결과가 아니다. 총괄은 실험 실행·WIP·계획/결과 정본을 소유한다.

## 1. 우선 판정

새 clean bilingual MTP 및 direct/trace 본대조를 우선하는 방향은 타당하다. 현재 읽은 코드에서 초기 본체가 MTP head 부착 때문에 바뀌거나, 교정 전 오답을 MTP target으로 되살리거나, 다음 user/PAD를 미래 목표로 삼는 결함은 발견하지 못했다. 그러나 아래 실행 선결과 주장 경계를 닫아야 한다. 이 문서는 모든 코드의 무결성·실행 안전·품질을 인증하지 않는다.

| 항목 | 관측·위험 | 필요한 처리 |
|---|---|---|
| 오늘 17시 종료 | clean controller와 재사용 engine은 상대 `max_wall_sec`만 적용한다. 기본4h가 현재 허가창을 자동 반영하지 않는다 | 각 cost/train/eval 직전 최신 잔여시간에서 종료·정리·기록 여유를 뺀 cap을 전달하고 별도 절대종료 관리. 옛40h 편성은 오늘 권한이 아니다 |
| 비용32 재사용 | engine 내부 선결은 status/code/corpus만 확인한다. 별도 `check_p101a_clean_cost.py`는 arm·32회·LR·분모·기대 본업데이트·CP 미저장까지 확인한다 | 직접 train 호출도 강화된 reader를 먼저 통과. 비용 없음/불일치/성공 재사용을 구분하고 원보고를 지우지 않는다 |
| 초기 본체의 사전 교차 | 엔진 compare는 네 본학습 완료 뒤에 initializer 내부의 본체 불일치를 검사한다 | 각 scratch/parent의 비용32 NTP·MTP 쌍과 direct·trace 부모 비용의 initial_core_sha256를 본런 전에 대조. 현재 불일치가 발견됐다는 뜻은 아니다 |
| 같은 코드의 범위 | clean.info가 계승하는 engine.CODE에는 실제 attention/삼진/optimizer 구현 일부가 빠져 있다 | modules.py·ternary.py·muon.py·optimizer_audit.py 등 실제 의존 모듈은 총괄의 source freeze로 추가 확인. 현재 비용 메타만으로 전 의존 코드 불변을 주장하지 않는다 |
| NOT_ADMITTED | 현재 교과 입력은 기존 자연 QA/replay·공개 canonical TRAIN이다. 10/22 목록 문장화·용어 수리·Luna 초안 후보는 코드상 입력 경로가 아니다 | CORPUS_READY를 전량 의미 검수·최신 정제 후보 입장·formal TRAIN_READY와 동일시하지 않는다. 새 후보를 경로 교체로 조용히 편입하지 않는다 |
| 방문 정책 checkpoint | route_scope가 업데이트 전체 backward까지 경로를 잠그고 cache도 모델·세션·receipt에 묶는다. 균일 경로의 제품 대조와 mutation 거부 회귀는 존재한다 | 비균일 fixed/update shuffle 및 R1/R3의 checkpoint ON/OFF 손실·파라미터 기울기 대응 증거도 확인. 유한한 gradient나 cost32 성공만으로 동일 gradient를 보증하지 않는다 |

## 2. MTP: 확인한 것과 못 확인한 것

- `diag_p101a_sft_mtp.load_runtime`: cfg의 MTP를 끈 상태에서 seed1337로 본체를 만든 뒤 parent 팔만 고정 부모를 로드한다. 본체 fingerprint를 먼저 계산하고 보조 head를 부착한다.
- `TiedMLPTransformer.attach_mtp_heads`: 본 head projection의 detach/clone으로 별도 Parameter를 만들며 RNG를 사용하지 않는다. 기존 `test_main_state_and_rng_unchanged`와 head checkpoint gradient 대조가 존재한다.
- 같은 초기화 조건은 scratch-NTP↔scratch-MTP 및 parent-NTP↔parent-MTP 각각이다. scratch와 parent의 본체가 같아야 한다는 요구는 잘못이다. 기존 compare는 initializer 내부의 초기 본체·자료·노출·target·업데이트·코드를 대조한다.
- `masked_record`는 명시한 supervised assistant allowlist 바깥의 y를-100, owner를0으로 바꾼다. `horizon_targets`는 모든 중간 target이 같은 양의 owner이며 마스킹되지 않았을 때만 허용한다. EOT 자체는 합법적인 끝 목표이고 다음 턴/PAD는 아니다.
- main CE와 각 horizon의 분모는 전체 optimizer update의 실제 감독 위치 수이다. 보조 projection gradient·loss 감소·추론 draft 수락률은 정답성 인증이 아니다.
- 새로운 교과의 704회는 기존 Broad 704와 목적함수가 같지 않다. 이번 엔진에는 Broad의 추가 native replay gradient가 없고, native32는 전후 진단이다. 옛8M은 LR도 달라 새로운 순수 자료 효과 비교가 아니다.
- MTP 네 팔의 동일 row/target 노출은 추가 head 계산까지 동일하다는 뜻이 아니다. 실제 update/wall·추가 파라미터/optimizer·head gradient와 품질을 각각 보고해야 한다.

근거: [clean controller](../../scripts/diag_p101a_clean_bilingual.py), [재사용 engine](../../scripts/diag_p101a_sft_mtp.py), [손실/턴 경계](../../tinylm/train/mtp_sft.py), [모델 head](../../tinylm/model/transformer.py), [비용 reader](../../scripts/check_p101a_clean_cost.py), [기존 회귀](../../scripts/test_p101a_sft_mtp.py).

## 3. 자료·입장·평가 오염

`rows_for('mtp')`는 기존 NATURAL v1의 TRAIN views0/1, DEV view2, replay, Broad v2의 selected_source_indices에 해당하는 p090_public_v3 원행을 읽는다. 따라서 clean은 문맥결손 교사4473행 제외와 교정턴 마스크를 갖춘 실험 교과라는 뜻이다. 전체 위키/FineWeb 본문 정제, 학술 용어의 표준성 검증, 최신 Luna 번역 후보의 학습 입장 완료라는 뜻이 아니다.

공식 TRAIN 주석을 감독 target으로 쓰는 것과 최종 benchmark 정답을 되먹이는 것은 다르다. 코드에는 `official_train_annotation_gold_inputs`, `official_eval_gold_inputs=0`, `luna_drafts_admitted=0`, 전체 사전학습/재표현 오염 미감사가 분리돼 있다. 이것은 읽은 경로의 계약이며 전 사전학습 자료의 독립 재감사 결과가 아니다. 자연 QA의 실제 진실성·다른 표현 동치까지 검수했다고 주장할 수 없다.

MTP 첫답 평가는 학습 중 검증에 쓰는 DEV512의 annotation exact이다. 새 독립 TEST나 범용 의미 정확도가 아니다. 과거 assistant가 들어 있는 평가는 제공된 고정 이력 아래 마지막 답의 첫 시도이며, 모델이 앞 턴부터 스스로 이어간 전체 rollout 검증과 구별한다. native32도 전 원문 풀의 언어 보존 증거가 아니다.

근거: [새 첫답 평가기](../../scripts/diag_p101a_clean_eval.py), [P101A 계획 신규 절](../../test_plan/P101A_M0-U2-QK-MTP-기능계약.md), [결과092 §15~16](../../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md), [10/22 미입장 상태 인계](../../handoff/202610220107_HANDOFF.md).

## 4. 직접답 대 검산풀이

동일4096개 TRAIN root·같은 질문·부모·4pass128회이지만 감독 패키지가 다르다. 계획/준비 기록상 직접답은 입력199563·target19880/pass, trace는 입력307799·target128116/pass로 target이 약6.44배다. 같은 padded slots와 update 수는 같은 실제 target 노출·계산량을 의미하지 않는다. `reasoning 효과만 분리`, `같은 token 예산에서 효율 개선`이라고 보고하면 무효다.

생산자는 addition/lookup/update의 코드 사실을 먼저 정하고 canonical root로 이름·표현·질문대상·교환형을 묶어 split한다. 원래 사용자 1+1/2+2와 canary 덧셈, 초기값3/5 표도 예약한다. 각 중간 digit/carry 또는 update/query/select를 원래 입력 사실로 재검산하며, final 값과 trace 형식/단계의 정오는 분리된다. 외부 공개 지식의 독립 verifier나 학습된 잠재추론 경로는 아니다.

DEV/TEST1024행은 각각128 root의 언어·표현 반복이다. 1024개의 독립 문제로 계산하지 말고 root 단위 대응과 언어/표현별 결과를 보존해야 한다. 최초 답만 평가하고 정답 숫자를 임의 위치에서 주워 맞히지 않는 scorer 정책을 유지한다.

근거: [검산 생산자](../../scripts/p106b_verified_trace_data.py), [첫답 scorer](../../scripts/diag_p101a_clean_eval.py), [producer 회귀](../../scripts/test_p106b_verified_trace.py).

## 5. P078 방문 랜덤·shuffle·prefix router

기존 P070B의 CLA 원자 단위 일정·owner별 방문 key·고정 route 모델을 재사용한다. owner/consumer의 순서와 같은 방문 번호, route multiset을 검사하고 boundary CLA 조각을 고정한다. shuffle은 별도 random.Random/hash로 계산하므로 전역 학습 RNG에 의존하지 않는다. 제품 forward의 checkpoint closure는 layer·KV·mode 값을 기본 인자로 포착한다. route는 한 update의 모든 micro/backward 동안 바뀌지 않으며, cache는 다른 모델/다른 세션에서 같은 경로라도 거부한다. 새 router를 모델 코어에 중복 구현할 이유는 없다.

네 방문 팔은 같은22528 교과·부모·4pass704회이지만 eager/compile OFF·MTP OFF이다. 앞 MTP 엔진의 compile 경로·목적함수와 새4팔을 그대로 인과 비교하지 않는다. balanced_count의 R1/R2/R2/R3 평균과 전체 padded layer-visit slots가 R2와 같아도 R3 peak, 실제 길이·배치 및 지연 분포까지 같지는 않다. matched-policy VAL이 주판독이고 uniform R2로 강제한 결과는 학습 함수 불일치의 보조 진단이다.

prefix router의 과학 단계는 미리 정한 balanced_count704 본체의 닫힌 완료를 필요로 한다. R1 parent의 resource-only 실행을 scientific fallback으로 승격하지 않는다. TRAIN-only R1/R2/R3 CE를 라벨로 쓰고, 알려진 과거 이력+현재 assistant header까지만 prefix feature로 읽으며 standalone 인코딩 일치를 검사한다. DEV1/3/5 선택과 별도 연결성분 TEST, random quota/untrained/constant controls가 존재한다. 원 V1의 부족을 seed 검색·최소량 축소·row 삭제로 회피하지 않는다.

head는 임베딩의 mean·position-weighted mean·last token과 길이 특성의 작은 MLP다. 훈련 CE 상대값 예측이나 같은 quota 선택이 실제 정답·추론 능력·지연 이득을 보장하지 않는다. 전 사전학습 오염 및 재표현 동치는 미감사다. TEST 자유답·정답 판독·feature/head 오버헤드 포함 wall을 회수해야 의미가 생긴다.

근거: [방문 학습 primitive](../../scripts/p078_route_training.py), [방문 controller](../../scripts/diag_p078_route_training.py), [기존 CLA 구현](../../scripts/p070b_cla_routes.py), [router primitive](../../scripts/p078_prefix_router.py), [router controller](../../scripts/diag_p078_prefix_router.py), [기존 route 회귀](../../scripts/test_p078_route_training.py), [기존 prefix 회귀](../../scripts/test_p078_prefix_router.py).

## 6. 이번 선택지와 권고

| 선택 | 장점 | 비용·위험 | 권고 |
|---|---|---|---|
| MTP 네 팔+직접답/trace를 먼저 완료·원답 회수 | 자료/감독 목적을 분리한 새 질문에 답한다 | 네 팔·평가·저장 시간이 필요. cost32 외삽은 전체 wall 보증이 아님 | 우선. deadline·source/cost 선결을 닫고 독립 첫답·보존 기록까지 확보 |
| 남은 시간에 P078 네 정책의 본대조 | 새 교과에서 학습 시 경로 정책 효과를 직접 본다 | 기록상 본704×4 최소예약8.619h 이상이며 기존40h 권한 계약을 별도 갱신해야 한다 | 전체 미완료 평가/검산 여유까지 실제 창에 들어갈 때만 진행 |
| prefix router까지 동시에 확장 | 학습된 경로 선택과 고정 quota 제어를 비교 | balanced704 완료 후 labels/fit/DEV/TEST/원답 비용과 본체·source 계약이 추가된다 | 오늘의 필수 결과를 밀어내지 않는다. 사전 선결이 없으면 준비/HOLD 유지 |

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
