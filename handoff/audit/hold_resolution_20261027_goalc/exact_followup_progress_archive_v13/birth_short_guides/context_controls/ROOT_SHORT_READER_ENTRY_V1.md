# 동일한 v2 판독기의 짧은 호출 경로

자기 역할만 사용한다. 기존 ROOT_DELIVERY_READER_TASK의 원문ID와 정확 패킷번호를 두 위치 인자로 전달한다. 명령의 시작은 `bash /home/uranus/tinyLM/tmp/hold-c-v1`이다. 뒤에 원문ID, 숫자 패킷번호를 순서대로 적는다.

한 exec에서 지정 패킷 하나만 읽고 출력 한도는 10000토큰 이상을 준다. 기존 v2의 metadata와 END, 최종 original/candidate/full_diff 논리 END 및 EOF를 확인한다. 다른 packet이나 경로를 추정하지 않는다. 실제 wrapper SHA는 3DCCB97124851FF73F343409D5C41006519B8CE6AF81839466993609E0DF739A, 기존 v2 SHA는 4152095B58E5F2A97C579D332B6DDA5DF219E72190829E690AB2053329413C17이다.

기존 guard/config/registry/journal과 역할·ID·SHA·순서 검사는 그대로다. 완료한 입력을 이 도구 때문에 다시 읽지 말고 자기 최신 완료 TASK 다음 미착수부터 쓴다. --probe는 총괄 시험 전용이며 Luna 정식 판독에는 붙이지 않는다. 실패/잘림은 판독에 세지 않고 정확 명령의 성공 출력만 사용한다.
