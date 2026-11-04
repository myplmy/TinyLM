"""Close one exact punctuation flag without changing any training text."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v26 as policy

sha=lambda value:hashlib.sha256(value).hexdigest().upper()
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
raw=guard_path.read_bytes()
assert sha(raw)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=json.loads(raw)
key='expanded_train:1060968'
source_sha='D503A0B5E47711C7DEF15671A02E36E3934A1020F85EDC9D3F6429E4A561F497'
body_sha='DEE28132E18422327B4243CE150F9FD4E01DD7DEC1074B7EC77A0FA17940449F'
assert key not in guard['restricted_ids']
assert source_sha not in guard['restricted_hashes'] and body_sha not in guard['restricted_hashes']
manifest_path=BASE/'root12_independent_admission_counter_v1/manifest.json'
raw=manifest_path.read_bytes()
assert sha(raw)=='A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'
source=next(row for row in json.loads(raw)['rows'] if row['id']==key)
assert source['original']['sha256']==source_sha
original_path=ROOT/source['original']['path']
body_path=BASE/'exact_cohort_rendered_v1/DE'/f'{body_sha}.txt'
original=original_path.read_bytes();body=body_path.read_bytes()
assert sha(original)==source_sha and sha(body)==body_sha
original=original.decode('utf-8');body=body.decode('utf-8')
assert not policy.ordered_deletion(original,body)
before='fopen()is insecure, so I’ll test the replacement function'
after='fopen()is insecure.'
assert original.count(before)==1
# Whitespace joins are ignored by the original ordered-character guard.
# Only the comma-to-period at the held unfinished clause needs exact closure.
normalized=original.replace(before,after)
assert policy.ordered_deletion(normalized,body)
assert 'fopen() is insecure.' in body
receipt=dict(status='ONE_EXACT_SOURCE_BODY_ORDER_FLAG_CLOSED_BY_CONTEXT_AND_SUBSEQUENCE',
    id=key,original=source['original'],body=dict(path=str(body_path.relative_to(ROOT)),sha256=body_sha),
    root_approved=True,root_full_original_context_read_previously=True,
    root_full_exact_diff_rechecked=True,raw_ordered_deletion=False,
    ordered_after_single_exact_punctuation_normalization=True,
    exact_normalization=dict(before=before,after=after,occurrences=1),
    rationale='The held unfinished test-intention clause leaves the original Windows-thinks-insecure claim. Joining lik/e and adding a space change no nonwhitespace order; a period closes that existing clause. No API, encoding, author uncertainty or fact is invented.',
    guard_waiver=False,training_TXT_written=0,scope='ONLY_THE_TWO_SHA256_VALUES_ABOVE',
    input_pins={str(guard_path.relative_to(ROOT)):sha(guard_path.read_bytes()),
        str(manifest_path.relative_to(ROOT)):sha(raw),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__).read_bytes())},
    goal_complete=False,training_authorized=False)
out=AUDIT/'ROOT_1060968_EXACT_ORDER_CLOSURE_V1.json'
with out.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps(dict(status=receipt['status'],path=str(out.relative_to(ROOT)),sha256=sha(out.read_bytes()))))
