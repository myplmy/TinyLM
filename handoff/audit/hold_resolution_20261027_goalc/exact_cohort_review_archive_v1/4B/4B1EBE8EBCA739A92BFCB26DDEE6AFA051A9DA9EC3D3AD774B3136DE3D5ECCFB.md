# TASK_031 독립 판독

| ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 |
|---|---|---|---|---|
| expanded_train:132617 | REVISE_TEXT | original·candidate 전문, 지정 패킷 0001 전체 diff END, 양쪽 실제 EOF, 새 본문 전체 diff·EOF | expanded_train_132617_birth_years_held_preserving_month_day_20261103.txt | 본문 `1895년 10월 19일`과 분류 `1875년 출생`이 충돌한다. 두 연도 및 직접 연결 분류를 sidecar `hold_132617_conflicting_birth_year_fields_20261103.md`에 원형 보류하고 10월 19일, 1958년 10월 22일 사망일과 경력·다른 분류를 보존했다. 별도 인물인 어머니의 70대 서술을 출생연도 판단에 쓰지 않았다. |
| expanded_train:133445 | ACCEPT_CANDIDATE | original·candidate 전문, 지정 패킷 0001 무차이 diff END, 양쪽 실제 EOF | expanded_train_133445_candidate.txt | 본문·출생 서술·분류가 모두 1891년을 가리킨다. 1904년의 직접 `14세` 표현은 나이 역산이나 출생연도 정정에 사용하지 않았다. 친족 현정건·현진건의 별도 출생·사망일과 제목·저서 및 연혁을 현철의 날짜와 혼동하지 않았다. |
| expanded_train:133538 | REVISE_TEXT | original·candidate 전문, 지정 패킷 0001→0004 연속 전체 입력과 마지막 논리 END, 직접 전체 diff·양쪽 실제 EOF, 새 본문 전체 diff·EOF | expanded_train_133538_unqualified_death_days_held_preserving_month_20261103.txt | 출생 1880년은 본문과 분류가 일치한다. 다만 리드 `1922년 2월 6일`과 비인용 본문 `1922년 2월 11일`은 같은 사망 사건에 대한 조건 없는 상충 일자다. 두 일자만 sidecar `hold_133538_conflicting_unqualified_death_days_20261103.md`에 원형 보류하고 공통 1922년 2월, 암살 사건·자베이 거리 및 사후 서술을 보존했다. 박노자에게 귀속된 직접인용의 2월 11일 표기와 출처 귀속은 원문 그대로 유지했으며 반복을 독립 증거로 세지 않았다. |
| expanded_train:134009 | ACCEPT_CANDIDATE | original·candidate 전문, 지정 패킷 0001 무차이 diff END, 양쪽 실제 EOF | expanded_train_134009_candidate.txt | 본문에서 1900년 출생 및 1992년 12월 27일 사망을 적고, 분류의 출생·사망 연도도 각각 일치한다. 여성 교육 경력·인물 및 단체 관계·명단 수록 등 나머지 내용을 후보가 보존했다. |
| expanded_train:134422 | ACCEPT_CANDIDATE | original·candidate 전문, 지정 패킷 0001 무차이 diff END, 양쪽 실제 EOF | expanded_train_134422_candidate.txt | 본문과 분류의 출생연도 1925년 및 사망연도 1975년이 일치한다. 1975년 1월 29일 사망일과 사망 서술, 군 경력·외교관 경력 및 부친 안병범의 별도 날짜를 혼동하지 않았다. |
