"""Compare one actual unblocked frame in RAM and reject blocked metadata only."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import batched_lossless_review_entry_v2 as new
import active_guard_v6_preflight_v1 as guard

guard.activate()
old = new.frozen_batch()
entry = old.frozen_entry()
metadata, scope, core = old.setup(ROOT, entry)
context = core.resolve_assignment(ROOT, scope, 'legacy_review',
    'remaining_field_title_page_015_counter_v1', 'expanded_train:365119', metadata.pinned)
guard.require_payload_context(context)
_, views, pieces = old.batch(core, ROOT, scope, 'legacy_review', context['cohort'],
    context['source_id'], 1, 1, metadata.pinned)
shortcut = str(ROOT/'tmp/hold-g-field-lossless-batch-v1')
actual = subprocess.run(['bash', shortcut, '15', '365119', '1', '1'], capture_output=True, check=True)
head, body = actual.stdout.split(b'\nSOURCE_DATA_VIEW_BEGIN\n', 1)
info = json.loads(head.split(b' ', 1)[1])
length = info['range'][1] - info['range'][0]
assert body[:length] == pieces[0]['text'].encode('utf-8')
assert info['cumulative_guard']['sha256'] == guard.EXPECTED
blocked = subprocess.run(['bash', shortcut, '15', '360211', '1', '1'], capture_output=True)
assert blocked.returncode != 0 and not blocked.stdout
assert b'restricted source identity' in blocked.stderr
guard.assert_no_protected_opens()
result = dict(status='GUARD6_EXACT_FRAME_AND_PRE_PAYLOAD_METADATA_REJECTION_VERIFIED',
    source_id=context['source_id'], frame_part=1, frame_bytes=length, exact_old_frame_match=True,
    blocked_id='expanded_train:360211', blocked_before_payload_and_stdout=True,
    guard_sha256=guard.EXPECTED, restricted_payload_reads=0, payload_copies=0,
    input_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
        [Path(__file__), AUDIT/'active_guard_v6_preflight_v1.py',
         AUDIT/'batched_lossless_review_entry_v2.py', AUDIT/'GUARD6_METADATA_TESTS_V1.log']},
    goal_complete=False, training_authorized=False)
out = AUDIT/'GUARD6_BATCH_ACTUAL_FRAME_AND_METADATA_REJECTION_V1.json'
assert not out.exists()
with out.open('x', encoding='utf-8') as stream:
    stream.write(json.dumps(result, indent=2) + '\n')
print(json.dumps({k:v for k,v in result.items() if k != 'input_pins'}))
