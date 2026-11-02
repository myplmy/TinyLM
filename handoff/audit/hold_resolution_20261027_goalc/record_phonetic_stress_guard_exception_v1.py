"""Record one exact stress-transcription false code match; never waive a class."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_policy as original_guard
from scripts import p106b_hold_resolution_policy_v26 as policy

diagnostic = inv.cache.read(AUDIT / 'EXACT_COHORT_BODY_DIAGNOSTICS_V4.json')
row = next(r for r in diagnostic['rows'] if r['id'] == 'expanded_train:1291499' and
           r['cohort'] == 'repeat_named_full_independent_v1')
raw_pin, body_pin = row['original'], row['body']
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
assert row['id'] not in contract['restricted_ids']
assert raw_pin['sha256'] not in contract['restricted_hashes']
for pin in (raw_pin, body_pin):
    assert inv.file_sha(ROOT / pin['path']) == pin['sha256']
raw = (ROOT / raw_pin['path']).read_text(encoding='utf-8')
body = (ROOT / body_pin['path']).read_text(encoding='utf-8')
before, opened = original_guard.real_code_blocks(raw)
after, new_opened = original_guard.real_code_blocks(body)
assert before == after == [] and not opened and not new_opened
quote = chr(96)
pattern = quote + '[^' + quote + chr(10) + ']+' + quote
left, right = list(re.finditer(pattern, raw)), list(re.finditer(pattern, body))
changes = [op for op in difflib.SequenceMatcher(None, [m.group() for m in left],
    [m.group() for m in right], autojunk=False).get_opcodes() if op[0] != 'equal']
assert len(left) == 74 and len(right) == 73 and len(changes) == 1
tag, lo, hi, start, end = changes[0]
assert tag == 'delete' and hi == lo + 1 and start == end
match = left[lo]
line_number = raw.count(chr(10), 0, match.start()) + 1
line = raw.splitlines()[line_number - 1]
assert line_number == 99 and 'palatalized άδεια' in line and 'three syllables' in line
sidecar = inv.BASE / 'agents/context_controls/repeat_named_full_independent_v1/hold_1291499_v2.md'
assert line in sidecar.read_text(encoding='utf-8')
assert not policy.code_preserved(raw, body) and policy.unicode_examples_preserved(raw, body)
result = dict(status='EXACT_PAIR_PHONETIC_STRESS_MATCH_ADJUDICATED_NOT_A_GENERAL_CODE_WAIVER',
    id=row['id'], original=raw_pin, body=body_pin, review=row['review'],
    false_code_match=dict(original_span=list(match.span()), original_line=line_number,
        text=match.group(), actual_context=line),
    unchanged_real_fenced_code_blocks=0, unchanged_other_inline_matches=73,
    full_held_source_line=dict(path=str(sidecar.relative_to(ROOT)), sha256=inv.file_sha(sidecar)),
    reason='逆따옴표 두 개는 그리스어 전사의 강세 표기다. 그 사이 문자열은 실행 코드가 아니라 누락된 예제행/소실 기호에 의존하는 발음 대조 문장이다. 원형 문장은 sidecar에 보존되어 있으며 나머지73개 정규식 매치와 실제 표의 셀·축은 그대로다.',
    root_approved=True, applies_only_to_original_and_body_sha256=True,
    production_guard_changed=False, cache_admitted=False, goal_complete=False, training_authorized=False,
    producer_sha256=inv.file_sha(Path(__file__)))
# Use ordinary Korean in the authored reason; the source examples remain exact.
result['reason'] = result['reason'].replace('逆따옴표', '역따옴표')
inv.write_json(AUDIT / 'EXACT_PHONETIC_STRESS_CODE_EXCEPTION_1291499_V1.json', result)
print(json.dumps(dict(id=row['id'], exact_pair_approved=True, other_inline_matches_unchanged=73,
    production_guard_changed=False, cache_admitted=False), ensure_ascii=False))
