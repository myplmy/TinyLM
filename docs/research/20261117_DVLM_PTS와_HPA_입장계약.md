# DVLM PTS·HPA 입장과 실제 교사 대조

사용자158의2026-11-17 17시 CPU/GPU 승인으로 원장63의 미구현 범위를 진행한다. 현재 CPU1 속도 측정이 끝날 때까지 새 CPU/GPU 수치 실행은 하지 않고 설계·소스 작성만 진행한다.

## 원문 확인과 이번 해석

[DVLM §3.1·부록 A.2–A.3](https://arxiv.org/html/2609.33816v1)을 웹에서 직접 열었다.2026-11-13의 전문 열람 실패 기록은 당시 증거로 보존한다. 원문은 정렬 그룹, 같은 그룹의 앞선 확장 토큰, 원 prefix와 논리 위치, 단독 디코딩이 안 되는 표본의 제외를 명시한다. 학생 어휘 head의 초기화와 다음 학생 토큰 지도는 식5~6을 참조한다. 아래 구체 입장·거부·테스트 정책은 TinyLM의 구현 선택이다. 저자 코드 재현으로 부르지 않는다.

## 세 대안

| 안 | 내용 | 이득 | 제약·비용 |
|---|---|---|---|
| A, 선택 | 순수 PTS/HPA 계약 뒤 기존 Qwen0.6의 그룹별 직렬 교사와 실제 hidden 대조 | 순수 attention 자산을 재사용하고 입력 누설·위치 오류를 분리 | 새 순수 helper/진입기와 CPU/GPU 수치 게이트; 약30~60분 준비 |
| B | 기존 Qwen3.5 hybrid의 모든 state를 동시에 분기 | 기존 교사를 계속 사용 | conv/recurrent/KV까지 소유·원복·가시성 검증이 필요; 이번 첫 게이트로 더 비쌈 |
| C | 현재 exact-token DSKDv2를 유지 | 새 입력 경로 없음 | PTS·HPA·학생 어휘 head의 미완을 답하지 못함 |

A를 선택한다. 기존 완료 primitive/DSKD/공식 평가를 반복하지 않는다. 새 경로의 hidden 정합과 head 초기화는 기술 증거이며 새 본학습·정답성·방법 채택은 별도다.

## 파일별 권한과 영향

| 경로 | 동작 | 승인 근거 | 제외 |
|---|---|---|---|
| scripts/p106b_dvlm_pts.py, scripts/test_p106b_dvlm_pts.py | 새 순수 정렬·PTS·위치·가시성·shift 계약 | 사용자158의 미완63 구현 | CPU1 동결 소스/제품 코드 변경0 |
| scripts/diag_p106b_dvlm_pts.py 및 후속 native 진입기 | 별도 현재 시계·정확 입력·실제 교사 대조 | 같은 CPU/GPU 주도실험 | 검사 전 실제 실행/설치0 |
| test_result/evidence/p106b_dvlm_pts_v1_20261117/** | 새 profile·사전 예측·보고서 | 연구 기록 | 기존 자료/로그 불변 |
| P106B 계획/결과101·두 목록·방법론·기준표·COMPASS·원장63/158·registry | 필요한 문서 연쇄 | 같은 수행·보고 | 루트09·과거 감사·다른 WIP 변경0 |
| 기존 Qwen0.6 정확 자산/토크나이저·기존 TRAIN128의 소유 frozen export | 입장 후 정확 파일만 읽기 | 기존63의 교사/학생 입력 계약 | corpus 편입·평가정답 학습·다른 정제·보호 데이터0 |

| 영향 축 | 판정과 조치 |
|---|---|
| 코드/caller/중복 | 새 helper만 사용. 현재 scripts/tinylm에 PTS/HPA 구현은 없고 기존 hybrid primitive와 native hidden 관찰자는 재사용 가능한 별도 부품이다. 기존 함수 시그니처/기본값은 불변 |
| 데이터 | 기존 파일은 불변. 완전 동일 텍스트/개별 학생 token의 무손실 변환이 안 되면 표본 전체 HOLD 사유를 기록. CE를 조용히 줄이거나 원천을 새 TRAIN으로 승인하지 않음 |
| 테스트 | 서로 다른 토큰 경계·그룹 내 이전 확장·그룹 간 차단·논리 위치·다음 target/owner·깨진 UTF-8/비단조 디코더·부분 원천·수치/원복을 검사 |
| 문서 | 계획→실제 JSON/원로그→결과101→목록/기준표/방법론/COMPASS로 연결 |
| 부채/우선 | hybrid를 우회해 성공했다고 하지 않음. 순수 attention에서 먼저 PTS 계약을 검증하고 hybrid는 별도 유지. 본학습 자료/권리는 여전히 입장 선결 |
| GPU 권한/소유 | 이번158의17시까지, CPU1 측정 후 단일GPU 직렬. 원CP·라이브러리·다른 정제·Git·삭제0 |
| 비교/지표 | 같은 교사·token ID·논리 위치·FP32/MATH와원허용차의 PTS 대 그룹 직렬 대조. 다른 모델의 품질 점수와 합치지 않음 |

## 구현 정책과 사전 판정

정렬은 양쪽의 누적 무손실 byte 끝점이 처음 같은 곳에서 닫는다. 비단조 prefix decode·단독 UTF-8 불완전·빈 token·전체 본문 불일치·끝의 불일치 residual은 명시 HOLD로 거부한다. residual을 자동 수락하는 구현은 이번 정책이 아니다. 원래 CE와 거부 분모는 남긴다.

ByteLevel이 명시된 native 토크나이저는 기존 검산된 raw-byte helper로 전체 문자열을 대조한다. 교사 token 하나가 다중 byte 문자를 나눠도 전체 bytes를 보존하며 학생 token의 독립 디코딩/재토큰화는 별도로 검사한다. 이는 손실 있는 문자열 suffix를 그대로 자르는 동작과 구분하는 TinyLM 정책이다. `build_layout`은 이미 검증한 배열의 순수 배치 함수이고 실제 입장 caller는 `prepare_layout`의 전체/단독 디코딩과 재토큰화 검사를 반드시 거친다.

원 teacher row는 원 causal prefix만 본다. 학생 확장 row는 이전 정렬 그룹의 원 teacher prefix, 같은 그룹의 앞선 학생 확장, 자기 확장의 현재까지를 본다. 물리 concatenate offset을 RoPE 위치로 쓰지 않는다. head 위치는 각 학생 확장의 마지막이고 지도는 다음 학생 token이다. 마지막 위치와 비감독 owner는 ignore한다.

순수 계약 통과 후 PTS 전체 teacher hidden을 정렬 그룹마다 별도로 계산한 원 prefix+해당 private 그룹과 대응한다. 원교사 prefix와 private suffix의 값, future/타그룹 변경 불변·같은그룹 앞선 private 변경 민감성을 관찰한다. 원교사 자산·표준 inference와 state는 변경하지 않는다. FP32/MATH의 원 native atol1e-5/rtol1e-4를 사용하고 미달은 그대로 남긴다.

새 학생 어휘 head는 초기화/지도 위치를 먼저 검산한다. 충분한 정식 TRAIN/dev/test와 전체 head 학습·OPD 전에는 그 초기화나 합성 업데이트를 품질 성과로 판정하지 않는다. 현재 단계는 모델 점수/새head 학습/전체DVLM 미실행이다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
