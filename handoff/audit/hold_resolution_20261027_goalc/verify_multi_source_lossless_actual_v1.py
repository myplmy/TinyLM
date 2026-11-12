"""Compare actual old/new fixed CLIs byte-for-byte for five roles' short IDs."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(AUDIT))
import active_guard_v6_preflight_v1 as guard
import multi_source_lossless_review_entry_v1 as new

ROLES = dict(c='context_controls', h='context_hangul', l='context_latin',
             j='historical_review', g='legacy_review')
PAGE = 13


def record(stream, prefix):
    line = stream.readline()
    assert line.startswith(prefix + b' '), (prefix, line[:80])
    return json.loads(line[len(prefix)+1:])


def frame_text(stream, frame):
    assert stream.readline() == b'SOURCE_DATA_VIEW_BEGIN' + bytes([10])
    lo, hi = frame['range']
    value = stream.read(hi-lo)
    assert len(value) == hi-lo
    return value.decode('utf-8')


def parse_old(raw):
    stream = io.BytesIO(raw)
    header = record(stream, b'TRUSTED_LOSSLESS_CONTEXT_V3')
    pieces = []
    while True:
        position = stream.tell()
        line = stream.readline()
        stream.seek(position)
        if line.startswith(b'TRUSTED_LOSSLESS_BATCH_END '):
            end = record(stream, b'TRUSTED_LOSSLESS_BATCH_END')
            assert end['source_id'] == header['source_id'] and not stream.read()
            return header, pieces
        item = record(stream, b'TRUSTED_LOSSLESS_VIEW_V3')
        item['text'] = frame_text(stream, item)
        suffix = b'EOF' if item['end_of_view'] else b'MORE_PARTS_REMAIN'
        assert stream.readline() == bytes([10])
        assert stream.readline() == b'SOURCE_DATA_VIEW_' + suffix + bytes([10])
        pieces.append(item)


def parse_new(raw):
    stream = io.BytesIO(raw)
    context = record(stream, b'TRUSTED_TASK_BATCH_CONTEXT_V1')
    packets = []
    current = None
    while True:
        position = stream.tell()
        line = stream.readline()
        stream.seek(position)
        if line.startswith(b'TRUSTED_TASK_BATCH_END_V1 '):
            end = record(stream, b'TRUSTED_TASK_BATCH_END_V1')
            assert not stream.read()
            return packets, end
        if line.startswith(b'TRUSTED_TASK_SOURCE_CONTEXT_V1 '):
            local = record(stream, b'TRUSTED_TASK_SOURCE_CONTEXT_V1')
            current = dict(header=dict(context['shared_header'], **local), pieces=[])
            packets.append(current)
            continue
        assert current is not None
        item = record(stream, b'TRUSTED_TASK_FRAME_V1')
        assert item.pop('source_id') == current['header']['source_id']
        item['text'] = frame_text(stream, item)
        assert stream.readline() == bytes([10])
        end = record(stream, b'TRUSTED_TASK_FRAME_END_V1')
        assert end == dict(source_id=current['header']['source_id'], part=item['part'],
            end_of_view=item['end_of_view'], next_part=item['next_part'])
        current['pieces'].append(item)


def invoke(path, values):
    started = time.monotonic()
    process = subprocess.run(['bash', str(path), *map(str, values)], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert process.returncode == 0, process.stderr.decode('utf-8')[:1200]
    return process.stdout, time.monotonic()-started


def main():
    guard.activate()
    contract = guard.checked_contract()
    old = new.frozen_batch()
    metadata, scope, core = old.setup(ROOT, old.frozen_entry())
    cohort = 'remaining_field_title_page_' + format(PAGE, '03d') + '_counter_v1'
    read = new.cached_reader(metadata.pinned)
    rows = []
    pins = {}
    for name, role in ROLES.items():
        manifest = json.loads(read(ROOT, scope['roles'][role][cohort]))
        eligible = []
        for row in manifest['rows']:
            if row['role'] != role or row['original']['sha256'] != row['candidate']['sha256']:
                continue
            try:
                guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['candidate']), contract)
            except ValueError:
                continue
            path = core.base.data_path(ROOT, row['original']['path'])
            size = path.stat().st_size
            if size <= 1600:
                eligible.append((size, row))
        chosen = [row for _size,row in sorted(eligible, key=lambda pair:(pair[0],pair[1]['id']))[:5]]
        assert len(chosen) == 5, role
        ids = [row['id'] for row in chosen]
        baseline = []
        old_bytes = 0
        old_seconds = 0
        old_shortcut = ROOT/('tmp/hold-'+name+'-field-lossless-batch-v1')
        new_shortcut = ROOT/('tmp/hold-'+name+'-field-task-batch-v1')
        for ident in ids:
            raw, seconds = invoke(old_shortcut, [PAGE, ident, 1, 3])
            baseline.append(parse_old(raw))
            old_bytes += len(raw)
            old_seconds += seconds
        raw, seconds = invoke(new_shortcut, [PAGE, *ids])
        packets, end = parse_new(raw)
        assert end['requested_ids'] == end['returned_ids'] == ids
        assert end['completed_pair_ids'] == ids and end['not_returned_ids'] == end['continuations'] == []
        assert end['first_read_credit'] == end['source_body_copies_written'] == 0
        assert len(packets) == 5 and len(raw) <= new.MAX_OUTPUT_BYTES
        for packet, (expected_header, expected_pieces) in zip(packets, baseline):
            assert packet['header'] == expected_header
            assert packet['pieces'] == expected_pieces
            assert packet['pieces'][-1]['end_of_view']
            assert packet['header']['cumulative_guard']['sha256'] == guard.EXPECTED
        pins.update({str(path.relative_to(ROOT)):guard.inv.file_sha(path) for path in [old_shortcut,new_shortcut]})
        rows.append(dict(role=role, ids=ids, source_ids=5, returned_frames=sum(len(p['pieces']) for p in packets),
            all_header_fields_and_body_frame_bytes_equal=True, every_pair_EOF=True,
            old_cli_invocations=5, new_cli_invocations=1, old_output_bytes=old_bytes,
            new_output_bytes=len(raw), old_subprocess_wall_seconds=old_seconds,
            new_subprocess_wall_seconds=seconds, new_first_read_credit=0))
    guard.assert_no_protected_opens()
    for path in [Path(__file__),new.OLD,AUDIT/'multi_source_lossless_review_entry_v1.py',
            AUDIT/'MULTI_SOURCE_LOSSLESS_REVIEW_F3_F4_V1.md',AUDIT/'MULTI_SOURCE_LOSSLESS_REVIEW_TESTS_V1.log',
            guard.CONTRACT,AUDIT/'active_guard_v6_preflight_v1.py']:
        pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
    result = dict(status='FIVE_ROLES_25_SOURCE_ACTUAL_FIXED_CLI_HEADER_AND_FRAME_EQUIVALENCE_VERIFIED',
        rows=rows,total_sources=25,old_cli_invocations=25,new_cli_invocations=5,
        old_output_bytes=sum(row['old_output_bytes'] for row in rows),
        new_output_bytes=sum(row['new_output_bytes'] for row in rows),
        actual_source_payloads_opened_for_transport_equivalence=True,
        original_or_candidate_copies_written=0,new_human_first_read_credit=0,
        protected_payload_open_attempts=0,whole_job_speed_multiplier_claimed=False,
        input_pins=pins,goal_complete=False,training_authorized=False)
    out = AUDIT/'MULTI_SOURCE_FIVE_ROLES_ACTUAL_EQUIVALENCE_VERIFIED_V1.json'
    assert not out.exists()
    guard.inv.write_json(out, result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'rows','input_pins'}},ensure_ascii=False))


if __name__ == '__main__':main()
