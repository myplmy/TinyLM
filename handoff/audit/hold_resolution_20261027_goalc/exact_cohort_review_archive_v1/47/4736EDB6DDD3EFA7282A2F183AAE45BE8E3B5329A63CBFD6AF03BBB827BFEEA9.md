# expanded_train:452473 정제 판정

- 원문: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_native_proofs_v1/pages/page_017/inputs/expanded_train_452473_original.txt` — SHA-256 `B6951F003A15D5079D89AC6AD9B240E1E5F0B9AD89563674233595C11162309C`
- 후보/준비 입력: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_native_proofs_v1/pages/page_017/inputs/expanded_train_452473_candidate.txt` — SHA-256 `974C8F07AEE065538730BDAA4A2D8C3DD5A0E9FCF3912230E79415DA829C469C`
- 출력: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/remaining_field_title_page_017_counter_v1/expanded_train_452473_task001_v1.txt`
- 판정: 후보가 제거한 행성 이름 등의 빈 괄호 15곳과 비어 있던 `참조` 표제를 반영했다. 외부 링크 제목 뒤의 빈 괄호 9곳도 링크 표지의 빈 값으로 판단해 삭제하고, 실제 제목·저자·매체·날짜는 그대로 보존했다. `행성의 기호` 아래의 “이 표는 … 열거한다”는 표 행 없이 표에 직접 의존하므로 보류했다. 같은 문단의 행성 영어명과 그리스·로마 신 이름에 관한 독립 문장은 유지했다. 내용 없는 `일일 운동` 표제는 삭제했다. 끝의 `표 1` 캡션과 동일 행의 별자리·하우스·행성 관계를 설명하는 문장은 표 자료가 없어 직접 의존하므로 보류하고, 직전의 화성·양자리 설명 문단은 보존했다. 비어 있지 않은 참고문헌과 외부 링크 항목은 제목·서지 정보를 포함해 모두 유지했다.
- 검토: batch-v1 pair 1–13/13 전량, 마지막 part `end_of_view=true`; 수정 전 준비 후보와 출력의 바이트 일치를 확인했다. 최종 TXT 전문·후보 대비 전체 diff·EOF를 확인했고, batch-v1의 원문-후보 16개 변경과 이어 대조했다. 외부 사실 확인은 하지 않았다.
