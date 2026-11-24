"""Probe document isolation on approved P109 routes with native CPU autograd."""

import os
from unittest.mock import patch

import torch

from scripts import diag_p107_g4_r2_visibility as fixed
from scripts import p109_train_visit_policy as policy
from tinylm.model import transformer, visibility


TAG = 'p107_g4_policy_visibility_cpu_v1_20261119'
OUT = fixed.OUT.with_name(TAG)
SEED, HORIZON = 1337, 16
SOURCES = (*policy.SOURCES, 'scripts/diag_p107_g4_policy_visibility_cpu.py',
           'scripts/diag_p107_g4_r2_visibility.py', 'tinylm/model/visibility.py',
           'tinylm/train/hybrid_mntp.py')


def route_cases(model):
    cfg, owners = model.cfg, model.owner
    first = {}
    for index in range(HORIZON):
        route = policy.route_for(cfg, owners, 'balanced_count', SEED, index, HORIZON)
        if len(route) in (16, 40):
            first.setdefault(len(route), (index, route))
    assert set(first) == {16, 40}
    yield from (('balanced_count', *first[count]) for count in sorted(first))
    route = policy.route_for(cfg, owners, 'second_shuffle_r2', SEED, 0, HORIZON)
    original = policy.route_for(cfg, owners, 'uniform_r2', SEED, 0, HORIZON)
    assert len(route) == 28 and route[:14] == original[:14] and route[14:26] != original[14:26]
    yield 'second_shuffle_r2', 0, route


def probe_route(model, route):
    model.training_route = route
    topology = policy.cla.trace(model.cfg, model.owner, list(route))

    def prepare(mask, tokens, cfg, schedule, **kwargs):
        if tuple(schedule) != route:
            raise ValueError('document visibility probe requires its pinned P109 update route')
        return visibility.prepare_visibility(mask, tokens, cfg, range(cfg.n_layers), **kwargs)

    docs = torch.tensor([[0] * 7 + [1] * 8 + [-1] * 2])
    tokens = torch.arange(35, 52)[None, :].masked_fill(docs.lt(0), 0)
    selected = torch.zeros_like(tokens, dtype=torch.bool)
    selected[:, [2, 5, 9, 12]] = True

    def batch(raw, kind):
        if kind == 'CAUSAL':
            return fixed.causal_batch(raw, docs, vocab_size=model.cfg.vocab_size)
        return fixed.mntp_batch(raw, docs, selected, vocab_size=model.cfg.vocab_size)

    outputs = []
    with patch.object(transformer, 'prepare_visibility', prepare):
        for kind in ('CAUSAL', 'MNTP'):
            original = batch(tokens, kind)
            for target in (0, 1):
                edit = tokens.clone()
                edit[docs.eq(1 - target)] += 17
                own = docs[0, :-1].eq(target)
                base, grad, count = fixed.observe(model, original, docs[0, :-1], target)
                other, changed, _ = fixed.observe(model, batch(edit, kind), docs[0, :-1], target)
                _, snapshot, _ = fixed.observe(model, original, docs[0, :-1], target, mutate_after=True)
                assert torch.equal(base, other) and torch.equal(grad, changed) and torch.equal(grad, snapshot)
                assert bool(grad[:, ~own].eq(0).all()) and bool(grad[:, own].ne(0).any())
                case = dict(kind=kind, document=target, targets=count, isolated=True, snapshot_exact=True)
                if target == 1 or kind == 'MNTP':
                    a, leak, _ = fixed.observe(model, original, docs[0, :-1], target, open_boundary=True)
                    b, _, _ = fixed.observe(model, batch(edit, kind), docs[0, :-1], target, open_boundary=True)
                    case['open_logit_delta'] = float((a-b).abs().max())
                    case['open_forbidden_gradient'] = float(leak[:, docs[0, :-1].eq(1-target)].abs().max())
                    assert case['open_logit_delta'] > 0. and case['open_forbidden_gradient'] > 0.
                outputs.append(case)
    return dict(visits=topology['visits'], kv=topology['kv_entries'], route=route, cases=outputs)


def main():
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    torch.set_num_threads(1)
    original = fixed.make_model('cpu')
    model = policy.RoutedG4(original.cfg).train()
    model.load_state_dict(original.state_dict(), strict=True)
    model.set_anneal(1.)
    out = []
    for name, index, route in route_cases(model):
        report = dict(policy=name, update=index, **probe_route(model, route))
        out.append(report)
        print('P107_G4_POLICY_VISIBILITY', name, index, len(route), len(report['cases']), flush=True)
    assert not torch.cuda.is_initialized()
    pins = {path: fixed.head.SHA(fixed.ROOT / path) for path in SOURCES}
    OUT.mkdir(exist_ok=False)
    fixed.head.WRITE(OUT / 'report.json', dict(tag=TAG, seed=SEED, horizon=HORIZON, sources=pins, routes=out,
                    isolated_cases=sum(len(row['cases']) for row in out), gpu_calls=0, checkpoint_loads=0))


if __name__ == '__main__':
    main()
