# 필드 역할의 경로·출력 분할 재사용

상태: 구현 착수 전 영향도. 사용자 전체 정제 재개와 objective의 CPU 도구 구현·시험·별도 파생자료 허가 안에서 수행한다.

| 경로 | 동작 | 권한 | 제외 |
|---|---|---|---|
| 현재 감사 폴더의 field_scoped_packet_entry_v1.py/준비기/시험/JSON registry | 신설·CPU 실행 | 관련 도구 구현·시험 | 기존helper·원문·후보·캐시 수정 없음 |
| tmp/hold-h-field-v1, hold-j-field-v1, hold-g-field-v1 | 새 역할별 진입점 | 지정 원문 판독 지원 | 기존파일 덮기 없음 |
| 각 역할 agents 루트의 ROOT_FIELD_SHORT_READER_ENTRY_V1.md | 새 위임 안내 | 이미 허가된 field36페이지 자기명단 | 타역할·타세션·보호원문 없음 |

## 선택과 이유

| 안 | 이점 | 한계/비용 |
|---|---|---|
| A. 긴literal 경로를 계속 복사 | 새 코드 없음 | 실제0채움폭·부모폴더오류·출력잘림이 반복됨 |
| B. 기존scoped_packet_reader_v1에 역할/페이지별 봉인목록 연결 | 2000자 분할·SHA·범위/순서검사를 재사용 | 새metadata registry와 작은진입점 필요 |
| C. birth전달guard 전체를 field로 다시 설계 | 시간기록까지 통합 가능 | 스키마/과거증거/이행범위가 크게 달라짐 |

수행: B. 실제 확인한 기존helper SHA `DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6`를 고정한다. registry는 기존manifest의 reading_parts만 재사용하고 본문을 열거나 재추출하지 않는다. restricted ID 및 original SHA를 metadata로 먼저 검사하고, 런타임도 두 경계를 통과해야 helper를 호출한다. 이미 판독한 입력을 다시 읽거나 과거전달증거를 새로 만들지 않는다. 이 경로에는 birth식 시간journal을 추가하지 않는다.

## F4 영향도

- 코드: 기존helper, controls field v1 호출부와 birth v2 호출부를 직접 읽었다. 기존helper는본문2000자분할/packetSHA/단일registryID범위를 소유한다. 새진입점은 metadata의 역할·페이지·보호ID/SHA를 먼저 검사하고 기존함수를 그대로 호출한다. 기존실행파일은 수정하지 않는다.
- 데이터: 기존field36 manifest의 세역할 자기명단/패킷핀만 새registry로 연결한다. 원문/후보/기존TASK·identity계획·저장리뷰는불변이다. 보호metadata는 본문없이 별도제외목록에 기록하며 숨기지 않는다.
- 시험: 합성registry의 올바른범위, 타역할/미배정ID/페이지, ID보호/SHA보호의 helper호출전거부, registry변조, packet순서·조각경계 회귀를 확인한다. 실제호출은root의도구검증일뿐전량판독으로 세지 않는다.
- 정본: 캐시·학습조건·기준표/METHODS 수치는 바뀌지 않는다. 새도구의근거/안내/WIP만 갱신한다. 완료A–E는여전히미충족이다.
- 부채/우선순위: 새문서추출기나의미판정기를만들지않는다. 알려진경로오류와출력잘림을줄이고필드본문정제는Luna가계속한다.
- 도메인: GPU/모델/학습·설치/다운로드없음. 보호ID/SHA를본문보다먼저검사한다. 타세션전용경로접근없음. 출력성공/정적회귀와이해·의미승인·품질을혼동하지않는다. 이진입점은OS격리/실행자신원인증을제공하지않는다.
