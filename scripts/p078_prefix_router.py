"""P078 learned-prefix pilot primitives; no torch/assets on module import.

The MLP learns TRAIN-only relative CE, not an oracle action at inference.
Its deliberately small embedding features are not full relational reasoning.
Atomic routes/session leases remain owned by the unchanged Stage2 helper.
"""
from __future__ import annotations
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
import ast
import hashlib
import json
import math
from pathlib import Path
import random
from types import SimpleNamespace
import unicodedata
from scripts import p078_route_training as route

SCHEMA = 'P078_PREFIX_ROUTER_V1'
FEATURE_SPEC = dict(schema=SCHEMA, pooling=['mean', 'position_weighted_mean', 'last_token'],
    scalars=['log1p_prefix_tokens', 'prefix_tokens/1024'], embedding='FROZEN_BODY_EMB_ROWS_FP32',
    boundary='x[:first_actual_supervised_target+1]; known-past correction allowed; future gold excluded',
    validation='exact standalone canonical known-past+assistant-header encode equality on every TRAIN/VAL row',
    limitation='small order-sensitive embedding statistics, NOT full reasoning')
HEAD = dict(hidden=64, outputs=3, activation='tanh', loss='relative_ce_mse', epochs=5,
    dev_epochs=[1, 3, 5], adam_lr=.001, micro_bs=8, accum=16, seed=1337, head_device='cpu', cpu_threads=1)
POLICIES = ('learned', 'random_quota', 'untrained', 'constant_train_mean')


def readonly_plan(geometry, owners, index, root=route.ROOT):
    """Reuse exact source-owned pure function bodies, without importing torch/model."""
    from collections import defaultdict
    path = Path(root) / 'scripts/p070b_cla_routes.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names = ('middle_units', 'schedule', 'repeat_draw', 'trace', 'route_sha')
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    constants = [node for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id in ('VERSION', 'MODES') for t in node.targets)]
    if len(constants) != 2: raise ValueError('pinned route schema/modes changed')
    if tuple(f.name for f in functions) != names: raise ValueError('pinned pure route functions changed')
    namespace = dict(Counter=Counter, defaultdict=defaultdict, random=random, hashlib=hashlib, json=json)
    exec(compile(ast.Module(body=[*constants, *functions], type_ignores=[]), str(path), 'exec'), namespace)
    pure = SimpleNamespace(**{name: namespace[name] for name in names})
    path = Path(root) / 'scripts/p078_route_training.py'; tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('bounded_count', 'plan')]
    if tuple(f.name for f in functions) != ('bounded_count', 'plan'): raise ValueError('pinned Stage2 pure route plan changed')
    namespace = dict(backend=lambda: pure, sha=route.sha, SCHEMA=route.SCHEMA, Policy=route.Policy)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    receipt = namespace['plan'](SimpleNamespace(**geometry), owners, route.Policy('balanced_count'), index, 4, 'probe')
    return json.loads(json.dumps(receipt))  # Match exact route_scope/raw JSON representation of KV tuple keys.


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def row_sha(row): return route.sha(row)


def text_content(content):
    """Read str or canonical text-block lists, joining exactly without separators.

    This is a read-only projection, matching serialize._blocks for text only;
    original rows/metadata and their byte identities are never rewritten.
    """
    if isinstance(content, str): return content
    if not isinstance(content, list): raise ValueError('text str or canonical text-block list required')
    if any(not isinstance(block, dict) or block.get('type') != 'text' or not isinstance(block.get('text'), str) for block in content):
        raise ValueError('text-only canonical blocks required; non-text/malformed blocks refused')
    return ''.join(block['text'] for block in content)


def case_order_sha(row, seed=1337):
    known = []
    for message in row.get('messages', []):
        if message.get('role') == 'assistant': break
        known.append(dict(message, content=text_content(message.get('content'))))
    if not known or not any(m.get('role') == 'user' for m in known): raise ValueError('question-only deterministic order required')
    return route.sha([SCHEMA, seed, 'case_order_without_answers', known])


def group_keys(row):
    """Connected components preserve article/context/root aliases across views."""
    meta = row.get('meta', {})
    if meta.get('language') not in ('ko', 'en'): raise ValueError('explicit bilingual lineage required')
    keys = set()
    for field in ('article_id', 'context_id'):
        value = meta.get(field)
        if not isinstance(value, str) or not value: raise ValueError('original article/context identity required')
        keys.add(field + ':' + value)
    roots = [meta.get(k) for k in ('parent_concept_id', 'semantic_root_id', 'root_id', 'root')]
    roots = [v for v in roots if isinstance(v, str) and v]
    if not roots: raise ValueError('original semantic root required')
    keys.update('root:' + v for v in roots)
    context = meta.get('context_original')
    if not isinstance(context, str) or not normalized(context): raise ValueError('original context required')
    # No language prefix: exact normalized cross-language duplicates stay together.
    keys.add('context_text:' + route.sha(normalized(context)))
    first = next((m.get('content') for m in row.get('messages', []) if m.get('role') == 'user'), None)
    first = text_content(first)
    keys.add('question:' + route.sha(normalized(first)))
    return sorted(keys)


def split_manifest(rows, *, seed=1337, min_rows=128, min_language=64):
    if not rows or any(type(v) is not int or v < 1 for v in (min_rows, min_language)):
        raise ValueError('positive fixed split minima required')
    parent = list(range(len(rows))); key_owner = {}; keys = []
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, row in enumerate(rows):
        keys.append(group_keys(row))
        for key in keys[-1]:
            if key in key_owner: parent[find(i)] = find(key_owner[key])
            else: key_owner[key] = i
    components = {}
    for i in range(len(rows)): components.setdefault(find(i), []).append(i)
    result = dict(schema=SCHEMA, seed=seed, min_rows=min_rows, min_language=min_language,
        rows=len(rows), groups=len(components), splits={'dev': [], 'test': []},
        body_validation_reused=True, fully_pipeline_blind=False,
        claim='TEST unused by router fitting/selection only; body already validated on original VAL',
        future_fresh_roots='NOT_IMPLEMENTED; separate fresh-source contract required')
    for members in components.values():
        group = route.sha(sorted({key for i in members for key in keys[i]}))
        split = 'dev' if int(route.sha([SCHEMA, seed, group])[:16], 16) % 2 == 0 else 'test'
        for i in members:
            result['splits'][split].append(dict(index=i, row_sha256=row_sha(rows[i]),
                language=rows[i]['meta']['language'], group_sha256=group, keys=keys[i], case_order_sha256=case_order_sha(rows[i], seed)))
    result['counts'] = {}
    for split, items in result['splits'].items():
        items.sort(key=lambda v: (v['case_order_sha256'], v['index']))
        counts = dict(Counter(v['language'] for v in items)); result['counts'][split] = dict(rows=len(items), languages=counts)
        if len(items) < min_rows or any(counts.get(language, 0) < min_language for language in ('ko', 'en')):
            raise ValueError('HOLD_SPLIT_MINIMA: no seed search, row deletion or threshold reduction')
    a, b = (set(k for v in result['splits'][s] for k in v['keys']) for s in ('dev', 'test'))
    if a & b: raise ValueError('router DEV/TEST connected group leakage')
    result['manifest_sha256'] = route.sha(result)
    return result


def prefix(record):
    """Shift-aware first kept target boundary; owner2 correction stays owner2."""
    if not len(record.x) == len(record.y) == len(record.segments): raise ValueError('aligned encoded record required')
    first = next((i for i, y in enumerate(record.y) if y != -100), None)
    if first is None or type(record.segments[first]) is not int or record.segments[first] < 1:
        raise ValueError('first actual supervised assistant target required')
    if any(record.y[i] != -100 for i in range(first)): raise ValueError('future-only boundary error')
    return route.QuestionPrefix(tuple(record.x[:first + 1]))


def validate_prefix(row, record, tokenizer, *, serializer=None):
    """Independently encode known-past text, detecting cross-boundary BPE leakage."""
    if serializer is None:
        route.import_guard()
        from tinylm.chat.serialize import serialize as serializer
    first = next((i for i, y in enumerate(record.y) if y != -100), None)
    if first is None: raise ValueError('first actual supervised boundary required')
    owner = record.segments[first]; previous = []; assistant = 0; found = False
    for message in row.get('messages', []):
        if message.get('role') == 'assistant':
            assistant += 1
            if assistant == owner: found = True; break
        previous.append(message)
    if not found: raise ValueError('actual supervised owner absent from canonical messages')
    text = serializer(dict(messages=previous), 'chatml', add_generation_prompt=True)
    result = prefix(record)
    if tuple(tokenizer.encode(text).ids) != result.token_ids:
        raise ValueError('HOLD_PREFIX_BOUNDARY: standalone known-past IDs differ; no row deletion/owner relabel/gold prefix')
    return result


@dataclass
class Quota:
    total: int
    seed: int = 1337
    index: int = 0
    remaining: list | None = None
    def __post_init__(self):
        if type(self.total) is not int or self.total < 1: raise ValueError('fixed positive case total required')
    def choose(self, scores=None, *, random_choice=False):
        if self.index >= self.total: raise ValueError('all declared cases already consumed')
        if self.index % 4 == 0:
            n = min(4, self.total - self.index)
            self.remaining = {1: [2], 2: [1, 3], 3: [1, 2, 3], 4: [1, 2, 2, 3]}[n][:]
        before = self.remaining[:]
        if random_choice:
            local = random.Random(int(route.sha([SCHEMA, self.seed, self.index, 'random_quota'])[:16], 16))
            action = local.choice(self.remaining)
        else:
            if not isinstance(scores, (list, tuple)) or len(scores) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in scores):
                raise ValueError('only three finite current-prefix predictions allowed')
            action = min(set(self.remaining), key=lambda a: (scores[a - 1], a))
        self.remaining.remove(action)
        receipt = dict(index=self.index, total=self.total, quota_before=before, action=action,
            quota_after=self.remaining[:], seed=self.seed, uses_future_prefix=False, uses_gold=False)
        self.index += 1
        return action, receipt


def action_slot(model, action):
    if action not in (1, 2, 3) or model.policy.arm != 'balanced_count': raise ValueError('balanced frozen body and action R1/R2/R3 required')
    for i in range(4):
        if route.bounded_count(model.policy, i, 4, 'probe') == action: return i
    raise ValueError('action cannot be represented by original atomic policy')


@contextmanager
def action_scope(model, action, question_prefix=None):
    """Real action dispatch, not the learning rule; owner/consumer units unchanged."""
    slot = action_slot(model, action)
    with model.route_scope(slot, 4, 'probe', question_prefix) as receipt:
        if receipt['actual_repeats'] != action: raise ValueError('selected action/actual repeat mismatch')
        yield receipt


def freeze_body(model):
    model.clear_quant(); model.eval(); model.set_anneal(1.)
    for parameter in model.parameters(): parameter.requires_grad_(False); parameter.grad = None
    model.freeze_quant()


def features(model, question_prefix, *, body_sha256, tokenizer_sha256):
    route.import_guard(); import torch
    if not isinstance(question_prefix, route.QuestionPrefix) or len(question_prefix.token_ids) > model.cfg.max_seq_len:
        raise ValueError('nonempty bounded typed prefix required')
    if model.training or any(p.requires_grad or p.grad is not None for p in model.parameters()):
        raise ValueError('frozen no-gradient body required')
    with torch.no_grad():
        ids = torch.tensor(question_prefix.token_ids, device=next(model.parameters()).device, dtype=torch.long)
        if int(ids.max()) >= model.cfg.vocab_size: raise ValueError('prefix token out of vocabulary')
        embedding = model._emb_rows() if getattr(model, '_emb_fmt', None) not in (None, 'bf16', 'fp16') else model._emb_w()
        values = torch.nn.functional.embedding(ids, embedding).float(); n = len(question_prefix.token_ids)
        weights = torch.arange(1, n + 1, device=values.device, dtype=torch.float32)
        feature = torch.cat((values.mean(0), (values * weights[:, None]).sum(0) / weights.sum(), values[-1],
            values.new_tensor([math.log1p(n), n / 1024.]))).detach()
    value = feature.cpu().tolist()
    if not all(math.isfinite(v) for v in value): raise ValueError('nonfinite frozen prefix feature')
    fingerprint = route.sha(dict(spec=FEATURE_SPEC, prefix=question_prefix.token_ids, body=body_sha256,
        tokenizer=tokenizer_sha256, feature=value))
    return feature, fingerprint


def make_head(width, seed=1337):
    route.import_guard(); import torch
    if type(width) is not int or width < 5 or (width - 2) % 3: raise ValueError('declared3E+2 feature width required')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return torch.nn.Sequential(torch.nn.Linear(width, 64), torch.nn.Tanh(), torch.nn.Linear(64, 3))


def relative_ce(losses):
    if len(losses) != 3 or any(type(x) not in (float, int) or not math.isfinite(x) or x < 0 for x in losses):
        raise ValueError('three finite nonnegative TRAIN CE labels required')
    mean = sum(losses) / 3
    return [x - mean for x in losses]


def per_row_ce(model, records, *, action, pad_id=0, width=1024, device='cuda'):
    route.import_guard(); import torch
    from tinylm.train import mtp_sft as core
    if not records or len(records) > 8 or any(r.targets <= 0 for r in records): raise ValueError('micro8 positive assistant rows required')
    if type(width) is not int or not 1 <= width <= model.cfg.max_seq_len: raise ValueError('bounded fixed execution width required')
    if model.training or any(p.requires_grad or p.grad is not None for p in model.parameters()): raise ValueError('body must remain frozen')
    x, y, owners = core.pad_records(records, pad_id, device, fixed_width=width, batch_size=len(records))
    with torch.no_grad(), action_scope(model, action) as receipt:
        model.freeze_quant(); hidden = model(x, return_hidden=True); sums = []; counts = []
        for i, record in enumerate(records):
            keep = y[i].ne(-100) & owners[i].gt(0); selected = hidden[i][keep]; labels = y[i][keep]
            if int(keep.sum()) != record.targets: raise ValueError('actual owner/CE denominator differs')
            total = 0.
            for start in range(0, len(labels), 128):
                logits = model._head_logits(selected[start:start + 128].unsqueeze(0)).squeeze(0).float()
                total += float(torch.nn.functional.cross_entropy(logits, labels[start:start + 128], reduction='sum'))
            if not math.isfinite(total): raise ValueError('nonfinite per-row CE')
            sums.append(total); counts.append(record.targets)
    return sums, counts, receipt


def trial_labels(model, records, *, split, pad_id=0, width=1024, device='cuda'):
    if split != 'train': raise ValueError('trial route labels are TRAIN-only; DEV/TEST gold cannot select actions')
    losses = []; routes = []
    for action in (1, 2, 3):
        sums, counts, receipt = per_row_ce(model, records, action=action, pad_id=pad_id, width=width, device=device)
        losses.append([v / n for v, n in zip(sums, counts)]); routes.append(receipt)
    rows = [[losses[a][i] for a in range(3)] for i in range(len(records))]
    return rows, [relative_ce(v) for v in rows], routes


def head_update(head, optimizer, x, y, mean, scale):
    """One real head optimizer step, micro8 accumulation/whole-update row denominator."""
    import torch
    if not 1 <= len(x) <= 128 or len(y) != len(x): raise ValueError('at-most128 head rows required')
    optimizer.zero_grad(set_to_none=True); total = 0.
    for start in range(0, len(x), 8):
        prediction = head((x[start:start + 8] - mean) / scale)
        loss = (prediction - y[start:start + 8]).square().sum() / (len(x) * 3)
        if not bool(torch.isfinite(loss)): raise ValueError('nonfinite router objective')
        loss.backward(); total += float(loss.detach())
    if not all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in head.parameters()): raise ValueError('missing/nonfinite learned head gradients')
    optimizer.step()
    if not all(bool(torch.isfinite(p).all()) for p in head.parameters()): raise ValueError('nonfinite learned head parameters after actual step')
    return total
