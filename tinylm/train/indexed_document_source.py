"""Optional offset-indexed explicit documents, with bounded token payload reads.

The existing resident input/source and CLI are unchanged. This validates sealed
bytes and declared admission, not rights, semantics or raw-source provenance.
Callers authorize the exact root. No corpus discovery or file writes occur.
"""
from __future__ import annotations

from array import array
from bisect import bisect_right
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
from itertools import accumulate
import json
import os
from pathlib import Path
import stat
import sys

import torch

from . import document_input as legacy


@dataclass(frozen=True)
class IndexLimits:
    total_tokens: int = 16_000_000
    total_bytes: int = 128_000_000
    documents: int = 100_000
    metadata_bytes: int = 32_000_000
    record_bytes: int = 1_000_000
    shards: int = 64

    def __post_init__(self):
        hard = (75_000_000, 1_280_000_000, 100_000, 32_000_000, 1_000_000, 64)
        if any(type(v) is not int or not 0 < v <= cap for v, cap in zip(asdict(self).values(), hard)):
            raise ValueError('explicit positive indexed-input limits exceed the hard profile')


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _root(root):
    path = Path(root).absolute()
    parts = path.parts
    if (any(part in ('.git', '.agents', '.codex', '.claude', '.aws') for part in parts)
            or any(parts[i:i+2] == ('datasets', 'TinyDataset') for i in range(len(parts)-1))):
        raise ValueError('protected root rejected before filesystem queries')
    return path


@dataclass(frozen=True)
class BoundFile:
    path: str
    bytes: int
    sha256: str
    stamp: tuple

    @property
    def ref(self):
        return dict(path=self.path, bytes=self.bytes, sha256=self.sha256)


@contextmanager
def _open_ref(root, ref, allowed_root, limit, expected=None):
    if (not isinstance(ref, dict) or set(ref) != {'path', 'bytes', 'sha256'}
            or type(ref['bytes']) is not int or not 0 < ref['bytes'] <= limit
            or not legacy._digest(ref['sha256'])):
        raise ValueError('exact bounded file reference required')
    _root(Path(root) / legacy._relative(ref['path']))
    path = legacy.input_path(root, ref['path'], allowed_root)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        identity = _stamp(info)
        if (not stat.S_ISREG(info.st_mode) or info.st_size != ref['bytes']
                or expected is not None and identity != expected):
            raise ValueError('input kind, size or sealed file identity changed')
        yield stream, identity
        if _stamp(os.fstat(stream.fileno())) != identity:
            raise ValueError('input changed during the bounded read')


def _meta(root, ref, allowed_root):
    with _open_ref(root, ref, allowed_root, legacy.MAX_META_BYTES) as (stream, identity):
        raw = stream.read(legacy.MAX_META_BYTES+1)
        if len(raw) != ref['bytes'] or legacy.sha256(raw) != ref['sha256']:
            raise ValueError('metadata bytes or SHA differ')
    return legacy._json(raw), BoundFile(**ref, stamp=identity)


def _manifest(root, manifest_ref, allowed_root, tokenizer_sha256, vocab_size, allow_admitted, limits, split):
    if (not legacy._digest(tokenizer_sha256) or type(vocab_size) is not int
            or not 35 < vocab_size < 2**63 or type(allow_admitted) is not bool
            or not isinstance(limits, IndexLimits)):
        raise ValueError('verified tokenizer/vocabulary, explicit admission mode and limits required')
    m, bound = _meta(root, manifest_ref, allowed_root)
    if (not isinstance(m, dict) or set(m) != {'schema', 'purpose', 'split', 'tokenizer', 'admission', 'shards'}
            or m['schema'] != legacy.SCHEMA or m['split'] != split
            or not isinstance(m['tokenizer'], dict)
            or type(m['tokenizer'].get('vocab_size')) is not int
            or m['tokenizer'] != dict(sha256=tokenizer_sha256, vocab_size=vocab_size)):
        raise ValueError('explicit document split or tokenizer contract differs')
    a = m['admission']
    if (not isinstance(a, dict) or set(a) != {'status', 'authority_ref', 'training_authorized', 'evidence'}
            or not isinstance(a['authority_ref'], str) or not a['authority_ref'].strip()):
        raise ValueError('explicit admission declaration required')
    shards = m['shards']
    if not isinstance(shards, list) or not 1 <= len(shards) <= limits.shards:
        raise ValueError('bounded explicit shard list required')
    files = [bound]
    if m['purpose'] == 'SYNTHETIC_TECHNICAL':
        if (a['status'] != 'TECHNICAL_FIXTURE_ONLY' or a['training_authorized'] is not False
                or a['evidence'] is not None):
            raise ValueError('fixture cannot claim language-training admission')
    elif m['purpose'] == 'TRAIN_ADMITTED':
        if split != 'train' or not allow_admitted or a['status'] != 'TRAIN_APPROVED' or a['training_authorized'] is not True:
            raise ValueError('caller did not authorize admitted TRAIN input')
        evidence, evidence_file = _meta(root, a['evidence'], allowed_root)
        expected = dict(schema=legacy.ADMISSION_SCHEMA, split='train', approved_for_training=True,
            authority_ref=a['authority_ref'], tokenizer_sha256=tokenizer_sha256,
            shards_sha256=legacy.canonical_sha(shards))
        if (not isinstance(evidence, dict) or evidence != expected
                or evidence.get('approved_for_training') is not True):
            raise ValueError('admission evidence does not bind the exact shard list')
        files.append(evidence_file)
    elif m['purpose'] == 'EVAL_ADMITTED':
        if split != 'val' or not allow_admitted or a['status'] != 'EVAL_APPROVED' or a['training_authorized'] is not False:
            raise ValueError('caller did not authorize admitted validation input')
        evidence, evidence_file = _meta(root, a['evidence'], allowed_root)
        expected = dict(schema=legacy.ADMISSION_SCHEMA, split='val', approved_for_evaluation=True,
            authority_ref=a['authority_ref'], tokenizer_sha256=tokenizer_sha256,
            shards_sha256=legacy.canonical_sha(shards))
        if (not isinstance(evidence, dict) or evidence != expected
                or evidence.get('approved_for_evaluation') is not True):
            raise ValueError('validation evidence does not bind the exact shard list')
        files.append(evidence_file)
    else:
        raise ValueError('unknown document purpose')
    seen = set()
    declared_bytes = declared_tokens = declared_documents = 0
    for item in shards:
        if (not isinstance(item, dict) or set(item) != {'file', 'documents', 'tokens'}
                or type(item['documents']) is not int or not 0 < item['documents'] <= limits.documents
                or type(item['tokens']) is not int or not 0 < item['tokens'] <= limits.total_tokens):
            raise ValueError('bounded shard counts required')
        ref = item['file']
        if (not isinstance(ref, dict) or set(ref) != {'path', 'bytes', 'sha256'}
                or not isinstance(ref['path'], str) or ref['path'] in seen
                or type(ref['bytes']) is not int or not 0 < ref['bytes'] <= legacy.MAX_SHARD_BYTES
                or not legacy._digest(ref['sha256'])):
            raise ValueError('duplicate or invalid bounded shard reference')
        legacy._relative(ref['path'])
        seen.add(ref['path'])
        declared_bytes += ref['bytes']
        declared_tokens += item['tokens']
        declared_documents += item['documents']
    if (declared_bytes > limits.total_bytes or declared_tokens > limits.total_tokens
            or declared_documents > limits.documents):
        raise ValueError('aggregate declared input budget exceeded before shard reads')
    return m, files


def _row(raw, purpose, vocab):
    row = legacy._json(raw)
    if not isinstance(row, dict) or set(row) != {'source_id', 'token_ids', 'language', 'source_sha256'}:
        raise ValueError('exact explicit document row required')
    name, tokens = row['source_id'], row['token_ids']
    languages = ('synthetic',) if purpose == 'SYNTHETIC_TECHNICAL' else ('ko', 'en', 'mixed', 'und')
    if (not isinstance(name, str) or not 0 < len(name) <= 256 or not name.strip()
            or any(ord(c) < 32 for c in name) or row['language'] not in languages
            or not legacy._digest(row['source_sha256'])):
        raise ValueError('source identity, language or declared SHA differs')
    if (not isinstance(tokens, list) or not 3 <= len(tokens) <= legacy.MAX_DOCUMENT_TOKENS
            or any(type(t) is not int or not 0 <= t < vocab or t == 13 for t in tokens)):
        raise ValueError('exact bounded token IDs without reserved mask required')
    return row


@dataclass(frozen=True)
class Record:
    shard: int
    offset: int
    bytes: int
    sha256: str
    source_id: str
    tokens: int
    language: str
    declared_source_sha256: str
    token_sha256: str


@dataclass(frozen=True)
class IndexedDocumentInput:
    root: Path
    allowed_root: str
    records: tuple
    shards: tuple
    metadata_files: tuple
    _contract_json: str

    @property
    def contract(self):
        return json.loads(self._contract_json)

    @property
    def source_ids(self):
        return tuple(row.source_id for row in self.records)

    def validate_files(self):
        for ref in (*self.metadata_files, *self.shards):
            with _open_ref(self.root, ref.ref, self.allowed_root, max(legacy.MAX_META_BYTES, legacy.MAX_SHARD_BYTES), ref.stamp):
                pass

    def read_tokens(self, index):
        row = self.records[index]
        shard = self.shards[row.shard]
        with _open_ref(self.root, shard.ref, self.allowed_root, legacy.MAX_SHARD_BYTES, shard.stamp) as (stream, _):
            stream.seek(row.offset)
            raw = stream.read(row.bytes)
            if len(raw) != row.bytes or legacy.sha256(raw) != row.sha256:
                raise ValueError('selected document bytes or row SHA changed')
        value = _row(raw, self.contract['purpose'], self.contract['vocab_size'])
        if (value['source_id'] != row.source_id or len(value['token_ids']) != row.tokens
                or value['language'] != row.language or value['source_sha256'] != row.declared_source_sha256):
            raise ValueError('selected document differs from the validated index')
        return value['token_ids']

    def as_source(self, *, batch, length, micros, vocab, seed, pad_id=0, packed=False):
        return IndexedDocumentSource(self, batch=batch, length=length, micros=micros,
            vocab=vocab, seed=seed, pad_id=pad_id, packed=packed)


def load_indexed_document_input(root, manifest_ref, *, allowed_root, tokenizer_sha256,
                                vocab_size, allow_admitted=False, limits=None, split='train'):
    root = _root(root)
    if split not in ('train', 'val'):
        raise ValueError('only an explicit train or val split is supported')
    limits = IndexLimits() if limits is None else limits
    m, metadata = _manifest(root, manifest_ref, allowed_root, tokenizer_sha256, vocab_size, allow_admitted, limits, split)
    records, shards = [], []
    ids, token_hashes = set(), set()
    corpus = hashlib.sha256()
    total_tokens = total_bytes = metadata_bytes = duplicates = max_record = max_tokens = 0
    if sys.byteorder != 'little' or array('q').itemsize != 8:
        raise ValueError('this exact resident-byte oracle requires little-endian int64')
    for shard_index, item in enumerate(m['shards']):
        ref = item['file']
        count = tokens = offset = 0
        digest = hashlib.sha256()
        with _open_ref(root, ref, allowed_root, legacy.MAX_SHARD_BYTES) as (stream, identity):
            while True:
                raw = stream.readline(limits.record_bytes+1)
                if not raw:
                    break
                if len(raw) > limits.record_bytes or not raw.strip():
                    raise ValueError('raw document record budget or blank row')
                value = _row(raw, m['purpose'], vocab_size)
                name, values = value['source_id'], value['token_ids']
                if name in ids:
                    raise ValueError('duplicate source ID; no silent row dropping')
                ids.add(name)
                token_hash = legacy.canonical_sha(values)
                duplicates += token_hash in token_hashes
                token_hashes.add(token_hash)
                record = Record(shard_index, offset, len(raw), legacy.sha256(raw), name,
                    len(values), value['language'], value['source_sha256'], token_hash)
                metadata_bytes += len(json.dumps(asdict(record), sort_keys=True,
                    ensure_ascii=False, separators=(',', ':')).encode('utf-8'))+1
                total_tokens += len(values)
                if (len(records)+1 > limits.documents or total_tokens > limits.total_tokens
                        or metadata_bytes > limits.metadata_bytes):
                    raise ValueError('actual document/token/index metadata budget exceeded')
                records.append(record)
                encoded = name.encode('utf-8')
                corpus.update(len(encoded).to_bytes(8, 'little'));corpus.update(encoded)
                corpus.update(len(values).to_bytes(8, 'little'));corpus.update(array('q', values).tobytes())
                digest.update(raw)
                count += 1;tokens += len(values);offset += len(raw)
                max_record = max(max_record, len(raw));max_tokens = max(max_tokens, len(values))
                del value, values, raw
            if (count != item['documents'] or tokens != item['tokens'] or offset != ref['bytes']
                    or digest.hexdigest().upper() != ref['sha256']):
                raise ValueError('actual shard counts/bytes/SHA differ')
        shards.append(BoundFile(**ref, stamp=identity))
        total_bytes += offset
    contract = dict(schema='P107_INDEXED_DOCUMENT_INPUT_V1', purpose=m['purpose'], split=split,
        manifest_sha256=manifest_ref['sha256'], tokenizer_sha256=tokenizer_sha256, vocab_size=vocab_size,
        shards_sha256=legacy.canonical_sha(m['shards']), admission_status=m['admission']['status'],
        authority_ref=m['admission']['authority_ref'], documents=len(records), tokens=total_tokens,
        file_bytes=total_bytes, duplicate_token_documents=duplicates, dropped_documents=0,
        corpus_sha256=corpus.hexdigest().upper(), limits=asdict(limits),
        serialized_record_metadata_bytes=metadata_bytes, max_raw_record_bytes=max_record,
        max_document_tokens=max_tokens, retained_document_token_values=0,
        source_sha256_validation='DECLARED_ONLY_RAW_SOURCE_NOT_READ',
        semantic_rights_leakage_review='NOT_PERFORMED_BY_THIS_BYTE_CONTRACT',
        memory_measurement='PAYLOAD_AND_SERIALIZED_INDEX_COUNTERS_NOT_PROCESS_RSS')
    result = IndexedDocumentInput(root, allowed_root, tuple(records), tuple(shards), tuple(metadata),
        json.dumps(contract, sort_keys=True, separators=(',', ':')))
    result.validate_files()
    return result


class IndexedDocumentSource:
    def __init__(self, data, *, batch, length, micros, vocab, seed, pad_id=0, packed=False):
        if (not isinstance(data, IndexedDocumentInput)
                or any(type(x) is not int for x in (batch, length, micros, vocab, seed, pad_id))
                or min(batch, micros) < 1 or length < 2 or vocab != data.contract['vocab_size']
                or not 0 <= pad_id <= 34 or not 0 <= seed < 2**63 or type(packed) is not bool):
            raise ValueError('exact indexed input, integer shape/seed and reserved PAD required')
        self._packed_offsets = (0, *accumulate(row.tokens for row in data.records)) if packed else ()
        if packed and self._packed_offsets[-1] <= length:
            raise ValueError('the indexed documents cannot fill one packed source window')
        data.validate_files()
        self.data = data
        self.batch, self.length, self.micros, self.vocab, self.pad_id = batch, length, micros, vocab, pad_id
        contract = dict(schema='P107_INDEXED_DOCUMENT_SOURCE_V1', input_sha256=legacy.canonical_sha(data.contract),
            corpus_sha256=data.contract['corpus_sha256'], batch=batch, length=length, micros=micros,
            vocab=vocab, seed=seed, pad_id=pad_id, documents=len(data.records),
            sampling=('UNIFORM_PACKED_WINDOW_WITH_REPLACEMENT' if packed
                      else 'UNIFORM_DOCUMENT_WITH_REPLACEMENT_THEN_UNIFORM_FULL_CROP'))
        self._contract_json = json.dumps(contract, sort_keys=True, separators=(',', ':'))
        self.signature = legacy.canonical_sha(contract)
        self.rng = torch.Generator(device='cpu').manual_seed(seed)
        self.cursor, self.active = 0, False
        self.record_reads = self.requested_record_bytes = self.max_decoded_document_tokens = 0

    @property
    def contract(self):
        return json.loads(self._contract_json)

    def _read_document(self, index):
        document = self.data.read_tokens(index)
        self.record_reads += 1
        self.requested_record_bytes += self.data.records[index].bytes
        self.max_decoded_document_tokens = max(self.max_decoded_document_tokens, len(document))
        return document

    def _sample_document(self, tokens, docs):
        index = int(torch.randint(len(self.data.records), (1,), generator=self.rng, device='cpu'))
        document = self._read_document(index)
        start = int(torch.randint(max(1, len(document)-self.length), (1,), generator=self.rng, device='cpu'))
        crop = torch.tensor(document[start:start+self.length+1], dtype=torch.long, device='cpu')
        tokens[:crop.numel()] = crop
        docs[:crop.numel()] = index

    def _sample_packed_window(self, tokens, docs):
        offsets = self._packed_offsets
        start = int(torch.randint(offsets[-1]-self.length, (1,), generator=self.rng, device='cpu'))
        stop = start + self.length + 1
        index = bisect_right(offsets, start) - 1
        written = 0
        while start < stop:
            end = min(stop, offsets[index+1])
            source = slice(start-offsets[index], end-offsets[index])
            output = slice(written, written+end-start)
            tokens[output] = torch.tensor(self._read_document(index)[source], dtype=torch.long, device='cpu')
            docs[output] = index
            written += end-start
            start = end
            index += 1

    def next_update(self):
        if self.active:
            raise ValueError('source update is already active')
        before = self.rng.get_state().clone()
        self.active = True
        try:
            self.data.validate_files()
            output = []
            sample = self._sample_packed_window if self._packed_offsets else self._sample_document
            for _ in range(self.micros):
                tokens = torch.full((self.batch, self.length+1), self.pad_id, dtype=torch.long, device='cpu')
                docs = torch.full_like(tokens, -1)
                for row in range(self.batch):
                    sample(tokens[row], docs[row])
                output.append((tokens, docs))
            self.data.validate_files()
            self.cursor += 1
            return output
        except BaseException:
            self.rng.set_state(before)
            raise
        finally:
            self.active = False

    def state_dict(self):
        if self.active:
            raise ValueError('only a complete source boundary can be stored')
        self.data.validate_files()
        return dict(schema='P107_INDEXED_DOCUMENT_SOURCE_STATE_V1', signature=self.signature,
            cursor=self.cursor, rng=self.rng.get_state().clone())

    def load_state_dict(self, state):
        self.rng.set_state(self.validate_state_dict(state))
        self.cursor = state['cursor']

    def validate_state_dict(self, state):
        if (self.active or not isinstance(state, dict) or set(state) != {'schema', 'signature', 'cursor', 'rng'}
                or state['schema'] != 'P107_INDEXED_DOCUMENT_SOURCE_STATE_V1'
                or state['signature'] != self.signature or type(state['cursor']) is not int or state['cursor'] < 0
                or not isinstance(state['rng'], torch.Tensor) or state['rng'].device.type != 'cpu'
                or state['rng'].dtype != torch.uint8 or state['rng'].ndim != 1):
            raise ValueError('different indexed source/schema/shape or invalid cursor/RNG')
        probe = torch.Generator(device='cpu')
        probe.set_state(state['rng'])
        self.data.validate_files()
        return probe.get_state()
