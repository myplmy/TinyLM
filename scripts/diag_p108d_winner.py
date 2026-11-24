"""Versioned affine winner capture, CPU constrained editing and native replay."""
from __future__ import annotations

import argparse
import gc
import json
import time
import traceback
import unittest
import numpy as np
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend
import tinylm

from scripts import diag_p108c_scope as io
from scripts import diag_p108b_margin as margin_owner
from scripts import p108c_limits as limits
from scripts import p108d_winner as mathematics
from scripts import p108_wsp_attention as edits
from scripts import p108_weight_space as answer_metrics
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p106b_shards import ShardWriter

BASE = io.ROOT / "test_result/evidence/p108d_winner_v2_s1337"
FAILED = io.ROOT / "test_result/evidence/p108d_winner_v1_s1337"
PROFILE = BASE / "profile.json"
INITIAL = BASE / "initial_plan.md"
CAPTURE = BASE / "capture"
SOLVE = BASE / "solve"
VALIDATE = BASE / "validate"
COMMON_BUDGET = 13.8821193483393
CODE = ("scripts/p108d_winner.py", "scripts/test_p108d_winner.py",
        "scripts/diag_p108d_winner.py", "scripts/test_p108d_native_contract.py", "scripts/p108c_limits.py",
        "scripts/p108_wsp_attention.py", "scripts/diag_p108b_margin.py",
        "scripts/p108_value_edit.py", "scripts/interactive_research_infer.py")


def source():
    parent, fits, originals, states, refs = margin_owner.source()
    packed = margin_owner.packed_inputs(fits, originals)
    baseline = io.closed_answers(io.OLD / "geometry", parent["baseline"]["answers_manifest"])
    guard = [row for row in baseline.values() if row["split"] != "select_dev"
             and row["protected"] and row["exact"]]
    dev = io.read(io.OLD / "select_dev.json")["rows"]
    protected_path = io.OLD / "target_protection_v1/protected_keys.npz"
    previous_logits = io.BASE / "margin_actual_v1/ORIGINAL_logits.npz"
    refs.update({protected_path, previous_logits, io.BASE / "margin_actual_v2/report.json",
                 io.OLD / "select_dev.json", FAILED/"profile.json", FAILED/"capture/report.json",
                 FAILED/"capture/failed_diag_p108d_winner.py"})
    if len(guard) != 7 or len(dev) != 96 or sum(len(r["targets"]) for r in packed) != 62:
        raise ValueError("same24 FIT/62 targets/7 guards/96 prior DEV required")
    return parent, fits, packed, guard, dev, baseline, refs


def prepare():
    limits.Budget(1800).check(admission=True)
    if BASE.exists():
        raise FileExistsError("preserve winner experiment namespace")
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in (
        "scripts.test_p108d_winner","scripts.test_p108d_native_contract"))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun != 9:
        raise RuntimeError("all nine independent CPU/native-window contracts required")
    import scipy
    parent, fits, packed, guard, dev, baseline, refs = source()
    BASE.mkdir()
    with INITIAL.open("xb") as stream:
        stream.write(io.PLAN.read_bytes())
    io.write_new(PROFILE, dict(schema="P108D_AFFINE_WINNER_V1", authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(), cleanup_seconds=limits.CLEANUP_SECONDS,
        model=parent["origin"]["name"], origin=parent["origin"], layer=13,
        layer_reason="CERTIFIED_AFFINE_SUFFIX_NOT_UNEXPLAINED_INDEX_SELECTION",
        code={name:io.sha(io.ROOT/name) for name in CODE},
        references={str(p.relative_to(io.ROOT)):io.sha(p) for p in sorted(refs)},
        initial_plan_sha256=io.sha(INITIAL), packed=packed,
        guard_ids=[r["id"] for r in guard], dev_ids=[r["id"] for r in dev],
        scipy_version=scipy.__version__, numpy_version=np.__version__,
        independent_CPU_contracts=result.testsRun,
        common_budget=COMMON_BUDGET, norm_rtol=2e-5, margin_original_rms_factor=.10,
        cutting_rounds=32, dual_max_iterations=5000, primal_tolerance=1e-5,
        relative_gap_tolerance=1e-5, native_maximum_logit_error=.002,
        arms=["NONE", "NORMAL7_FULL_PREFIX"], max_new=64,
        capture_max_seconds=600, solve_max_seconds=1800, validate_max_seconds=1200,
        precision="FP32_MATH_TF32_OFF", model_body_optimizer_updates=0,
        value_optimizer_updates=0, checkpoint_writes=0,
        final_or_official_used=False, prior_DEV_is_not_blind=True))
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU preparation initialized CUDA")
    print("[WINNER_PREPARED]62 canonical content/EOT positions;two protected variants;no model", flush=True)


def verify():
    profile = io.read(PROFILE)
    if (profile["authority_directive"] != 142 or profile["authority_end"] != limits.AUTHORITY_END.isoformat()
            or profile["cleanup_seconds"] != limits.CLEANUP_SECONDS
            or profile["initial_plan_sha256"] != io.sha(INITIAL)):
        raise ValueError("exact winner authority and initial plan required")
    for name, digest in {**profile["code"], **profile["references"]}.items():
        if io.sha(io.ROOT/name) != digest:
            raise ValueError("winner source changed: " + name)
    return profile


def module_and_structure(active):
    model = active["model"]
    outputs = edits.outputs(model)
    modules = [outputs["mlp:"+str(i)] for i in range(14)]
    last = model.layers[-1]
    if (active["route"].mode != "float" or model.training or model.visit_schedule() != list(range(14))
            or len({m.weight.data_ptr() for m in modules}) != 14 or
            last.has_lora or last.has_lrm or last.has_film or getattr(model, "_emb_fmt", None) is not None
            or type(model.norm_f).__name__ != "RMSNorm" or model.norm_f.state_dict()
            or model.emb_up is None):
        raise ValueError("unique R1 float last-down, pure RMS and supported linear factorized head required")
    gate = float(last.gates[1].detach())
    if not np.isfinite(gate) or gate == 0 or modules[13].weight.shape != (768, 2048):
        raise ValueError("finite nonzero native gate and exact original native shape required")
    return modules[13], gate


def canonical_head_logits(model, hidden, start, count):
    if hidden.ndim != 3 or hidden.shape[0] != 1 or hidden.shape[1] - start != count or start < 0 or count <= 0:
        raise ValueError("exact complete target suffix without prompt-head projection required")
    return model._head_logits(hidden[:, start:])


def observe(active, module, packed):
    saved = {}
    start, count = packed["start"], len(packed["targets"])

    def keys(_module, args, _output):
        if "keys" in saved:
            raise ValueError("one physical last down visit required")
        saved["keys"] = args[0][0, start:start+count].detach().cpu().numpy().copy()

    def residuals(_module, args):
        if "residuals" in saved:
            raise ValueError("one final RMS invocation required")
        saved["residuals"] = args[0][0, start:start+count].detach().cpu().numpy().copy()

    key_hook = module.register_forward_hook(keys)
    residual_hook = active["model"].norm_f.register_forward_pre_hook(residuals)
    try:
        ids = torch.tensor([packed["ids"]], device="cuda")
        hidden = active["model"](ids, return_hidden=True)
        logits = canonical_head_logits(active["model"],hidden,start,count)[0].detach().cpu().numpy().copy()
    finally:
        key_hook.remove()
        residual_hook.remove()
    if saved["keys"].shape != (count, 2048) or saved["residuals"].shape != (count, 768):
        raise ValueError("complete canonical target window required")
    return saved, logits


def start_report(directory, profile, seconds):
    limits.Budget(seconds).check(admission=True)
    if directory.exists():
        raise FileExistsError("preserve previous phase: " + str(directory))
    directory.mkdir()
    return dict(schema=profile["schema"], status="STARTED", source_profile_sha256=io.sha(PROFILE),
                optimizer_updates=0, value_optimizer_updates=0, checkpoint_writes=0,
                final_or_official_used=False)


def capture():
    profile = verify()
    report = start_report(CAPTURE, profile, profile["capture_max_seconds"])
    budget = limits.Budget(profile["capture_max_seconds"])
    report["entry_resources"] = cleanup_owner.resources()
    started = time.monotonic()
    active = module = model = None
    failure = None
    try:
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        with manual.selected_runtime(manual.resolve_model(profile["model"])) as active:
            try:
                model = active["model"]
                if manual.state_fingerprint(model) != profile["origin"]["core_sha256"]:
                    raise ValueError("original full core differs")
                module, gate = module_and_structure(active)
                keys, residuals, logits, gold = [], [], [], []
                with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
                    for row in profile["packed"]:
                        budget.check()
                        observed, raw = observe(active, module, row)
                        keys.append(observed["keys"])
                        residuals.append(observed["residuals"])
                        logits.append(raw)
                        gold.extend(row["targets"])
                    embedding = model._emb_w().detach().cpu().double().numpy()
                    up = model._emb_up_w().detach().cpu().double().numpy()
                    scale = model.norm_f_scale.detach().cpu().double().numpy()
                    head = ((embedding @ up.T) * scale).astype(np.float32)
                features = np.concatenate(keys)
                raw_residuals = np.concatenate(residuals)
                native_logits = np.concatenate(logits)
                previous = io.load_arrays(io.BASE/"margin_actual_v1/ORIGINAL_logits.npz")["logits"]
                if not np.array_equal(native_logits, previous):
                    raise RuntimeError("same62 complete native original logits required")
                rms = np.sqrt(np.mean(raw_residuals.astype(np.float64)**2, axis=1) + model.norm_f.eps)
                predicted = (raw_residuals.astype(np.float64) @ head.astype(np.float64).T) / rms[:, None]
                mismatch = int(np.sum(predicted.argmax(axis=1) != native_logits.argmax(axis=1)))
                error = float(np.max(np.abs(predicted - native_logits)))
                if mismatch or error > profile["native_maximum_logit_error"]:
                    raise RuntimeError("affine original winner/logit certificate failed")
                protected = io.load_arrays(io.OLD/"target_protection_v1/protected_keys.npz")["keys"]
                if protected.shape != (239, 2048):
                    raise ValueError("exact prior full-prefix normal7 key matrix required")
                report["features"] = io.save_arrays(CAPTURE/"features.npz", keys=features,
                    residuals=raw_residuals, gold=np.asarray(gold, dtype=np.int64), original_rms=rms,
                    original_before=module.weight.detach().cpu().numpy().copy(), protected_keys=protected)
                head_packets = []
                for start in range(0, len(head), 4096):
                    head_packets.append(io.save_arrays(CAPTURE/f"head_{start:05d}.npz", head=head[start:start+4096]))
                report.update(status="AFFINE_NATIVE_CAPTURE_COMPLETE", gate=gate, norm_eps=model.norm_f.eps,
                    head_packets=head_packets, head_shape=list(head.shape), model_forwards=24,
                    target_positions=62, original_logits_bitexact=True, original_argmax_mismatches=mismatch,
                    original_head_max_logit_error=error, original_core_unchanged=True,
                    derived_head_coefficients_are_not_a_model_checkpoint=True,
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                if manual.state_fingerprint(model) != profile["origin"]["core_sha256"]:
                    raise RuntimeError("capture changed the model")
                module = model = None
            finally:
                module = model = None
        active = None
    except BaseException as error:
        failure = str(error)
        report.update(status="AFFINE_NATIVE_CAPTURE_ERROR", error=failure, traceback=traceback.format_exc())
        error.__traceback__ = None
    finally:
        active = module = model = None
        gc.collect()
        cleanup_error = cleanup_owner.cleanup(report)
        if cleanup_error is not None:
            failure = failure or str(cleanup_error)
            report.update(status="AFFINE_NATIVE_CAPTURE_CLEANUP_ERROR", error=failure)
        report["wall_seconds"] = time.monotonic() - started
        io.write_new(CAPTURE/"report.json", report)
        print("[WINNER_CAPTURE_END]"+json.dumps({k:report.get(k) for k in (
            "status", "target_positions", "original_head_max_logit_error", "wall_seconds",
            "cuda_allocated_after_bytes", "cuda_reserved_after_bytes", "error")}), flush=True)
    if failure is not None:
        raise RuntimeError("preserved affine capture failure: " + failure)


def captured():
    report = io.read(CAPTURE/"report.json")
    if (report["status"] != "AFFINE_NATIVE_CAPTURE_COMPLETE" or
            report["cuda_allocated_after_bytes"] or report["cuda_reserved_after_bytes"]):
        raise ValueError("closed native capture and cleanup required")
    for packet in [report["features"], *report["head_packets"]]:
        if io.sha(io.ROOT/packet["path"]) != packet["sha256"]:
            raise ValueError("original affine artifact changed")
    arrays = io.load_arrays(io.ROOT/report["features"]["path"])
    head = np.concatenate([io.load_arrays(io.ROOT/p["path"])["head"] for p in report["head_packets"]])
    return report, arrays, head


def solve():
    profile = verify()
    report = start_report(SOLVE, profile, profile["solve_max_seconds"])
    budget = limits.Budget(profile["solve_max_seconds"])
    started = time.monotonic()
    capture_report, arrays, head = captured()
    margins = arrays["original_rms"] * profile["margin_original_rms_factor"]
    arms = []
    for name in profile["arms"]:
        budget.check()
        protected = None if name == "NONE" else arrays["protected_keys"]
        directory = SOLVE/name
        directory.mkdir()
        requested, result = mathematics.solve_winners(head, arrays["residuals"], arrays["keys"],
            arrays["gold"], capture_report["gate"], margins, protected=protected,
            rounds=profile["cutting_rounds"], max_iter=profile["dual_max_iterations"],
            tolerance=profile["primal_tolerance"], check=budget.check)
        result_pin = io.write_new(directory/"solver.json", result)
        variants = [(name+"_MINIMUM", requested)]
        if np.linalg.norm(requested) > COMMON_BUDGET * (1 + profile["norm_rtol"]):
            variants.append((name+"_BUDGET", requested * (COMMON_BUDGET/np.linalg.norm(requested))))
        for variant, delta in variants:
            after, actual, physical = mathematics.materialize(arrays["original_before"], delta, budget=COMMON_BUDGET)
            raw_scores = (arrays["residuals"] + capture_report["gate"]*(arrays["keys"] @ actual.T)) @ head.T
            achieved, rivals = mathematics.winner_margins(raw_scores, arrays["gold"])
            rms_after = np.sqrt(np.mean((arrays["residuals"] + capture_report["gate"]*
                                         (arrays["keys"] @ actual.T))**2, axis=1) + capture_report["norm_eps"])
            physical.update(predicted_argmax_correct=int(np.sum(raw_scores.argmax(axis=1)==arrays["gold"])),
                maximum_raw_violation=float((margins-achieved).max()),
                protected_output_norm=(None if protected is None else float(np.linalg.norm(actual @ protected.T))))
            packet = io.save_arrays(directory/(variant+"_packet.npz"), before=arrays["original_before"], after=after)
            prediction = io.save_arrays(directory/(variant+"_prediction.npz"),
                actual_delta=actual.astype(np.float32), margins=achieved, predicted_winners=raw_scores.argmax(axis=1),
                predicted_rms=rms_after)
            entry = dict(name=variant, protection=name, physical=physical, packet=packet,
                         predictions=prediction, solver=result_pin,
                         solver_status=result["status"], source_data_role="EDIT_FIT_ONLY")
            io.write_new(directory/(variant+"_physical.json"), entry)
            arms.append(entry)
        print("[WINNER_QP_ARM]"+json.dumps(dict(name=name,status=result["status"],norm=result["norm"],
              constraints=result["constraint_count"],violation=result["maximum_raw_violation"],
              wall_seconds=result["wall_seconds"])),flush=True)
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU QP initialized CUDA")
    report.update(status="WINNER_CPU_SOLVE_COMPLETE", arms=arms, model_forwards=0, new_generations=0,
                  capture_report_sha256=io.sha(CAPTURE/"report.json"), wall_seconds=time.monotonic()-started)
    io.write_new(SOLVE/"report.json", report)
    print("[WINNER_QP_END]"+json.dumps(dict(status=report["status"],arms=len(arms),
          wall_seconds=report["wall_seconds"])),flush=True)


def validate():
    profile = verify()
    report = start_report(VALIDATE, profile, profile["validate_max_seconds"])
    budget = limits.Budget(profile["validate_max_seconds"])
    started = time.monotonic()
    solve_report = io.read(SOLVE/"report.json")
    if solve_report["status"] != "WINNER_CPU_SOLVE_COMPLETE" or len(solve_report["arms"]) > 4:
        raise ValueError("closed prespecified CPU arms required")
    _, fits, packed, guards, dev, baseline, refs = source()
    capture_report, arrays, head = captured()
    report["entry_resources"] = cleanup_owner.resources()
    report["arms"] = []
    active = model = module = delta_native = None
    failure = None
    try:
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        with manual.selected_runtime(manual.resolve_model(profile["model"])) as active:
            try:
                model = active["model"]
                module, gate = module_and_structure(active)
                if manual.state_fingerprint(model) != profile["origin"]["core_sha256"]:
                    raise ValueError("native original core differs")
                canary = fits[0]
                answer, generation = manual.emit(active, canary["question"], max_new=profile["max_new"])
                if generation["generated_ids"] != baseline[canary["id"]]["generation"]["generated_ids"]:
                    raise ValueError("original full greedy answer canary differs")
                report["original_generation_canary_exact"] = True
                report["baseline_answers_reused"] = len(fits)+len(dev)+len(guards)
                for arm in solve_report["arms"]:
                    budget.check()
                    directory = VALIDATE/arm["name"]
                    directory.mkdir()
                    if io.sha(io.ROOT/arm["packet"]["path"]) != arm["packet"]["sha256"]:
                        raise ValueError("CPU physical packet changed")
                    packet = io.load_arrays(io.ROOT/arm["packet"]["path"])
                    if not np.array_equal(packet["before"], module.weight.detach().cpu().numpy()):
                        raise ValueError("packet original differs from native matrix")
                    delta_native = torch.from_numpy(packet["after"]-packet["before"]).to(module.weight)
                    writer = ShardWriter(directory, "answers", limit=2_000_000)
                    cells, offset, maximum_error, mismatch = [], 0, 0., 0
                    with edits.edit(model, active["route"], [("mlp:13",delta_native)]) as proof:
                        physical = module.weight.detach().cpu().double().numpy()-packet["before"].astype(np.float64)
                        with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
                            for row in packed:
                                budget.check()
                                saved, native = observe(active, module, row)
                                count = len(row["targets"])
                                original_keys = arrays["keys"][offset:offset+count]
                                if not np.array_equal(saved["keys"],original_keys):
                                    raise ValueError("last down edit changed its own canonical prefix key")
                                residual = arrays["residuals"][offset:offset+count]+gate*(original_keys@physical.T)
                                rms = np.sqrt(np.mean(residual**2,axis=1)+capture_report["norm_eps"])
                                predicted = residual@head.T/rms[:,None]
                                maximum_error = max(maximum_error,float(np.max(np.abs(predicted-native))))
                                mismatch += int(np.sum(predicted.argmax(axis=1)!=native.argmax(axis=1)))
                                target = np.asarray(row["targets"])
                                gold_scores = native[np.arange(count),target]
                                other = native.copy();other[np.arange(count),target]=-np.inf
                                cells.append(dict(id=row["id"],content_argmax_correct=int(np.sum(native[:-1].argmax(axis=1)==target[:-1])),
                                    content_positions=count-1,eot_argmax_correct=bool(native[-1].argmax()==target[-1]),
                                    all_argmax_correct=bool(np.all(native.argmax(axis=1)==target)),
                                    minimum_native_gold_margin=float(np.min(gold_scores-other.max(axis=1)))))
                                io.save_arrays(directory/("tf_"+str(offset).zfill(3)+".npz"),native_logits=native,
                                               predicted_logits=predicted.astype(np.float32))
                                offset += count
                            if mismatch or maximum_error > profile["native_maximum_logit_error"]:
                                raise RuntimeError("predicted/native winner or logit gate failed")
                            for row in fits+dev+guards:
                                budget.check()
                                answer,generation=manual.emit(active,row["question"],max_new=profile["max_new"])
                                tail=len(generation["terminal_ids"])
                                ids=generation["generated_ids"][:-tail] if tail else generation["generated_ids"]
                                writer.append(dict(row,variant=arm["name"],answer=answer,generation=generation,
                                    exact=answer_metrics.exact_answer(answer,row["expected"]),
                                    diagnostics=answer_metrics.repetition_metrics(ids,answer,row["question"]),
                                    baseline_answer=baseline[row["id"]]["answer"],
                                    baseline_exact=baseline[row["id"]]["exact"]))
                    manifest=writer.close(lineage=dict(source_profile_sha256=io.sha(PROFILE),
                        packet_sha256=arm["packet"]["sha256"],FIT_used_for_edit=True,DEV_previously_exposed=True))
                    observed=io.closed_answers(directory,manifest)
                    summaries={}
                    for split,rows in (("FIT",fits),("DEV",dev),("GUARD",guards)):
                        summaries[split]=dict(rows=len(rows),exact=sum(observed[r["id"]]["exact"] for r in rows),
                            baseline_exact=sum(bool(baseline[r["id"]]["exact"]) for r in rows),
                            corrected=sum(not baseline[r["id"]]["exact"] and observed[r["id"]]["exact"] for r in rows),
                            harmed=sum(baseline[r["id"]]["exact"] and not observed[r["id"]]["exact"] for r in rows))
                    row_report=dict(name=arm["name"],physical=arm["physical"],weight_replay=proof,
                        actual_physical_norm=float(np.linalg.norm(physical)),native_logit_max_error=maximum_error,
                        predicted_native_argmax_mismatches=mismatch,teacher_forcing=cells,summaries=summaries,
                        answers_manifest=manifest)
                    io.write_new(directory/"report.json",row_report)
                    report["arms"].append(row_report)
                    delta_native=None
                    print("[WINNER_NATIVE_ARM]"+json.dumps(dict(name=arm["name"],summaries=summaries,
                        maximum_error=maximum_error,mismatch=mismatch)),flush=True)
                if manual.state_fingerprint(model)!=profile["origin"]["core_sha256"]:
                    raise RuntimeError("native model core not restored")
                report.update(status="WINNER_NATIVE_VALIDATION_COMPLETE",original_core_restored=True,
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                module=model=None
            finally:
                module=model=None
        active=None
    except BaseException as error:
        failure=str(error)
        report.update(status="WINNER_NATIVE_VALIDATION_ERROR",error=failure,traceback=traceback.format_exc())
        error.__traceback__=None
    finally:
        active=model=module=delta_native=None
        gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:
            failure=failure or str(cleanup_error)
            report.update(status="WINNER_NATIVE_CLEANUP_ERROR",error=failure)
        report["wall_seconds"]=time.monotonic()-started
        io.write_new(VALIDATE/"report.json",report)
        print("[WINNER_VALIDATE_END]"+json.dumps({k:report.get(k) for k in (
            "status","wall_seconds","cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}),flush=True)
    if failure is not None:
        raise RuntimeError("preserved winner validation failure: "+failure)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("preflight","prepare","check","capture","solve","validate"))
    phase=parser.parse_args().phase
    if phase=="preflight":
        limits.Budget(1800).check(admission=True)
        import scipy
        source()
        if torch.cuda.is_initialized():raise RuntimeError("preflight initialized CUDA")
        print("[WINNER_PREFLIGHT]closed sources and existing scipy="+scipy.__version__+";model0",flush=True)
    elif phase=="prepare":prepare()
    elif phase=="check":verify();print("[WINNER_CHECK]immutable source/authority;model0",flush=True)
    elif phase=="capture":capture()
    elif phase=="solve":
        try:solve()
        except BaseException as error:
            if SOLVE.exists() and not (SOLVE/"report.json").exists():
                io.write_new(SOLVE/"report.json",dict(status="WINNER_CPU_SOLVE_ERROR",
                    error=str(error),traceback=traceback.format_exc(),optimizer_updates=0,
                    checkpoint_writes=0,new_generations=0,CUDA_initialized=torch.cuda.is_initialized()))
            raise
    else:validate()


if __name__=="__main__":main()
