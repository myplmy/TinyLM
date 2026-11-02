# 123070 신규 미발행 작업본 편집 허가

root가 기존 candidate의 정확한 바이트만 두 새 파일에 복사했다. 정제 문구나 수정은 아직 없다. base는 원형 입력 복사본으로 고정 보존하고 work만 아래 범위에서 편집한다.
원형base: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/remaining_birth_full_counter_v1/expanded_train_123070_scoped_base_v1.txt
base_sha256: 3B96206FAAE6F3F1816F2146FA8D6A1B3D1D4E6430E3A5786BB172BC0A91F423
신규work: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/remaining_birth_full_counter_v1/expanded_train_123070_pending_work_v1.txt
work_initial_sha256: 3B96206FAAE6F3F1816F2146FA8D6A1B3D1D4E6430E3A5786BB172BC0A91F423
이 work 한 파일에 한해 첫 완료리뷰로 선택되기 전 apply_patch Update File의 좁은 편집을 허용한다. 기존 완료본문/리뷰/다른초안은 수정하지 않는다. 신규work 편집을 끝내면 해당 TXT를 선택하는 새 review023버전을 기록하고 그 뒤 다시 덮지 않는다. 후속정정은새버전이다.
이 두 exact 자기파일의 literal cat 및 `diff -u -- base work`만 추가 읽기 허용한다. raw공유입력경로 cat/sed/rg/find/경로없는검색 금지는 유지한다. 원문전체/diff다시읽기는 기존고정reader만사용한다.
새 TXT/MD를 heredoc 또는 apply_patch Add File로 작성하는 기존 쓰기도 허용돼 있다. 새 파일의 내용을 직접 쓰는 것은 입력경로 읽기가 아니다. 셸변수/동적경로검색으로우회하지않는다.
생년 월일10월18일과원호가붙은9월11일을 한쪽만 선택하지 않는다. 원래각날짜의표기맥락을유지하고새달력라벨·환산을추가하지않는다. 연도1127과분류1155는선택없이보류하되원호+서력연도쌍은같은필드전체로보류한다. 사망1192/분류1158도실제상충연도만보류하고독립사건/기존월일을유지한다. root가두월일의공개맥락을추가확인중이다.
이름·주체·독립나이·실제조건·인용을삭제하지않는다. 같은생년/사망분류역할을먼저확인하며서지제목의연도는고치지않는다. 편집후실제차이는base/work의정확diff로확인한다.
