# 전체 field 대기열의 정확 역할 배정

사용자는 전체 잔여 정제와 최대5 Luna를 승인했다. 기존5역할을 유지하고 미리 생성된 field12~36의 각 역할 지정 ID·manifest·TASK·출력 폴더를 한 번에 결합한다. 이미 끝낸 페이지는 재시작하지 않고 현재 PROGRESS 다음부터 계속한다. C/L은 자기 root12 독립대조 배정을 모두 마친 뒤 field12부터 이어간다.

| 안 | 장점 | 단점/비용 |
|---|---|---|
| 매100여 ID 페이지마다 새 scope | 범위가 작음 | 빈번한 총괄 왕복과 별칭/문서 버전 누적 |
| field12~36 전체의 역할별 정확 명세를 고정 | 같은5역할의 대기 감소·원문/후보 추가 복사0 | manifest와 TASK metadata를 한 번 전량 검산 |
| 저장소 전체 자유 검색 위임 | 총괄 대기 감소 | 타역할/보호경로 경계 약화. 수행하지 않음 |

두번째안을 수행한다. 원문 처리량 한도나 완료 판정을 바꾸지 않고 정해진 다음 배정을 미리 고정한다.

| 파일·경로 | 동작 | 승인·보호 경계 |
|---|---|---|
| 본 audit의 prepare_remaining_field_bindings_v1.py·새 binding/scope/manifest V6 | 신설·metadata 검증 | goal1·5·6과 현재 전체정제 승인. 원형/후보 읽기·해시0 |
| data_cache/.../remaining_field_title_readers_v1/complete.json·각 page manifest 및 역할 TASK MD | 읽기·metadata SHA 검산 | 해당 전체 대상의 정확 입력. 보호 TinyDataset/타세션 제외 |
| tmp/hold-*-field-lossless-v6 및 C/L counter V6 | 새 고정별칭 생성 | 기존 entry4/core3/guard5·동일역할 검증 유지. payload 사본0 |
| 각 data_cache/.../agents/ROLE/COHORT | Luna의 새 TXT/MD·진행 기록만 | 기존원형/후보/저장본문 덮기·삭제/코드·시험·GPU·모델·Git 금지 |

| 축 | 영향 |
|---|---|
| 코드 | 새 판독 알고리즘 없음. 기존 고정 별칭을 현재 역할·새 고정scope로 생성. |
| 데이터 | 기존 manifest/원형/후보/정제본 그대로. 정확 ID·TASK 경로와 SHA만 연결. |
| 검증 | 모든 manifest/역할 ID 수/중복/TASK 핀, 정상7개 별칭·잘못된 역할/범위·제한자료 거절. 27회귀의 core/entry/guard 바이트 유지. |
| 정본 | 새 binding과 진행WIP만 갱신. 전체 처리/최종재계측 전 METHODS·기준표 종결은 아님. |
| 부채·비용 | 페이지별 별칭 버전 양산을 줄임. 이후 새 제한 발견은 별도 guard 선결 유지. |
| GPU·소유권 | CPU metadata/지정텍스트만. 원형·캐시·타세션·보호데이터 불변. |
| 비교·증거 | 같은입력·역할·토크나이저, scope 검증은 내용판정이나 학습품질이 아님. |
| 문서연쇄 | 실제 페이지 저장 ID 수와 처리상태를 계속 재계수. 목표 A–E 미완료 유지. |
