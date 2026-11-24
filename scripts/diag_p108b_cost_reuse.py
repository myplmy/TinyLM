"""CPU physical/cost accounting from completed policies; never runs a model."""
import argparse
import gc
import hashlib
import json
import math
import time
from pathlib import Path
import numpy as np
import torch
import tinylm
from scripts import diag_p108c_scope as io
from scripts import p108c_limits as limits
from scripts import interactive_research_infer as manual

ROOT = io.ROOT
OLD = io.OLD
POLICIES = OLD/"policies_v1"
OUT = ROOT/"handoff/audit/nov16_night_p108c/p108b_cost_reuse_v3"
CODE = ("scripts/diag_p108b_cost_reuse.py", "scripts/test_p108b_cost_reuse.py",
        "scripts/p108c_limits.py", "scripts/interactive_research_infer.py")


def digest(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest().upper()


def checkpoint_keys(cfg, state_names):
    # The constructor owns parameters in root ModuleLists; logical layers keep references.
    required = dict(n_prelude=2, n_middle=10, n_coda=2,
                    dim=768, ffn_dim=2048, tie_mlp=False)
    if (any(cfg.get(k) != v for k,v in required.items()) or
            sum(cfg[k] for k in ("n_prelude", "n_middle", "n_coda")) != 14):
        raise ValueError("exact completed nonshared14-layer cfg required")
    names = ([f"pre_mlps.{i}.down_proj.weight"for i in range(2)] +
             [f"mid_mlps.{i}.down_proj.weight"for i in range(10)] +
             [f"coda_mlps.{i}.down_proj.weight"for i in range(2)])
    observed = {k for k in state_names if k.endswith("down_proj.weight")}
    if set(names) != observed:
        raise ValueError("native root ownership names differ; no guessed logical layer key")
    return names


def physical_trace(originals, steps):
    current = {}; touched = {}; path = 0.; attempts = 0; rounds = []
    for layer, requested, after in steps:
        original = np.asarray(originals[layer])
        before = current.get(layer, original)
        if (before.dtype != np.float32 or requested.dtype != np.float32 or after.dtype != np.float32
                or before.shape != requested.shape or before.shape != after.shape
                or before.ndim != 2 or not np.isfinite(after).all()
                or not np.array_equal(before+requested, after)):
            raise ValueError("exact finite same-shape FP32 native write required")
        step = after.astype(np.float64)-before.astype(np.float64)
        mask = step != 0
        touched[layer] = touched.get(layer, np.zeros_like(mask)) | mask
        attempts += int(mask.sum()); length = float(np.linalg.norm(step))
        path += length; current[layer] = after.copy()
        delta = {i:w.astype(np.float64)-originals[i].astype(np.float64)for i,w in current.items()}
        norm = math.sqrt(sum(float(np.square(d).sum())for d in delta.values()))
        rounds.append(dict(layer=layer, before_sha256=digest(before), after_sha256=digest(after),
            actual_step_norm=length, cumulative_net=norm, cumulative_path=path,
            step_changed_entries=int(mask.sum())))
    delta = {i:w.astype(np.float64)-originals[i].astype(np.float64)for i,w in current.items()}
    final = dict(net_norm=math.sqrt(sum(float(np.square(d).sum())for d in delta.values())),
        path_norm=path, changed_entries=sum(int((d != 0).sum())for d in delta.values()),
        ever_changed_entries=sum(int(m.sum())for m in touched.values()),
        sum_step_changed_entries=attempts, net_layer_norms={str(i):float(np.linalg.norm(d))for i,d in delta.items()},
        unique_layers=sorted(i for i,d in delta.items()if np.any(d != 0)))
    return final, rounds, delta


def generation_cost(rows):
    return dict(calls=len(rows), prompt_tokens_sum=sum(r["generation"]["prompt_tokens"]for r in rows),
        generated_tokens_sum=sum(r["generation"]["generated_tokens"]for r in rows),
        supervised_or_processed_forward_tokens="NOT_MEASURED_BY_THIS_RECEIPT")


def answer_rows(directory, manifest):
    rows = []
    for spec in manifest["shards"]:
        path = directory/spec["path"]
        if io.sha(path) != spec["sha256"]:
            raise ValueError("closed answer bytes changed")
        rows.extend(json.loads(line)for line in path.read_text().splitlines())
    if len(rows) != manifest["rows"]:
        raise ValueError("closed answer membership differs")
    return rows


def actual():
    budget = limits.Budget(1800); budget.check(admission=True)
    if OUT.exists():
        raise FileExistsError("preserve prior physical/cost readback")
    profile = io.read(OLD/"policy_profile_v1.json")
    manifest = manual.verify_manifest(); spec = manual.resolve_model(profile["model"])
    entry = manifest["entries"][spec.name]
    if entry["checkpoint"]["sha256"] != profile["origin"]["checkpoint_sha256"]:
        raise ValueError("read-only parent checkpoint differs")
    paths = sorted(POLICIES.glob("*/report.json"))
    if len(paths) != 22:
        raise ValueError("closed18 primary+4 supplementary policies required")
    refs = {str(p.relative_to(ROOT)):io.sha(p)for p in paths}
    refs[str(OLD.relative_to(ROOT)/"policy_profile_v1.json")] = io.sha(OLD/"policy_profile_v1.json")
    OUT.mkdir()
    io.write_new(OUT/"admission.json", dict(authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(), cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=1800, code={p:io.sha(ROOT/p)for p in CODE}, references=refs,
        checkpoint=entry["checkpoint"], model_instantiations=0, gpu_calls=0))
    started = time.monotonic(); torch.set_num_threads(4)
    payload = manual.read_selected_payload(torch, spec, entry)
    names = checkpoint_keys(payload["cfg"], payload["model"])
    originals = {i:payload["model"][name].numpy().copy()for i,name in enumerate(names)}
    if len({payload["model"][name].untyped_storage().data_ptr()for name in names}) != 14:
        raise ValueError("this ledger expects14 unique completed-parent matrices")
    del payload; gc.collect()
    records = []; errors = []; final_deltas = {}
    for path in paths:
        budget.check(); report = io.read(path); name = report["name"]
        reused = name == "SINGLE1"
        source = io.read(ROOT/report["source_report"]) if reused else report
        packets = [source["packet"]] if reused else report["packets"]
        steps = []; packet_refs = []
        for packet in packets:
            source_path = ROOT/packet["path"]
            if io.sha(source_path) != packet["sha256"]:
                raise ValueError("closed ordered physical packet changed")
            arrays = io.load_arrays(source_path)
            layer = source["layer"] if reused else packet["layer"]
            steps.append((layer, arrays["requested"], arrays["after"]))
            packet_refs.append(dict(packet, actual_layer=layer))
        physical, rounds, deltas = physical_trace(originals, steps)
        for key in ("net_norm", "path_norm"):
            if not math.isclose(physical[key], report["physical"][key], rel_tol=1e-10, abs_tol=1e-9):
                errors.append(dict(name=name, field=key, independent=physical[key], recorded=report["physical"][key]))
        for index, packet in enumerate(packets):
            for field in ("before_weight_sha256", "after_weight_sha256"):
                if field in packet:
                    expected = rounds[index][field.replace("_weight", "")]
                    if expected != packet[field]:
                        errors.append(dict(name=name, round=index+1, field=field))
        if not reused:
            for r, measured in zip(report["rounds"], rounds):
                if "layer" not in r:
                    continue
                measured.update(predicted_gain=r["chosen_predicted_gain"], actual_gain=r["chosen_actual_gain"],
                    gain_prediction_error=r["chosen_predicted_gain"]-r["chosen_actual_gain"],
                    accepted_alpha=r["alpha"], actual_J=r["after"]["J"],
                    FIT_correct=len(r["retention"]["correct_ids"]),
                    lost_previous_FIT=r["retention"]["lost_previous_ids"])
        finals = answer_rows(path.parent, report["answers_manifest"]) if not reused else answer_rows((ROOT/report["source_report"]).parent, source["answers_manifest"])
        generated = list(finals)
        if not reused:
            for r in report["rounds"]:
                generated.extend(r.get("fit_answers", []))
                for trial in r.get("trials", []):
                    generated.extend(trial["protected_answers"])
            counts = report["counts_new"]
        else:
            layer = source["layer"]
            previous = io.read(OLD/"geometry"/f"layer{layer-1:02d}"/"report.json")["counts"]
            counts = {k:source["counts"][k]-previous[k]for k in source["counts"]}
        generated_cost = generation_cost(generated)
        if counts["generated_calls"] != generated_cost["calls"]:
            errors.append(dict(name=name, field="generated_calls", independent=generated_cost["calls"], recorded=counts["generated_calls"]))
        inferred_forwards = (counts["objective_calls"]*152 + counts["native_projection_replays"]//14
                            + generated_cost["generated_tokens_sum"])
        decomposition_match = inferred_forwards == counts["model_forwards"]
        # All policies use the frozen positive KL coefficient:24 FIT and128 KL gradients.
        internal_gradient_calls = counts["gradient_calls"]*152
        record = dict(name=name, status=report["status"], actual_norms=physical, rounds=rounds,
            match_status=report.get("match_status", "REUSED_EXACT_ATLAS_ARM"),
            replay_new_cost=report["counts_new"], original_incremental_counts=counts,
            counters_are_distinct_units=True, derived_autograd_grad_calls=internal_gradient_calls,
            generated_cost=generated_cost, inferred_forward_calls=inferred_forwards,
            forward_decomposition_match=decomposition_match,
            source_counter_scope="CUMULATIVE_LAYER_DIFFERENCE" if reused else "ACTUAL_ARM_INCREMENT",
            shared_initial_gradient_and_value_library="EXCLUDED_FROM_ARM_COUNTS_NOT_FREE",
            wall_seconds=report.get("wall_seconds"),
            FIT_exact=sum(r["exact"]is True for r in finals if r["split"] == "fit"),
            DEV_target_exact=report["dev"]["target"]["exact"], J=report["objective"]["J"],
            packets=packet_refs, source_report=str(path.relative_to(ROOT)), source_report_sha256=io.sha(path))
        records.append(record)
        if name in ("SINGLE1", "SAME4", "SEQ4", "EQUAL4", "ADAPT_D4", "ADAPT_R4"):
            final_deltas[name] = deltas
        print("[COST_REUSE_PROGRESS]"+name+" physical="+str(not errors), flush=True)
    pairs = []
    for a,b in (("SINGLE1","SAME4"),("SEQ4","EQUAL4"),("ADAPT_D4","ADAPT_R4")):
        da, db = final_deltas[a], final_deltas[b]
        dot = sum(float((da[i]*db[i]).sum())for i in set(da)&set(db))
        na = math.sqrt(sum(float((d*d).sum())for d in da.values()))
        nb = math.sqrt(sum(float((d*d).sum())for d in db.values()))
        pairs.append(dict(a=a,b=b,global_delta_cosine=dot/(na*nb),norm_a=na,norm_b=nb))
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU-only completed-artifact audit initialized CUDA")
    geometry = io.read(OLD/"geometry/report.json")
    result = dict(schema="P108B_COMPLETED_COST_REUSE_V1", status="CPU_ACCOUNTING_COMPLETE" if not errors else "CPU_ACCOUNTING_NEGATIVE",
        records=records, pair_directions=pairs, discrepancies=errors,
        original_atlas_common_cost=geometry["counts"], original_atlas_wall_seconds=geometry["wall_seconds"],
        original_library_cost="NOT_REATTRIBUTED_TO_EACH_ARM", source_profile_sha256=io.sha(OUT/"admission.json"),
        checkpoint_payload_cpu_reads=1, model_instantiations=0, model_forward_calls=0,
        new_gpu_calls=0, new_generations=0, new_optimizer_updates=0, checkpoint_writes=0,
        same_query_budget_experiment="NOT_RUN", timing_scope="HISTORICAL_NON_INTERLEAVED_NOT_NEW_GPU_SPEED_TEST",
        wall_seconds=time.monotonic()-started)
    io.write_new(OUT/"report.json", result)
    print("[COST_REUSE_END]"+__import__("json").dumps(dict(status=result["status"], policies=len(records), discrepancies=len(errors),
        decomposition_matches=sum(r["forward_decomposition_match"]for r in records),wall_seconds=result["wall_seconds"])),flush=True)
    if errors:
        raise RuntimeError("preserved physical/cost mismatch")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=("check", "actual"))
    phase = ap.parse_args().phase
    if phase == "check":
        limits.Budget(1800).check(admission=True)
        if not (OLD/"policy_profile_v1.json").is_file():
            raise FileNotFoundError("completed policy profile missing")
        print("[COST_REUSE_CHECK]22 closed policies;CPU payload read only;new model/GPU0", flush=True)
    else:
        actual()


if __name__ == "__main__":
    main()
