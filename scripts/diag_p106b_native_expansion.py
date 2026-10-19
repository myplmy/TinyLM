#!/usr/bin/env python3
"""CPU-only, write-once legacy TRAIN -> canonical chat32 cache preparation.

EOS-delimited cache segments are not original URL/documents. Mechanical byte
equivalence is not new information or semantic decontamination. Only explicit
workers read bins; source/check-only do not. No model, CUDA, remote acquisition,
legacy VAL, old-cache mutation or automatic full build exists on this route.
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG, SCHEMA = 'p106b_native_expansion_v1_s1337', 'P106B_NATIVE_EXPANSION_CPU_V1'
CACHE, EVIDENCE = ROOT / 'data_cache' / TAG, ROOT / 'test_result/evidence' / TAG
OLD_TRAIN = ROOT / 'data_cache/ko-en_1200000000/train.bin'
OLD_META = OLD_TRAIN.parent / 'meta.json'
OLD_TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768.json'
CURRENT_VAL = ROOT / 'data_cache/ko-en_601000000_chat32/val.bin'
CURRENT_META = CURRENT_VAL.parent / 'meta.json'
CURRENT_TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
CURRENT_TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
CURRENT_VAL_SHA = 'AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C'
EXPECTED_OLD_IDS, EXPECTED_VAL_IDS, EXPECTED_VOCAB = 1194000000, 3005000, 32768
EOS, PILOT_IDS, PILOT_SECONDS = 2, 1048576, 1200
MAX_SEGMENT_IDS, MAX_BODY_BYTES = 1048576, 16777216
PUBLIC_LIMIT, DISK_RESERVE, RECORD_RESERVE = 20000000, 1 << 30, 600
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
BUILD_STOP = datetime(2026, 10, 20, 5, tzinfo=timezone.utc)
MODES = ('source', 'pilot', 'budget', 'build', 'readback')
SCRIPT = 'scripts/diag_p106b_native_expansion.py'
CODE = (SCRIPT, 'scripts/test_p106b_native_expansion.py',
        'scripts/p106b_shards.py', 'scripts/p106b_stage_receipt.py', '.gitignore')
THREAD_ENV = dict(TOKENIZERS_PARALLELISM='false', RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1',
                 OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
                 CUDA_VISIBLE_DEVICES='')


class Pending(RuntimeError):
    """Missing exact prerequisite/resources, not a failed student experiment."""


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def ids_bytes(ids):
    values = list(ids)
    if any(type(value) is not int or not 0 <= value < 65536 for value in values):
        raise ValueError('exact uint16 integer IDs required')
    packed = array('H', values)
    if sys.byteorder != 'little': packed.byteswap()
    return packed.tobytes()


def ids_hash(ids):
    return hashlib.sha256(ids_bytes(ids)).hexdigest().upper()


def byte_alphabet():
    values = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    chars, extra = list(values), 0
    for value in range(256):
        if value not in values:
            values.append(value); chars.append(256 + extra); extra += 1
    return {chr(char): value for value, char in zip(values, chars)}


def validate_layout(old, current):
    """Validate the suffix32-merge removal/ID shift, not numeric ID compatibility."""
    for codec_spec in (old, current):
        if (codec_spec.get('normalizer') is not None or codec_spec.get('truncation') is not None
                or codec_spec.get('padding') is not None or codec_spec['model'].get('type') != 'BPE'
                or codec_spec['model'].get('dropout') not in (None, 0, 0.)
                or codec_spec['model'].get('byte_fallback') not in (False, None)
                or codec_spec['pre_tokenizer'].get('type') != 'ByteLevel'
                or codec_spec['pre_tokenizer'].get('add_prefix_space') is not False
                or codec_spec['decoder'].get('type') != 'ByteLevel'):
            raise ValueError('unmodified byte-level BPE/no normalization/padding/truncation required')
        vocab = codec_spec['model']['vocab']
        if (any(type(index) is not int for index in vocab.values())
                or sorted(vocab.values()) != list(range(len(vocab)))):
            raise ValueError('bijective contiguous vocabulary required')
        added = codec_spec['added_tokens']
        if (any(a.get('special') is not True or a.get('lstrip') or a.get('rstrip')
                or a.get('single_word') or a.get('normalized') for a in added)
                or any(vocab.get(a['content']) != a['id'] for a in added)):
            raise ValueError('literal, non-stripping special-token contract required')
    a, b = old['model'], current['model']
    n = len(a['vocab'])
    if (n < 291 or len(b['vocab']) != n or len(old['added_tokens']) != 3
            or len(current['added_tokens']) != 35 or len(a['merges']) - len(b['merges']) != 32
            or a['merges'][:len(b['merges'])] != b['merges']):
        raise ValueError('same-size vocabulary with exactly32 new specials/removed suffix merges required')
    expected = ('<pad>', '<bos>', '<eos>')
    for index, literal in enumerate(expected):
        if (old['added_tokens'][index] != current['added_tokens'][index]
                or a['vocab'].get(literal) != index or b['vocab'].get(literal) != index):
            raise ValueError('shared0/1/2 pad/bos/eos meanings changed')
    for literal, index in a['vocab'].items():
        if 3 <= index < n - 32 and b['vocab'].get(literal) != index + 32:
            raise ValueError('surviving normal token ID shift differs')
        if index >= n - 32 and literal in b['vocab']:
            raise ValueError('old trailing32 merges were not actually removed')
    if sorted(a['id'] for a in current['added_tokens']) != list(range(35)):
        raise ValueError('current special IDs0..34 required')
    return dict(vocab=n, new_special_ids=list(range(3, 35)), removed_old_tail_ids=[n - 32, n - 1],
                ordinary_id_shift=32, id_direct_copy_allowed=False)


class ByteCodec:
    def __init__(self, config):
        from tokenizers import Tokenizer
        self.config = config
        self.backend = Tokenizer.from_str(json.dumps(config, ensure_ascii=False))
        self.specials = {a['id']: a['content'] for a in config['added_tokens']}
        alphabet = byte_alphabet(); self.pieces = [None] * len(config['model']['vocab'])
        for token, index in config['model']['vocab'].items():
            try:
                self.pieces[index] = (self.specials[index].encode('utf-8') if index in self.specials
                                      else bytes(alphabet[char] for char in token))
            except KeyError as exc:
                raise ValueError('non-byte-level ordinary vocabulary symbol') from exc
        for index, literal in self.specials.items():
            if (self.backend.encode(literal, add_special_tokens=False).ids != [index]
                    or self.backend.decode([index], skip_special_tokens=False) != literal
                    or self.pieces[index] != literal.encode()):
                raise ValueError('special meaning/bytes/canonical roundtrip differs')

    def raw(self, ids, max_bytes=MAX_BODY_BYTES):
        parts, size = [], 0
        for index in ids:
            if type(index) is not int or not 0 <= index < len(self.pieces):
                raise ValueError('source ID outside exact tokenizer vocabulary')
            piece = self.pieces[index]; size += len(piece)
            if size > max_bytes:
                raise ValueError('segment exceeds declared byte bound; no truncation/replacement')
            parts.append(piece)
        return b''.join(parts)

    def text(self, ids):
        raw = self.raw(ids)
        text = raw.decode('utf-8', errors='strict')
        if self.backend.decode(list(ids), skip_special_tokens=False).encode('utf-8') != raw:
            raise ValueError('manual bytes and library lossless decode differ')
        return text, raw


class CodecPair:
    def __init__(self, old, current):
        self.layout = validate_layout(old, current)
        self.old, self.current = ByteCodec(old), ByteCodec(current)
        self.new_specials = {key: value for key, value in self.current.specials.items() if key >= 3}
        self.literal_ids = {value: key for key, value in self.new_specials.items()}
        self.literal_pattern = re.compile('|'.join(re.escape(s) for s in self.literal_ids))

    def transform(self, segment):
        if (not segment or len(segment) > MAX_SEGMENT_IDS or segment[-1] != EOS
                or EOS in segment[:-1]):
            raise ValueError('one bounded complete EOS2 cache segment required')
        body = segment[:-1]; text, raw = self.old.text(body)
        encoded = self.current.backend.encode(text, add_special_tokens=False).ids
        if EOS in encoded:
            raise ValueError('canonical body introduced EOS2; boundary semantics changed')
        decoded, restored = self.current.text(encoded)
        if (raw != restored or decoded != text
                or self.current.backend.encode(decoded, add_special_tokens=False).ids != encoded):
            raise ValueError('strict UTF8/byte/canonical-ID equivalence failed')
        if any(body.count(index) != encoded.count(index) for index in (0, 1)):
            raise ValueError('shared pad/bos occurrence semantics changed')
        literals = Counter(self.literal_ids[m.group()] for m in self.literal_pattern.finditer(text))
        specials = Counter(index for index in encoded if index in self.new_specials)
        if literals != specials:
            raise ValueError('canonical reserved literal/token occurrence counts differ')
        return encoded + [EOS], dict(body_bytes=len(raw), byte_sha256=hashlib.sha256(raw).hexdigest().upper(),
            new_special_counts=dict(specials), old_tail_merge_tokens=sum(
                index >= self.layout['vocab'] - 32 for index in body))

    def current_segment(self, segment):
        if not segment or segment[-1] != EOS or EOS in segment[:-1]:
            raise ValueError('complete current EOS segment required')
        text, raw = self.current.text(segment[:-1])
        encoded = self.current.backend.encode(text, add_special_tokens=False).ids
        if encoded != list(segment[:-1]) or self.current.raw(encoded) != raw:
            raise ValueError('complete current VAL segment is not canonical')
        return list(segment)


def aligned_match(haystack, needle):
    if not needle or len(needle) % 2 or len(haystack) % 2:
        raise ValueError('nonempty uint16-aligned pattern/array bytes required')
    cursor, ignored = 0, 0
    while True:
        cursor = haystack.find(needle, cursor)
        if cursor < 0: return False, ignored
        if cursor % 2 == 0: return True, ignored
        ignored += 1; cursor += 1


@dataclass(frozen=True)
class ValIndex:
    full: frozenset
    partials: tuple
    summary: dict

    def match(self, ids):
        raw, reasons, ignored = ids_bytes(ids), [], 0
        if (len(ids), hashlib.sha256(raw).hexdigest().upper()) in self.full:
            reasons.append('FULL_CANONICAL_EOS_IDS')
        for label, pattern in self.partials:
            found, odd = aligned_match(raw, pattern); ignored += odd
            if found: reasons.append(label)
        return reasons, ignored


def build_val_index(ids, pair):
    full, first, buffer = set(), None, []
    count, full_rows = 0, 0
    for index in ids:
        if type(index) is not int or not 0 <= index < pair.layout['vocab']:
            raise ValueError('current VAL ID outside vocabulary')
        buffer.append(index); count += 1
        if len(buffer) > MAX_SEGMENT_IDS:
            raise ValueError('current VAL segment exceeds bound')
        if index == EOS:
            if first is None:
                first = buffer[:-1]
            else:
                canonical = pair.current_segment(buffer)
                full.add((len(canonical), ids_hash(canonical))); full_rows += 1
            buffer = []
    prefix, suffix = (list(buffer), list(buffer)) if first is None else (first, buffer)
    partials = tuple((label, ids_bytes(value)) for label, value in
                     (('VAL_PREFIX_PARTIAL_IDS', prefix), ('VAL_SUFFIX_PARTIAL_IDS', suffix)) if value)
    return ValIndex(frozenset(full), partials, dict(total_ids=count, complete_eos_segments=full_rows,
        unique_complete_id_hashes=len(full), first_fragment_policy='before_first_EOS_without_delimiter; conservatively partial',
        prefix_partial_ids=len(prefix), suffix_partial_ids=len(suffix),
        prefix_partial_sha256=ids_hash(prefix), suffix_partial_sha256=ids_hash(suffix),
        empty_partials_not_patterns=True, minimum_partial_length=1,
        matching='exact canonical full EOS hash OR either nonempty aligned uint16 ID substring',
        semantic_near_or_pretraining_decontamination='NOT_ESTABLISHED'))


def convert_stream(ids, pair, val_index, *, on_keep=None, on_event=None):
    """Consume every supplied ID; never accumulate all converted source in RAM."""
    stats = Counter({key: 0 for key in ('old_input_ids', 'old_complete_ids', 'old_kept_ids',
        'old_excluded_ids', 'old_incomplete_tail_ids', 'new_canonical_ids', 'new_kept_ids',
        'new_excluded_ids', 'complete_segments', 'kept_segments', 'excluded_segments',
        'verified_body_bytes', 'unaligned_partial_candidates_ignored', 'old_tail_merge_tokens')})
    stats.update(old_tail_merge_tokens_converted=0, old_tail_merge_tokens_retained=0,
                 old_tail_merge_tokens_excluded_validation=0)
    old_specials, new_specials, kept_specials, reasons = Counter(), Counter(), Counter(), Counter()
    consumer, all_new, kept_new = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    buffer, start, ordinal = [], 0, 0
    for index in ids:
        if type(index) is not int or not 0 <= index < pair.layout['vocab']:
            raise ValueError('legacy TRAIN ID outside declared vocabulary')
        stats['old_input_ids'] += 1
        if index in (0, 1, 2): old_specials[index] += 1
        if index >= pair.layout['vocab'] - 32: stats['old_tail_merge_tokens'] += 1
        buffer.append(index)
        if len(buffer) > MAX_SEGMENT_IDS:
            raise ValueError('legacy EOS segment exceeds bound; no splitting/truncation')
        if index != EOS: continue
        try:
            converted, proof = pair.transform(buffer)
        except (ValueError, UnicodeError) as exc:
            raise ValueError('legacy segment conversion stopped: segment=' + str(ordinal)
                + ' old_offset=' + str(start) + ' old_ids=' + str(len(buffer))) from exc
        original_raw, canonical_raw = ids_bytes(buffer), ids_bytes(converted)
        consumer.update(original_raw); all_new.update(canonical_raw)
        hits, odd = val_index.match(converted)
        n, m = len(buffer), len(converted)
        stats.update(old_complete_ids=n, new_canonical_ids=m, complete_segments=1,
            verified_body_bytes=proof['body_bytes'], unaligned_partial_candidates_ignored=odd,
            old_tail_merge_tokens_converted=proof['old_tail_merge_tokens'])
        new_specials.update(proof['new_special_counts'])
        if hits:
            stats.update(old_excluded_ids=n, new_excluded_ids=m, excluded_segments=1,
                old_tail_merge_tokens_excluded_validation=proof['old_tail_merge_tokens']); reasons.update(hits)
        else:
            stats.update(old_kept_ids=n, new_kept_ids=m, kept_segments=1,
                old_tail_merge_tokens_retained=proof['old_tail_merge_tokens'])
            kept_new.update(canonical_raw); kept_specials.update(proof['new_special_counts'])
            if on_keep is not None: on_keep(canonical_raw)
        event = dict(segment=ordinal, old_offset=start, old_ids=n, new_ids=m,
            old_ids_sha256=hashlib.sha256(original_raw).hexdigest().upper(),
            new_ids_sha256=hashlib.sha256(canonical_raw).hexdigest().upper(),
            body_bytes=proof['body_bytes'], body_sha256=proof['byte_sha256'],
            disposition='EXCLUDE_VALIDATION' if hits else 'KEEP', exclusion_reasons=hits,
            old_tail_merge_tokens=proof['old_tail_merge_tokens'])
        if on_event is not None: on_event(event)
        start += n; ordinal += 1; buffer = []
    tail_raw = pair.old.raw(buffer)
    consumer.update(ids_bytes(buffer)); stats['old_incomplete_tail_ids'] = len(buffer)
    stats['old_tail_merge_tokens_incomplete_tail'] = (stats['old_tail_merge_tokens']
                                                    - stats['old_tail_merge_tokens_converted'])
    if buffer and on_event is not None:
        on_event(dict(segment=ordinal, old_offset=start, old_ids=len(buffer), new_ids=0,
            old_ids_sha256=ids_hash(buffer), disposition='EXCLUDE_INCOMPLETE_TAIL',
            byte_count=len(tail_raw), byte_sha256=hashlib.sha256(tail_raw).hexdigest().upper(),
            old_tail_merge_tokens=sum(index >= pair.layout['vocab'] - 32 for index in buffer),
            utf8='NOT_DECODED_INCOMPLETE', exclusion_reasons=['INCOMPLETE_SOURCE_OR_PILOT_TAIL']))
    if (stats['old_input_ids'] != stats['old_kept_ids'] + stats['old_excluded_ids'] + len(buffer)
            or stats['new_canonical_ids'] != stats['new_kept_ids'] + stats['new_excluded_ids']):
        raise ValueError('whole consumer/drop/tail conservation failed')
    return dict(stats, old_special_counts={str(k): v for k, v in old_specials.items()},
        new_special_counts={str(k): v for k, v in new_specials.items()},
        retained_new_special_counts={str(k): v for k, v in kept_specials.items()}, validation_reason_segments=dict(reasons),
        reason_counts_may_overlap=True, incomplete_tail_bytes=len(tail_raw),
        incomplete_tail_ids_sha256=ids_hash(buffer), incomplete_tail_utf8='NOT_DECODED_INCOMPLETE',
        consumer_old_ids_sha256=consumer.hexdigest().upper(),
        canonical_ids_sha256=all_new.hexdigest().upper(), retained_ids_sha256=kept_new.hexdigest().upper(),
        replacement_repair=False, provenance='EOS_DELIMITED_CACHE_SEGMENTS_NOT_ORIGINAL_DOCUMENTS',
        train_to_train_unique_information='NOT_MEASURED; no train-to-train deduplication claim')


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(ROOT):
        raise ValueError('exact repository-owned absolute path required')
    for part in (path, *path.parents):
        if part.is_symlink(): raise ValueError('linked source/output ancestor forbidden')
        if part == ROOT: break
    return path


def read_path(path):
    path = Path(path)
    allowed = {OLD_TRAIN, OLD_META, OLD_TOKENIZER, CURRENT_VAL, CURRENT_META, CURRENT_TOKENIZER, ROOT / '.gitignore',
               *(ROOT / relative for relative in CODE)}
    if path not in allowed and not any(path.is_relative_to(base) for base in (CACHE, EVIDENCE)):
        raise ValueError('input outside exact allowlist; legacy VAL/current TRAIN are never inputs')
    return safe(path)


def digest(path, *, allow_whole_source=False, note=None):
    path = read_path(path)
    if path == OLD_TRAIN and not allow_whole_source:
        raise ValueError('whole legacy TRAIN hashing requires explicit budget worker permission')
    result, consumed, stamped = hashlib.sha256(), 0, time.perf_counter()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            result.update(block); consumed += len(block)
            if note is not None and time.perf_counter() - stamped >= 30:
                note('[NATIVE_CPU_HASH] bytes=' + str(consumed)); stamped = time.perf_counter()
    return result.hexdigest().upper()


def read_json(path):
    path = read_path(path)
    if not path.is_file(): raise Pending('required owned metadata absent: ' + path.name)
    if path.stat().st_size >= PUBLIC_LIMIT: raise ValueError('JSON must be below20MB')
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    if not any(path.is_relative_to(base) for base in (CACHE, EVIDENCE)):
        raise ValueError('only new tagged cache/evidence writes permitted')
    path = safe(path)
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(body) >= PUBLIC_LIMIT: raise ValueError('public/generated JSON must be below20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(body)


def info():
    pins = {relative: digest(ROOT / relative) if (ROOT / relative).is_file() else 'NOT_CREATED' for relative in CODE}
    return dict(schema=SCHEMA, tag=TAG, code_sha256=pins, code_complete='NOT_CREATED' not in pins.values(),
        cpu_only=True, model_loading=False, gpu=False, external_acquisition=False,
        old_train_path=str(OLD_TRAIN.relative_to(ROOT)), current_val_path=str(CURRENT_VAL.relative_to(ROOT)),
        expected_old_train_ids=EXPECTED_OLD_IDS, expected_current_val_ids=EXPECTED_VAL_IDS,
        current_val_sha256=CURRENT_VAL_SHA, current_tokenizer_sha256=CURRENT_TOKENIZER_SHA,
        pilot_old_ids_limit=PILOT_IDS, pilot_wall_limit_seconds=PILOT_SECONDS,
        eos_id=EOS, max_segment_old_ids=MAX_SEGMENT_IDS, max_body_bytes=MAX_BODY_BYTES,
        record_reserve_seconds=RECORD_RESERVE, authority_end_utc=END.isoformat(),
        full_build_readback_stop_utc=BUILD_STOP.isoformat(), minimum_partial_ids=1,
        partial_policy='both edges without EOS; nonempty exact aligned substring; no relaxation',
        incomplete_tail='count/hash/exclude; never decode with replacement',
        corpus_unit='EOS_DELIMITED_CACHE_SEGMENT_NOT_ORIGINAL_URL_DOCUMENT',
        source_pool_policy='REPLACE_WITH_RETAINED_POOL_ONLY; never add existing601M',
        raw_output_policy='ignored data_cache only; never stage/publish original text or generated bin',
        host_measurement_required_for=['budget', 'build'], host_measurement_max_age_seconds=600,
        worker_termination='SIGTERM_TO_KEYBOARDINTERRUPT130; SIGKILL activity preservation NOT_GUARANTEED',
        legacy_val_access=False, formal_train_ready=False, new_information_quality='NOT_ESTABLISHED')


def fingerprint(path):
    path = read_path(path); value = path.stat()
    if not path.is_file(): raise ValueError('regular fixed input required')
    return dict(path=str(path.relative_to(ROOT)), bytes=value.st_size, mtime_ns=value.st_mtime_ns,
                inode=value.st_ino, device=value.st_dev)


def source_snapshot():
    """Small config reads and bin stat only; no bin opened or hashed here."""
    old_meta, current_meta = read_json(OLD_META), read_json(CURRENT_META)
    old_config, current_config = read_json(OLD_TOKENIZER), read_json(CURRENT_TOKENIZER)
    ignore = read_path(ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    if not {'**/data_cache/', 'data_cache/', '/data_cache/'}.intersection(ignore):
        raise ValueError('explicit whole data_cache ignore rule required; no Git writes allowed')
    layout = validate_layout(old_config, current_config)
    small = {str(path.relative_to(ROOT)): digest(path) for path in
             (OLD_META, CURRENT_META, OLD_TOKENIZER, CURRENT_TOKENIZER)}
    old_stat, val_stat = fingerprint(OLD_TRAIN), fingerprint(CURRENT_VAL)
    if (old_meta.get('train') != EXPECTED_OLD_IDS or old_stat['bytes'] != 2 * EXPECTED_OLD_IDS
            or current_meta.get('val') != EXPECTED_VAL_IDS or val_stat['bytes'] != 2 * EXPECTED_VAL_IDS
            or old_meta.get('vocab') != EXPECTED_VOCAB or layout['vocab'] != EXPECTED_VOCAB
            or current_meta.get('vocab') != EXPECTED_VOCAB
            or current_meta.get('tokenizer_lineage') != 'chat32'
            or current_meta.get('tokenizer_sha256') != CURRENT_TOKENIZER_SHA
            or small[str(CURRENT_TOKENIZER.relative_to(ROOT))] != CURRENT_TOKENIZER_SHA):
        raise ValueError('exact declared legacy TRAIN/current chat32 metadata/config/uint16 sizes required')
    return dict(small_file_sha256=small, legacy_train=old_stat, current_val=val_stat, layout=layout,
        raw_cache_gitignore_sha256=digest(ROOT / '.gitignore'),
        dtype='uint16', byte_order='little', bin_hashes='NOT_READ_BY_SOURCE_STAGE',
        declared_global_old_mix={k: old_meta.get(k) for k in ('mix_sources', 'mix_ratio_cfg', 'mix_tokens', 'mix_token_frac')},
        declared_global_current_mix={k: current_meta.get(k) for k in ('mix_sources', 'mix_ratio_cfg', 'mix_tokens', 'mix_token_frac')},
        mix_scope='historical full-corpus metadata; not observed TRAIN/retained/draw language fractions',
        current_train_ids_from_meta=current_meta.get('train'), legacy_val_access=False,
        source_revision_original_url_or_document_id='UNAVAILABLE; not reconstructed')


def verify_source(expected):
    if sha(source_snapshot()) != sha(expected):
        raise ValueError('read-only original source/config stat or SHA changed')


class UInt16Input:
    def __init__(self, stream, limit, *, chunk_ids=65536):
        if type(limit) is not int or limit < 0 or type(chunk_ids) is not int or chunk_ids < 1:
            raise ValueError('explicit bounded integer input extent required')
        self.stream, self.limit, self.chunk = stream, limit, chunk_ids
        self.count, self.raw_sha = 0, hashlib.sha256()

    def __iter__(self):
        while self.count < self.limit:
            requested = 2 * min(self.chunk, self.limit - self.count)
            block = self.stream.read(requested)
            if not block or len(block) > requested or len(block) % 2:
                raise ValueError('input ended early or uint16 byte alignment differs')
            self.raw_sha.update(block)
            values = array('H'); values.frombytes(block)
            if sys.byteorder != 'little': values.byteswap()
            self.count += len(values)
            yield from values

    def hexdigest(self):
        return self.raw_sha.hexdigest().upper()


@contextmanager
def single_core_environment():
    previous = {key: os.environ.get(key) for key in THREAD_ENV}
    try:
        os.environ.update(THREAD_ENV)
        yield
    finally:
        for key, value in previous.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value


@contextmanager
def wall_limit(seconds):
    if type(seconds) is not int or seconds < 1:
        raise ValueError('positive wall bound required')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*_): raise TimeoutError('CPU worker wall limit exceeded; partial evidence preserved')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, previous)


@contextmanager
def termination_guard():
    """Owned worker only: TERM unwinds finally; SIGKILL cannot be caught.

    Ignore repeated TERM after the first request so bounded cleanup/activity
    writing can finish. Restore the exact prior handler on every exit path.
    """
    previous, interrupted = signal.getsignal(signal.SIGTERM), False
    def terminate(*_):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt('owned CPU worker received SIGTERM')
    signal.signal(signal.SIGTERM, terminate)
    try: yield
    finally: signal.signal(signal.SIGTERM, previous)


def authority(mode, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('aware clock required')
    until = BUILD_STOP if mode in ('budget', 'build', 'readback') else END
    available = (until - now).total_seconds() - RECORD_RESERVE
    if available <= 0: raise Pending('explicit CPU deadline/600s recording reserve ended')
    return available


def report_path(mode):
    if mode not in MODES: raise ValueError('registered CPU mode required')
    return EVIDENCE / mode / 'report.json'


def activity_path(mode):
    if mode not in MODES: raise ValueError('registered CPU mode required')
    return EVIDENCE / ('activity_' + mode + '.json')


def read_report(mode):
    report, activity = read_json(report_path(mode)), read_json(activity_path(mode))
    expected_status = dict(source='SOURCE_METADATA_PINNED', pilot='PILOT_CPU_COMPLETE',
        budget='FULL_BUILD_BUDGET_ADMITTED', build='FULL_CONVERSION_COMPLETE_NOT_TRAINING',
        readback='FULL_CACHE_READBACK_COMPLETE')
    if (sha(report.get('recipe')) != sha(info()) or report.get('mode') != mode
            or report.get('status') != expected_status[mode]
            or activity.get('schema') != SCHEMA or activity.get('tag') != TAG or activity.get('mode') != mode
            or activity.get('complete') is not True or type(activity.get('returncode')) is not int
            or activity['returncode'] != 0 or activity.get('code_sha256') != info()['code_sha256']
            or activity.get('report_sha256') != digest(report_path(mode))
            or activity.get('report_path') != str(report_path(mode).relative_to(ROOT))
            or type(activity.get('seconds')) not in (int, float)
            or not math.isfinite(activity['seconds']) or activity['seconds'] < 0
            or type(activity.get('max_wall_sec')) is not int or not 60 <= activity['max_wall_sec'] <= 21600):
        raise Pending('completed same-code exact-report CPU prerequisite required')
    if datetime.fromisoformat(activity['recorded_at']).tzinfo is None:
        raise ValueError('aware CPU completion timestamp required')
    return report


def peak_rss_bytes():
    # This Linux/WSL worker reports ru_maxrss KiB, not model/GPU resident memory.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def pool_for_draw(pool_ids, draw_ids=None):
    if type(pool_ids) is not int or pool_ids < 0 or (draw_ids is not None
            and (type(draw_ids) is not int or draw_ids <= 0)):
        raise ValueError('nonnegative actual pool and positive optional draw required')
    return dict(retained_pool_ids=pool_ids, max_draw_under_pool2x=pool_ids // 2,
        requested_draw_ids=draw_ids, pool_div_draw=None if draw_ids is None else pool_ids / draw_ids,
        pool2x_admissible=None if draw_ids is None else pool_ids >= 2 * draw_ids,
        existing601m_added=False, unique_information_or_language_quality='NOT_ESTABLISHED')


def guest_disk_measurement():
    path = safe(CACHE).parent
    return dict(path=str(path.relative_to(ROOT)), free_bytes=shutil.disk_usage(path).free,
        measured_at_utc=datetime.now(timezone.utc).isoformat(),
        method='shutil.disk_usage; guest logical filesystem only, NOT host backing-store free',
        filesystem_type='NOT_AUTODETECTED')


def utc_measurement_time(value):
    # Python3.10 rejects PowerShell's Z/seven-fraction ISO spelling. Keep the
    # original spelling in the receipt and floor sub-microseconds (conservative
    # for maximum-age admission), never silently reinterpret local time.
    if not isinstance(value, str): raise ValueError('explicit ISO UTC host timestamp required')
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|\+00:00)', value)
    if not match: raise ValueError('host timestamp needs explicit UTC Z or+00:00')
    fraction = ((match.group(2) or '') + '000000')[:6]
    return datetime.fromisoformat(match.group(1) + '.' + fraction + '+00:00')


def host_measurement(value, *, now=None):
    """Root-supplied fresh physical-host observation, never inferred from guest."""
    if value is None: raise Pending('fresh explicit root host-free measurement/evidence required')
    free = value.get('free_bytes')
    if type(free) is not int or free <= 0 or not value.get('label') or not value.get('evidence_path'):
        raise ValueError('positive host bytes, input storage label and root evidence path required')
    stamp = utc_measurement_time(value['measured_at'])
    now = datetime.now(timezone.utc) if now is None else now
    if (stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0 or now.tzinfo is None):
        raise ValueError('root host measurement and check require aware UTC timestamp')
    age = (now - stamp).total_seconds()
    if not 0 <= age <= 600:
        raise Pending('root host measurement must be within600s at each budget/build entry')
    path = Path(value['evidence_path'])
    if not path.is_absolute(): path = ROOT / path
    if not any(path.is_relative_to(base) for base in (ROOT / 'handoff/audit', ROOT / 'test_result')):
        raise ValueError('root host evidence must be an exact small audit/result artifact')
    path = safe(path)
    if not path.is_file(): raise Pending('root host measurement evidence absent')
    if path.stat().st_size >= PUBLIC_LIMIT: raise ValueError('host evidence must be below20MB')
    return dict(free_bytes=free, measured_at_utc=stamp.isoformat(), measured_at_input=value['measured_at'],
        timestamp_precision='microseconds; sub-microsecond fraction conservatively floored', age_seconds_at_entry=age,
        storage_label=value['label'], evidence_path=str(path.relative_to(ROOT)),
        evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        method='ROOT_SUPPLIED_PHYSICAL_HOST_OBSERVATION; not measured/inferred by this tool',
        label_scope='input label only; VHDX/backing-store mapping NOT_AUTODETECTED',
        evidence_scope='file SHA binding; value/topology provenance remains root-owned',
        runtime_continuous_host_free_guarantee=False)


def load_pair():
    if any(os.environ.get(key) != value for key, value in THREAD_ENV.items()):
        raise ValueError('explicit single-core tokenizer environment required before codec construction')
    return CodecPair(read_json(OLD_TOKENIZER), read_json(CURRENT_TOKENIZER))


def load_current_val(pair):
    started = time.perf_counter()
    with read_path(CURRENT_VAL).open('rb') as stream:
        reader = UInt16Input(stream, EXPECTED_VAL_IDS)
        index = build_val_index(reader, pair)
    if reader.count != EXPECTED_VAL_IDS or reader.hexdigest() != CURRENT_VAL_SHA:
        raise ValueError('complete exact current chat32 VAL SHA/consumer required')
    return index, dict(seconds=time.perf_counter() - started, ids=reader.count,
        source_sha256=reader.hexdigest(), index=index.summary)


def source_stage():
    if not info()['code_complete']: raise Pending('both new files and code pins required')
    snapshot = source_snapshot()
    return dict(status='SOURCE_METADATA_PINNED', source=snapshot,
        disk=dict(guest_logical=guest_disk_measurement(), host='NOT_MEASURED_BY_TOOL'),
        scope='metadata/codec layout and bin stat only; no bin opened or hashed',
        pilot='NOT_RUN', full_build='NOT_RUN', model_gpu_training='NOT_RUN')


def pilot_stage():
    original = read_report('source')['source']; verify_source(original)
    pair = load_pair(); index, val = load_current_val(pair)
    event_bytes = 0
    def observe(event):
        nonlocal event_bytes
        event_bytes += len((json.dumps(event, sort_keys=True, separators=(',', ':')) + '\n').encode())
    started = time.perf_counter()
    count = min(PILOT_IDS, EXPECTED_OLD_IDS)
    with read_path(OLD_TRAIN).open('rb') as stream:
        reader = UInt16Input(stream, count)
        stats = convert_stream(reader, pair, index, on_event=observe)
    elapsed = time.perf_counter() - started
    if (reader.count != count or stats['old_input_ids'] != count
            or reader.hexdigest() != stats['consumer_old_ids_sha256']):
        raise ValueError('fixed-prefix read and actual consumer/hash denominator differ')
    verify_source(original)
    return dict(status='PILOT_CPU_COMPLETE', source=original, current_val=val,
        disk=dict(guest_logical=guest_disk_measurement(), host='NOT_MEASURED_BY_TOOL'),
        metrics=stats, conversion_seconds=elapsed, old_ids_per_second=count / elapsed,
        complete_segment_checks_observed=stats['complete_segments'] > 0,
        prefix_read_ids=count, prefix_read_bytes=2 * count, prefix_sha256=reader.hexdigest(),
        whole_legacy_source_sha256='NOT_READ_BY_PILOT', audit_sample_encoded_bytes=event_bytes,
        peak_process_rss_bytes=peak_rss_bytes(), rss_scope='Linux ru_maxrss KiB*1024; CPU process peak, not model/GPU',
        full_build='NOT_RUN', pool_scope='bounded prefix positions only; not full remaining/unique pool',
        pool2draw_prefix_only=pool_for_draw(stats['new_kept_ids']),
        semantic_quality_or_new_knowledge='NOT_ESTABLISHED')


def forecast(pilot, source_ids, *, remaining_seconds, free_bytes):
    stats = pilot['metrics']; consumed = stats['old_input_ids']; complete = stats['old_complete_ids']
    elapsed = pilot['conversion_seconds']
    if consumed <= 0 or complete <= 0 or not math.isfinite(elapsed) or elapsed <= 0:
        raise Pending('successful observed complete-segment pilot required for full-build forecast')
    canonical = math.ceil(source_ids * stats['new_canonical_ids'] / complete)
    # Whole prefix elapsed/audit includes incomplete-tail overhead, but only
    # complete EOS IDs actually exercised canonical conversion. Never let a
    # long unconverted tail inflate the extrapolation denominator.
    audit_bytes = math.ceil(source_ids * pilot['audit_sample_encoded_bytes'] / complete)
    estimated_build = math.ceil(2.0 * (source_ids * elapsed / complete + pilot['current_val']['seconds']) + 120)
    required_disk = 2 * (2 * canonical + audit_bytes) + DISK_RESERVE
    # No retention fraction extrapolation is promoted to actual remaining pool.
    preliminary_readback = 120 + 2 * pilot['current_val']['seconds']
    result = dict(estimated_build_seconds=estimated_build, preliminary_readback_seconds=preliminary_readback,
        estimated_unfiltered_canonical_ids=canonical, estimated_audit_bytes=audit_bytes,
        required_disk_bytes=required_disk, available_disk_bytes=free_bytes,
        remaining_after_record_reserve_seconds=remaining_seconds, headroom_factor=2.0,
        extrapolation_complete_old_ids=complete,
        extrapolation_scope='whole prefix elapsed/audit divided by complete EOS old IDs; tail overhead included',
        uncertainty='prefix extrapolation, not a whole-corpus guarantee; runtime disk/deadline guards remain',
        actual_retained_pool='NOT_BUILT; no prefix retention/unique-information extrapolation',
        full_build='NOT_RUN')
    if required_disk > free_bytes: raise Pending('conservative CPU build disk estimate plus1GiB does not fit')
    if estimated_build + preliminary_readback > remaining_seconds or estimated_build > 21600:
        raise Pending('CPU build/readback estimate does not fit05Z/600s reserve or6h worker bound')
    return result


def budget_stage(*, allow_full_scan=False, host=None):
    if not allow_full_scan: raise Pending('budget whole-source hashing needs explicit --allow-full-scan')
    host_now, guest_now = host_measurement(host), guest_disk_measurement()
    pilot = read_report('pilot'); verify_source(pilot['source'])
    initial = forecast(pilot, EXPECTED_OLD_IDS, remaining_seconds=authority('budget'),
                       free_bytes=guest_now['free_bytes'])
    if initial['required_disk_bytes'] > host_now['free_bytes']:
        raise Pending('root-measured physical host free does not fit independent disk requirement')
    started = time.perf_counter()
    source_sha = digest(OLD_TRAIN, allow_whole_source=True, note=lambda text: print(text, flush=True))
    hash_seconds = time.perf_counter() - started
    verify_source(pilot['source'])
    # Readback performs ID/range/EOS/audit verification as well as hashing.
    readback_seconds = math.ceil(max(120., hash_seconds * 4.,
        2.0 * EXPECTED_OLD_IDS * pilot['conversion_seconds'] / pilot['metrics']['old_complete_ids'] * .1))
    total = initial['estimated_build_seconds'] + readback_seconds
    if total > authority('budget'):
        raise Pending('measured hash plus conversion/readback forecast no longer fits05Z')
    return dict(status='FULL_BUILD_BUDGET_ADMITTED', source=pilot['source'],
        disk=dict(guest_logical=guest_now, host_root_input=host_now),
        pilot_report_sha256=digest(report_path('pilot')), source_train_sha256=source_sha,
        whole_source_hash_seconds=hash_seconds, source_bytes=2 * EXPECTED_OLD_IDS,
        source_hash_bytes_per_second=2 * EXPECTED_OLD_IDS / max(hash_seconds, 1e-9),
        forecast=dict(initial, estimated_readback_seconds=readback_seconds,
                      total_estimated_seconds=total),
        full_build='NOT_RUN', future_training='NOT_AUTHORIZED_BY_THIS_CPU_RECEIPT')


def validate_build_budget(budget, pilot, max_wall_sec, *, free_bytes, remaining_seconds, host_free_bytes=None):
    prediction = budget['forecast']
    if (not re.fullmatch('[0-9A-F]{64}', budget.get('source_train_sha256', ''))
            or budget.get('pilot_report_sha256') != digest(report_path('pilot'))
            or sha(budget.get('source')) != sha(pilot['source'])):
        raise ValueError('same-source/code successful pilot and whole-source SHA budget required')
    if host_free_bytes is None:
        raise Pending('current root host-free measurement required, not old budget free bytes')
    if (max_wall_sec < prediction['estimated_build_seconds']
            or prediction['required_disk_bytes'] > free_bytes
            or prediction['required_disk_bytes'] > host_free_bytes
            or prediction['total_estimated_seconds'] > remaining_seconds):
        raise Pending('explicit worker cap/disk/05Z completion and readback reserve do not fit')


def validate_readback_budget(budget, max_wall_sec, *, remaining_seconds):
    required = budget['forecast'].get('estimated_readback_seconds')
    if type(required) not in (int, float) or not math.isfinite(required) or required <= 0:
        raise ValueError('positive finite measured-budget readback estimate required')
    if required > max_wall_sec or required > remaining_seconds or max_wall_sec > remaining_seconds:
        raise Pending('readback estimate/declared worker cap must both fit05Z minus600s record reserve')
    return required


def build_stage(*, allow_full_build=False, max_wall_sec=1200, draw_ids=None, host=None):
    if not allow_full_build: raise Pending('full build needs explicit --allow-full-build')
    host_now, guest_now = host_measurement(host), guest_disk_measurement()
    pilot, budget = read_report('pilot'), read_report('budget'); verify_source(pilot['source'])
    validate_build_budget(budget, pilot, max_wall_sec,
        free_bytes=guest_now['free_bytes'], host_free_bytes=host_now['free_bytes'],
        remaining_seconds=authority('build'))
    target, metadata = safe(CACHE / 'train.bin'), safe(CACHE / 'meta.json')
    if target.exists() or metadata.exists() or (CACHE / 'segments').exists():
        raise FileExistsError('preserve partial/complete converted cache and segment ledger')
    pair = load_pair(); index, val = load_current_val(pair)
    if sha(val['index']) != sha(pilot['current_val']['index']):
        raise ValueError('same complete current VAL exclusion index required')
    safe(CACHE).mkdir(parents=True, exist_ok=True)
    audit = ShardWriter(safe(CACHE / 'segments'), 'segments', limit=PUBLIC_LIMIT - 1)
    started, stamped, written = time.perf_counter(), time.perf_counter(), 0
    def event(row):
        nonlocal stamped
        audit.append(row)
        if time.perf_counter() - stamped >= 20:
            if shutil.disk_usage(CACHE).free < DISK_RESERVE:
                raise Pending('runtime1GiB free-disk reserve reached; partial cache preserved')
            authority('build')
            print('[NATIVE_CPU_BUILD] ' + json.dumps(dict(old_offset=row['old_offset'],
                old_ids=row['old_ids'], output_bytes=written)), flush=True)
            stamped = time.perf_counter()
    try:
        with target.open('xb') as output, read_path(OLD_TRAIN).open('rb') as stream:
            def keep(block):
                nonlocal written
                if output.write(block) != len(block): raise OSError('short write; incomplete output retained')
                written += len(block)
                if written % (64 << 20) < len(block) and shutil.disk_usage(CACHE).free < DISK_RESERVE:
                    raise Pending('runtime free-disk reserve reached')
            reader = UInt16Input(stream, EXPECTED_OLD_IDS)
            stats = convert_stream(reader, pair, index, on_keep=keep, on_event=event)
            output.flush(); os.fsync(output.fileno())
    finally:
        # Flush/close partial ledger shards without creating a success manifest.
        audit._finish()
    if (reader.count != EXPECTED_OLD_IDS or stats['old_input_ids'] != EXPECTED_OLD_IDS
            or reader.hexdigest() != budget['source_train_sha256']
            or stats['consumer_old_ids_sha256'] != budget['source_train_sha256']
            or written != 2 * stats['new_kept_ids']):
        raise ValueError('whole input reader/consumer SHA/count or output denominator differs')
    manifest = audit.close(lineage=dict(tag=TAG, kind='EOS_CACHE_SEGMENT_AUDIT',
        source_train_sha256=budget['source_train_sha256']))
    verify(CACHE / 'segments', manifest); verify_source(pilot['source'])
    meta = dict(schema=SCHEMA, tag=TAG, train=stats['new_kept_ids'], val=0, vocab=EXPECTED_VOCAB,
        token_dtype='uint16', byte_order='little', tokenizer_lineage='chat32',
        tokenizer_sha256=CURRENT_TOKENIZER_SHA, train_sha256=stats['retained_ids_sha256'],
        source_train_sha256=budget['source_train_sha256'], source_ids=EXPECTED_OLD_IDS,
        current_val_sha256=CURRENT_VAL_SHA, source_snapshot_sha256=sha(pilot['source']),
        code_sha256=info()['code_sha256'], original_data_mutated=False, legacy_val_access=False,
        unit='EOS_DELIMITED_CACHE_SEGMENTS_NOT_URL_DOCUMENTS',
        pool2draw=pool_for_draw(stats['new_kept_ids'], draw_ids),
        formal_train_ready=False, language_or_new_information_quality='NOT_ESTABLISHED')
    write_json(metadata, meta)
    return dict(status='FULL_CONVERSION_COMPLETE_NOT_TRAINING', source=pilot['source'],
        disk=dict(guest_logical=guest_now, host_root_input=host_now,
                  runtime_host_free='NOT_CONTINUOUSLY_OBSERVED; guest reserve/write errors still stop'),
        budget_report_sha256=digest(report_path('budget')), pilot_report_sha256=digest(report_path('pilot')),
        source_train_sha256=budget['source_train_sha256'], metrics=stats, current_val=val,
        actual_conversion_seconds=time.perf_counter() - started, output_path=str(target.relative_to(ROOT)),
        output_bytes=written, output_sha256=stats['retained_ids_sha256'],
        meta_sha256=digest(metadata), audit_manifest=manifest,
        audit_manifest_sha256=digest(CACHE / 'segments/segments_shards_manifest.json'),
        pool2draw=meta['pool2draw'], peak_process_rss_bytes=peak_rss_bytes(),
        training='NOT_RUN', model_gpu='NOT_RUN', readback='NOT_RUN')


def recount_audit(events, expected):
    observed = Counter({key: 0 for key in ('old_input_ids', 'old_complete_ids', 'old_kept_ids',
        'old_excluded_ids', 'old_incomplete_tail_ids', 'new_canonical_ids', 'new_kept_ids',
        'new_excluded_ids', 'complete_segments', 'kept_segments', 'excluded_segments',
        'verified_body_bytes', 'old_tail_merge_tokens', 'old_tail_merge_tokens_converted',
        'old_tail_merge_tokens_retained', 'old_tail_merge_tokens_excluded_validation',
        'old_tail_merge_tokens_incomplete_tail')})
    cursor, ordinal, tail_seen = 0, 0, False
    for row in events:
        n, m = row.get('old_ids'), row.get('new_ids')
        if (tail_seen or type(n) is not int or n <= 0 or type(m) is not int or m < 0
                or n > MAX_SEGMENT_IDS or m > MAX_BODY_BYTES + 1
                or type(row.get('segment')) is not int or row['segment'] != ordinal
                or type(row.get('old_offset')) is not int or row['old_offset'] != cursor):
            raise ValueError('entire ordered input consumer/offset/last-tail ledger required')
        tail_merges = row.get('old_tail_merge_tokens')
        if (type(tail_merges) is not int or not 0 <= tail_merges <= n
                or not re.fullmatch('[0-9A-F]{64}', row.get('old_ids_sha256', ''))):
            raise ValueError('exact old segment/tail-merge/hash receipt required')
        cursor += n; ordinal += 1
        observed.update(old_input_ids=n, old_tail_merge_tokens=row['old_tail_merge_tokens'])
        disposition = row['disposition']
        if disposition == 'EXCLUDE_INCOMPLETE_TAIL':
            if m != 0 or row.get('utf8') != 'NOT_DECODED_INCOMPLETE':
                raise ValueError('incomplete tail cannot produce training IDs')
            observed.update(old_incomplete_tail_ids=n, old_tail_merge_tokens_incomplete_tail=tail_merges)
            tail_seen = True
        elif disposition in ('KEEP', 'EXCLUDE_VALIDATION'):
            if m < 1 or bool(row.get('exclusion_reasons')) != (disposition == 'EXCLUDE_VALIDATION'):
                raise ValueError('complete keep/drop/EOS outcome differs')
            if (type(row.get('body_bytes')) is not int or not 0 <= row['body_bytes'] <= MAX_BODY_BYTES
                    or not re.fullmatch('[0-9A-F]{64}', row.get('body_sha256', ''))
                    or not re.fullmatch('[0-9A-F]{64}', row.get('new_ids_sha256', ''))):
                raise ValueError('exact byte/current-ID hash ledger required')
            observed.update(old_complete_ids=n, new_canonical_ids=m, complete_segments=1,
                verified_body_bytes=row['body_bytes'], old_tail_merge_tokens_converted=tail_merges)
            if disposition == 'KEEP':
                observed.update(old_kept_ids=n, new_kept_ids=m, kept_segments=1,
                                old_tail_merge_tokens_retained=tail_merges)
            else:
                observed.update(old_excluded_ids=n, new_excluded_ids=m, excluded_segments=1,
                                old_tail_merge_tokens_excluded_validation=tail_merges)
        else: raise ValueError('registered segment disposition required')
    if any(value != expected.get(key) for key, value in observed.items()):
        raise ValueError('complete input/drop/tail/byte/token ledger totals differ')
    if (cursor != expected['old_input_ids'] or expected['old_input_ids'] !=
            expected['old_kept_ids'] + expected['old_excluded_ids'] + expected['old_incomplete_tail_ids']
            or expected['new_canonical_ids'] != expected['new_kept_ids'] + expected['new_excluded_ids']):
        raise ValueError('input and output conservation failed')
    return dict(observed, ledger_events=ordinal, tail_seen=tail_seen)


def readback_stage():
    built = read_report('build'); verify_source(built['source'])
    pilot, budget = read_report('pilot'), read_report('budget')
    if (built['budget_report_sha256'] != digest(report_path('budget'))
            or built['pilot_report_sha256'] != digest(report_path('pilot'))
            or sha(pilot['source']) != sha(built['source'])
            or built['source_train_sha256'] != budget['source_train_sha256']):
        raise ValueError('same completed CPU source/pilot/budget/build receipts required')
    meta = read_json(CACHE / 'meta.json'); stats = built['metrics']; count = meta['train']
    if (digest(CACHE / 'meta.json') != built['meta_sha256']
            or meta.get('tag') != TAG or meta.get('code_sha256') != info()['code_sha256']
            or meta.get('tokenizer_sha256') != CURRENT_TOKENIZER_SHA
            or meta.get('token_dtype') != 'uint16' or meta.get('byte_order') != 'little'
            or type(count) is not int or count != stats['new_kept_ids']
            or meta.get('val') != 0 or stats['old_input_ids'] != EXPECTED_OLD_IDS
            or stats['consumer_old_ids_sha256'] != budget['source_train_sha256']
            or stats['old_special_counts'].get('2', 0) != stats['complete_segments']
            or safe(CACHE / 'train.bin').stat().st_size != 2 * count):
        raise ValueError('exact full consumer/source SHA/converted cache metadata required')
    eos, last = 0, None
    with read_path(CACHE / 'train.bin').open('rb') as stream:
        reader = UInt16Input(stream, count)
        for index in reader:
            if not 0 <= index < EXPECTED_VOCAB: raise ValueError('converted ID outside chat32')
            eos += index == EOS; last = index
    if (reader.count != count or reader.hexdigest() != built['output_sha256']
            or reader.hexdigest() != meta['train_sha256'] or reader.hexdigest() != stats['retained_ids_sha256']
            or eos != stats['kept_segments'] or (count > 0 and last != EOS)):
        raise ValueError('all converted IDs/hash/kept segments/last EOS required')
    manifest = read_json(CACHE / 'segments/segments_shards_manifest.json')
    if (sha(manifest) != sha(built['audit_manifest'])
            or digest(CACHE / 'segments/segments_shards_manifest.json') != built['audit_manifest_sha256']
            or manifest.get('lineage') != dict(tag=TAG, kind='EOS_CACHE_SEGMENT_AUDIT',
                                             source_train_sha256=budget['source_train_sha256'])):
        raise ValueError('whole EOS-cache ledger lineage/manifest SHA differs')
    verify(safe(CACHE / 'segments'), manifest)
    def events():
        for spec in manifest['shards']:
            with read_path(CACHE / 'segments' / spec['path']).open(encoding='utf-8') as stream:
                for line in stream: yield json.loads(line)
    observed = recount_audit(events(), stats); verify_source(built['source'])
    return dict(status='FULL_CACHE_READBACK_COMPLETE', source=built['source'],
        build_report_sha256=digest(report_path('build')), actual_output_ids=count,
        actual_output_sha256=reader.hexdigest(), actual_eos_segments=eos, last_id=last,
        empty_pool=count == 0, full_input_consumer=observed,
        source_train_sha256_verified_by_completed_build_stream=budget['source_train_sha256'],
        original_source_rehash_in_readback=False, pool2draw=built['pool2draw'],
        actual_cache_usable=count > 1024, semantic_or_language_quality='NOT_ESTABLISHED',
        model_gpu_training='NOT_RUN', unique_information='NOT_MEASURED')


def preflight(mode, *, allow_full_scan=False, allow_full_build=False, max_wall_sec=1200, host=None):
    if mode not in MODES: raise ValueError('registered CPU-only target required')
    if not info()['code_complete']: raise Pending('all new/shared code files required')
    if CACHE != ROOT / 'data_cache' / TAG or EVIDENCE != ROOT / 'test_result/evidence' / TAG:
        raise ValueError('exact ignored raw-cache and small-evidence namespaces required')
    if report_path(mode).exists() or activity_path(mode).exists():
        raise FileExistsError('write-once complete/partial phase artifacts preserved')
    if mode == 'source':
        if CACHE.exists() or EVIDENCE.exists(): raise FileExistsError('first source must own a fresh namespace')
        source_snapshot()
    else:
        source = read_report('source'); verify_source(source['source'])
        if mode in ('budget', 'build', 'readback'): read_report('pilot')
        if mode == 'budget':
            if not allow_full_scan: raise Pending('explicit --allow-full-scan required for whole TRAIN hash')
            host_measurement(host)
        if mode == 'build':
            if not allow_full_build: raise Pending('explicit --allow-full-build required')
            host_now = host_measurement(host)
            validate_build_budget(read_report('budget'), read_report('pilot'), max_wall_sec,
                free_bytes=guest_disk_measurement()['free_bytes'], host_free_bytes=host_now['free_bytes'],
                remaining_seconds=authority('build'))
        if mode == 'readback':
            read_report('build')
            validate_readback_budget(read_report('budget'), max_wall_sec,
                                     remaining_seconds=authority('readback'))
    return dict(target=mode, code_only=False, bin_read=False, gpu=False,
                scope='metadata/prerequisite check only, not conversion/cache quality')


@termination_guard()
def worker(mode, *, max_wall_sec=1200, allow_full_scan=False, allow_full_build=False, draw_ids=None, host=None):
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600:
        raise ValueError('bounded60..21600 worker cap required')
    if mode == 'pilot' and max_wall_sec > PILOT_SECONDS:
        raise ValueError('first-prefix pilot is bounded at1200s')
    if max_wall_sec > authority(mode): raise Pending('worker cap would spend absolute600s record reserve')
    if report_path(mode).exists() or activity_path(mode).exists():
        raise FileExistsError('preserve previous complete/partial CPU phase')
    began, code = time.perf_counter(), 9
    try:
        with single_core_environment(), wall_limit(max_wall_sec):
            preflight(mode, allow_full_scan=allow_full_scan, allow_full_build=allow_full_build,
                      max_wall_sec=max_wall_sec, host=host)
            if mode == 'source': payload = source_stage()
            elif mode == 'pilot': payload = pilot_stage()
            elif mode == 'budget': payload = budget_stage(allow_full_scan=allow_full_scan, host=host)
            elif mode == 'build': payload = build_stage(allow_full_build=allow_full_build,
                    max_wall_sec=max_wall_sec, draw_ids=draw_ids, host=host)
            elif mode == 'readback': payload = readback_stage()
            else: raise ValueError('registered CPU mode required')
            # Recipe and results never share a flat namespace (v1 broad failure).
            result = dict(recipe=info(), mode=mode, **payload)
            write_json(report_path(mode), result)
            code = 0
        print('[NATIVE_CPU_COMPLETE] ' + json.dumps(dict(mode=mode, status=payload['status'],
            model_gpu_training='NOT_RUN')), flush=True)
        return 0
    except Pending:
        code = 8; raise
    except KeyboardInterrupt:
        code = 130; raise
    finally:
        path = report_path(mode)
        write_json(activity_path(mode), dict(schema=SCHEMA, tag=TAG, mode=mode, complete=code == 0,
            returncode=code, seconds=time.perf_counter() - began, max_wall_sec=max_wall_sec,
            code_sha256=info()['code_sha256'], recorded_at=datetime.now(timezone.utc).isoformat(),
            report_path=str(path.relative_to(ROOT)) if path.is_file() else None,
            report_sha256=digest(path) if path.is_file() else None,
            scope='actual CPU worker including all source verification; not model/GPU/training'))


def phase_commands(mode, *, max_wall_sec=1200, allow_full_scan=False, allow_full_build=False, draw_ids=None, host=None):
    if mode not in MODES or type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 21600:
        raise ValueError('registered mode and bounded worker cap required')
    if mode == 'pilot' and max_wall_sec > PILOT_SECONDS: raise ValueError('pilot1200s cap')
    if allow_full_scan and mode != 'budget' or allow_full_build and mode != 'build':
        raise ValueError('full-scan/build flags belong only to their exact phase')
    if draw_ids is not None:
        pool_for_draw(0, draw_ids)
        if mode != 'build': raise ValueError('future optional draw is recorded only by actual build')
    py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT]
    flags = ['--max-wall-sec', str(max_wall_sec)]
    if allow_full_scan: flags += ['--allow-full-scan']
    if allow_full_build: flags += ['--allow-full-build']
    if draw_ids is not None: flags += ['--draw-tokens', str(draw_ids)]
    if host is not None:
        if mode not in ('budget', 'build') or set(host) != {'free_bytes', 'measured_at', 'label', 'evidence_path'}:
            raise ValueError('complete root host input belongs only to budget/build')
        flags += ['--host-free-bytes', str(host['free_bytes']), '--host-measured-at', str(host['measured_at']),
                  '--host-storage-label', str(host['label']), '--host-evidence-path', str(host['evidence_path'])]
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_native_expansion', '-v']),
            ('PREFLIGHT', base + ['--mode', 'preflight', '--target-mode', mode, '--worker', '--execute'] + flags),
            ('EXECUTE', base + ['--mode', mode, '--worker', '--execute'] + flags)]


def launch(command, timeout):
    env = dict(os.environ); env.update(THREAD_ENV)
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, start_new_session=True)
    try: return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = sys.exc_info()[0] is KeyboardInterrupt
        try:
            if process.poll() is None and os.getpgid(process.pid) == process.pid:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        except ProcessLookupError: pass
        return 130 if interrupted else 124


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=(*MODES, 'preflight'))
    parser.add_argument('--target-mode', choices=MODES)
    parser.add_argument('--worker', action='store_true'); parser.add_argument('--max-wall-sec', type=int, default=1200)
    parser.add_argument('--allow-full-scan', action='store_true'); parser.add_argument('--allow-full-build', action='store_true')
    parser.add_argument('--draw-tokens', type=int)
    parser.add_argument('--host-free-bytes', type=int); parser.add_argument('--host-measured-at')
    parser.add_argument('--host-storage-label'); parser.add_argument('--host-evidence-path')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        target = args.target_mode if args.mode == 'preflight' else args.mode
        if target is None or args.mode != 'preflight' and args.target_mode is not None:
            raise ValueError('only preflight uses an explicit target-mode')
        values = (args.host_free_bytes, args.host_measured_at, args.host_storage_label, args.host_evidence_path)
        if any(value is not None for value in values) and not all(value is not None for value in values):
            raise ValueError('all four root host-measurement fields required together')
        host = None if all(value is None for value in values) else dict(free_bytes=args.host_free_bytes,
            measured_at=args.host_measured_at, label=args.host_storage_label, evidence_path=args.host_evidence_path)
        phases = phase_commands(target, max_wall_sec=args.max_wall_sec, allow_full_scan=args.allow_full_scan,
            allow_full_build=args.allow_full_build, draw_ids=args.draw_tokens, host=host)
        if args.check_only:
            print('[NATIVE_CPU_CHECK_ONLY] ' + json.dumps(info(), sort_keys=True), flush=True); return 0
        if args.mode == 'preflight':
            if not args.worker: raise ValueError('bounded explicit preflight worker required')
            authority(target)
            with single_core_environment(), wall_limit(min(args.max_wall_sec, PILOT_SECONDS)):
                preflight(target, allow_full_scan=args.allow_full_scan, allow_full_build=args.allow_full_build,
                          max_wall_sec=args.max_wall_sec, host=host)
            print('[NATIVE_CPU_PREFLIGHT] CPU metadata only; bins/model/GPU NOT_RUN', flush=True); return 0
        if args.worker:
            return worker(target, max_wall_sec=args.max_wall_sec, allow_full_scan=args.allow_full_scan,
                          allow_full_build=args.allow_full_build, draw_ids=args.draw_tokens, host=host)
        return pipeline(phases, lambda command: launch(command, min(args.max_wall_sec + 120, authority(target))),
            lambda line: print(line, flush=True), experiment='P106B_NATIVE_EXPANSION_CPU_' + target)['returncode']
    except Pending as exc:
        print('[NATIVE_CPU_FINAL] HOLD8: ' + str(exc), flush=True); return 8
    except KeyboardInterrupt:
        print('[NATIVE_CPU_FINAL] INTERRUPTED130; partial artifacts preserved', flush=True); return 130
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        traceback.print_exc()
        print('[NATIVE_CPU_FINAL] TOOL_ERROR9: ' + str(exc), flush=True); return 9


if __name__ == '__main__':
    raise SystemExit(main())
