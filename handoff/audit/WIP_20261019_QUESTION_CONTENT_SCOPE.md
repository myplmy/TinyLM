# 질문 내용 선택 진단 범위와 사전검증

권한: 사용자의 2026-10-20 17:00 KST까지 CPU+GPU 주도 실험 승인. 기존75M 목표나 학습 정책을 바꾸지 않는 별도 평가다. 새 학습·optimizer·체크포인트 저장0이다.

## 대안과 선택

| 안 | 내용 | 비용 추정 | 장단점 |
|---|---|---|---|
| A 선택 | 실제 TRAIN T0와 같은 상태 T2·TEST T0/T2의 TF/자유답 | GPU5~10분, 3모델 사이 유휴는 별도 | 최종 fitting/표면 전이와 평균손실의 한계를 좁히나 원인의 전부는 증명 못함 |
| B 후속 | 같은 교과의 content 가중치만 변경 | 구현·gradient 회귀와 별도384회 대조 필요 | 짧은 답 선택 개선을 시험하지만 아직 약한 fitting 원인이 미분리 |
| C 후속 | 같은 산수 자료의 난도 교과순서 대조 | 새 순서·동일 multiset 검증과 학습 필요 | 상태 일반화를 겨냥하지만 우선 암기/전이 구분 필요 |

A를 우선한다. 이는 현재 네팔을 고치거나 좋은 표본만 다시 고르는 작업이 아니다.

## 파일별 쓰기와 읽기

| 경로 | 동작 | 권한·제외 |
|---|---|---|
| scripts/diag_p106b_question_content_probe.py | 신설 | 독립 평가·선결·원형 검산만. 기존 source/model 파일 수정0 |
| scripts/test_p106b_question_content_probe.py | 신설 | CPU 모의 logits/decoder·가짜 source·분모·경로 회귀 |
| run_P106B_Stage4ev0W/evWa/evWb/evWc/evR 이름의 SH5개 | 구현 후 신설 | CPU→부모/고정뒤/변형균형→readback. 각 독립 종료, 입력 대기 없음 |
| 기존 P106B 계획·결과101·목록·기준표·방법론·COMPASS·WIP·experiments.tsv | 연쇄 갱신 | 새 지표·조건·원로그를 기존 역사 아래 누적 |
| data_cache/p106b_question_content_probe_v1_s1337/ | 새 배타 namespace | 새 문항/실답만, 기존 캐시 수정·삭제0 |
| test_result/evidence/p106b_question_content_probe_v1_s1337/ | 작은 공개 근거 | 자료 원문/가중치는 제외, 모든 파일20MB 미만 |

읽기는 기존 v2의 코드·닫힌 CPU/학습/실답 보고, 동결 coded2432와 관련 wire pass, 9716F40E tokenizer, 원부모·fixed_last·varied_balanced의 정확한 CP만 쓴다. 새 HF·외부 원천·TinyDataset·사전·native train.bin/val.bin 추가 열람은 하지 않는다.

upstream read_prepared는 옛 원천까지 다시 열므로 새 진단은 동결 v2 보고의 정확한 SHA·현재 코드·공개 CPU binding과 coded/wire projection을 직접 검증한다. 이 제한된 projection을 옛 전체 원천의 신규 감사로 부르지 않는다. 불일치면 GPU 전에 중단한다.

## 영향도

- 코드: 기존 render/encode_row/emit64·FP32 wrapper를 재사용하며 핵심 모델·학습·생성 함수는 불변이다.
- 데이터: 같은64 query의 KO/EN·T0/T2·CQ256표면/모델. lookup은2부모×4질문, JSON은4부모×2키로 완전 집합을 보존한다.
- 시험: 실제 encoded wire membership, shift/mask/owner, root/split, ties/rank/EOT, 손실 분모, 원형 재집계, 생성의 user-only 입력을 모의 회귀한다.
- 문서: §318의 fitting 미확인과 후행 후보를 연결하고 실제 생성/TF/proxy를 구분한다.
- 부채: 새 헤드/메모리/학습 목적은 추가하지 않는다. 목적이 다른 과거 TF/prefix 결과를 이 조건의 PASS로 재사용하지 않는다.
- 도메인: GPU는 순차·권한 내·모델 사이 유휴, 기존 CP/로그 불변, 비교는 같은 질문/생성 조건의 기술·내용 진단 범위다.

## 사전 고정 조건

태그 p106b_question_content_probe_v1_s1337는 check_run_registry의 태그 조회에서 미사용이다. 같은 명령에 함께 준 다른 조회 옵션은 태그 우선 반환 때문에 실행됐다고 주장하지 않는다. 학습량은0이며 pool≥2배·LR/WSD 비교는 해당 없음이다.

기존 평가 코호트에서 split별·가족별8 query를 결과와 무관한 ID hash로 고른다. lookup/JSON 부모는 통째로 고른다. 언어2×표현2×CQ 고정, parent/fixed_last/varied_balanced의3개 최종 가중치에서768실답을 새로 생성한다. TEST는 이미 모니터한 탐색 표본이며 blind benchmark가 아니다.

TRAIN T0-CQ의 전체 encoded x/y/segment와 prompt/target SHA를 실제 실행한 pass의 wire·닫힌 학습 보고와 대조한다. fixed_last는4회, varied_balanced는 rotation에 따라1회 노출이다. 최종 실패만으로 학습 중 한 번도 배우지 못했다고 단정하지 않는다.

## 측정과 판정

FP32-MATH/eval/no-grad에서 content/EOT NLL 합·분모·평균과 모든 target argmax를 따로 남긴다. 첫 gold token의 전어휘 순위/tie 구간·최강 nongold nonterminal과의 margin·EOT/EOS를 기록한다. prefix-only cache/last 경로와 full-TF predictor 차이도 기록하되 작은 수치 차이나 argmax 차이만으로 code bug를 확정하지 않는다.

자유 생성은 기존 emit64의 max64/greedy0/topk1/KV-on/MTP-off를 바꾸지 않고 user 질문만 넣는다. TF의 gold reference와 자유생성 입력은 분리한다. 모든 TF argmax가 맞는데 자유 token IDs가 다르면 경로/수치 검토 flag이지 즉시 버그 판정이 아니다.

JSON의 첫 token은 구문 시작일 수 있으므로 키·payload·전체 엄격 일치를 분리한다. D형 logit 대응은 기존 cohort 안의 적절한 single-content-token 쌍에만 후행 계산하며, 없으면 미적용이다. 비교 ID는 readout에만 쓰고 생성 후보로 넣지 않는다.

TRAIN T0→동일상태 T2만 표면의 대응 비교다. TRAIN→TEST는 상태/난도도 달라진다. 언어·표현 반복이나768답을768독립문제로 세지 않는다. 새 seed CI·일반 지능·Falcon 도달·75M 완료를 주장하지 않는다.

기술 정상 종료는 source/형태/본문/원형 검산의 성립이다. 모델 오답을 실행 오류로 바꾸지 않는다. 소형 CE 차이의 기존 nats 문턱이나 임의 정답률 문턱은 적용하지 않는다.

## 비용과 중단

실측1694답의 단순 외삽은 세 모델 자유생성 약206초다. TF/로딩 포함 GPU5~10분은 추정이며 속도 향상을 주장하지 않는다. CPU준비 상한300초, 각 모델 상한600초, 종합 검산600초를 계획한다. 실제 20일17시 권한 종료보다1시간 먼저 새 모델 작업을 멈추고 기록 시간을 남긴다. 각 namespace의 기존 완성/부분 파일 재사용·덮어쓰기는 거부한다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 추가로 고정한 읽기·해석 경계

실제 실행 연결은 정확한 train_fixed_last와 train_varied_balanced 두 폴더의 report.json·start.json·updates_shards_manifest.json·선언된384개 스칼라 update shard만 읽는다. 모두 기존 v2의 공개 근거이며 다른 태그나 디렉터리 재고를 열지 않는다.

첫 target index k=len(prompt_ids)-1, wire.x[:k+1]와 실제 생성 prefix, y/owner/EOT를 맞춘다. prefix 노출과 완전 x/y/owner 일치를 분리하고 동일 prefix의 다른 지도 target·masked 문맥 노출은 별도로 기록한다. T0의4/1 노출뿐 아니라 T2/TEST의 실제 prefix0도 확인해야 미노출 표면이라고 부른다.

첫 predictor 비교는 첫 단계만 설명한다. TF-perfect/free-different에는 terminal/길이를 포함한 첫 불일치 index와 그때까지의 일치 prefix를 기록하며 이후 단계의 기전은 별도 trace 전 미확인이다. rank1 tie와 실제 argmax 선택을 구분하고 global nongold/nonterminal/EOT/EOS margin을 따로 둔다.

Boolean 상수 baseline과 가족별 content/EOT 분모를 보존한다. T0/T2는 token 길이와 질문-답 거리도 달라지는 표면 변화이지 순수 의미 재표현 효과가 아니다.

prepare의 선결은 source mode로 원래 동결 입력을 확인한다. 아직 없는 새 corpus를 요구하는 preflight로 준비를 막지 않는다. eval/readback의 선결은 새 CPU 계약을 요구한다. check-only는 코드만 읽고 실제 자료·모델·자식을 실행하지 않는다.

ROOT의 메타데이터 조회에서 F708CE04… 보고 해시와 현재 info가 전부 같고 source map은60개였다. 옛 compact의53이라는 비공식 수를 복사하지 않는다. 이 조회는 wire membership이나 GPU 진단 완료가 아니다.

추가로 check_run_registry의 plan 조회를 별도 실행했다. 낮은 문자열 겹침의 과거 사전학습 후보만 반환했으며, 이 도구가 이번 동결 projection의 TF/실제 답 평가 중복을 직접 검증한 것은 아니다. 기존 결과의 TRAIN평가가 T2/T3인 점과 새 T0 포함 여부를 코드·원형으로 대조하는 것이 중복 판단의 직접 근거다.

회귀 검토에서 순위·argmax·경쟁 token 값의 자기모순, 완료 보고 뒤 출력/정리 오류, 부모를 공유한 질문의 독립성 과장이 발견되어 실제 실행 전에 수리한다. 저장된 scalar는 NLL·margin·분모·내부 정합성을 다시 계산할 수 있지만, 저장하지 않은 전어휘 logit으로부터 정확한 순위 수를 독립 재계산한 증거는 아니다. 해당 계산 함수는 합성 전체 어휘 벡터와 CPU tensor를 대응시켜 별도 검증한다.
