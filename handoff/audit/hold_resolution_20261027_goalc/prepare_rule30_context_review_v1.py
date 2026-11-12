"""Prepare six exact independent context assignments; reuse program final bodies."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from scripts import p106b_hold_resolution_policy_v30 as policy

guard.activate()
ids = ['expanded_train:5957', 'expanded_train:6722', 'expanded_train:87620',
       'expanded_train:584703', 'expanded_train:691012', 'expanded_train:1101770']
cohort = 'remaining_rule30_independent_context_v1'
proof_path = AUDIT/'RULE30_EVENT_METADATA_LITERAL_INDEPENDENT_VERIFIED_V1.json'
census_path = AUDIT/'RULE30_EVENT_METADATA_CENSUS_V1.json'
proof = json.loads(proof_path.read_bytes())
census = json.loads(census_path.read_bytes())
good = {row['id']:row for row in proof['rows'] if row['eligible_narrow_literal_delta']}
assert set(ids) <= set(good)
metadata = {}
for shard in census['metadata_manifest']['shards']:
    path = ROOT/census['metadata_directory']/shard['path']
    assert guard.inv.file_sha(path) == shard['sha256']
    for line in path.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row['id'] in ids:
            metadata[row['id']] = row
rows = []
for ident in ids:
    source_pin = metadata[ident]['source_manifest']
    manifest_path = ROOT/source_pin['path']
    assert guard.inv.file_sha(manifest_path) == source_pin['sha256']
    source, = [row for row in json.loads(manifest_path.read_bytes())['rows'] if row['id'] == ident]
    guard.require_payload_context(source)
    original_path = ROOT/source['original']['path']
    raw = original_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == source['original']['sha256']
    proposed = policy.propose(dict(source, text=raw.decode('utf-8'), previous_holds=[]))
    assert proposed['decision'] == 'EDIT'
    text = proposed.get('candidate', proposed['text'])
    digest = guard.inv.sha(text)
    assert digest == good[ident]['proposed_body_sha256']
    path = guard.inv.BASE/'rule30_literal_final_bodies_v1'/digest[:2]/(digest+'.txt')
    if path.exists():
        assert not path.is_symlink() and guard.inv.file_sha(path) == digest
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(text.encode('utf-8'))
    row = dict(source, role='historical_review', candidate=dict(path=str(path.relative_to(ROOT)),sha256=digest),
        reading_parts=[], program_derived_candidate=True, program_policy='p106b_hold_resolution_policy_v30',
        independent_context_review_not_yet_performed=True, root_approved=False, cache_admitted=False)
    rows.append(row)
directory = guard.inv.BASE/cohort
assert not directory.exists()
directory.mkdir()
inputs = {str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in [proof_path,census_path,
    guard.CONTRACT,AUDIT/'AUTHORED_LITERAL_BATCH_F3_F4_V1.md']}
manifest = dict(status='EXACT_SIX_CONTEXT_REVIEW_ASSIGNMENTS_NOT_ADMISSION', rows=rows,
    assignments={'historical_review':dict(ids=ids)}, input_pins=inputs,
    source_code_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
        [Path(__file__),ROOT/'scripts/p106b_hold_resolution_policy_v30.py']},
    cache_admitted=False,goal_complete=False,training_authorized=False)
manifest_path = directory/'manifest.json'
guard.inv.write_json(manifest_path,manifest)
scope6 = json.loads((AUDIT/'LOSSLESS_REVIEW_READER_SCOPE_V6.json').read_bytes())
scope = dict(schema=scope6['schema'], contract=dict(path=str(guard.CONTRACT.relative_to(ROOT)),
    sha256=guard.EXPECTED,bytes=guard.CONTRACT.stat().st_size),core=scope6['core'],
    transport_protocol=scope6['transport_protocol'],roles={'historical_review':{cohort:dict(
        path=str(manifest_path.relative_to(ROOT)),sha256=guard.inv.file_sha(manifest_path),bytes=manifest_path.stat().st_size)}},
    root_or_cache_admission=False,output_writes=0)
scope_path = AUDIT/'RULE30_CONTEXT_LOSSLESS_SCOPE_V1.json'
assert not scope_path.exists()
guard.inv.write_json(scope_path,scope)
review_dir = guard.inv.BASE/'agents/historical_review'/cohort
review_dir.mkdir(parents=True,exist_ok=False)
assignment = '''# rule30 独立 문맥 판독 배정

- 역할: historical_review. 입력은 manifest의 정확한 여섯 원형/프로그램 후보와 고정 reader만.
- 허용: 지정 원형·후보 전문/전체 diff/EOF 판독, 이 디렉터리의 새 review_001.md(5행),
  review_002.md(1행), 필요한 새 TXT/MD만. 원형·프로그램 후보·기존 결과 변경/삭제 금지.
- 코드·시험·모델·GPU·Git·규약 수정 금지. 프로그램 후보를 정답으로 전제하지 않는다.
- 실제 차 있는 값·인용·학술어·조건·부정·불확실성, 전체 문맥 독립성과 빈 끝 표제/metadata
  경계를 검토한다. 결손이 남으면 그 사례는 HOLD하며 문제가 있는 부분을 구체적으로 기록한다.
- 출력표: ID | 판정 | 실제 판독 범위 | 정확 출력 | 구체 근거. 적합한 후보는
  ACCEPT_CANDIDATE와 reader 헤더 accept_output_absolute 한 경로. HOLD 출력은 —.
- 원형/패킷 복사본을 만들지 않는다. 마지막에 여섯 건을 묶어서 한 번 보고하고 기존 field 커서로 복귀.
- 실제 직접 읽은 수는 여섯 건만 계수한다. 이 배정은 전체 rule30 자료의 개별 완독 주장이 아니다.
'''
with (review_dir/'ASSIGNMENT_V1.md').open('x',encoding='utf-8') as stream:
    stream.write(assignment)
guard.assert_no_protected_opens()
print(json.dumps(dict(cohort=cohort,ids=ids,scope_sha256=guard.inv.file_sha(scope_path),
    scope_bytes=scope_path.stat().st_size,final_bodies=6,original_or_packet_copies=0)))
