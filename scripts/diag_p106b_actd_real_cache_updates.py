"""Paired in-memory Native updates using the preserved, causally aligned ACTD cache."""

import argparse
from collections import Counter
from datetime import datetime
import gc
import json
import os
from pathlib import Path
import time

from scripts import diag_p106b_alm_cache as encoder
from scripts import diag_p106b_gsq_objective as native
from scripts import interactive_research_infer as manual
from scripts.p106b_actd_cache import accepted_positions
from scripts.p106b_shards import verify


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_result/evidence"
SOURCE = EVIDENCE / "p106b_actd_top128_v1_20261113"
TAG = "p106b_actd_real_cache_updates_v2_20261119"
OUT = EVIDENCE / TAG
PLAN = ROOT / "test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md"
DEADLINE = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
POLICY = "causal_left_variant"
MODEL = "new595-broad-q"
BATCH, ACCUM, WIDTH, UPDATES = 8, 4, 1024, 4
LR, ACTD_WEIGHT = 1e-5, 0.3
LEGACY_CONFIG_SHA = "3F8D9DD89665F77B2915298B0BFAA377FC1338958A5F9808EAB147ADCBB5D8EF"
P109_CONFIG_SHA = "63FD8974FF221708D9E8265586528DA10D78F7C27C4E9B5A0C0D997E0A7CA1B3"
PINNED_CODE = (
    "scripts/diag_p106b_actd_real_cache_updates.py",
    "scripts/diag_p106b_alm_cache.py",
    "scripts/diag_p106b_gsq_objective.py",
    "scripts/diag_p107_hybrid_mntp.py",
    "scripts/interactive_research_infer.py",
    "scripts/p106b_weight_route.py",
    "scripts/p106b_actd_anchor.py",
    "scripts/p106b_actd_cache.py",
    "scripts/p106b_actd_consumer.py",
    "scripts/p106b_shards.py",
    "tinylm/train/mtp_sft.py",
    "tinylm/model/transformer.py",
    "tinylm/model/ternary.py",
    "tinylm/model/modules.py",
    "tinylm/config.py",
)


def authority(reserve=0):
    if (DEADLINE - datetime.now(DEADLINE.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("User 177 experiment time or stop limit reached")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_shards(folder, manifest):
    verify(folder, manifest)
    for shard in manifest["shards"]:
        with (folder / shard["path"]).open(encoding="utf-8") as stream:
            yield from map(json.loads, stream)


def counts(group):
    return dict(rows=len(group), input_tokens=sum(len(row[0]) for row in group),
                ce_targets=sum(sum(target != -100 for target in row[1]) for row in group),
                actd_targets=sum(len(row[3]) for row in group))


def verify_selected_checkpoint(entry):
    manifest, _ = manual.small_json(manual.MANIFEST)
    old_sources = manifest["source_sha256"]
    training_sources = {**old_sources, "tinylm/config.py": P109_CONFIG_SHA}
    current_sources = manual.required_source_pins(ROOT)
    if (manifest["schema"] != manual.MANIFEST_SCHEMA or manifest["inference_only"] is not True
            or old_sources.get("tinylm/config.py") != LEGACY_CONFIG_SHA
            or current_sources != training_sources
            or manifest["entries"][MODEL] != entry or manifest["tokenizer"]["sha256"] != manual.TOKENIZER_SHA):
        raise ValueError("The training reproduction requires the documented P109-only configuration change")
    spec = manual.resolve_model(MODEL)
    completed = manual.inspect_model(spec)
    if completed["status"] != "READY_METADATA_ONLY":
        raise ValueError("The selected legacy model needs actual train completion evidence")
    report = completed["report"]
    if (entry["report"]["sha256"] != completed["report_sha256"]
            or entry["checkpoint"]["sha256"] != report["checkpoint_sha256"]
            or entry["core_sha256"] != report["final_core_sha256"]
            or entry["header"]["quantization_route"] != report["quantization_route"]):
        raise ValueError("The selected checkpoint was not bound to that completed training run")
    manual.verify_descriptor(entry["report"], spec.report, ROOT)
    manual.verify_descriptor(entry["activity"], spec.activity, ROOT)
    manual.verify_descriptor(manifest["tokenizer"], manual.TOKENIZER, ROOT)


def load_student(entry):
    spec = manual.resolve_model(MODEL)
    torch, config_type, model_type, route = manual.inference_modules()
    torch.set_num_threads(2)
    payload = manual.read_selected_payload(torch, spec, entry)
    cfg = config_type(**payload["cfg"])
    manual.validate_cfg(cfg, entry["header"])
    with torch.device("cpu"), torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(61105)
        model = model_type(cfg)
    with route.weight_route(model, "ternary"):
        route.load_routed_state(model, payload, "ternary")
        if manual.state_fingerprint(model) != entry["core_sha256"]:
            raise ValueError("The reconstructed original student core differs")
    model.clear_quant()
    return model


def inputs():
    profile_path, report_path = SOURCE / "profile.json", SOURCE / "teacher/report.json"
    edge_path, witness_path = SOURCE / "anchor_lookup.json", SOURCE / "ROOT_TEACHER_EXIT_v1.json"
    previous, report, witness = map(read, (profile_path, report_path, witness_path))
    if (previous["secondary_policy"] != POLICY or previous["corpus_admitted"] is not False
            or previous["k"] != 128 or previous["student_vocab"] != 32768
            or report["status"] != "ACTD_NATIVE_TOP128_COMPLETE" or report["rows_completed"] != 128
            or report["returncode"] != 0 or not report["sources_and_inputs_unchanged"]
            or report["owned_model_alive_after_release"] is not False
            or report["final_cuda_cleanup"]["allocated_bytes"] or report["final_cuda_cleanup"]["reserved_bytes"]
            or witness["actual_process_exit_code"] != 0
            or witness["report_sha256"] != manual.file_sha(report_path)
            or witness["profile_sha256"] != report["profile_sha256"]
            or report["profile_sha256"] != manual.file_sha(profile_path)
            or previous["anchor_lookup_sha256"] != manual.file_sha(edge_path)):
        raise ValueError("The original ACTD inputs and completed teacher cache must match")
    rows = list(read_shards(SOURCE, previous["prepared_manifest"]))
    cached_rows = list(read_shards(SOURCE / "teacher", report["cache_manifest"]))
    cached = {row["row_id"]: row for row in cached_rows}
    if (len(rows) != 128 or len(cached_rows) != 128
            or len(cached) != 128 or set(cached) != {row["row_id"] for row in rows}
            or Counter(row["language"] for row in rows) != {"en": 64, "ko": 64}):
        raise ValueError("Exact original train row coverage required")
    anchors = read(edge_path)
    records = []
    for row in rows:
        saved = cached[row["row_id"]]
        if (saved["schema"] != "P106B_ACTD_NATIVE_TOP128_ROW_V1"
                or saved["prepared_row_sha256"] != encoder.object_sha(row)):
            raise ValueError("Cached teacher predictor belongs to a different prepared row")
        distributions = {int(index): value for index, value in saved["distributions"].items()}
        good, held = accepted_positions(row, distributions, policy=POLICY, k=128,
                                        anchor_lookup=anchors, student_vocab=32768)
        if (saved["acceptance"][POLICY] != {"accepted": len(good), "held": len(held)}
                or any(pos["lookahead_characters"] != 0
                       or pos["teacher_character_end"] > pos["student_character_end"] for pos in good)):
            raise ValueError("Causal acceptance differs from actual cache provenance")
        packed = row["packed"]["student"]
        x, y, segments = packed["ids"][:-1], packed["labels"][1:], packed["turn_ids"][1:]
        if not len(x) == len(y) == len(segments) <= WIDTH or sum(t != -100 for t in y) != row["ce_targets"]:
            raise ValueError("Original supervised sequence length or shift changed")
        records.append((x, y, segments, good))
    totals = counts(records)
    if totals != dict(rows=128, input_tokens=32216, ce_targets=772, actd_targets=611):
        raise ValueError("Actual input and target denominators differ from the plan")
    if report["accepted_positions"][POLICY] != 611 or report["held_positions"][POLICY] != 161:
        raise ValueError("Original teacher acceptance accounting changed")
    groups = [records[start:start+BATCH*ACCUM] for start in range(0, len(records), BATCH*ACCUM)]
    by_group = [counts(group) for group in groups]
    if any(row["ce_targets"] <= 0 or row["actd_targets"] <= 0 for row in by_group):
        raise ValueError("Each original group needs both loss denominators")
    model = previous["student_model"]
    if native.MODEL != MODEL or previous["student_pad_id"] != 0:
        raise ValueError("Exact original Native student and pad ID required")
    verify_selected_checkpoint(model)
    paths = [ROOT / source for source in (*PINNED_CODE, manual.MANIFEST, manual.TOKENIZER)]
    paths.extend(ROOT / model[key]["path"] for key in ("report", "activity"))
    paths.extend((profile_path, report_path, edge_path, witness_path))
    for folder, manifest in ((SOURCE, previous["prepared_manifest"]),
                             (SOURCE / "teacher", report["cache_manifest"])):
        paths.extend(folder / entry["path"] for entry in manifest["shards"])
    pins = {path.relative_to(ROOT).as_posix(): manual.file_sha(path) for path in paths}
    profile = dict(tag=TAG, user_directive=177, deadline=DEADLINE.isoformat(),
                   cases="ORIGINAL_BOUNDED_TECHNICAL_TRAIN128", model=model,
                   plan_sha256=manual.file_sha(PLAN),
                   batch=BATCH, accum=ACCUM, width=WIDTH, updates=UPDATES,
                   pad_id=0, seed=1337, dtype="BF16", optimizer="ADAMW_LR1E5_CLIP1",
                   lr=LR, policy=POLICY, actd_weight=ACTD_WEIGHT, sources=pins, groups=by_group,
                   counts=totals, original_end=witness["actual_process_exit_code"],
                   train_corpus_admitted=False, held_out_evaluation=False, checkpoint_writes=0)
    return profile, groups


def prepare():
    import torch

    authority()
    profile, _ = inputs()
    student = load_student(profile["model"])
    if torch.cuda.is_initialized() or any(p.is_cuda for p in student.parameters()):
        raise RuntimeError("Student preflight must remain on CPU")
    del student
    OUT.mkdir()
    (OUT / "plan_at_execution.md").write_bytes(PLAN.read_bytes())
    native.write(OUT / "profile.json", profile)
    print("ACTD_REAL_PREFLIGHT", profile["counts"], profile["groups"], flush=True)


def train_arm(profile, groups, enable_actd):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.p106b_actd_consumer import components
    from tinylm.train.mtp_sft import Record, pad_records

    model = load_student(profile["model"])
    model.cfg.grad_checkpoint = True
    model.cuda().train()
    torch.manual_seed(profile["seed"])
    initial = manual.state_fingerprint(model)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=LR, betas=(.9, .95), weight_decay=0.,
                                  foreach=False, fused=False)
    history = []
    torch.cuda.reset_peak_memory_stats()
    for ordinal, (group, denominator) in enumerate(zip(groups, profile["groups"], strict=True), 1):
        authority(10)
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        started = time.perf_counter()
        ce_sum = anchor_sum = residual_sum = 0.
        actual_ce = actual_actd = 0
        for start in range(0, len(group), BATCH):
            rows = group[start:start+BATCH]
            records = [Record(x, y, segments) for x, y, segments, _ in rows]
            x, y, segments = pad_records(records, profile["pad_id"], "cuda",
                                         fixed_width=WIDTH, batch_size=BATCH)
            positions = [dict(pos, batch_row=index) for index, row in enumerate(rows)
                         for pos in row[3]] if enable_actd else []
            with sdpa_kernel(SDPBackend.MATH):
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    hidden = model(x, return_hidden=True)
                    terms = components(model, hidden, y, segments, positions,
                                       ce_denominator=denominator["ce_targets"],
                                       actd_denominator=denominator["actd_targets"],
                                       enable_actd=enable_actd)
                    loss = terms["ce_sum"] / denominator["ce_targets"]
                    loss = loss + ACTD_WEIGHT * (terms["anchor_sum"] + terms["residual_sum"]) / denominator["actd_targets"]
                loss.backward()
            ce_sum += terms["ce_sum"].detach().item()
            anchor_sum += terms["anchor_sum"].detach().item()
            residual_sum += terms["residual_sum"].detach().item()
            actual_ce += terms["ce_targets"]
            actual_actd += terms["actd_positions"]
            del loss, terms, hidden, x, y, segments
        if actual_ce != denominator["ce_targets"] or actual_actd != (denominator["actd_targets"] if enable_actd else 0):
            raise ValueError("Actual optimizer group has different supervised positions")
        gradients = [p.grad.detach() for p in params if p.grad is not None]
        grad_max = torch.stack(torch._foreach_norm(gradients, float("inf"))).max().item()
        grad_norm = torch.nn.utils.clip_grad_norm_(params, 1., error_if_nonfinite=True).item()
        if not grad_norm > 0:
            raise ValueError("An optimizer group has no parameter signal")
        optimizer.step()
        torch.cuda.synchronize()
        row = dict(update=ordinal, ce_targets=actual_ce, actd_targets=actual_actd,
                   ce_sum=ce_sum, anchor_sum=anchor_sum, residual_sum=residual_sum,
                   grad_norm=grad_norm, grad_max=grad_max, seconds=time.perf_counter()-started)
        history.append(row)
        print("ACTD_REAL_UPDATE", enable_actd, row, flush=True)
    final = manual.state_fingerprint(model)
    optimizer_steps = sorted({int(state["step"].item()) for state in optimizer.state.values()})
    result = dict(initial=initial, final=final, history=history, optimizer_steps=optimizer_steps,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                  peak_reserved_bytes=torch.cuda.max_memory_reserved())
    if initial == final or optimizer_steps != [UPDATES]:
        raise ValueError("All trained AdamW parameters must apply the four updates")
    return result


def actual():
    import torch
    from scripts.diag_p107_hybrid_mntp import close_owned_cuda

    authority(180)
    saved = read(OUT / "profile.json")
    current, groups = inputs()
    if saved != current or (OUT / "report.json").exists():
        raise ValueError("A single fresh execution with the original sealed profile is required")
    point = manual.require_idle_gpu()
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 8 * (1 << 30):
        raise MemoryError("The single GPU needs at least 8 GiB free for matched updates")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    result = dict(gpu_entry=point, profile_sha256=manual.file_sha(OUT / "profile.json"),
                  checkpoint_writes=0, teacher_reruns=0, arms={})
    for name, enabled in (("ce", False), ("ce_actd", True)):
        result["arms"][name] = train_arm(saved, groups, enabled)
        gc.collect()
        torch.cuda.empty_cache()
    a, b = result["arms"].values()
    if (a["initial"] != b["initial"] or a["history"][0]["ce_sum"] != b["history"][0]["ce_sum"]
            or a["final"] == b["final"]):
        raise ValueError("Paired initial-state, first CE or final-state contract failed")
    close_owned_cuda(torch, result)
    checkpoint = ROOT / saved["model"]["checkpoint"]["path"]
    result["source_preserved"] = (
        all(manual.file_sha(ROOT / path) == digest for path, digest in saved["sources"].items())
        and manual.file_sha(checkpoint) == saved["model"]["checkpoint"]["sha256"]
    )
    if not result["source_preserved"]:
        raise ValueError("An original input or selected checkpoint changed")
    native.write(OUT / "report.json", result)
    print("ACTD_REAL_RESULT", a["optimizer_steps"], b["optimizer_steps"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "actual"))
    phase = parser.parse_args().phase
    if os.environ.get("CUDA_VISIBLE_DEVICES") != ("" if phase == "prepare" else "0"):
        parser.error("Use an isolated CPU preflight or the explicitly selected GPU")
    if phase == "actual" and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Deterministic cuBLAS configuration is required")
    (prepare if phase == "prepare" else actual)()


if __name__ == "__main__":
    main()
