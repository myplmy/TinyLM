"""Verify the delegated one-cell repair and four unchanged review rows."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


guard_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V2.json'
assert sha(guard_path) == 'E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B'
guard = json.loads(guard_path.read_bytes())
manifest = json.loads((BASE/'remaining_literal_full_counter_v1/manifest.json').read_bytes())
source, = [x for x in manifest['rows'] if x['id'] == 'expanded_train:1357468']
assert source['id'] not in guard['restricted_ids']
assert all(source[k]['sha256'] not in guard['restricted_hashes'] for k in ('original','candidate'))
directory = BASE/'agents/context_latin/remaining_literal_full_counter_v1'
old = directory/'reviewed_1357468_v1.txt'
new = directory/'reviewed_1357468_sample_cell_followup_20261104_v1.txt'
assert sha(old) == '9B00F53FEBE1AAD72CA261D5770A235E418E13FBFB9C05E26647F718C70617DF'
before = b'| 5 | R | 8 | 10 | 8 | 6 | 6 | 7 | 7 | 3 | 5 | 8 | 4 | 8 | 6 | 6 | 7 | 11 |'
after = b'| 5 | R | 8 | 10 | 8 | 6 | 6 | 7 | 7 | 3 | 5 | 8 | 4 | 8 | 6 | 6 | 7 | 7 |'
x, y = old.read_bytes(), new.read_bytes()
assert x.count(before) == 1 and x.replace(before, after, 1) == y


def other_rows(path):
    return [line for line in path.read_text(encoding='utf-8').splitlines()
            if line.startswith('| expanded_train:') and
            not line.startswith('| expanded_train:1357468 |')]


assert len(other_rows(directory/'review_022.md')) == 4
assert other_rows(directory/'review_022.md') == other_rows(directory/'review_022_v2.md')
assert x.endswith(bytes([10])) == y.endswith(bytes([10]))
y.decode('utf-8')
proof = AUDIT/'LITERAL_1357468_SAMPLE_TABLE_SOURCE_COMPARISON_V1.json'
json.loads(proof.read_bytes())
pin = lambda path: dict(path=str(path.relative_to(ROOT)), sha256=sha(path))
receipt = dict(status='EXACT_ONE_CELL_SOURCE_SUPPORTED_CORRECTION_VERIFIED',
    id=source['id'], original=source['original'], old_body=pin(old), new_body=pin(new),
    proof=pin(proof), review=pin(directory/'review_022_v2.md'),
    correction=pin(directory/'correction_1357468_sample_cell_followup_20261104_v1.md'),
    one_cell_only_11_to_7=True, other_four_review_rows_unchanged=True,
    UTF8_valid=True, EOF_unchanged=True, new_original_payload_reads=0,
    code_or_model_execution=0, root_training_body_authorship=0, new_first_review_credit=0,
    root_adopted=0, cache_admitted=0, goal_complete=False, training_authorized=False,
    input_pins={str(path.relative_to(ROOT)):sha(path) for path in (Path(__file__),guard_path)})
out = AUDIT/'LITERAL_1357468_SAMPLE_CELL_FOLLOWUP_VERIFIED_V1.json'
with out.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(''.join(difflib.unified_diff(x.decode().splitlines(True),y.decode().splitlines(True))))
print(json.dumps(dict(receipt=pin(out), new_body_sha256=sha(new))))
