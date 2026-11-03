# 355073 패킷 reader 호출 오류 기록

- 첫 실행은 지정 reader의 355073 패킷 1, piece 1을 성공적으로 읽었고 original/candidate 본문을 출력했다.
- 같은 셸 호출에서 piece 2 명령 문자열을 잘못 조합해 쉘이 `unexpected EOF while looking for matching quote`를 반환했다. 이 두 번째 호출은 실행되지 않았으며, 해당 실패 명령에서 입력 내용을 읽지 않았다.
- 이후 지정된 고정 reader를 정확한 `--source-id expanded_train:355073 --packet 1 --piece 2` 인수로 다시 호출했고 전체 diff와 `END expanded_train:355073 full_diff`, `END_APPROVED_PACKET_PIECE`를 확인했다.
- 재시도는 같은 지정 piece만 읽었다. 다른 경로나 파일을 검색·열지 않았다.
