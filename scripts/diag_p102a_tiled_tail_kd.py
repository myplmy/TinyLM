"""Measure a weighted uniform-tail KD objective on an exact tied-head fixture."""

import argparse
import gc
import json
import os
import subprocess
import sys
import time

from scripts import diag_p013_native_matched_training as io
from scripts.diag_p102a_weighted_head_vocab import cpu_compare


TAG = "p102a_tiled_topk_uniform_tail_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
VOCABS = (32768, 248320)
ROWS, RANK, WIDTH, UPDATES, TILE = 384, 256, 768, 6, 8192
CAP = 155
SOURCES = (
    "scripts/diag_p102a_tiled_tail_kd.py", "scripts/diag_p013_native_matched_training.py",
    "scripts/diag_p102a_weighted_head_vocab.py", "tinylm/train/streaming_head.py",
)


def source_pins():
    return {name: io.digest(io.ROOT / name) for name in SOURCES}


def losses(features, table, labels, anchors, masses, tile):
    import torch
    import torch.nn.functional as F
    from tinylm.train.streaming_head import vocab_nll

    remainder = (1 - masses.sum()) / (table.shape[0] - len(masses))
    entropy = -(masses * masses.log()).sum() - (1 - masses.sum()) * remainder.log()
    if tile is None:
        nll = -F.log_softmax(F.linear(features, table), dim=-1)
        teacher = torch.full_like(nll, remainder).scatter(1, anchors, masses.expand_as(anchors))
        ce = nll.gather(1, labels[:, None]).squeeze(1)
        return ce, (teacher * nll).sum(dim=-1) - entropy
    ce = vocab_nll(features, table, labels, tile=tile)
    chosen = (features * table[labels]).sum(dim=-1)
    anchor_logits = torch.einsum("nr,nkr->nk", features, table[anchors])
    mean_logit = F.linear(features, table.mean(dim=0, keepdim=True)).squeeze(-1)
    teacher_mean = (anchor_logits * (masses - remainder)).sum(dim=-1)
    teacher_mean += mean_logit * (table.shape[0] * remainder)
    return ce, ce + chosen - teacher_mean - entropy


def prepare():
    import torch

    assert os.environ["CUDA_VISIBLE_DEVICES"] == ""
    generator = torch.Generator().manual_seed(68211)
    features = torch.randn(11, 6, generator=generator, dtype=torch.float64, requires_grad=True)
    table = torch.randn(29, 6, generator=generator, dtype=torch.float64, requires_grad=True)
    labels = torch.arange(11)
    anchors = (labels[:, None] + 2 * torch.arange(1, 5)) % len(table)
    masses = table.new_tensor([.32, .2, .14, .09])
    base = losses(features, table, labels, anchors, masses, None)
    tiled = losses(features, table, labels, anchors, masses, 7)
    inputs = (features, table)
    weight = features.new_tensor([.2, .8, .6, .5, 1.2, 1.4, .9, 1.1, .3, .8, 1.3])
    gradients = [
        torch.autograd.grad(((ce + .3 * kl) * weight).sum() / weight.sum(), inputs)
        for ce, kl in (base, tiled)
    ]
    for left, right in zip((*base, *gradients[0]), (*tiled, *gradients[1]), strict=True):
        torch.testing.assert_close(left, right, atol=1e-12, rtol=1e-10)
    assert not torch.cuda.is_initialized()
    OUT.mkdir()
    io.write(PROFILE, dict(tag=TAG, sources=source_pins(), python=sys.executable,
        torch=str(torch.__version__), vocabs=VOCABS, steps=UPDATES, rows=ROWS, tile=TILE,
        teacher="top-8 normalized mass 0.75; uniform complement 0.25 over all other IDs",
        weighted_targets=ROWS-len(range(0, ROWS, 9)), same_adamw=True, cpu_fp64_oracle=True,
        gpu_calls=0, checkpoint_writes=0))
    print("P102A_TAIL_KD_READY", io.digest(PROFILE), flush=True)


def verify():
    p = json.loads(PROFILE.read_bytes())
    assert p["sources"] == source_pins() and p["python"] == sys.executable
    assert p["vocabs"] == list(VOCABS) and p["steps"] == UPDATES and p["tile"] == TILE
    return p


def arm(torch, vocab, tile):
    import torch.nn.functional as F

    rng = torch.Generator().manual_seed(68211)
    table = torch.nn.Parameter((torch.randn(vocab, RANK, generator=rng) * .025).cuda())
    projection = torch.nn.Parameter((torch.randn(WIDTH, RANK, generator=rng) * .018).cuda())
    optimizer = torch.optim.AdamW((table, projection), lr=8e-5, weight_decay=0., foreach=False)
    masses = table.new_tensor([.30, .14, .10, .07, .05, .04, .03, .02])
    keep = torch.arange(ROWS).remainder(9) != 0
    metrics = []
    snapshot = None
    for step in range(UPDATES):
        assert not (OUT / "STOP").exists()
        seq = torch.randint(vocab, (ROWS + 1,), generator=rng)
        x, labels = seq[:-1][keep].cuda(), seq[1:][keep].cuda()
        anchors = (x[:, None] + 17 * torch.arange(1, 9, device="cuda")) % vocab
        weights = torch.linspace(.2, 1.8, ROWS).roll(31 * step)[keep].cuda()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        started = time.perf_counter()
        hidden = F.layer_norm(F.linear(F.embedding(x, table), projection), (WIDTH,))
        features = F.linear(hidden, projection.T)
        ce, kl = losses(features, table, labels, anchors, masses, tile)
        loss = ((ce + .3 * kl) * weights).sum() / weights.sum()
        loss.backward()
        copy_seconds = 0.
        if step == 0:
            torch.cuda.synchronize()
            copy_started = time.perf_counter()
            snapshot = dict(ce=ce.detach().cpu(), kl=kl.detach().cpu(),
                table_grad=table.grad.cpu(), projection_grad=projection.grad.cpu())
            copy_seconds = time.perf_counter() - copy_started
        norm = torch.nn.utils.clip_grad_norm_((table, projection), 1., error_if_nonfinite=True)
        optimizer.step()
        torch.cuda.synchronize()
        metrics.append(dict(step=step+1, weighted=float(loss.detach()), grad_norm=float(norm),
            targets=len(labels), seconds=time.perf_counter()-started-copy_seconds,
            peak_allocated_bytes=torch.cuda.max_memory_allocated()))
        if step == 0:
            snapshot.update(table_after=table.detach().cpu(), projection_after=projection.detach().cpu())
    return metrics, snapshot


def worker(vocab):
    import torch

    p = verify()
    assert vocab in VOCABS and p["torch"] == str(torch.__version__)
    entry = io.reserve_device()
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    print("P102A_TAIL_KD_WORKER", vocab, "pid="+str(os.getpid()), flush=True)
    dense, base = arm(torch, vocab, None)
    gc.collect()
    torch.cuda.empty_cache()
    tiled, candidate = arm(torch, vocab, TILE)
    tolerance = {key: ((1e-5, 1e-4) if key in ("ce", "kl") else (2e-6, 1e-5))
                 for key in base}
    compare = {key: cpu_compare(torch, base[key], candidate[key], *tolerance[key]) for key in base}
    io.write(OUT / f"{vocab}.json", dict(entry=entry, vocab=vocab, dense=dense, tiled=tiled,
        first_step=compare, tolerance=tolerance, exit=0, profile_sha256=io.digest(PROFILE)))


def run():
    verify()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
    assert time.time() + len(VOCABS) * (CAP + 25) + 40 < io.CUTOFF
    rows = []
    for vocab in VOCABS:
        if (OUT / "STOP").exists():
            break
        io.reserve_device()
        command = ["timeout", "--signal=INT", "--kill-after=15s", f"{CAP}s", sys.executable,
            "-B", "-u", "-m", "scripts.diag_p102a_tiled_tail_kd", "worker", str(vocab)]
        result = subprocess.run(command, cwd=io.ROOT)
        rows.append(dict(vocab=vocab, exit=result.returncode))
        print("P102A_TAIL_KD_TERMINAL", vocab, result.returncode, flush=True)
    release = io.reserve_device()
    complete = len(rows) == len(VOCABS) and all(row["exit"] == 0 for row in rows)
    io.write(OUT / "terminal.json", dict(complete=complete, exit=0 if complete else 8,
        rows=rows, release=release, profile_sha256=io.digest(PROFILE)))
    return 0 if complete else 8


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "worker"))
    parser.add_argument("vocab", type=int, nargs="?")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "worker":
        worker(args.vocab)
    else:
        raise SystemExit(run())
