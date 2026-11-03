# 1418578: 공식 PEP와 직접 맞춘 코드 소실

총괄이 지정 원문의 해당 문맥과 [공식 PEP227](https://peps.python.org/pep-0227/)의 예제·재바인딩 절을 직접 대조했다. 원문 SHA-256은 FF0DB57BF072E532257E98ECF9C83A376CCD43BC835036BCA7346955CBD27F68다. 최신 페이지의 다른 절이나 현재 Python 기능을 통째로 이식하지 않는다.

bank_account 예제는 원문과 발행처의 모든 비공백 토큰이 일치하되, 두 대입문의 좌변/우변에서 [0] 네 곳만 소실됐다. deposit과 withdraw 각각 두 balance에 [0]을 붙이는 복원만 근거가 있다. return balance 두 곳은 발행처에서도 그대로이므로 return balance[0]으로 바꾸지 않는다. 기존9논리줄의 들여쓰기는 순서대로0/4/4/8/8/4/8/8/4칸이다. 이 정확한 정의/두 내부 함수 구조에 한정한다.

make_wrapper의 조건에도 원문 attr과 발행처 attr[0]의 직접 대응이 있다. 비교의 [0] 한 곳만 복원할 수 있다. 원래 Python2의 raise/print/long 표기와 대화형 프롬프트는 최신 Python으로 고치지 않는다. wrapper의 실제8논리줄(바깥def/class/안쪽def/if/return/else/raise/바깥return)의 들여쓰기는0/4/8/12/16/12/16/4칸이며 프롬프트 뒤 코드 기준이다.

Tim Peters 예제의 # skip to the next page는 실제 코드 주석이다. UI나 우리 검수메모로 지우지 않는다. 이 예제는 i대입/바깥def/안쪽def/print/첫주석/skip주석/둘째주석/for/pass/g호출의10논리줄이고 들여쓰기는0/0/4/8/4/4/4/4/8/4칸이다. 원문의 비공백 토큰과 발행처가 모두 일치한다. 일반적으로 공백만 맞으면 의미 보존이라는 증거가 아니라 이 특정 발행처의 실제 구조를 확인한 것이다.

XXX Explain the examples, XXX need some counterexamples, XXX Much more to say here 같은 미완 편집 placeholder는 원 저자의 미완 기록임을 sidecar에 남겨 분리할 수 있다. 반면 XXX Jeremy, is this still the case?처럼 바로 뒤 구현 주장에 대한 원 저자의 불확실성은 그 주장과 함께 보존한다. 질문을 지우고 확정 사실처럼 만들지 않는다. 학술 비교/귀속이 채워진 다른 XXX 구간도 단어만 보고 일괄 삭제하지 않는다.

실제 새 TXT는 Luna가 작성한다. 임의의 함수/인덱스/문장/블록을 만들거나 실행하지 않는다. 정확 새 본문·원형 sidecar와 자기 TASK026의 다섯 행을 유지한 새 리뷰로 연결한다. 검산 JSON은 총괄 소유이며 Luna가 코드/검사를 실행하거나 열 필요는 없다.
