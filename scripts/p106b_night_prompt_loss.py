"""Separate natural-TRAIN context/question LM targets and additive prompt CE.

No source/tokenizer/checkpoint file is opened and no model is constructed here.
The driver owns real records, the optimizer-update denominator and execution.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_qa_data as data
from tinylm.chat.serialize import SPECS, serialize

IGNORE = -100
CONTEXT = 1024
VERSION = 'P106B_NIGHT_PROMPT_BODY_LM_V1'


def _view(value):
    if type(value) is int and value in (0, 1):
        return value
    if isinstance(value, str) and value in ('0', '1'):
        return int(value)
    raise ValueError('only training wrappers0/1 may receive prompt LM targets')


def _marker(name, forbidden):
    index = 0
    while True:
        marker = '\ue000TLM_PROMPT_' + name + '_' + str(index) + '\ue001'
        if all(marker not in value for value in forbidden):
            return marker, index
        index += 1


def _body_ranges(context, question, language, view, forbidden):
    """Locate UNIQUE SENTINELS in the wrapper template, never actual text.find."""
    cm, ci = _marker('CONTEXT', forbidden)
    qm, qi = _marker('QUESTION', [*forbidden, cm])
    template = data._user(cm, qm, language, view)
    if template.count(cm) != 1 or template.count(qm) != 1:
        raise ValueError('wrapper must transport each structural sentinel exactly once')
    prefix, found, tail = template.partition(cm)
    middle, found_q, suffix = tail.partition(qm)
    if found != cm or found_q != qm or qm in prefix:
        raise ValueError('registered training wrapper context/question order changed')
    user = prefix + context + middle + question + suffix
    if user != data._user(context, question, language, view):
        raise ValueError('wrapper transformed original context/question contents')
    context_range = [len(prefix), len(prefix) + len(context)]
    start_q = context_range[1] + len(middle)
    return user, dict(context=context_range, question=[start_q, start_q + len(question)]), ci + qi


def _special_ids(tokenizer):
    spec = SPECS['chatml']
    names = [spec['start'], spec['end'], *spec['think'], *spec['call'], *spec['result'],
             '<|pad|>', '<pad>']
    ids = {value for name in names if name is not None
           for value in [tokenizer.token_to_id(name)] if value is not None}
    # Added special tokens are excluded even if their literal spelling occurs
    # inside the source body. A fixture tokenizer need not expose this method.
    decoder = getattr(tokenizer, 'get_added_tokens_decoder', None)
    if callable(decoder):
        ids.update(index for index, token in decoder().items() if getattr(token, 'special', False))
    return ids


def prompt_labels(pair, view, tok, record=None):
    """Return x/assistant_y unchanged plus disjoint shifted prompt_y and proof.

    All returned arrays have len(ids[:-1]). A prompt_y[j] target belongs to raw
    token j+1 and is predicted from hidden[j]. Only fully contained original
    context/question text is eligible; wrapper/control/assistant/PAD is excluded.
    """
    view = _view(view)
    if (not isinstance(pair, dict) or pair.get('split') != 'train'
            or pair.get('language') not in ('ko', 'en')
            or any(not isinstance(pair.get(key), str) or not pair[key]
                   for key in ('context', 'question'))):
        raise ValueError('explicit natural TRAIN pair required; replay/evaluation rows are excluded')
    row = data.render_view(pair, view)
    if (len(row['messages']) != 2 or [m['role'] for m in row['messages']] != ['user', 'assistant']
            or row['meta'].get('kind') != 'night_natural_qa'
            or row['meta'].get('supervised_assistant_turns') != [1]):
        raise ValueError('only one original natural-QA assistant may own answer supervision')
    if 'views' in pair and (not isinstance(pair['views'], dict) or pair['views'].get(str(view)) != row):
        raise ValueError('frozen pair view differs from the exact original renderer')
    ids, assistant_labels, fulltext = data.encode_view(row, tok)
    encoded = tok.encode(fulltext)
    offsets = list(encoded.offsets)
    if (list(encoded.ids) != ids or len(offsets) != len(ids)
            or len(assistant_labels) != len(ids) or not 1 < len(ids) <= CONTEXT + 1):
        raise ValueError('actual canonical IDs/offsets/assistant labels/context differ')
    user, relative, retries = _body_ranges(pair['context'], pair['question'], pair['language'], view,
        [pair['context'], pair['question'], fulltext])
    if data.text(row['messages'][0]) != user:
        raise ValueError('exact rendered user body differs')
    marker, extra_retries = _marker('WHOLE_USER', [user, fulltext])
    probe = copy.deepcopy(row)
    probe['messages'][0]['content'] = [dict(type='text', text=marker)]
    framed = serialize(probe, 'chatml')
    if framed.count(marker) != 1:
        raise ValueError('serialized user sentinel must occur once')
    head, found, tail = framed.partition(marker)
    spec = SPECS['chatml']
    expected_head = spec['start'] + spec['roles']['user'] + '\n'
    expected_tail = spec['end'] + spec['sep'] + serialize(dict(messages=row['messages'][1:]), 'chatml')
    if (found != marker or head != expected_head or tail != expected_tail
            or head + user + tail != fulltext):
        raise ValueError('exact single-turn ChatML user framing is not proven')
    origin = len(head)
    ranges = {name: [origin + a, origin + b] for name, (a, b) in relative.items()}
    if any(fulltext[a:b] != pair[name] for name, (a, b) in ranges.items()):
        raise ValueError('tracked original body ranges changed')
    special = _special_ids(tok)
    prompt_full = [IGNORE] * len(ids)
    counts = dict(context=0, question=0)
    boundary_by_field = dict(context=0, question=0)
    boundary_dropped = special_dropped = zero_offsets = first_dropped = 0
    for index, position in enumerate(offsets):
        if (len(position) != 2 or any(type(value) is not int for value in position)
                or not 0 <= position[0] <= position[1] <= len(fulltext)):
            raise ValueError('actual tokenizer offsets must be bounded Unicode character pairs')
        a, b = position
        if b == a:
            zero_offsets += 1
            continue
        inside = [name for name, (lo, hi) in ranges.items() if lo <= a < b <= hi]
        overlap = [name for name, (lo, hi) in ranges.items() if a < hi and b > lo]
        if not inside:
            if overlap:
                boundary_dropped += 1
                for name in overlap:
                    boundary_by_field[name] += 1
            continue
        if len(inside) != 1:
            raise ValueError('prompt token has ambiguous context/question ownership')
        if ids[index] in special:
            special_dropped += 1
            continue
        if index == 0:
            first_dropped += 1
            continue
        if assistant_labels[index] != IGNORE:
            raise ValueError('prompt token overlaps assistant/EOT supervision')
        prompt_full[index] = ids[index]
        counts[inside[0]] += 1
    x, assistant_y, prompt_y = ids[:-1], assistant_labels[1:], prompt_full[1:]
    if any(p != IGNORE and a != IGNORE for p, a in zip(prompt_y, assistant_y)):
        raise ValueError('shifted prompt and assistant target masks overlap')
    if record is not None:
        if (not hasattr(record, 'x') or not hasattr(record, 'y')
                or any(type(value) is not int for value in record.x)
                or any(type(value) is not int for value in record.y)
                or list(record.x) != x or list(record.y) != assistant_y):
            raise ValueError('supplied record.x/.y differs from the exact shifted original encoder')
    n = sum(value != IGNORE for value in prompt_y)
    if n != sum(counts.values()):
        raise ValueError('shifted prompt denominator lost or added a target')
    proof = dict(schema=VERSION, root=pair['root'], language=pair['language'], view=view,
        ranges=ranges, user_range=[origin, origin + len(user)], token_count=n,
        token_count_by_field=counts, boundary_dropped=boundary_dropped,
        boundary_dropped_by_field=boundary_by_field, special_dropped=special_dropped,
        zero_offset_tokens=zero_offsets, unpredictable_first_token_dropped=first_dropped,
        excluded_tokens=len(ids) - n, assistant_targets=sum(v != IGNORE for v in assistant_y),
        x_tokens=len(x), full_tokens=len(ids), assistant_disjoint=True,
        record_checked=record is not None, sentinel_collision_retries=retries + extra_retries,
        shift='prompt_y[j] predicts original ids[j+1] from hidden[j]',
        offset_unit='original Unicode character offsets; complete containment only')
    return dict(x=x, assistant_y=assistant_y, prompt_y=prompt_y, proof=proof)


def prompt_sums(model, hidden, labels, checkpoint_heads=True, chunk=128):
    """Gather real prompt predictors only; return FP32 CE SUM and true count.

    labels contains each row's actual-length shifted prompt_y, never padded
    targets. The hidden tensor retains the driver's fixed [rows,1024,H] shape.
    """
    import torch
    import torch.nn.functional as F
    if (not isinstance(hidden, torch.Tensor) or hidden.ndim != 3
            or hidden.shape[0] < 1 or hidden.shape[1] != CONTEXT or hidden.shape[2] < 1
            or not hidden.is_floating_point()):
        raise ValueError('floating hidden[rows,1024,H] required')
    if (not isinstance(labels, (list, tuple)) or len(labels) != hidden.shape[0]
            or type(checkpoint_heads) is not bool or type(chunk) is not int or chunk < 1):
        raise ValueError('one real-length prompt label list per hidden row and positive chunk required')
    positions = []
    for row, values in enumerate(labels):
        if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= CONTEXT:
            raise ValueError('nonempty actual-length label rows, without padded tail, required')
        for column, target in enumerate(values):
            if type(target) is not int or (target < 0 and target != IGNORE):
                raise ValueError('prompt target must be integer vocabulary ID or IGNORE')
            if target != IGNORE:
                positions.append((row, column, target))
    # Keep even an empty auxiliary sum FP32 without allocating a full FP32
    # copy of the fixed-width hidden tensor or giving PAD any nonzero gradient.
    total = hidden.reshape(-1)[:1].float().sum() * 0.
    for start in range(0, len(positions), chunk):
        block = positions[start:start + chunk]
        rows = torch.tensor([v[0] for v in block], dtype=torch.long, device=hidden.device)
        columns = torch.tensor([v[1] for v in block], dtype=torch.long, device=hidden.device)
        targets = torch.tensor([v[2] for v in block], dtype=torch.long, device=hidden.device)
        features = hidden[rows, columns].unsqueeze(0)
        def head_ce(features, targets):
            logits = model._head_logits(features)
            if (not isinstance(logits, torch.Tensor) or logits.ndim != 3
                    or tuple(logits.shape[:2]) != (1, targets.numel())
                    or logits.shape[2] < 1 or not logits.is_floating_point()
                    or bool((targets >= logits.shape[2]).any())):
                raise ValueError('bounded prompt-head shape/vocabulary target mismatch')
            return F.cross_entropy(logits.squeeze(0).float(), targets, reduction='sum')
        if checkpoint_heads and torch.is_grad_enabled() and features.requires_grad:
            from torch.utils.checkpoint import checkpoint
            part = checkpoint(head_ce, features, targets, use_reentrant=False, preserve_rng_state=False)
        else:
            part = head_ce(features, targets)
        total = total + part
    return total, len(positions)


def prompt_update_loss(sum, n, beta):
    """Add beta*prompt_SUM/WHOLE_UPDATE_prompt_targets to unchanged answer CE."""
    import torch
    if (not isinstance(sum, torch.Tensor) or sum.ndim != 0 or not sum.is_floating_point()
            or not bool(torch.isfinite(sum.detach())) or bool(sum.detach().lt(0))
            or type(n) is not int or n < 0 or type(beta) not in (int, float) or beta not in (0., .1)):
        raise ValueError('finite nonnegative scalar sum, whole-update count and beta0/.1 required')
    if n == 0:
        if bool(sum.detach().ne(0)):
            raise ValueError('zero prompt targets permit zero prompt sum only')
        return sum * 0.
    return beta * sum / n
