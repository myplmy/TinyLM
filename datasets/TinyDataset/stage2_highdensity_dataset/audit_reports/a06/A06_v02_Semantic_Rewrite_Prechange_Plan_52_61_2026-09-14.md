# A06 v02 의미 재서술 사전 변경 계획 — 52~61행 (2026-09-14)

- source v02 SHA-256: `C3736DB745456D9C0CAB1FBFB05C7C19D8C041771996F865E81617517F012516`
- registry SHA-256: `4E1982D98D2ACA7EBE751025E6F448D17C9EE9FD7E533EEA52FC2E08432D6033`
- source concept·text와 같은 locator의 registry primary만 변경하며 relations, other_type, registry 비-primary field는 보존한다.

| locator | 새 concept | 관계 | 의미 근거 |
|---|---|---|---|
| v02:52 | 건조 경보와 환기 명령을 함께 승인하는 기준 | process, state, contrast | 건조 신호·창 상태·승인 순서 |
| v02:53 | 베드 수분 부족 때 관수 밸브를 보류하는 기준 | boundary, role, attribute | 수분값·수압·운영자 판단 |
| v02:54 | 기상 예보와 팬 속도를 양액 수위와 함께 판단하는 기준 | boundary, comparison, state | 외기 예보·팬 속도·탱크 수위 비교 |
| v02:55 | 차광막 위치와 환기창 명령의 확인 순서 | process, boundary, role | 위치 신호·명령·작업자의 복구 순서 |
| v02:56 | 한랭 예보 중 건조 센서 경보를 해석하는 기준 | state, contrast, comparison | 예보 온도·센서값·관수 판단 |
| v02:57 | 야간 관수 점검과 베드 관찰의 분리 기준 | classification, boundary, function | 점검·관찰·제어 기능의 분리 |
| v02:58 | 습도 제어와 건조 경보가 엇갈릴 때의 비상 확인 | process, state, contrast | 습도 상태·건조 경보·재확인 |
| v02:59 | 교대 인계 때 압력계와 배수 유량을 대조하는 기준 | boundary, role, attribute | 인계자·압력값·유량값 |
| v02:60 | 환기창 상태와 양액 수위 지시가 다를 때의 우선순위 | boundary, comparison, state | 창 상태·수위·전력 상태 비교 |
| v02:61 | 팬 정비 중 배수 작업을 보류하는 절차 | process, boundary, role | 정비 구역·배수 작업·안전 순서 |

candidate와 backup 및 post-audit만 A06 전용 경로에 작성한다. v01과 package, 다른 영역, 공용 파일은 제외한다.
