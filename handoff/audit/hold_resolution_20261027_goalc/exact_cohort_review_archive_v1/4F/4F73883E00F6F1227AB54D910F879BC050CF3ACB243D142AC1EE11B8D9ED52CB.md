# 현재 TASK 경계에서 고정 reader로 전환

Latin1353개 배정의2122패킷 전량 재구성, 실제 CLI 성공과 다른 역할 ID 거부를 총괄이 검산했다. 원래 목표와 입력은 그대로다. 현재 이미 읽는 TASK를 마친 뒤 정확 다음 TASK부터 이 규약을 적용하고, 완료 TASK를 도구 전환 때문에 다시 읽지 않는다.

- `ROOT_FIXED_READER_SCOPE_V1.md`의 앞 규칙과 자기 정확 `ROOT_FIXED_READER_TASK_NNN_V1.md`를 읽는다.271개 파일 경로 목록을 전부 재출력할 필요는 없다.
- 원문·최종후보·전체차이 패킷은 이 자기 TASK의 고정 명령으로만 판독한다. 이전 remaining_birth 경로나 직접 raw packet cat으로 돌아가지 않는다.
- 명령은 이미 Python 실행파일을 포함한 완결 명령이다. 앞에 Python 경로를 또 붙이지 않고 `tools.exec_command`의 cmd로 그대로 호출한다.
- 한 exec에서 한 패킷을 호출하며 출력 예산은10000토큰 이상이다. 내부 piece2/2 헤더는 두 조각을 합친 뒤의 메타데이터이며 본문은 논리 패킷 전체다. 논리 원문/후보/전체차이가 여러 패킷이면 각 패킷을 순서대로 끝까지 읽는다.
- 같은 명령을 반복해도 다음 패킷으로 넘어가지 않는다. 다음 번호는 현재 TASK 명령에서 고른다. 잘림이 있으면 해당 부분을 다시 확인하고 실제 범위를 기록한다.
- 자기 `ROOT_UNCHANGED_INITIAL_COPIES_V1.md`의 앞10줄과 필요한 ID 행을 볼 수 있다.1353개 고정 후보의 자기 initial_candidate 사본은 원래 후보와 바이트가 같고 새 정제본이 아니다.
- 자기 initial_candidate는 읽고 자기 새 draft_로 복사할 수 있으며 입력 사본 자체는 덮지 않는다. 초안·최종본 규약은 현재 `AUTHOR_DRAFT_PUBLICATION_RULES_20261103_V1.md`를 따른다.
- ACCEPT 출력은 `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/birth_root11_independent_v1/inputs/<source>_<ID>_candidate.txt`의 원래 지정 경로다. 자기 initial 사본이나 이전 단계 경로를 ACCEPT로 연결하지 않는다. validation 접두어도 실제 TASK를 그대로 따른다.
- 새 의미 보완은 자기 새 TXT/원형 MD로 작성한다. 이 규약은 registry/helper 코드·다른 역할 자료 읽기, 임의 Python·해시·시험·통계·웹·Git·모델 권한을 추가하지 않는다.
