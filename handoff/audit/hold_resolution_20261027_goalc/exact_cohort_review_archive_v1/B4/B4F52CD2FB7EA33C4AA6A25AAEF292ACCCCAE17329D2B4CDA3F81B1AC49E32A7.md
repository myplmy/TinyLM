# TASK_016 검토

| ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 |
|---|---|---|---|---|
| expanded_train:1215899 | REVISE_TEXT | 원문 전문 패킷 0001 실제 판독, 후보 바이트동일 증명 연결, full_diff 패킷 0002–0003의 마지막 논리 END 확인, 새 본문 전체 diff 끝 확인 | expanded_train_1215899_revised.txt | Java socket Q&A의 질문·응답, `connect()` 설명과 실제 방법을 유지하고, 마지막의 대상 없는 `The equivalent of` 조각만 `hold_1215899_v1.md`에 보존했다. |
| expanded_train:1236419 | REVISE_TEXT | 원문 전문 패킷 0001–0005 실제 판독, 후보 바이트동일 증명 연결 및 full_diff 패킷 0009 마지막 논리 END 확인, 새 본문 전체 diff의 끝 및 실제 마지막 본문행 확인 | expanded_train_1236419_revised_v6.txt | 빠진 그림·통계량·방정식·일정·정의에 직접 의존하는 조각만 `hold_1236419_v6.md`에 원형 보존했다. Langevin/GD의 완결 설명·조건, 실제 변수와 수치, 남아 있는 코드 조각을 보존했다. `The code is:`는 실제 남은 코드 블록을 가리켜 살렸고, 두 번 찍힌 마침표 하나만 정리했다. 식·값·코드를 보충하지 않았다. |
| expanded_train:1246440 | REVISE_TEXT | 원문 전문 패킷 0001–0004 실제 판독, 후보 바이트동일 증명 연결 및 full_diff 패킷 0008 마지막 논리 END 확인, 새 본문 전체 diff 끝 확인 | expanded_train_1246440_revised_v6.txt | Python 대입·참조 예시의 실제 코드와 값은 유지하고, 소실 대상에 의존하는 불완결 설명 및 문제 도입부만 `hold_1246440_v2.md`에 보존했다. 마지막 `same value` 문장의 열린 괄호를 닫았으며 식·값을 만들어 넣지 않았다. |
| expanded_train:1254747 | ACCEPT_CANDIDATE | 원문 전문 패킷 0001–0002 실제 판독, 후보 바이트동일 증명 연결 및 full_diff 패킷 0004 마지막 논리 END 확인 | expanded_train_1254747_candidate.txt | STM32/USB/가상 COM 관련 명칭, 버전·보드·도구 경로·명령·함수 대응·전압 정보가 모두 실제 값과 문맥을 갖춘다. 사용자별 Makefile 경로 지시는 미기입 데이터가 아닌 사용자 설정 지시다. 본문 변경이 필요하지 않다. |
| expanded_train:1259178 | REVISE_TEXT | 원문 전문 패킷 0001–0006 실제 판독, 후보 바이트동일 증명 연결 및 full_diff 패킷 0012 마지막 논리 END 확인, 새 본문 전체 diff 끝 확인 | expanded_train_1259178_revised.txt | VB6 설명·실제 코드/상수·UI 이벤트·데이터베이스 제공자와 ADODC 설정을 보존했다. 값 없는 단독 `Built in Type` 표제만 `hold_1259178_v1.md`에 원형 보존하며, 앞의 실제 `Built in Type User Defined Types`는 유지했다. |
