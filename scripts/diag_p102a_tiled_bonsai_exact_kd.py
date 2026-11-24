"""Compare exact full-distribution KD and tiled NLL on a tied-head fixture."""

import argparse
from datetime import datetime
import gc
import json
import os
from pathlib import Path
import sys
import time

from scripts import diag_p013_native_matched_training as io
from scripts.diag_p102a_weighted_head_vocab import cpu_compare


TAG = "p102a_tiled_bonsai_exact_kd_v3_20261119"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
WITNESS = io.ROOT / "handoff/audit/research_20261118_01a1e647/PRISM_NATIVE_RAW_CLOSED_READBACK_v1.json"
VOCAB, ROWS, RANK, WIDTH, UPDATES, TILE = 248320, 384, 256, 768, 6, 8192
CUTOFF = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
SOURCES = (
    "scripts/diag_p102a_tiled_bonsai_exact_kd.py",
    "scripts/diag_p013_native_matched_training.py",
    "scripts/diag_p102a_weighted_head_vocab.py",
    "tinylm/train/streaming_head.py",
)


def frozen_logits(torch):
    import numpy as np

    evidence = json.loads(WITNESS.read_bytes())
    assert evidence["process_exit"] == 0 and evidence["actual_gpu_loaded"] and evidence["native_handles_closed"]
    assert evidence["same_A_bits_exact"] and evidence["B_differs_from_A"] and evidence["formal_benchmark"] == "NOT_RUN"
    files, values = {}, []
    for key in ("A0", "B"):
        pin = evidence["native_vectors"][key]
        path = io.ROOT / pin["path"]
        assert path.stat().st_size == pin["bytes"] and io.digest(path) == pin["sha256"]
        array = np.load(path, allow_pickle=False)
        assert array.dtype == np.float32 and array.shape == (VOCAB,) and np.isfinite(array).all()
        files[key] = pin
        values.append(torch.from_numpy(array.copy()))
    return torch.stack(values).double(), files


def losses(features, table, labels, teachers, probs, tile):
    import torch
    import torch.nn.functional as F
    from tinylm.train.streaming_head import vocab_nll

    entropy = -torch.xlogy(probs, probs).sum(dim=1)[teachers]
    if tile is None:
        ce = F.cross_entropy(F.linear(features, table), labels, reduction="none")
    else:
        ce = vocab_nll(features, table, labels, tile=tile)
    selected = (features * table[labels]).sum(dim=1)
    expected_logits = (features * (probs @ table)[teachers]).sum(dim=1)
    expected_nll = (ce + selected) * probs.sum(dim=1)[teachers] - expected_logits
    return ce, expected_nll - entropy


def fingerprint(torch):
    logits, files = frozen_logits(torch)
    probs = logits.softmax(dim=1)
    top, indices = probs.topk(8, dim=1)
    complement = probs.scatter(1, indices, 0.)
    data = dict(tag=TAG, source_pins={name: io.digest(io.ROOT / name) for name in SOURCES},
        teacher_readback_sha256=io.digest(WITNESS), teacher_vectors=files, vocab=VOCAB, rows=ROWS,
        seed=68211, steps=UPDATES, tile=TILE, torch=str(torch.__version__), python=sys.executable,
        cutoff_KST=CUTOFF.isoformat(), approval_ref="WIP-176", teacher_top8_mass=top.sum(dim=1).tolist(),
        teacher_tail_mass=complement.sum(dim=1).tolist(), teacher_tail_max=complement.max(dim=1).values.tolist(),
        prefixes_for_numerical_fixture_only=True, gpu_calls_at_prepare=0, checkpoint_writes=0)
    return data, logits


def prepare(torch):
    import torch.nn.functional as F

    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    profile, logits = fingerprint(torch)
    probabilities = logits.softmax(dim=1).float()
    generator = torch.Generator().manual_seed(profile["seed"])
    labels = torch.tensor([1, TILE - 1, TILE, 2 * TILE - 1, 2 * TILE, VOCAB - 2, VOCAB - 1])
    features = torch.randn(len(labels), 6, generator=generator, requires_grad=True)
    table = (torch.randn(VOCAB, 6, generator=generator) * .025).requires_grad_()
    teachers = torch.arange(len(labels)) % len(probabilities)
    weights = torch.linspace(.2, 1.8, len(labels))
    x64, w64, p64 = features.double(), table.double(), probabilities.double()
    nll = -F.log_softmax(F.linear(x64, w64), dim=1)
    oracle_ce = nll.gather(1, labels[:, None]).squeeze(1)
    oracle_kl = (nll * p64[teachers]).sum(dim=1) + torch.xlogy(p64, p64).sum(dim=1)[teachers]
    objective64 = ((oracle_ce + .3 * oracle_kl) * weights.double()).sum() / weights.double().sum()
    reference = (oracle_ce, oracle_kl, *torch.autograd.grad(objective64, (x64, w64)))
    for tile in (None, TILE):
        ce, kl = losses(features, table, labels, teachers, probabilities, tile)
        objective = ((ce + .3 * kl) * weights).sum() / weights.sum()
        candidate = (ce, kl, *torch.autograd.grad(objective, (features, table)))
        for index, (left, right) in enumerate(zip(reference, candidate, strict=True)):
            atol, rtol = (1e-5, 1e-4) if index < 2 else (2e-6, 1e-5)
            torch.testing.assert_close(left, right.double(), atol=atol, rtol=rtol)
    assert not torch.cuda.is_initialized()
    OUT.mkdir()
    io.write(PROFILE, profile)
    print("P102A_BONSAI_EXACT_KD_READY", io.digest(PROFILE), flush=True)


def arm(torch, probs, seed, tile):
    import torch.nn.functional as F

    generator = torch.Generator().manual_seed(seed)
    table = torch.nn.Parameter((torch.randn(VOCAB, RANK, generator=generator) * .025).cuda())
    projection = torch.nn.Parameter((torch.randn(WIDTH, RANK, generator=generator) * .018).cuda())
    optimizer = torch.optim.AdamW((table, projection), lr=8e-5, weight_decay=0., foreach=False)
    keep = torch.arange(ROWS).remainder(9) != 0
    records, first = [], None
    for step in range(UPDATES):
        assert time.time() + 20 < CUTOFF.timestamp() and not (OUT / "STOP").exists()
        seq = torch.randint(VOCAB, (ROWS + 1,), generator=generator)
        ids, labels = seq[:-1][keep].cuda(), seq[1:][keep].cuda()
        teachers = (torch.arange(ROWS)[keep] % len(probs)).cuda()
        weights = torch.linspace(.2, 1.8, ROWS).roll(31 * step)[keep].cuda()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        started = time.perf_counter()
        hidden = F.layer_norm(F.linear(F.embedding(ids, table), projection), (WIDTH,))
        features = F.linear(hidden, projection.T)
        ce, kl = losses(features, table, labels, teachers, probs, tile)
        objective = ((ce + .3 * kl) * weights).sum() / weights.sum()
        objective.backward()
        copy_seconds = 0.
        if step == 0:
            torch.cuda.synchronize()
            copy_started = time.perf_counter()
            first = dict(ce=ce.detach().cpu(), kl=kl.detach().cpu(),
                         table_grad=table.grad.cpu(), projection_grad=projection.grad.cpu())
            copy_seconds = time.perf_counter() - copy_started
        norm = torch.nn.utils.clip_grad_norm_((table, projection), 1., error_if_nonfinite=True)
        optimizer.step()
        torch.cuda.synchronize()
        records.append(dict(step=step + 1, targets=len(labels), objective=float(objective.detach()),
            gradient_norm=float(norm), seconds=time.perf_counter() - started - copy_seconds,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved()))
        if step == 0:
            first.update(table_after=table.detach().cpu(), projection_after=projection.detach().cpu())
    return records, first


def actual(torch):
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0" and time.time() + 190 < CUTOFF.timestamp()
    assert not (OUT / "terminal.json").exists()
    profile, logits = fingerprint(torch)
    assert profile == json.loads(PROFILE.read_bytes())
    entry = io.reserve_device()
    torch.backends.cuda.matmul.allow_tf32 = False
    probs = logits.softmax(dim=1).float().cuda()
    print("P102A_BONSAI_EXACT_KD_START", os.getpid(), flush=True)
    dense, base = arm(torch, probs, profile["seed"], None)
    gc.collect()
    torch.cuda.empty_cache()
    tiled, candidate = arm(torch, probs, profile["seed"], TILE)
    tolerance = {name: ((1e-5, 1e-4) if name in ("ce", "kl") else (2e-6, 1e-5)) for name in base}
    compare = {name: cpu_compare(torch, base[name], candidate[name], *tolerance[name]) for name in base}
    del probs
    gc.collect()
    torch.cuda.empty_cache()
    owned_allocated = torch.cuda.memory_allocated()
    sources_unchanged = fingerprint(torch)[0] == profile
    status = 0 if sources_unchanged else 8
    print("P102A_BONSAI_EXACT_KD_PRE_EXIT", owned_allocated, torch.cuda.memory_reserved(), sources_unchanged, flush=True)
    io.write(OUT / "terminal.json", dict(exit=status, entry=entry, dense=dense, tiled=tiled,
        comparison=compare, tolerance=tolerance, allocator_pre_exit_bytes=owned_allocated,
        reserved_pre_exit_bytes=torch.cuda.memory_reserved(), sources_unchanged=sources_unchanged,
        profile_sha256=io.digest(PROFILE), model_loads=0, checkpoint_writes=0))
    print("P102A_BONSAI_EXACT_KD_DONE", UPDATES * 2, {key: row["mismatch"] for key, row in compare.items()}, flush=True)
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "actual"))
    args = parser.parse_args()
    import torch

    torch.set_num_threads(1)
    raise SystemExit((prepare if args.mode == "prepare" else actual)(torch))
