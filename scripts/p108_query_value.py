"""Private position adaptation of the sealed value optimizer, without mutation."""
from types import FunctionType


def prompt_end(item):
    ids = item.get('prompt_ids')
    if not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids):
        raise ValueError('actual nonempty prompt token IDs required')
    pos = len(ids) - 1
    if item.get('start') != pos or item['x'].ndim != 2 or item['x'].shape != (1, item['x'].shape[1]):
        raise ValueError('original one-shift batch-one contract required')
    if item['x'].shape[1] < len(ids) or item['x'][0, :len(ids)].tolist() != ids:
        raise ValueError('prompt prefix changed or truncated')
    return pos


def adapt_optimizer(original, pack, oracle):
    if original.__closure__ is not None or not callable(pack) or not callable(oracle):
        raise ValueError('explicit closure-free optimizer and adapters required')
    namespace = dict(original.__globals__, pack=pack, oracle=oracle)
    result = FunctionType(original.__code__, namespace, original.__name__, original.__defaults__)
    result.__kwdefaults__ = original.__kwdefaults__
    return result
