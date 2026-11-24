"""CPU layer/pooling scope atlas from one closed native observation pass."""
import argparse
import platform
import time
import numpy as np
import torch
from scripts import diag_p108c_scope as io
from scripts import diag_p108c_native as native
from scripts import p108c_scope as scope
from scripts import p108c_limits as limits

ROOT, BASE = io.ROOT, io.BASE
PROFILE = BASE/"scope_atlas_profile_v1.json"
INITIAL = BASE/"scope_atlas_initial_plan_v1.md"
OUT = BASE/"scope_atlas_v1"
CODE = ("scripts/diag_p108c_scope_atlas.py", "scripts/p108c_scope.py",
        "scripts/p108c_limits.py", "scripts/diag_p108c_scope.py")


def source():
    native.verify()
    report = io.read(native.OUT/"report.json")
    if (report["status"] != "NATIVE_SCOPE_COMPLETE" or
            report["cached_branch_generation_mismatches"] or
            report["native_feature_decision_differences"] or
            not report["original_core_restored"] or report["cuda_allocated_after_bytes"] or
            report["cuda_reserved_after_bytes"]):
        raise ValueError("closed native observations and exact declared branch replay required")
    metadata = io.read(native.OUT/"inputs.json")
    rows = metadata["rows"]
    if len(rows) != 254 or [r["capture_role"] for r in rows] != ["TRAIN"]*151+["DEV"]*96+["GUARD"]*7:
        raise ValueError("unchanged native row membership/order required")
    arrays = {}
    refs = {native.PROFILE, native.OUT/"report.json", native.OUT/"inputs.json"}
    for layer in range(14):
        spec = report["feature_packets"][str(layer)]
        path = ROOT/spec["path"]
        if io.sha(path) != spec["sha256"].upper():
            raise ValueError("native feature packet changed")
        values = io.load_arrays(path)
        if sorted(values) != sorted(metadata["views"]):
            raise ValueError("feature view ownership differs")
        for view, value in values.items():
            expected_width = 2048 if view.startswith("key_") else 768
            if value.shape != (254, expected_width):
                raise ValueError("native feature width/order differs")
        arrays[layer] = values
        refs.add(path)
    return rows, arrays, refs


def prepare():
    limits.Budget(1800).check(admission=True)
    if PROFILE.exists() or INITIAL.exists():
        raise FileExistsError("preserve previous scope-atlas admission")
    rows, arrays, refs = source()
    plan = io.PLAN.read_bytes()
    with INITIAL.open("xb") as stream:
        stream.write(plan)
    io.write_new(PROFILE, dict(schema="P108C_SCOPE_ATLAS_V1", authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(), cleanup_seconds=limits.CLEANUP_SECONDS,
        max_seconds=1800, sources={n:io.sha(ROOT/n) for n in CODE},
        references={str(p.relative_to(ROOT)):io.sha(p) for p in sorted(refs)},
        initial_plan_sha256=__import__("hashlib").sha256(plan).hexdigest().upper(),
        numpy_version=np.__version__, python_version=platform.python_version(),
        new_fit_families=55, reused_last13_family=True, new_scoring_models_per_family=5,
        no_new_native_or_final=True, model_loads=0, gpu_calls=0))
    print("[SCOPE_ATLAS_PREPARED]55 new feature families;last13 frozen control reused;model0", flush=True)


def verify():
    limits.Budget(1800).check()
    p = io.read(PROFILE)
    if (p["authority_directive"] != 142 or p["cleanup_seconds"] != limits.CLEANUP_SECONDS or
            p["authority_end"] != limits.AUTHORITY_END.isoformat() or
            p["sources"] != {n:io.sha(ROOT/n) for n in CODE} or
            io.sha(INITIAL) != p["initial_plan_sha256"] or p["numpy_version"] != np.__version__):
        raise ValueError("exact atlas code/runtime/authority and initial plan required")
    for path, sha in p["references"].items():
        if io.sha(ROOT/path) != sha:
            raise ValueError("frozen native source changed")
    return p


def selection_key(selected, layer, view):
    return (-selected["dev"]["tp"], selected["parameter_bytes"], view, layer,
            selected["name"], selected["threshold"])


def actual():
    p = verify(); budget = limits.Budget(p["max_seconds"]); budget.check(admission=True)
    if OUT.exists():
        raise FileExistsError("preserve previous atlas")
    OUT.mkdir(); start = time.monotonic()
    rows, arrays, _ = source()
    _, frozen, old_router, data, _, _, original, edited = native.source()
    train_y = np.array([r["label"] for r in rows[:151]])
    dev_y = np.array([r["family"] == "target" for r in rows[151:247]], dtype=int)
    groups = [r["group"] for r in rows[:151]]
    parent = io.read(io.OUT/"selection.json")["selected"]
    best = dict(selected=parent, layer=13, view="key_last", reused=True)
    best_model = old_router
    table = [dict(best, status="REUSED_FROZEN_LAST13_WITH_NATIVE_DECISION_PARITY")]
    completed = 0; uninformative = []
    for layer in range(14):
        for view in sorted(arrays[layer]):
            if layer == 13 and view == "key_last":
                continue
            budget.check()
            x = arrays[layer][view]
            try:
                models, fit = scope.fit_models(x[:151], train_y, groups,
                    np.zeros((1, x.shape[1])), ridge_values=(1e-4, 1e-2, 1.))
                # No arbitrary application of the layer13 edit to other representations.
                models = [m for m in models if m["kind"] != "delta_response"]
                model, selection = scope.select(models, x[:151], train_y,
                                                  x[151:247], dev_y, x[247:])
            except ValueError as error:
                if "zero direction" not in str(error):
                    raise
                uninformative.append(dict(layer=layer, view=view, reason=str(error)))
                table.append(dict(layer=layer, view=view, status="UNINFORMATIVE_ZERO_DIRECTION"))
                continue
            report_pin = io.write_new(OUT/"families"/("layer"+str(layer).zfill(2)+"_"+view+".json"),
                dict(layer=layer, view=view, fit=fit, selection=selection))
            entry = dict(layer=layer, view=view, selected=selection["selected"],
                         status="CPU_SCOPE_FIT_COMPLETE", selection_packet=report_pin, reused=False)
            table.append(entry); completed += 1
            if selection_key(entry["selected"], layer, view) < selection_key(best["selected"], best["layer"], best["view"]):
                best = entry; best_model = model
            if completed%8 == 0:
                print("[SCOPE_ATLAS_PROGRESS] families="+str(completed)+
                      " best_dev_tp="+str(best["selected"]["dev"]["tp"]), flush=True)
    arrays_to_save = {k:v for k,v in best_model.items() if isinstance(v, np.ndarray)}
    metadata = {k:v for k,v in best_model.items() if not isinstance(v, np.ndarray)}
    if arrays_to_save:
        metadata["arrays"] = io.save_arrays(OUT/"selected_model.npz", **arrays_to_save)
    metadata["model_array_names"] = sorted(arrays_to_save)
    io.write_new(OUT/"frozen_router_v1.json", dict(model=metadata, threshold=best["selected"]["threshold"],
        feature_layer=best["layer"], feature_view=best["view"], selected=best["selected"],
        selection_profile_sha256=io.sha(PROFILE), selected_before_new_final=True,
        final_or_official_consumed=False))
    x = arrays[best["layer"]][best["view"]]
    decisions = scope.route(best_model, x, best["selected"]["threshold"])
    cached = {}
    for name, first, last, cases in (("FIT",0,24,data["fits"]),("DEV",151,247,data["dev"]),
                                     ("GUARD",247,254,[original[i]for i in data["guard_ids"]])):
        values = []
        for row, enabled in zip(cases, decisions[first:last]):
            a, b = original[row["id"]], edited[row["id"]]
            answer = b if enabled else a
            values.append(dict(id=row["id"], gated_on=bool(enabled),
                original_exact=a["exact"], global_exact=b["exact"], cache_join_exact=answer["exact"]))
        cached[name] = dict(items=len(values), original_exact=sum(r["original_exact"]is True for r in values),
            global_exact=sum(r["global_exact"]is True for r in values),
            cache_join_exact=sum(r["cache_join_exact"]is True for r in values), rows=values)
    io.write_new(OUT/"cached_answer_join.json", dict(role="CACHED_COMPOSITION_NOT_NEW_NATIVE",groups=cached))
    report = dict(schema=p["schema"], status="SCOPE_ATLAS_CPU_COMPLETE_FINAL_NOT_RUN",
        selected=best, family_table=table, new_fit_families=completed,
        uninformative_families=uninformative, reused_families=1,
        new_scoring_models=completed*5, final_or_official_consumed=False,
        original_source_arrays_unchanged=True, model_loads=0, generated_replies=0,
        cuda_initialized=torch.cuda.is_initialized(), wall_seconds=time.monotonic()-start,
        source_profile_sha256=io.sha(PROFILE), selection_over_many_views_not_independent_test=True)
    if report["cuda_initialized"]:
        raise RuntimeError("CPU atlas unexpectedly initialized CUDA")
    io.write_new(OUT/"report.json", report)
    print("[SCOPE_ATLAS_END] "+__import__("json").dumps({k:report[k]for k in
        ("status","selected","new_fit_families","new_scoring_models","wall_seconds")}), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=("preflight","prepare","check","actual"))
    phase = ap.parse_args().phase
    if phase == "preflight":
        limits.Budget(1800).check(admission=True); source()
        print("[SCOPE_ATLAS_PREFLIGHT]14 closed native layers/4 views;model0",flush=True)
    elif phase == "prepare":
        prepare()
    elif phase == "check":
        verify(); print("[SCOPE_ATLAS_CHECK]source exact;model0;CUDA0",flush=True)
    else:
        actual()


if __name__ == "__main__":
    main()
