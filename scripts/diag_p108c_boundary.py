"""Frozen scope versus global edit on unseen probes and actual own-history turns."""
import argparse
from collections import Counter
import gc
import json
import time
import traceback
import numpy as np
import torch
import tinylm

from scripts import diag_p108c_scope as io
from scripts import diag_p108c_native as native
from scripts import diag_p108c_scope_atlas as atlas
from scripts import p108c_boundary_data as probes
from scripts import p108c_runtime as runtime
from scripts import p108c_limits as limits
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p106b_shards import ShardWriter

ROOT, BASE = io.ROOT, io.BASE
PROFILE = BASE/"boundary_profile_v1.json"
INITIAL = BASE/"boundary_initial_plan_v1.md"
DATA = BASE/"boundary_data_v1.json"
OUT = BASE/"boundary_actual_v1"
ARMS = ("ORIGINAL", "GLOBAL", "DELTA_SCOPE", "ATLAS_SCOPE")
CODE = ("scripts/diag_p108c_boundary.py", "scripts/p108c_boundary_data.py",
        "scripts/test_p108c_boundary.py", "scripts/p108c_runtime.py",
        "scripts/p108c_scope.py", "scripts/p108c_limits.py",
        "scripts/interactive_research_infer.py", "scripts/p108_wsp_attention.py",
        "scripts/p108_weight_space.py", "scripts/p106b_shards.py")


def load_router(frozen):
    metadata = frozen["model"]
    model = {k:v for k,v in metadata.items() if k not in ("arrays", "model_array_names")}
    refs = set()
    if "arrays" in metadata:
        path = ROOT/metadata["arrays"]["path"]
        if io.sha(path) != metadata["arrays"]["sha256"]:
            raise ValueError("frozen scope arrays changed")
        arrays = io.load_arrays(path)
        if sorted(arrays) != metadata["model_array_names"]:
            raise ValueError("frozen scope array keys changed")
        model.update(arrays); refs.add(path)
    return model, refs


def source():
    native.verify(); atlas.verify()
    p, frozen0, router0, previous, rows, refs, original, edited = native.source()
    atlas_report = io.read(atlas.OUT/"report.json")
    if atlas_report["status"] != "SCOPE_ATLAS_CPU_COMPLETE_FINAL_NOT_RUN":
        raise ValueError("closed atlas required")
    frozen1 = io.read(atlas.OUT/"frozen_router_v1.json")
    router1, extra = load_router(frozen1)
    refs.update(extra)
    refs.update({native.PROFILE, native.OUT/"report.json", atlas.PROFILE,
                 atlas.OUT/"report.json", atlas.OUT/"frozen_router_v1.json"})
    configurations = {
        "DELTA_SCOPE": dict(model=router0, threshold=frozen0["threshold"],
            feature_layer=13, feature_view="key_last"),
        "ATLAS_SCOPE": dict(model=router1, threshold=frozen1["threshold"],
            feature_layer=frozen1["feature_layer"], feature_view=frozen1["feature_view"]),
    }
    questions = [r["question"] for r in list(original.values())+list(edited.values())]
    return p, configurations, refs, questions


def preflight():
    limits.Budget(3600).check(admission=True)
    p, configurations, refs, questions = source()
    value = probes.dataset(); rows = probes.validate(value, questions)
    tok = manual.local_tokenizer(manual.verify_manifest())
    from tinylm.chat.serialize import serialize
    lengths = {}
    for r in rows:
        text = serialize(dict(messages=manual.prompt_messages(r["question"])),
                         "chatml", add_generation_prompt=True)
        encoded = tok.encode(text)
        runtime.question_indices(text, r["question"], encoded.offsets)
        lengths[r["id"]] = len(encoded.ids)
        if len(encoded.ids)+96 > 1024:
            raise ValueError("fresh single input would be truncated")
    for dialog in value["dialogs"]:
        conservative_bound = sum(lengths[r["id"]]+96+32 for r in dialog)
        if conservative_bound > 1024:
            raise ValueError("conservative3-turn input bound exceeds context")
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU preflight initialized CUDA")
    print("[BOUNDARY_PREFLIGHT]fresh208 single+12 own-history turns;four frozen paths;model0", flush=True)
    return p, configurations, refs, value, lengths


def prepare():
    if any(p.exists() for p in (PROFILE, INITIAL, DATA)):
        raise FileExistsError("preserve previous fresh-boundary admission")
    p, configurations, refs, value, lengths = preflight()
    data_pin = io.write_new(DATA, value)
    plan = io.PLAN.read_bytes()
    with INITIAL.open("xb") as f:
        f.write(plan)
    io.write_new(PROFILE, dict(schema="P108C_FRESH_BOUNDARY_V1", authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(), cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=3600, max_new=96, model=p["model"], origin=p["origin"],
        sources={n:io.sha(ROOT/n) for n in CODE},
        references={str(p.relative_to(ROOT)):io.sha(p) for p in sorted(refs)},
        initial_plan_sha256=io.sha(INITIAL), data=data_pin, arms=list(ARMS),
        optimizer_updates=0, checkpoint_writes=0, training_allowed=False,
        official=False, fresh_answers_opened=False, frozen_before_new_answers=True,
        expected_generated_replies=880, expected_original_prefills=256,
        single_cases=208, own_history_turns=12, max_single_prompt_tokens=max(lengths.values()),
        frozen_routers={k:dict(threshold=v["threshold"], feature_layer=v["feature_layer"],
            feature_view=v["feature_view"], name=v["model"]["name"])for k,v in configurations.items()},
        quality_and_scope_are_separate=True, no_post_final_reselection=True))
    print("[BOUNDARY_PREPARED]220 inputs/880 replies;scope and edit frozen before answers", flush=True)


def verify():
    limits.Budget(3600).check()
    p = io.read(PROFILE)
    if (p["authority_directive"] != 142 or p["authority_end"] != limits.AUTHORITY_END.isoformat()
            or p["cleanup_seconds"] != limits.CLEANUP_SECONDS
            or p["sources"] != {n:io.sha(ROOT/n) for n in CODE}
            or io.sha(INITIAL) != p["initial_plan_sha256"]
            or io.sha(DATA) != p["data"]["sha256"]):
        raise ValueError("exact new phase authority/source/initial plan/data required")
    for name, expected in p["references"].items():
        if io.sha(ROOT/name) != expected:
            raise ValueError("frozen boundary source changed: "+name)
    return p


def arm_order(index):
    offset = index % len(ARMS)
    return ARMS[offset:] + ARMS[:offset]


def summaries(records):
    result = {}
    for arm in ARMS:
        result[arm] = {}
        for mode in ("SINGLE", "OWN_HISTORY"):
            selected = [r for r in records if r["arm"] == arm and r["mode"] == mode]
            result[arm][mode] = dict(total=metrics.summarize(selected),
                families={family:metrics.summarize([r for r in selected if r["family"] == family])
                    for family in sorted({r["family"] for r in selected})})
            if arm in ("DELTA_SCOPE", "ATLAS_SCOPE"):
                routed = [r for r in selected if r["scope_expected"]]
                negative = [r for r in selected if not r["scope_expected"]]
                result[arm][mode]["scope"] = dict(targets=len(routed),
                    target_enabled=sum(r["routing"]["enabled"] for r in routed),
                    non_targets=len(negative), non_target_enabled=sum(r["routing"]["enabled"] for r in negative))
    # Only the single-turn panel has the same actual input history for every arm.
    by = {(r["arm"], r["id"]):r for r in records if r["mode"] == "SINGLE"}
    paired = {}
    for arm in ARMS[1:]:
        pairs = [(by[("ORIGINAL", identifier)], r)for (name, identifier),r in by.items() if name == arm]
        paired[arm] = dict(same_inputs=len(pairs),
            strict_corrected=sum(a["exact"] is False and b["exact"] is True for a,b in pairs),
            strict_harmed=sum(a["exact"] is True and b["exact"] is False for a,b in pairs),
            changed_answer_tokens=sum(a["generation"]["generated_ids"] != b["generation"]["generated_ids"] for a,b in pairs),
            note="OWN_HISTORY is deliberately a different actual-history panel")
    return result, paired


def actual():
    p = verify(); budget = limits.Budget(p["max_seconds"]); budget.check(admission=True)
    if OUT.exists():
        raise FileExistsError("preserve previous fresh boundary run")
    entry = cleanup_owner.resources(); OUT.mkdir(); start = time.monotonic()
    report = dict(schema=p["schema"], status="STARTED", source_profile_sha256=io.sha(PROFILE),
        entry_resources=entry, optimizer_updates=0, checkpoint_writes=0,
        final_opened=True, official=False, no_reselection=True)
    active = engine = packet = None; failure = None; writer = None
    try:
        _, configurations, _, _ = source()
        data = io.read(DATA); probes.validate(data)
        packet = io.load_arrays(io.ARM/"packet.npz")
        torch.set_num_threads(4)
        with manual.selected_runtime(manual.resolve_model(p["model"])) as active:
            try:
                if manual.state_fingerprint(active["model"]) != p["origin"]["core_sha256"]:
                    raise ValueError("original model core differs")
                c = configurations["DELTA_SCOPE"]
                engine = runtime.RoutedEdit(active, c["model"], c["threshold"], packet, budget)
                writer = ShardWriter(OUT, "answers", limit=2_000_000)
                records = []; feature_meta = []; feature13 = []; feature12 = []
                def observe(row, history, owner):
                    budget.check(); torch.cuda.synchronize(); began = time.monotonic()
                    observation = engine.capture(row["question"], history=history, max_new=p["max_new"])
                    torch.cuda.synchronize(); seconds = time.monotonic()-began
                    observation_index = len(feature_meta)
                    feature_meta.append(dict(id=row["id"], history_owner=owner,
                        prompt_sha256=observation["prompt_sha256"], ids=observation["ids"],
                        question_positions=observation["question_positions"], prefill_seconds=seconds))
                    feature13.append(observation["features"]["key_last"][13])
                    feature12.append(observation["features"]["key_last"][12])
                    return observation, observation_index
                def generate(row, history, arm, observation, feature_index, mode):
                    budget.check()
                    c = configurations[arm] if arm in configurations else configurations["DELTA_SCOPE"]
                    engine.router = c["model"]; engine.threshold = c["threshold"]
                    engine.feature_layer = c["feature_layer"]; engine.feature_view = c["feature_view"]
                    forced = False if arm == "ORIGINAL" else True if arm == "GLOBAL" else None
                    torch.cuda.synchronize(); began = time.monotonic()
                    answer, generation, routing = engine.emit(row["question"], history=history,
                        max_new=p["max_new"], observation=observation, forced=forced)
                    torch.cuda.synchronize(); seconds = time.monotonic()-began
                    content = generation["generated_ids"][:-len(generation["terminal_ids"])] if generation["terminal_ids"] else generation["generated_ids"]
                    record = dict(row, arm=arm, mode=mode, answer=answer, generation=generation,
                        actual_history=[dict(m)for m in history], routing=routing,
                        feature_observation_index=feature_index, generate_and_edit_seconds=seconds,
                        exact=metrics.exact_answer(answer, row["expected"]) if row["expected"] is not None else None,
                        factual_string_present=(row["content_answer"].casefold() in answer.casefold()) if row["content_answer"] else None,
                        diagnostics=metrics.repetition_metrics(content, answer, row["question"]))
                    writer.append(record); records.append(record)
                    if len(records)%64 == 0:
                        print("[BOUNDARY_PROGRESS]replies="+str(len(records)), flush=True)
                    return answer
                for index, row in enumerate(data["singles"]):
                    observation, feature_index = observe(row, [], "COMMON_SINGLE")
                    for arm in arm_order(index):
                        generate(row, [], arm, observation, feature_index, "SINGLE")
                for index, dialog in enumerate(data["dialogs"]):
                    for arm in arm_order(index):
                        history = []
                        for row in dialog:
                            observation, feature_index = observe(row, history, arm)
                            answer = generate(row, history, arm, observation, feature_index, "OWN_HISTORY")
                            history += [dict(role="user", content=row["question"]), dict(role="assistant", content=answer)]
                manifest = writer.close(lineage=dict(model_core=p["origin"]["core_sha256"],
                    source_profile=io.sha(PROFILE), no_reselection=True, actual_own_history=True))
                features_pin = io.save_arrays(OUT/"gating_features.npz",
                    key_layer13=np.stack(feature13), key_layer12=np.stack(feature12))
                metadata_pin = io.write_new(OUT/"feature_metadata.json", dict(rows=feature_meta,
                    features=features_pin, no_label_or_gold_in_model_input=True))
                totals, paired = summaries(records)
                report.update(status="FRESH_BOUNDARY_COMPLETE", summaries=totals,
                    paired_single=paired, answers_manifest=manifest, feature_metadata=metadata_pin,
                    counts=dict(engine.counts), generated_replies=len(records),
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                    style_naturalness="GPT_READING_PENDING_NOT_AUTOMATICALLY_SCORED")
                if (len(records) != p["expected_generated_replies"] or
                        engine.counts["original_prefills"] != p["expected_original_prefills"]):
                    raise RuntimeError("declared fresh membership count differs")
                if manual.state_fingerprint(active["model"]) != p["origin"]["core_sha256"]:
                    raise RuntimeError("original complete model was not restored")
                report["original_core_restored"] = True
            finally:
                if engine is not None:
                    engine.close()
                engine = None
        active = packet = None
    except BaseException as error:
        failure = str(error)
        report.update(status="FRESH_BOUNDARY_ERROR", error=failure, traceback=traceback.format_exc())
        error.__traceback__ = None
    finally:
        if engine is not None:
            engine.close()
        active = engine = packet = None
        gc.collect(); cleanup_error = cleanup_owner.cleanup(report)
        if cleanup_error is not None and failure is None:
            failure = str(cleanup_error)
        report["wall_seconds"] = time.monotonic()-start
        io.write_new(OUT/"report.json", report)
        print("[BOUNDARY_END]"+json.dumps({k:report.get(k)for k in
            ("status","generated_replies","wall_seconds","original_core_restored",
             "cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}), flush=True)
    if failure is not None:
        raise RuntimeError("preserved fresh-boundary failure: "+failure)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=("preflight", "prepare", "check", "actual"))
    phase = ap.parse_args().phase
    if phase == "preflight":
        preflight()
    elif phase == "prepare":
        prepare()
    elif phase == "check":
        verify(); print("[BOUNDARY_CHECK]exact phase source/authority;model0", flush=True)
    else:
        actual()


if __name__ == "__main__":
    main()
