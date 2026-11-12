"""Check the exact author edit; prepare one editable final with a pinned preimage."""
from pathlib import Path
import json
import re
import hashlib
import sys

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens

activate();guard=checked_contract()


def write(path,value):
    with path.open('xb') as stream:stream.write((json.dumps(value,ensure_ascii=False,indent=2)+chr(10)).encode())


prepared=json.loads((AUDIT/'LATIN_259718_EXACT_EDITABLE_PREFILL_V1.json').read_bytes())
pin=prepared['original'];assert pin['sha256'] not in guard['restricted_hashes']
raw=(ROOT/pin['path']).read_bytes();assert hashlib.sha256(raw).hexdigest().upper()==pin['sha256']
source=raw.decode('utf-8');body_path=ROOT/prepared['editable_output'];edited=body_path.read_bytes();body=edited.decode('utf-8')
expected=re.sub(r'[ \t]*\([ \t]*,[ \t]*\)','',source,count=1)
assert source.count('(, )')==1 and body.rstrip('\r\n')==expected.rstrip('\r\n')
receipt=dict(status='ONE_OPTIONAL_TITLE_ALIAS_AND_TERMINAL_LF_ONLY_INDEPENDENTLY_VERIFIED',
    source_id=prepared['source_id'],original=pin,
    final_body=dict(path=prepared['editable_output'],sha256=hashlib.sha256(edited).hexdigest().upper(),bytes=len(edited)),
    original_bytes=len(raw),other_populated_characters_changed=0,source_original_modified=False,
    semantic_edit_author='context_latin',root_prepared_only_exact_original_prefill=True,
    terminal_LF_added=True,root_approved=False,cache_admitted=False,goal_complete=False,training_authorized=False)
write(AUDIT/'LATIN_259718_AUTHOR_FINAL_DIFF_INDEPENDENT_VERIFIED_V1.json',receipt)
print(json.dumps(receipt,ensure_ascii=False))

manifest=json.loads((BASE/'remaining_field_title_page_012_counter_v1/manifest.json').read_bytes())
row,=[row for row in manifest['rows'] if row['id']=='expanded_train:263562']
assert row['role']=='context_latin' and row['id'] not in guard['restricted_ids']
assert all(row[key]['sha256'] not in guard['restricted_hashes'] for key in ['original','candidate'])
pin=row['candidate'];raw=(ROOT/pin['path']).read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()==pin['sha256'] and len(raw)<20_000_000
out=BASE/'agents/context_latin/remaining_field_title_page_012_counter_v1/expanded_train_263562_context_latin_task017_editable_prefill_20261113_v1.txt'
assert not out.exists() and not out.parent.is_symlink()
with out.open('xb') as stream:stream.write(raw)
assert out.read_bytes()==raw
assert_no_protected_opens()
receipt=dict(status='EXACT_PINNED_CANDIDATE_PREFILL_FOR_AUTHOR_EDIT_NOT_ADMISSION',source_id=row['id'],
    original=row['original'],prefill_source_candidate=pin,editable_output=str(out.relative_to(ROOT)),
    pre_edit_sha256=pin['sha256'],bytes=len(raw),pre_edit_bytes_recoverable_from_immutable_input=True,
    author_role='context_latin',one_exact_editable_prefill_authorized=True,semantic_edits_by_root=0,
    extra_intermediate_corpus_copies=0,review_completed=False,root_approved=False,cache_admitted=False)
write(AUDIT/'LATIN_263562_EXACT_EDITABLE_PREFILL_V1.json',receipt)
print(json.dumps(receipt,ensure_ascii=False))
