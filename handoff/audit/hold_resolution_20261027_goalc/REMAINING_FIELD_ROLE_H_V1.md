# context_hangul 잔여 field의 정확 연속 배정

현재 field15의 자기 PROGRESS 다음 미완료 ID부터 계속한다. 해당 역할의 실제 배정 수량을 다 저장하고 완료 수/마지막 ID를 보고한 뒤 field16 TASK_001로 넘어간다. 이후 자기 역할 field36까지 순서대로 계속한다. 이미 끝낸 이전 페이지를 재시작하지 않으며 다른 역할의 페이지 완료를 기다리지 않는다.

현재 ID는 V5 EOF까지 마치고 다음 ID부터 V6 별칭을 쓴다. entry4/core3/guard5 바이트와 전량 판독 형식은 같다. 이미 완독한 ID를 전환 때문에 재독하지 않는다.

field 판독: `bash /home/uranus/tinyLM/tmp/hold-h-field-lossless-v6 PAGE SOURCE_ID pair PART`. PAGE는 아래 표의 정수다.

각 PAGE의 입력 manifest는 `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_PPP_counter_v1/manifest.json`이다. PPP는 PAGE의 3자리 표기다. 자기 역할에 배정된 ID만 읽는다.

각 PAGE의 입력 TASK와 출력은 `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/remaining_field_title_page_PPP_counter_v1/`이다. `TASK_001.md`부터 실제 표의 TASK 수까지이며 각 TASK의 지정 ID·원형·후보 경로가 정본이다. 새 TXT/MD와 PROGRESS만 쓰고 기존 원형·후보·저장 본문을 덮거나 삭제하지 않는다. 코드·시험·모델·GPU·학습·Git은 맡지 않는다.

정확 배정은 [binding](/home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/RESUME_REMAINING_FIELD_ROLE_BINDINGS_V2.json)의 SHA 777492CCC99246535356136F15B49BEC2368CB61061F152BD24162978F61BF18로 고정됐다. 해당 큰 JSON 전체를 출력할 필요 없이 이 작은 안내와 자기 TASK를 읽으면 된다. 총괄은 125배정/12605고유ID/2577 TASK 핀, 정상 별칭7건·거절5건을 metadata로 검산했다. guard5의 거절은 원형/후보/packet 재열람·추가 해시로 우회하지 말고 NEEDS_ROOT로 보고한다.

| PAGE | 자기 ID 수 | TASK 수 | TASK_001 첫 ID |
|---:|---:|---:|---|
| 12 | 103 | 21 | expanded_train:241075 |
| 13 | 102 | 21 | expanded_train:271724 |
| 14 | 103 | 21 | expanded_train:307866 |
| 15 | 102 | 21 | expanded_train:351111 |
| 16 | 102 | 21 | expanded_train:400874 |
| 17 | 102 | 21 | expanded_train:451895 |
| 18 | 102 | 21 | expanded_train:485747 |
| 19 | 102 | 21 | expanded_train:524057 |
| 20 | 102 | 21 | expanded_train:572298 |
| 21 | 103 | 21 | expanded_train:619217 |
| 22 | 103 | 21 | expanded_train:663902 |
| 23 | 101 | 21 | expanded_train:695621 |
| 24 | 102 | 21 | expanded_train:736111 |
| 25 | 103 | 21 | expanded_train:786540 |
| 26 | 127 | 26 | expanded_train:830608 |
| 27 | 102 | 21 | expanded_train:873202 |
| 28 | 109 | 22 | expanded_train:929956 |
| 29 | 103 | 21 | expanded_train:1001681 |
| 30 | 126 | 26 | expanded_train:1042260 |
| 31 | 102 | 21 | expanded_train:1079731 |
| 32 | 104 | 21 | expanded_train:1145557 |
| 33 | 103 | 21 | expanded_train:1196655 |
| 34 | 126 | 26 | expanded_train:1247044 |
| 35 | 99 | 20 | expanded_train:1255515 |
| 36 | 63 | 13 | expanded_train:1311080 |

한 TASK나 페이지 종료는 전체 목표 완료가 아니다. 원문/후보가 같은 바이트여도 문맥 검토상 결함이 있으면 정제/부분 HOLD한다. 문제가 없어 그대로 보존할 때만 KEEP_SOURCE/ACCEPT_CANDIDATE의 원래 절대경로를 선택하고, 실제 수정 때만 새 TXT를 만든다. 판정 셀은 단일 토큰, 정확 출력 셀은 TXT 절대경로 하나이며 sidecar는 사유 칸에 둔다.

긴 일반 문서는 첫 part의 총 수·SHA 확인 뒤 2파트씩 묶을 수 있다. 각 exec_command max_output_tokens 4000과 바깥 functions.exec max_output_tokens 12000처럼 합산 여유를 잡고 모든 결과를 읽는다. 잘리면 미노출 part를 실제 재독하고 미완료를 EOF 완료로 기록하지 않는다. 새 경계 판단이 필요한 문서는 한 part씩 진행한다. packet/후보 사본을 저장하지 않는다.

실제 판정행이 정확하고 진행요약 건수만 틀리면 PROGRESS 한 줄로 정정한다. 판정·본문·SHA·경로가 바뀌면 새 정식 리뷰 버전으로 남긴다. 다음 페이지별 별도 승인·pilot 파일을 기다리거나 만들 필요 없다. 새 본문은 전문/원문 전체 diff/EOF를 확인한다.

