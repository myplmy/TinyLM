"""Index the exact pending authored set without copying or reopening TXT bodies."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from selection_metadata_store_v1 import SelectionStore
from profile_authored_remaining_deltas_v2 import signature


def json_pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest().upper(), bytes=len(raw))


def run(config_path):
    guard.activate()
    pins = {}

    def read(path, expected=None):
        path = Path(path)
        assert path.suffix == '.json' and not path.is_symlink()
        raw = path.read_bytes()
        assert 0 < len(raw) < 20_000_000
        sha = hashlib.sha256(raw).hexdigest().upper()
        assert expected is None or sha == expected, str(path)
        pins[str(path.relative_to(ROOT))] = sha
        return json.loads(raw)

    config = read(config_path)
    stage = read(ROOT / config['stage']['path'], config['stage']['sha256'])
    selection = SelectionStore(AUDIT).read(ROOT / config['selection']['path'], config['selection']['sha256'])
    prior = SelectionStore(AUDIT).read(AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11.json')
    prior_ids = {row['id'] for row in prior['rows']}
    selected_ids = {row['id'] for row in selection['rows']}
    selected_hashes = {row['original_text_sha256'] for row in selection['rows']}
    pins[config['selection']['path']] = config['selection']['sha256']
    contract = guard.checked_contract()
    blocked_ids = set(contract['restricted_ids']) | set(contract['trusted_metadata'])
    blocked_hashes = set(contract['restricted_hashes'])
    reviewed = {}
    all_reviews = defaultdict(list)
    seen = set()
    specs = list(stage['coverage']) + [dict(cohort='root12_independent_admission_counter_v1', version='v39')]
    for spec in specs:
        cohort, version = spec['cohort'], spec['version']
        if (cohort, version) in seen:
            continue
        seen.add((cohort, version))
        summary_path = guard.inv.BASE / (cohort + '_snapshots') / version / 'complete.json'
        summary = read(summary_path, stage['input_pins'].get(str(summary_path.relative_to(ROOT))))
        assert not summary['errors']
        manifest_path = guard.inv.BASE / cohort / 'manifest.json'
        manifest = read(manifest_path, stage['input_pins'].get(str(manifest_path.relative_to(ROOT))))
        sources = {row['id']: row for row in manifest['rows']}
        for shard in summary['shards']:
            records = read(ROOT / shard['path'], shard['sha256'])
            for record in records:
                if record.get('decision') == 'NEEDS_ROOT':
                    blocked_ids.add(record['id'])
                    if record.get('original'):
                        blocked_hashes.add(record['original']['sha256'])
                if record.get('original') and record.get('review') and not record.get('metadata_only'):
                    all_reviews[record['original']['sha256']].append(record)
                if cohort == 'root12_independent_admission_counter_v1':
                    continue
                if record['status'] == 'NO_SAVED_REVIEW_ROW' or record.get('metadata_only'):
                    continue
                if record.get('individual_human_full_read_completed') is False:
                    continue
                source = sources[record['id']]
                if record['id'] in reviewed:
                    assert reviewed[record['id']]['source']['original']['sha256'] == source['original']['sha256']
                    continue
                reviewed[record['id']] = dict(source=source, record=record, cohort=cohort)
    fresh = {key: value for key, value in reviewed.items() if key not in prior_ids}
    assert len(fresh) == stage['fresh_first_review_unique']
    assert sum(value['source']['occurrences'] for value in fresh.values()) == stage['fresh_first_review_positions']
    pending = {key: value for key, value in fresh.items() if key not in selected_ids}
    pending_positions = sum(value['source']['occurrences'] for value in pending.values())
    assert pending_positions == stage['official_stage_partition']['processed_not_ROOT_admitted'] == config['expected_pending_positions']
    assert len(pending) == config['expected_pending_unique']

    profiles = {}
    for spec in config['profiles']:
        report = read(ROOT / spec['path'], spec['sha256'])
        directory = ROOT / report['metadata_directory']
        for shard in report['metadata_manifest']['shards']:
            path = directory / shard['path']
            assert not path.is_symlink() and guard.inv.file_sha(path) == shard['sha256']
            pins[str(path.relative_to(ROOT))] = shard['sha256']
            for offset, record in enumerate(guard.inv.cache.rows(directory, dict(shards=[shard]))):
                digest = record['original']['sha256']
                profiles[digest] = dict(record=record, locator=dict(path=str(path.relative_to(ROOT)), sha256=shard['sha256'], offset=offset))

    rows = []
    counts, positions, examples = Counter(), Counter(), defaultdict(list)
    for ident, item in sorted(pending.items()):
        source = item['source']
        digest = source['original']['sha256']
        reviews = all_reviews[digest]
        primary = [row for row in reviews if row['cohort'] != 'root12_independent_admission_counter_v1'
                   and row.get('decision') in {'EDIT_TEXT', 'EDIT_RECIPE', 'KEEP_SOURCE', 'ADOPT_CANDIDATE'}
                   and row.get('body') and row.get('clean_text_sha256')]
        profile = None
        if ident in blocked_ids or any(source[key]['sha256'] in blocked_hashes for key in ['original', 'candidate']):
            group = 'EXPLICIT_CONTEXT_OR_RESTRICTED_HOLD'
        elif digest in selected_hashes:
            group = 'IDENTICAL_ORIGINAL_ALREADY_SELECTED_REQUIRES_ID_JOIN'
        elif not primary:
            group = 'NO_COMPLETED_PRIMARY_BODY'
        elif len({row['clean_text_sha256'] for row in reviews if row.get('body') and row.get('clean_text_sha256')}) != 1:
            group = 'DIFFERENT_SAVED_BODIES_REQUIRE_CONTEXT'
        elif not re.search(r'EOF|전체|전문|전량|끝|full', primary[0].get('read_scope', ''), re.I):
            group = 'FULL_READ_CLAIM_NOT_ESTABLISHED'
        else:
            profile = profiles.get(digest)
            assert profile is not None, 'eligible current body missing from full+delta profiles'
            record = profile['record']
            assert record['id'] == ident
            assert signature(record['body']['sha256'], record['all_reviews']) == signature(
                primary[0]['clean_text_sha256'], [row['review'] for row in reviews]), 'stale profile body or review identity'
            group = record['delta']['kind'] + (':REMAINING_CONTEXT_FLAGS' if record['remaining_deferrals'] or record['remaining_headings'] else ':NO_SCANNER_GAPS')
        row = dict(id=ident, original_sha256=digest, occurrences=source['occurrences'], group=group,
                   primary_cohort=item['cohort'], latest_review=item['record'].get('review'),
                   root_approved=False, cache_admitted=False)
        if profile:
            row['profile_record'] = profile['locator']
            row['body_sha256'] = profile['record']['body']['sha256']
        rows.append(row)
        counts[group] += 1
        positions[group] += source['occurrences']
        if len(examples[group]) < 3:
            examples[group].append(ident)
    assert len(rows) == len({row['id'] for row in rows}) == len(pending)
    assert sum(positions.values()) == pending_positions
    index_path = guard.inv.BASE / config['index_name']
    index = dict(schema='AUTHORED_PENDING_LOCATOR_INDEX_V1', rows=rows,
                 original_or_candidate_TXT_opens=0, payload_copies=0, additional_first_read_credit=0,
                 root_adopted=0, cache_admitted=0, input_pins=pins)
    assert not index_path.exists()
    assert len((json.dumps(index, ensure_ascii=False, indent=2) + chr(10)).encode()) < 20_000_000
    guard.inv.write_json(index_path, index)
    pins[str(Path(__file__).relative_to(ROOT))] = guard.inv.file_sha(Path(__file__))
    pins[str(guard.CONTRACT.relative_to(ROOT))] = guard.inv.file_sha(guard.CONTRACT)
    report = dict(status='EXACT_PENDING_AUTHORED_WORKSET_LOCATORS_RECONCILED_NOT_ADMISSION',
                  recorded_at=datetime.now(timezone.utc).isoformat(), unique_sources=len(rows), positions=pending_positions,
                  counts=dict(counts), position_counts=dict(positions), examples=dict(examples),
                  index=json_pin(index_path), source_body_opens=0, source_body_copies=0,
                  profile_reuse_requires_current_body_and_all_review_SHA=True,
                  root_adopted=0, cache_admitted=0, additional_first_read_credit=0,
                  input_pins=pins, goal_complete=False, training_authorized=False)
    output = AUDIT / config['report_name']
    assert not output.exists()
    guard.inv.write_json(output, report)
    guard.assert_no_protected_opens()
    print(json.dumps({key: value for key, value in report.items() if key not in {'input_pins', 'examples'}}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    path = Path(args.config).resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    run(path)
