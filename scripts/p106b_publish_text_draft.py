#!/usr/bin/env python3
"""Root-owned copy-only text publication; never an authoring/quality gate.

Only BASE/packets/NAME.json and BASE/author_scratch/WORKER/UNIQUE.json
may be read. The code determines BASE/published/PACKETSTEM/ID.json.
Every ordinary publication attempt gets a new exclusive UUID receipt folder.
Packet raw bytes are deduplicated in publish_receipts/source_packets/SHA.json;
candidate input raw bytes remain independent per-attempt copies.
Existing final files, including incomplete ones, are never repaired/replaced.
No model, torch, tokenizer, canonical corpus, hooks, training or downloads.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p106b_text_batches as b

BASE_REL = Path('data_cache/p106b_text_work_20261022')
BASE = ROOT / BASE_REL
LIMIT = 20_000_000  # every individual input/archive/receipt/final must be <20MB
SCHEMA = 'P106B_COPY_ONLY_TEXT_PUBLISH_V1'
CODE_ROOT = ROOT
CODE = ('scripts/p106b_publish_text_draft.py', 'scripts/test_p106b_publish_text_draft.py',
    'scripts/p106b_text_batches.py', 'scripts/p106b_native_text_audit.py',
    'scripts/p106b_text_policy_revision.py', 'scripts/p106b_source_cleanup.py', 'scripts/p106b_shards.py')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def bytes_sha(raw): return hashlib.sha256(raw).hexdigest().upper()


def object_sha(value):
    return bytes_sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8'))


def code_hashes(): return {p: bytes_sha((CODE_ROOT / p).read_bytes()) for p in CODE}


def json_bytes(value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) >= LIMIT: raise ValueError('individual receipt must be below20MB')
    return raw


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError('duplicate JSON field: ' + key)
        value[key] = item
    return value


def parse(raw):
    def nonfinite(value): raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=nonfinite)


def owned_path(value, category):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise ValueError('literal local JSON path required')
    if any(p in ('.', '..') for p in value.split('/')): raise ValueError('path traversal refused')
    if BASE != ROOT / BASE_REL: raise ValueError('literal repository BASE required')
    path = Path(value); path = path if path.is_absolute() else ROOT / path
    path = b.safe(path)
    try: parts = path.relative_to(BASE).parts
    except ValueError: raise ValueError('outside the dedicated text BASE')
    expected = 2 if category == 'packet' else 3
    if (len(parts) != expected or parts[0] != ('packets' if category == 'packet' else 'author_scratch')
            or path.suffix != '.json' or NAME.fullmatch(path.stem) is None
            or (category == 'input' and NAME.fullmatch(parts[1]) is None)):
        raise ValueError('exact packet or worker/unique scratch JSON path required')
    return path


@contextmanager
def directory(path, create=False):
    """POSIX anchored directories; parent symlink races cannot redirect opens."""
    path = b.safe(path)
    parts = path.relative_to(ROOT).parts
    fd = os.open(ROOT, DIR_FLAGS)
    try:
        for part in parts:
            if part in ('.', '..'): raise ValueError('unresolved directory component')
            if create:
                try: os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError: pass
            following = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd); fd = following
        yield fd
    finally: os.close(fd)


def stamp(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


class Oversize(ValueError):
    def __init__(self, path, info):
        super().__init__('size>=20MB refused before reading/copying; scratch remains untouched')
        self.observation = dict(path=str(path.relative_to(ROOT)), bytes=info.st_size,
            sha256=None, raw_archive='NOT_READ_OR_COPIED_OVERSIZE', stamp=stamp(info))


def read_owned(path):
    """Bound before open, again after open, and after read; no linked files."""
    path = b.safe(path)
    with directory(path.parent) as parent:
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1: raise ValueError('regular single-link JSON file required')
        if before.st_size >= LIMIT: raise Oversize(path, before)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if opened.st_size >= LIMIT: raise Oversize(path, opened)
            if stamp(opened) != stamp(before): raise ValueError('file replaced before read')
            raw = stream.read(LIMIT)
            after = os.fstat(stream.fileno())
        current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
    if (len(raw) >= LIMIT or len(raw) != before.st_size or stamp(before) != stamp(after)
            or stamp(after) != stamp(current)): raise ValueError('file changed during bounded read')
    return raw, dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=bytes_sha(raw), stamp=stamp(after))


def exclusive_bytes(parent, name, raw):
    if len(raw) >= LIMIT: raise ValueError('individual write must be below20MB')
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600, dir_fd=parent)
    with os.fdopen(fd, 'wb') as stream:
        if stream.write(raw) != len(raw): raise OSError('short exclusive write; partial file preserved')
        stream.flush(); os.fsync(stream.fileno()); identity = stamp(os.fstat(stream.fileno()))
    os.fsync(parent)
    return identity


def verify_packet_reference(reference, expected):
    raw, current = read_owned(ROOT / reference['path'])
    if current != reference or raw != expected:
        raise ValueError('shared raw packet bytes/SHA/size/identity differ; no overwrite or repair')


def archive_packet(raw):
    """One O_EXCL byte copy per SHA; existing corrupt/partial copies fail closed."""
    if len(raw) >= LIMIT: raise ValueError('raw packet must be below20MB')
    path = BASE / 'publish_receipts/source_packets' / (bytes_sha(raw) + '.json')
    with directory(path.parent, create=True) as parent:
        # Serialize only this short archive critical section. A crashed writer
        # releases the lock but leaves its partial file for explicit rejection.
        fcntl.flock(parent, fcntl.LOCK_EX)
        try: exclusive_bytes(parent, path.name, raw)
        except FileExistsError: pass
        stored, reference = read_owned(path)
        if stored != raw or reference['sha256'] != bytes_sha(raw) or reference['bytes'] != len(raw):
            raise ValueError('existing shared raw packet is partial or mismatched; preserve it and fail')
    return reference


def identity(value, key):
    if type(value) is not int or value < 0 or len(str(value)) > 128:
        raise ValueError(key + ' must be a nonnegative integer, not bool/string')
    return value


def supplied(row, source, keys):
    for key in keys:
        if key in row and (key not in source or object_sha(row[key]) != object_sha(source[key])):
            raise ValueError('supplied source metadata differs: ' + key)
    if 'source' in row and object_sha(row['source']) != object_sha(source): raise ValueError('supplied source object differs')
    for key in ('meta', 'source_metadata'):
        if key in row and object_sha(row[key]) != object_sha(source.get('meta', {})):
            raise ValueError('supplied source metadata differs: ' + key)
    if 'training_admission' in row and row['training_admission'] != 'NOT_ADMITTED':
        raise ValueError('publication cannot assert training admission')


def validate(packet, row, kind):
    if not isinstance(packet, dict) or not isinstance(row, dict): raise ValueError('one strict JSON object required')
    key, collection = ('id', 'documents') if kind == 'native' else ('source_index', 'sources')
    ident = identity(row.get(key), key); sources = packet.get(collection)
    if not isinstance(sources, list) or not sources: raise ValueError('sealed packet collection required')
    seen = {}
    for source in sources:
        if not isinstance(source, dict): raise ValueError('sealed source object required')
        source_id = identity(source.get(key), key)
        if source_id in seen: raise ValueError('duplicate source ID in sealed packet')
        seen[source_id] = source
    if ident not in seen: raise ValueError('input ID is not owned by this packet')
    source = seen[ident]
    supplied(row, source, ('source_index', 'source_id', 'root_id', 'source_line_sha256', 'source_split', 'eos_segment_index'))
    proof = dict(id=ident, source_object_sha256=object_sha(source),
        source_scope='SEALED_PACKET_OBJECT_ONLY; whole canonical/cache validation remains root import responsibility')
    if kind == 'native':
        if not isinstance(source.get('text'), str) or b.sha(source['text']) != source.get('sha256'):
            raise ValueError('sealed native original text SHA differs')
        if 'source_sha256' in row and row['source_sha256'] != source['sha256']:
            raise ValueError('supplied source SHA differs')
        if packet.get('edit_contract', b.LINE_EDIT_CONTRACT) != b.LINE_EDIT_CONTRACT:
            raise ValueError('publisher requires existing positioned LF edit contract')
        if row.get('decision') not in ('KEEP', 'REWRITE', 'HOLD') or not isinstance(row.get('changes'), list):
            raise ValueError('native decision and explicit changes array required')
        text, ranges = b.apply_positioned_edits(source['text'], row['changes'])
        for change in row['changes']:
            resolved = next(v for v in ranges if v['source_lines'] == change['source_lines'])
            for field in ('source_span_sha256', 'offset_unit', 'line_range_unit'):
                if field in change and change[field] != resolved[field]:
                    raise ValueError('supplied positioned source metadata differs: ' + field)
        if 'proposed_text' in row and row['proposed_text'] != text: raise ValueError('undeclared text changes')
        if row['decision'] in ('KEEP', 'HOLD') and text != source['text']: raise ValueError('KEEP/HOLD must preserve original')
        if 'root_resolved_source_ranges' in row and object_sha(row['root_resolved_source_ranges']) != object_sha(ranges):
            raise ValueError('supplied resolved source ranges differ')
        proof.update(classification='NATIVE_SOURCE_BOUND_DRAFT', authored_variant_count=0,
            original_text_sha256=source['sha256'], reconstructed_text_sha256=b.sha(text),
            decision=row['decision'], resolved_ranges=ranges)
    else:
        variants, reason = row.get('variants'), row.get('triage_reason')
        if not isinstance(variants, list) or not isinstance(reason, str): raise ValueError('variants array and literal triage_reason required')
        original = [dict(role=m['role'], content=b.plain_content(m['content'])) for m in source['messages']]
        if not original: raise ValueError('nonempty sealed conversation required')
        allowed = source.get('meta', {}).get('supervised_assistant_turns')
        assistant_count = sum(m['role'] == 'assistant' for m in original)
        if allowed is not None and (not isinstance(allowed, list) or not allowed
                or len(set(allowed)) != len(allowed)
                or any(type(v) is not int or not 1 <= v <= assistant_count for v in allowed)):
            raise ValueError('invalid explicit source assistant supervision allowlist')
        if not variants:
            if not reason.strip(): raise ValueError('triage-only source needs an explicit nonempty reason')
            proof.update(classification='NOT_AUTHORED_TRIAGE_ONLY', authored_variant_count=0)
        else:
            if (len(variants) != 3 or any(not isinstance(v, dict) for v in variants)
                    or {v.get('kind') for v in variants} != set(b.KINDS)):
                raise ValueError('all three distinct complete variants required')
            for variant in variants:
                supplied(variant, source, ('source_index', 'source_id', 'root_id', 'source_line_sha256', 'source_split'))
                wanted = 'en' if variant['kind'] == 'en_rephrase' else 'ko'
                if 'requested_language' in variant and variant['requested_language'] != wanted:
                    raise ValueError('requested-language metadata differs from declared kind')
                b.validate_variant_conversation(original, variant)
            proof.update(classification='SFT_THREE_VARIANT_STRUCTURAL_DRAFT', authored_variant_count=3)
        proof['declared_source_line_sha256'] = source.get('source_line_sha256')
    return proof


def publish(packet_value, input_value, kind, *, argv=None):
    """Return (exit code, receipt); only this function creates publication data."""
    if BASE != ROOT / BASE_REL:
        return 9, dict(schema=SCHEMA, status='INCOMPLETE_RECEIPT_UNAVAILABLE', exit_code=9,
            error='literal repository BASE required', published_by_this_attempt=False)
    attempt = BASE / 'publish_receipts' / uuid.uuid4().hex
    receipt = dict(schema=SCHEMA, status='INCOMPLETE', published_by_this_attempt=False,
        packet_argument=packet_value, input_argument=input_value, kind=kind,
        attempt=str(attempt.relative_to(ROOT)), started_utc=datetime.now(timezone.utc).isoformat(),
        training_admission='NOT_ADMITTED', semantic_truth='NOT_VERIFIED', language_truth='NOT_VERIFIED',
        qualification='source/position/turn structure only; no fact, language or learning PASS')
    if argv is not None: receipt['command_argv'] = list(argv)
    try:
        with directory(attempt.parent, create=True) as parent:
            os.mkdir(attempt.name, mode=0o700, dir_fd=parent)  # exclusive UUID ownership
        with directory(attempt) as log:
            exclusive_bytes(log, 'request.json', json_bytes(receipt))
            code_before = None; read_paths = {}; final = None; created_identity = None; rc = 9
            try:
                code_before = code_hashes(); receipt['code_sha256_before'] = code_before
                if kind not in ('native', 'sft'): raise ValueError('exact native or sft kind required')
                packet_path = owned_path(packet_value, 'packet'); input_path = owned_path(input_value, 'input')
                raw, input_before = read_owned(input_path); read_paths['input'] = (input_path, input_before)
                receipt['input_before'] = input_before; exclusive_bytes(log, 'input.raw.json', raw)
                packet_raw, packet_before = read_owned(packet_path); read_paths['packet'] = (packet_path, packet_before)
                receipt['packet_before'] = packet_before
                receipt['packet_raw_reference'] = archive_packet(packet_raw)
                packet, row = parse(packet_raw), parse(raw); proof = validate(packet, row, kind)
                receipt['source_before'] = proof; ident = proof['id']
                final = b.safe(BASE / 'published' / packet_path.stem / (str(ident) + '.json'))
                receipt['final'] = str(final.relative_to(ROOT))
                for role, (path, before) in read_paths.items():
                    if read_owned(path)[1] != before: raise ValueError(role + ' changed before final creation')
                verify_packet_reference(receipt['packet_raw_reference'], packet_raw)
                with directory(final.parent, create=True) as destination:
                    try:
                        created_identity = exclusive_bytes(destination, final.name, raw)
                    except FileExistsError:
                        rc = 8; receipt['status'] = 'ALREADY_EXISTS_NOT_A_COMPLETION_PROOF'
                    else: rc = 0
                if rc == 8:
                    b.safe(final)  # a symlink is a path failure, never a readable existing draft
                    try: receipt['final_observation'] = read_owned(final)[1]
                    except Exception as observed:
                        # A concurrent creator may still be writing. EEXIST is
                        # already definitive: never retry/overwrite or claim it complete.
                        receipt['final_observation_error'] = type(observed).__name__
                else:
                    final_raw, observed = read_owned(final); receipt['final_observation'] = observed
                    if observed['stamp'] != created_identity or final_raw != raw:
                        raise ValueError('new final bytes/identity differ from raw input copy')
                for role, (path, before) in read_paths.items():
                    after_raw, after = read_owned(path); receipt[role + '_after'] = after
                    if after != before: raise ValueError(role + ' changed during publication')
                    if role == 'packet': receipt['source_after'] = validate(parse(after_raw), row, kind)
                if receipt['source_after'] != proof: raise ValueError('sealed source changed during publication')
                verify_packet_reference(receipt['packet_raw_reference'], packet_raw)
                if code_hashes() != code_before: raise ValueError('publisher/helper code bytes changed')
                receipt['code_sha256_after'] = code_before
                if rc == 0:
                    receipt.update(status='PUBLISHED_COPY_ONLY_DRAFT', published_by_this_attempt=True)
            except BaseException as exc:
                rc = 130 if isinstance(exc, KeyboardInterrupt) else 9
                receipt.update(status='INCOMPLETE', published_by_this_attempt=False,
                    error_type=type(exc).__name__, error=str(exc)[:2000])
                if isinstance(exc, Oversize): receipt['oversize_observation'] = exc.observation
                # Preserve any partial/new final; never unlink, replace or retry.
                if final is not None:
                    try: receipt['final_observation_after_failure'] = read_owned(final)[1]
                    except Exception as observed: receipt['final_observation_error'] = type(observed).__name__
                for role, (path, before) in read_paths.items():
                    try: receipt[role + '_after'] = read_owned(path)[1]
                    except Exception as observed: receipt[role + '_after_error'] = type(observed).__name__
                try: receipt['code_sha256_after'] = code_hashes()
                except Exception as observed: receipt['code_sha256_after_error'] = type(observed).__name__
            receipt.update(exit_code=rc, ended_utc=datetime.now(timezone.utc).isoformat())
            # Publish a complete, fsynced receipt atomically without replacing
            # any file. A crash leaves a pending file, never a half JSON receipt.
            # Keep the pending evidence; no deletion/cleanup is performed here.
            exclusive_bytes(log, 'receipt.pending.json', json_bytes(receipt))
            os.link('receipt.pending.json', 'receipt.json', src_dir_fd=log, dst_dir_fd=log,
                follow_symlinks=False)
            os.fsync(log)
        return rc, receipt
    except BaseException as exc:
        # Receipt namespace or disk failure is not permission to write elsewhere.
        return 9, dict(schema=SCHEMA, status='INCOMPLETE_RECEIPT_UNAVAILABLE', exit_code=9,
            attempt=str(attempt), error_type=type(exc).__name__, error=str(exc)[:1000],
            published_by_this_attempt=False, completion_claim=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet'); parser.add_argument('--input'); parser.add_argument('--kind')
    parser.add_argument('--check-only', action='store_true')
    actual_argv = list(sys.argv[1:] if argv is None else argv)
    try: args = parser.parse_args(actual_argv)
    except SystemExit as exc:
        if exc.code == 0: return 0  # help is not a publication attempt
        if '--check-only' in actual_argv: return 2  # malformed read-only checks still never write
        rc, receipt = publish(None, None, None, argv=actual_argv)
        print('[TEXT_PUBLISH_ATTEMPT] ' + json.dumps(receipt, ensure_ascii=False, sort_keys=True), flush=True)
        return rc
    if args.check_only:
        for name in CODE: ast.parse((CODE_ROOT / name).read_text(encoding='utf-8'), filename=name)
        print('[TEXT_PUBLISH_CODE_ONLY] ' + json.dumps(dict(schema=SCHEMA, code_sha256=code_hashes(),
            asset_reads=0, writes=0, model_calls=0, torch_imports=0))); return 0
    rc, receipt = publish(args.packet, args.input, args.kind, argv=actual_argv)
    print('[TEXT_PUBLISH_ATTEMPT] ' + json.dumps(receipt, ensure_ascii=False, sort_keys=True), flush=True)
    return rc


if __name__ == '__main__': raise SystemExit(main())
