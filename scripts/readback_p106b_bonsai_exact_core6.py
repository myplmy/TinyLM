"""Recount stored Bonsai Core6 likelihoods and pair them with stored NativeQ rows."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shlex

from handoff.audit.research_20261118_01a1e647.check_hellaswag_exact_intervals import check_row
from scripts import diag_p106b_bonsai_native_core6 as core
from scripts import run_p106b_hellaswag_exact_suffix as suffix
from scripts import summarize_p106b_core6_pairs as pairs
from scripts.p106b_official_tasks import task_requests


ROOT = pairs.ROOT
OUT = suffix.EVIDENCE / "p106b_bonsai_exact_core6_readback_v1_20261118"
REFERENCE = OUT / "nativeq_and_bonsai_five.json"
FULL = OUT / "full_core6.json"
COMPARATOR = "native595-q"
TASK = "hellaswag"


def load_official(inputs):
    tasks, _ = pairs.load_readonly_tasks(inputs)
    items, receipt = core.mc.prepare_items(tasks)
    suffix.require(receipt == suffix.read(core.PROFILE)["tasks"]["items"], "official request or order differs")
    return tasks, items


def shard_rows(directory, manifest):
    suffix.verify_shards(directory, manifest)
    for shard in manifest["shards"]:
        with (directory / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                yield json.loads(line)


def reference():
    suffix.require(not REFERENCE.exists(), "reference output already exists")
    inputs = pairs.Inputs()
    tasks, items = load_official(inputs)
    admission = suffix.read(core.OUT / "actual/report.json")
    inputs.add(core.PROFILE, admission["profile_sha256"])
    inputs.add(core.OUT / "actual/report.json")
    five = {}
    for name, task in tasks.items():
        if name == TASK:
            continue
        evidence = admission["tasks"][name]
        directory = core.OUT / "actual"
        manifest = evidence["manifest"]
        suffix.require(evidence["status"] == "COMPLETE" and manifest["rows"] == len(items[name]),
                       f"the stored Bonsai task is incomplete: {name}")
        primary = pairs.PRIMARY[name]
        values = []
        for row, item in zip(shard_rows(directory, manifest), items[name], strict=True):
            suffix.require(all(row[key] == value for key, value in item.items()), f"Bonsai case differs in {name}")
            pred, norm, metrics = core.mc.item_score(task, item, row["responses"])
            suffix.require(row["pred"] == pred and row["pred_norm"] == norm
                           and core.canonical(row["metrics"]) == core.canonical(metrics),
                           f"Bonsai stored scoring differs in {name}")
            values.append(metrics[primary])
        suffix.require(sum(values) / len(values) == evidence["metrics"][primary], f"Bonsai aggregate differs in {name}")
        five[name] = dict(values=values, metrics=evidence["metrics"], manifest_sha256=manifest["concat_sha256"])

    path = pairs.report_path(COMPARATOR)
    inputs.add(path)
    report = pairs.read_json(path)
    pairs.admit_report(COMPARATOR, report)
    contracts = {name: pairs.CaseContracts(task, pairs.COUNTS[name], task_requests) for name, task in tasks.items()}
    for name, contract in contracts.items():
        for left, right in zip(contract.rows, items[name], strict=True):
            suffix.require(all(left[key] == right[key] for key in ("doc", "choices", "arguments")),
                           f"NativeQ and Bonsai do not share the same request in {name}")
    native = pairs.recount_model(COMPARATOR, path, report, tasks, inputs, task_requests, contracts)
    inputs.unchanged()
    OUT.mkdir(exist_ok=True)
    core.PRISM.write(REFERENCE, dict(source_sha256=suffix.digest(Path(__file__)),
        official_profile_sha256=suffix.digest(core.PROFILE), nativeq=native, bonsai_five=five,
        model_loads=0, gpu_calls=0))
    print("BONSAI_CORE6_PAIR_REFERENCE", suffix.digest(REFERENCE), native["rows"], flush=True)


def raw_logs(paths, receipts):
    expected = {tag.removeprefix(suffix.TAG_PREFIX): (tag, seal) for tag, seal in receipts.items()}
    logs = {}
    for name in paths:
        path = pairs.regular(name)
        suffix.require(path.parent == ROOT / "test_result", "raw log must be in test_result")
        with path.open(encoding="utf-8") as stream:
            command = [line.removeprefix("[runlog] cmd=").strip() for line in stream if line.startswith("[runlog] cmd=")]
        argv = shlex.split(command[0]) if len(command) == 1 else []
        suffix.require("--run-id" in argv, f"one suffix invocation required in {path.name}")
        run_id = argv[argv.index("--run-id") + 1]
        suffix.require(run_id in expected and run_id not in logs, f"unexpected or duplicate run in {path.name}")
        tag, seal = expected[run_id]
        state = suffix.read(suffix.EVIDENCE / tag / "terminal.json")
        with path.open(encoding="utf-8") as stream:
            codes = [int(line.split()[2]) for line in stream if line.startswith("[runlog] 종료코드 ")]
        suffix.require(codes == [state["exit"]], f"process exit and terminal differ in {path.name}")
        logs[run_id] = dict(path=str(path.relative_to(ROOT)), sha256=suffix.digest(path), exit=codes[0], terminal_sha256=seal)
    suffix.require(logs.keys() == expected.keys(), "closed logs required for each suffix with retained rows")
    return logs


def full(paths, reference_sha):
    suffix.require(not FULL.exists() and suffix.digest(REFERENCE) == reference_sha,
                   "a verified reference and unused full output are required")
    fixed, cursor, receipts = suffix.history()
    suffix.require(cursor == fixed["rows_total"], "official HellaSwag rows are incomplete")
    logs = raw_logs(paths, receipts)
    previous = suffix.read(REFERENCE)
    suffix.require(previous["official_profile_sha256"] == suffix.digest(core.PROFILE), "reference task profile changed")
    inputs = pairs.Inputs()
    tasks, items = load_official(inputs)
    expected = items[TASK]
    rows, counts = [], Counter()
    historical = [child["tag"] for child in suffix.read(suffix.ANCHOR)["children"]]
    for tag in (*historical, *receipts):
        directory = suffix.EVIDENCE / tag
        for record in suffix.read(directory / "terminal.json")["intervals"]:
            if record["rows"] == 0:
                continue
            first, end = record["first"], record["end_exclusive"]
            suffix.require(first == len(rows), "hole or overlap after a closed interval")
            for row in shard_rows(directory / f"rows_{first:05}_{end:05}", record["manifest"]):
                index = len(rows)
                suffix.require(index < cursor and row["doc_id"] == index, "wrong official document order")
                truncated, positions = check_row(row, expected[index])
                counts.update(candidates=4, truncate_candidates=truncated, positions=positions)
                rows.append(row)
    suffix.require(len(rows) == cursor and counts["candidates"] == 4 * cursor, "full official denominator required")
    result = core.mc.aggregate(tasks[TASK], rows)
    values = {name: task["values"] for name, task in previous["bonsai_five"].items()}
    values[TASK] = [row["metrics"][pairs.PRIMARY[TASK]] for row in rows]
    paired = pairs.paired_intervals(previous["nativeq"]["values"], values)
    inputs.unchanged()
    core.PRISM.write(FULL, dict(task=TASK, official=fixed["official"], hellaswag_rows=cursor,
        counts=dict(counts), hellaswag=result, paired_bonsai_minus_nativeq=paired,
        nativeq=previous["nativeq"]["model_proof"], reference_sha256=reference_sha, suffix_raw=logs,
        cpu_anchor_sha256=suffix.ANCHOR_SHA, source_sha256=suffix.digest(Path(__file__)), model_loads=0, gpu_calls=0))
    print("BONSAI_CORE6_FULL_CPU_READBACK", cursor, result["metrics"], paired["mean6"], suffix.digest(FULL), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("reference", "full"))
    parser.add_argument("--log", action="append", default=[])
    parser.add_argument("--reference-sha")
    args = parser.parse_args()
    suffix.require(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "CPU recount requires empty CUDA selection")
    if args.mode == "reference":
        reference()
    else:
        full(args.log, args.reference_sha)


if __name__ == "__main__":
    main()
