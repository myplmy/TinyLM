"""Lossless, content-addressed storage for this session's selection metadata.

Corpus bodies are never opened here.  A manifest pins ordered JSON row shards;
its logical digest covers the original native dict encoded as compact UTF-8.
Frozen consumers can opt in for explicitly pinned manifests without changing
Path.read_bytes (which must continue to hash the actual on-disk file).
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import re

AUDIT = Path(__file__).resolve().parent
FORMAT = 'TINYLM_SELECTION_ROWS_V1'
FORMAT_KEY = 'selection_storage_schema'
SHARD_DIRECTORY = 'selection_metadata_row_shards_v1'
FILE_LIMIT = 20_000_000
SHARD_LIMIT = 4_000_000
ROWS_PER_SHARD = 512
_NATIVE_LOADS = json.loads


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                       allow_nan=False) + chr(10)).encode('utf-8')


def validate_native(document):
    require(isinstance(document, dict) and FORMAT_KEY not in document,
            'native selection must be a dict without the storage marker')
    rows = document.get('rows')
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            'selection rows must be dictionaries')
    require(type(document.get('source_ids')) is int and
            document['source_ids'] == len(rows), 'source_ids differs')
    ids = [row.get('id') for row in rows]
    require(all(isinstance(key, str) and key for key in ids), 'invalid row id')
    require(len(ids) == len(set(ids)), 'duplicate selection row id')


class SelectionStore:
    def __init__(self, directory=AUDIT):
        directory = Path(directory).absolute()
        require(not directory.is_symlink(), 'audit directory is a symlink')
        self.directory = directory.resolve()

    def selection_path(self, path):
        path = Path(path).absolute()
        require(path.parent == self.directory, 'selection outside exact audit directory')
        require(re.fullmatch(r'ROOT_AUTHORED_SELECTIONS_V[1-9][0-9]*\.json', path.name)
                is not None, 'unexpected selection filename')
        require(not path.is_symlink(), 'selection is a symlink')
        return path

    @staticmethod
    def read_small(path, expected=None, expected_bytes=None):
        require(not path.is_symlink() and path.is_file(), 'missing or symlinked metadata')
        size = path.stat().st_size
        require(0 < size < FILE_LIMIT, 'metadata file must be below 20MB')
        if expected_bytes is not None:
            require(size == expected_bytes, 'metadata length differs')
        raw = path.read_bytes()
        require(len(raw) == size, 'metadata changed while reading')
        if expected is not None:
            require(digest(raw) == expected, 'metadata SHA differs')
        return raw

    def shard_path(self, pin):
        sha = pin.get('sha256')
        require(isinstance(sha, str) and re.fullmatch(r'[0-9A-F]{64}', sha) is not None,
                'invalid shard SHA')
        expected_name = SHARD_DIRECTORY + '/' + sha + '.json'
        require(pin.get('path') == expected_name, 'shard path must be content addressed')
        parent = self.directory / SHARD_DIRECTORY
        require(not parent.is_symlink(), 'shard directory is a symlink')
        path = parent / (sha + '.json')
        require(not path.is_symlink(), 'shard is a symlink')
        return path

    def decode(self, path, raw):
        value = _NATIVE_LOADS(raw)
        if not isinstance(value, dict) or FORMAT_KEY not in value:
            validate_native(value)
            return value
        require(value[FORMAT_KEY] == FORMAT, 'unknown selection storage version')
        require(set(value) == {FORMAT_KEY, 'logical_name', 'native_key_order',
                'native_metadata', 'row_shards', 'source_ids', 'logical_json_bytes',
                'logical_json_sha256', 'canonical_encoding'}, 'unexpected manifest keys')
        require(value['logical_name'] == path.name, 'manifest logical filename differs')
        require(value['canonical_encoding'] == 'UTF8_COMPACT_JSON_PLUS_LF_V1',
                'unknown logical encoding')
        keys = value['native_key_order']
        metadata = value['native_metadata']
        require(isinstance(keys, list) and all(isinstance(k, str) for k in keys)
                and len(keys) == len(set(keys)) and keys.count('rows') == 1,
                'invalid native key order')
        require(isinstance(metadata, dict) and set(metadata) == set(keys) - {'rows'},
                'native metadata keys differ')
        require(FORMAT_KEY not in metadata, 'nested storage manifest is forbidden')
        pins = value['row_shards']
        require(isinstance(pins, list), 'row_shards must be a list')
        rows = []
        for pin in pins:
            require(isinstance(pin, dict) and set(pin) == {'path', 'sha256', 'bytes', 'rows'},
                    'invalid shard pin')
            require(type(pin['rows']) is int and 0 < pin['rows'] <= ROWS_PER_SHARD,
                    'invalid shard row count')
            require(type(pin['bytes']) is int and 0 < pin['bytes'] <= SHARD_LIMIT,
                    'invalid shard byte count')
            shard = self.shard_path(pin)
            shard_raw = self.read_small(shard, pin['sha256'], pin['bytes'])
            group = _NATIVE_LOADS(shard_raw)
            require(isinstance(group, list) and len(group) == pin['rows'],
                    'shard rows differ')
            require(encode(group) == shard_raw, 'shard is not canonical UTF-8 JSON')
            rows.extend(group)
        require(type(value['source_ids']) is int and len(rows) == value['source_ids'],
                'manifest source count differs')
        result = {key: rows if key == 'rows' else metadata[key] for key in keys}
        validate_native(result)
        logical = encode(result)
        require(len(logical) == value['logical_json_bytes'], 'logical JSON length differs')
        require(digest(logical) == value['logical_json_sha256'], 'logical JSON SHA differs')
        return result

    def read(self, path, expected=None):
        path = self.selection_path(path)
        return self.decode(path, self.read_small(path, expected))

    def write(self, path, document, *, force_sharded=False):
        path = self.selection_path(path)
        require(not path.exists(), 'selection already exists; overwrite forbidden')
        validate_native(document)
        logical = encode(document)
        if not force_sharded and len(logical) < FILE_LIMIT:
            with path.open('xb') as stream:
                stream.write(logical)
            return dict(path=str(path), sha256=digest(logical), bytes=len(logical),
                        storage='INLINE', row_shards=0, created_shards=0,
                        reused_shards=0, logical_json_sha256=digest(logical))
        # Build and validate every planned file before publishing any file.
        groups, group, group_size = [], [], 3
        for row in document['rows']:
            row_size = len(encode(row)) - 1
            require(row_size + 3 <= SHARD_LIMIT, 'single metadata row exceeds shard bound')
            if group and (len(group) >= ROWS_PER_SHARD or
                          group_size + row_size + 1 > SHARD_LIMIT):
                groups.append(group)
                group, group_size = [], 3
            group.append(row)
            group_size += row_size + (1 if len(group) > 1 else 0)
        if group:
            groups.append(group)
        planned = []
        for group in groups:
            raw = encode(group)
            require(len(raw) <= SHARD_LIMIT, 'planned shard exceeds bound')
            sha = digest(raw)
            pin = dict(path=SHARD_DIRECTORY + '/' + sha + '.json', sha256=sha,
                       bytes=len(raw), rows=len(group))
            planned.append((pin, raw))
        header = {FORMAT_KEY: FORMAT, 'logical_name': path.name,
                  'native_key_order': list(document),
                  'native_metadata': {k: v for k, v in document.items() if k != 'rows'},
                  'row_shards': [pin for pin, _ in planned],
                  'source_ids': len(document['rows']),
                  'logical_json_bytes': len(logical),
                  'logical_json_sha256': digest(logical),
                  'canonical_encoding': 'UTF8_COMPACT_JSON_PLUS_LF_V1'}
        header_raw = encode(header)
        require(len(header_raw) < FILE_LIMIT, 'selection header exceeds bound')
        directory = self.directory / SHARD_DIRECTORY
        require(not directory.is_symlink(), 'shard directory is a symlink')
        directory.mkdir(exist_ok=True)
        created = reused = created_bytes = 0
        for pin, raw in planned:
            shard = self.shard_path(pin)
            if shard.exists():
                require(self.read_small(shard, pin['sha256'], pin['bytes']) == raw,
                        'existing content-addressed shard differs')
                reused += 1
            else:
                with shard.open('xb') as stream:
                    stream.write(raw)
                created += 1
                created_bytes += len(raw)
        require(self.decode(path, header_raw) == document,
                'independent reconstruction differs before manifest publication')
        with path.open('xb') as stream:
            stream.write(header_raw)
        return dict(path=str(path), sha256=digest(header_raw), bytes=len(header_raw),
                    storage=FORMAT, row_shards=len(planned), created_shards=created,
                    reused_shards=reused, logical_json_sha256=digest(logical),
                    logical_json_bytes=len(logical),
                    created_shard_bytes=created_bytes)


@contextmanager
def bound_selection_loads(pins, *, directory=AUDIT):
    """Allow frozen json.load/loads only for these exact on-disk selection pins.

    Ordinary JSON goes directly to the original decoder.  Unbound manifest
    headers are rejected.  Every result is a fresh dict/list, just like loads.
    Physical file hashing remains untouched.
    """
    store = SelectionStore(directory)
    allowed = {}
    for path, sha in pins:
        path = store.selection_path(path)
        raw = store.read_small(path, sha)
        decoded = _NATIVE_LOADS(raw)
        if isinstance(decoded, dict) and FORMAT_KEY in decoded:
            allowed[digest(raw)] = store.decode(path, raw)

    def loads(raw, *args, **kwargs):
        binary = raw.encode('utf-8') if isinstance(raw, str) else raw
        if isinstance(binary, (bytes, bytearray)) and \
                FORMAT_KEY.encode('ascii') in binary:
            # A quoted example containing the key is still ordinary JSON.
            document = _NATIVE_LOADS(raw)
            if isinstance(document, dict) and FORMAT_KEY in document:
                require(not args and all(value is None for value in kwargs.values()),
                        'custom decoder options for storage manifest are forbidden')
                sha = digest(binary)
                require(sha in allowed, 'selection manifest is not explicitly SHA bound')
                return deepcopy(allowed[sha])
        return _NATIVE_LOADS(raw, *args, **kwargs)

    with patch.object(json, 'loads', loads):
        yield store
