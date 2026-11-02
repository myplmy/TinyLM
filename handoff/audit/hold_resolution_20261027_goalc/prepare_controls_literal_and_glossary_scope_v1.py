"""Prepare fixed registries and unchanged edit bases; author no cleaned prose."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
HELPER = AUDIT / 'scoped_packet_reader_v1.py'


def sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def save(path, value):
    payload = value.encode('utf-8')
    assert 0 < len(payload) < 20_000_000
    with path.open('xb') as stream:
        stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(payload))


def fixed_reader(label, cohort, rows):
    registry_path = AUDIT / ('SCOPED_CONTEXT_CONTROLS_' + label.upper() + '_INPUTS_V1.json')
    registry = dict(allowed_packet_directory=str((BASE / cohort / 'reading_packets_v1').relative_to(ROOT)),
        sources={r['id']: r['reading_parts'] for r in rows})
    for row in rows:
        for pin in row['reading_parts']:
            assert sha((ROOT / pin['path']).read_bytes()) == pin['sha256']
    registry_pin = save(registry_path, json.dumps(registry, ensure_ascii=False, indent=2) + chr(10))
    template = (AUDIT / 'read_context_controls_birth_packet_v1.py').read_text(encoding='utf-8')
    template = template.replace('SCOPED_CONTEXT_CONTROLS_BIRTH_INPUTS_V1.json', registry_path.name)
    template = template.replace('BCE445B7C4897A75926EAC3618D5EFBC8E5F371EC71D891E1B41966F36F0A588',
                                registry_pin['sha256'])
    assert sha(HELPER.read_bytes()) == 'DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'
    path = AUDIT / ('read_context_controls_' + label + '_packet_v1.py')
    return save(path, template), registry_pin


literal_path = BASE / 'remaining_literal_full_counter_v1/manifest.json'
literal = json.loads(literal_path.read_text(encoding='utf-8'))
literal_rows = [r for r in literal['rows'] if r['role'] == 'context_controls']
literal_reader, literal_registry = fixed_reader('literal', 'remaining_literal_full_counter_v1', literal_rows)
directory = BASE / 'agents/context_controls/remaining_literal_full_counter_v1'
lines = ['# controls 다음 유형의 고정 입력 읽기', '',
    '기존 출생 배정110과 별도 glossary 중재를 마친 뒤에 이 유형을 시작한다. 현재 START/TASK는 준비 입력이며 의미 검토 완료가 아니다.',
    '자기 START_HERE/TASK001–072/READING_VIEWS 및 이 MD만 literal cat으로 읽는다. 원문·후보·diff는 아래 고정 reader만 허용한다.',
    'registry·도구 코드 열기/수정, 다른 Python, 경로 없는 검색, 원문 raw cat/sed/rg/find는 금지한다.',
    '이 reader 실행은 총괄 구현의 고정 읽기 도구 예외이며 코딩·시험·해시 계산 권한이 아니다.',
    '명령의 source-id/packet/piece만 자기 실제 TASK에 맞춰 선택한다. 패킷은2000문자이므로 piece는1이며 총 packet 수와 마지막 논리END를 확인한다.',
    '각 호출 max_output_tokens는8000 이상을 사용한다. source_packet_sequence_complete=true까지 한 ID를 순서대로 다 읽는다.',
    '명령: ' + str(ROOT / 'handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py'),
    '`/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B ' + str(ROOT / literal_reader['path']) +
        ' --source-id ' + literal_rows[0]['id'] + ' --packet 1 --piece 1`',
    '실제 정제 쓰기는 자기 새 TXT/MD만 noclobber이며 기존 파일/리뷰는 보존한다. 원형·모델·GPU·학습·타 역할/세션 자료는 금지한다.']
literal_scope = save(directory / 'ROOT_SCOPED_INPUT_READER_V1.md', chr(10).join(lines) + chr(10))

cohort = 'repeat_named_full_independent_v1'
independent = json.loads((BASE / cohort / 'manifest.json').read_text(encoding='utf-8'))
glossary = next(r for r in independent['rows'] if r['id'] == 'expanded_train:574329')
assert glossary['role'] == 'context_controls'
reader, registry = fixed_reader('glossary_574329', cohort, [glossary])
directory = BASE / 'agents/context_controls' / cohort
payload = (ROOT / glossary['original']['path']).read_bytes()
assert sha(payload) == glossary['original']['sha256']
base = directory / 'expanded_train_574329_primary_original_base_v1.txt'
work = directory / 'expanded_train_574329_primary_working_v1.txt'
for path in (base, work):
    with path.open('xb') as stream:
        stream.write(payload)
alignment_path = AUDIT / 'GLOSSARY_574329_PRIMARY_DEFINITION_ALIGNMENT_V2.json'
alignment = json.loads(alignment_path.read_text(encoding='utf-8'))
assert alignment['counts'] == {'EXACT_PRIMARY_HEADWORD_RESTORATION_CANDIDATE': 182, 'HEADING_ALREADY_PRESENT': 34}
parts = []
candidates = [r for r in alignment['rows'] if r['status'] == 'EXACT_PRIMARY_HEADWORD_RESTORATION_CANDIDATE']
for number, offset in enumerate(range(0, len(candidates), 20), 1):
    lines = ['# 발행처의 정확 정의 대조 표제 ' + str(number), '',
        '이 표제만 대응 원문 정의 앞에 넣는 복원을 검토한다. 정의 문장은 바꾸지 않는다. 원문 줄번호는 편집 전 번호다.', '']
    for row in candidates[offset:offset + 20]:
        lines += ['## ' + row['heading'],
            '원문 정의 시작: 줄 ' + str(row['original_line']) + ', 문자범위 ' + str(row['original_definition_span']),
            '원문 정의 식별 앞부분: ' + row['original_definition_prefix'],
            '발행처: ' + row['source_url'], '']
    pin = save(directory / ('ROOT_GLOSSARY_PRIMARY_LABELS_' + str(number).zfill(2) + '_V1.md'), chr(10).join(lines) + chr(10))
    parts.append(pin)
scope_lines = ['# 574329의 근거 있는 표제 복원', '',
    '기존 독립 TASK016의 유일한 미결이다. 현재 birth TASK를 마감한 뒤 이 중재를 수행하고, 이어 기존 birth 다음 TASK부터110까지 재개한다.',
    '총괄이 실제 발행처를 찾아 원문 정의와 공백만 무시한 전문 일치를 대조했다. 발행처 표제182개를 아래 지정 MD로 제공한다. 기존 표제34개는 중복 삽입하지 않는다.',
    '발행처: https://news.masterworksfineart.com/2017/11/07/art-dictionary',
    '이것은 캐시의 출처 계보 복구나 전기/미술사 전체의 사실 검증이 아니다. sourcekind UNKNOWN은 유지한다.',
    'Read more 링크는 발행처에 추가된 UI이며 원문 정의에 없으므로 넣지 않는다. 원래 COUTERPROOF 등 철자는 임의 교정하지 않는다.',
    '입력 전문 읽기는 아래 단일 ID 고정 reader만 허용한다. 이 MD·지정 표제 MD·자기 기존 TASK016/START/리뷰·sidecar와 자기 base/working/diff의 literal 읽기만 추가 허용한다.',
    '도구 코드/registry/외부웹/다른Python/검색/다른역할·세션은 읽거나 실행하지 않는다.',
    '`/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B ' + str(ROOT / reader['path']) +
        ' --source-id expanded_train:574329 --packet 1 --piece 1`',
    '27개2000~6000문자 패킷은 원문→기존 선택→전체diff의 연속이다. 각 packet의 pieces를 순서대로 다 읽으며 source_packet_sequence_complete와 실제논리END를 확인한다. 호출 max_output_tokens8000 이상.',
    '총괄은 원문 바이트 그대로 base와 미선택 working을 복사했다. 아직 정제 본문이 아니며 생성된 라벨/문장도 없다.',
    'base: ' + str(base), 'working: ' + str(work),
    '원문 전체가 working에 있으므로 실제 TXT 정제와 표제 삽입은 Luna가 apply_patch Update File로 수행한다. 첫 리뷰에 참조되기 전의 working만 편집할 수 있고, 리뷰 저장 뒤에는 동결하여 새 버전을 만든다.',
    '182개의 일치 정의는 문맥을 확인해 정확 원래 정의 앞에 실제 표제를 넣어 살린다. 여러 줄 정의·번호·인용·수량·단위·조건을 유지한다. 동일 MEZZOTINT의 서로 다른 두 정의를 중복이라고 합치지 않는다.',
    'BACK TO TOP 같은 탐색 UI와 원문 결손 의존 조각은 원형 sidecar와 함께 분리하며 완결된 정의/인쇄술 예시는 보존한다. 근거 없는 표제·설명·번역은 만들지 않는다.',
    '각 지정 표제 MD는 다음 경로다. 원문 줄은 삽입 후 이동하므로 정의 앞부분과 문맥으로 정확 위치를 확인한다.']
scope_lines += ['- ' + str(ROOT / pin['path']) for pin in parts]
scope_lines += ['', '실제 전체 TXT와 별도 원형 hold MD를 만든 뒤 기존 TASK016의 다른4행도 유지한 새 review_016_vN.md에 정확 output basename과 구체 근거를 기록한다.',
    '똑같은 candidate를 복제해 수정으로 세지 않는다. 파일명 충돌은 기존 파일을 보존하고 새 버전을 선택한다. 이 건 뒤 원래 birth 배정을 계속한다.']
scope = save(directory / 'ROOT_GLOSSARY_PRIMARY_RECOVERY_V1.md', chr(10).join(scope_lines) + chr(10))
receipt = dict(status='FIXED_READERS_AND_UNCHANGED_BASES_ONLY_NOT_CLEANED_TEXT',
    literal=dict(unique_sources=len(literal_rows), reader=literal_reader, registry=literal_registry, scope=literal_scope),
    glossary=dict(id=glossary['id'], reader=reader, registry=registry, scope=scope, label_scopes=parts,
        original=glossary['original'], unchanged_base=dict(path=str(base.relative_to(ROOT)), sha256=sha(payload)),
        unselected_working=dict(path=str(work.relative_to(ROOT)), initial_sha256=sha(payload))),
    producer_sha256=sha(Path(__file__).read_bytes()), training_authorized=False, goal_complete=False)
save(AUDIT / 'CONTROLS_LITERAL_AND_GLOSSARY_INPUT_SCOPE_V1.json', json.dumps(receipt, ensure_ascii=False, indent=2) + chr(10))
print(json.dumps(dict(literal_sources=len(literal_rows), glossary_sources=1, restoration_labels=182,
    cleaned_texts_written_by_root=0), ensure_ascii=False))
