# 2026-11-12 잔여 HOLD 원문 작업 재개 위임

사용자의 현재 전체 정제 재개 지시와 목표 §5를 근거로 `gpt-6-luna`, `max` 추론의
원문 작업 역할을 최대5개 사용한다. 재개 확인 시 살아 있는 보조는0개였고, 예전 사용량 제한으로
끝난 실행을 현재 진행 중으로 세지 않는다. 총괄은 규칙·검증·채택·코드·Git을 담당한다.

| 역할 | 현재 페이지/미완 TASK | 고정 입력 안내 | 정확 쓰기 소유 경로 |
|---|---|---|---|
| context_controls C | 12 /014,259740은19/37까지 읽은 미완 | REMAINING_FIELD_ROLE_C_V1.md | data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/remaining_field_title_page_PPP_counter_v1/ |
| context_latin L | 12 /010 및250303 미완 보완 | REMAINING_FIELD_ROLE_L_V1.md | data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_latin/remaining_field_title_page_PPP_counter_v1/ |
| context_hangul H | 16 /010 미완 | REMAINING_FIELD_ROLE_H_V1.md | data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/remaining_field_title_page_PPP_counter_v1/ |
| historical_review J | 15 /010 미완 | REMAINING_FIELD_ROLE_J_V1.md | data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/historical_review/remaining_field_title_page_PPP_counter_v1/ |
| legacy_review G | 14 /011의325259 미완, 앞4행 저장 확인 | REMAINING_FIELD_ROLE_G_V1.md | data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/legacy_review/remaining_field_title_page_PPP_counter_v1/ |

안내와 이 명세는 `/home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/`에 있다.
PPP는 각 역할이 기존 V6 binding에서 소유한 페이지의3자리 표기다. 자신의 START_HERE,
TASK, 기존 PROGRESS와 저장된 TXT/MD만 읽고 이어간다. 현재 페이지 뒤에는 자기 field36까지
정확 배정을 계속한다. 이미 마친 페이지를 전량 다시 시작하지 않는다.
C/L은 root12의 미완 커서를 보존하고 field 최초 검토를 우선한다. 기존 안내의 root12 우선 문구는
이 최신 총괄 지시로 대체한다. 역할 간 자료·보호 TinyDataset·타세션 경로는 읽거나 검색하지 않는다.

원문·후보 읽기 실행은 정확히 `bash /home/uranus/tinyLM/tmp/hold-X-field-lossless-v6 PAGE ID pair PART`
별칭만 허용한다. X는 각각 c/l/h/j/g다. 고정 entry4/core3/guard5 및
`LOSSLESS_REVIEW_READER_SCOPE_V6.json` SHA68D97F85C6DB1F76A284B12A65663633D39B44F07CA502E6EA1C8844B9F5CC46,
`RESUME_REMAINING_FIELD_ROLE_BINDINGS_V2.json` SHA777492CCC99246535356136F15B49BEC2368CB61061F152BD24162978F61BF18를
그대로 사용한다. guard 거절을 raw·packet·추가 해시·다른 런처로 우회하지 않는다.

허용 쓰기는 자기 소유 경로의 새 TXT/MD와 기존 PROGRESS 갱신뿐이다. 기존 원문/후보/정제본문/리뷰는
덮거나 삭제하지 않으며 본문·판정·SHA·경로가 바뀌면 새 버전으로 남긴다. 단순 끝줄바꿈만으로
새 버전을 만들지 않는다. 정상 원문/후보를 그대로 선택할 때는 기존 경로를 쓰고 사본을 만들지 않는다.
sidecar는 원문 절대경로·SHA·확인 구간/앵커를 참조하고 원문 전체를 복사하지 않는다.
자기 새 출력의 정확 경로에 대한 존재 확인은 덮어쓰기 방지용으로 허용한다.

코드·시험·설정·작업규약·WIP·모델·GPU·학습·Git·삭제·설치·웹 취득·전처리 스크립트 실행은 금지한다.
정제 본문의 전문/원문 전체 diff/EOF 확인은 자기 허용 텍스트에만 한다. 끝 UTF8 바이트를 잘라내지 않는다.
판독 중인 문서의 모든 part가 실제로 노출돼야 EOF 완료라고 한다. 생략 출력과 잘린 출력은 판독으로 세지 않는다.

일반 철도 안전·운영·약품·코드·보안 교육이라는 주제만으로 임의 새 제한을 만들지 않는다.
부정·조건·날짜·단위·외국어 이름·코드·차 있는 참고문헌과 정상 반복을 보존한다.
제목/선행 문장으로 주어가 이어지는 문장을 자동 삭제하지 않는다. 근거 없는 사실을 채우지 않는다.
명시된 제한 또는 실제 불명 구간은 정확히 보고하고 독립 작업을 계속한다.

완료 보고는 마지막 실제 EOF ID·part, 저장한 리뷰/본문 경로, 변경 이유와 미완 커서다.
기존 진행량을 새 수행량으로 재계상하지 않는다. 오류나 사용량 제한이면 마지막 저장·미완 커서를
보고하고 자동 재시도나 코드 수리를 하지 않는다. 한 TASK 종료를 전체 목표 완료로 표현하지 않는다.
