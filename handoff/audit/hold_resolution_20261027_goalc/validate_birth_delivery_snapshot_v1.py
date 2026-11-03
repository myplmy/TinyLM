"""Create a separate fail-closed view of a raw strict snapshot. Never admit bodies."""
from pathlib import Path
from collections import Counter
import argparse
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
GROUP = 'birth_root11_independent_v1'
module = AUDIT / 'birth_input_delivery_guard_v1.py'
spec = importlib.util.spec_from_file_location('delivery_snapshot_guard', module)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def pin(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=guard.sha(path.read_bytes()))


def save(path, value):
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
    guard.require(len(payload) < 5_000_000, 'guarded output needs a smaller shard')
    with path.open('xb') as stream:
        stream.write(payload)
    return dict(path=str(path.relative_to(ROOT)), sha256=guard.sha(payload), bytes=len(payload))


def run(snapshot_version, output_version):
    guard.require(all(re.fullmatch(r'v[1-9][0-9]*', v) for v in (snapshot_version, output_version)),
                  'explicit immutable versions required')
    activation_path = AUDIT / 'BIRTH_INPUT_DELIVERY_ACTIVATION_V1.json'
    activation = json.loads(activation_path.read_bytes())
    config_pin = activation['config']
    module_sha = activation['module']['sha256']
    config, contract, sources = guard.load_config(ROOT, config_pin, module_sha)
    guard.require(activation['cohort'] == GROUP == config['cohort'], 'cohort changed')
    activated = {}
    for role, assignment in activation['roles'].items():
        for task in assignment['task_pins']:
            guard.read_pin(ROOT, task)
        for ident in assignment['activated_source_ids']:
            guard.require(ident not in activated and sources[ident]['role'] == role, 'activation overlap')
            activated[ident] = role
    events_by_id, event_pins = {}, []
    for role in activation['roles']:
        events, pins = guard.load_events(ROOT, config, role)
        event_pins += pins
        for event in events:
            events_by_id.setdefault((role, event.get('source_id')), []).append(event)
    raw_path = BASE / (GROUP + '_snapshots') / snapshot_version / 'complete.json'
    raw_pin = pin(raw_path)
    raw = json.loads(guard.read_pin(ROOT, raw_pin))
    guard.require(raw['cohort'] == GROUP and raw['expected'] == len(sources) == 2707,
                  'raw snapshot source set changed')
    guard.require(raw['root_adopted'] == raw['cache_admitted'] == 0, 'unexpected admitted input')
    records = []
    for shard in raw['shards']:
        records += json.loads(guard.read_pin(ROOT, shard))
    guard.require(len(records) == len({r['id'] for r in records}) == len(sources) and
                  {r['id'] for r in records} == set(sources), 'raw snapshot coverage changed')
    target = BASE / 'birth_root11_input_delivery_gated_v1' / output_version
    guard.require(not target.exists(), 'new immutable output version required')
    target.mkdir(parents=True)
    counts, gated, review_times, review_pins = Counter(), [], {}, []
    failures = []
    for raw_row in records:
        ident, role = raw_row['id'], raw_row['role']
        guard.expected_event(config, contract, sources, role, ident, 1, config_pin['sha256'], module_sha)
        guard.require(raw_row['original']['sha256'] == sources[ident]['original']['sha256'],
                      'raw source binding changed')
        row = dict(raw_row)
        if ident not in activated:
            delivery = dict(status='HISTORICAL_BEFORE_ACTIVATION_NO_RETROSPECTIVE_EMISSION_CLAIM')
        elif not raw_row.get('review'):
            delivery = dict(status='NO_SAVED_REVIEW_ROW')
        else:
            review = raw_row['review']
            key = (review['path'], review['sha256'])
            try:
                if key not in review_times:
                    review_times[key] = guard.review_timestamp(ROOT, review)
                    review_pins.append(dict(path=review['path'], sha256=review['sha256'],
                                            mtime_ns=review_times[key]))
                delivery = guard.gate_source(config, contract, sources, role, ident,
                    config_pin['sha256'], module_sha, review_times[key],
                    events_by_id.get((role, ident), []))
            except (ValueError, OSError) as error:
                delivery = dict(status='REVIEW_BYTE_OR_TIMESTAMP_PRECONDITION_NOT_MET', error=str(error))
        counts[delivery['status']] += 1
        if delivery['status'] in ('INPUT_DELIVERY_PRECONDITION_NOT_MET',
                                   'REVIEW_BYTE_OR_TIMESTAMP_PRECONDITION_NOT_MET'):
            failures.append(dict(id=ident, role=role, review=raw_row.get('review'), delivery=delivery))
            # Block accidental body consumption; the immutable raw shard preserves all bytes/pins.
            row = {k: raw_row[k] for k in ('id', 'role', 'cohort', 'original', 'review') if k in raw_row}
            row.update(status='BLOCKED_BY_PROSPECTIVE_INPUT_DELIVERY_GUARD',
                       raw_snapshot_status=raw_row['status'], root_approved=False, cache_admitted=False)
        row['input_delivery'] = delivery
        gated.append(row)
    shards = [save(target / f'records_{n//350:03}.json', gated[n:n+350])
              for n in range(0, len(gated), 350)]
    result = dict(status='BIRTH_DELIVERY_GATED_VIEW_NOT_ROOT_ADMISSION', cohort=GROUP,
                  raw_snapshot=raw_pin, raw_snapshot_shards=raw['shards'],
                  activation=pin(activation_path), config=config_pin, module=activation['module'],
                  validator=pin(Path(__file__).resolve()), expected=len(sources), records=len(gated),
                  counts=dict(counts), failures=failures, event_shards=event_pins,
                  original_review_bytes_and_mtime_pins=review_pins, shards=shards,
                  raw_errors=len(raw['errors']), raw_needs_root=raw['needs_root'],
                  historical_emission_proven=False, semantic_review_inferred_from_emission=False,
                  root_adopted=0, cache_admitted=0, goal_complete=False, training_authorized=False)
    complete = save(target / 'complete.json', result)
    print(json.dumps(dict(status=result['status'], counts=dict(counts), failures=len(failures),
                          raw_errors=result['raw_errors'], receipt=complete), ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot-version', required=True)
    parser.add_argument('--output-version', required=True)
    args = parser.parse_args()
    run(args.snapshot_version, args.output_version)
