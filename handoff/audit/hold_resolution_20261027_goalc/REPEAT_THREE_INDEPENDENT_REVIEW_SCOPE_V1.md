# 반복 중재 수정3건의 별도 의미 판독

역할은 기존 context_latin Luna이며 다른 역할의 파일은 아래 정확한 읽기 경로로만 허용한다. 새 본문을 작성한 역할의 판단과 별개로 원문·수정문 전문을 읽고 실제 정보와 문맥 보존을 판독한다. 계산·해시·코드·시험·Git·웹·모델·GPU 및 목록 밖 자료는 금지한다.

입력 원문은 `data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_local_context_counter_v1/inputs/expanded_train_<ID>_original.txt`의362272,704965,711348 세 파일이다.

수정문 정확 경로:

- `data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/historical_review/repeat_local_context_counter_v1/expanded_train_362272_review_v1.txt`
- `data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_local_context_counter_v1/expanded_train_704965_reviewed_v3.txt`
- `data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_local_context_counter_v1/expanded_train_711348_reviewed_v3.txt`

출력은 자기 `agents/context_latin/repeat_three_independent_v1/` 폴더의 새 TXT/MD만 허용한다. `review_001.md`는 `ID | 판정 | 근거 | 출력 TXT 경로 | 보류 MD 경로`5열로 저장한다. 판정은 ACCEPT_CANDIDATE/REVISE_CANDIDATE/NEEDS_ROOT 중 하나다. 수정이 필요하지 않으면 정확한 위 입력 수정문 경로를 출력 칸에 쓰고 새 TXT를 복사할 필요는 없다. 수정이 필요하면 자기 폴더에 전체 새 TXT를 작성하고 옛 입력은 보존한다.

확인할 것은 단순 중복 감소가 아니라 저자·인용 주체·제목과 개별 항목·날짜·수치·단위·조건·계획·불확실성·논지의 순서가 유지되는지, 같은 반복이라도 실제 다른 글이나 다른 역할이 있었는지다. 원문에 없는 사실 정정은 하지 않는다. 검수 설명은 학습 본문에 넣지 않는다. 먼저 두 전문을 판독하고 나서 판단 근거를 기록한다.

이 검토는3개 수정에 한정된다. 전체 잔여 목표의 작업량 상한이나 최종 캐시 승인으로 쓰지 않는다.
