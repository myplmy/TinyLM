"""Bind existing saved evidence before scheduling duplicate reads; never waive flags."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    assert not path.is_symlink() and path.resolve().is_relative_to(BASE.resolve() if
        path.is_relative_to(BASE) else AUDIT.resolve())
    data = path.read_bytes()
    assert len(data) < 20_000_000
    pins[str(path.relative_to(ROOT))] = sha(data)
    return json.loads(data)


def verify(pin, archive=False):
    path = ROOT / (pin['archive'] if archive and pin.get('archive') else pin['path'])
    assert not path.is_symlink() and (path.resolve().is_relative_to(BASE.resolve()) or
                                     path.resolve().is_relative_to(AUDIT.resolve()))
    data = path.read_bytes()
    assert 0 < len(data) < 20_000_000 and sha(data) == pin['sha256']
    return data


def role_from_review(pin):
    parts = Path(pin['path']).parts
    marker = list(BASE.relative_to(ROOT).parts) + ['agents']
    assert list(parts[:len(marker)]) == marker
    return parts[len(marker)]


root_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json'
root = read(root_path)
assert pins[str(root_path.relative_to(ROOT))] == '624AE91E66B4104F864E389B001A58E2C67C2D509D78F7E348DABC4FAD30A152'
guard_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
guards = {r['id']: r for r in read(guard_path)['records'] if r.get('ordered_source_deletion') is False}
assert len(guards) == 585
closure = read(AUDIT / 'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json')
assert pins[str(guard_path.relative_to(ROOT))] == closure['input_pins'][str(guard_path.relative_to(ROOT))]
direct = {r['id'] for r in read(AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V12.json')['rows']}
repeat = {r['id'] for r in read(AUDIT / 'EXISTING_REPEAT_ORDERED_FLAG_REVIEW_BINDINGS_V1.json')['rows']}
snapshot_path = BASE / 'birth_root11_independent_v1_snapshots/v12/complete.json'
snapshot = read(snapshot_path)
birth = {r['id'] for p in snapshot['shards'] for r in json.loads(verify(p)) if r.get('review')} & set(guards)
known = direct | repeat | birth
assert len(known) == 293
selected = {r['id']: r['selected'] for r in root['rows']}
contract = read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
manifests = {}
rows, successful = [], set()
for ident in sorted(set(guards) - known):
    current = selected[ident]
    cohort = current.get('cohort', 'unknown')
    result = dict(id=ident, selected_cohort=cohort, current_body_sha256=current['clean_text_sha256'],
                  original_text_sha256=guards[ident]['original_text_sha256'],
                  selected_review=current.get('review'), root_semantic_waiver=False)
    # Apply BOTH protection identities before even hashing assigned text or review bytes.
    if ident in contract['restricted_ids'] or result['original_text_sha256'] in contract['restricted_hashes']:
        result['status'] = 'RESTRICTED_METADATA_ONLY_NOT_OPENED'
        rows.append(result)
        continue
    assert current['clean_text_sha256'] == guards[ident]['clean_text_sha256']
    manifest_path = BASE / cohort / 'manifest.json' if re.fullmatch(r'[A-Za-z0-9_]+', cohort) else None
    if manifest_path is None or not manifest_path.is_file():
        result['status'] = 'NO_CANONICAL_COHORT_MANIFEST_IN_THIS_AUDIT'
        rows.append(result)
        continue
    if cohort not in manifests:
        manifests[cohort] = {r['id']: r for r in read(manifest_path)['rows']}
    source = manifests[cohort].get(ident)
    result['manifest'] = dict(path=str(manifest_path.relative_to(ROOT)),
                              sha256=pins[str(manifest_path.relative_to(ROOT))])
    result['manifest_directly_pinned_by_root11'] = root['input_pins'].get(result['manifest']['path']) == result['manifest']['sha256']
    if source is None:
        result['status'] = 'SOURCE_ABSENT_FROM_CURRENT_COHORT_MANIFEST'
        rows.append(result)
        continue
    previous = source.get('previous_role')
    avoided = source.get('avoided_current_body_author_roles', [])
    assigned = source.get('role')
    distinct = bool(assigned and ((previous and assigned != previous) or
        (avoided and assigned not in avoided and source.get('assigned_role_had_current_body_review') is False)))
    result.update(assigned_role=assigned, previous_role=previous,
                  avoided_current_body_author_roles=avoided,
                  distinct_role_assignment_metadata=distinct,
                  candidate=source.get('candidate'))
    if not distinct:
        result['status'] = 'MANIFEST_FOUND_DISTINCT_ROLE_OWNERSHIP_NOT_PROVEN_HERE'
        rows.append(result)
        continue
    try:
        assert source['original']['sha256'] == result['original_text_sha256']
        assert current['review'] and role_from_review(current['review']) == assigned
        review = verify(current['review'], archive=True).decode('utf-8')
        matches = [line for line in review.splitlines() if line.startswith('|') and
                   line.split('|')[1].strip().strip('`') == ident]
        assert len(matches) == 1, 'exact full-ID review row is not uniquely bound'
        verify(source['original'])
        verify(source['candidate'])
        verify(dict(path=current['body'], sha256=current['clean_text_sha256']))
        if previous and source.get('review'):
            verify(source['review'], archive=True)
            if previous != 'root':
                assert role_from_review(source['review']) == previous
        result.update(status='EXACT_CURRENT_BODY_AND_SAVED_REVIEW_WITH_DISTINCT_ASSIGNMENT_METADATA',
                      reviewer_role=assigned, original=source['original'],
                      current_body=dict(path=current['body'], sha256=current['clean_text_sha256']),
                      input_equals_current_body=source['candidate']['sha256'] == current['clean_text_sha256'],
                      exact_saved_review_row=matches[0],
                      historical_emission_time_proven=False, independent_semantic_pass_granted=False)
        successful.add(ident)
    except (AssertionError, KeyError, OSError, ValueError) as error:
        result.update(status='EXISTING_BINDING_REQUIRES_FURTHER_AUDIT', error=str(error))
    rows.append(result)
assert len(rows) == 292
result = dict(status='EXISTING_FLAG_PROVENANCE_LINK_AUDIT_NOT_NEW_SEMANTIC_REVIEW',
    ordered_flag_sources=585, prior_three_scope_linked_sources=len(known), audited_remaining_sources=len(rows),
    additional_exact_saved_review_links=len(successful),
    counts=dict(Counter(r['status'] for r in rows)),
    combined_record_scopes=sorted(known | successful),
    flags_without_a_link_in_these_audited_scopes=len(set(guards) - known - successful),
    rows=rows, input_pins=pins, new_original_text_semantic_reads=0,
    root_or_cache_adoptions=0, automatic_flag_waivers=0, protected_body_reads=0,
    whole_goal_complete=False,
    limits=['Saved review rows, current byte hashes and distinct role assignment metadata are linked.',
            'This does not verify historical input delivery, actual comprehension, or original ownership chains beyond recorded pins.',
            'Unlinked records may have other valid reviews; no duplicate reading task is automatically scheduled.',
            'Missing explicit identity or ownership remains unresolved here. No alias or weak substring fallback is used.'])
target = AUDIT / 'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V1.json'
payload = (json.dumps(result, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
assert len(payload) < 20_000_000
with target.open('xb') as stream:
    stream.write(payload)
print(json.dumps({k:v for k,v in result.items() if isinstance(v,(str,int,bool))}, ensure_ascii=False))
