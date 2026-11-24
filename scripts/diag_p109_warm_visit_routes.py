"""Profile the P109 visit policies on an existing 16-layer G4 checkpoint."""

import argparse
from contextlib import contextmanager
from datetime import datetime
import gc
import json
import os
import sys
import time

from scripts import diag_p013_native_matched_training as io
from scripts import p078_route_training as p078


TAG = "p109_warm_visit_routes_v2_20261119"
SHUFFLE_IDENTITY = "p109_warm_visit_routes_v1_20261118"
OUT = io.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
PARENT = io.ROOT / "runs/ckpt/m100s12_ko-en_300M_d16_g4_r20.pt"
CUTOFF = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
POLICIES = ("uniform_r2", "balanced_count", "second_shuffle_r2")
UPDATES, WIDTH, SEED = 16, 64, 1337
SOURCES = (
    "scripts/diag_p109_warm_visit_routes.py", "scripts/p078_route_training.py",
    "scripts/p070b_cla_routes.py", "scripts/diag_p013_native_matched_training.py",
    "tinylm/model/transformer.py", "tinylm/model/ternary.py", "tinylm/model/modules.py",
    "tinylm/config.py", "tinylm/infer/generate.py",
)


def load_parent(torch):
    from tinylm.config import TMTConfig
    from tinylm.infer.generate import _strip

    assert PARENT.is_file() and not PARENT.is_symlink()
    state = torch.load(PARENT, map_location="cpu", weights_only=True)
    cfg = TMTConfig(**state["cfg"])
    assert (cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.cla_group) == (2, 12, 2, 4, 2)
    assert cfg.tie_mlp and cfg.dim == 768 and cfg.vocab_size == 32768 and cfg.train_repeat == 2.0
    assert cfg.repeat_mode == "uniform" and cfg.infer_repeat == 1.0 and not cfg.mtp_aux
    cfg.grad_checkpoint = True
    cfg.train_repeat = 3.0  # Cap; the checked schedule below owns actual visits.
    return cfg, _strip(state["model"]), state["step"]


def build_model(cfg):
    routes = p078.backend()

    class VisitTransformer(routes.FixedRouteTransformer):
        def set_route(self, route):
            if getattr(self, "_visit_locked", False):
                raise RuntimeError("route must remain fixed through backward and cached decoding")
            receipt = routes.trace(self.cfg, self.owner, route)
            if receipt["middle_repeats"] > int(self.cfg.train_repeat):
                raise ValueError("route exceeds the approved repeat cap")
            self._fixed_route = tuple(route)
            self.route_sha256 = routes.route_sha(self.cfg, self.owner, route)
            self.route_trace = receipt

        @contextmanager
        def visit(self, schedule):
            self.set_route(schedule)
            self._visit_locked = True
            try:
                yield self.route_trace
            finally:
                self.clear_quant()
                self._visit_locked = False

    return VisitTransformer(cfg, mode="uniform", repeats=3)


def policy_schedules(cfg, owners):
    routes = p078.backend()
    fixed = routes.schedule(cfg, owners, "uniform", 2)
    middle = cfg.n_prelude
    second = middle + cfg.n_middle
    coda = second + cfg.n_middle
    result = {"uniform_r2": [fixed] * UPDATES, "balanced_count": [], "second_shuffle_r2": []}
    policy = p078.Policy("balanced_count", SEED)
    for index in range(UPDATES):
        count = p078.bounded_count(policy, index, UPDATES, "train")
        result["balanced_count"].append(routes.schedule(cfg, owners, "uniform", count))
        shuffle_seed = int(p078.sha([SHUFFLE_IDENTITY, SEED, index])[:16], 16)
        shuffled = routes.schedule(cfg, owners, "shuffle", 1, shuffle_seed)
        second_only = fixed[:second] + shuffled[middle:second] + fixed[coda:]
        routes.trace(cfg, owners, second_only)
        assert second_only[:second] == fixed[:second] and second_only[coda:] == fixed[coda:]
        result["second_shuffle_r2"].append(second_only)
    assert any(row != fixed for row in result["second_shuffle_r2"])
    assert all(sum(map(len, visits)) == len(fixed) * UPDATES for visits in result.values())
    return result


def fingerprint(torch, schedules, parent_step):
    return dict(tag=TAG, checkpoint=str(PARENT.relative_to(io.ROOT)), checkpoint_sha256=io.digest(PARENT),
        parent_step=parent_step, source_pins={name: io.digest(io.ROOT / name) for name in SOURCES},
        routes=schedules, targets_per_arm=UPDATES * WIDTH, torch=str(torch.__version__),
        python=sys.executable, cutoff_KST=CUTOFF.isoformat(), approval_ref="WIP-176",
        synthetic_only=True, checkpoint_writes=0, formal_quality=False)


def arm(torch, model, schedules):
    import torch.nn.functional as F
    from torch.nn.attention import SDPBackend, sdpa_kernel

    generator = torch.Generator().manual_seed(SEED)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=0., foreach=False)
    model.train()
    model.set_anneal(1.0)
    events = []
    for schedule in schedules:
        assert time.time() + 25 < CUTOFF.timestamp() and not (OUT / "STOP").exists()
        ids = torch.randint(8, model.cfg.vocab_size, (1, WIDTH + 1), generator=generator).cuda()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        with model.visit(schedule) as route, sdpa_kernel(SDPBackend.MATH):
            logits = model(ids[:, :-1])
            loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), ids[:, 1:].reshape(-1))
            assert bool(torch.isfinite(loss))
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            torch.cuda.synchronize()
        events.append(dict(loss=float(loss.detach()), grad_norm=float(grad_norm), visits=route["visits"],
                           seconds=time.perf_counter() - start, route_sha256=model.route_sha256,
                           peak_allocated_bytes=torch.cuda.max_memory_allocated()))

    prompt = torch.randint(8, model.cfg.vocab_size, (1, 9), generator=generator).cuda()
    model.eval()
    with model.visit(schedules[-1]), torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
        model.freeze_quant()
        full = model(prompt, logits_last_only=True)
        _, cache = model(prompt[:, :-1], use_cache=True, logits_last_only=True)
        decoded, _ = model(prompt[:, -1:], past_kv=cache, use_cache=True, logits_last_only=True)
        probe = dict(max_abs=float((full - decoded).abs().max()),
                     greedy_equal=bool((full.argmax(dim=-1) == decoded.argmax(dim=-1)).all()),
                     close=bool(torch.isclose(full, decoded, atol=1e-4, rtol=1e-4).all()),
                     route_sha256=model.route_sha256, kv_entries=len(cache))
    return dict(events=events, token_targets=len(events) * WIDTH,
                layer_token_visits=sum(event["visits"] * WIDTH for event in events), cache_probe=probe)


def main(torch, mode):
    expected_device = "" if mode == "prepare" else "0"
    assert os.environ["CUDA_VISIBLE_DEVICES"] == expected_device
    cfg, weights, step = load_parent(torch)
    model = build_model(cfg)
    model.load_state_dict(weights, strict=True)
    schedules = policy_schedules(cfg, model.owner)
    profile = fingerprint(torch, schedules, step)
    if mode == "prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir()
        io.write(PROFILE, profile)
        print("P109_WARM_VISITS_READY", io.digest(PROFILE), flush=True)
        return

    assert time.time() + 320 < CUTOFF.timestamp() and profile == json.loads(PROFILE.read_bytes())
    assert not (OUT / "terminal.json").exists()
    entry = io.reserve_device()
    torch.backends.cuda.matmul.allow_tf32 = False
    print("P109_WARM_VISITS_START", os.getpid(), flush=True)
    model.cuda()
    results = {}
    for name in POLICIES:
        model.load_state_dict(weights, strict=True)
        gc.collect()
        torch.cuda.empty_cache()
        results[name] = arm(torch, model, schedules[name])
        print("P109_WARM_VISITS_ARM", name, results[name]["layer_token_visits"], flush=True)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    allocated = torch.cuda.memory_allocated()
    reserved = torch.cuda.memory_reserved()
    sources_unchanged = profile == fingerprint(torch, schedules, step)
    status = 0 if sources_unchanged else 8
    print("P109_WARM_VISITS_PRE_EXIT", allocated, reserved, sources_unchanged, flush=True)
    io.write(OUT / "terminal.json", dict(exit=status, entry=entry, results=results,
        profile_sha256=io.digest(PROFILE), allocator_pre_exit_bytes=allocated,
        reserved_pre_exit_bytes=reserved, sources_unchanged=sources_unchanged, checkpoint_writes=0))
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "actual"))
    args = parser.parse_args()
    import torch

    torch.set_num_threads(1)
    raise SystemExit(main(torch, args.mode))
