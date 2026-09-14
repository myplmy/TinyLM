# A06 v02 의미 재서술 사전 변경 계획 — 32~41행 (2026-09-14)

- source v02 SHA-256: `90A99CC73B3673D5182A3F0F44BEFDC98B9B53D932C6BBA903487F2002754553`
- registry SHA-256: `8C5650721A9E9A8F14E5414D99299BE7CDA461D5D195BB9A614C0BE0D46EB8BE`
- 같은 locator의 source concept·text와 registry primary만 갱신하며, relations와 other_type은 보존한다.

| locator | 새 concept | 관계 | 의미 근거 |
|---|---|---|---|
| v02:32 | 한랭 예보 중 순환팬 저속 운전 기준 | state, contrast, comparison | 외기 예보·상층 온도·팬 속도 비교 |
| v02:33 | 관수 밸브 통신 장애의 재시도 기준 | classification, boundary, function | 밸브 위치 응답과 통신 실패의 구분 |
| v02:34 | 원격 표본에서 센서 값과 제어 명령을 구분하는 방법 | process, state, contrast, other | 표본 한계·명령·창 위치의 별도 확인 |
| v02:35 | 교대 인계 때 배수 유량과 압력 경보를 확인하는 순서 | boundary, role, attribute | 유량값·압력값·인계자의 역할 |
| v02:36 | 환기와 양액 보충이 겹칠 때의 기상 대응 | boundary, comparison, state | 외기 예보·수위·창 개방의 우선 비교 |
| v02:37 | 정비 뒤 순환팬을 다시 켜는 절차 | process, boundary, role | 정비 완료·안전 점검·팬 기동 제한 |
| v02:38 | 양액 보충과 환기창 개방이 겹칠 때의 초기 대응 | state, contrast, comparison | 수위·실내 온도·창 개방의 우선 비교 |
| v02:39 | 베드 수분 기록과 배수 압력 경보의 구분 | classification, boundary, function | 토양 수분·배수 압력의 원인 분리 |
| v02:40 | 함수율 경보와 환기 제어의 예외 기간 판단 | process, state, contrast | 경보 지속시간·환기 상태의 재판정 |
| v02:41 | 베드 관수와 차광막 구동이 겹칠 때의 보류 | boundary, role, attribute | 수분값·차광막 위치·담당자 판단 |

candidate·apply backup·post-audit는 A06 전용 경로에만 기록한다. v01 package, 다른 영역, 공용 파일은 변경하지 않는다.
