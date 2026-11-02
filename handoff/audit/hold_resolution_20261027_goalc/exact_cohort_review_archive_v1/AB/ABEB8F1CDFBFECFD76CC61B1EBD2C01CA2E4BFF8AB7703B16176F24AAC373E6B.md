# 경로 오류 기록

아래 네 호출은 지정 입력에 경로 접두어를 잘못 붙이거나 금지된 `../`를 사용해 실패했다. 각 응답은 파일 없음이었고, 파일 본문 내용은 반환되지 않았다. 이후 입력·프로토콜은 TASK/READING_VIEWS/root 허용서에 적힌 정확 절대경로로 읽었다.

| 호출 | 관측 응답 | 본문 반환 |
|---|---|---|
| `diff -u /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/remaining_birth_full_counter_v1/inputs/expanded_train_1184460_candidate.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/remaining_birth_full_counter_v1/expanded_train_1184460_revised_v2.txt` | `diff: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/remaining_birth_full_counter_v1/inputs/expanded_train_1184460_candidate.txt: No such file or directory` | 없음 |
| `cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/reading_packets_v1/expanded_train_1009428_0006.txt` | `cat: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/reading_packets_v1/expanded_train_1009428_0006.txt: No such file or directory` | 없음 |
| `cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/inputs/expanded_train_1028244_candidate.txt` | `cat: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/inputs/expanded_train_1028244_candidate.txt: No such file or directory` | 없음 |
| `cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/../repeat_named_roles_counter_v2/ROOT_MEDIATION_V3.md` | `cat: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/../repeat_named_roles_counter_v2/ROOT_MEDIATION_V3.md: No such file or directory` | 없음 |

정확 경로로 재시도한 성공 판독에 실패 호출의 내용을 근거로 포함하지 않았다.
