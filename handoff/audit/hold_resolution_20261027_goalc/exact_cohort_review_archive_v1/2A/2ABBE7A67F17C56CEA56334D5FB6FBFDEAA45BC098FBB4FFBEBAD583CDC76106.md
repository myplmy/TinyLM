# TASK_003 판독 리뷰 보정

입력 원문·후보 경로 접두부: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_native_proofs_v1/pages/page_002/inputs/`
순서 패킷 경로 접두부: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/remaining_field_title_page_002_counter_v1/reading_packets_v1/`

| ID | 판정 | 실제 판독 범위 | 출력 (TXT basename) | 구체 근거 |
|---|---|---|---|---|
| expanded_train:12248 | REVISE_TEXT | 지정 original/candidate 전문 EOF; packet 0001–0005의 original·candidate·full_diff END; 직접 full_diff 끝 | revise_12248_empty_intro_slots_20261103_v1.txt | 스탕달의 실제 이름·IPA·월일/연도, 생애·작품·평가·참고문헌·외부 링크·분류를 보존했다. 도입부의 빈 슬롯은 hold_12248_empty_intro_slots_footnote_20261103_v1.md에, 내용 없는 각주 표제도 같은 MD에 원형 기록했다. |
| expanded_train:12410 | REVISE_TEXT | 지정 original/candidate 전문 EOF; packet 0001–0002의 original·candidate·full_diff END; 직접 full_diff 끝 | revise_12410_empty_alias_slot_20261103_v1.txt | 한국·중국·다른 지역 정당들의 실제 이름, 연도, 설립·해산·변경 관계 및 순서를 보존했다. `국민당 (일본)()`의 채워진 지역명은 남기고 뒤 빈 슬롯만 제거했으며 원형을 hold_12410_empty_alias_slot_20261103_v1.md에 기록했다. |
| expanded_train:12545 | REVISE_TEXT | 지정 original/candidate 전문 EOF; packet 0001–0008의 모든 연속 original·candidate·full_diff END; 직접 full_diff 끝 | revise_12545_empty_sections_20261103_v1.txt | 개최국 선정·예선·추첨 규칙, D/E/F조의 채워진 설명, 득점·골 수, 순위 방법, 기타 기록·조건·날짜와 링크는 보존했다. 비어 있는 대회/표 표제 및 빈 제목 슬롯만 hold_12545_empty_sections_20261103_v1.md에 원형 기록했다. |
| expanded_train:12656 | REVISE_TEXT | 지정 original/candidate 전문 EOF; packet 0001–0002의 original·candidate·full_diff END; 직접 full_diff 끝 | revise_12656_empty_intro_heading_20261103_v1.txt | 에드가 드가의 이름과 출생·사망 월일/연도, 생애·화풍 설명, 작품명, 링크와 분류를 유지했다. 빈 괄호 슬롯과 항목 없는 `주요 작품`·`각주` 표제는 hold_12656_empty_intro_heading_20261103_v1.md에 보존했다. |
| expanded_train:13213 | REVISE_TEXT | 지정 original/candidate 전문 EOF; packet 0001–0008의 모든 연속 original·candidate·full_diff END; 원문-후보 full_diff에 차이 없음 END | revise_13213_empty_fields_equation_pointer_20261103_v1.txt | 총괄 중재에 따라 화살표만 남은 `악티늄(←, ←)`·`Ac(←)` 괄호 두 슬롯만 hold_13213_missing_arrow_fields_equation_pointer_20261103_v1.md에 원형 보존했다. 악티늄명·Ac 기호·원자번호 89·1889년과 채워진 문장은 유지했으며 외부 사실로 날짜를 고치지 않았다. 뒤따르는 식이 없는 문장은 화학식 없이 본문에 실제 적힌 베릴륨-알파 입자-중성자 관계를 보존하고, 빈 식 포인터만 정리했다. |
