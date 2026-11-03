# 666693의 실제 메서드 표제와 코드 개행 근거

총괄이 지정 원문 전문과 발행자의 CPAN POD를 실제 대조했다.

- 원문 ID: expanded_train:666693
- primary: https://metacpan.org/pod/Config%3A%3AHosts
- 확인한 POD의 표시 VERSION은 0.01이다. 배포판 버전과 혼동하거나 원문에 버전을 새로 넣지 않는다.

원문 5행부터의 정의 순서/문구가 POD의 각 명명된 항목과 일치한다. 영어 뜻이나 나열 순서만 추정한 매칭이 아니다. 다음 표제만 각 실제 정의 바로 앞에 복원할 수 있다.

| 원문 행 | 복원 가능한 실제 표제 |
|---|---|
| 5–6 | new ($;%) |
| 7 | is_valid_ip ($) |
| 8 | is_valid_host($) |
| 9 | read_hosts($;$) |
| 10 | determine_ip_or_host ($$) |
| 11–12 | query_host ($$) |
| 13 | insert_host ($%) |
| 14 | delete_host ($$) |
| 15–16 | update_host ($$) |
| 17 | write_hosts($;$) |

원문 3행 SYNOPSIS의 실제 토큰은 primary의 예시와 일치한다. primary에서 확인한 독립 문장 경계와 read_hosts 뒤의 기존 주석 끝에만 개행을 복원할 수 있다. 이 구간의 코드를 실행하거나 의미상 수정하지 않는다. 주석과 이후 호출의 분리는 이번 primary 확인에 한정되며 다른 자료의 주석 끝을 추정할 권한이 아니다.

원문에 이미 있는 저자/감사/조건/라이선스는 보존한다. 원문에 없는 새 문서 절이나 추가 API/사실은 넣지 않는다. 빈 탐색 예고 등은 기존 최소 분리 원칙으로 처리한다. 실제 본문은 Luna가 새 TXT/sidecar/review 버전으로 만들고 총괄의 후속 검산 전까지 채택하지 않는다.
