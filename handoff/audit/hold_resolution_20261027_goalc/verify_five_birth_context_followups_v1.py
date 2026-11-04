"""Close five scoped birth followups and verify two review-path-only repairs."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}
reused = AUDIT / 'verify_two_birth_followups_810478_95554_v1.py'
nodes = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name == 'read']
assert len(nodes) == 1
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(reused), 'exec'), globals())
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser, FROZEN

contract = json.loads(read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'))
assert pins[str((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').relative_to(ROOT))] == (
    'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF')
manifest = json.loads(read(BASE / 'birth_root11_independent_v1/manifest.json'))
ids = {121135, 79984, 81208, 139681, 355073}
sources = {int(row['id'].split(':')[1]): row for row in manifest['rows']
           if int(row['id'].split(':')[1]) in ids}
assert set(sources) == ids
for source in sources.values():
    assert source['id'] not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
originals = {}
for number, source in sources.items():
    data = read(ROOT / source['original']['path'])
    assert hashlib.sha256(data).hexdigest().upper() == source['original']['sha256']
    originals[number] = data
resolve, parse, parser_sha = load_parser()
pins[str(FROZEN.relative_to(ROOT))] = parser_sha
controls = BASE / 'agents/context_controls/birth_root11_independent_v1'
latin = BASE / 'agents/context_latin/birth_root11_independent_v1'
results = []


def replace_once(data, old, new):
    old_bytes, new_bytes = old.encode('utf-8'), new.encode('utf-8')
    assert data.count(old_bytes) == 1
    return data.replace(old_bytes, new_bytes, 1)


def check_review(number, directory, older, newer, expected_output):
    before = {resolve(row['cells'][0]): row for row in parse(read(directory / older))}
    after = {resolve(row['cells'][0]): row for row in parse(read(directory / newer))}
    ident = 'expanded_train:' + str(number)
    assert len(before) == len(after) == 5 and set(before) == set(after)
    assert all(before[key]['raw'] == after[key]['raw'] for key in before if key != ident)
    output = after[ident]['cells'][3]
    assert output in {str(expected_output), expected_output.name}
    return dict(path=str((directory / newer).relative_to(ROOT)),
                sha256=pins[str((directory / newer).relative_to(ROOT))],
                exact_review_row=after[ident]['raw'], other_review_rows_unchanged=4)


candidate = read(ROOT / sources[121135]['candidate']['path'])
assert hashlib.sha256(candidate).hexdigest().upper() == '7D3926036D69A5DFB5EE6B2110B8EB73D425E8748683EBF81D735A4749B903CE'
review = check_review(121135, controls, 'review_004.md', 'review_004_v2.md',
                      ROOT / sources[121135]['candidate']['path'])
assert '1839와 1840 출생연도 주장을 모두 분리' in review['exact_review_row']
assert '경력 연혁의 1840년 9월 7일은 월일·출생지와 함께 보존' not in review['exact_review_row']
results.append(dict(id='expanded_train:121135', body_unchanged=True, review=review,
                    body=sources[121135]['candidate'], change='REVIEW_DESCRIPTION_ONLY'))

candidate79984 = read(ROOT / sources[79984]['candidate']['path'])
assert hashlib.sha256(candidate79984).hexdigest().upper() == '238E5CD56FE0CC31466F4DA9548620040F7B11B756F3B0FD38352B0AFB07CB4B'
path79984 = controls / 'expanded_train_79984_reviewed_task229_v1.txt'
body79984 = read(path79984)
assert replace_once(candidate79984, '~ 1995년 3월 30일', '1995년 3월 30일 사망') == body79984
assert hashlib.sha256(body79984).hexdigest().upper() == '6C8C1011AB9A37D02271FAFFAD208E9E71488F38EC1C05B271E5240F245C6EAF'
read(controls / 'hold_79984_task229_v1.md')
results.append(dict(id='expanded_train:79984', change='ONE_DEATH_ROLE_LABEL', outside_bytes_unchanged=True,
                    body=dict(path=str(path79984.relative_to(ROOT)), sha256=pins[str(path79984.relative_to(ROOT))]),
                    review=check_review(79984, controls, 'review_229.md', 'review_229_v2.md', path79984)))

v1 = read(controls / 'expanded_train_81208_reviewed_task233_v1.txt')
v2 = read(controls / 'expanded_train_81208_reviewed_task233_v2.txt')
path81208 = controls / 'expanded_train_81208_reviewed_task233_v3.txt'
v3 = read(path81208)
assert hashlib.sha256(v1).hexdigest().upper() == '27F961B06D03546F2113FC62239CDD44B0D29A24407A2D6651D9807806CAB9C0'
assert replace_once(v1, '음력 8월 21일 ~ 1955년 6월 1일',
                    '음력 8월 21일 출생, 1955년 6월 1일 사망') == v2
start = v2.index('강씨; 강동기'.encode('utf-8'))
end = v2.index('민족운동과 교육활동'.encode('utf-8'), start)
block = v2[start:end]
assert len(block.decode('utf-8')) == 494 and len(block) == 1170
assert v2[:start] + v2[end:] == v3 and block in originals[81208]
assert hashlib.sha256(v3).hexdigest().upper() == '13220B33D658FD293F7180A93C0742B5E6BB4C75B2D85F117421336944CF14F4'
old_hold = read(controls / 'hold_81208_task233_v1.md')
new_hold = read(controls / 'hold_81208_task233_v2.md')
assert new_hold.startswith(old_hold)
quote_lines = []
for line in new_hold.decode('utf-8').splitlines():
    if line == '>':
        quote_lines.append('')
    elif line.startswith('> '):
        quote_lines.append(line[2:])
assert '\n'.join(quote_lines).rstrip('\n') == block.decode('utf-8').rstrip('\n')
read(controls / 'review_233_v2.md')
results.append(dict(id='expanded_train:81208', change='ONE_DATE_ROLE_LABEL_AND_ONE_UNATTRIBUTED_BLOCK',
                    outside_bytes_unchanged=True, raw_block_characters=494, raw_block_bytes=1170,
                    entire_raw_block_preserved=True, prior_hold_prefix_unchanged=True,
                    body=dict(path=str(path81208.relative_to(ROOT)), sha256=pins[str(path81208.relative_to(ROOT))]),
                    review=check_review(81208, controls, 'review_233.md', 'review_233_v3.md', path81208)))

for number, task, old_sha, final_sha in [
        (139681, 86, 'A7F5D220E0642FEAC5987AF1433A21D1CA2A56020B80A4471CCDBF0EDB6C01FD',
         '4215154A162E61F687C7E2DD56D90C6A9772ADF0051832E3573C24E5393FC98D'),
        (355073, 139, 'FD03BBA90A94654E7B53D1769E230B44B7D7CA7E28A0D8235F5DE6A90F621A67',
         'C5B8822425EFA1231F85197A79DD49846107F8D6D4127A13A516FDF4DCD47019')]:
    before = read(latin / f'reviewed_{number}_task{task:03}_v1.txt')
    path = latin / f'reviewed_{number}_task{task:03}_v2.txt'
    after = read(path)
    assert hashlib.sha256(before).hexdigest().upper() == old_sha
    assert hashlib.sha256(after).hexdigest().upper() == final_sha
    if number == 139681:
        expected = replace_once(before, 'ᠭᠠᠮᠠᠯᠠ, , 또는', 'ᠭᠠᠮᠠᠯᠠ, 또는')
        expected = replace_once(expected, '키릴 문자:Гамала, ~ 1302년', '키릴 문자:Гамала, 사망: 1302년')
        source_date = '1302년 2월 8일(음력 1월 10일) 혹은 2월 2일(음력 1월 4일)'
    else:
        source_date = '1488년 8월 20일(음력 7월 14일)'
        expected = replace_once(before, '순숙공주(順淑公主)', '순숙공주(順淑公主, 사망: ' + source_date + ')')
    assert expected == after and source_date.encode('utf-8') in originals[number]
    assert not before.endswith(b'\n') and not after.endswith(b'\n')
    prior_hold = read(latin / f'hold_{number}_task{task:03}_v1.md')
    revised_hold = read(latin / f'hold_{number}_task{task:03}_v2.md')
    assert revised_hold.startswith(prior_hold)
    results.append(dict(id='expanded_train:' + str(number), change='SCOPED_LEAD_ONLY',
                        outside_bytes_unchanged=True, terminal_non_newline_EOF_preserved=True,
                        prior_hold_prefix_unchanged=True, original_calendar_claim_preserved_not_converted=True,
                        body=dict(path=str(path.relative_to(ROOT)), sha256=final_sha),
                        review=check_review(number, latin, f'review_{task:03}.md', f'review_{task:03}_v2.md', path)))

field_manifest = json.loads(read(BASE / 'remaining_field_title_page_001_counter_v1/manifest.json'))
field_sources = {row['id']: row for row in field_manifest['rows']}
directory = BASE / 'agents/context_latin/remaining_field_title_page_001_counter_v1'
metadata_repairs = []


def no_link_markup(text):
    return re.sub(r'\[([^\]\n]+)\]\([^()\s]+\)', lambda match: match[1], text).replace('`', '')


for task in (1, 2):
    older = parse(read(directory / f'review_{task:03}.md'))
    newer_path = directory / f'review_{task:03}_v2.md'
    newer = parse(read(newer_path))
    assert len(older) == len(newer) == 5
    old_by_id = {resolve(row['cells'][0]): row for row in older}
    new_by_id = {resolve(row['cells'][0]): row for row in newer}
    assert len(old_by_id) == len(new_by_id) == 5 and set(old_by_id) == set(new_by_id)
    for ident, previous in old_by_id.items():
        source = field_sources[ident]
        assert source['role'] == 'context_latin'
        assert ident not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
        current = new_by_id[ident]
        assert previous['cells'][:3] == current['cells'][:3]
        assert no_link_markup(previous['cells'][4]) == no_link_markup(current['cells'][4])
        target = Path(current['cells'][3])
        assert target.is_absolute() and target.parent == directory
        assert target.name == previous['cells'][3]
        assert re.search(r'_' + ident.split(':')[1] + r'_', target.name)
        payload = read(target)
        links = re.findall(r'\[([^\]\n]+)\]\(([^()\s]+)\)', current['cells'][4])
        assert links
        for label, link in links:
            sidecar = Path(link)
            assert sidecar.parent == directory and sidecar.name == label
            read(sidecar)
        metadata_repairs.append(dict(id=ident, task=task, body_sha256=hashlib.sha256(payload).hexdigest().upper(),
                                     exact_output=str(target.relative_to(ROOT)), newer_review=str(newer_path.relative_to(ROOT))))

prior = json.loads(read(AUDIT / 'ROOT11_BIRTH_FLAG_CONTEXT_ADJUDICATION_V1.json'))
assert {row['id'] for row in results} == set(prior['pending_ids'])
assert len(results) == 5 and len(metadata_repairs) == 10
read(reused)
read(Path(__file__).resolve())
read(AUDIT / 'exact_manifest_review_row_binding_v1.py')
result = dict(status='FIVE_BIRTH_CONTEXT_FOLLOWUPS_AND_TEN_METADATA_ONLY_REVIEW_PATH_REPAIRS_VERIFIED',
              birth_results=results, birth_unique_sources=5, birth_new_bodies=4,
              source_scoped_followups_pending=0, other_birth_review_rows_unchanged=20,
              field_metadata_only_review_repairs=metadata_repairs, field_new_bodies=0,
              actual_root_full_new_body_reads=['892883', 'e68622'],
              actual_root_final_block_diff_and_sidecar_read='2d9697',
              actual_root_final_review_and_EOF_read='8d4166',
              premature_draft_observation=dict(chunk='e68622', id='expanded_train:355073',
                  sha256='61B7E5DF883C86ECA6CD52A4C764BC6E145268B467A587768BAA3409F7084E20',
                  extra_terminal_LF=1, adopted=False, final_non_newline_EOF_verified=True),
              original_or_existing_files_overwritten_by_root=False, input_pins=pins,
              automatic_flag_waivers=0, new_root_or_cache_adoptions=0,
              independent_whole_2707_semantic_pass_claimed=False, goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT11_FIVE_CONTEXT_FOLLOWUPS_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], birth_sources=5, new_birth_bodies=4,
                     field_metadata_repairs=10, remaining_this_scope=0, root_adopted=0), ensure_ascii=False))
