"""Prospective packet emission evidence; neither authentication nor comprehension."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time

SCHEMA = 'BIRTH_PACKET_SUCCESSFUL_EMISSION_V1'
MAX_SHARD_BYTES = 1_000_000
MAX_EVENT_BYTES = 8_000
PIN_FIELDS = ('cohort', 'role', 'source_id', 'packet', 'packets',
              'original_sha256', 'candidate_sha256', 'packet_sha256',
              'config_sha256', 'module_sha256', 'reader_sha256', 'registry_sha256')


def sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def secure_path(root, relative):
    root = Path(root).absolute()
    part = Path(relative)
    require(not part.is_absolute() and part.parts and '..' not in part.parts,
            'path must remain within the exact root')
    cursor = root
    require(not root.is_symlink(), 'trusted root is a symlink')
    for name in part.parts:
        cursor = cursor / name
        require(not cursor.is_symlink(), 'symlink is outside the evidence contract')
    require(cursor.absolute().is_relative_to(root), 'path escaped root')
    return cursor


def read_pin(root, pin):
    path = secure_path(root, pin['path'])
    payload = path.read_bytes()
    require(sha(payload) == pin['sha256'], 'root-pinned metadata or tool changed')
    return payload


def load_config(root, config_pin, module_sha256):
    require(sha(Path(__file__).read_bytes()) == module_sha256, 'delivery module changed')
    config = json.loads(read_pin(root, config_pin))
    require(config['schema'] == 'BIRTH_INPUT_DELIVERY_CONFIG_V1', 'unknown config schema')
    contract = json.loads(read_pin(root, config['contract']))
    manifest = json.loads(read_pin(root, config['manifest']))
    require(isinstance(contract['restricted_ids'], list) and
            isinstance(contract['restricted_hashes'], list), 'invalid metadata protection')
    rows = {r['id']: r for r in manifest['rows']}
    require(len(rows) == len(manifest['rows']), 'duplicate source identity')
    return config, contract, rows


def expected_event(config, contract, rows, role, source_id, packet, config_sha256,
                   module_sha256):
    # No source/packet bytes, tool subprocess, or input-body hash before BOTH gates.
    require(source_id not in contract['restricted_ids'], 'restricted source ID')
    require(source_id in rows, 'unknown source identity')
    row = rows[source_id]
    require(row['original']['sha256'] not in contract['restricted_hashes'],
            'restricted original source hash')
    require(role in config['roles'] and row['role'] == role, 'different role assignment')
    require(isinstance(packet, int) and not isinstance(packet, bool) and
            1 <= packet <= len(row['reading_parts']), 'packet outside assigned sequence')
    assigned = config['roles'][role]
    part = row['reading_parts'][packet - 1]
    return dict(cohort=config['cohort'], role=role, source_id=source_id, packet=packet,
                packets=len(row['reading_parts']), original_sha256=row['original']['sha256'],
                candidate_sha256=row['candidate']['sha256'], packet_sha256=part['sha256'],
                config_sha256=config_sha256, module_sha256=module_sha256,
                reader_sha256=assigned['reader']['sha256'],
                registry_sha256=assigned['registry']['sha256'])


def event_hash(event):
    return sha(json.dumps(event, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8'))


def append_event(root, config, event, limit=MAX_SHARD_BYTES):
    require(0 < limit <= MAX_SHARD_BYTES, 'invalid shard limit')
    role_root = config['roles'][event['role']]['event_directory']
    suffix = 'root_probes' if event['purpose'] == 'ROOT_VERIFICATION_PROBE' else 'review_inputs'
    directory = secure_path(root, str(Path(role_root) / suffix))
    require(directory.is_dir(), 'fixed event directory is missing')
    record = dict(event, event_sha256=event_hash(event))
    payload = (json.dumps(record, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':')) + chr(10)).encode('utf-8')
    require(len(payload) <= min(MAX_EVENT_BYTES, limit), 'event exceeds fixed limit')
    # A directory inode lock avoids a mutable lockfile and keeps rotations serial.
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        files = sorted(directory.glob('events_*.jsonl'))
        require(all(re.fullmatch(r'events_[0-9]{6}\.jsonl', p.name) for p in files),
                'unrecognised event shard')
        require([p.name for p in files] == [f'events_{n:06}.jsonl' for n in range(len(files))],
                'event shard sequence has a gap')
        for path in files:
            secure_path(root, str(path.relative_to(root)))
            require(path.stat().st_size <= limit, 'existing event shard exceeds limit')
        number = len(files) - 1 if files and files[-1].stat().st_size + len(payload) <= limit else len(files)
        target = directory / f'events_{number:06}.jsonl'
        handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        try:
            require(os.fstat(handle).st_size + len(payload) <= limit, 'event rotation raced')
            require(os.write(handle, payload) == len(payload), 'partial event append')
            os.fsync(handle)
        finally:
            os.close(handle)
    finally:
        os.close(descriptor)
    return target


def checked_packet_output(stdout, expected, part):
    prefix = b'APPROVED_COMPLETE_PACKET '
    ending = (chr(10) + 'END_APPROVED_COMPLETE_PACKET' + chr(10)).encode('utf-8')
    require(stdout.startswith(prefix) and stdout.endswith(ending), 'incomplete packet envelope')
    header_bytes, rest = stdout.split(b'\n', 1)
    header = json.loads(header_bytes[len(prefix):])
    payload = rest[:-len(ending)]
    text = payload.decode('utf-8')
    require(0 <= len(text) <= 4000, 'packet exceeds bounded output')
    require(sha(payload) == expected['packet_sha256'] == header['sha256'], 'packet payload changed')
    require(header['source_id'] == expected['source_id'] and
            header['packet'] == expected['packet'] and header['packets'] == expected['packets'],
            'packet envelope identity differs')
    require(header['path'] == part['path'] and header['total_characters'] == len(text) and
            header['packet_complete'] is True and
            header['source_packet_sequence_complete'] == (expected['packet'] == expected['packets']),
            'packet boundary metadata differs')
    return stdout


def emit(root, config_pin, module_sha256, role, source_id, packet, probe=False,
         stdout=None, runner=subprocess.run, clock=time.time_ns):
    config, contract, rows = load_config(root, config_pin, module_sha256)
    event = expected_event(config, contract, rows, role, source_id, packet,
                           config_pin['sha256'], module_sha256)
    assigned = config['roles'][role]
    read_pin(root, assigned['registry'])
    read_pin(root, assigned['reader'])
    child = runner([sys.executable, '-I', '-B', str(secure_path(root, assigned['reader']['path'])),
                    '--source-id', source_id, '--packet', str(packet)],
                   cwd=root, capture_output=True, timeout=30, check=False)
    require(child.returncode == 0, 'fixed packet reader failed: ' +
            child.stderr.decode('utf-8', errors='replace')[-1500:])
    output = checked_packet_output(child.stdout, event, rows[source_id]['reading_parts'][packet - 1])
    sink = sys.stdout.buffer if stdout is None else stdout
    require(sink.write(output) == len(output), 'partial packet stdout write')
    sink.flush()
    # An event is created only after a successful write/flush of the complete output.
    event.update(schema=SCHEMA, emitted_at_ns=clock(),
                 purpose='ROOT_VERIFICATION_PROBE' if probe else 'REVIEW_INPUT')
    append_event(root, config, event)
    return event


def load_events(root, config, role):
    events, pins = [], []
    directory = secure_path(root, str(Path(config['roles'][role]['event_directory']) / 'review_inputs'))
    files = sorted(directory.glob('events_*.jsonl'))
    require([p.name for p in files] == [f'events_{n:06}.jsonl' for n in range(len(files))],
            'event shard sequence has a gap or unrecognised name')
    for path in files:
        secure_path(root, str(path.relative_to(root)))
        payload = path.read_bytes()
        require(len(payload) <= MAX_SHARD_BYTES and payload.endswith(b'\n'),
                'event shard is oversized or incomplete')
        pins.append(dict(path=str(path.relative_to(root)), sha256=sha(payload), bytes=len(payload)))
        for line in payload.splitlines():
            require(len(line) <= MAX_EVENT_BYTES, 'oversized event line')
            event = json.loads(line)
            claimed = event.pop('event_sha256')
            require(event_hash(event) == claimed and event.get('schema') == SCHEMA,
                    'event hash or schema changed')
            events.append(event)
    return events, pins


def gate_source(config, contract, rows, role, source_id, config_sha256, module_sha256,
                review_mtime_ns, events):
    require(isinstance(review_mtime_ns, int) and review_mtime_ns > 0, 'invalid review timestamp')
    # expected_event enforces both metadata protections before event matching.
    count = len(rows[source_id]['reading_parts']) if source_id in rows else 1
    missing, late = [], []
    for packet in range(1, count + 1):
        expected = expected_event(config, contract, rows, role, source_id, packet,
                                  config_sha256, module_sha256)
        matches = [e for e in events if e.get('schema') == SCHEMA and
                   e.get('purpose') == 'REVIEW_INPUT' and
                   all(e.get(k) == expected[k] for k in PIN_FIELDS) and
                   isinstance(e.get('emitted_at_ns'), int) and e['emitted_at_ns'] > 0]
        if not matches:
            missing.append(packet)
        elif not any(e['emitted_at_ns'] <= review_mtime_ns for e in matches):
            late.append(packet)
    return dict(status='INPUT_DELIVERED_BEFORE_REVIEW' if not missing and not late else
                'INPUT_DELIVERY_PRECONDITION_NOT_MET', source_id=source_id,
                role=role, packets=count, missing_packets=missing, late_packets=late,
                review_mtime_ns=review_mtime_ns, root_adopted=0, cache_admitted=0)


def review_timestamp(root, pin):
    path = secure_path(root, pin['path'])
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    require(sha(payload) == pin['sha256'], 'review bytes differ from immutable snapshot')
    require((before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns), 'review changed while sampled')
    return after.st_mtime_ns


def cli(root, config_pin, module_sha256, role):
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--packet', required=True, type=int)
    parser.add_argument('--probe', action='store_true')
    args = parser.parse_args()
    emit(root, config_pin, module_sha256, role, args.source_id, args.packet, args.probe)
