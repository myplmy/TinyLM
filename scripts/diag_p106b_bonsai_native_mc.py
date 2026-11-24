"""Evaluate Bonsai PTQ1_0 with the existing official multiple-choice definitions."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sysconfig
import time

import numpy as np

from scripts import diag_p106b_belebele as belebele
from scripts import diag_p106b_bonsai_native_lambada as lambada
from scripts import prepare_p106b_kobest_official_eval as kobest
from scripts.p106b_official_lm_adapter import COMMIT, MANIFEST, SOURCE, canonical, prepare_harness
from scripts.p106b_official_tasks import task_requests
from scripts.p106b_prism_likelihood import PrismLikelihood
from scripts.p106b_shards import ShardWriter, verify as verify_shards
from scripts.summarize_p106b_core6_pairs import memory_task


prism = lambada.prism
ROOT = prism.ROOT
TAG = "p106b_bonsai_native_mc_v1_20261118"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
LAMBADA_READBACK = prism.AUDIT / "BONSAI_NATIVE_LAMBADA_CLOSED_READBACK_v1.json"
HARD_SECONDS = 3000
MIN_FREE_BYTES = 8*1024**3
TOTAL_BYTES = 128_000_000
EXPECTED = {**{f"belebele_{lang}": 900 for lang in belebele.LANGUAGES},
            **{f"kobest_{family}": spec[0] for family, spec in kobest.SPECS.items()}}
SOURCES = (
    "scripts/diag_p106b_bonsai_native_mc.py", "scripts/diag_p106b_belebele.py",
    "scripts/diag_p106b_bonsai_native_lambada.py", "scripts/prepare_p106b_kobest_official_eval.py",
    "scripts/p106b_official_tasks.py", "scripts/summarize_p106b_core6_pairs.py",
    "scripts/diag_p106b_official_core6.py",
)


def load_tasks(kobest_only=False):
    os.environ.update(HF_EVALUATE_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    docs, asset_metadata, alignment = belebele.read_assets(allow_download=False)
    be, be_definition = belebele.load_tasks(docs)
    tasks = {f"belebele_{lang}": be[lang] for lang in belebele.LANGUAGES}
    pins = {str((belebele.DATA / info["filename"]).relative_to(ROOT)):
            prism.digest(belebele.DATA/info["filename"]) for info in belebele.SPECS.values()}
    from datasets import Dataset
    from lm_eval.api.task import ConfigurableTask
    from lm_eval.tasks._yaml_loader import load_yaml

    manifest_path = kobest.ASSETS/"manifest.json"
    manifest = prism.read(manifest_path)
    assert manifest["dataset_revision"] == kobest.REVISION and manifest["source_commit"] == COMMIT
    sources = kobest.task_sources(SOURCE, Path(prism.read(MANIFEST)["archive_path"]))
    pins.update({str((SOURCE/name).relative_to(ROOT)): value for name, value in sources.items()})
    pins[str(manifest_path.relative_to(ROOT))] = prism.digest(manifest_path)
    assert {x["family"] for x in manifest["tests"]} == set(kobest.SPECS) and len(manifest["tests"]) == 5
    for item in manifest["tests"]:
        family, name = item["family"], item["task"]
        assert name == "kobest_"+family and item["rows"] == EXPECTED[name]
        path = kobest.ASSETS/(family+"_test.jsonl")
        assert str(path.relative_to(ROOT)) == item["local_path"]
        pins[item["local_path"]] = prism.digest(path)
        assert pins[item["local_path"]] == item["sha256"]
        proof = kobest.scan_test(path, family)
        assert proof["ordered_json_sha256"] == item["ordered_json_sha256"]
        original = load_yaml(str(SOURCE/f"lm_eval/tasks/kobest/{name}.yaml"), resolve_func=True, recursive=True)
        semantic = {key: original.get(key) for key in item["semantic_fields_unchanged"]}
        original.update(item["storage_overrides"])
        rows = [json.loads(line, object_pairs_hook=kobest.unique_object) for line in path.read_bytes().splitlines()]
        task = memory_task(ConfigurableTask, original, {"test": Dataset.from_list(rows)})
        assert set(task.dataset) == {"test"} and not task.eval_docs.cache_files
        assert all(getattr(task.config, key) == value for key, value in semantic.items() if value is not None)
        tasks[name] = task
    assert {name: len(t.eval_docs) for name,t in tasks.items()} == EXPECTED
    selected = {name: task for name,task in tasks.items() if not kobest_only or name.startswith("kobest_")}
    return selected, pins, dict(belebele=be_definition, belebele_assets=asset_metadata, alignment=alignment,
        kobest_sources=sources, kobest_revision=kobest.REVISION)


def item_for(task, doc, index):
    _, choices, requests = task_requests(task, doc, index)
    gold = task.doc_to_text(doc) if task.multiple_input else task.doc_to_target(doc)
    if isinstance(gold, str):
        gold = choices.index(gold)
    if type(gold) is not int or not 0 <= gold < len(choices):
        raise ValueError("official gold is not an exact choice index")
    arguments = [list(request.args) for request in requests]
    assert all(request.idx == i for i, request in enumerate(requests))
    if task.config.task.startswith("belebele_"):
        assert arguments == [list(r.args) for r in belebele.requests_for(task, doc, index)]
    return dict(doc_id=index, doc=doc, choices=choices, arguments=arguments, gold=gold)


def item_score(task, item, responses):
    responses = [lambada.official.valid_response(value) for value in responses]
    assert len(responses) == len(item["choices"])
    scores = [ll for ll, _ in responses]
    pred = max(range(len(scores)), key=scores.__getitem__)
    norm = max(range(len(scores)), key=lambda i: scores[i]/len(item["choices"][i]))
    official = task.process_results(item["doc"], responses)
    gold = item["gold"]
    expected = {"acc": int(pred == gold), "acc_norm": int(norm == gold), "f1": (gold, pred)}
    assert "acc" in official and all(value == expected[name] for name,value in official.items())
    return pred, norm, {name: expected[name] for name in official}


def aggregate(task, rows):
    metrics = task.aggregation()
    matrix = Counter((row["gold"], row["pred"]) for row in rows)
    classes = sorted({j for cell in matrix for j in cell})
    total = len(rows)
    per_class = [2*matrix[j,j]/sum(value*((g == j)+(p == j)) for (g,p),value in matrix.items())
                 for j in classes]
    expected = dict(acc=sum(matrix[j,j] for j in classes)/total,
        acc_norm=sum(row["gold"] == row["pred_norm"] for row in rows)/total,
        f1=math.fsum(per_class)/len(per_class))
    results = {name: float(fn([row["metrics"][name] for row in rows])) for name, fn in metrics.items()}
    assert all(math.isclose(score, expected[name], abs_tol=1e-12, rel_tol=1e-10) for name,score in results.items())
    return dict(metrics=results, classes=classes, confusion=[[matrix[g,p] for p in classes] for g in classes])


def prepare_items(tasks):
    itemsets, receipts = {}, {}
    for name, task in tasks.items():
        rows, digest, label_difference = [], hashlib.sha256(), 0
        for index, doc in enumerate(task.eval_docs):
            item = item_for(task, dict(doc), index)
            if name.startswith("kobest_"):
                label_difference += item["gold"] != doc["label"]
            digest.update(canonical(item)+bytes((10,)))
            rows.append(item)
        dummy = []
        for row in rows[:32]:
            responses = [(-float(i+1), False) for i in range(len(row["choices"]))]
            pred, norm, metrics = item_score(task, row, responses)
            sample = dict(gold=row["gold"], pred=pred, pred_norm=norm, metrics=metrics)
            canonical(sample)
            dummy.append(sample)
        check = aggregate(task, dummy)
        itemsets[name] = rows
        receipts[name] = dict(rows=len(rows), ordered_full_request_sha256=digest.hexdigest().upper(),
            official_vs_raw_label_difference=label_difference, cpu_metric_fixture=check)
    return itemsets, receipts


def source_pins():
    return {name:prism.digest(ROOT/name) for name in SOURCES}


def prior_proof():
    old_profile, native = lambada.verify()
    readback = prism.read(LAMBADA_READBACK)
    assert readback["status"] == "CLOSED_FULL_OFFICIAL_EVALUATION"
    assert readback["profile"]["sha256"] == prism.digest(lambada.PROFILE)
    return old_profile, native


def prepare(kobest_only=False):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    prior_proof()
    tasks, data, metadata = load_tasks(kobest_only)
    _, proof = prepare_items(tasks)
    sources = source_pins()
    OUT.mkdir(exist_ok=False)
    snapshot = OUT/"sources"
    snapshot.mkdir()
    for name in sources:
        with (snapshot/Path(name).name).open("xb") as stream:
            stream.write((ROOT/name).read_bytes())
    prism.write(PROFILE, dict(schema="P106B_BONSAI_NATIVE_MC_PROFILE_V1", tag=TAG, sources=sources,
        data_pins=data, definition=metadata, tasks=proof, lambada_readback_sha256=prism.digest(LAMBADA_READBACK),
        hard_seconds=HARD_SECONDS, output_cap_bytes=TOTAL_BYTES, GPU_calls=0, kobest_only=kobest_only))
    print("BONSAI_MC_PREPARED", {k:v["rows"] for k,v in proof.items()}, prism.digest(PROFILE), flush=True)


def verify():
    profile = prism.read(PROFILE)
    assert profile["sources"] == source_pins()
    assert profile["lambada_readback_sha256"] == prism.digest(LAMBADA_READBACK)
    assert all(prism.digest(OUT/"sources"/Path(name).name) == sha for name,sha in profile["sources"].items())
    assert all(prism.digest(ROOT/name) == sha for name,sha in profile["data_pins"].items())
    assert time.time()+120 < lambada.CUTOFF
    _, native = prior_proof()
    return profile, native


def token_jobs(engine, items, check):
    plans, work, holes, failures = [], [], [], 0
    for item in items:
        check()
        try:
            candidates = [engine.plan(*args) for args in item["arguments"]]
        except ValueError as error:
            failures += 1
            if len(holes) < 16:
                holes.append(dict(index=item["doc_id"], reason=str(error)))
            continue
        prefixes = {engine.prefix(plan,i) for plan in candidates for i in range(len(plan.continuation_ids))}
        work.append(sum(map(len,prefixes)))
        plans.append(candidates)
    return plans, work, holes, failures


def evaluate(engine, name, task, items, target, remaining, check, budget):
    plans, work, holes, failures = token_jobs(engine, items, check)
    if failures:
        return dict(status="TOKEN_BOUNDARY_HOLD", rejected=failures, examples=holes, scored_rows=0)
    largest = max(range(len(items)), key=work.__getitem__)
    longest = max(plans[largest], key=lambada.work)
    proof = lambada.numerical_gate(engine, [("first", plans[0][0]), ("max_work_item_choice",longest)])
    picks = sorted({i*(len(items)-1)//15 for i in range(16)} | {largest})
    tick = time.monotonic()
    pilot = {i:engine.score(plans[i]) for i in picks}
    measured = time.monotonic()-tick
    forecast = 1.5*measured*max(len(items)/len(picks), sum(work)/sum(work[i] for i in picks))+120
    point = dict(sample_indices=picks, seconds=measured, forecast_seconds=forecast, remaining_seconds=remaining())
    print("BONSAI_MC_COST", name, json.dumps(point), flush=True)
    if not math.isfinite(forecast) or forecast > point["remaining_seconds"]:
        return dict(status="COST_HOLD", scored_rows=0, cost=point)

    writer = ShardWriter(target, name, limit=10_000_000)
    scored, completed = [], False
    tick = time.monotonic()
    try:
        for i, (item, candidates) in enumerate(zip(items, plans, strict=True)):
            check()
            scores = pilot[i] if i in pilot else engine.score(candidates)
            responses = [score["response"] for score in scores]
            pred, norm, metrics = item_score(task, item, responses)
            row = dict(**item, pred=pred, pred_norm=norm, metrics=metrics, responses=responses,
                tokens=[dict(**lambada.task_plan(plan), continuation_ids=list(plan.continuation_ids),
                    greedy_ids=score["greedy_ids"], position_logprob=score["position_logprob"])
                    for plan,score in zip(candidates,scores,strict=True)])
            used = len(canonical(row))+1
            if budget[0]+used > TOTAL_BYTES:
                raise lambada.Hold("total record byte limit")
            writer.append(row)
            scored.append(row)
            budget[0] += used
            if (i+1) % 250 == 0:
                print("BONSAI_MC_PROGRESS",name,i+1,len(items),flush=True)
        result = aggregate(task, scored)
        completed = True
    finally:
        if scored:
            manifest = writer.close(lineage=dict(tag=TAG, task=name, evaluation_only=True, complete=completed))
        else:
            writer._finish()
    verify_shards(target, manifest)
    return dict(status="COMPLETE", scored_rows=len(scored), cost=point, numerical_oracles=proof,
        sample_manifest=manifest, decoding_seconds=time.monotonic()-tick, **result,
        predictor_positions=sum(work), max_input_tokens=max(len(plan.input_ids) for item in plans for plan in item),
        choice_context_truncation=sum(plan.truncated_context_tokens>0 for item in plans for plan in item))


def actual():
    if time.time()+HARD_SECONDS+120 > lambada.CUTOFF:
        raise lambada.Hold("declared interval unavailable")
    started = time.monotonic()
    profile, native = verify()
    assert os.environ.get("LD_LIBRARY_PATH") == native["bundle"]
    assert not any(key.startswith(("LLAMA_ARG_", "GGML_")) for key in os.environ)
    target = OUT/"actual"
    target.mkdir(exist_ok=False)
    report = dict(schema="P106B_BONSAI_NATIVE_MC_ACTUAL_V1", tag=TAG, PID=os.getpid(),
        started_UTC=datetime.now(timezone.utc).isoformat(), profile_sha256=prism.digest(PROFILE),
        tasks={}, result_exit=1, training_steps=0, checkpoint_writes=0)

    def remaining():
        return min(HARD_SECONDS-(time.monotonic()-started), lambada.CUTOFF-time.time()-30)

    def check():
        if remaining() <= 0 or (OUT/"STOP").exists():
            raise lambada.Hold("declared evaluation deadline or owned STOP")

    def stop(_sig, _frame):
        raise lambada.Hold("owned interrupt")

    previous = signal.signal(signal.SIGINT, stop)
    try:
        report["gpu_point_entry"] = lambada.require_idle_gpu()
        output = subprocess.check_output(["nvidia-smi","--query-gpu=memory.free","--format=csv,noheader,nounits"],
            text=True, timeout=10)
        report["gpu_point_free_bytes"] = int(output.strip())*1024**2
        if report["gpu_point_free_bytes"] < MIN_FREE_BYTES:
            raise lambada.Hold("below fixed free memory admission")
        tasks, data, metadata = load_tasks(profile["kobest_only"])
        itemsets, anchor = prepare_items(tasks)
        assert canonical(data) == canonical(profile["data_pins"])
        assert canonical(anchor) == canonical(profile["tasks"])
        assert canonical(metadata) == canonical(profile["definition"])
        template,_ = prepare_harness(runtime_root=Path(sysconfig.get_paths()["purelib"]))
        budget = [0]
        with prism.native.NativeModel(native["bundle"],ROOT/native["model"],check=check) as model:
            assert model.piece(lambada.EOT) == b"<|im_end|>"
            witness = np.load(prism.OUT/"actual/A0_logits_fp32.npy", allow_pickle=False)
            actual_a = model.logits(native["prompts"]["A"]["native_ids"])
            if not np.array_equal(witness.view(np.uint32), actual_a.view(np.uint32)):
                raise lambada.Hold("A bit witness differs from the qualified native run")
            report["qualified_A_reproduced"] = True
            engine = PrismLikelihood(model,template,lambada.EOT,check=check)
            for name,task in tasks.items():
                result = evaluate(engine,name,task,itemsets[name],target,remaining,check,budget)
                report["tasks"][name] = result
                print("BONSAI_MC_TASK",name,{k:result[k] for k in ("status","scored_rows","metrics","rejected") if k in result},flush=True)
            report["native_forward_calls"] = model.calls
            report["native_processed_tokens"] = model.processed_tokens
        report["native_handles_closed"] = not model.model and not model.context and not model.backend
        if not report["native_handles_closed"]:
            raise ValueError("Prism context or model remained owned after evaluation")
        complete = set(report["tasks"]) == set(profile["tasks"]) and all(r["status"] == "COMPLETE" for r in report["tasks"].values())
        report.update(status="ALL_OFFICIAL_TASKS_COMPLETE" if complete else "PARTIAL_TASK_HOLD",
            result_exit=0 if complete else 8, output_bytes=budget[0])
    except BaseException as error:
        hold = isinstance(error,lambada.Hold)
        report.update(status="HOLD" if hold else "ERROR",result_exit=8 if hold else 1,
            error=dict(type=type(error).__name__, message=str(error)[:1000]))
    finally:
        signal.signal(signal.SIGINT,previous)
        report["wall_seconds"] = time.monotonic()-started
        report["process_peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        try:
            verify()
            report["frozen_files_unchanged"] = True
        except BaseException as error:
            report.update(status="FINAL_PROVENANCE_ERROR",result_exit=9,verify_error=str(error)[:1000])
        prism.write(target/"report.json", report)
    print("BONSAI_MC_TERMINAL",{k:report[k] for k in ("status","result_exit","wall_seconds","error","verify_error") if k in report},flush=True)
    return report["result_exit"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","check","actual"))
    parser.add_argument("--kobest-recovery", action="store_true")
    args = parser.parse_args()
    stage = args.stage
    if args.kobest_recovery:
        TAG = "p106b_bonsai_native_kobest_v2_20261118"
        OUT = ROOT/"test_result/evidence"/TAG
        PROFILE = OUT/"profile.json"
    if stage == "prepare":
        prepare(args.kobest_recovery)
    elif stage == "check":
        profile, native = verify()
        print("BONSAI_MC_CHECK",len(profile["tasks"]),len(native["pins"]),prism.digest(PROFILE))
    else:
        raise SystemExit(actual())
