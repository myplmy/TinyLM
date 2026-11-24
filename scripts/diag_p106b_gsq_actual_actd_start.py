"""Compare hard STE and GSQ starts using an existing causal ACTD teacher cache."""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from scripts import diag_p102a_g4_joint_ce_kl_batch8 as sampling
from scripts import diag_p106b_actd_real_cache_updates as input_cache
from scripts import interactive_research_infer as manual


ROOT = input_cache.ROOT
TAG = "p106b_gsq_actual_actd_start_v2_20261119"
OUT = input_cache.EVIDENCE / TAG
OUT_PROFILE = OUT / "profile.json"
PLAN = input_cache.PLAN
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
ARMS = ("ste", "gsq")
UPDATES = 8
TEMPERATURES = (1., 1., .85, .85, .70, .70, .55, .55)
SEED = 1337
LR = 2e-4
LIMIT = 240


def time_gate(reserve=0):
    if (END - datetime.now(END.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("Current WIP177 time window or local STOP reached")


def sources():
    from tinylm.config import build_config

    cache, groups = input_cache.inputs()
    config = build_config("m100s10", "dense", input_cache.WIDTH, True)
    if (config.vocab_size, config.n_layers, config.dim, config.tie_mlp) != (32768, 14, 768, False):
        raise ValueError("Original dense14 geometry required")
    pins = dict(cache["sources"])
    for path in (Path(__file__).resolve(), ROOT / "scripts/p106b_gsq_objective.py",
                 ROOT / "scripts/p093b_native_repair.py", Path(sampling.__file__).resolve()):
        pins[path.relative_to(ROOT).as_posix()] = manual.file_sha(path)
    parameters = dict(tag=TAG, user_directive=177, end=END.isoformat(), cases=list(ARMS), seed=SEED,
                      optimizer="AdamW_FIXED_CLIP1", lr=LR, real_cache=cache["counts"],
                      attention="MATH", dtype="BF16", config=json.loads(json.dumps(asdict(config))), updates=UPDATES,
                      batch=input_cache.BATCH, accum=input_cache.ACCUM, width=input_cache.WIDTH,
                      plan_sha256=manual.file_sha(PLAN), source_pins=pins, group_counts=cache["groups"],
                      gsq_temperatures=list(TEMPERATURES), gsq_logit_strength=4.6,
                      actd_weight=.3, teachers_replayed=0, original_checkpoint_loads=0,
                      output_checkpoint_writes=0, formal_train_or_held_quality=False)
    return parameters, groups, config


def seal():
    time_gate()
    parameters, _, _ = sources()
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    input_cache.native.write(OUT_PROFILE, parameters)
    verify()
    print("GSQ_ACTD_SEAL", parameters["real_cache"], parameters["source_pins"][Path(__file__).resolve().relative_to(ROOT).as_posix()],
          flush=True)


def verify():
    saved = input_cache.read(OUT_PROFILE)
    current, groups, config = sources()
    if saved != current:
        raise ValueError("The exact plan, old teacher samples or current source changed")
    return saved, groups, config


def ternary_readback(bridge, previous=None):
    """Count deterministic codes and scales by the physical matrix that owns them."""
    import torch

    bridge.banks.eval()
    digest = sha256()
    counts: dict[str, Counter] = {}
    saved = {}
    with torch.no_grad():
        for key, bank in bridge.banks.items():
            if bridge.arm == "gsq":
                codes, scales = bank.code_scale()
            else:
                weights = bank.matrix().reshape(bank.master.size(0), -1, bank.group)
                codes = weights.sign().to(torch.int8)
                scales = weights.abs().amax(-1, keepdim=True)
            code_array = codes.cpu().numpy().reshape(-1)
            scale_array = scales.cpu().numpy().reshape(-1)
            label = ("shared_embedding" if key == bridge.embedding else
                     "shared_embedding_projection" if key == bridge.embedding_up else "body")
            digest.update(key.encode())
            digest.update(code_array.tobytes())
            totals = counts.setdefault(label, Counter())
            totals.update(negative=int(np.count_nonzero(code_array == -1)),
                          zero=int(np.count_nonzero(code_array == 0)),
                          positive=int(np.count_nonzero(code_array == 1)), elements=code_array.size)
            if previous is None:
                saved[key] = (code_array, scale_array)
            else:
                old_codes, old_scales = previous[key]
                totals.update(code_changes=int(np.count_nonzero(code_array != old_codes)),
                              scale_changes=int(np.count_nonzero(scale_array != old_scales)))
        for totals in counts.values():
            if totals["elements"] != totals["negative"] + totals["zero"] + totals["positive"]:
                raise ValueError("Realized deterministic values are not ternary")
    return {"sha256": digest.hexdigest().upper(), "counts": counts}, saved


def micro_terms(model, rows, denominator):
    from scripts.p106b_actd_consumer import components
    from tinylm.train.mtp_sft import Record, pad_records

    records = [Record(x, y, segment) for x, y, segment, _ in rows]
    x, y, segments = pad_records(records, 0, "cuda", fixed_width=input_cache.WIDTH,
                                 batch_size=input_cache.BATCH)
    positions = [dict(pos, batch_row=index) for index, row in enumerate(rows) for pos in row[3]]
    return components(model, model(x, return_hidden=True), y, segments, positions,
                      ce_denominator=denominator["ce_targets"], actd_denominator=denominator["actd_targets"],
                      enable_actd=True)


def train_arm(arm, profile, groups, config):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.p106b_gsq_objective import ObjectiveBridge
    from tinylm.model.transformer import TiedMLPTransformer

    torch.manual_seed(SEED)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 10000 * (1 << 20):
        raise MemoryError("Current single-device free memory is under 10,000 MiB")
    model = TiedMLPTransformer(config)
    initial_core = manual.state_fingerprint(model)
    model.cuda().train()
    model.set_anneal(1.)
    bridge = ObjectiveBridge(model, arm, logit_strength=profile["gsq_logit_strength"])
    parameters = bridge.parameters_for_optimizer()
    optimizer = torch.optim.AdamW(parameters, lr=LR, weight_decay=0., foreach=False, fused=False)
    begin, baseline_codes = ternary_readback(bridge)
    history = []
    with bridge.installed(), sdpa_kernel(SDPBackend.MATH):
        model.eval()
        with torch.no_grad(), bridge.realization(SEED, backward_expected=False):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                probe = micro_terms(model, groups[0][:input_cache.BATCH], profile["group_counts"][0])
            start_loss = {name: float(probe[name]) for name in ("ce_sum", "anchor_sum", "residual_sum")}
            del probe
        model.train()
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        for step, temperature in enumerate(TEMPERATURES, 1):
            time_gate(15)
            group_index = (step - 1) % len(groups)
            group = groups[group_index]
            denominator = profile["group_counts"][group_index]
            optimizer.zero_grad(set_to_none=True)
            if arm == "gsq":
                for bank in bridge.banks.values():
                    bank.temperature = temperature
            totals = Counter()
            tick = time.perf_counter()
            for micro, i in enumerate(range(0, len(group), input_cache.BATCH)):
                with bridge.realization(7331 + (step-1)*input_cache.ACCUM + micro):
                    with torch.autocast("cuda", dtype=torch.bfloat16):
                        terms = micro_terms(model, group[i:i+input_cache.BATCH], denominator)
                        loss = terms["ce_sum"] / denominator["ce_targets"]
                        loss = loss + profile["actd_weight"] * (terms["anchor_sum"] + terms["residual_sum"]) / denominator["actd_targets"]
                    bridge.backward(loss)
                    totals.update(ce_targets=terms["ce_targets"], actd_targets=terms["actd_positions"],
                                  ce_sum=terms["ce_sum"].detach().item(),
                                  actd_sum=(terms["anchor_sum"] + terms["residual_sum"]).detach().item())
                    del terms, loss
            if (totals["ce_targets"], totals["actd_targets"]) != (denominator["ce_targets"], denominator["actd_targets"]):
                raise ValueError("Measured supervision differs from the original group")
            grads = [p.grad.detach() for p in parameters if p.grad is not None]
            maximum = torch.stack(torch._foreach_norm(grads, float("inf"))).max().item()
            emb_grads = [p.grad.detach() for p in bridge.banks[bridge.embedding].parameters() if p.grad is not None]
            emb_max = torch.stack(torch._foreach_norm(emb_grads, float("inf"))).max().item()
            norm = torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True).item()
            if not (norm > 0 and emb_max > 0):
                raise ValueError("A planned update did not reach the shared embedding or model")
            optimizer.step()
            bridge.project()
            torch.cuda.synchronize()
            row = dict(totals, step=step, grad_norm=norm, grad_max=maximum, shared_embedding_grad_max=emb_max,
                       temperature=temperature if arm == "gsq" else None, seconds=time.perf_counter()-tick)
            history.append(row)
            print("GSQ_ACTD_UPDATE", arm, row, flush=True)
        peaks = dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())
    final, _ = ternary_readback(bridge, baseline_codes)
    collapse = {name: any(row[key] == 0 or row[key]/row["elements"] >= .99 for key in ("negative","zero","positive"))
                for name, row in final["counts"].items()}
    optimizer_steps = sorted({int(state["step"].item()) for state in optimizer.state.values()})
    if optimizer_steps != [UPDATES] or not any(row["scale_changes"] for row in final["counts"].values()):
        raise ValueError("Real optimizer/scale updates were not observed")
    return dict(arm=arm, initial_core_sha256=initial_core, initial_codes=begin, final_codes=final,
                deterministic_input_probe=start_loss, collapse_signal=collapse, history=history,
                optimizer_steps=optimizer_steps, training_peak=peaks, inventory=bridge.inventory(),
                source_teacher_reruns=0, checkpoint_writes=0)


def worker(arm):
    time_gate(115)
    profile, groups, config = verify()
    manual.require_idle_gpu()
    result = train_arm(arm, profile, groups, config)
    input_cache.native.write(OUT / f"{arm}.json", result)


def run():
    time_gate(LIMIT)
    profile, _, _ = verify()
    exits = {}
    physical = {}
    for arm in ARMS:
        time_gate(115)
        manual.require_idle_gpu()
        path = OUT / f"{arm}_device_100ms.csv"
        with path.open("xb") as stream:
            sampler = subprocess.Popen((*sampling.DEVICE, f"--loop-ms={sampling.INTERVAL_MS}"), stdout=stream)
            try:
                command = ["timeout", "--kill-after=8s", "104s", sys.executable, "-B", "-u", "-m",
                           "scripts.diag_p106b_gsq_actual_actd_start", "worker", arm]
                process = subprocess.run(command, cwd=ROOT, check=False)
                exits[arm] = process.returncode
                print("GSQ_ACTD_TERMINAL", arm, exits[arm], flush=True)
            finally:
                if sampler.poll() is None:
                    sampler.terminate()
                sampler.wait(timeout=8)
        samples = sampling.read_samples(path)
        if not samples:
            raise RuntimeError("Physical device sampling produced no records")
        physical[arm] = dict(samples=len(samples), peak=max(samples, key=lambda row: row["occupied_mib"]))
    released = manual.require_idle_gpu()
    results = {arm: input_cache.read(OUT / f"{arm}.json") for arm, code in exits.items() if code == 0}
    folded = len(results) == len(ARMS)
    equivalent = False
    if folded:
        a, b = (results[arm] for arm in ARMS)
        equivalent = (a["initial_core_sha256"] == b["initial_core_sha256"]
                      and a["initial_codes"] == b["initial_codes"]
                      and a["deterministic_input_probe"] == b["deterministic_input_probe"])
    source_preserved = all(manual.file_sha(ROOT / path) == digest
                           for path, digest in profile["source_pins"].items())
    complete = folded and equivalent and source_preserved
    input_cache.native.write(OUT / "report.json", dict(exits=exits, paired_initial_match=equivalent,
        result_complete=complete, device=physical, released=released, source_preserved=source_preserved,
        profile_sha256=manual.file_sha(OUT_PROFILE), arms=results))
    return 0 if complete else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare","actual","worker"))
    parser.add_argument("arm", choices=ARMS, nargs="?")
    args = parser.parse_args()
    expected = "" if args.phase == "prepare" else "0"
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected:
        parser.error("Use the isolated CPU or the one authorized CUDA device")
    if expected and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Deterministic cuBLAS configuration required")
    if args.phase == "worker" and args.arm:
        worker(args.arm)
    elif args.phase == "prepare" and args.arm is None:
        seal()
    elif args.phase == "actual" and args.arm is None:
        return run()
    else:
        parser.error("An arm is required only for the worker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
