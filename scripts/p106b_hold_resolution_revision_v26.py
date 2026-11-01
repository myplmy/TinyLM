"""Inherit verified v25 and audit the entire pending set for a narrow v26 delta.

This is not a full native-source v26 rerun and never admits cache bodies.
Only the previously censused27 source pairs are freshly decoded here.
"""
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
import json
import os
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy
from scripts import p106b_hold_resolution_revision_v25 as previous

CODE = previous.CODE + ['scripts/p106b_hold_resolution_metadata_v2.py',
                        'scripts/p106b_hold_resolution_policy_v26.py',
                        'scripts/p106b_hold_resolution_revision_v26.py']
SENTINEL = 'RAW_SOURCE_NOT_LOADED_FOR_VERIFIED_V25_UNCHANGED_ROW'


class MetadataOnlyRow(dict):
    def __getitem__(self, key):
        if key == 'text':
            raise ValueError('v26 unexpectedly accessed a non-censused original')
        return super().__getitem__(key)


def frozen_value(row):
    value = dict(decision=row['decision'], text=SENTINEL, reasons=row['reasons'],
                 changes=row['changes'], rules=row['rules'])
    if 'diagnostic_candidate' in row:
        value['candidate'] = row['diagnostic_candidate']
    return value


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES='', TOKENIZERS_PARALLELISM='false', RAYON_NUM_THREADS='1',
                      OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    base = inv.BASE
    audit = ROOT / 'handoff/audit/hold_resolution_20261027_goalc'
    source = base / 'draft_proposals_v25'
    out = base / 'draft_proposals_v26_delta_v1'
    inv.require(not out.exists(), 'new immutable delta namespace required')
    old_path = source / 'complete.json'
    receipt_path = audit / 'DRAFT_V25_EXECUTION_RECEIPT_V2.json'
    census_path = base / 'ordinal_metadata_candidate_census_v26_v1/complete.json'
    pairs_path = base / 'ordinal_metadata_counter_v26_v1/manifest.json'
    old, receipt = inv.cache.read(old_path), inv.cache.read(receipt_path)
    census, pairs = inv.cache.read(census_path), inv.cache.read(pairs_path)
    inv.require(receipt['original_process_exit_code'] == 0
                and receipt['completed_artifact']['sha256'] == inv.file_sha(old_path),
                'the inherited full25 must have actual and independently verified closure')
    for name, expected in census['production_source_pins'].items():
        inv.require(inv.file_sha(ROOT / name) == expected, 'censused policy changed')
    for name, expected in pairs['source_code_pins'].items():
        inv.require(inv.file_sha(ROOT / name) == expected, 'native-pair proof code changed')
    for name, expected in old['lineage']['source_code_sha256'].items():
        inv.require(inv.file_sha(ROOT / name) == expected, 'inherited full25 production code changed')
    pins = {name: inv.file_sha(ROOT / name) for name in CODE}
    inv.require(len(pins) == 66, 'production source count differs')
    inv.verify(source / 'unique', old['unique_manifest'])
    inv.verify(source / 'occurrences', old['occurrence_manifest'])
    pair_map = {row['id']: row for row in pairs['rows']}
    inv.require(len(pair_map) == len(pairs['rows']) == 27, 'all27 source pairs required')
    lineage = dict(status='VERIFIED_V25_INHERITANCE_WITH_SOURCE_PROVEN_V26_DELTA_NOT_CACHE_ADMISSION',
        inherited_full_draft=dict(path=str(old_path.relative_to(ROOT)), sha256=inv.file_sha(old_path)),
        inherited_actual_and_independent_receipt=dict(path=str(receipt_path.relative_to(ROOT)), sha256=inv.file_sha(receipt_path)),
        source_code_sha256=pins, rules='PRESERVE_V25_ROWS_EXCEPT_THE_CENSUSED_V26_ORDINAL_EXTENSION',
        full_native_v26_rerun=False, raw_sources_freshly_decoded=27,
        nonmatch_eos_and_utf8_are_inherited_verified_v25_evidence=True, training_authorized=False)
    writer = inv.ShardWriter(out / 'unique', 'decisions', limit=19_999_999)
    counts, phases, pending, transitions = (Counter() for _ in range(4))
    decisions, seen, changed = {}, set(), set()
    started = time.monotonic()
    with ExitStack() as stack:
        reader = inv.OriginalReader(inv.cache.read(base / 'scope.json'), stack)
        for row in inv.cache.rows(source / 'unique', old['unique_manifest']):
            inv.require(row['original_text_sha256'] not in seen, 'inherited source repeats')
            seen.add(row['original_text_sha256'])
            result = row
            if row['id'] in pair_map:
                pair = pair_map[row['id']]
                inv.require(row['decision'] == 'PENDING' and row['original_text_sha256'] == pair['original']['sha256'],
                            'censused delta source identity differs')
                raw, complete, valid = reader.text(row)
                inv.require(complete and valid and inv.sha(raw) == row['original_text_sha256'], 'fresh source differs')
                input_row = dict(row, text=raw, complete_eos=complete, valid_utf8=valid)
                before = policy.previous.propose(input_row)
                inv.require(before['decision'] == row['decision'] and before['reasons'] == row['reasons']
                            and before['changes'] == row['changes']
                            and before.get('candidate', before['text']) == row['diagnostic_candidate'],
                            'fresh exact source failed to reproduce all inherited25 proposal fields')
                value = policy.propose(input_row)
                clean = value.get('candidate', value['text'])
                inv.require(value['decision'] == pair['candidate_decision']
                            and value['reasons'] == pair['candidate_reasons']
                            and inv.sha(clean) == pair['candidate']['sha256'], 'source-pair26 proof differs')
                result = dict(row, decision=value['decision'], reasons=value['reasons'], changes=value['changes'],
                    rules=policy.RULES, clean_text_sha256=inv.sha(clean) if value['decision'] in {'KEEP', 'EDIT'} else None,
                    delta_extension_proof=dict(source_pair_manifest=str(pairs_path.relative_to(ROOT)),
                        source_pair_manifest_sha256=inv.file_sha(pairs_path), old_diagnostic_sha256=inv.sha(row['diagnostic_candidate']),
                        native_source_freshly_redecoded=True, metadata_boundary=value.get('metadata_boundary_proof')))
                result.pop('diagnostic_candidate', None)
                result.pop('text', None)
                if value['decision'] == 'EDIT':
                    result['text'] = clean
                elif value['decision'] == 'PENDING':
                    result['diagnostic_candidate'] = clean
                changed.add(row['id'])
                phases.update(fresh_native_source_pairs=1)
                transitions.update([row['decision'] + '_TO_' + value['decision']])
            elif row['decision'] == 'PENDING':
                value = frozen_value(row)
                proxy = MetadataOnlyRow(row, complete_eos=True, valid_utf8=True)
                individual = any('PRIOR_INDIVIDUAL_OR_SPAN' in reason for reason in row['reasons'])
                with patch.object(policy.previous, 'propose', new=lambda *args, **kwargs: value):
                    extended = policy.propose(proxy, individual)
                left, right = dict(value), dict(extended)
                left.pop('rules', None)
                right.pop('rules', None)
                inv.require(left == right, 'v26 affected a non-censused pending source: ' + row['id'])
                phases.update(pending_nonmatch_full_extension_audit=1)
            else:
                phases.update(inherited_terminal_json_unchanged=1)
            writer.append(result)
            decisions[row['original_text_sha256']] = result['decision'], result['reasons']
            counts.update([result['decision']])
            if result['decision'] == 'PENDING':
                pending.update(result['reasons'])
        inv.require(changed == set(pair_map) and phases['pending_nonmatch_full_extension_audit'] + 27 == 77665,
                    'whole pending coverage differs')
        unique_manifest = writer.close(lineage=lineage)
        occurrence_writer = inv.ShardWriter(out / 'occurrences', 'decisions', limit=19_999_999)
        occurrences, sources = Counter(), defaultdict(Counter)
        for row in inv.cache.rows(source / 'occurrences', old['occurrence_manifest']):
            decision, reasons = decisions[row['original_text_sha256']]
            occurrence_writer.append(dict(row, resolution=decision, resolution_reasons=reasons))
            occurrences.update(documents=1, input_ids=row['input_ids'], **{decision: 1})
            occurrences[decision + '_input_ids'] += row['input_ids']
            sources[row['source']].update([decision])
        inv.require(len(seen) == 297539 and occurrences['documents'] == 460695
                    and occurrences['input_ids'] == 462874291, 'complete inherited scope differs')
        inv.require(counts['PENDING'] == 77639 and occurrences['PENDING'] == 122534,
                    'the26-only terminal delta must be exactly26 unique and51 positions')
        occurrence_manifest = occurrence_writer.close(lineage=lineage)
    inv.require(pins == {name: inv.file_sha(ROOT / name) for name in CODE}, 'delta production code changed')
    report = dict(schema='RESIDUAL_VERIFIED_DELTA_V1', status='DRAFT_NOT_CACHE_ADMISSION', lineage=lineage,
        unique_counts=dict(counts), occurrence_counts=dict(occurrences), pending_reasons_unique=dict(pending),
        sources={name: dict(value) for name, value in sources.items()}, unique_manifest=unique_manifest,
        occurrence_manifest=occurrence_manifest, full_residual_scope_covered=True,
        full_native_source_rerun=False, inherited_scope_fresh_extension_audit=dict(phases),
        transitions=dict(transitions), raw_source_ids_freshly_decoded=sorted(changed),
        unprocessed=occurrences['PENDING'], root_adopted=0, cache_admitted=0,
        goal_complete=False, training_authorized=False, seconds=time.monotonic() - started,
        input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [
            old_path, receipt_path, census_path, pairs_path, audit / 'V26_VERIFIED_DELTA_SCOPE_V1.md']})
    inv.write_json(out / 'complete.json', report)
    print(json.dumps({key: report[key] for key in ['status', 'unique_counts', 'occurrence_counts',
        'inherited_scope_fresh_extension_audit', 'transitions', 'seconds']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
