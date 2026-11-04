"""Verify one ASCII marker removal and preserve unselected UTF-8 draft history."""
from pathlib import Path
import ast
import hashlib
import json
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
from exact_manifest_review_row_binding_v1 import load_parser

contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = json.loads(read(contract_path))
assert pins[str(contract_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
manifest = json.loads(read(BASE / 'birth_root11_independent_v1/manifest.json'))
source = next(row for row in manifest['rows'] if row['id'] == 'expanded_train:139681')
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
original = read(ROOT / source['original']['path'])
assert hashlib.sha256(original).hexdigest().upper() == source['original']['sha256']
directory = BASE / 'agents/context_latin/birth_root11_independent_v1'
old_path = directory / 'reviewed_139681_task086_v2.txt'
new_path = directory / 'reviewed_139681_task086_v5.txt'
before, after = read(old_path), read(new_path)
assert hashlib.sha256(before).hexdigest().upper() == '4215154A162E61F687C7E2DD56D90C6A9772ADF0051832E3573C24E5393FC98D'
assert hashlib.sha256(after).hexdigest().upper() == '70B794D881E267DBE166E75C27860CFDB69AC55804211C184B6E28AC5A852F3E'
old = '1311년 원 인종 즉위 후| 헌무(獻武)의 시호'.encode('utf-8')
new = '1311년 원 인종 즉위 후 헌무(獻武)의 시호'.encode('utf-8')
assert before.count(old) == 1 and old in original
assert before.replace(old, new, 1) == after and len(before) - len(after) == 1
assert len(after.decode('utf-8')) == 7325
assert not before.endswith(b'\n') and not after.endswith(b'\n')
old_hold = read(directory / 'hold_139681_task086_v2.md')
new_hold = read(directory / 'hold_139681_task086_v3.md')
assert new_hold.startswith(old_hold)
assert old.decode('utf-8') in new_hold.decode('utf-8') and new.decode('utf-8') in new_hold.decode('utf-8')
resolve, parse, _ = load_parser()
older = {resolve(row['cells'][0]): row for row in parse(read(directory / 'review_086_v2.md'))}
newer = {resolve(row['cells'][0]): row for row in parse(read(directory / 'review_086_v5.md'))}
assert len(older) == len(newer) == 5 and set(older) == set(newer)
assert all(older[ident]['raw'] == newer[ident]['raw'] for ident in older if ident != source['id'])
assert newer[source['id']]['cells'][3] == str(new_path)
assert 'hold_139681_task086_v3.md' in newer[source['id']]['raw']
unselected = []
for version, expected_sha, expected_utf8 in [
        (3, '283603294FF12EBCD8A3F50D53A9AD0A6B8242E0F9DC8ED2AA03061CCA0A0BAC', True),
        (4, '117164DB6EFEDFB1EC34345183D73CFC787DFABFB775AF7F343B2A1C3034EAD2', False)]:
    path = directory / f'reviewed_139681_task086_v{version}.txt'
    payload = read(path)
    assert hashlib.sha256(payload).hexdigest().upper() == expected_sha
    try:
        payload.decode('utf-8')
        valid_utf8 = True
    except UnicodeDecodeError:
        valid_utf8 = False
    assert valid_utf8 == expected_utf8
    unselected.append(dict(path=str(path.relative_to(ROOT)), sha256=expected_sha,
                           bytes=len(payload), valid_utf8=valid_utf8,
                           ends_LF=payload.endswith(b'\n'), selected=False))
read(reused)
read(Path(__file__).resolve())
result = dict(status='ONE_139681_ORPHAN_PIPE_REMOVAL_UTF8_AND_ALL_OTHER_BYTES_VERIFIED',
              id=source['id'], original=source['original'],
              prior_body=dict(path=str(old_path.relative_to(ROOT)), sha256=pins[str(old_path.relative_to(ROOT))]),
              body=dict(path=str(new_path.relative_to(ROOT)), sha256=pins[str(new_path.relative_to(ROOT))]),
              review=dict(path=str((directory / 'review_086_v5.md').relative_to(ROOT)),
                          sha256=pins[str((directory / 'review_086_v5.md').relative_to(ROOT))]),
              removed_bytes=1, outside_bytes_unchanged=True, non_newline_EOF_preserved=True,
              other_review_rows_unchanged=4, previous_hold_prefix_unchanged=True,
              prior_actual_root_full_body_read='e68622',
              actual_root_final_full_diff_and_sidecar_review_read='eb47c5',
              preserved_unselected_drafts=unselected,
              input_pins=pins, new_root_or_cache_adoptions=0,
              specific_followup_pending=0, whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT_139681_ORPHAN_PIPE_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], removed_bytes=1, other_review_rows_unchanged=4,
                     preserved_unselected_drafts=2, remaining_this_scope=0, root_adopted=0), ensure_ascii=False))
