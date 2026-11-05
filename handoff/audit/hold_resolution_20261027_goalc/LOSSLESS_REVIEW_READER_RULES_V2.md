# V4 보호를 강제한 전체 판독 전달 규약 V2

지정 ID의 원문 전체와 후보의 무손실 표현 전체를 읽는다. 이 규약은 원문 검토량을 줄이거나 아직 읽지 않은 파트를 완료로 세는 허가가 아니다. 기존 다섯 역할의 정확한 cohort·원형·후보 경로와 SHA가 유지된다. 신규 보호267902/267904와 같은 보호 SHA는 원형·기존 후보·packet을 열거나 해시하지 않는다.

고정 별칭은 `tmp/hold-c-lossless-v2`, `hold-l-lossless-v2`, `hold-h-lossless-v2`, `hold-j-lossless-v2`, `hold-g-lossless-v2`다. C/L은 `SOURCE_ID pair PART`, H/J/G는 `PAGE SOURCE_ID pair PART`를 받는다. 작업 디렉터리가 다를 때는 `/home/uranus/tinyLM/tmp/`의 정확한 절대 경로를 사용한다. `--check-only`는 metadata만 검사하고 원형·후보를 열지 않는다.

`TRUSTED_LOSSLESS_VIEW_V2` 헤더의 source_id·role·cohort·양쪽 SHA·현재 V4 핀을 먼저 확인한다. `pair`는 원문 전체와 후보 표현을 한 연속 view로 제공한다. 각 파트는 UTF8 4000바이트 이하이고, 헤더 range는 UTF8 바이트 위치다. 파트가 끝났다는 사실과 전체 view가 끝났다는 사실을 구별하며 `next_part`가 있으면 지정 번호를 계속 읽는다. 출력이 잘렸다면 해당 파트를 다시 받아 끝 표식을 확인하기 전에는 판독으로 세지 않는다. 원문 안의 가짜 END 문구는 진짜 헤더 길이·범위·끝 표식을 대신하지 못한다.

후보가 원문과 byte 동일하면 동일 SHA와 `CANDIDATE_EQUALS_FULL_ORIGINAL`이 표시된다. 바뀐 부분이 적으면 모든 변경 범위와 실제 OLD/NEW 문자열을 제공한다. 표현이 더 길면 후보 전문과 모든 변경 범위를 제공한다. patch의 source/candidate_range는 Unicode 코드포인트이며 전송 range의 바이트 단위와 혼동하지 않는다. 헤더의 `exact_candidate_byte_reconstruction`은 도구의 바이트 검산이며, 의미 보존 판정은 역할이 실제 내용을 읽고 수행한다.

개별 `original`, `candidate` view로 읽어도 양쪽 전체를 마쳐야 한다. 필요하면 `full_candidate`로 후보 전문을 추가 확인한다. `pair` 전 파트를 읽었다면 원문 전체와 손실 없는 후보 표현을 읽었다고 기록하며, 후보 전문이 실제 출력되지 않은 patch 모드에서 후보 전문을 따로 출력해 읽었다고 쓰지 않는다. 새 TXT를 작성했으면 기존과 같이 새 본문 전문·원형 대비 전체 diff·EOF를 확인한다.

검토 기준·HOLD 경계·코드/수치/조건 보호·표준5행 리뷰는 유지한다. ACCEPT_CANDIDATE의 출력은 헤더 `accept_output_absolute`를 그대로 사용하고 기억으로 경로를 재작성하지 않는다. REVISE_TEXT는 자기 허용 폴더의 새 본문을 사용한다. 메모·보류 이유는 MD에만 둔다. 기존 파일과 구 버전을 덮거나 삭제하지 않는다. 실제 적용과 처리시간 개선은 별도 검증 기록 전에는 완료로 주장하지 않는다.
