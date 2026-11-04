"""Verify a single dependent-condition removal and its original-source hold."""
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
from exact_manifest_review_row_binding_v1 import load_parser

contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = json.loads(read(contract_path))
assert pins[str(contract_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
manifest = json.loads(read(BASE / 'remaining_field_title_page_008_counter_v1/manifest.json'))
source = next(row for row in manifest['rows'] if row['id'] == 'expanded_train:134299')
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
original_bytes = read(ROOT / source['original']['path'])
assert hashlib.sha256(original_bytes).hexdigest().upper() == 'D57F7BD0544FA14C50EA8F6A19CAB85073AB3BDB1E172C896EF3F8A59290E6D7'
original = original_bytes.decode('utf-8')
directory = BASE / 'agents/context_hangul/remaining_field_title_page_008_counter_v1'
before = read(directory / 'expanded_train_134299_task012_v2.txt')
path = directory / 'expanded_train_134299_task012_v3.txt'
after = read(path)
assert hashlib.sha256(before).hexdigest().upper() == '434E051C58090DFB0A2012BBD5670C33CEFA1C91AD1C10BC520787C42E5F35AF'
assert hashlib.sha256(after).hexdigest().upper() == '82772D53D924DE5744800581484E283CDCFF4C11F7E2F6BD7BDA6A3039F76033'
removed = ('운동상수와 푸아송 괄호\n'
           '만약 어떤 동역학적 물리량이 운동상수, 즉 보존되는 물리량이라면 물리량은 시간에 대한 직접적인 함수가 아니며 해밀토니안과 물리량의 푸아송 괄호가 0이 되어야 한다.\n').encode('utf-8')
assert before.count(removed) == 1 and before.replace(removed, b'', 1) == after
assert len(after.decode('utf-8')) == 369
hold_path = directory / 'hold_134299_task012_v4.md'
note = read(hold_path).decode('utf-8')
read(directory / 'hold_134299_task012_v3.md')
blocks = re.findall(r'```text\n(.*?)\n```', note, re.S)
start = original.index('운동상수와 푸아송 괄호')
end = original.index('물리량의 시간적 변화', start)
expected_quote = original[start:end].rstrip('\n')
assert expected_quote in blocks
assert '맨 첫 번째 방정식을 연쇄법칙' in expected_quote
resolve, parse, _ = load_parser()
old_review = {resolve(row['cells'][0]): row for row in parse(read(directory / 'review_012.md'))}
new_review_path = directory / 'review_012_v2.md'
amendment = {resolve(row['cells'][0]): row for row in parse(read(new_review_path))}
assert len(old_review) == 5 and set(amendment) == {source['id']}
effective = dict(old_review, **amendment)
assert len(effective) == 5
assert all(effective[ident]['raw'] == old_review[ident]['raw'] for ident in old_review if ident != source['id'])
assert amendment[source['id']]['cells'][3] in {path.name, str(path)}
assert hold_path.name in amendment[source['id']]['raw']
for retained in ['푸아송 다양체', '푸아송 대수', '문희태(2006)', '서울대학교출판부', '317-9쪽.']:
    assert retained.encode('utf-8') in after and retained in original
read(reused)
read(Path(__file__).resolve())
result = dict(status='ONE_134299_DEPENDENT_CONDITION_BLOCK_AND_RAW_HOLD_VERIFIED',
              id=source['id'], original=source['original'],
              body=dict(path=str(path.relative_to(ROOT)), sha256=pins[str(path.relative_to(ROOT))]),
              review=dict(path=str(new_review_path.relative_to(ROOT)),
                          sha256=pins[str(new_review_path.relative_to(ROOT))]),
              standalone_review_rows=1, original_review_rows=5,
              effective_review_rows=5, effective_other_review_rows_unchanged=4,
              one_row_amendment_requires_original_review=True,
              outside_body_bytes_unchanged=True, complete_original_condition_and_proof_quote_preserved=True,
              no_new_formula_or_counterexample_authored=True,
              actual_root_full_original_read='b8e454',
              actual_root_full_new_body_diff_and_sidecar_review_read='2471f3',
              input_pins=pins, new_root_or_cache_adoptions=0,
              specific_followup_pending=0, whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT_134299_CONDITION_FOLLOWUP_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], effective_review_rows=5,
                     outside_bytes_unchanged=True, remaining_this_scope=0, root_adopted=0), ensure_ascii=False))
