"""Replay completed14 packets and observe content/EOT versus first-token margin."""
import argparse
import gc
import hashlib
import json
import time
import traceback
import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel, SDPBackend
import tinylm

from scripts import diag_p108c_scope as io
from scripts import p108c_limits as limits
from scripts import p108b_margin as metrics
from scripts import p108b_forecast_cv as ranking
from scripts import p108_value_edit as values
from scripts import p108_wsp_attention as edits
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner

PROFILE = io.BASE / "margin_profile_v2.json"
INITIAL = io.BASE / "margin_initial_plan_v2.md"
OUT = io.BASE / "margin_actual_v2"
PREVIOUS = io.BASE / "margin_actual_v1"
CODE = ("scripts/diag_p108b_margin.py", "scripts/p108b_margin.py",
        "scripts/test_p108b_margin.py", "scripts/p108b_forecast_cv.py",
        "scripts/p108_value_edit.py", "scripts/p108_wsp_attention.py",
        "scripts/interactive_research_infer.py", "scripts/p108c_limits.py")


def source():
    parent = io.read(io.OLD / "geometry/report.json")
    data = io.read(io.OLD / "data.json")
    fits = [r for r in data["rows"] if r["split"] == "fit"]
    if len(fits) != 24 or len(parent["layers"]) != 14 or not parent["registered_core_unchanged"]:
        raise ValueError("closed24 FIT and14 original-parent states required")
    originals = io.closed_answers(io.OLD / "geometry", parent["baseline"]["answers_manifest"])
    refs = {io.OLD / "geometry/report.json", io.OLD / "data.json"}
    refs.update(io.OLD / "geometry" / s["path"] for s in parent["baseline"]["answers_manifest"]["shards"])
    states = []
    for layer in range(14):
        directory = io.OLD / "geometry" / f"layer{layer:02d}"
        report_path = directory / "report.json"
        report = io.read(report_path)
        if report["layer"] != layer or report["status"] != "GLOBAL_SINGLE_LAYER_ACTUAL_COMPLETE":
            raise ValueError("completed single-layer source required")
        packet_path = io.ROOT / report["packet"]["path"]
        if io.sha(packet_path) != report["packet"]["sha256"]:
            raise ValueError("closed physical packet changed")
        cached = io.closed_answers(directory, report["answers_manifest"])
        states.append(dict(layer=layer, report=report, answers=cached))
        refs.update({report_path, packet_path})
        refs.update(directory / s["path"] for s in report["answers_manifest"]["shards"])
    return parent, fits, originals, states, refs


def packed_inputs(fits, originals):
    from tinylm.chat.serialize import serialize
    tokenizer = manual.local_tokenizer(manual.verify_manifest())
    result = []
    for row in fits:
        text = serialize(dict(messages=manual.prompt_messages(row["question"])), "chatml", add_generation_prompt=True)
        prompt = tokenizer.encode(text).ids
        answer = tokenizer.encode(row["expected"]).ids
        ids, targets, start = values.target_window(prompt, answer)
        cached = originals[row["id"]]["generation"]
        prompt_sha = hashlib.sha256(text.encode()).hexdigest().upper()
        if len(ids) > 1024 or len(prompt) != cached["prompt_tokens"] or prompt_sha != cached["prompt_sha256"]:
            raise ValueError("same complete serialized input as the cached native answer required")
        if not answer or any(token in (2, 4) for token in answer):
            raise ValueError("canonical content without embedded terminal required")
        result.append(dict(row, ids=ids, targets=targets, start=start, prompt_sha256=prompt_sha))
    return result


def prepare():
    limits.Budget(900).check(admission=True)
    if PROFILE.exists() or INITIAL.exists():
        raise FileExistsError("preserve margin admission")
    parent, fits, originals, states, refs = source()
    packed = packed_inputs(fits, originals)
    recovered = io.read(PREVIOUS / "cache_recovery_receipt.json")
    if recovered["original_first_id_mismatches"] or recovered["recovered_margin_VJP_projections"]:
        raise ValueError("closed original cache and explicitly missing derivative projections required")
    refs.update({PREVIOUS / "report.json", PREVIOUS / "ORIGINAL_logits.npz",
                 PREVIOUS / "cache_recovery_receipt.json", PREVIOUS / "failed_diag_p108b_margin.py"})
    target_positions = sum(len(r["targets"]) for r in packed)
    if target_positions != 62 or target_positions * 32768 * 4 >= 20_000_000:
        raise ValueError("closed62 positions and each complete FP32 state under20MB required")
    with INITIAL.open("xb") as stream:
        stream.write(io.PLAN.read_bytes())
    io.write_new(PROFILE, dict(schema="P108B_CONTENT_EOT_MARGIN_V1", authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(), cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=900, model=parent["origin"]["name"], origin=parent["origin"],
        sources={name:io.sha(io.ROOT/name) for name in CODE},
        references={str(path.relative_to(io.ROOT)):io.sha(path) for path in sorted(refs)},
        initial_plan_sha256=io.sha(INITIAL), packed=packed, target_positions=62,
        expected_model_forwards=360, expected_margin_vjps=24,
        precision="FP32_MATH_TF32_OFF", projection="ACTUAL_PHYSICAL_DELTA_CPU_FP64_ACCUMULATION",
        first_id_contract="ALL360_TF_FIRST_ARGMAX_VS_CACHED_NATIVE_FIRST_ID",
        first_id_mismatch_is_technical_negative=True, new_generations=0,
        body_optimizer_updates=0, value_optimizer_updates=0, checkpoint_writes=0,
        recovery_of="margin_v1", original_logits_reuse_if_bitexact=True,
        required_new_derivatives_because_original_projections_not_saved=True,
        persist_baseline_and_each_completed_layer=True,
        final_or_official_used=False, data_role="REUSED_EDIT_FIT_NOT_NEW_QUALITY_TEST"))
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU preparation initialized CUDA")
    print("[MARGIN_PREPARED]24 FIT/14 frozen packets;360 forwards/24 VJP;new generations0", flush=True)


def verify():
    limits.Budget(900).check()
    profile = io.read(PROFILE)
    if (profile["authority_directive"] != 142 or profile["authority_end"] != limits.AUTHORITY_END.isoformat()
            or profile["cleanup_seconds"] != limits.CLEANUP_SECONDS
            or profile["sources"] != {name:io.sha(io.ROOT/name) for name in CODE}
            or profile["initial_plan_sha256"] != io.sha(INITIAL)):
        raise ValueError("exact margin source/current authority/initial plan required")
    for name, expected in profile["references"].items():
        if io.sha(io.ROOT/name) != expected:
            raise ValueError("frozen margin input changed: " + name)
    return profile


def actual():
    profile = verify()
    budget = limits.Budget(profile["max_seconds"])
    budget.check(admission=True)
    entry = cleanup_owner.resources()
    if OUT.exists():
        raise FileExistsError("preserve previous margin diagnostic")
    OUT.mkdir()
    started = time.monotonic()
    report = dict(schema=profile["schema"], status="STARTED", source_profile_sha256=io.sha(PROFILE),
        entry_resources=entry, optimizer_updates=0, value_optimizer_updates=0,
        new_generations=0, checkpoint_writes=0, final_or_official_used=False)
    active = model = module = weights = direction = gradients = logits = hidden = None
    ids = target = objective = requested_native = None
    modules = {}
    counter_handle = None
    failure = None
    try:
        parent, fits, originals, states, refs = source()
        torch.set_num_threads(4)
        with manual.selected_runtime(manual.resolve_model(profile["model"])) as active:
            try:
                model = active["model"]
                if manual.state_fingerprint(model) != profile["origin"]["core_sha256"]:
                    raise ValueError("exact original core required")
                modules = {int(k.split(":")[1]):v for k,v in edits.outputs(model).items() if k.startswith("mlp:")}
                if sorted(modules) != list(range(14)) or active["route"].mode != "float":
                    raise ValueError("complete14 unique R1 float down matrices required")
                weights = [modules[i].weight for i in range(14)]
                packets = [io.load_arrays(io.ROOT/s["report"]["packet"]["path"]) for s in states]
                physical_deltas = []
                for layer, packet in enumerate(packets):
                    original = modules[layer].weight.detach().cpu()
                    requested = torch.from_numpy(packet["requested"])
                    after = torch.from_numpy(packet["after"])
                    if not torch.equal(original + requested, after):
                        raise ValueError("packet does not reproduce original-parent write")
                    physical_deltas.append(after.double() - original.double())
                forwards = [0]
                def count(_module, _args):
                    forwards[0] += 1
                    report["model_forwards"] = forwards[0]
                counter_handle = model.register_forward_pre_hook(count)
                baseline = {}
                projections = {}
                first_mismatches = []
                packets_written = []
                baseline_arrays = []
                metadata = []
                offset = 0
                torch.cuda.reset_peak_memory_stats()
                report["margin_vjps"] = 0
                report["completed_layers"] = []
                with sdpa_kernel(SDPBackend.MATH), torch.autocast("cuda", enabled=False), values.freeze_parameters(model):
                    for row in profile["packed"]:
                        budget.check()
                        ids = torch.tensor([row["ids"]], device="cuda")
                        target = torch.tensor(row["targets"], device="cuda")
                        values.refresh_autograd_views(model, active["route"])
                        with torch.enable_grad():
                            hidden = model(ids, return_hidden=True)
                            logits = model._head_logits(hidden[:, row["start"]:])[0]
                            raw = logits.detach().cpu().numpy().copy()
                            stats = metrics.summarize(torch.from_numpy(raw), target.cpu())
                            objective = logits[0, stats["first_gold"]] - logits[0, stats["reference_competitor"]]
                            gradients = torch.autograd.grad(objective, weights)
                            projections[row["id"]] = [metrics.directional_projection(g, d) for g,d in zip(gradients, physical_deltas)]
                            report["margin_vjps"] += 1
                            with torch.no_grad():
                                stats["native_mean_ce"] = float(F.cross_entropy(logits, target))
                        source_first = originals[row["id"]]["generation"]["generated_ids"][0]
                        if stats["first_argmax"] != source_first:
                            first_mismatches.append(dict(state="ORIGINAL", id=row["id"], native=stats["first_argmax"], cached=source_first))
                        baseline[row["id"]] = stats
                        baseline_arrays.append(raw)
                        metadata.append(dict(id=row["id"], start=offset, end=offset+len(target), targets=row["targets"]))
                        offset += len(target)
                        gradients = logits = hidden = ids = target = objective = None
                    new_baseline = np.concatenate(baseline_arrays)
                    old_baseline = io.load_arrays(PREVIOUS / "ORIGINAL_logits.npz")["logits"]
                    report["previous_baseline_max_difference"] = float(np.abs(new_baseline.astype(float)-old_baseline.astype(float)).max())
                    if np.array_equal(new_baseline, old_baseline):
                        old_path = PREVIOUS / "ORIGINAL_logits.npz"
                        packets_written.append(dict(path=str(old_path.relative_to(io.ROOT)),
                            sha256=io.sha(old_path), bytes=old_path.stat().st_size, reused_exact=True))
                    else:
                        packets_written.append(io.save_arrays(OUT/"ORIGINAL_logits.npz", logits=new_baseline))
                    io.write_new(OUT / "baseline.json", dict(stats=baseline, projections=projections,
                        offsets=metadata, original_logits=packets_written[0],
                        previous_baseline_max_difference=report["previous_baseline_max_difference"]))
                    cells = []
                    for layer, state in enumerate(states):
                        budget.check()
                        arrays = []
                        requested = torch.from_numpy(packets[layer]["requested"])
                        module = modules[layer]
                        requested_native = requested.to(module.weight)
                        with edits.edit(model, active["route"], [("mlp:"+str(layer), requested_native)]):
                            if not torch.equal(module.weight.detach().cpu(), torch.from_numpy(packets[layer]["after"])):
                                raise ValueError("actual layer replay differs from source after")
                            if manual.state_fingerprint(model) != state["report"]["after_core_sha256"]:
                                raise ValueError("actual replay complete core differs from old global state")
                            with torch.no_grad():
                                for row in profile["packed"]:
                                    budget.check()
                                    ids = torch.tensor([row["ids"]], device="cuda")
                                    target = torch.tensor(row["targets"], device="cuda")
                                    hidden = model(ids, return_hidden=True)
                                    logits = model._head_logits(hidden[:, row["start"]:])[0]
                                    raw = logits.cpu().numpy().copy()
                                    before = baseline[row["id"]]
                                    stats = metrics.summarize(torch.from_numpy(raw), target.cpu(), reference_competitor=before["reference_competitor"])
                                    stats["native_mean_ce"] = float(F.cross_entropy(logits, target))
                                    cached = state["answers"][row["id"]]
                                    source_first = cached["generation"]["generated_ids"][0]
                                    if stats["first_argmax"] != source_first:
                                        first_mismatches.append(dict(state=layer, id=row["id"], native=stats["first_argmax"], cached=source_first))
                                    prediction = projections[row["id"]][layer]
                                    cells.append(dict(layer=layer, id=row["id"], stats=stats,
                                        source_first_id=source_first, cached_full_answer_exact=cached["exact"],
                                        predicted_margin_gain=prediction,
                                        predicted_after_reference_margin=before["reference_margin"]+prediction,
                                        actual_reference_margin_gain=stats["reference_margin"]-before["reference_margin"],
                                        actual_true_margin_gain=stats["true_margin"]-before["true_margin"],
                                        competitor_gap=stats["reference_margin"]-stats["true_margin"],
                                        competitor_switched=stats["first_competitor"] != before["reference_competitor"],
                                        content_ce_contribution_gain=before["content_contribution"]-stats["content_contribution"],
                                        eot_ce_contribution_gain=before["eot_contribution"]-stats["eot_contribution"],
                                        ce_gain=before["mean_ce"]-stats["mean_ce"],
                                        old_predicted_ce_gain=parent["baseline"]["objective"]["predicted_fit_gain_by_id"][row["id"]][str(layer)],
                                        source_mean_ce_difference=stats["native_mean_ce"]-state["report"]["objective"]["fit_ce_by_id"][row["id"]]))
                                    arrays.append(raw)
                                    logits = hidden = ids = target = None
                            packets_written.append(io.save_arrays(OUT/f"layer{layer:02d}_logits.npz", logits=np.concatenate(arrays)))
                            io.write_new(OUT / f"layer{layer:02d}_metrics.json",
                                dict(layer=layer, cells=[c for c in cells if c["layer"] == layer],
                                     logits_packet=packets_written[-1]))
                        requested_native = None
                        report["completed_layers"].append(layer)
                        print("[MARGIN_PROGRESS]layer="+str(layer), flush=True)
                io.write_new(OUT/"case_metrics.json", dict(baseline=baseline, cells=cells, offsets=metadata, projections=projections))
                target_correct = np.array([c["stats"]["first_argmax"] == c["stats"]["first_gold"] for c in cells])
                predicted_positive = np.array([c["predicted_after_reference_margin"] > 0 for c in cells])
                reference_error = np.array([c["predicted_margin_gain"]-c["actual_reference_margin_gain"] for c in cells])
                true_error = np.array([c["predicted_margin_gain"]-c["actual_true_margin_gain"] for c in cells])
                if forwards[0] != 360 or len(cells) != 336:
                    raise RuntimeError("complete declared observation count differs")
                report.update(status="MARGIN_OBSERVATION_COMPLETE" if not first_mismatches else "FIRST_PATH_NUMERICAL_NEGATIVE",
                    model_forwards=forwards[0], margin_vjps=24, cells=336,
                    first_argmax_cache_mismatches=first_mismatches, logits_packets=packets_written,
                    canonical_first_correct=int(target_correct.sum()), cached_full_answer_correct=sum(c["cached_full_answer_exact"] for c in cells),
                    reference_margin_gain_rmse=float(np.sqrt(np.mean(reference_error**2))),
                    true_margin_gain_rmse=float(np.sqrt(np.mean(true_error**2))),
                    predicted_positive_confusion=dict(tp=int((predicted_positive & target_correct).sum()),
                        fp=int((predicted_positive & ~target_correct).sum()), fn=int((~predicted_positive & target_correct).sum()),
                        tn=int((~predicted_positive & ~target_correct).sum())),
                    forecast_margin_first_correct_auc=ranking.auc([c["predicted_after_reference_margin"] for c in cells], target_correct),
                    ce_gain_first_correct_auc=ranking.auc([c["old_predicted_ce_gain"] for c in cells], target_correct),
                    competitor_switched=sum(c["competitor_switched"] for c in cells),
                    mean_content_ce_contribution_gain=float(np.mean([c["content_ce_contribution_gain"] for c in cells])),
                    mean_eot_ce_contribution_gain=float(np.mean([c["eot_ce_contribution_gain"] for c in cells])),
                    source_mean_ce_max_difference=max(abs(c["source_mean_ce_difference"]) for c in cells),
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                    peak_scope="POST_LOAD_THROUGH_VJP_AND_REPLAY_ONLY")
                if manual.state_fingerprint(model) != profile["origin"]["core_sha256"]:
                    raise RuntimeError("original complete core not restored")
                report["original_core_restored"] = True
            finally:
                if counter_handle is not None:
                    counter_handle.remove()
                modules.clear()
                weights = gradients = logits = hidden = module = model = None
                ids = target = objective = requested_native = None
        active = None
    except BaseException as error:
        failure = str(error)
        report.update(status="MARGIN_OBSERVATION_ERROR", error=failure, traceback=traceback.format_exc())
        error.__traceback__ = None
    finally:
        active = model = module = weights = direction = gradients = logits = hidden = None
        ids = target = objective = requested_native = None
        modules.clear()
        gc.collect()
        cleanup_error = cleanup_owner.cleanup(report)
        if cleanup_error is not None and failure is None:
            failure = str(cleanup_error)
        report["wall_seconds"] = time.monotonic()-started
        io.write_new(OUT/"report.json", report)
        print("[MARGIN_END]"+json.dumps({k:report.get(k) for k in ("status","model_forwards","margin_vjps","canonical_first_correct","cached_full_answer_correct","wall_seconds","cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}), flush=True)
    if failure is not None:
        raise RuntimeError("preserved margin observation failure: "+failure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "check", "actual"))
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
    elif phase == "check":
        verify()
        print("[MARGIN_CHECK]exact closed packets/inputs/current authority;model0", flush=True)
    else:
        actual()


if __name__ == "__main__":
    main()
