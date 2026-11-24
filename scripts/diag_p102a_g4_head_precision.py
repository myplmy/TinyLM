"""Trace one recorded synthetic G4 update across two head precisions."""

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
import sys

from scripts import diag_p102a_g4_native_vocab_tile as previous
from scripts import diag_p102a_head_muon_trace as ns


ROOT = previous.ROOT
TAG = 'p102a_g4_head_precision_v1_20261119'
OUT = previous.OUT.parent / TAG
OLD_DATA = previous.OUT / 'actual_artifacts/data_cache/synthetic_262144'
SOURCES = (*previous.SOURCES, 'scripts/diag_p102a_g4_head_precision.py',
           'scripts/diag_p102a_head_muon_trace.py', 'scripts/runlog.py')
FILES = (OLD_DATA / 'train.bin', OLD_DATA / 'meta.json', previous.OUT / 'report.json',
         previous.OUT / 'terminal_readback.json')
MIB = 1024 ** 2


def digest(path):
    return sha256(path.read_bytes()).hexdigest().upper()


def identities():
    return {str(p.relative_to(ROOT)): digest(p)
            for p in (*(ROOT / p for p in SOURCES), *FILES, previous.PLAN)}


def original_inputs(torch, original):
    from tinylm.data.loader import Loader

    loader = Loader('train', previous.MICRO, previous.WIDTH, 'cpu', OLD_DATA, seed=1234)
    assert original['train_sha256'] == digest(OLD_DATA / 'train.bin')
    assert len(loader.d) == 260834 and loader.rng.bit_generator.state == original['sampler_start']
    batches = [loader() for _ in range(previous.ACCUM)]
    assert all(x.shape == y.shape == (previous.MICRO, previous.WIDTH) and x.dtype == torch.long
               and bool(y.ge(0).all()) and bool(y.lt(32768).all()) for x, y in batches)
    hashes = [[sha256(t.contiguous().numpy().tobytes()).hexdigest().upper() for t in pair]
              for pair in batches]
    return batches, hashes


def new_model(torch, original):
    from tinylm.config import build_config
    from tinylm.model import TiedMLPTransformer
    from tinylm.train.anneal_schedule import quant_anneal_factor

    torch.manual_seed(1337)
    cfg = build_config('m100s12_g4', 'tied', previous.WIDTH, ckpt=True)
    cfg.train_repeat = 2.
    model = TiedMLPTransformer(cfg).train()
    model.set_anneal(quant_anneal_factor(0, previous.STEPS, 'wsd', 'linear', 0., .6))
    assert len(model.visit_schedule()) == 28 and cfg.mlp_group == 4 and cfg.cla_group == 2
    signature = sha256()
    for p in model.parameters():
        signature.update(p.detach().numpy().tobytes())
    assert signature.hexdigest().upper() == original['initial_model_sha256'], 'initial G4 differs'
    return model


def head_graph(torch, hidden, targets, table, weight, amp, tile):
    """Single microbatch, output-only derivatives on detached tied operands."""
    from torch.nn import functional as F
    from tinylm.train.streaming_head import vocab_nll

    valid = targets.reshape(-1).ne(-100)
    with torch.autocast(hidden.device.type, dtype=torch.bfloat16, enabled=amp):
        active = hidden.reshape(-1, hidden.shape[-1])[valid] if tile else hidden
        projected = F.linear(active if amp else active.float(), weight.t())
        labels = targets.reshape(-1)
        if tile:
            ce = vocab_nll(projected, table, labels[valid], tile=tile).mean()
        else:
            ce = F.cross_entropy(F.linear(projected, table).reshape(-1, table.shape[0]), labels)
    gradients = torch.autograd.grad(ce / previous.ACCUM, (projected, hidden, table, weight))
    p = projected.detach().reshape(-1, table.shape[1])
    d = gradients[0].detach().reshape_as(p)
    observed = dict(projected=p if tile else p[valid], projected_gradient=d if tile else d[valid],
                    hidden_gradient=gradients[1], output_table_gradient=gradients[2],
                    output_projection_gradient=gradients[3])
    return (float(ce.detach()), {k: v.detach().cpu() for k, v in observed.items()})


def logit_tiles(torch, projected, table, amp, tile):
    """Vary GEMM width with the exact same projected input and no graph."""
    from torch.nn import functional as F

    with torch.no_grad(), torch.autocast(projected.device.type, dtype=torch.bfloat16, enabled=amp):
        full = F.linear(projected, table)
        result = dict(elements=full.numel(), unequal=0, outside_tolerance=0, max_abs=0.)
        for start in range(0, table.shape[0], tile):
            stop = start + tile
            ref = full[:, start:stop].float()
            value = F.linear(projected, table[start:stop]).float()
            delta = (value - ref).abs()
            result['unequal'] += int(delta.ne(0).sum())
            result['outside_tolerance'] += int((delta > 1e-5 + 1e-4 * ref.abs()).sum())
            result['max_abs'] = max(result['max_abs'], float(delta.max()))
    return result


def names_after_route(torch, model):
    from tinylm.train.anneal_schedule import lr_factor
    from tinylm.train.muon import Muon
    from tinylm.train.optimizer_audit import matrix_decay_groups

    scale = lr_factor(0, 5, previous.STEPS, 'wsd')
    groups, matrices = matrix_decay_groups(model, 1e-3, 0.)
    matrix_ids = {id(p) for p in matrices}
    adam_groups = []
    for group in groups:
        values = [p for p in group['params'] if id(p) not in matrix_ids]
        if values:
            adam_groups.append(dict(group, params=values, lr=group['lr'] * scale))
    adam = torch.optim.AdamW(adam_groups, betas=(.9, .95), eps=1e-8)
    matrix = Muon(matrices, lr=4e-3 * scale, weight_decay=0., scale_mode='rms')
    owners = {n: 'Muon' if id(p) in matrix_ids else 'AdamW' for n, p in model.named_parameters()}
    assert owners['emb.weight'] == 'AdamW' and owners['emb_up.weight'] == 'Muon'
    assert len(owners) == len(matrices) + sum(len(g['params']) for g in adam_groups)
    return adam, matrix, owners


def run_arm(torch, original, batches, amp, tile):
    from tinylm.train import trainer
    from tinylm.train.streaming_head import target_nll

    model = new_model(torch, original).to('cuda')
    adam, matrix, owners = names_after_route(torch, model)
    params = dict(model.named_parameters())
    selected = ('emb_up.weight', 'mid_mlps.0.down_proj.weight')
    initial = {k: params[k].detach().cpu() for k in selected}
    before = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    losses, hidden_hashes = [], []
    for step, (x, y) in enumerate(batches):
        with torch.autocast('cuda', dtype=torch.bfloat16):
            hidden = model(x, return_hidden=True)
            with torch.autocast('cuda', dtype=torch.bfloat16, enabled=amp):
                head_input = hidden if amp else hidden.float()
                if tile:
                    nll, valid = target_nll(model, head_input, y, chunk=y.numel(), tile=tile)
                    ce = nll.sum() / valid.sum()
                else:
                    ce = trainer._ce_chunked(model._head_logits(head_input).reshape(-1, 32768), y.reshape(-1))
        (ce / previous.ACCUM).backward()
        losses.append(float(ce.detach()))
        snapshot = hidden.detach().cpu()
        hidden_hashes.append(sha256(snapshot.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest().upper())
        if step == 0:
            head_snapshot = (snapshot, y.cpu(), model._emb_w().detach().cpu(), model._emb_up_w().detach().cpu())
        del ce, hidden, head_input
    peak = torch.cuda.max_memory_allocated()
    raw = {k: p.grad.detach().cpu() for k, p in params.items()}
    clip = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.))
    assert torch.isfinite(torch.tensor(clip))
    clipped = {k: params[k].grad.detach().cpu() for k in selected}
    adam.step()
    matrix.step()
    final = {k: p.detach().cpu() for k, p in params.items()}
    options = {key: matrix.param_groups[0][key] for key in ns.MUON_KEYS}
    result = dict(losses=losses, clip_norm=clip, hidden_sha256=hidden_hashes,
                  start_allocated_mib=before / MIB, forward_backward_peak_mib=peak / MIB,
                  full_update_peak_mib=torch.cuda.max_memory_allocated() / MIB,
                  actual_updates=1, optimizer_options=options)
    return result, (raw, final, initial, clipped, owners, head_snapshot)


def compare_pair(torch, amp, original, batches):
    from tinylm.train import muon

    base, (raw, final, initial, clipped, owners, snapshot) = run_arm(torch, original, batches, amp, 0)
    torch.cuda.empty_cache()
    candidate, (other_raw, other_final, other_initial, other_clipped, other_owners, _) = run_arm(
        torch, original, batches, amp, previous.TILE)
    torch.cuda.empty_cache()
    assert base['hidden_sha256'] == candidate['hidden_sha256'] and owners == other_owners
    assert all(torch.equal(v, other_initial[k]) for k, v in initial.items())
    compared = {}
    for key, left, right in (('raw_gradient', raw, other_raw), ('first_weight', final, other_final)):
        compared[key] = {kind: previous.tensor_comparison(torch,
            {n: v for n, v in left.items() if owners[n] == kind},
            {n: v for n, v in right.items() if owners[n] == kind}) for kind in ('AdamW', 'Muon')}
    replay = {}
    for name, value in initial.items():
        modes = {}
        for fp32 in (False, True):
            a, b = [ns.replay_one(torch, muon, value, g, base['optimizer_options'], device='cuda', fp32=fp32)
                    for g in (clipped[name], other_clipped[name])]
            if not fp32:
                assert torch.equal(a['weight'], final[name]) and torch.equal(b['weight'], other_final[name])
            modes['fp32_ns' if fp32 else 'native_ns'] = previous.tensor_comparison(torch, a, b)
        replay[name] = modes
    return dict(reference=base, tile=candidate, compared=compared, replay=replay), snapshot


def head_pair(torch, snapshot, amp, tile, device):
    h, y, table, weight = (v.to(device) for v in snapshot)
    h.requires_grad_()
    table.requires_grad_()
    weight.requires_grad_()
    ref_ce, ref = head_graph(torch, h, y, table, weight, amp, 0)
    tile_ce, new = head_graph(torch, h, y, table, weight, amp, tile)
    numbers = previous.tensor_comparison(torch, ref, new)
    return dict(reference_ce=ref_ce, tile_ce=tile_ce, head_gradients=numbers,
                same_projection_logits=logit_tiles(torch, ref['projected'].to(device), table, amp, tile))


def prepare(torch):
    old = json.loads(FILES[2].read_text())
    terminal = json.loads(FILES[3].read_text())
    assert terminal['exit'] == 8 and terminal['report_sha256'] == digest(FILES[2])
    assert old['training_updates'] == 12 and old['tile']['train_ce'][0] != old['reference']['train_ce'][0]
    _, hashes = original_inputs(torch, old['reference'])
    new_model(torch, old['reference'])
    torch.manual_seed(7)
    fixture = (torch.randn(2, 4, 12), torch.tensor([[0, -100, 5, 8], [4, 1, -100, 20]]),
               torch.randn(35, 5), torch.randn(12, 5))
    audit = head_pair(torch, fixture, False, 7, 'cpu')
    assert not audit['head_gradients']['outside_tolerance']
    assert abs(audit['reference_ce'] - audit['tile_ce']) < 2e-6 and not torch.cuda.is_initialized()
    previous.write_new(OUT / 'profile.json', dict(tag=TAG, source_and_input=identities(),
                       batch_sha256=hashes, cpu=audit, physical_updates=4, draw_per_arm=16384))
    print('P102A_G4_HEAD_PRECISION_READY', flush=True)
    return 0


def actual(torch):
    profile = json.loads((OUT / 'profile.json').read_text())
    assert profile['source_and_input'] == identities()
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12 * 1024 * MIB
    from tinylm.train import muon

    ns.validate_ns_interface(muon._newton_schulz)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision('high')
    old = json.loads(FILES[2].read_text())
    batches, hashes = original_inputs(torch, old['reference'])
    assert hashes == profile['batch_sha256']
    batches = [(x.to('cuda'), y.to('cuda')) for x, y in batches]
    previous.write_new(OUT / 'active.json', dict(pid=os.getpid(), tag=TAG, device=torch.cuda.get_device_name()))
    print('P102A_G4_HEAD_PRECISION_ACTIVE', os.getpid(), flush=True)
    result = {}
    snapshots = []
    for label, amp in (('bf16_amp', True), ('fp32_head_high', False)):
        result[label], snapshot = compare_pair(torch, amp, old['reference'], batches)
        snapshots.append(snapshot[0])
        result[label]['head_only'] = head_pair(torch, snapshot, amp, previous.TILE, 'cuda')
        torch.cuda.empty_cache()
        print('P102A_G4_HEAD_PRECISION_PAIR', label, flush=True)
    assert torch.equal(*snapshots), 'body hidden changed with head precision'
    trace = result['bf16_amp']
    old_difference = {name: sum(trace[name]['losses']) / previous.ACCUM - old[name]['train_ce'][0]
                      for name in ('reference', 'tile')}
    assert all(abs(diff) <= 2e-6 for diff in old_difference.values()), old_difference
    assert profile['source_and_input'] == identities()
    previous.write_new(OUT / 'report.json', dict(tag=TAG, comparisons=result, source_and_input=identities(),
                       batch_sha256=hashes, old_bf16_first_ce_difference=old_difference,
                       fp32_matmul_precision=torch.get_float32_matmul_precision(), actual_updates=4,
                       checkpoint_writes=0, final_quality='NOT_RUN'))
    print('P102A_G4_HEAD_PRECISION_RESULT', old_difference, flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'actual'))
    args = parser.parse_args()
    assert datetime.now(previous.CUTOFF.tzinfo) + timedelta(minutes=5) < previous.CUTOFF
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ('' if args.phase == 'prepare' else '0')
    if args.phase == 'prepare':
        OUT.mkdir(exist_ok=False)
    else:
        assert not (OUT / 'active.json').exists() and not (OUT / 'report.json').exists()
    os.environ['TINYLM_DIR'] = str(OUT / 'unused_root')
    os.environ['TINYLM_HF'] = str(OUT / 'unused_root/HF')
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return (prepare if args.phase == 'prepare' else actual)(torch)


if __name__ == '__main__':
    sys.exit(main())
