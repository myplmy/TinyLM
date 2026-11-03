# 574329의 근거 있는 표제 복원

기존 독립 TASK016의 유일한 미결이다. 현재 birth TASK를 마감한 뒤 이 중재를 수행하고, 이어 기존 birth 다음 TASK부터110까지 재개한다.
총괄이 실제 발행처를 찾아 원문 정의와 공백만 무시한 전문 일치를 대조했다. 발행처 표제182개를 아래 지정 MD로 제공한다. 기존 표제34개는 중복 삽입하지 않는다.
발행처: https://news.masterworksfineart.com/2017/11/07/art-dictionary
이것은 캐시의 출처 계보 복구나 전기/미술사 전체의 사실 검증이 아니다. sourcekind UNKNOWN은 유지한다.
Read more 링크는 발행처에 추가된 UI이며 원문 정의에 없으므로 넣지 않는다. 원래 COUTERPROOF 등 철자는 임의 교정하지 않는다.
입력 전문 읽기는 아래 단일 ID 고정 reader만 허용한다. 이 MD·지정 표제 MD·자기 기존 TASK016/START/리뷰·sidecar와 자기 base/working/diff의 literal 읽기만 추가 허용한다.
도구 코드/registry/외부웹/다른Python/검색/다른역할·세션은 읽거나 실행하지 않는다.
`/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_glossary_574329_packet_v1.py --source-id expanded_train:574329 --packet 1 --piece 1`
27개2000~6000문자 패킷은 원문→기존 선택→전체diff의 연속이다. 각 packet의 pieces를 순서대로 다 읽으며 source_packet_sequence_complete와 실제논리END를 확인한다. 호출 max_output_tokens8000 이상.
총괄은 원문 바이트 그대로 base와 미선택 working을 복사했다. 아직 정제 본문이 아니며 생성된 라벨/문장도 없다.
base: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/expanded_train_574329_primary_original_base_v1.txt
working: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/expanded_train_574329_primary_working_v1.txt
원문 전체가 working에 있으므로 실제 TXT 정제와 표제 삽입은 Luna가 apply_patch Update File로 수행한다. 첫 리뷰에 참조되기 전의 working만 편집할 수 있고, 리뷰 저장 뒤에는 동결하여 새 버전을 만든다.
182개의 일치 정의는 문맥을 확인해 정확 원래 정의 앞에 실제 표제를 넣어 살린다. 여러 줄 정의·번호·인용·수량·단위·조건을 유지한다. 동일 MEZZOTINT의 서로 다른 두 정의를 중복이라고 합치지 않는다.
BACK TO TOP 같은 탐색 UI와 원문 결손 의존 조각은 원형 sidecar와 함께 분리하며 완결된 정의/인쇄술 예시는 보존한다. 근거 없는 표제·설명·번역은 만들지 않는다.
각 지정 표제 MD는 다음 경로다. 원문 줄은 삽입 후 이동하므로 정의 앞부분과 문맥으로 정확 위치를 확인한다.
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_01_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_02_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_03_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_04_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_05_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_06_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_07_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_08_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_09_V1.md
- /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/repeat_named_full_independent_v1/ROOT_GLOSSARY_PRIMARY_LABELS_10_V1.md

실제 전체 TXT와 별도 원형 hold MD를 만든 뒤 기존 TASK016의 다른4행도 유지한 새 review_016_vN.md에 정확 output basename과 구체 근거를 기록한다.
똑같은 candidate를 복제해 수정으로 세지 않는다. 파일명 충돌은 기존 파일을 보존하고 새 버전을 선택한다. 이 건 뒤 원래 birth 배정을 계속한다.
