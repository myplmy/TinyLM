"""Verify every original line, exact publisher heading, and removed UI occurrence."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy

alignment_path = AUDIT / 'GLOSSARY_574329_PRIMARY_DEFINITION_ALIGNMENT_V2.json'
alignment = inv.cache.read(alignment_path)
snapshot_path = inv.BASE / 'repeat_named_full_independent_v1_snapshots/v12/complete.json'
snapshot = inv.cache.read(snapshot_path)
chosen = []
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT / shard['path']) == shard['sha256']
    chosen += [row for row in inv.cache.read(ROOT / shard['path']) if row['id'] == alignment['id']]
assert len(chosen) == 1
chosen = chosen[0]
assert chosen.get('body') and not chosen.get('error') and chosen['decision'] == 'EDIT_TEXT'
raw_pin, body = alignment['original'], ROOT / chosen['body']
assert inv.file_sha(ROOT / raw_pin['path']) == raw_pin['sha256']
assert inv.file_sha(body) == chosen['clean_text_sha256']
raw = (ROOT / raw_pin['path']).read_text(encoding='utf-8')
clean = body.read_text(encoding='utf-8')
original_lines = raw.splitlines()
inserts = {}
for row in alignment['rows']:
    if row['status'] != 'EXACT_PRIMARY_HEADWORD_RESTORATION_CANDIDATE':
        continue
    index = row['original_line'] - 1
    assert index not in inserts and row['exact_normalized_definition_matches'] == 1
    inserts[index] = row['heading']
assert len(inserts) == 182
assert sum(line.strip() == 'BACK TO TOP' for line in original_lines) == 23
assert original_lines[0].startswith('|An abridged glossary')
expected = []
removed = []
for index, line in enumerate(original_lines):
    if index in inserts:
        expected.append(inserts[index])
    if line.strip() == 'BACK TO TOP':
        removed.append(dict(original_line=index + 1, text=line, reason='PAGE_NAVIGATION_ONLY'))
        continue
    expected.append(line[1:] if index == 0 else line)
normalize = lambda lines: [line for line in lines if line.strip()]
assert normalize(expected) == normalize(clean.splitlines()), 'definition/heading/order differs'
assert clean.startswith('An abridged glossary')
assert policy.code_preserved(raw, clean)
assert policy.unicode_examples_preserved(raw, clean)
assert policy.semantic_style_preserved(raw, clean)
assert not inv.corpus.MEMOS.search(clean)
result = dict(status='EXACT_SOURCE_AND_PUBLISHER_HEADING_RESTORATION_VERIFIED_NOT_CACHE_ADMISSION',
    id=alignment['id'], original=raw_pin, body=dict(path=chosen['body'], sha256=chosen['clean_text_sha256']),
    author_output=chosen['author_output'], independent_review=chosen['review'],
    alignment=dict(path=str(alignment_path.relative_to(ROOT)), sha256=inv.file_sha(alignment_path)),
    snapshot=dict(path=str(snapshot_path.relative_to(ROOT)), sha256=inv.file_sha(snapshot_path)),
    counts=dict(restored_exact_primary_headings=182, original_headings_preserved=34,
        removed_navigation_lines=23, removed_isolated_intro_delimiter=1,
        other_nonblank_source_line_changes=0), removed_ui=removed,
    source_url=alignment['source_url'], root_approved=True,
    approval_scope='Only this original/body SHA pair and the supplied exact heading alignments.',
    source_kind='UNKNOWN_MIXED_NATIVE_CACHE', root_authored_cleaned_prose=False,
    production_policy_changed=False, cache_admitted=False, goal_complete=False, training_authorized=False,
    producer_sha256=inv.file_sha(Path(__file__)))
inv.write_json(AUDIT / 'GLOSSARY_574329_RESTORATION_VERIFIED_V1.json', result)
with (AUDIT / 'GLOSSARY_574329_RESTORATION_VERIFIED_V1.md').open('x', encoding='utf-8') as stream:
    stream.write('# 판화 용어집574329 표제 복원 검증' + chr(10) * 2)
    stream.write('Luna가 실제 정제 TXT를 작성했고 총괄이 원문 전체 줄과 표제 대응을 검산했다. '
        '발행처 정의와 일치한 표제182개를 복원하고 기존34표제·모든 정의 문구·순서를 보존했다. '
        '탐색 UI23줄과 고립 도입 구분자 한 문자 외에 원문의 비빈 줄 변경은0이다. '
        'code·Unicode·style·본문 검수 메모 검사는 통과했다. 아직 새 캐시에 채택한 수량은0이다.' + chr(10) * 2)
    stream.write('발행처: [Art Dictionary](https://news.masterworksfineart.com/2017/11/07/art-dictionary). '
        '문자열 일치는 캐시의 출처 메타데이터 복구나 미술사 전체 사실검증이 아니다.' + chr(10))
print(json.dumps(dict(id=alignment['id'], counts=result['counts'], exact_pair_root_approved=True,
    cache_admitted=False), ensure_ascii=False))
