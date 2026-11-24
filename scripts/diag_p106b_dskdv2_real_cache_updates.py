"""Run paired Native updates with the original full-vocabulary DSKDv2 cache."""

import argparse
from collections import Counter
from datetime import datetime
import gc
import os
from pathlib import Path
import subprocess
import time

import numpy as np

from scripts import diag_p102a_g4_joint_ce_kl_batch8 as sampling
from scripts import diag_p106b_actd_real_cache_updates as actd
from scripts import interactive_research_infer as manual
from scripts.p106b_dskdv2_recovery import acceptance_contract, feature_contract


ROOT, EVIDENCE = actd.ROOT, actd.EVIDENCE
TAG = "p106b_dskdv2_real_cache_updates_v1_20261119"
OUT = EVIDENCE / TAG
PROFILE = OUT / "profile.json"
PROJECTORS = OUT / "initial_projectors.npz"
ORIGINAL = EVIDENCE / "p106b_dskdv2_hidden_v1_20261113"
RECOVERY = EVIDENCE / "p106b_dskdv2_hidden_recovery_v2_20261113"
HEADS = EVIDENCE / "p106b_dskdv2_heads_v1_20261113"
BRIDGE = EVIDENCE / "p106b_dskdv2_bridge_v1_20261113"
MAP = EVIDENCE / "p106b_actd_anchor_v1_20261113"
FEATURES = ROOT / "data_cache/p106b_dskdv2_hidden_v1_20261113"
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
ALPHA, LR, CHUNK = .03, 1e-5, 8


def gate(reserve=0):
    if (END - datetime.now(END.tzinfo)).total_seconds() <= reserve or (OUT / "STOP").exists():
        raise TimeoutError("User 177 time limit or local stop reached")


def file_stamp(path):
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]


def receipt(directory, report_path, witness_path):
    profile = directory / "profile.json"
    report = actd.read(report_path)
    witness = actd.read(witness_path)
    if (report["returncode"] != 0 or witness["actual_tool_exit"] != 0
            or witness["report_sha256"] != manual.file_sha(report_path)
            or report["profile_sha256"] != manual.file_sha(profile)
            or witness["profile_sha256"] != report["profile_sha256"]):
        raise ValueError("Matching immutable exit and model proof required")
    return report


def cache_inputs():
    recovery_report = RECOVERY / "actual/report.json"
    recovery_witness = RECOVERY / "ROOT_ACTUAL_EXIT_v1.json"
    recovered = receipt(RECOVERY, recovery_report, recovery_witness)
    manifest_path = RECOVERY / "features_manifest.json"
    saved = actd.read(RECOVERY / "profile.json")
    if (recovered["accepted_positions"] != 538 or recovered["corpus_admitted"] is not False
            or not recovered["sources_features_and_assets_unchanged"]
            or saved["features_manifest_sha256"] != manual.file_sha(manifest_path)):
        raise ValueError("Same closed original source features required")
    head_report, head_witness = BRIDGE / "head/report.json", BRIDGE / "ROOT_HEAD_EXIT_v1.json"
    head_gate = receipt(BRIDGE, head_report, head_witness)
    if head_gate["selected_head_policy"] != "CHUNK" or not head_gate["chunk_pass"]:
        raise ValueError("Previously verified short teacher-head operation required")
    paths = [recovery_report, recovery_witness, manifest_path, RECOVERY / "profile.json",
             head_report, head_witness, BRIDGE / "profile.json"]
    pos_dir = ORIGINAL / "teacher"
    pos_manifest = pos_dir / "positions_shards_manifest.json"
    source_witness = ORIGINAL / "ROOT_FINALIZER_FAILURE_v1.json"
    original_receipt = actd.read(source_witness)
    if (original_receipt["actual_tool_exit"] != 1
            or original_receipt["positions_manifest_sha256"] != manual.file_sha(pos_manifest)
            or original_receipt["profile_sha256"] != saved["original_profile_sha256"]):
        raise ValueError("The exact closed subartifact must match the preserved original exit")
    positions_manifest = actd.read(pos_manifest)
    saved_positions = list(actd.read_shards(pos_dir, positions_manifest))
    positions = {row["row_id"]: row for row in saved_positions}
    feature_manifest = actd.read(manifest_path)
    features = {row["row_id"]: row for row in feature_manifest["features"]}
    prepared_path = actd.SOURCE / "profile.json"
    prepared = actd.read(prepared_path)
    original_rows = list(actd.read_shards(actd.SOURCE, prepared["prepared_manifest"]))
    exact_ids = {row["row_id"] for row in original_rows}
    if (len(saved_positions) != 128 or feature_manifest["rows"] != 128 or len(original_rows) != 128
            or 128 != len(exact_ids) or set(positions) != exact_ids or set(features) != exact_ids):
        raise ValueError("Closed coverage of the original 128 rows required")
    paths.extend((pos_manifest, source_witness, prepared_path))
    paths.extend(pos_dir / record["path"] for record in positions_manifest["shards"])
    paths.extend(actd.SOURCE / record["path"] for record in prepared["prepared_manifest"]["shards"])
    mapping_path, mode_path = MAP / "teacher_to_student_anchors.json", MAP / "teacher_mapping_modes.json"
    mapping, modes = actd.read(mapping_path), actd.read(mode_path)
    paths += [mapping_path, mode_path]
    groups = []
    for raw in original_rows:
        row_id = raw["row_id"]
        pos, desc = positions[row_id], features[row_id]
        path = ROOT / desc["path"]
        if (path != FEATURES / (row_id + ".npy") or path.is_symlink()
                or desc["sha256"] != pos["feature_sha256"] or manual.file_sha(path) != desc["sha256"]
                or path.stat().st_size != desc["bytes"]
                or pos["prepared_row_sha256"] != actd.encoder.object_sha(raw)
                or not pos["original_ce_unchanged"] or pos["partial_token_fallback"]):
            raise ValueError("Original features, alignment and student record differ")
        array = np.load(path, allow_pickle=False, mmap_mode="r")
        feature_contract(array, tokens=len(raw["teacher"]["ids"])-1)
        if list(array.shape) != desc["shape"]:
            raise ValueError("Feature file shape differs from its recovered manifest")
        paths.append(path)
        student = raw["packed"]["student"]
        x, y, segment = student["ids"][:-1], student["labels"][1:], student["turn_ids"][1:]
        accepted = []
        for item in pos["positions"]:
            student_index = item["student_predictor_raw_index"]
            teacher_index = item["teacher_predictor_raw_index"]
            if (item["lookahead_bytes"] != 0 or not 0 <= student_index < len(y)
                    or not 0 <= teacher_index < len(array) or y[student_index] != item["student_target_id"]
                    or segment[student_index] != item["owner"]):
                raise ValueError("Exact zero-lookahead supervised position required")
            if acceptance_contract(item, mapping, modes):
                accepted.append((student_index, teacher_index, item["mapped_student_argmax"]))
        ids = [item[1] for item in accepted]
        groups.append((x, y, segment, accepted, np.ascontiguousarray(array[ids])))
    microgroup = actd.BATCH * actd.ACCUM
    groups = [groups[start:start+microgroup] for start in range(0, len(groups), microgroup)]
    denominators = [dict(rows=len(group), x=sum(len(row[0]) for row in group),
                         ce=sum(sum(y != -100 for y in row[1]) for row in group),
                         kd=sum(len(row[3]) for row in group)) for group in groups]
    if [sum(r[name] for r in denominators) for name in ("rows", "x", "ce", "kd")] != [128, 32216, 772, 538]:
        raise ValueError("The actual training positions differ from the intended original pool")
    entry = prepared["student_model"]
    actd.verify_selected_checkpoint(entry)
    paths += [ROOT / entry[key]["path"] for key in ("report", "activity")]
    return groups, denominators, entry, paths


def collect():
    groups, denominators, entry, files = cache_inputs()
    head_profile = actd.read(HEADS / "profile.json")
    asset, = [item for key, item in head_profile["teacher_assets"]["files"].items() if key.endswith(".safetensors")]
    head_path = Path(asset["resolved_path"])
    if not head_path.is_absolute() or not head_path.resolve().is_relative_to(ROOT / "HF/models--Qwen--Qwen3.5-0.8B-Base"):
        raise ValueError("The original local teacher asset is required")
    current_stamp = file_stamp(head_path)
    if current_stamp[2] != asset["bytes"]:
        raise ValueError("Original teacher asset size changed")
    paths = [Path(__file__).resolve(), Path(sampling.__file__).resolve(), HEADS / "profile.json", HEADS / "report.json",
             HEADS / "overlap_ids.json", ROOT / "scripts/p106b_dskdv2_bridge.py",
             ROOT / "scripts/p106b_dskdv2_contract.py", ROOT / "scripts/p106b_dskdv2_recovery.py",
             ROOT / "scripts/diag_p106b_alm_cache.py"]
    paths.extend(ROOT / name for name in (*actd.PINNED_CODE, manual.MANIFEST, manual.TOKENIZER))
    pins = {path.relative_to(ROOT).as_posix(): manual.file_sha(path) for path in set(files + paths)}
    profile = dict(tag=TAG, user_directive=177, end=END.isoformat(), source_pins=pins,
                   plan_sha256=manual.file_sha(actd.PLAN), teacher_head=str(head_path),
                   teacher_head_key=head_profile["teacher_key"], teacher_asset_sha256=asset["sha256"],
                   teacher_asset_stamp=current_stamp, denoms=denominators, student=entry,
                   alpha=ALPHA, lr=LR, batch=actd.BATCH, accum=actd.ACCUM, width=actd.WIDTH,
                   chunk=CHUNK, choice="CE_VS_REAL_NATIVE_DUALSPACE_DSKD", teacher_body_calls=0,
                   checkpoint_writes=0, corpus_admitted=False)
    return profile, groups


def load_head(profile):
    from safetensors import safe_open

    path = Path(profile["teacher_head"])
    if file_stamp(path) != profile["teacher_asset_stamp"]:
        raise ValueError("The sealed local teacher asset changed")
    with safe_open(path, framework="pt", device="cpu") as handle:
        head = handle.get_tensor(profile["teacher_head_key"]).float()
    if head.shape != (248320, 1024) or file_stamp(path) != profile["teacher_asset_stamp"]:
        raise ValueError("Expected the original stable full Qwen output head")
    return head


def prepare():
    import torch
    from scripts.p106b_dskdv2_bridge import initialize_native_bank

    gate()
    torch.set_num_threads(4)
    profile, _ = collect()
    path = Path(profile["teacher_head"])
    if manual.file_sha(path) != profile["teacher_asset_sha256"] or file_stamp(path) != profile["teacher_asset_stamp"]:
        raise ValueError("Original teacher asset SHA-256 mismatch")
    model = actd.load_student(profile["student"])
    align = actd.read(HEADS / "overlap_ids.json")
    initialized = initialize_native_bank(model, load_head(profile), align["student_ids"], align["teacher_ids"])
    past = actd.read(HEADS / "report.json")["initialization"]
    if len(align["student_ids"]) != 23302 or any(abs(past[k]-initialized["stats"][k]) > 1e-10
               for k in ("t2s_relative_logit_error", "s2t_relative_logit_error")):
        raise ValueError("Original actual projector initialization does not reproduce")
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU initialization must remain off CUDA")
    OUT.mkdir()
    with PROJECTORS.open("xb") as stream:
        np.savez(stream, t2s=initialized["t2s"].numpy(), s2t=initialized["s2t"].numpy())
    (OUT / "plan_at_execution.md").write_bytes(actd.PLAN.read_bytes())
    actd.native.write(PROFILE, dict(inputs=profile, projectors_sha256=manual.file_sha(PROJECTORS),
                                  initialization=initialized["stats"]))
    verify()
    print("DSKDV2_REAL_PREFLIGHT", profile["denoms"], initialized["stats"], flush=True)


def verify():
    sealed = actd.read(PROFILE)
    current, groups = collect()
    if sealed["inputs"] != current or sealed["projectors_sha256"] != manual.file_sha(PROJECTORS):
        raise ValueError("The prepared inputs or initial projectors differ")
    return current, groups


def train(name, profile, groups):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from torch.utils.checkpoint import checkpoint
    from scripts.p106b_actd_consumer import components
    from scripts.p106b_dskdv2_bridge import native_sums
    from tinylm.train.mtp_sft import Record, pad_records

    kd = name == "dskd"
    model = actd.load_student(profile["student"])
    model.cfg.grad_checkpoint = True
    model.cuda().train()
    torch.manual_seed(1337)
    initial = manual.state_fingerprint(model)
    student = [p for p in model.parameters() if p.requires_grad]
    if kd:
        head = load_head(profile).cuda()
        with np.load(PROJECTORS, allow_pickle=False) as data:
            pt = torch.nn.Parameter(torch.from_numpy(data["t2s"]).cuda())
            ps = torch.from_numpy(data["s2t"]).cuda()
            original_pt, original_ps = pt.detach().cpu(), ps.detach().cpu()
        trainable = student + [pt]
    else:
        trainable = student
    opt = torch.optim.AdamW(trainable, lr=LR, betas=(.9, .95), weight_decay=0., foreach=False, fused=False)
    torch.cuda.reset_peak_memory_stats()
    history = []

    def objective(hs, ht, up, embedding, wt, t2s, s2t, labels):
        with torch.autocast("cuda", enabled=False):
            terms = native_sums(hs, ht, up, embedding, wt, t2s, s2t, labels)
        return terms["student_kd_sum"], terms["teacher_kd_sum"], terms["projector_ce_sum"]

    for step, (group, counts) in enumerate(zip(groups, profile["denoms"], strict=True), 1):
        gate(15)
        opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        start = time.perf_counter()
        total = Counter(ce=0, kd=0, ce_sum=0., student_kl=0., teacher_kl=0., projector_ce=0.)
        for begin in range(0, len(group), actd.BATCH):
            batch = group[begin:begin+actd.BATCH]
            records = [Record(x, y, segment) for x, y, segment, _, _ in batch]
            x, y, segment = pad_records(records, 0, "cuda", fixed_width=actd.WIDTH, batch_size=actd.BATCH)
            with sdpa_kernel(SDPBackend.MATH):
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    hidden = model(x, return_hidden=True)
                    ce = components(model, hidden, y, segment, [], ce_denominator=counts["ce"],
                                    actd_denominator=counts["kd"], enable_actd=False)
                loss = ce["loss"]
                total.update(ce=ce["ce_targets"], ce_sum=ce["ce_sum"].detach().item())
                if kd:
                    for index, (_, _, _, positions, matrix) in enumerate(batch):
                        for start_at in range(0, len(positions), CHUNK):
                            sub = positions[start_at:start_at+CHUNK]
                            selected = torch.tensor([record[0] for record in sub], device="cuda")
                            labels = torch.tensor([record[2] for record in sub], device="cuda")
                            ht = torch.from_numpy(matrix[start_at:start_at+len(sub)]).cuda()
                            parts = checkpoint(objective, hidden[index].index_select(0, selected).float(), ht,
                                               model._emb_up_w(), model._emb_w(), head, pt, ps, labels,
                                               use_reentrant=False, preserve_rng_state=False)
                            loss = loss + ALPHA * sum(parts) / counts["kd"]
                            total.update(kd=len(sub), student_kl=parts[0].detach().item(),
                                         teacher_kl=parts[1].detach().item(), projector_ce=parts[2].detach().item())
                            del parts, selected, labels, ht
                loss.backward()
            del loss, hidden, ce, x, y, segment
        if total["ce"] != counts["ce"] or total["kd"] != (counts["kd"] if kd else 0):
            raise ValueError("The actual loss did not consume the intended supervision")
        grads = [p.grad.detach() for p in trainable if p.grad is not None]
        grad_max = torch.stack(torch._foreach_norm(grads, float("inf"))).max().item()
        norm = torch.nn.utils.clip_grad_norm_(trainable, 1., error_if_nonfinite=True).item()
        if not norm > 0 or (kd and (pt.grad is None or head.grad is not None or ps.grad is not None)):
            raise ValueError("The trainable student/projector scope must match the experiment")
        opt.step()
        torch.cuda.synchronize()
        row = dict(total, step=step, norm=norm, grad_max=grad_max, seconds=time.perf_counter()-start)
        history.append(row)
        print("DSKDV2_REAL_UPDATE", name, row, flush=True)
    peaks = dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())
    final = manual.state_fingerprint(model)
    optimizer_steps = sorted({int(state["step"].item()) for state in opt.state.values()})
    changed = int(pt.detach().cpu().ne(original_pt).sum()) if kd else 0
    frozen = not kd or torch.equal(ps.cpu(), original_ps)
    if (initial == final or optimizer_steps != [len(groups)] or not frozen
            or (kd and changed <= 0)):
        raise ValueError("Actual student/projector optimizer state or frozen inverse differs")
    return dict(initial=initial, final=final, optimizer_steps=optimizer_steps, history=history,
                training_peak=peaks, projector_cells_changed=changed, reverse_projector_frozen=frozen)


def run():
    import torch
    from scripts.diag_p107_hybrid_mntp import close_owned_cuda

    gate(180)
    profile, groups = verify()
    starting = manual.require_idle_gpu()
    if torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 10 * (1 << 30):
        raise MemoryError("One available device with 10 GiB free is required")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    arms = {}
    for name in ("ce", "dskd"):
        path = OUT / f"{name}_device_100ms.csv"
        with path.open("xb") as stream:
            sampler = subprocess.Popen((*sampling.DEVICE, f"--loop-ms={sampling.INTERVAL_MS}"), stdout=stream)
            try:
                arms[name] = train(name, profile, groups)
            finally:
                if sampler.poll() is None:
                    sampler.terminate()
                sampler.wait(timeout=8)
        samples = sampling.read_samples(path)
        arms[name].update(samples=len(samples), device_peak=max(samples, key=lambda row: row["occupied_mib"]))
        actd.native.write(OUT / (name + ".json"), arms[name])
        gc.collect()
        torch.cuda.empty_cache()
    a, b = arms.values()
    if (a["initial"] != b["initial"] or a["final"] == b["final"]
            or a["history"][0]["ce_sum"] != b["history"][0]["ce_sum"]):
        raise ValueError("The paired initial or final state did not meet the contract")
    result = dict(profile_sha256=manual.file_sha(PROFILE), arms=arms, entry_device=starting,
                  teacher_body_calls=0, checkpoint_writes=0)
    close_owned_cuda(torch, result)
    checkpoint_path = ROOT / profile["student"]["checkpoint"]["path"]
    result["source_preserved"] = (
        all(manual.file_sha(ROOT / path) == digest for path, digest in profile["source_pins"].items())
        and manual.file_sha(checkpoint_path) == profile["student"]["checkpoint"]["sha256"]
        and file_stamp(Path(profile["teacher_head"])) == profile["teacher_asset_stamp"]
    )
    if not result["source_preserved"]:
        raise ValueError("One immutable model or source differs")
    actd.native.write(OUT / "report.json", result)
    print("DSKDV2_REAL_RESULT", a["optimizer_steps"], b["optimizer_steps"], b["projector_cells_changed"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "actual"))
    phase = parser.parse_args().phase
    expected = "" if phase == "prepare" else "0"
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected:
        parser.error("Use the isolated CPU or the single authorized GPU")
    if expected and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        parser.error("Deterministic cuBLAS configuration required")
    (prepare if phase == "prepare" else run)()


if __name__ == "__main__":
    main()
