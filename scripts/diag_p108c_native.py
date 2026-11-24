"""Admit, observe, and replay a frozen input-scoped edit on the actual model."""
import argparse
import gc
import json
from pathlib import Path
import time
import traceback

import tinylm
import numpy as np
import torch

from scripts import diag_p108c_scope as offline
from scripts import p108c_limits as limits
from scripts import p108c_scope as classifier
from scripts import p108c_runtime as runtime
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p106b_shards import ShardWriter

ROOT, BASE = offline.ROOT, offline.BASE
PROFILE = BASE/"native_profile_v1.json"
INITIAL = BASE/"native_initial_plan_v1.md"
OUT = BASE/"native_scope_v1"
CODE = ("scripts/p108c_runtime.py", "scripts/diag_p108c_native.py",
        "scripts/test_p108c_runtime.py", "scripts/p108c_scope.py", "scripts/p108c_limits.py",
        "scripts/interactive_research_infer.py", "scripts/p108_wsp_attention.py",
        "scripts/p108_weight_space.py", "scripts/p106b_shards.py")


def source():
    p = offline.verify()
    frozen = offline.read(offline.OUT/"frozen_router_v1.json")
    if frozen["profile_sha256"] != offline.sha(offline.PROFILE):
        raise ValueError("closed CPU router/profile binding changed")
    metadata = frozen["model"]
    router = {k:v for k,v in metadata.items() if k not in ("arrays", "model_array_names")}
    refs = {offline.PROFILE, offline.OUT/"frozen_router_v1.json", offline.OUT/"report.json",
            offline.OUT/"inputs.json", offline.OUT/"reused_features.npz"}
    if "arrays" in metadata:
        array = metadata["arrays"]
        path = ROOT/array["path"]
        if offline.sha(path) != array["sha256"].upper():
            raise ValueError("frozen scope model numeric bytes changed")
        values = offline.load_arrays(path)
        if sorted(values) != metadata["model_array_names"]:
            raise ValueError("frozen model array ownership differs")
        router.update(values); refs.add(path)
    data = offline.inputs()
    refs.update(data["refs"])
    original = offline.closed_answers(offline.OLD/"geometry", data["original_manifest"])
    edited = offline.closed_answers(offline.ARM, data["edited_manifest"])
    rows = [dict(r, capture_role="TRAIN") for r in data["train_meta"]]
    rows += [dict(r, capture_role="DEV") for r in data["dev"]]
    rows += [dict(original[i], capture_role="GUARD") for i in data["guard_ids"]]
    if len(rows) != 254 or len({r["id"] for r in rows}) != 254:
        raise ValueError("complete distinct TRAIN151/DEV96/guard7 inputs required")
    return p, frozen, router, data, rows, refs, original, edited


def preflight():
    limits.Budget(1200).check(admission=True)
    p, frozen, router, data, rows, refs, original, edited = source()
    manifest = manual.verify_manifest()
    tok = manual.local_tokenizer(manifest)
    from tinylm.chat.serialize import serialize
    for row in rows:
        text = serialize(dict(messages=manual.prompt_messages(row["question"])),
                         "chatml", add_generation_prompt=True)
        encoded = tok.encode(text)
        runtime.question_indices(text, row["question"], encoded.offsets)
        if len(encoded.ids)+64 > 1024:
            raise ValueError("native scope input would be truncated")
    print("[NATIVE_SCOPE_PREFLIGHT]254 valid current-question spans;model0;no CUDA", flush=True)
    return p, frozen, router, data, rows, refs, original, edited


def prepare():
    if PROFILE.exists() or INITIAL.exists():
        raise FileExistsError("preserve previous native admission")
    p, frozen, router, data, rows, refs, original, edited = preflight()
    plan = offline.PLAN.read_bytes()
    profile = dict(schema="P108C_NATIVE_SCOPE_V1", authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(), cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=1200, max_new=64, model=p["model"], origin=p["origin"],
        sources={name:offline.sha(ROOT/name) for name in CODE},
        references={str(path.relative_to(ROOT)):offline.sha(path) for path in sorted(refs)},
        initial_plan_sha256=__import__("hashlib").sha256(plan).hexdigest().upper(),
        selected_router=frozen["model"]["name"], threshold=frozen["threshold"],
        all14_feature_views=["key_last", "key_question_mean", "residual_last", "residual_question_mean"],
        native_prefills=254, conditional_generated_replies=127, forced_canaries=2,
        feature_reuse_decision_contract="ALL254_OLD_VS_NATIVE_GATE_DECISIONS_MUST_MATCH",
        no_posthoc_feature_tolerance_for_gate=True,
        optimizer_updates=0, checkpoint_writes=0, final_or_official_consumed=False)
    with INITIAL.open("xb") as stream:
        stream.write(plan)
    offline.write_new(PROFILE, profile)
    print("[NATIVE_SCOPE_PREPARED]254 prefills;127 conditional+2 forced canaries;old artifacts frozen", flush=True)


def verify():
    limits.Budget(1200).check()
    p = offline.read(PROFILE)
    if (p["authority_directive"] != 142 or p["authority_end"] != limits.AUTHORITY_END.isoformat() or
            p["sources"] != {name:offline.sha(ROOT/name) for name in CODE} or
            offline.sha(INITIAL) != p["initial_plan_sha256"]):
        raise ValueError("exact new authority/code/initial plan required")
    for path, expected in p["references"].items():
        if offline.sha(ROOT/path) != expected:
            raise ValueError("frozen source changed: " + path)
    return p


def actual():
    p = verify()
    budget = limits.Budget(p["max_seconds"])
    budget.check(admission=True)
    if OUT.exists():
        raise FileExistsError("preserve previous native trial")
    entry = cleanup_owner.resources()
    OUT.mkdir()
    start = time.monotonic()
    report = dict(schema=p["schema"], status="STARTED", entry_resources=entry,
        source_profile_sha256=offline.sha(PROFILE), optimizer_updates=0,
        checkpoint_writes=0, final_or_official_consumed=False)
    active = engine = packet = model = None
    failure = None
    try:
        _, frozen, router, data, rows, _, original, edited = source()
        packet = offline.load_arrays(offline.ARM/"packet.npz")
        torch.set_num_threads(4)
        with manual.selected_runtime(manual.resolve_model(p["model"])) as active:
            try:
                if manual.state_fingerprint(active["model"]) != p["origin"]["core_sha256"]:
                    raise ValueError("native original full core differs")
                engine = runtime.RoutedEdit(active, router, frozen["threshold"], packet, budget)
                captures = {}; by_view = {v:[] for v in p["all14_feature_views"]}
                for row in rows:
                    budget.check()
                    observed = engine.capture(row["question"], max_new=p["max_new"])
                    captures[row["id"]] = observed
                    for name in by_view:
                        by_view[name].append(observed["features"][name])
                feature_packets = {}
                for layer in range(14):
                    values = {name:np.stack(v)[:, layer] for name,v in by_view.items()}
                    feature_packets[str(layer)] = offline.save_arrays(
                        OUT/"features"/("layer"+str(layer).zfill(2)+".npz"), **values)
                metadata_pin = offline.write_new(OUT/"inputs.json",
                    dict(rows=rows, capture_roles={"TRAIN":151, "DEV":96, "GUARD":7},
                         views=p["all14_feature_views"], feature_packets=feature_packets))
                old = np.concatenate([data["train_x"], data["dev_x"], data["guard_x"]])
                new = np.stack([captures[row["id"]]["features"]["key_last"][13] for row in rows])
                old_scores, new_scores = classifier.score(router, old), classifier.score(router, new)
                old_gate = old_scores >= frozen["threshold"]
                new_gate = new_scores >= frozen["threshold"]
                parity_rows = [dict(id=row["id"], old_score=float(a), native_score=float(b),
                    old_enabled=bool(c), native_enabled=bool(d),
                    feature_max_error=float(np.abs(old[i].astype(float)-new[i].astype(float)).max()),
                    feature_relative_l2=float(np.linalg.norm(old[i].astype(float)-new[i].astype(float))) /
                        max(float(np.linalg.norm(old[i].astype(float))), 1e-30))
                    for i,(row,a,b,c,d) in enumerate(zip(rows,old_scores,new_scores,old_gate,new_gate))]
                parity = dict(items=254, decision_differences=int((old_gate != new_gate).sum()),
                              rows=parity_rows, feature_tolerance_relaxed=False)
                offline.write_new(OUT/"source_feature_parity.json", parity)
                if parity["decision_differences"]:
                    raise RuntimeError("stored-vs-native feature changed a frozen routing decision")
                writer = ShardWriter(OUT, "answers", limit=2_000_000)
                generated = []; mismatches = []
                canary = data["fits"][0]
                for enabled in (False, True):
                    answer, info, gate = engine.emit(canary["question"], observation=captures[canary["id"]],
                        max_new=p["max_new"], forced=enabled)
                    reference = (edited if enabled else original)[canary["id"]]
                    if info["generated_ids"] != reference["generation"]["generated_ids"]:
                        raise RuntimeError("forced native original/edited canary differs")
                    writer.append(dict(canary, answer=answer, generation=info, routing=gate,
                                       variant="FORCED_ON_CANARY" if enabled else "FORCED_OFF_CANARY"))
                evaluation = data["fits"]+data["dev"]+[original[i] for i in data["guard_ids"]]
                for index,row in enumerate(evaluation):
                    budget.check()
                    answer, info, gate = engine.emit(row["question"], observation=captures[row["id"]],
                                                    max_new=p["max_new"])
                    reference = (edited if gate["enabled"] else original)[row["id"]]
                    same = info["generated_ids"] == reference["generation"]["generated_ids"]
                    record = dict(row, answer=answer, generation=info, routing=gate,
                        variant="FROZEN_SCOPE", actual_history=[],
                        exact=None if row.get("expected") is None else metrics.exact_answer(answer,row["expected"]),
                        diagnostics=metrics.repetition_metrics(
                            info["generated_ids"][:-len(info["terminal_ids"])] if info["terminal_ids"] else info["generated_ids"],
                            answer,row["question"]), same_as_declared_cached_branch=same)
                    if not same:
                        mismatches.append(row["id"])
                    generated.append(record); writer.append(record)
                    if (index+1)%32 == 0:
                        print("[NATIVE_SCOPE_PROGRESS] replies="+str(index+1), flush=True)
                manifest = writer.close(lineage=dict(model_core=p["origin"]["core_sha256"],
                    conditional_input_only=True, fixed_joint_edit=offline.ARM.name))
                report.update(status="NATIVE_SCOPE_COMPLETE", answers_manifest=manifest,
                    feature_packets=feature_packets, metadata_pin=metadata_pin,
                    native_feature_decision_differences=parity["decision_differences"],
                    cached_branch_generation_mismatches=mismatches,
                    counts=dict(engine.counts), generated_replies=len(generated)+2,
                    summaries={name:dict(items=len(selected), exact=sum(r["exact"] is True for r in selected),
                        gated_on=sum(r["routing"]["enabled"] for r in selected)) for name,selected in
                        (("FIT", generated[:24]), ("DEV", generated[24:120]), ("GUARD", generated[120:]))},
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                if mismatches or report["counts"]["original_prefills"] != 254 or len(generated) != 127:
                    raise RuntimeError("conditional branch/source replay or native counts differ")
                if manual.state_fingerprint(active["model"]) != p["origin"]["core_sha256"]:
                    raise RuntimeError("original full model was not restored")
                report["original_core_restored"] = True
            finally:
                if engine is not None:
                    engine.close()
                engine = None
        active = packet = model = None
    except BaseException as error:
        failure = str(error)
        report.update(status="NATIVE_SCOPE_ERROR", error=failure, traceback=traceback.format_exc())
        error.__traceback__ = None
    finally:
        if engine is not None:
            engine.close()
        active = engine = packet = model = None
        gc.collect()
        cleanup_error = cleanup_owner.cleanup(report)
        if cleanup_error is not None and failure is None:
            failure = str(cleanup_error)
        report["wall_seconds"] = time.monotonic()-start
        offline.write_new(OUT/"report.json", report)
        print("[NATIVE_SCOPE_END] "+json.dumps({k:report.get(k) for k in
            ("status","generated_replies","summaries","wall_seconds","original_core_restored",
             "cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}), flush=True)
    if failure is not None:
        raise RuntimeError("preserved native scope failure: "+failure)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=("preflight", "prepare", "check", "actual"))
    phase = ap.parse_args().phase
    if phase == "preflight":
        preflight()
    elif phase == "prepare":
        prepare()
    elif phase == "check":
        verify()
        print("[NATIVE_SCOPE_CHECK] exact source/authority; model0", flush=True)
    else:
        actual()


if __name__ == "__main__":
    main()
