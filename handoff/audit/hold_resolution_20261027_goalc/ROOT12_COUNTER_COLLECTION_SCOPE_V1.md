# 교차 리뷰의 저장 행만 본문에 연결

기존 V5/V6 collector는 미검토를 포함한 전체 cohort의 원문/후보를 매 snapshot마다 열어 reading-view hash를 만든다. 새 교차 묶음은 3,688건이므로 작은 결과 회수마다 이를 반복하면 적체를 늘린다.

| 안 | 장점 | 한계 |
|---|---|---|
| 기존 전량 view 생성과 전량 0행 snapshot | 기존 schema 유지 | 저장되지 않은 수천 본문까지 반복 읽음 |
| 기존 파서/선택/본문 바인딩 재사용, 저장 행에만 view 생성, 미검토 ID는 명시 목록 | 선결과 원문 연결을 유지하며 불필요한 재독 감소 | 교차 snapshot schema를 명시해야 함 |
| 결과를 append-only event delta만 기록 | 최소 쓰기량 | 별도 replay와 precedence 소비기 필요 |

두 번째 안을 선택한다. 새 counter collector만 신설하고 기존 산출물은 보존한다. 위험한 본문 읽기 전에 V3 ID/SHA를 차단하며, 과제 일치·명시 TXT·partial-view 오복사 차단은 고정 함수를 그대로 재사용한다. 전체 대상은 manifest, 저장 행은 records, 미검토는 unreviewed_ids와 합계로 대조한다. source/body guard·의미·채택 판정은 약화하지 않는다.

사용자 goal의 CPU 코드/시험/파생 산출물 허용 범위다. 쓰기는 이 감사 폴더와 새 counter snapshot뿐이며 원문/기존 캐시/보호 데이터/타 세션/GPU/모델/Git 외부변경은 제외한다. 새 source TXT 읽기는 저장 리뷰 ID에만 발생하는지 Python observer로 검산한다. 해당 observer는 OS 권한 보장의 주장이 아니다. 기존 재사용 함수와 새로운 coverage·누락 분모를 검증하고 source 읽기 ID 목록을 기록한다.

중간 코드·상태는 WIP와 작은 감사 receipt가 소유한다. 아직 공식 기준표·METHODS의 데이터 채택 수치는 바꾸지 않는다. 새 캐시와 consumer가 통과하면 해당 별도 단계에서 동기화한다.
