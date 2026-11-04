"""Render the generator-owned final handoff from the exact owned ledger."""
import argparse
import hashlib
from pathlib import Path
import re

from scripts import wip

BASE=Path('handoff/audit/nov04_p107_cli')
TARGET=Path('handoff/202611042233_HANDOFF.md')
LEDGER=Path('handoff/WIP_20261022_작업원장.md')
PREVIOUS=Path('handoff/202611011123_HANDOFF.md')

BODY='''@@HEAD@@

- **이전**: [202611011123_HANDOFF.md](202611011123_HANDOFF.md).
- **코드가 정본**은 tinylm/이며 영구 규범은 [AGENTS.md](../AGENTS.md), Codex 장기기억은 ai_dev_tool/Codex/다.
- **AI 는 학습/GPU 코드를 직접 실행하지 않는다**는 기본 경계를 유지한다. 이번에는 사용자107이11월5일02:00 KST까지 CPU/GPU를 명시 허가한 연구만 총괄이 직접 수행했다. 다음 세션의 새 모델 실행 승인이 아니다.
- **이 문서는 요약하지 않는다**. 원로그/수치 정본은 연결 결과문서, 진행 상태는 [정확한 WIP](WIP_20261022_작업원장.md)가 소유한다. 전체 원장은 아직 열려 있다.
- **정적 감사 기록**: [선행 소유238입력 감사](audit/nov04_p107_cli/STATIC_AUDIT_v3.json), 마감 기록은 같은 디렉터리의 STATIC_AUDIT_v4.json이다. 소유6PASS/0ERROR/71NOT_RUN과 전역77PASS는 다르다.
- **결과 원로그 폐합**: [정확27로그 manifest](audit/nov04_p107_cli/RESULT_CLOSURE_v1.json), [두 스모크 원로그 별도 결속](audit/nov04_p107_cli/SMOKE_RESULT_BINDINGS_v1.json). 검사 전문은 이 문서에 복사하지 않는다.

## 0. 사용자 지시 (@@COUNT@@건) — 원문과 처리

| # | 사용자가 지시한 것 | AI 가 판단한 목적 | 그래서 필요했던 작업 | 실제로 한 것 | 결과 |
|---|---|---|---|---|---|
@@TABLE@@

현재107/107a가 이번 연구 범위다. 이전 지시는 기존 WIP의 원문·상태를 그대로 계승했다. 특히59의 기술 연결 일부를 진행했다고 실제 corpus/편향·전체 본학습까지 완료로 바꾸지 않았다. 다른 세션의 정제 원장·본문·캐시·프로세스는 이번 소유 범위가 아니다.

## 1. 가장 중요한 것 셋

1. **가중치는 실제로 바꿨지만 답변은 개선되지 않았다.** 완료 Q/F 모델의 방향 수리는 독립128문항에서12→12/5→5였고, 정답580위치로 만든 지도 보정도 새 독립256문항에서 다섯 팔 모두34정답이었다. 반복·질문 재출력은 남고 수리는 비채택이다.
2. **후속 원인 진단은 보정 신호 손실을 보여 줬다.** 기존 calibration만 분석했을 때 full ridge→rank16→선택 cap의 평균1차 신호는2.025→0.966→0.0138이었다. 같은 보정 질문4개에서 제한 없는 행렬은 두 답 token, 정답별 활성값 주입은 네 답 token을 바꿨지만 독립 일반화/지능 증거는 아니다.
3. **전체 스모크와 파일 재개 기술은 실제 확인했다.** 첫 인계 collector 실패를 보존하고 새 명시 scope로106동작/44자식0을 회수했다. 기존 trainer에 명시 파일·별도 기술CLI를 연결한 논리2/물리3갱신이 새 프로세스에서도 전체 상태 EXACT였다. 실제 corpus·75M streaming·추가300M은 열지 않았다.

## 2. 무엇을 했나

### 2.0 사용자용 판독 — 내부 경로를 몰라도 이해되는 설명

| 관측 | 의미 | 사용자 영향 | 다음 행동 |
|---|---|---|---|
| 방향 수리 후 독립 정답12/128·5/128이 그대로 | 반복 관련 방향을 제거하는 것만으로 정답 지식을 회복하지 못함 | 수정 모델을 더 좋은 모델로 채택하지 않음 | 같은 편집을 반복하기보다 새 학습/표현 목표의 근거부터 판단 |
| 정답을 사용한 국소 보정도34/256으로 동률 | 교사강제 손실 감소가 실제 자유 답변 개선을 보장하지 않음 | 단순 CE 개선을 지능 성과로 보고하지 않음 | full 학습과 독립 평가 조건을 별도로 준비 |
| rank/cap이 신호를 줄이고 정답별 oracle은 기존4질문에서만 효과 | 내부를 바꿀 여지는 있으나 입력별 정답을 아는 개입은 실용 답변기가 아님 | cap 확대/큰 rank를 바로 생산에 채택하지 않음 | 독립성·보호 기능을 보존할 다음 목표를 선택 |
| 새 파일 CLI의 별도 프로세스 재개가 전체 EXACT | 저장된 문서 추출·optimizer·정책·LR 상태가 연결 경로에서 보존됨 | 향후 실제 자료를 넣을 기술 선결 일부가 준비됨 | 정제 TRAIN 입장/편향/75M streaming 선결은 계속 분리 |
| 현재 전체 스모크106동작·44자식0 | 기본 학습 팔/필드 계약의 동작은 유지됨 | 이번 모델 수리 비채택과 도구 동작 성공을 구분 | 동일 팔을 무의미하게 다시 실행하지 않음 |

### 2.1 누가·언제·왜·무엇을·어디서·어떻게

총괄 Codex가2026-11-04의 사용자107 CPU/GPU 창에서 /home/uranus/tinyLM의 기존 완료 모델을 사용했다. 이번 목표는 작은 새 모델의 지능 성과를 발표하는 것이 아니라 직접 가중치 개입이 기존 실패를 고치는지 통제된 방식으로 판단하는 것이었다. 서브 에이전트는 새로 호출하지 않았다. 원본 CP는 읽기 전용이고 새로운 연구 tag/출력만 썼다.

첨부 제안과 두 공유 URL은 자료로 취급했다. 두 URL은 도구의 DisabledError로 본문을 받지 못했다. 사용자107a의 허가 뒤 정확한 로컬 모델 시각화·프루닝 도구 검토 채팅의 공개33메시지/assistant21만 선택했다. 첨부와 개행 정규화 일치1을 확인했다. 웹사이트 전체 장애로 단정하지 않았고 사적 추론/tool payload를 저장하지 않았다. [접근 영수증](audit/nov04_weight_space/REFERENCE_ACCESS_v1.json)이 범위를 소유한다.

### 2.2 P108의 방법과 실제 판정

[결과108](../test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md)과 [계획P108](../test_plan/P108_직접가중치-방향수리와-학습개입.md)이 정본이다. 첫 수리는 자연 반복의 같은 token 집합/마지막8token 고정 순서 대조에서 down 방향을 구하고 실제 잠재/계산 가중치를 바꿨다. Q의 잠재49152개 수정은 삼진 scale 때문에 계산1342049개를 바꿔 좁은 열만의 대조로 해석하지 않았다. 실제 지지집합/norm/특이값을 맞춘 행 부호3seed·반대 방향을 사용했다. Q의 정답12/128 대 수리12/128, 무작위11~13이었다. 실수 모델은 두 realization의 비영점 byte parity를 확인해 중복 팔을 생략했고5/128이 모든 팔에서 같았다. Q/F는 독립 학습 모델이어서 둘 간 차이를 순수 양자화 효과라고 주장하지 않는다.

두번째 방법은 마지막 down13에서 정답 대 경쟁 token의 gradient와 key를 수집해 ridge/SVD rank16 보정 인자를 구한 사후 지도 학습이다. 무지도 수리 또는 ROME/MEMIT 전체 재현으로 부르지 않았다. 새 calib128/dev128/test256을 분리했고 정답/EOT580위치·독립 유한차분4개를 확인했다. nominal 인자는180224B지만 실제 적용은 dense 계산 캐시이며 삼진 압축/배포 커널이 아니다. dev의 세 cap 정답20/19/19 중 동결한0.25%를 독립 test에 적용했으나 원본/보정/무작위3팔 모두34/256·교정0이었다. 보호 과제0/64, 일상 반복과 질문 echo가 남는다. 원문 답변도 총괄이 읽었다.

후속 calibration-only 진단은 기존580위치의 full/rank/cap 신호와 사전 고정한4문항만 확인했다. CPU 선형 예상에서 새 양수 margin은 선택 cap에서1위치였다. 실제4+13/1+15의 한영 네 질문은 원본/선택 cap에서 모두13/15 같은 틀린 첫 답 token을 골랐다. 상한 없는 rank16은 한국어 둘만17/16으로 바뀌었고 정답별 직접 활성값 oracle은 네 개를 바꿨다. EOT는 모든 조건4/4다. 다시 사용한 고유 지도 위치8과5조건의 실제 target 비교40을 나눠 기록했다. 자유 생성/독립 일반화 시험은 추가하지 않았다. [독립 진단 영수증](audit/nov04_weight_space/ATTENUATION_ROOT_READBACK_v1.json)이 실제 결과·원본 SHA·복원을 재검산했다.

선형 목표 방향이 전부 무의미했던 것은 아니지만 저랭크 공유/크기 제한·입력별 차이가 신호를 약화시켰다는 한정 해석이다. 더 큰 cap을 test로 다시 고르지 않았고 기존 음성을 유지했다. 이번 완료 모델은 untied MLP/R1에서도 실패했으므로 MLP 공유나 재귀만이 반복의 필요 원인이라는 설명은 맞지 않는다. 모든 원인이 해결됐다는 결론도 아니다.

### 2.3 원장59의 새 파일 입력/CLI와 새 프로세스 재개

[결과107§18](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md)은 기존 ExplicitDocumentSource/AdaptiveMNTPTrainer/HybridTrainingSession/boundary_store를 재사용한 연결을 기록한다. 합성4문서16388token ID/109885B JSONL만 사용했다. 기본 run100m/모델/optimizer는 바꾸지 않았고 새 CLI도 합성 기술 목적만 허용한다. 보호 경로는 stat 전 거부한다. 파일 SHA/입장 검사로 원문 의미/권리/정답성/문서 누설을 증명하지 않는다.

CPU20+10=고유30 뒤 현재 전체 smoke를 묶은 profile에서 실제 논리2갱신/262144입력을 실행하고 첫 경계781352215B를16MB 이하49조각으로 보존했다. 새 프로세스가 한 갱신을 replay해 전체 model/optimizer/policy/source/RNG/세션과 loss/target/LR가 EXACT였다. 물리3갱신/393216입력·run25.721747초/resume14.598884초이며 두 시간은 prefix/저장량이 달라 가속비가 아니다. peak reserved6100615168B·최종 소유 CUDA0/0, 원 CP·source·입력 불변이다. [독립 판독](audit/nov04_p107_cli/ROOT_READBACK_v1.json)과 [봉인 source/합성 입력](audit/nov04_p107_cli/SOURCE_ARCHIVE_v1.json)을 보존했다.

## 3. 무엇이 바뀌었나 — 코드·도구

P108 직접 편집/원복, 실제 지지집합 대조, 정답 margin 보정·원답 판독·calibration 감쇠/실제 oracle 진단은 scripts/p108_*.py와 diag/test_p108_*.py에 분리했다. 원본 model 구조/기본 trainer/생성기는 변경하지 않았다. 파일 입장은 tinylm/train/document_input.py, opt-in 연구 CLI는 scripts/train_p107_documents.py이며 기존 source/trainer/session/store를 호출한다. 실제 실행 profile·source 바이트·원로그·실패를 보존한다.

### 3.1 정본 동기화·미갱신 사유

| 산출물 | 필요 여부 | 실제 diff | 미갱신 사유 |
|---|---|---|---|
| 결과108/107 | 필요 | P108§1~14와 P107§18에 원로그/조건/정량/실패/명령 누적 | 없음 |
| 계획P108/P107 | 필요 | 새 단계 사전 계약·실제 종료·예측 대조·미완 경계 | 없음; 후속 조건부 연구가 남아 계획 전체를 -done으로 바꾸지 않음 |
| 실험계획목록/실험목록 | 필요 | 최신 결과·범위·날짜 | 없음 |
| EXPERIMENT_BASELINES | 필요 | 새 namespace 실행 전 예약과 최종 범위/음성/기술 결과 | 없음 |
| METHODS·methods03/05 | 필요 | 편집 비채택/감쇠 한계와 파일 재개 기술을 분리 | 없음 |
| COMPASS | 필요 | 새 두 결과/현재 smoke와 원장59의 기술 완료·실제 corpus 미완 | 없음 |
| experiments.tsv | 필요 | 398~421의 종료/취소/명령 보존 이력; 이번 활성 큐 없음 | 후속419~421은 늦은 역사 등록임을 명시 |
| Codex08 | 필요 | no-op/범위/연결/종료 작업공간·언어/도구 실패와 재발 방지 | 환경 훅/공용 검사기를 수정하지 않음 |
| scripts/flag_whitelist.tsv | 불필요 | 이번 소유 diff 없음 | 다른 세션 dirty를 보존함 |
| 원장/인계/정적·원로그 폐합 | 필요 | 공식 WIP API·이 단일 최종 인계·명시 감사 | 전체 WIP는 미완 항목이 있어 닫지 않음 |
| 루트09/보호 데이터/타 정제 | 불필요 | 변경0 | 현재 승인 대상이 아님 |

## 4. 조심할 것 — 다음 세션이 밟을 자리

02:00 KST 이후 새 모델/대규모 계산을 이 연구 권한으로 시작하지 않는다. 추가300M 금지와 다른 세션 정제 소유권은 계속된다. 과거 고정 평가/공식 benchmark를 편집 선택·새 교육에 넣지 않는다. 원 CP·원로그·생성 snapshot·기존 cache를 임의 삭제하지 않는다. runtime tensor와781MB 연구 snapshot은 Git에 넣지 않았다. 각 저장 결과 파일20MB 상한을 유지했다.

### 4.1 스모크·동적 검증 계승

| 항목 | 상태 | 근거 | 사용자 요청 반영 |
|---|---|---|---|
| run_smoke_check.sh 정본의 Codex 격리 등가 경로 | NOT_REQUIRED(이번 권한으로 같은106동작/44자식을 실제 완료했고 현재 모델/trainer core75파일이 불변임을 별도 대조함) | 결과108§12·두 smoke raw/report·SMOKE_RESULT_BINDINGS_v1 | §6b 실행 요청 없음; 기본 경로가 바뀌면 새 실행 필요 |

첫 전체 smoke는 인계 상속에 필요한 이전 문서의 scope 누락으로455.627초/종료1이었다. 알려진 경로 SHA를 확인한 뒤 이전 인계 한 개만 추가하고 독립 collector0을 먼저 받았다. 재실행400.554초/0, source/기존 합성 원형 불변·오류0이다. 공유 규칙/모델팔은 그대로다. 소유 정적6종에는 인계 의미 검사가 없어 첫 오류를 발견하지 못한 범위 차이를 설명했다.

Stage6bW는 계산/원복 뒤 일반 empty_cache가 cuBLAS 작업공간을 해제하지 않아 종료 검사1이었다. 소스·원로그를 보존한6cW에서 기존 close_owned_cuda를 재사용했다. 재실행은8519680B 작업공간을 실제 확인해0/0으로 끝났고 source/원 CP 최종 검사는 독립 실행했다. 첫 실패의 잔량값을 소급하지 않았다.

### 4.2 미해결 검사·판정

| 검사 | 정확한 대상 | 증거와 상태 | 운영 영향 | 권장 조치 | 대안 | 승인 주체 |
|---|---|---|---|---|---|---|
| 전역 정적 수집 | 보호 데이터/다른 세션이 포함될 수 있는 전체77종 | 명시 소유6PASS/0ERROR/71NOT_RUN | 전역 완료라고 할 수 없음 | 소유 경계가 닫힌 후 전역 검사의 권한/범위부터 확인 | 현재 소유 검사와 독립 인계/결과 검사 유지 | 사용자/해당 소유 세션 |
| frontier C2/C3 전수 | 전체 live-plan·승인 진행 제안서 | NOT_VERIFIED | 전체 원장을 닫을 수 없음 | 별도 전수 의미 감사 범위 확정 | 현재 상속1개 HOLD와 원장 미완 보존 | 사용자 |
| 실제 corpus/본학습 | P107 실제 정제 TRAIN과75M streaming | NOT_RUN | 합성 재개 성공을 학습 효율로 쓸 수 없음 | 정제 산출물 명시 입장·편향·전체 평가 선결 | 현재 합성 기술 계약만 사용 | 사용자/정제 총괄 |
| 가중치 수리의 일반화 | P108 독립 test/일상 | GATE_NEGATIVE·정답 증가0 | 새 수정 모델 비채택 | 다른 학습 목표/자료 준비 근거를 검토 | 원래 완료 모델 보존 | 사용자/연구 총괄 |

## 5. 확보한 수치

| 측정 | 실제 값 | 해석 범위 |
|---|---:|---|
| Q 방향 수리 독립 exact |12/128→12/128|현재 수리 비채택 |
| F 방향 수리 독립 exact |5/128→5/128|Q/F 사이 순수 양자화 인과 아님 |
| 지도 보정 독립 exact |34/256→34/256|다섯 팔 동률·교정0 |
| 지도 보정 반복 지표 |123/272→122/272|한 건 감소도 정답 복사 회복은 아님 |
| 기존580위치 평균 선형 신호 |2.025195→0.966241→0.013784|full/rank16/cap·실제 정답률 아님 |
| 고정4문항 body token |0/4·0/4·2/4·4/4|원본/선택/상한없음/정답 oracle·일반화 아님 |
| 새 국소 진단 실제 wall |3.072881초|whole worker·GPU busy 단독 계측 아님 |
| 새 국소 진단 allocated/reserved peak |773903872/796917760B|정리 후0/0 |
| P107 파일 CLI |논리2/물리3갱신·262144/393216입력|전체 재개 EXACT·언어 품질 아님 |
| 새 연구 snapshot |781352215B/49조각|원 CP 변경 아님·현재 보존 |
| 전체 smoke 재확인 |106동작/44자식·400.554086초·0|명시 collector 범위·전역 검사 아님 |
| 결과 원로그 연결 |27개·누락0/스모크별도2개|숫자/과학 판정은 root·실제 원JSON 추가 대조 |

정식 벤치마크는 이번 수리에서 새로 실행하지 않았다. 실제 일상16원답과 바뀐 규칙 답을 총괄이 읽었고 질문 반복·나열·오답이 남았다. 공식 점수/Falcon 수준 도달·일반 한국어/영어 대화 개선은 이번 성과로 주장하지 않는다. 기존 공식 점수는 기존 결과101§579 등이 소유하며 이번 수리 점수로 재사용하지 않는다.

## 6. 열린 질문

1. rank·보정 크기·단일 마지막층 목표를 어떻게 바꿔야 보호 기능과 독립 일반화를 함께 보존하는가. 현재 cap 확대는 채택하지 않았고 단순 재탐색을 권하지 않는다.
2. 실제 정제 corpus에서 P107 입장/언어·희귀 token 편향/75M streaming·전체 causal 평가가 성립하는가. 다른 세션 정제 완료를 자동 가정하지 않는다.
3. 기존8h 교사 생산과 KoBEST의 설치/공식 metric 선결은 이번 연구로 닫지 않았다. 지금 즉시 실행 또는 설치를 요청하지 않는다.

권장 방향은 먼저 정제 완료 근거와 본학습 자료 입장을 닫는 것, 그 뒤 실제 완료 모델의 독립 평가, 마지막으로 새 보정 목표의 별도 검토다. 새 작은 학습 성과를 일반 지능으로 평가하거나 이미 끝난 동일 수리를 반복하지 않는다.

## 7. 다음 권장 실험 순서 — 역사 예상8.0h·현재 READY0

| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |
|---:|---:|---|---|---:|---:|---|---|---|---|
|1|3|P106B 사용자8h 교사 증분생산|run_P106B_Stage4fsXW_user_supported_resume8h.sh|8.0|8.0|PRESENT|HOLD|원천/cursor·생산 계약 확인과 새8h 실행창|상속된 사용자용 경로다. 이번 남은02시 창보다 길고 원천 선결을 재검증하지 않아 자동 실행하지 않음|

**시간 미달 사유**: 이번 권한은11월5일02:00 KST까지이며8시간을 온전히 실행할 수 없다. 원천/cursor·생산 계약을 다른 세션 정제 완료로 가정하지 않는다. 기존 완료 진단은 실제 처리됐고 같게 다시 큐에 넣지 않는다. 전체 frontier 의미 감사는 수행하지 않았으므로 큰 큐가 준비됐다고 주장하지 않는다. 현재 즉시 사용자 실행 요청은0이다.

> FRONTIER_COVERAGE_NOT_VERIFIED — 전체 원장을 닫지 않으며 전용 정제 경로를 전역 스캔하지 않는다.
> FRONTIER_SEMANTIC_NOT_VERIFIED — 상속한 HOLD와 미완 과학 판단을 자동 완료 처리하지 않는다.

### 7.1 이전 큐 제외·완료 이관

| 이전 배치 | 처리 | 근거 |
|---|---|---|
|run_P106B_Stage4fsXW_user_supported_resume8h.sh|본표 HOLD 유지|직전 미완료 한 건을 무손실 계승; TSV id3·8h |
|P108 실제 수행16개 SH|명령 보존·-done·삭제|결과108§11·LAUNCHER_RETIREMENT_v1; 종료한 실패 시도도 보존 |
|P108 후속 실제3개 SH|명령 보존·-done·삭제|결과108§14·nov04_p107_cli/RETIREMENT_v1 |
|P107 Stage8bW/8cW SH|명령 보존·-done·삭제|결과107§18.6·같은 정확5개 정리 영수증 |
|P108 미실행3개 SH|대체되어 -cancel 보존|더 엄격한 v2/v3/지도 단계로 대체; 미실행을 완료로 세지 않음 |

연구 snapshot·기존 tensor packet·원로그는 삭제하지 않았다. 이번 실제 수행21SH의 정확 원문·모드·SHA와 복구 경로는 두 manifest가 소유한다. 이들은 사용자가 다시 실행해야 하는 잔여 큐가 아니다.

## 6b. 사용자에게 부탁하는 것

| 대상 | 정확한 위치 | 근거 | 사용자가 할 행동 | 완료 신호 | AI 후속 처리 |
|---|---|---|---|---|---|
| 실행 요청 없음 | 결과108§12·결과107§18 | 현재 전체 smoke와 실제 기술 재개는 수행 완료 | 이번에는 요청할 것이 없다. 같은 고정 profile을 다시 실행하지 않음 | 없음 | 새 코드/새 권한/새 자료가 생기면 필요한 실행만 재판정 |
| -done 삭제 요청 없음 | 결과108§11/14·결과107§18.6·두 정리 manifest | 이번 소유21SH는 명령/SHA 보존 후 이미 삭제됨 | 이번 소유 범위의 추가 삭제 가능한 -done 배치 없음. 다른 CP/원로그를 지우지 않음 | 소유 정리 영수증0 | 과거 다른 런처는 이번에 일괄 판정하지 않음 |
| 그 외 요청 없음 | 원장59·107/107a | 정제/설치·새 고유 자료의 사람 판독은 이번에 열지 않음 | 즉시 승인·설치·원문 검수를 요청하지 않음 | 없음 | 불명 의미만 필요한 경우 별도 쉬운 질문/답 원문으로 요청 |

## 8. 커밋 메시지

먼저 연구 핵심219경로/12969230B를 로컬424f922f525df1f5e8fcee8b47f56585658b26ee에 저장했다. 제목은 연구: P108 가중치 수리의 음성 결과와 검증 근거 보존이다. 정확 부모/전체 경로/모든 blob SHA·범위 미반영0/index0을 검산했다. [첫 저장 영수증](audit/nov04_weight_space/LOCAL_COMMIT_v1.json).

후속 기록/검증/소유 구현은 다음 한국어 제목/본문으로 표준 정확 경로 commit --only를 사용한다. 최종 commit hash와 실제 사후 검산은 최종 채팅 및 tmp/nov04_weight_space_final_commit_receipt.json이 소유한다. 같은 커밋 hash를 자기 파일 안에 넣기 위한 덮어쓰기/무의미한 추가 커밋을 하지 않는다. 타 세션 dirty/개인 설정·runtime·보호 자료는 staging하지 않고 push/PR0이다.

### 제목

```text
연구: 가중치 보정 신호 진단과 명시 입력 재개 검증
```

### 본문

```text
- P108의 기존 독립 음성을 보존하고 저랭크·크기 제한의 신호 손실과 실제 국소 개입을 분리 검증
- 기존 P107 source/trainer/session/store에 명시 파일 입장과 합성 기술 CLI를 연결하고 새 프로세스 전체 재개 일치 확인
- 첫 오류와 복구 원로그, 현재 전체 스모크 및 정확 원로그 연결·명령 보존·최종 인계를 저장
- 다른 세션 정제, 원본 체크포인트, 대용량 runtime과 외부 변경은 제외
```

## 9. compact 프롬프트 — 이번 세션이 압축될 때 남길 것

> M4·M5 E2E PASS 전까지의 **수동 보조**이며 자동 소비 계약이 아니다.

```text
정확 WIP는 handoff/WIP_20261022_작업원장.md이며 세션01a0b33b-d14e-7c40-ada8-229a1f97eabd 소유다.
이번107의 CPU/GPU 연구 권한은11월5일02시까지다. 다른 세션 정제/보호 데이터·추가300M·원CP 변경·다운로드/설치/push는 제외했다.
P108 실제 편집/원복은 성공했지만 Q/F 독립12→12/5→5·새 지도 보정 독립256 모든팔34로 수리 비채택이다.
기존580 calibration의 full/rank16/선택cap 평균 선형 신호2.025/0.966/0.0138. 고정4문항 body0/0/2/4는 oracle 한정이며 지능 성과가 아니다.
Stage6b 종료 정리 실패는 보존했고 기존 cuBLAS 정리를 재사용한6c 실제0·원CP불변·CUDA0/0이다.
파일 CLI는 합성4문서16388token만 썼고 논리2/물리3갱신·새프로세스 전체 EXACT다. 781352215B/49조각 snapshot은 보존한다.
현재 전체 smoke v1실패→v2 106동작/44자식0. 소유 정적6/0/71과 전역77PASS를 혼동하지 않는다.
원로그27폐합0·스모크2별도SHA. 실제 수행21SH는 원문/명령/SHA보존 후-done·삭제, 미실행3은-cancel로 남았다.
원장59 실제 corpus/편향/75M streaming·전체 지능효과는 미완이다. 전체 WIP와 frontier는 닫지 않는다.
중간커밋424f922f이며 최종 저장은 정확 소유 경로만 사용한다. 최종 영수증에서 HEAD/index와 미반영을 확인한다.
```

## 10. 세션 시작 프롬프트 — 다음 세션이 붙여넣는 것

- **열린 WIP 상태**: 있음.
- **정확한 WIP / 첫 미완료**: handoff/WIP_20261022_작업원장.md /1번.
- **첫 행동과 선결**: 현재 사용자 요청과 AGENTS/Codex README·00/06을 읽고 정확 세션 원장·이 인계를 확인한다. 1번의 정제는 다른 세션 소유이므로 tmp의 공개 조정 메모로 수신 상태만 확인하고 전용 본문/캐시/프로세스를 조사하거나 다시 정제하지 않는다. 59번은 명시 입장/실제 corpus 편향·streaming 선결만 남았고 합성 비용/재개를 반복하지 않는다.
- **승인 전 금지**: 마감 뒤 새 모델/대규모 계산, 추가300M, 타 정제/보호 데이터, 원 CP/원로그 삭제·덮어쓰기, 임의 설치/다운로드, push/PR. 현재 읽기·기록과 새 실행 권한을 구분한다.

```text
/home/uranus/tinyLM에서 이 인계와 세션ID가 같은 열린 WIP를 먼저 읽어라.
107/107a의 실제 결과·원로그 폐합·최종 커밋 영수증을 확인하고 완료한 가중치 수리/합성 재개를 다시 실행하지 말라.
원장1의 다른 세션 정제 소유권과59의 실제 corpus/75M 선결을 보존하며 사용자 현재 요청에서 가능한 다음 행동만 제시하라.
독립34/256·일상 반복을 숨기지 말고 작은 국소 oracle·스모크·정적을 지능 성과로 승격하지 말라.
```

## 11. 참조 치트시트

| 대상 | 정본 |
|---|---|
| 규범·메모리 | AGENTS.md·ai_dev_tool/Codex/README.md와00~08 |
| 현재 진행 | handoff/WIP_20261022_작업원장.md |
| 직접 수리와 신호 진단 | 결과108§1~14·P108 계획·두 사전 설계/감쇠 설계 |
| 파일 CLI·재개 | 결과107§18·P107 계획·nov04_p107_cli/PROFILE/ROOT_READBACK_v1 |
| 직접 원인 진단 검산 | nov04_weight_space/ATTENUATION_ROOT_READBACK_v1.json |
| 정확 원로그/스모크 | nov04_p107_cli/RESULT_CLOSURE_v1·SMOKE_RESULT_BINDINGS_v1 |
| 실행 source/명령 보존 | nov04_weight_space/SOURCE_ARCHIVE_v1~v3·LAUNCHER_ARCHIVE_v1, nov04_p107_cli/SOURCE_ARCHIVE_v1·COMPLETED_LAUNCHERS_v1 |
| 연구 경계 snapshot | runs/isolated/p107_document_cli_v1_20261104/boundary_u1/manifest.json·49조각, Git 제외 |
| 최종 로컬 저장 검산 | tmp/nov04_weight_space_final_commit_receipt.json, 실제 커밋 뒤 생성 |

루트09는 공유 정본이며 이번에 수정하지 않았다. 기존 문서·실패·원답은 보존하고 본문을 다른 세션으로 이관하지 않았다.
'''


def table_text():
    current=wip.parse_table(LEDGER.read_text(encoding='utf-8')).rows
    old={}
    body=PREVIOUS.read_text(encoding='utf-8').split('## 0.',1)[1].split('## 1.',1)[0]
    for line in body.splitlines():
        if not line.startswith('|'):continue
        cells=wip._markdown_cells(line)
        if len(cells)==6:
            key=cells[0].replace('*','').strip()
            if re.fullmatch(r'\d+[A-Za-z]?',key):old[key]=cells
    rendered=[]
    for _,number,cells in current:
        if number=='107':
            purpose='직접 수리의 효과를 완료 원형·독립 대조로 판단하고 남은 기술 선결을 진행'
            need='자료/일차 근거 대조·행렬 실제 편집/원복·지도 보정·원인 진단·파일 CLI·기록/검증'
        elif number=='107a':
            purpose='공유 링크가 불가하면 허가된 정확 로컬 공개 채팅만 확인'
            need='열람 상태 분리·공개 메시지/첨부 대조·범위/SHA 영수증'
        else:
            previous=old.get(number)
            purpose=previous[2] if previous else '원지시별 실제 처리·미완·재개 근거 보존'
            need=previous[3] if previous else '현재 소유 산출물과 실제 증거를 대조'
        row=[number,cells[1],purpose,need,cells[3],cells[2]+' — '+cells[4]]
        if any(chr(10) in value or '<br>' in value for value in row):
            raise ValueError('directive table must keep one physical line per row')
        rendered.append('| '+' | '.join(row)+' |')
    return len(current),chr(10).join(rendered)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','refresh_table'))
    args=parser.parse_args()
    before=TARGET.read_text(encoding='utf-8')
    count,table=table_text()
    if args.mode=='prepare':
        if '사용자 지시 (N건)' not in before:raise ValueError('only the new generator skeleton can be filled')
        after=BODY.replace('@@HEAD@@',before.splitlines()[0]).replace('@@COUNT@@',str(count)).replace('@@TABLE@@',table)
    else:
        pattern=r'(## 0\. 사용자 지시 \()\d+(건\) — 원문과 처리\n\n\| # \|[^\n]*\n\|---\|[^\n]*\n)(.*?)(\n\n현재107/107a)'
        after,n=re.subn(pattern,lambda m:m[1]+str(count)+m[2]+table+m[4],before,count=1,flags=re.S)
        if n!=1:raise ValueError('exact final directive table required')
    if after==before:raise ValueError('no new handoff patch needed')
    patch='*** Begin Patch'+chr(10)+'*** Update File: /home/uranus/tinyLM/'+str(TARGET)+chr(10)+'@@'+chr(10)
    patch+=''.join('-'+line+chr(10) for line in before.splitlines())
    patch+=''.join('+'+line+chr(10) for line in after.splitlines())+'*** End Patch'+chr(10)
    output=BASE/('FINAL_HANDOFF_v1.patch' if args.mode=='prepare' else 'FINAL_HANDOFF_TABLE_v2.patch')
    with output.open('x',encoding='utf-8') as stream:stream.write(patch)
    print('PATCH',str(output),'rows',count,'bytes',len(after.encode('utf-8')),
          'source_sha256',hashlib.sha256(LEDGER.read_bytes()).hexdigest().upper())


if __name__=='__main__':main()
