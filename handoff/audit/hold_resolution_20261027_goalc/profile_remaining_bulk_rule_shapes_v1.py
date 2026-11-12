"""Inspect existing current HOLD classes once; write small counts/pins, never bodies."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from selection_metadata_store_v1 import SelectionStore
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v28 as policy
from scripts import p106b_hold_resolution_repeat_context_v1 as repeat

activate()
guard = checked_contract()
blocked_ids = set(guard['restricted_ids']) | set(guard['trusted_metadata'])
blocked_hashes = set(guard['restricted_hashes'])
pins = {}
started = time.monotonic()


def read(path, expected=None):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    assert expected is None or digest == expected, str(path)
    pins[str(path.relative_to(ROOT))] = digest
    return json.loads(raw)


opaque = read(AUDIT/'OPAQUE_UNADOPTED_HOLD_ROOT32_ROSTER23_V1.json',
              '87EB0550B9F11BC3EC4E6CBF6B75673A8785633B0522762F7E4277849292EFEF')
selection = SelectionStore(AUDIT).read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V35.json',
    'DF7AA25488D2F8694588E98F866DCA61FDA66A62E8D8BB0395159B0287559BC3')
remaining = set(opaque['hold_hashes']) - {row['original_text_sha256'] for row in selection['rows']
                                        if row['selected']['decision'] != 'HOLD'}
assert len(remaining) == 66383
targets = {'MAIN_BODY_REPETITION_REQUIRES_CONTEXT', 'APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT'}
totals, weights, distribution = Counter(), Counter(), Counter()
examples = defaultdict(list)
seen = set()
for group in ['remaining_field_title_readers_v1', 'remaining_other_types_readers_v1']:
    index = read(inv.BASE/group/'complete.json')
    for page in index['pages']:
        manifest = read(ROOT/page['path'], page['sha256'])
        for row in manifest['rows']:
            source_hash = row['original_text_sha256']
            if source_hash not in remaining:
                continue
            assert source_hash not in seen
            seen.add(source_hash)
            reasons = set(row.get('remaining_reasons', []))
            specific = reasons - {'FIELD_OR_TITLE_ROLE_REQUIRES_INDEPENDENT_SOURCE_READING',
                                  'OTHER_TYPES_REQUIRE_INDEPENDENT_SOURCE_READING'}
            if len(specific) != 1 or not specific <= targets:
                continue
            reason = next(iter(specific))
            totals[reason] += 1
            weights[reason] += row['occurrences']
            if row['id'] in blocked_ids or any(row[k]['sha256'] in blocked_hashes for k in ['original','candidate']):
                distribution[reason+':protected_not_opened'] += 1
                continue
            pin = row['original']
            path = (ROOT/pin['path']).resolve()
            assert path.is_relative_to(inv.BASE) and not path.is_symlink()
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest().upper() == pin['sha256'] == source_hash
            source = raw.decode('utf-8')
            label = reason
            detail = {}
            if reason == 'MAIN_BODY_REPETITION_REQUIRES_CONTEXT':
                lines = [line.strip() for line in policy.plain_text(source).splitlines() if line.strip()]
                count = Counter(line for line in lines if len(line) >= 6 and
                                policy.v1.normalize_heading(line) not in policy.v1.LABELS)
                repeated = {line:n for line,n in count.items() if n > 1}
                proof = repeat.prove(source)
                if proof:
                    shape = 'EXISTING_PROVED_DISTINCT_HEADERS_OR_BYLINES'
                elif not repeated:
                    shape = 'NO_REPEAT_AFTER_PROTECTED_CONTEXT_MASK'
                elif all(len(line) <= 80 and not re.search(r'[.!?。！？]$',line) for line in repeated):
                    shape = 'ONLY_SHORT_NON_SENTENCE_REPEATS'
                elif any(a == b and a in repeated for a,b in zip(lines,lines[1:])):
                    shape = 'AT_LEAST_ONE_ADJACENT_REPEATED_VALUE'
                else:
                    shape = 'SEPARATED_LONG_OR_SENTENCE_REPEATS'
                detail = dict(repeated_line_kinds=len(repeated), max_repeated_characters=max(map(len,repeated),default=0))
            else:
                blocks = [m for m in policy.BLOCK.finditer(source) if m[0].strip()]
                suffix = blocks[-1][0] if blocks else ''
                intro = policy.intro(source)
                shape = ('TYPED_INTRO_WITH_SHORT_SUFFIX' if intro and len(suffix) <= 1000
                         else 'TYPED_INTRO_WITH_LONG_SUFFIX' if intro else 'NO_EXISTING_TYPED_INTRO')
                detail = dict(last_block_characters=len(suffix), last_block_lines=len(suffix.splitlines()),
                              existing_metadata_boundary_proved=bool(policy.separate_metadata_suffix(source)[2]))
            key = label+':'+shape
            distribution[key] += 1
            bucket = key+(':+4KB' if len(raw) > 4000 else ':at_most_4KB')
            if len(examples[bucket]) < 3:
                examples[bucket].append(dict(id=row['id'], original=pin, candidate=row['candidate'],
                    occurrences=row['occurrences'], original_bytes=len(raw), source_class=shape, detail=detail))
        assert_no_protected_opens()

assert len(remaining-seen) == 879
result = dict(status='CURRENT_ROOT35_SINGLE_REASON_SHAPES_NOT_ADMISSION',
              expected_current_unique=len(remaining), queued_remaining_unique=len(seen), outside_queues=879,
              target_unique=dict(totals), target_positions=dict(weights), source_shapes=dict(distribution),
              examples=dict(examples), input_pins=pins, elapsed_seconds=time.monotonic()-started,
              source_or_candidate_modified=False, corpus_payload_copies_written=0,
              automatic_admissions=0, goal_complete=False, training_authorized=False)
out = AUDIT/'REMAINING_BULK_RULE_SHAPES_ROOT35_V1.json'
with out.open('xb') as stream:
    stream.write((json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode())
print(json.dumps({k:v for k,v in result.items() if k not in {'examples','input_pins'}},ensure_ascii=False))
