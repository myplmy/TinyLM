"""CPU checkpoint archival primitives; never construct or run a model.

Only optimizer root fields may be removed. Fingerprints cover every retained
field, tensor byte, view and shared-storage relation, including auxiliary heads.
"""
from collections import OrderedDict
import copy
import hashlib
import io
import json
import pickle
import struct
import zipfile

REMOVE_FIELDS = ('opt', 'opt_muon')


class StorageRef:
    def __init__(self, key):
        self.key = key


class MetadataOnly(pickle.Unpickler):
    """Read tensor descriptors without importing torch or executing globals."""
    def find_class(self, module, name):
        if (module, name) == ('collections', 'OrderedDict'):
            return OrderedDict
        if module == 'torch' and name in (
                'FloatStorage', 'HalfStorage', 'BFloat16Storage', 'LongStorage',
                'IntStorage', 'ByteStorage', 'BoolStorage', 'DoubleStorage'):
            return module, name
        if (module, name) == ('torch._utils', '_rebuild_tensor_v2'):
            return lambda storage, *args: storage
        if (module, name) == ('_codecs', 'encode'):
            def legacy_bytes(text, encoding):
                if type(text) is not str or encoding != 'latin1' or len(text) >= 2_000_000:
                    raise ValueError('unsupported protocol2 byte encoding')
                return text.encode('latin1')
            return legacy_bytes
        raise ValueError('unsupported checkpoint metadata global')

    def persistent_load(self, value):
        if (not isinstance(value, tuple) or len(value) < 5
                or value[0] != 'storage' or not isinstance(value[2], str)):
            raise ValueError('unsupported checkpoint storage metadata')
        return StorageRef(value[2])


def storage_keys(value):
    if isinstance(value, StorageRef):
        return {value.key}
    if isinstance(value, dict):
        return set().union(*(storage_keys(v) for v in value.values())) if value else set()
    if isinstance(value, (tuple, list)):
        return set().union(*(storage_keys(v) for v in value)) if value else set()
    return set()


def metadata(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        pickles = [v for v in entries if v.filename.endswith('/data.pkl')]
        if len(pickles) != 1 or pickles[0].file_size >= 2_000_000:
            raise ValueError('one bounded pickle metadata member required')
        value = MetadataOnly(io.BytesIO(archive.read(pickles[0].filename))).load()
        if not isinstance(value, dict) or 'model' not in value or 'cfg' not in value:
            raise ValueError('model and config metadata required')
        sizes = {v.filename.rsplit('/', 1)[-1]: v.file_size
                 for v in entries if '/data/' in v.filename}
    removed = set().union(*(storage_keys(value[k]) for k in REMOVE_FIELDS if k in value))
    kept = storage_keys({k: v for k, v in value.items() if k not in REMOVE_FIELDS})
    return dict(root_fields=list(value), step=value.get('step'),
        optimizer_fields=[k for k in REMOVE_FIELDS if k in value],
        optimizer_exclusive_bytes=sum(sizes[k] for k in removed-kept))


def retained_payload(value):
    if not isinstance(value, dict) or not all(k in value for k in ('model', 'cfg', 'step')):
        raise ValueError('expected checkpoint dictionary')
    removed = [k for k in REMOVE_FIELDS if k in value]
    if not removed:
        raise ValueError('already optimizer-free; never rewrite it')
    # All other fields, not just model, survive this operation.
    retained = copy.copy(value)
    for key in removed:
        retained.pop(key)
    return retained, removed


def fingerprint(value):
    import torch
    storage_ids, storage_rows, objects = {}, [], {}
    tensor_count = 0

    def node(item):
        nonlocal tensor_count
        if isinstance(item, torch.Tensor):
            if item.device.type != 'cpu' or item.layout != torch.strided or item.is_quantized:
                raise ValueError('dense unquantized CPU tensors required')
            tensor_count += 1
            storage = item.untyped_storage()
            sid = storage._cdata
            if sid not in storage_ids:
                number = len(storage_rows)
                storage_ids[sid] = number
                raw = torch.empty(0, dtype=torch.uint8).set_(storage, 0, (storage.nbytes(),), (1,))
                digest = hashlib.sha256()
                for start in range(0, raw.numel(), 8*1024*1024):
                    digest.update(memoryview(raw[start:start+8*1024*1024].numpy()))
                storage_rows.append(dict(bytes=storage.nbytes(), sha256=digest.hexdigest()))
            return ['tensor', type(item).__module__, type(item).__qualname__,
                storage_ids[sid], str(item.dtype), list(item.shape),
                list(item.stride()), item.storage_offset(), item.requires_grad,
                item.is_conj(), item.is_neg(), node(item.__dict__) if item.__dict__ else None]
        if item is None:
            return ['none']
        if type(item) is bool:
            return ['bool', item]
        if type(item) is int:
            return ['int', str(item)]
        if type(item) is float:
            return ['float64_bits', struct.pack('>d', item).hex()]
        if type(item) is str:
            return ['str', item]
        if type(item) is bytes:
            return ['bytes', item.hex()]
        if type(item) not in (dict, OrderedDict, tuple, list, set, frozenset):
            raise ValueError('unsupported retained object: '+str(type(item)))
        if id(item) in objects:
            return ['object_ref', objects[id(item)]]
        number = len(objects)
        objects[id(item)] = number
        if isinstance(item, dict):
            body = [[node(k), node(v)] for k, v in item.items()]
            attrs = node(item.__dict__) if hasattr(item, '__dict__') and item.__dict__ else None
        elif isinstance(item, (set, frozenset)):
            if any(type(v) not in (str, int, float, bool, bytes) for v in item):
                raise ValueError('only primitive retained set members supported')
            body, attrs = [node(v) for v in sorted(item, key=lambda v:(str(type(v)), repr(v)))], None
        else:
            body, attrs = [node(v) for v in item], None
        return [type(item).__name__, number, body, attrs]

    tree = node(value)
    encoded = json.dumps(dict(tree=tree, storages=storage_rows), ensure_ascii=True,
                         separators=(',', ':'), allow_nan=False).encode('ascii')
    return dict(sha256=hashlib.sha256(encoded).hexdigest().upper(),
        tensor_occurrences=tensor_count, storages=len(storage_rows),
        retained_storage_bytes=sum(v['bytes'] for v in storage_rows))


def load_cpu(path):
    import torch
    return torch.load(path, map_location='cpu', weights_only=True, mmap=True)
