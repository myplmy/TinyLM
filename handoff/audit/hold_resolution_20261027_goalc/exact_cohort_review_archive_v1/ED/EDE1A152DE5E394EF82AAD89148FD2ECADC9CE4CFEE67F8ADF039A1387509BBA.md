| ID | 판정 | 실제 판독 범위 | 출력 TXT | 구체 근거 |
|---|---|---|---|---|
| expanded_train:151725 | REVISE_TEXT | 지정 packet 1–3의 원문·후보·전체 diff를 논리 END와 각 packet EOF까지 판독; 새 본문 전문 및 후보 대비 전체 diff 확인 | reviewed_151725_task090_v1.txt | 1121년 출생은 리드·본문·분류에서 일치한다. 명시된 `1175년 1월 12일(1174년 음력 12월 18일)` 대응과 본문·분류의 1174년은 변경하지 않고, 리드의 닫히지 않은 바깥 괄호만 닫았다. |
| expanded_train:151767 | NEEDS_ROOT | 지정 packet 1–2의 원문·후보·전체 diff를 논리 END와 각 packet EOF까지 판독 | — | 출생 1888년/분류 1898년 및 사망 1943년/분류 1941년의 충돌 연도는 후보에서 제거되고 월일·향년은 남아 있다. 다만 `1942년 ... 체포되어 이듬해 ... 시달렸다` 뒤에 `12월 8일 순국`이 이어져 1943년 사망을 간접 단정하는지 미결이다. 정확 연결 범위는 총괄에 질문했으며 출력은 아직 선택하지 않았다. |
| expanded_train:151967 | ACCEPT_CANDIDATE | 지정 packet 1–3의 원문·후보·전체 diff를 논리 END와 각 packet EOF까지 판독 | expanded_train_151967_candidate.txt | 리드·본문·분류의 1158년 출생이 일치하고 1210년 및 실제 월일·음력 표기도 유지된다. 후보는 빈 각주·참고문헌 표제만 정리한다. |
| expanded_train:152179 | ACCEPT_CANDIDATE | 지정 packet 1–2의 원문·후보·전체 diff를 논리 END와 각 packet EOF까지 판독 | expanded_train_152179_candidate.txt | 리드·본문·분류의 1209년 출생과 1257년 사망이 일치한다. 윤달을 포함한 명시 사망 날짜와 생애·가족·경력은 보존되고 후보는 빈 참고 표제만 정리한다. |
| expanded_train:152213 | ACCEPT_CANDIDATE | 지정 packet 1–2의 원문·후보·전체 diff를 논리 END와 각 packet EOF까지 판독 | expanded_train_152213_candidate.txt | 리드·본문·분류의 1068년 출생과 1135년 사망이 일치한다. 후보는 실제 날짜 및 생애를 유지하고 빈 각주·외부 링크 표제만 제거한다. |
