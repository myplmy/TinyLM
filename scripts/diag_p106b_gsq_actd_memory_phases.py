"""Attribute live CUDA storage during the existing dense14 GSQ/STE ACTD objective."""

import argparse
import ast
from contextlib import nullcontext
from datetime import datetime, timedelta
import gc
import math
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import weakref

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_gsq_actual_actd_start as original
from scripts import diag_p106b_gsq_scaled_actd_deploy as scaled
from scripts import p106b_actd_consumer as actd
from scripts import p106b_gsq_objective as objective
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p106b_gsq_scaled_actd_deploy import read, write
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.p106b_gsq_coordinates import ScaledGSQBank
from tinylm.model.transformer import TiedMLPTransformer


ROOT, SHA, sampling = original.ROOT, original.manual.file_sha, original.sampling
TAG = "p106b_gsq_actd_memory_phases_v1_20261119"
OUT = original.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
ARMS = ("ste", "scaled_gsq")
STEPS, LIMIT = 2, 95
BATCH, ACCUM = original.input_cache.BATCH, original.input_cache.ACCUM
SCALED_LOG = ROOT / "test_result/101_log_20261119_P106B_Stage7gsY_ScaledDeploy_GPU.txt"
TRANSFORMER = "tinylm/model/transformer.py"
OLD_TRANSFORMER = "551A9CD015BBEFC00CEFD981B5DFBCAB3C3DB594026608C8004902850989FA7E"
CURRENT_TRANSFORMER = "75F305C23CB7C5E0D03926F8D1B81A06A7FFE7F5738ACF002D24160E76E374A9"
VISIBILITY = "tinylm/model/visibility.py"
OLD_VISIBILITY = "7D7E0BC42077585998FF312E707C8E5D8A041CCCD0F7097A070EB38F4D73BABD"
CURRENT_VISIBILITY = "73DCF0B8E7279B614F9758556A80F2EE4B97CD3B66D0E201A17E7AAB19736FBB"


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(original.END.tzinfo) + timedelta(seconds=reserve) >= original.END:
        raise RuntimeError("owned STOP or deadline")


def verify(profile):
    assert profile["tag"] == TAG and profile["approval"] == 177
    assert all(SHA(ROOT / name) == expected for name, expected in profile["pins"].items())


def verify_cache_lineage(entry):
    cache, manual = original.input_cache, original.manual
    manifest, _ = manual.small_json(manual.MANIFEST)
    previous = manifest["source_sha256"]
    # Only the known opt-in document mask hook changed after the archived run.
    expected = {**previous, "tinylm/config.py": cache.P109_CONFIG_SHA, TRANSFORMER: CURRENT_TRANSFORMER,
                VISIBILITY: CURRENT_VISIBILITY}
    assert previous[TRANSFORMER] == OLD_TRANSFORMER and previous["tinylm/config.py"] == cache.LEGACY_CONFIG_SHA
    assert previous[VISIBILITY] == OLD_VISIBILITY
    assert manual.required_source_pins(ROOT) == expected
    assert manifest["schema"] == manual.MANIFEST_SCHEMA and manifest["inference_only"] is True
    assert manifest["entries"][cache.MODEL] == entry and manifest["tokenizer"]["sha256"] == manual.TOKENIZER_SHA
    spec = manual.resolve_model(cache.MODEL)
    completed = manual.inspect_model(spec)
    assert completed["status"] == "READY_METADATA_ONLY"
    report = completed["report"]
    assert entry["report"]["sha256"] == completed["report_sha256"]
    assert entry["checkpoint"]["sha256"] == report["checkpoint_sha256"]
    assert entry["core_sha256"] == report["final_core_sha256"]
    assert entry["header"]["quantization_route"] == report["quantization_route"]
    manual.verify_descriptor(entry["report"], spec.report, ROOT)
    manual.verify_descriptor(entry["activity"], spec.activity, ROOT)
    manual.verify_descriptor(manifest["tokenizer"], manual.TOKENIZER, ROOT)


def source_config():
    with patch.object(original.input_cache, "verify_selected_checkpoint", verify_cache_lineage):
        return original.sources()


def prepare():
    current, groups, _ = source_config()
    prior, control = [read(original.OUT / f"{name}.json") for name in ("profile", "report")]
    assert control["result_complete"] and control["paired_initial_match"]
    assert SHA(original.OUT / "profile.json") == control["profile_sha256"]
    assert all(current[key] == prior[key] for key in ("config", "seed", "optimizer", "lr", "real_cache",
                                                     "group_counts", "gsq_temperatures", "actd_weight"))
    archived = [ast.literal_eval(line.split("gsq ", 1)[1]) for line in SCALED_LOG.read_text().splitlines()
                if line.startswith("GSQ_ACTD_UPDATE gsq ")]
    assert len(archived) == 8 and len(groups) == 4 and all(len(group) == BATCH * ACCUM for group in groups)
    previous_profile = read(scaled.OUT / "profile.json")
    assert previous_profile["coordinate_gain"] == scaled.GAIN == 4096
    assert read(scaled.OUT / "deployment_recovered.json")["passed"]
    OUT.mkdir()
    sealed = OUT / "plan_at_execution.md"
    heading = "### Stage7gsZ — "
    _, text = original.PLAN.read_text(encoding="utf8").split(heading, 1)
    assert TAG in text
    sealed.write_text(heading + text, encoding="utf8")
    paths = (Path(__file__).resolve(), Path(actd.__file__), Path(objective.__file__),
             ROOT / "scripts/p106b_gsq_coordinates.py", original.OUT / "profile.json", original.OUT / "report.json",
             scaled.OUT / "profile.json", scaled.OUT / "deployment_recovered.json", SCALED_LOG, sealed)
    pins = dict(current["source_pins"])
    pins.update({str(path.relative_to(ROOT)): SHA(path) for path in paths})
    profile = dict(tag=TAG, approval=177, pins=pins, setup=current, initial={
        "core": control["arms"]["ste"]["initial_core_sha256"], "codes": control["arms"]["ste"]["initial_codes"]},
        expected={"ste": control["arms"]["ste"]["history"][:STEPS], "scaled_gsq": archived[:STEPS]})
    verify(profile)
    write(PROFILE, profile)
    print("GSQ_MEMORY_READY", current["batch"], current["accum"], current["width"],
          [row["actd_targets"] for row in current["group_counts"][:STEPS]], flush=True)


def storage(tensors, device="cuda"):
    found = {}
    for tensor in tensors:
        if isinstance(tensor, torch.Tensor) and tensor.device.type == device:
            value = tensor.untyped_storage()
            if value.nbytes():
                found[value.data_ptr()] = value.nbytes()
    return found


def persistent(bridge, optimizer):
    model = storage((*bridge.model.parameters(), *bridge.model.buffers()))
    banks = storage(bridge.banks.parameters())
    code = storage(p for name, p in bridge.banks.named_parameters() if name.endswith(("mask_logit", "sign_logit")))
    scales = storage(p for name, p in bridge.banks.named_parameters() if name.endswith(".scale"))
    states = [value for group in optimizer.state.values() for value in group.values()]
    moments = storage(states)
    return dict(model_bytes=sum(model.values()), frozen_master_bytes=sum(storage(bridge.masters.values()).values()),
                banks_bytes=sum(banks.values()), code_logits_bytes=sum(code.values()), scales_bytes=sum(scales.values()),
                optimizer_cuda_bytes=sum(moments.values()), optimizer_cpu_bytes=sum(storage(states, "cpu").values())), model | banks | moments


def sampled_forward(model, bridge, rows, denominators, known):
    refs, frontier, teacher = [], {}, {}
    original_sums = actd.actd_sums

    def pack(tensor):
        saved = tensor.detach()
        refs.append(weakref.ref(saved))
        return saved

    def observe_hidden(_module, _args, value):
        frontier.update(hidden_bytes=sum(storage((value,)).values()), allocated_after_model=torch.cuda.memory_allocated())

    def observe_teacher(logits, anchors, scores, **kwargs):
        teacher.update(storage((anchors, scores)))
        return original_sums(logits, anchors, scores, **kwargs)

    materialized = storage(bridge._current.values())
    hook = model.register_forward_hook(observe_hidden)
    try:
        with torch.autograd.graph.saved_tensors_hooks(pack, lambda x: x), patch.object(actd, "actd_sums", observe_teacher):
            terms = original.micro_terms(model, rows, denominators)
    finally:
        hook.remove()
    live = [value for ref in refs if (value := ref()) is not None]
    visible = storage(live)
    floating = storage(value for value in live if value.is_floating_point())
    excluded = known.keys() | materialized.keys() | teacher.keys()
    frontier.update(teacher_signal_bytes=sum(teacher.values()), outer_saved_total_bytes=sum(visible.values()),
                    teacher_saved_bytes=sum(visible[k] for k in visible.keys() & teacher.keys()),
                    external_saved_float_bytes=sum(floating[k] for k in floating.keys()-excluded),
                    external_saved_meta_bytes=sum(visible[k] for k in visible.keys()-floating.keys()-excluded),
                    materialized_weight_bytes=sum(materialized[k] for k in materialized.keys()-known.keys()),
                    allocated_after_loss=torch.cuda.memory_allocated(), actd_positions=terms["actd_positions"])
    assert frontier["teacher_signal_bytes"] == 128 * 12 * terms["actd_positions"]
    return terms, frontier


def measure(arm, profile):
    _, groups, cfg = source_config()
    torch.manual_seed(profile["setup"]["seed"])
    model = TiedMLPTransformer(cfg)
    assert original.manual.state_fingerprint(model) == profile["initial"]["core"]
    model.cuda().train()
    model.set_anneal(1.)
    fix = patch.object(objective, "GSQBank", lambda *a, **kw: ScaledGSQBank(*a, **kw, gain=scaled.GAIN))
    with fix if arm == "scaled_gsq" else nullcontext():
        bridge = objective.ObjectiveBridge(model, "gsq" if arm == "scaled_gsq" else "ste", logit_strength=4.6)
    begin, codes = original.ternary_readback(bridge)
    del codes
    assert begin == profile["initial"]["codes"]
    params = bridge.parameters_for_optimizer()
    opt = torch.optim.AdamW(params, lr=original.LR, weight_decay=0., foreach=False, fused=False)
    moments, phases, history = {}, {}, []
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    with bridge.installed(), sdpa_kernel(SDPBackend.MATH):
        for step in range(STEPS):
            opt.zero_grad(set_to_none=True)
            for bank in bridge.banks.values():
                if arm == "scaled_gsq":
                    bank.temperature = original.TEMPERATURES[step]
            counts = profile["setup"]["group_counts"][step]
            ce_values, actd_values = [], []
            ce_targets = actd_targets = 0
            for micro in range(ACCUM):
                gate()
                group = groups[step][micro*BATCH:(micro+1)*BATCH]
                sample = (step, micro) == (1, 0)
                if sample:
                    moments, known = persistent(bridge, opt)
                    phases["allocated_before_realization"] = torch.cuda.memory_allocated()
                with bridge.realization(7331 + step * ACCUM + micro):
                    if sample:
                        phases["allocated_after_realization"] = torch.cuda.memory_allocated()
                    with torch.autocast("cuda", dtype=torch.bfloat16):
                        if sample:
                            terms, observed = sampled_forward(model, bridge, group, counts, known)
                            phases.update(observed)
                        else:
                            terms = original.micro_terms(model, group, counts)
                        teacher_loss = terms["anchor_sum"] + terms["residual_sum"]
                        loss = terms["ce_sum"] / counts["ce_targets"] + .3 * teacher_loss / counts["actd_targets"]
                    bridge.backward(loss)
                    if sample:
                        phases.update(allocated_after_backward=torch.cuda.memory_allocated(),
                                      gradient_bytes=sum(storage(p.grad for p in params).values()))
                    ce_values.append(float(terms["ce_sum"].detach()))
                    actd_values.append(float(teacher_loss.detach()))
                    ce_targets += terms["ce_targets"]
                    actd_targets += terms["actd_positions"]
                    del terms, loss, teacher_loss
                guard_card()
            expected = profile["expected"][arm][step]
            assert (ce_targets, actd_targets) == (expected["ce_targets"], expected["actd_targets"])
            totals = dict(ce_sum=sum(ce_values), actd_sum=sum(actd_values),
                          grad_norm=float(torch.nn.utils.clip_grad_norm_(params, 1., error_if_nonfinite=True)))
            assert all(math.isclose(value, expected[key], rel_tol=2e-5, abs_tol=1e-6) for key, value in totals.items()), totals
            opt.step()
            bridge.project()
            guard_card()
            history.append(totals)
    return dict(arm=arm, persistent=moments, phases=phases, history=history,
                max_allocated=torch.cuda.max_memory_allocated(), max_reserved=torch.cuda.max_memory_reserved())


def guard_card():
    free, total = torch.cuda.mem_get_info()
    if total - free > 13_000_000_000:
        raise RuntimeError("card occupancy exceeded 13 GB")


def worker(arm, profile):
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    free, total = torch.cuda.mem_get_info()
    assert torch.cuda.device_count() == 1 and free >= 12500 * 2**20
    torch.cuda.set_per_process_memory_fraction((13_000_000_000 - (total-free) - 256*2**20) / total)
    result = measure(arm, profile)
    gc.collect()
    write(OUT / f"{arm}_material.json", result)
    close_owned_cuda(torch, result)
    write(OUT / f"{arm}.json", result)
    print("GSQ_MEMORY_PHASES", arm, result["persistent"], result["phases"], flush=True)


def run(profile):
    entry = original.manual.require_idle_gpu()
    raw = OUT / "device_100ms.csv"
    exits = {}
    with raw.open("xb") as stream:
        monitor = subprocess.Popen((*sampling.DEVICE, f"--loop-ms={sampling.INTERVAL_MS}"), stdout=stream)
        try:
            for arm in ARMS:
                gate(LIMIT + 5)
                cmd = ["timeout", "--kill-after=4s", f"{LIMIT}s", sys.executable, "-B", "-m", __spec__.name, "worker", arm]
                exits[arm] = subprocess.run(cmd, cwd=ROOT).returncode
                if exits[arm] or not idle():
                    break
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    verify(profile)
    samples = sampling.read_samples(raw)
    returned = idle()
    receipt = dict(exits=exits, returned=returned, source_preserved=True, entry=entry,
                   device_peak=max(samples,key=lambda row:row["occupied_mib"]))
    write(OUT / "report.json", receipt)
    print("GSQ_MEMORY_RELEASE", receipt, flush=True)
    if exits != dict.fromkeys(ARMS, 0) or not returned:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    parser.add_argument("arm", choices=ARMS, nargs="?")
    args = parser.parse_args()
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.phase == "prepare" else "0")
    torch.set_num_threads(2)
    gate(2*LIMIT + 20 if args.phase == "run" else 0)
    if args.phase == "prepare":
        prepare()
    else:
        profile = read(PROFILE)
        if args.phase == "run":
            verify(profile)
            run(profile)
        else:
            worker(args.arm, profile)


if __name__ == "__main__":
    main()
