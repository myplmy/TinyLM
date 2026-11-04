"""Bounded, hash-bound explicit-document input for the optional P107 path.

This validates bytes and declared admission, not semantic quality, rights or
raw-document provenance. Callers own authorization of the exact input root.
No corpus discovery, preprocessing, downloads or model imports occur here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

SCHEMA = 'P107_DOCUMENT_INPUT_V1'
ADMISSION_SCHEMA = 'P107_TRAIN_DOCUMENT_ADMISSION_V1'
MAX_META_BYTES = 1_000_000
MAX_SHARD_BYTES = 19_999_999
MAX_TOTAL_BYTES = 128_000_000
MAX_TOKENS = 16_000_000
MAX_DOCUMENTS = 100_000
MAX_DOCUMENT_TOKENS = 65_536
PROTECTED = ('datasets/TinyDataset', '.git', '.agents', '.codex', '.claude', '.aws')


def sha256(data):
    return hashlib.sha256(data).hexdigest().upper()


def canonical_sha(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8'))


def _digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789ABCDEF' for c in value)


def _relative(value):
    if not isinstance(value, str) or not value or chr(92) in value:
        raise ValueError('explicit normalized POSIX relative input path required')
    p = PurePosixPath(value)
    if p.is_absolute() or str(p) != value or '..' in p.parts:
        raise ValueError('input traversal or unnormalized path')
    if any(value == prefix or value.startswith(prefix+'/') for prefix in PROTECTED):
        raise ValueError('protected input path')
    return p


def input_path(root, name, allowed_root):
    """Reject forbidden prefixes before stat/open; reject linked ancestors."""
    root = Path(root).absolute()
    relative, prefix = _relative(name), _relative(allowed_root)
    if prefix == PurePosixPath('.') or prefix not in relative.parents:
        raise ValueError('input must be a file under the exact authorized root')
    current = root
    for part in (None, *relative.parts):
        if part is not None:
            current = current/part
        if current.is_symlink():
            raise ValueError('linked input path')
    return root/relative


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate JSON field')
        out[key] = value
    return out


def _json(raw):
    def invalid(_):
        raise ValueError('nonfinite JSON value')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=invalid)


def read_bound(root, ref, allowed_root, *, limit):
    if (not isinstance(ref, dict) or set(ref) != {'path', 'bytes', 'sha256'}
            or type(ref['bytes']) is not int or not 0 < ref['bytes'] <= limit
            or not _digest(ref['sha256'])):
        raise ValueError('exact bounded file descriptor required')
    path = input_path(root, ref['path'], allowed_root)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != ref['bytes']:
            raise ValueError('input file kind or byte count changed')
        raw = stream.read(limit+1)
    if len(raw) != ref['bytes'] or sha256(raw) != ref['sha256']:
        raise ValueError('input file bytes or SHA changed')
    return raw


@dataclass(frozen=True)
class DocumentInput:
    documents: tuple
    source_ids: tuple
    languages: tuple
    declared_source_sha256: tuple
    _contract_json: str

    @property
    def contract(self):
        return json.loads(self._contract_json)

    def as_source(self, *, batch, length, micros, vocab, seed):
        import torch
        from .document_source import ExplicitDocumentSource
        if vocab != self.contract['vocab_size']:
            raise ValueError('source vocabulary differs from admitted input')
        return ExplicitDocumentSource([torch.tensor(x, dtype=torch.long) for x in self.documents],
            self.source_ids, batch=batch, length=length, micros=micros, vocab=vocab, seed=seed)


def load_document_input(root, manifest_ref, *, allowed_root, tokenizer_sha256,
                        vocab_size, allow_admitted=False):
    if (not _digest(tokenizer_sha256) or type(vocab_size) is not int or vocab_size <= 35
            or type(allow_admitted) is not bool):
        raise ValueError('caller must provide the verified tokenizer identity and explicit admission mode')
    raw = read_bound(root, manifest_ref, allowed_root, limit=MAX_META_BYTES)
    m = _json(raw)
    if (not isinstance(m, dict) or set(m) != {'schema', 'purpose', 'split', 'tokenizer', 'admission', 'shards'}
            or m['schema'] != SCHEMA or m['split'] != 'train'
            or not isinstance(m['tokenizer'], dict)
            or type(m['tokenizer'].get('vocab_size')) is not int
            or m['tokenizer'] != dict(sha256=tokenizer_sha256, vocab_size=vocab_size)):
        raise ValueError('document schema, TRAIN split or tokenizer differs')
    a = m['admission']
    if (not isinstance(a, dict) or set(a) != {'status', 'authority_ref', 'training_authorized', 'evidence'}
            or not isinstance(a['authority_ref'], str) or not a['authority_ref'].strip()):
        raise ValueError('explicit admission declaration required')
    shards = m['shards']
    if not isinstance(shards, list) or not 1 <= len(shards) <= 64:
        raise ValueError('bounded explicit shard list required')
    if m['purpose'] == 'SYNTHETIC_TECHNICAL':
        if (a['status'] != 'TECHNICAL_FIXTURE_ONLY' or a['training_authorized'] is not False
                or a['evidence'] is not None):
            raise ValueError('fixture must not claim corpus training admission')
    elif m['purpose'] == 'TRAIN_ADMITTED':
        if not allow_admitted or a['status'] != 'TRAIN_APPROVED' or a['training_authorized'] is not True:
            raise ValueError('corpus training admission is not authorized by this caller')
        evidence = _json(read_bound(root, a['evidence'], allowed_root, limit=MAX_META_BYTES))
        expected = dict(schema=ADMISSION_SCHEMA, split='train', approved_for_training=True,
            authority_ref=a['authority_ref'], tokenizer_sha256=tokenizer_sha256,
            shards_sha256=canonical_sha(shards))
        if (not isinstance(evidence, dict) or evidence != expected
                or evidence.get('approved_for_training') is not True):
            raise ValueError('admission evidence does not bind these exact shards')
    else:
        raise ValueError('unknown document purpose')
    documents, ids, languages, declared = [], [], [], []
    total_bytes = total_tokens = 0
    seen_paths, seen_ids, token_hashes = set(), set(), set()
    duplicate_tokens = 0
    for item in shards:
        if not isinstance(item, dict) or set(item) != {'file', 'documents', 'tokens'}:
            raise ValueError('explicit shard counts required')
        if (type(item['documents']) is not int or not 0 < item['documents'] <= MAX_DOCUMENTS
                or type(item['tokens']) is not int or not 0 < item['tokens'] <= MAX_TOKENS):
            raise ValueError('invalid shard counts')
        ref = item['file']
        if not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or ref['path'] in seen_paths:
            raise ValueError('duplicate or invalid shard descriptor')
        seen_paths.add(ref['path'])
        raw = read_bound(root, ref, allowed_root, limit=MAX_SHARD_BYTES)
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError('aggregate input byte budget exceeded')
        shard_documents = shard_tokens = 0
        for line in raw.splitlines():
            if not line.strip():
                raise ValueError('blank document record')
            row = _json(line)
            if not isinstance(row, dict) or set(row) != {'source_id', 'token_ids', 'language', 'source_sha256'}:
                raise ValueError('explicit document record required')
            name, tokens = row['source_id'], row['token_ids']
            if (not isinstance(name, str) or not 0 < len(name) <= 256 or not name.strip()
                    or any(ord(c) < 32 for c in name) or name in seen_ids):
                raise ValueError('duplicate or invalid source ID')
            valid_languages = ('synthetic',) if m['purpose'] == 'SYNTHETIC_TECHNICAL' else ('ko', 'en', 'mixed', 'und')
            if row['language'] not in valid_languages or not _digest(row['source_sha256']):
                raise ValueError('language or declared source hash differs')
            if (not isinstance(tokens, list) or not 3 <= len(tokens) <= MAX_DOCUMENT_TOKENS
                    or any(type(t) is not int or not 0 <= t < vocab_size or t == 13 for t in tokens)):
                raise ValueError('document tokens must be exact IDs without the reserved mask')
            token_hash = canonical_sha(tokens)
            duplicate_tokens += token_hash in token_hashes
            token_hashes.add(token_hash)
            seen_ids.add(name)
            documents.append(tuple(tokens)); ids.append(name)
            languages.append(row['language']); declared.append(row['source_sha256'])
            shard_documents += 1; shard_tokens += len(tokens); total_tokens += len(tokens)
            if len(documents) > MAX_DOCUMENTS or total_tokens > MAX_TOKENS:
                raise ValueError('aggregate document/token budget exceeded')
        if shard_documents != item['documents'] or shard_tokens != item['tokens']:
            raise ValueError('actual document/token totals differ from the sealed shard')
    contract = dict(schema=SCHEMA, purpose=m['purpose'], split='train',
        manifest_sha256=manifest_ref['sha256'], tokenizer_sha256=tokenizer_sha256,
        vocab_size=vocab_size, shards_sha256=canonical_sha(shards),
        admission_status=a['status'], authority_ref=a['authority_ref'],
        documents=len(documents), tokens=total_tokens, file_bytes=total_bytes,
        duplicate_token_documents=duplicate_tokens, dropped_documents=0,
        source_sha256_validation='DECLARED_ONLY_RAW_SOURCE_NOT_READ',
        semantic_rights_leakage_review='NOT_PERFORMED_BY_THIS_BYTE_CONTRACT')
    return DocumentInput(tuple(documents), tuple(ids), tuple(languages), tuple(declared),
                         json.dumps(contract, sort_keys=True, separators=(',', ':')))
