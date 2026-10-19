"""Gold-free extractive readout for an already trained P106B span head.

This module opens no assets, tokenizer files, models, checkpoints or devices.
The caller supplies a tokenizer object, an answer-free serialized prefix, its
declared reference character range, an existing head and prefix-only hidden.
No answer, answer location, conversation metadata or vocabulary decoder is an
inference argument. This is a source extraction diagnostic, not a generative
decoder, a semantic judge or evidence that the source is true.

Token IDs and Unicode character offsets remain unchanged. Zero-width offsets
and tokens crossing the declared reference boundary are not source-bank keys.
ByteLevel duplicate/overlapping offsets are allowed in tokenizer order. Output
is the original prefix substring spanning the selected token offsets; only
outer Python ``str.strip`` whitespace removal is applied to the returned text.
In particular, Korean particles, punctuation and BPE boundary spill remain.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POLICIES = ('independent', 'valid_joint')
NORMALIZATION = 'OUTER_WHITESPACE_STRIP_ONLY'


def _integer(value):
    return type(value) is int


def _range(value, size):
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(not _integer(v) for v in value)
            or not 0 <= value[0] < value[1] <= size):
        raise ValueError('nonempty in-prefix Unicode reference range required')
    return tuple(value)


@dataclass(frozen=True)
class SpanBank:
    """Exact prefix encoding and a source-only, strictly past token bank."""

    prefix: str
    reference_range: tuple[int, int]
    ids: tuple[int, ...]
    offsets: tuple[tuple[int, int], ...]
    positions: tuple[int, ...]
    query: int
    max_tokens: int = 1024

    def __post_init__(self):
        if not isinstance(self.prefix, str) or not self.prefix:
            raise ValueError('nonempty serialized answer-free prefix required')
        lo, hi = _range(self.reference_range, len(self.prefix))
        if type(self.reference_range) is not tuple:
            raise ValueError('immutable reference range required')
        reference = self.prefix[lo:hi]
        first = self.prefix.find(reference)
        # find again from first+1 also detects overlapping duplicate passages.
        if first != lo or self.prefix.find(reference, first + 1) != -1:
            raise ValueError('the entire declared reference must occur once in prefix')
        if (not _integer(self.max_tokens) or self.max_tokens < 1
                or type(self.ids) is not tuple or not self.ids
                or len(self.ids) > self.max_tokens
                or any(not _integer(v) or v < 0 for v in self.ids)):
            raise ValueError('nonempty bounded prefix of nonnegative real token IDs required')
        if (type(self.offsets) is not tuple or len(self.offsets) != len(self.ids)
                or any(type(pair) is not tuple or len(pair) != 2
                       or any(not _integer(v) for v in pair)
                       or not 0 <= pair[0] <= pair[1] <= len(self.prefix)
                       for pair in self.offsets)):
            raise ValueError('one valid immutable Unicode offset pair per token required')
        previous = None
        for a, b in self.offsets:
            if a == b:
                continue
            if previous is not None and (a < previous[0] or b < previous[1]):
                raise ValueError('nonzero token offsets must preserve tokenizer text order')
            previous = (a, b)
        if not _integer(self.query) or self.query != len(self.ids) - 1:
            raise ValueError('query must be the last actual prefix token')
        expected = tuple(i for i, (a, b) in enumerate(self.offsets)
                         if lo <= a < b <= hi)
        if (type(self.positions) is not tuple or any(not _integer(v) for v in self.positions)
                or self.positions != expected or not expected):
            raise ValueError('complete nonempty reference-contained token bank required')
        if any(i >= self.query for i in expected):
            raise ValueError('reference token bank must strictly precede prefix query')


def build_bank(tokenizer, prefix, reference_range, *, max_tokens=1024):
    """Encode only ``prefix``; no gold or answer-location metadata is consumed.

    ``reference_range`` is absolute in the full serialized prefix, not relative
    to a user message. It must be declared independently of the answer. A token
    straddling its boundaries is excluded rather than split or retokenized.
    The caller remains responsible for supplying an answer-free prefix and a
    range belonging to the intended reference, rather than a question/history.
    """
    if not isinstance(prefix, str) or not prefix:
        raise ValueError('nonempty serialized answer-free prefix required')
    lo, hi = _range(reference_range, len(prefix))
    if not _integer(max_tokens) or max_tokens < 1:
        raise ValueError('positive integer prefix token bound required')
    if not callable(getattr(tokenizer, 'encode', None)):
        raise ValueError('caller-supplied tokenizer encode method required')
    encoded = tokenizer.encode(prefix)
    try:
        ids = tuple(encoded.ids)
        offsets = tuple(tuple(pair) for pair in encoded.offsets)
    except (AttributeError, TypeError) as exc:
        raise ValueError('encoding must expose token IDs and Unicode offset pairs') from exc
    # SpanBank validates every offset before any source slicing or tensor work.
    positions = tuple(i for i, pair in enumerate(offsets)
                      if len(pair) == 2 and all(_integer(v) for v in pair)
                      and lo <= pair[0] < pair[1] <= hi)
    return SpanBank(prefix, (lo, hi), ids, offsets, positions, len(ids) - 1, max_tokens)


def boundary_scores(head, hidden, bank):
    """Score the existing qs/ks/qe/ke head on exact prefix-only hidden.

    Accept [T,D] or [1,T,D], with T exactly the prefix encoding length. Projection
    uses each Linear's stored dtype with ambient autocast disabled; projected
    q/k dot products are FP32 and use the original ``1/sqrt(rank)`` scale. This
    inference helper does not update
    weights, mutate modes, create parameters or retain an autograd graph.
    """
    import torch
    if not isinstance(bank, SpanBank):
        raise ValueError('validated SpanBank required')
    if (not isinstance(hidden, torch.Tensor) or not hidden.is_floating_point()
            or hidden.ndim not in (2, 3)):
        raise ValueError('floating prefix hidden [T,D] or [1,T,D] required')
    if hidden.ndim == 3:
        if hidden.shape[0] != 1:
            raise ValueError('one exact prefix per span readout required')
        hidden = hidden[0]
    if (hidden.shape[0] != len(bank.ids) or hidden.shape[1] < 1
            or not bool(torch.isfinite(hidden).all())):
        raise ValueError('finite hidden must contain exactly all prefix positions')
    try:
        keys = set(head.keys())
    except (AttributeError, TypeError) as exc:
        raise ValueError('existing qs/ks/qe/ke Linear head required') from exc
    if keys != {'qs', 'ks', 'qe', 'ke'}:
        raise ValueError('exactly qs/ks/qe/ke head projections required')
    modules = [head[name] for name in ('qs', 'ks', 'qe', 'ke')]
    if any(not isinstance(layer, torch.nn.Linear) or layer.bias is not None
           or layer.in_features != hidden.shape[1] or layer.out_features < 1
           for layer in modules):
        raise ValueError('bias-free Linear projections matching hidden dimension required')
    rank, dtype, device = modules[0].out_features, modules[0].weight.dtype, modules[0].weight.device
    if any(layer.out_features != rank or layer.weight.dtype != dtype
           or layer.weight.device != device or not layer.weight.is_floating_point()
           or not bool(torch.isfinite(layer.weight).all()) for layer in modules):
        raise ValueError('finite head projections need matching rank, dtype and device')
    if device != hidden.device:
        raise ValueError('head and prefix hidden must be on the same device')
    with torch.no_grad(), torch.autocast(device_type=hidden.device.type, enabled=False):
        source = hidden[list(bank.positions)].to(dtype=dtype)
        query = hidden[bank.query].to(dtype=dtype)
        result = []
        for suffix in ('s', 'e'):
            values = (head['k' + suffix](source).float()
                      @ head['q' + suffix](query).float()) / math.sqrt(rank)
            if values.shape != (len(bank.positions),) or not bool(torch.isfinite(values).all()):
                raise ValueError('finite one-dimensional boundary scores required')
            result.append(values)
    return tuple(result)


def _scores(values, size):
    import torch
    if isinstance(values, torch.Tensor):
        if values.ndim != 1 or not values.is_floating_point():
            raise ValueError('one-dimensional floating boundary scores required')
        values = values.detach().cpu().tolist()
    if (not isinstance(values, (tuple, list)) or len(values) != size
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
        raise ValueError('one finite boundary score per source-bank token required')
    return tuple(float(v) for v in values)


@dataclass(frozen=True)
class SpanReadout:
    policy: str
    status: str
    start_index: int
    end_index: int
    start_token: int
    end_token: int
    start_score: float
    end_score: float
    joint_score: float
    char_range: tuple[int, int] | None
    raw_text: str | None
    text: str | None
    normalization: str = NORMALIZATION


def select_span(bank, start_scores, end_scores, policy='independent'):
    """Select one span without a gold answer, length hint or repair heuristic.

    Independent argmax ties choose the first source token. A reversed result is
    returned as INVALID_REVERSED, with no text. valid_joint maximizes start[i]+
    end[j] over every i<=j, with no length cap, in linear time. Ties use the
    lexicographically earliest (i,j). Sums use Python float on the supplied score
    values, so both policies share the exact same projected scores.
    """
    if not isinstance(bank, SpanBank):
        raise ValueError('validated SpanBank required')
    if type(policy) is not str or policy not in POLICIES:
        raise ValueError('explicit independent or valid_joint policy required')
    start = _scores(start_scores, len(bank.positions))
    end = _scores(end_scores, len(bank.positions))
    if policy == 'independent':
        left = max(range(len(start)), key=start.__getitem__)
        right = max(range(len(end)), key=end.__getitem__)
    else:
        best_start = 0
        left, right, best_sum = 0, 0, start[0] + end[0]
        for j in range(len(start)):
            if start[j] > start[best_start]:
                best_start = j
            value, pair = start[best_start] + end[j], (best_start, j)
            if value > best_sum or (value == best_sum and pair < (left, right)):
                left, right, best_sum = best_start, j, value
    total = start[left] + end[right]
    if not math.isfinite(total):
        raise ValueError('finite combined boundary score required')
    first, last = bank.positions[left], bank.positions[right]
    valid = right >= left
    chars = (bank.offsets[first][0], bank.offsets[last][1]) if valid else None
    raw = bank.prefix[slice(*chars)] if valid else None
    return SpanReadout(policy, 'OK' if valid else 'INVALID_REVERSED', left, right,
                       first, last, start[left], end[right], total, chars, raw,
                       raw.strip() if valid else None)


def readout(head, hidden, bank, policy='independent'):
    """Existing head scores followed by one explicit extraction policy."""
    start, end = boundary_scores(head, hidden, bank)
    return select_span(bank, start, end, policy)
