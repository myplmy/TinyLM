# 기존 분할 판독기의 field 전용 짧은 호출

자기 역할의 field36페이지 명단만 읽는다. 명령 시작은 `bash /home/uranus/tinyLM/tmp/hold-h-field-v1`이고 뒤에 페이지숫자, 정확원문ID, 정확패킷번호, 조각번호(생략하면1)를 순서대로 붙인다.

기존TASK/READING_VIEWS와 ROOT_IDENTITY_TASK의 지정 읽기·동일후보 생략계획은 그대로다. 한exec 한조각, 출력한도10000토큰 이상으로 읽고 pieces/characters/packet_complete/source_packet_sequence_complete와 실제원문/후보/full_diff의 논리END·EOF를 모두 확인한다. 첫조각이 packet_complete=false이면 다음조각을 읽는다. 파일명/0채움/부모경로는 직접조합하지 않는다.

보호ID와원형SHA는본문보다먼저검사하며 기존helper의2000자분할/SHA/역할명단/순서검사를 재사용한다. 시간journal·이해/인증·의미PASS를 새로 제공하지 않는다. 완료한원문은도구때문에재독하지않고 현재입력을마친뒤정확다음미착수부터사용한다. source가없거나거부/잘림이면판독으로세지않고정확지정값을확인한다. 다른역할·other유형은이진입점범위가아니다.
