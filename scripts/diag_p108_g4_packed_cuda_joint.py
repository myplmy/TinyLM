"""Compare single/split fixed-scale edits and the existing CUDA table kernel."""

import argparse
from contextlib import ExitStack, nullcontext
from datetime import datetime
import gc
import json
import os
import statistics
import sys
import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts.diag_p108_g4_shared_pack import (PARENT, PARENT_SHA, ROOT, SOURCES, compare,
                                            digest, fingerprint, load_model)
from scripts.p108_shared_ternary_edit import apply_shared_down_packets, physical_down_owners
from scripts.p108_weight_space import tensor_sha
from scripts import p014e_packed_g128 as packed
from scripts import p108_native_scale as native


TAG = 'p108_g4_packed_cuda_joint_v1_20261119'
OUT = ROOT / 'test_result/evidence' / TAG
PLAN = ROOT / 'test_plan/P108_직접가중치-방향수리와-학습개입.md'
CUTOFF = datetime.fromisoformat('2026-11-19T16:55:00+09:00')
CODE = (*SOURCES, 'scripts/diag_p108_g4_packed_cuda_joint.py', 'scripts/p014e_direct_cuda.py',
        'scripts/p014e_direct_head_adapter.py', 'scripts/interactive_research_infer.py')


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), file=stream)


def inputs(model):
    owners = physical_down_owners(model)
    assert owners[2].layers == (2, 3, 4, 5) and owners[6].layers == (6, 7, 8, 9)
    group = model.cfg.micro_group
    weight_a, weight_b = (owners[i].module._wq for i in (2, 6))
    codes_a, scales_a = native.layout(weight_a, group)
    codes_b, scales_b = native.layout(weight_b, group)
    groups_a = codes_a.reshape(-1, group)
    groups_b = codes_b.reshape(-1, group)
    available_b = {}
    for i in groups_b.eq(0).any(-1).nonzero().flatten().tolist():
        scale = float(scales_b.reshape(-1)[i])
        if scale > 0:
            available_b.setdefault(scale, i)
    for i in (groups_a.eq(0).any(-1) & groups_a.ne(0).any(-1)).nonzero().flatten().tolist():
        scale = float(scales_a.reshape(-1)[i])
        if scale in available_b:
            j = available_b[scale]
            break
    else:
        raise RuntimeError('no exact scale shared by both physical owners')

    sign_a = int(groups_a[i].ne(0).nonzero()[0])
    zero_a = int(groups_a[i].eq(0).nonzero()[0])
    zero_b = int(groups_b[j].eq(0).nonzero()[0])
    split_a = codes_a.clone().reshape(-1, group)
    split_a[i, sign_a] *= -1
    single_a = split_a.clone()
    single_a[i, zero_a] = 1
    split_b = codes_b.clone().reshape(-1, group)
    split_b[j, zero_b] = 1
    targets = {
        'single': {2: native.from_codes(weight_a, single_a.reshape_as(codes_a), group)},
        'split': {2: native.from_codes(weight_a, split_a.reshape_as(codes_a), group),
                  6: native.from_codes(weight_b, split_b.reshape_as(codes_b), group)},
    }
    original = {2: weight_a, 6: weight_b}
    amounts = {key: sum(float((value.double() - original[index].double()).square().sum())
                        for index, value in change.items()) for key, change in targets.items()}
    assert amounts['single'] == amounts['split'] == 5 * scale ** 2 > 0
    packets = {key: {str(i): native.packet(original[i], value, group) for i, value in edit.items()}
               for key, edit in targets.items()}
    assert all(sum(len(p['indices']) for p in arm.values()) == 2 for arm in packets.values())
    return dict(scale=scale, l2_squared=amounts, packets=packets)


def numeric(model, sequence, after_id):
    full = model(torch.cat((sequence, after_id), dim=1), logits_last_only=True)
    first, cache = model(sequence, use_cache=True, logits_last_only=True)
    next_, after = model(after_id, past_kv=cache, use_cache=True, logits_last_only=True)
    assert len(cache) == len(after) == 14 and set(cache) == set(after)
    assert all(k.shape[2] == v.shape[2] == sequence.shape[1] + 1 for k, v in after.values())
    return [full, first, next_]


def greedy(model, tokens):
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    kv = None
    output = []
    for _ in range(8):
        logits, kv = model(tokens, past_kv=kv, logits_last_only=True, use_cache=True)
        tokens = logits[:, -1].argmax(dim=-1, keepdim=True)
        output.append(tokens)
    ids = torch.cat(output, dim=1).squeeze(0).tolist()
    torch.cuda.synchronize()
    return dict(seconds=time.perf_counter() - started, ids=ids,
                allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())


def benchmark(model, operator, width):
    from scripts.p014e_direct_head_adapter import direct_head

    tokens = ((torch.arange(width, device='cuda') * 7919 + 127) % model.cfg.vocab_size)[None]
    follow_id = torch.tensor([[233]], device='cuda')
    vectors = {}
    samples = {'reference': [], 'direct': []}
    for arm in ('reference', 'direct', 'direct', 'reference'):
        with (direct_head(model, operator) if arm == 'direct' else nullcontext()):
            if arm not in vectors:
                vectors[arm] = [value.cpu() for value in numeric(model, tokens, follow_id)]
            warmup = greedy(model, tokens)
            measured = [greedy(model, tokens) for _ in range(2)]
            assert all(row['ids'] == warmup['ids'] for row in measured)
            samples[arm].extend(measured)
    same_ids = all(r['ids'] == samples['reference'][0]['ids'] for rows in samples.values() for r in rows)
    cross = {name: compare(source, observed) for name, source, observed in
             zip(('full', 'prefill', 'cached'), vectors['reference'], vectors['direct'])}
    internal = {arm: compare(values[0], values[2]) for arm, values in vectors.items()}
    central = {arm: statistics.median(row['seconds'] for row in rows) for arm, rows in samples.items()}
    return dict(width=width, cross=cross, full_cached=internal, greedy_match=same_ids, samples=samples,
                median_seconds=central, speed_ratio=central['reference'] / central['direct'])


def transfer(model, name, spec):
    master_owners = physical_down_owners(model)
    edit = {int(key): value for key, value in spec.items()}
    with apply_shared_down_packets(model, edit, realization='codes') as receipts:
        payload = packed.export_payload(model, provenance={'source_checkpoint_sha256': PARENT_SHA, 'tag': TAG},
                                        embedding_format='ternary5_existing_twn', tile_rows=128)
        runtime = packed.load_payload(payload, device='cuda', tile_rows=4096)
        counts = dict.fromkeys(edit, 0)
        with ExitStack() as stack:
            for i in edit:
                layer = runtime.layers[i].mlp[0].down_proj
                affected = tuple(j for j, block in enumerate(runtime.layers) if block.mlp[0].down_proj is layer)
                assert affected == master_owners[i].layers and type(layer) is packed.PackedGroupLinear
                src = master_owners[i].module._wq
                assert torch.equal(layer.unpack_rows(0, layer.out_f).cpu(), src)

                def count(*_, owner=i):
                    counts[owner] += 1

                stack.callback(layer.register_forward_hook(count).remove)
            numeric(runtime, torch.tensor([[1, 127, 1097, 3111, 3]], device='cuda'),
                    torch.tensor([[233]], device='cuda'))
        assert set(counts.values()) == {24}
    matrices, rest = fingerprint(payload)
    embedding = tuple(tensor_sha(payload['embedding'][k]) for k in ('codes', 'scales'))
    metrics = dict(owner_calls_total=counts, packet_receipts=receipts, storage=packed.payload_storage(payload))
    if name == 'split':
        from scripts.p014e_direct_cuda import DirectPackedOperator

        operator = DirectPackedOperator(payload['embedding'], device='cpu')
        operator.packed_codes = runtime.packed_embedding.packed_codes
        operator.group_scales = runtime.packed_embedding.group_scales
        metrics['head_workloads'] = [benchmark(runtime, operator, width) for width in (128, 512)]
    return metrics, (matrices, rest, embedding)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('phase', choices=('prepare', 'actual'))
    args = cli.parse_args()
    assert datetime.now(CUTOFF.tzinfo) < CUTOFF and not PARENT.is_symlink() and digest(PARENT) == PARENT_SHA
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    pins = {name: digest(ROOT / name) for name in CODE}
    profile_path = OUT / 'profile.json'
    if args.phase == 'actual':
        profile = json.loads(profile_path.read_text())
        assert pins == profile['sources'] and digest(PLAN) == profile['plan_sha256']
        assert not (OUT / 'report.json').exists()
    with torch.no_grad():
        model, step = load_model()
        split = inputs(model)
    if args.phase == 'prepare':
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        write_new(profile_path, dict(tag=TAG, sources=pins, plan_sha256=digest(PLAN), geometry=split,
                                     checkpoint_sha256=PARENT_SHA, checkpoint_step=step))
        print('P108_G4_CUDA_PREPARED', json.dumps(split), flush=True)
        return 0
    assert split == profile['geometry'] and step == profile['checkpoint_step']
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 7 * (1 << 30)
    torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False
    write_new(OUT / 'active.json', dict(pid=os.getpid(), device=torch.cuda.get_device_name(), tag=TAG))
    print('P108_G4_CUDA_ACTIVE', os.getpid(), flush=True)
    observed, states = {}, {}
    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
        for name, packets in split['packets'].items():
            observed[name], states[name] = transfer(model, name, packets)
            gc.collect()
            torch.cuda.empty_cache()
            print('P108_G4_CUDA_ARM_DONE', name, flush=True)
    left, left_rest, left_embeddings = states['single']
    right, right_rest, right_embeddings = states['split']
    assert left_rest == right_rest and left_embeddings == right_embeddings and left.keys() == right.keys()
    altered = [paths for paths in left if left[paths] != right[paths]]
    assert altered == [('mid_mlps.0.down_proj',), ('mid_mlps.1.down_proj',)]
    assert all(left[paths][1] == right[paths][1] for paths in altered)
    assert digest(PARENT) == PARENT_SHA and pins == {name: digest(ROOT / name) for name in CODE}
    head_pass = all(work['greedy_match'] and
                    all(not row['outside_tolerance'] and row['reference_greedy'] == row['observed_greedy']
                        for row in work['cross'].values()) for work in observed['split']['head_workloads'])
    report = dict(tag=TAG, checkpoint_sha256=PARENT_SHA, sources=pins, geometry=split, variants=observed,
                  changed_paths=altered, exact_same_scale=True, head_pass=head_pass, training_updates=0,
                  checkpoint_writes=0, allocated_pre_exit=torch.cuda.memory_allocated(),
                  reserved_pre_exit=torch.cuda.memory_reserved())
    write_new(OUT / 'report.json', report)
    print('P108_G4_CUDA_REPORT', head_pass, report['allocated_pre_exit'], flush=True)
    return 0 if head_pass else 8


if __name__ == '__main__':
    sys.exit(main())
