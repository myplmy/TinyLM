# 6948의 누락된 printf 식별자와 문장 연결

총괄이 지정 원문 583자 전부와 Perl 발행자 문서의 5.20.3/5.26.3/현재판을 실제 대조했다.

- 원문 ID: expanded_train:6948
- primary: https://perldoc.perl.org/5.20.3/functions/printf
- 비교한 후속판: https://perldoc.perl.org/5.26.3/functions/printf

원문의 real filehandle이라는 표현은 5.20.3에 존재하고 후속판의 bareword로 현대화하지 않는다. 원문의 실제 버전 자체가 확정된 것은 아니므로 버전 표기를 본문에 새로 넣지 않는다.

다음 누락만 같은 문맥의 명명된 발행자 항목과 대응하므로 복원할 수 있다.

- 소유 함수 표제: `printf`. 맨 앞 실제 print/sprintf 식의 관계를 복구하는 접두 `Equivalent to`.
- output record separator의 비어 있는 식별자: `$\`.
- 원문의 LIST 생략 조건 뒤에는 `$_ is used as the format;`가 대응한다. 기존 뒤 절은 유지한다.
- real filehandle 예시의 두 빈 자리: 각각 `FH`, `$fh`.
- locale 조건은 기존 괄호와 문자열 앞의 `If use locale (including`만 복원한다.

새 Usage 네 가지, 후속판의 단일리스트 해석/경고/성능 조언 등 원문에 없는 단락을 가져오지 않는다. 기존 printf/sprintf, POSIX::setlocale(), LC_NUMERIC과 참고 이름은 보존한다. 실행하거나 Perl 코드를 새로 쓰지 않는다. Luna가 새 본문/sidecar/review를 작성하고 복원의 primary URL과 원문 연결을 남긴다.
