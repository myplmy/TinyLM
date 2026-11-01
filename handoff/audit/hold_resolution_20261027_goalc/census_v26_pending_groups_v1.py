"""Count unresolved rule combinations without reclassifying or admitting text."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
SOURCE = BASE / 'draft_proposals_v26_delta_v1'
report_path = SOURCE / 'complete.json'
receipt_path = AUDIT / 'DRAFT_V26_DELTA_EXECUTION_RECEIPT_V1.json'
report, receipt = inv.cache.read(report_path), inv.cache.read(receipt_path)
inv.require(receipt['completed_artifact']['sha256'] == inv.file_sha(report_path), 'verified26 identity changed')
inv.verify(SOURCE / 'unique', report['unique_manifest'])
counts, reasons, combinations = Counter(), Counter(), Counter()
examples = defaultdict(list)
birth_shapes = Counter()
started = time.monotonic()
for row in inv.cache.rows(SOURCE / 'unique', report['unique_manifest']):
    if row['decision'] != 'PENDING':
        continue
    counts.update(unique=1, occurrences=row['occurrences'])
    key = tuple(sorted(row['reasons']))
    combinations[key] += 1
    reasons.update(key)
    if len(examples[key]) < 3:
        examples[key].append(dict(id=row['id'], original_text_sha256=row['original_text_sha256']))
    if 'INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED' in key:
        candidate = row.get('diagnostic_candidate', '')
        first = candidate.split(chr(10) * 2, 1)[0]
        birth_fields = list(re.finditer(r'\([^()\r\n]*?([12][0-9]{3})년[ \t]*([0-9]{1,2})월[ \t]*([0-9]{1,2})일', first))
        categories = re.findall(r'(?m)^[ \t]*([12][0-9]{3})년[ \t]*출생[ \t]*$', candidate)
        uncertainty = bool(re.search(r'추정|논쟁|불명|미상|경(?:[ ,)]|$)|또는|[?？]|[0-9]년대', first))
        shape = ('ONE_TYPED_LEAD_BIRTH' if len(birth_fields) == 1 else 'OTHER_LEAD')
        shape += '/CATEGORY_' + str(min(len(categories), 2))
        shape += '/UNCERTAIN' if uncertainty else '/NO_EXPLICIT_UNCERTAINTY_IN_LEAD'
        shape += '/ONLY_BIRTH_REASON' if len(key) == 1 else '/OTHER_REASONS'
        birth_shapes[shape] += 1
inv.require(counts['unique'] == 77639 and counts['occurrences'] == 122534, 'remaining26 census does not conserve scope')
actual_occurrences = Counter()
inv.verify(SOURCE / 'occurrences', report['occurrence_manifest'])
for row in inv.cache.rows(SOURCE / 'occurrences', report['occurrence_manifest']):
    if row['resolution'] == 'PENDING':
        actual_occurrences.update(occurrences=1, input_ids=row['input_ids'])
inv.require(actual_occurrences['occurrences'] == counts['occurrences']
            and actual_occurrences['input_ids'] == report['occurrence_counts']['PENDING_input_ids'],
            'actual occurrence token counts differ')
counts['input_ids'] = actual_occurrences['input_ids']
result = dict(status='ALL_VERIFIED26_PENDING_REASON_COMBINATIONS_COUNTED_NOT_RESOLVED',
    counts=dict(counts), reasons=dict(reasons), birth_shapes=dict(birth_shapes),
    combinations=[dict(reasons=list(key), unique=count, examples=examples[key])
                  for key, count in combinations.most_common()],
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in [report_path, receipt_path, Path(__file__)]},
    native_source_freshly_decoded=False, body_changed=0, cache_admitted=0,
    goal_complete=False, training_authorized=False, seconds=time.monotonic()-started)
target = AUDIT / 'V26_PENDING_REASON_GROUP_CENSUS_V1.json'
inv.require(not target.exists(), 'new immutable reason census required')
inv.write_json(target, result)
print(json.dumps(dict(counts=result['counts'], reasons=result['reasons'], birth_shapes=result['birth_shapes'],
    top_combinations=result['combinations'][:20], seconds=result['seconds']),ensure_ascii=False))
