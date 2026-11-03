"""Join current immutable author evidence; keep every new choice unadmitted."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from guarded_reviewed_cache_v3 import hold_cases

old_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V10.json'
receipt_path = AUDIT / 'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V14.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
output = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW1.json'
old, receipt, contract = map(inv.cache.read, [old_path, receipt_path, contract_path])
inv.require(old['source_ids'] == 4381 and old['unresolved_sources'] == 0, 'prior root set differs')
blocked_ids, blocked_hashes = set(contract['restricted_ids']), set(contract['restricted_hashes'])
input_pins = {str(p.relative_to(ROOT)):inv.file_sha(p) for p in [old_path, receipt_path,
    contract_path, Path(__file__), AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD37_V1.json',
    AUDIT / 'ROOT_PRIOR_BODY_WITHDRAWAL_1255247_V1.json']}
snapshots, manifests = {}, {}
for item in receipt['rows']:
    inv.require(item['process_exit_code'] == 0, 'unsuccessful snapshot collection')
    pin = item['snapshot']
    inv.require(inv.file_sha(ROOT / pin['path']) == pin['sha256'], 'snapshot bytes changed')
    input_pins[pin['path']] = pin['sha256']
    snapshot = inv.cache.read(ROOT / pin['path'])
    sources = {}
    for shard in snapshot['shards']:
        inv.require(inv.file_sha(ROOT / shard['path']) == shard['sha256'], 'snapshot shard changed')
        sources.update({r['id']:r for r in inv.cache.read(ROOT / shard['path'])})
    snapshots[item['cohort']] = sources
    path = inv.BASE / item['cohort'] / 'manifest.json'
    inv.require(snapshot['input_pins'][str(path.relative_to(ROOT))] == inv.file_sha(path), 'source manifest changed')
    input_pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
    manifests[item['cohort']] = {r['id']:r for r in inv.cache.read(path)['rows']}

rows = {}
for prior in old['rows']:
    choice = dict(prior['selected'])
    rows[prior['id']] = dict(id=prior['id'], original_text_sha256=prior['original_text_sha256'],
        selected=choice, root_approved=True, cache_admitted=False,
        status='PRIOR_ROOT10_APPROVAL_PRESERVED_PENDING_NEW_CACHE',
        prior_root_selection_id=prior['id'], prior_guard_closure=prior['guard_closure'])
inv.require(len(rows) == 4381, 'prior source identity repeated')
cases = hold_cases()
cases_by_id = {r['id']:r for r in cases.values()}
pending = []
provenance = []
changed_prior = []
new_counts = Counter()


def body_choice(source, review, cohort):
    inv.require(not review.get('error') and review.get('body'), 'body review is absent or invalid')
    inv.require(source['id'] not in blocked_ids and source['original']['sha256'] not in blocked_hashes,
        'new choice contains a protected source')
    for pin in [source['original'], source['candidate'], review['review']]:
        inv.require(inv.file_sha(ROOT / pin['path']) == pin['sha256'], 'selected evidence changed')
    inv.require(inv.file_sha(ROOT / review['body']) == review['clean_text_sha256'], 'selected body changed')
    return dict(cohort=cohort, decision='KEEP' if review['clean_text_sha256'] == source['original']['sha256'] else 'EDIT',
        body=review['body'], clean_text_sha256=review['clean_text_sha256'], original=source['original'],
        review=review['review'], author_output=review.get('author_output'), compare_source=None,
        reason='LUNA_FULL_SOURCE_CONTEXT_REVIEW_SEE_EXACT_PINNED_REVIEW_AND_SIDECAR',
        root_approved=False)


def hold_choice(source, case):
    inv.require(case['root_approved'] is True and case['reviewed'] is True
        and case['decision'] == 'HOLD' and case['original']['sha256'] == source['original']['sha256'],
        'reviewed HOLD source differs')
    return dict(cohort='EXACT_ROOT_REVIEWED_NONADMISSION', decision='HOLD', body=None,
        clean_text_sha256=None, original=source['original'], review=case.get('author_first_review'),
        author_output=None, compare_source=None, reason=case['reason'], root_approved=True,
        content_reviewed=True, hold_review_evidence=case['authority_pin'])


cohorts = ['repeat_named_full_independent_v1', 'remaining_birth_full_counter_v1', 'remaining_literal_full_counter_v1']
for cohort in cohorts:
    for ident, review in snapshots[cohort].items():
        source = manifests[cohort][ident]
        if not review.get('body'):
            if ident in cases_by_id:
                choice = hold_choice(source, cases_by_id[ident])
            else:
                pending.append(dict(id=ident, cohort=cohort, status=review['status'],
                    decision=review.get('decision'), review=review.get('review')))
                continue
        else:
            choice = body_choice(source, review, cohort)
        inv.require(ident not in rows, 'new cohort overlaps an existing source')
        if cohort == 'repeat_named_full_independent_v1':
            first = snapshots['repeat_named_roles_counter_v2'][ident]
            inv.require(first.get('body') and not first.get('error'), 'first repeat review missing')
            inv.require(first['role'] != review['role'], 'repeat second reading is by the same author role')
            provenance.append(dict(id=ident, first_review=first['review'], first_body=first['body'],
                first_clean_text_sha256=first['clean_text_sha256'], independent_review=review['review'],
                independent_role=review['role'], selected_clean_text_sha256=choice['clean_text_sha256']))
        rows[ident] = dict(id=ident, original_text_sha256=source['original']['sha256'], selected=choice,
            root_approved=choice['decision'] == 'HOLD', cache_admitted=False,
            status='NEW_EXACT_SOURCE_CHOICE_PENDING_RUNTIME_AND_ROOT_CLOSURE',
            occurrences=source['occurrences'])
        new_counts[cohort] += 1

for ident, review in snapshots['root10_quantity_recheck_v1'].items():
    inv.require(ident in rows and ident in {r['id'] for r in old['rows']}, 'quantity recheck is outside prior set')
    source = manifests['root10_quantity_recheck_v1'][ident]
    prior = rows[ident]
    if ident in cases_by_id:
        choice = hold_choice(source, cases_by_id[ident])
    else:
        choice = body_choice(source, review, 'root10_quantity_recheck_v1')
    inv.require(prior['original_text_sha256'] == source['original']['sha256'], 'rechecked original differs')
    if choice['decision'] == prior['selected']['decision'] and choice.get('clean_text_sha256') == prior['selected'].get('clean_text_sha256'):
        continue
    changed_prior.append(dict(id=ident, before_decision=prior['selected']['decision'],
        before_clean_text_sha256=prior['selected'].get('clean_text_sha256'), after=choice))
    rows[ident] = dict(id=ident, original_text_sha256=source['original']['sha256'], selected=choice,
        root_approved=choice['decision'] == 'HOLD', cache_admitted=False,
        status='PRIOR_ROOT10_CHOICE_REPLACED_PENDING_RUNTIME_AND_ROOT_CLOSURE', prior_root_selection_id=ident)

inv.require(len(provenance) == 732, 'whole independent repeat evidence required')
inv.require(len(rows) == len({r['original_text_sha256'] for r in rows.values()}), 'source SHA overlaps across selections')
inv.require({r['id'] for r in rows.values() if r['selected']['decision'] == 'HOLD'} == set(cases_by_id),
    'every reviewed non-admission and the prior withdrawal must be represented')
result = dict(status='EXACT_SOURCE_BODY_PREVIEW_NOT_ROOT_ADMISSION', rows=sorted(rows.values(), key=lambda r:r['id']),
    source_ids=len(rows), selected_sources=len(rows), counts=dict(Counter(r['selected']['decision'] for r in rows.values())),
    unresolved_sources=len(pending), unresolved=pending, new_selected_by_cohort=dict(new_counts),
    changed_prior_choices=changed_prior, independent_repeat_provenance=provenance,
    root_guard_closure_required=True, runtime_and_numeric_guard_closure='NOT_RUN_ON_THIS_PREVIEW',
    restricted_parent_full_bodies_opened=False, prior_root10_choices=4381,
    input_pins=input_pins, cache_admitted=0, goal_complete=False, training_authorized=False)
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')
inv.require(len(payload)<20_000_000,'preview must be split before writing')
with output.open('xb') as stream:stream.write(payload)
print(json.dumps(dict(source_ids=len(rows),bytes=len(payload),counts=result['counts'],
    new_selected_by_cohort=dict(new_counts),pending_reviews=len(pending),
    changed_prior_choices=len(changed_prior),cache_admitted=0)))
