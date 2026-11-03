# 기존 complete-reader 헤더의 내부 조각 값

기존 hold-l-v1 및 고정 v2는 한 호출에 지정 packet 전체를 출력한다. 내부 read_piece 두 조각을 합친 뒤 헤더의 piece/characters만 마지막 내부 조각에서 복사하는 표기 한계가 있다. piece2/2·characters2000–4000이어도 출력은 전체 packet0–4000자이며 sha256·total_characters는 그 전체 패킷의 값이다. 문자 수4000은 원문서 전체 길이가 아니다. END_APPROVED_COMPLETE_PACKET은 현재 패킷의 끝이다.

ROOT_DELIVERY_READER_TASK_251_V1.md의 정확 명령은962627 packet1–2,96436 packet1–4다. 한exec 한packet/출력10000토큰 이상으로 아직 안 읽은 다음 packet을 읽고 모든 original/candidate/full_diff 논리 END와 마지막 source_packet_sequence_complete=true를 확인한다. 이미 실제 읽은 packet을 헤더 표기 때문에 재독하지 않으며 임의 piece 인자·--probe·raw cat을 추가하지 않는다. 실제 출력 잘림은 저장 판독으로 세지 않고 범위를 총괄에 보고한다. 다른 TASK도 그 TASK에 적힌 마지막 packet까지 이어 읽는다.

이 안내는 경로·입력·본문·판정 변경이나 새로운 실행 권한이 아니다. 총괄 root probe는 review 입력 전달 시각을 소급 증명하지 않는다.
