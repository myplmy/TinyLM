# V4 감독 수리 소비자 설계 — 원 엔진을 재사용하되 마스크·서명·평가 입구를 함께 연결한다

상태: `DESIGNED / IMPLEMENTATION_NOT_RUN`. 이 문서는 읽기 전용 코드 감사와 설계다. 새 소비자·회귀·학습·평가는 구현하거나 실행하지 않았다. 실제 V4 생산 완료·수치는 생산 영수증이 소유하며, 아래 숫자는 producer의 기대 계약과 앞선 두 행 토크나이저 감사값이다.

## 1. 범위와 질문

| 대상 | 이번 동작 | 제외 |
|---|---|---|
| 이 설계 문서 | 신설 | 실행 명령·배치 신설 없음 |
| V3 controller·공용 engine·평가기·생산 코드 | 읽기 | 학습 중인 코드, PINS, producer/test 수정 없음 |
| V3/V4 원본·기존 결과·CP | 보존 | 자료 교체, CP 로딩, 학습/평가/GPU/설치/다운로드 없음 |

질문은 **새 학습 소비자가 V4의 두 `[2]`를 실제 loss에서 지키는가**이다. MTP 자체의 효과, 감독 수리의 일반화 효과, 모든 PUBLIC의 정확성을 이번 설계로 입증하지 않는다. 현재 진행 중인 V3 대조는 두 팔 모두 같은 V3로 닫고 noisy-control로 보존한다. V3 한 팔과 V4 다른 팔을 연결하거나, V3 CP를 이어 학습해 V4의 새 대조로 부르는 안은 제외한다.

영향도: 새 소비자·단위회귀가 필요하지만 모델/손실 엔진 수정은 불필요하다. 데이터 영향은 별도 namespace의 명시 감독 수리다. 실제 실행 전 계획/결과/기준표/방법론/COMPASS의 후속 연결은 총괄 소유이며 이 문서는 그 정본들을 갱신하지 않는다. GPU 권한·동시 작업·원형 소유권·비교 조건·증거 수준을 분리한다.

## 2. 실제 호출 경로와 단절 지점

| 현재 소유 지점 | 관측 | V4 소비자가 해야 할 일 |
|---|---|---|
| [clean `TAGS`, `main`](/home/uranus/tinyLM/scripts/diag_p101a_clean_bilingual.py:159) | `args.tag`를 V3 family 태그로 고정하고 V3 준비 버전/코드 SHA를 검사한다 | 기존 main을 호출하거나 `TAGS`/`VERSION`을 바꾸지 말고 별도 버전형 진입점을 둔다 |
| [공용 `corpus_report`](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:72) | `CORPUS_READY`만 허용한다. V4의 `SUPERVISION_REPAIR_PREPARED_NOT_ADMITTED`는 현재 거부가 정상이다 | V4 원문 report/audit와 별도 실험용 실행 승인을 검산하는 reader가 필요하다. 원 report의 status를 바꾸지 않는다 |
| [공용 `encoded`](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:124) | `core.encode_record` 직접 호출이라 `supervised_assistant_turns`를 읽지 않는다 | `clean.encoded` → `masked_record` 경로를 실제로 연결한다. 태그 변경만으로는 부족하다 |
| [clean `masked_record`](/home/uranus/tinyLM/scripts/diag_p101a_clean_bilingual.py:38) | 허용목록 밖 y를 `-100`, owner를 `0`으로 만든다 | 기존 함수를 재사용한다. 없는 허용목록을 자동 추론하거나 전체 PUBLIC이 검수됐다고 해석하지 않는다 |
| [공용 `train_arm`](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:189) | 내부에서 `corpus_report`를 다시 호출하고, `load_runtime` 뒤 `encoded`를 호출한다 | reader와 encoder binding을 **전체 호출 동안** 유지한다. 바깥에서 report 한 번 읽는 것만으로는 안 된다 |
| [clean optimizer wrapper](/home/uranus/tinyLM/scripts/diag_p101a_clean_bilingual.py:133) | `ORIGINAL_OPTIMIZERS`를 main에서 따로 저장해야 한다 | 원 factory를 먼저 closure에 보관해 호출하고 LR만 기존 clean 값으로 설정한다. 초기값 None인 wrapper를 단독 호출하거나 패치된 자신을 재호출하지 않는다 |
| [clean `info`](/home/uranus/tinyLM/scripts/diag_p101a_clean_bilingual.py:145) | V3 버전과 전칭처럼 읽히는 `train_wrong_assistant=False`를 넣는다 | 그대로 복사하지 않는다. V4 SHA/수리 범위/나머지 미전수검토를 새 서명에 명시한다 |
| [cost `validate`](/home/uranus/tinyLM/scripts/check_p101a_clean_cost.py:18) | 팔·32회·full updates·코드/자료·시간·분모를 검산한다. CLI는 V3 경로에 고정돼 있다 | 함수는 재사용하되 V4 경로/metadata를 직접 전달한다. 기존 CLI를 V4 검사기로 오인하지 않는다 |
| [첫답 `prerequisites`](/home/uranus/tinyLM/scripts/diag_p101a_clean_eval.py:60) | V3 태그/버전과 같은 corpus SHA의 닫힌 학습 report를 요구한다 | V4용 선결 검사를 별도 binding한다. 학습만 V4로 바꾸고 평가를 V3로 남기지 않는다 |
| [첫답 `execute`](/home/uranus/tinyLM/scripts/diag_p101a_clean_eval.py:102) | 출력 evidence는 precondition 반환값을 쓰지만 검수 파일명은 `20261021_<family>_<arm>`으로 태그가 없다 | V4 고유 검수 식별자까지 분리해야 한다. 기존 review 파일 삭제·덮어쓰기로 해결하지 않는다 |
| [공용 `compare`](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:320) | 원 네 팔 전부를 읽고 같은 initializer 안에서 비교한다 | 새 네 팔이 모두 끝난 경우에만 그대로 재사용한다. 두 팔만 끝났으면 별도 pair readback으로 `2/4`를 표시하고 원 ARMS를 축소하지 않는다 |

따라서 producer 완료는 caller 완료가 아니다. 특히 `--tag`만 V4로 지정해 공용 engine을 직접 실행하면 status에서 막히거나, 거부 조건만 우회한 경우에는 `[2]`를 무시하는 encoder를 사용할 위험이 있다.

## 3. 세 가지 안과 권장 범위

| 안 | 방식 | 적합한 경우 | 비용·위험 |
|---|---|---|---|
| A — 얇은 범위형 어댑터, 권장 | 원 `train_arm`을 그대로 호출하고 reader/encoder/optimizer만 context 안에서 binding. 기존 첫답 execute도 V4 precondition과 고유 출력 식별자로 재사용 | 지금처럼 단일 프로세스·직렬 단계로 기존 clean 흐름을 최소 연결할 때 | 구현/회귀 비용 작음~중간. 함수 global binding이 빠지거나 자식이 옛 CLI로 재진입하면 무효이므로 실제 호출 회귀가 필수 |
| B — 원 엔진의 격리 module namespace | 같은 고정 소스를 별도 module 이름으로 로드하고 그 module의 reader/encoder/factory만 교체. 본문을 파일로 복제하지 않는다 | 장차 여러 소비자가 같은 프로세스에 공존하거나 전역 patch 복구 위험을 줄일 때 | 구현/회귀 비용 중간~높음. 원 모듈로 돌아가는 함수 내부 import와 `__globals__`를 전수 검증해야 한다. 수학/모델 이점은 없고 유지보수 비용이 더 든다 |
| C — 소비자 CPU 계약까지만 닫고 V4 본실험 보류 | 준비·마스크·호출·서명 mock을 먼저 확보하고 새 GPU admission/cost/main은 다음 창으로 넘긴다 | 남은 창에 두 새 cost와 두 본런·첫답 평가·후행 판독이 함께 들어가지 않을 때 | 당장 GPU 비용 0. 실제 V4 모델은 없으며 “연결 완료/품질 회복”이라고 보고하지 못한다 |

**권장:** A를 최소 구현 범위로 삼되, 현 V3 두 팔 완료 뒤 **별도 V4의 동일 initializer NTP/MTP 두 팔**부터 검토한다. 다음 질문을 부모 계보의 MTP 효과로 정한다면 원 P090B에서 새로 시작하는 `parent_ntp`/`parent_mtp` 쌍이 최소다. 이는 총괄 제안이지 사용자 선택으로 사칭하지 않는다. 새 창/비용이 부족하면 C로 명시 보류한다. scratch까지 필요한 질문은 새 V4 네 팔을 사전 선언하고 모두 완료한 뒤 판정한다. A/B 어느 쪽도 pinned source 수정이나 거대 학습 controller 복제를 요구하지 않는다.

## 4. 권장 어댑터의 좁은 책임

새 버전형 파일/테스트는 **후속 승인 후** 구현한다. 이번에는 만들지 않는다. 손실·모델·optimizer update·compile·CP 저장 루프는 원 engine이 계속 소유한다.

1. 명시한 V4 corpus 경로/report SHA/audit SHA와 producer/helper 코드 SHA를 검산한다. 초기 최소 구현은 기본 HF V4 경로 하나만 허용하고 data_cache 후보나 V3로 자동 fallback하지 않는다.
2. 실제 raw status는 `PREPARED_NOT_ADMITTED`인 채 유지한다. 별도의 정확 V4/소비자/팔/예산에 묶인 **실험용 실행 승인**이 있어야 새 reader가 반환한다. `CORPUS_READY`로 바꾼 사본, on-disk 승격, 품질 전칭을 만들지 않는다. 원 `train_arm`은 reader가 돌려준 dict를 소비할 수 있으므로 status 위장은 필요 없다.
3. CPU tokenizer와 **실제로 binding할 encoder**로 TRAIN/DEV를 검산한다. `records`의 순서·x/y/owner fingerprint, 전체 counts, 두 source의 h1–4를 서명한다. 원 engine은 모델을 읽은 뒤 encode하므로, 실패를 모델 전에 잡으려면 이 CPU 입구를 어댑터가 먼저 수행해야 한다.
4. 검산된 records를 cache해 반환하는 좁은 encoder closure를 쓰거나 동일 encoder를 다시 실행해 같은 fingerprint를 요구한다. 실제 runtime tokenizer도 같은 바이트/버전이어야 한다. 호출 횟수/실제 source SHA를 별도 소비 영수증에 남겨 “검사한 encoder와 실행한 encoder가 다름”을 잡는다.
5. 원 optimizer factory를 패치 **전에** 보관하고 원 그룹을 그대로 만든다. LR은 현 clean의 Adam `5e-5`, Muon `2e-4`를 유지한다. 행렬 WD0를 전체 Adam 그룹 WD0로 조용히 확대하지 않는다.
6. binding은 `train_arm`의 내부 reader 재호출부터 평가/저장/종료까지 유지하며 예외에도 복구한다. 원 ARMS/CODE/TAGS/PINS를 수정하지 않는다. 별도 subprocess를 쓴다면 자식도 새 어댑터로 들어오게 한다. 프로세스 내 patch가 exec를 넘어 보존된다고 가정하지 않는다.
7. 원 결과가 있어도 새 소비 영수증이 없으면 V4 완료로 채택하지 않는다. 원형 report/CP는 보존하고, 어댑터의 사후 검산 실패를 따로 남긴다. 기존 출력이 있으면 중단하고 자동 삭제/재시도하지 않는다.

안정적인 과학 서명에는 V4 report/audit, tokenizer, 두 원천 ID/line SHA, 원/새 코드와 실행 의존성, 배치/순서/패딩, 초기화, LR/optimizer 그룹, head/horizon/schedule, 평가 profile을 넣는다. 원 `engine.CODE`만으로 충분하다고 보지 않고 `model/modules.py`, Muon/optimizer audit, serializer/canonical, 평가 helper 등 실제 호출 의존성을 보완한다. 실행 시각·현재 잔여 시간·단계별 cap/권한 영수증은 별도 실행 영역에 둔다. 매번 달라지는 값을 안정 서명에 섞어 cost/main이 영원히 불일치하게 만들지도, 기존 validator의 비교 항목을 느슨하게 만들지도 않는다.

## 5. y/owner에서 실제 h1–4 loss까지의 보증

원 [count_record/horizon_targets](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:66)와 [components/normalized_loss](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:117)를 그대로 사용한다.

| 원천 | 첫 assistant의 기존 h1/2/3/4 | V4 첫 assistant | 둘째 assistant: V3/V4 동일 |
|---|---|---|---|
| PUBLIC192 | 91 / 90 / 89 / 88 | 0 / 0 / 0 / 0 | 52 / 51 / 50 / 49 |
| PUBLIC198 | 365 / 364 / 363 / 362 | 0 / 0 / 0 / 0 | 404 / 403 / 402 / 401 |

필수 조건은 첫 턴 y 전량 `-100`/owner0, 둘째 y/owner/EOT 보존, x 전량 동일이다. 첫 답은 입력 이력에 남고 후속 정답 loss에서 간접 영향을 줄 수 있다. 456은 첫 답 두 개 전체의 직접 감독 제외 분모이지 456개의 사실 오류 토큰이라는 뜻이 아니다. 첫 EOT도 제외하고 둘째 EOT는 유지한다. 유저/마스크 경계를 넘어서는 h2–4 window는 기존 같은-owner 조건으로 거부돼야 한다.

전체 기대 계약은 TRAIN 22,528행/5,405,444x/552,153 targets, DEV512/127,921x/2,977 targets, 4pass704 updates다. 4pass x는21,621,776, NTP targets는2,208,612이며 padded slot92,274,688과 다르다. 생성된 V4의 실제 report/audit와 매번 대조해야 하며, 이 문서가 수치 정본을 대체하지 않는다.

원 full-run 종료 검사는 updates/x만 직접 검사하므로 어댑터 readback이 총 `assistant_targets`, 각 epoch의 target/x, 두 수정 원천의 4회 노출을 추가 검산해야 한다. MTP의 history `active_head_target_counts`는 **활성 보조 weight가 있는 update**만 센다. 마지막 update는 기존 schedule에서 weight0이므로 단순히 전체 h2–4 분모×4를 요구하면 틀린 검산이다. 같은 `batches`·`coefficients`로 사전 계산한 active 분모와 대조한다. NTP 팔의 보조 활성 target0은 정상이다. cost32가 두 수리 행을 실제 방문했을 것이라고 가정하지 않는다.

## 6. 첫답 평가: 새 구현보다 기존 평가기의 정확한 버전 연결

주판정 경로는 [기존 clean 첫답 평가](/home/uranus/tinyLM/scripts/diag_p101a_clean_eval.py:102)를 재사용한다. 새 V4 precondition이 다음을 모두 검사해야 한다.

- 같은 V4 report/audit/소비자 서명의 완료 학습 report와 별도 소비 영수증, 정확 arm/CP SHA/토크나이저. V3 학습 report나 단순 파일 존재를 허용하지 않는다.
- 기존과 같은 DEV512 순서/질문, `FP32_MATH_TF32_OFF`, cache ON, `mtp_heads='off'`, `mtp_tokens=1`, greedy/top1/max_new128/EOT stop, retries0. MTP 학습 효과와 MTP 추론/FP16 head 정합 실험을 섞지 않는다.
- 출력 report뿐 아니라 검수 Markdown 경로도 V4로 구분한다. 최소 연결 후보는 어댑터 내부의 명시한 versioned selector `mtp_supervision_v4`를 기존 execute의 family 인자로 주고, 교체된 precondition은 canonical family=`mtp`, split=`val`을 별도로 기록하는 방식이다. 옛 CLI 허용값을 넓히지 않으며 실제 selector와 canonical family를 둘 다 영수증에 남긴다. 이는 고정 review basename 충돌을 피하기 위한 **출력 namespace**이지 새 과제나 데이터 변환이 아니다. 기존 `20261021_` prefix는 legacy basename일 뿐 실제 실행일로 보고하지 않는다. 이 연결이 모호하거나 원 함수가 다른 family 분기를 추가했다면 구현을 중단하고 작은 독립 출력 sink를 검토한다. 모듈 ROOT/Path 전역을 넓게 바꾸거나 old review를 삭제하는 해결은 권장하지 않는다.
- 위 selector가 과제 선택/금정답/원천 SHA를 바꾸지 않으며 원 V3 평가가 변하지 않는 mock을 먼저 통과시킨다. 기존 test의 score/prompt 예제만으로 이 새 호출 연결이 검증됐다고 하지 않는다.

DEV512는 학습 중 validation으로 쓰던 집합이며 독립 TEST가 아니다. annotation exact match와 종료/빈 답/추출실패/한영 raw 내용 검토를 분리한다. prompt에 기존 assistant 이력이 있으면 “첫답”은 그 주어진 prompt 뒤 첫 생성이지 대화 전체의 최초 턴/자유 rollout이라는 뜻이 아니다. 수리된 두 PUBLIC TRAIN 행은 자동으로 DEV에 추가되지 않으며, 추가해서 일반화 점수로 합산해서도 안 된다.

별도 진단을 원하면 두 source의 교정 continuation은 `TRAIN_REPLAY`로만 표기한다. 기존 `prompt_messages(row)`는 마지막 assistant만 떼므로 두 턴 행에서는 **옛 assistant가 주어진 gold-history continuation**이다. 이를 최초 자유답이나 실제 자가 교정 대화로 부르면 안 된다. 특히198의 첫 질문 “open ai”는 원래 모호하므로 open-source 답만을 최초 gold로 강요하지 않는다. 사용자 명확화가 포함된 새 단일 질문/실제 생성 이력의 후속 질문은 별도 사전 고정 진단이며 본 DEV 점수와 합산하지 않는다.

원 `train_arm`의 고정8 [answers](/home/uranus/tinyLM/scripts/p106b_education_followup.py:444)는 조건부 최대3시도다. 그대로 보존하되 `first_attempt_pass`와 `pass_within_three`를 분리하고 raw attempt1을 회수한다. 추가 진단을 이 helper의 초기 평가 중간에 넣어 RNG/시간을 바꾸지 않는다. 본 첫답512 평가도, MTP inference parity가 보인 “같은 답”도 일반적인 의미 정답을 보증하지 않는다.

## 7. 초기화·비용·예산

[load_runtime](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:98)을 그대로 재사용한다. scratch는 원 parent의 형상/토크나이저 계보를 읽지만 학습 가중치를 복사하지 않고 seed1337로 새 본체를 만든다. parent 팔은 같은 고정 P090B 가중치만 읽는다. 각 initializer 안에서 NTP/MTP의 initial core SHA를 맞추며 scratch와 parent끼리 같아야 한다고 요구하지 않는다. [attach_mtp_heads](/home/uranus/tinyLM/tinylm/model/transformer.py:484)는 RNG를 소비하지 않는 clone 방식이며 optimizer 전 attach 순서도 유지한다. cost32의 업데이트된 본체를 main의 초기화로 재사용하지 않는다.

원 `checkpoint(tag, arm)` 파일명의 `32M`은 역사적 접두사다. 이 함수를 재사용하더라도 실제 V4 입력량/지도량으로 보고하지 않고 report의 실제 counts를 사용한다.

**V3 cost를 V4 입장권으로 재사용하면 안 된다.** x/순서가 같아도 corpus/report/audit/소비자 코드 SHA와 gathered head/CE targets가 다르다. 원 `train_arm`도 같은 code/corpus를 요구한다. V3 cost는 역사적 시간 참고값일 뿐이다. 실제 선택한 V4 팔마다 새 cost32가 필요하며, 같은 initializer라는 이유로 NTP cost를 MTP 팔에 복사할 수도 없다.

원 `train_arm`의 cost 입구는 status/code/corpus 중심으로 비교한다. 새 어댑터는 더 강한 기존 `check_p101a_clean_cost.validate`를 직접 호출해 arm·32회·704 full updates·CP 저장0·32개 유한 양수 시간·실제 x/target 분모까지 확인한다. 새 wrapper/의존 코드가 바뀌면 기존 V4 cost도 다시 검토해야 한다. 소비자 연결 후 비용은 이 문서에서 측정하지 않았다.

| 단계 | 미래 최소 비용 | 현재 증거 |
|---|---|---|
| 실제 V4 생산/CPU 소비 계약 | 전체 tokenizer/행 검산+mock; GPU0 | producer 준비와 consumer 검증은 별개이며 이 문서는 실행0 |
| initializer 한 쌍 cost | NTP32 + MTP32 | 새 V4 측정 필요, 시간/VRAM 미측정 |
| 같은 V4 한 쌍 main | 각704 updates, 둘 다 새 초기화 | NOT_RUN; 같은 자료/서명으로 쌍을 완료해야 함 |
| 첫답/후행 검산 | 각 DEV512 + 기존 raw8/native 판독 | NOT_RUN; update 외삽만으로 이 시간을 포함했다고 하면 안 됨 |

원 wall_limit은 상대 worker cap이지 절대17시 종료나 모든 단계의 잔액 원장이 아니다. 현재 허가의 절대 종료·정리 여유·외부 timeout·GPU 단독 점유를 유지하고, 적용되는 실제 지출 원장을 새 tag로 초기화하지 않는다. P078의 별도 가족 예산을 V4 승인 대신 쓰거나 그 원장을 변경하지도 않는다. 오늘 창에 모두 못 넣으면 C이며, 다음 창은 새 승인이 필요하다.

## 8. 구현 승인 뒤 필수 회귀와 no-claim 경계

1. 새 check-only는 원천/CP/모델/Torch 없이 코드·계약만 읽는다. V4/승인 부재·잘못된 SHA/status·symlink·기존 출력·만료는 모델 전에 거부한다.
2. 실제 새 진입점→reader→encoder→원 `train_arm` 내부 재호출의 연결을 mock으로 확인한다. 원 raw `engine.encoded`로 회귀하거나 옛 CLI를 자식으로 실행하면 실패해야 한다. 예외 시 binding 복구와 V3 불변도 검사한다.
3. 두 source ID/원문/line SHA/순서가 맞는 V4 실제 encode에서 위 표를 재검산한다. 첫 EOT masking, 둘째 EOT 유지, 경계 straddle, 전체 h1 및 active h2–4 분모, 언어/원천별 token mass를 검사한다. 후자는 행 비율을 target 균형으로 오인하지 않기 위한 기록이다.
4. cost 잘못된 팔/단계/코드/자료/분모/32회 미완결과 V3 cost를 모두 거부한다. source/소비자 SHA가 달라진 뒤 완료로 승격하지 않는다.
5. first-answer CLI/selector→V4 precondition→CP→DEV512→score/raw/review output까지 mock 연결을 검사한다. V3 CP, 원래 review 경로, retries/선택후 best 답, source198의 모호한 최초질문을 고정 gold로 취급하는 경로를 거부한다.
6. 실제 GPU 실행은 별도 승인 뒤다. initial core·실제 records 서명·704회/x/target·history·CP/report/raw 연계가 맞아야 소비 완료이며, 그 뒤 첫답 의미/언어/보존 판정을 별도로 한다. 단일 initializer 두 팔은 `2/4`이며 원 네 팔 compare를 속여 호출하지 않는다.

예측: 같은 엔진/입력이라 연결 자체는 작은 adapter로 가능하지만, 두 첫 답의 직접 감독만 제거한 것으로 일반대화나 독립 의미 평가가 개선될지는 미확인이다. 잘못된 이력은 입력에 남고 나머지 PUBLIC은 전수 검수되지 않았다. MTP는 진위 판정기가 아니다. V3와 V4의 교차 비교에는 감독·분모 변화가 포함되므로 이를 MTP 단독 효과로 귀속하지 않는다.

이 문서는 현재 허용된 설계 산출물 하나이며, 소비자 구현·실제 V4 준비·새 cost/main·첫답 평가·채택을 완료로 선언하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
