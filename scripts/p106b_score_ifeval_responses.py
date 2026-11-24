"""Apply the pinned official IFEval checker to the existing complete CPU index."""

import argparse
from importlib import import_module, metadata, util
import json
import os
from pathlib import Path
import random

from packaging.version import Version

from scripts.p106b_ifeval_response_readback import (
    OUT, ROOT, ROWS, SOURCE, TAG, digest, file_bytes, publish_json, readback,
)


AUDIT = ROOT / "handoff/audit/research_20261118_01a1e647/IFEVAL541_DATA_ADMISSION_v1.json"
TASK_FILES = {"ifeval.yaml", "utils.py", "instructions.py", "instructions_registry.py", "instructions_util.py"}
METRICS = ("prompt_level_strict_acc", "inst_level_strict_acc",
           "prompt_level_loose_acc", "inst_level_loose_acc")
INSTRUCTIONS = 834


def dependency_readiness():
    manifest_bytes = file_bytes(SOURCE.parent / "manifest.json")
    admission = json.loads(file_bytes(AUDIT))
    if digest(manifest_bytes) != admission["asset_manifest_sha256"]:
        raise ValueError("The evaluation-only asset manifest has changed")
    pins = json.loads(manifest_bytes)["local_scorer_source_pins"]
    framework = util.find_spec("lm_eval")
    if framework is None or framework.origin is None:
        raise ValueError("Use the existing pinned lm_eval environment")
    installed = Path(framework.origin).resolve().parent / "tasks/ifeval"
    if ({Path(relative).name for relative in pins} != TASK_FILES or len(pins) != len(TASK_FILES)
            or any((ROOT / relative).parent != installed or digest(file_bytes(ROOT / relative)) != sha
                   for relative, sha in pins.items())):
        raise ValueError("The active IFEval checker must be the pinned source")

    versions = {"lm_eval": metadata.version("lm_eval")}
    blockers = []
    for package in ("langdetect", "immutabledict", "nltk"):
        try:
            version = metadata.version(package)
        except metadata.PackageNotFoundError:
            version = None
        versions[package] = version
        if version is None or util.find_spec(package) is None:
            blockers.append(package)
    if versions["nltk"] is not None and Version(versions["nltk"]) < Version("3.9.1"):
        blockers.append("nltk>=3.9.1")
    if not blockers:
        nltk = import_module("nltk")
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            blockers.append("punkt_tab")
    return dict(ready=not blockers, dependency_blockers=blockers, versions=versions,
                required_resource="tokenizers/punkt_tab", official_checker_source_sha256=pins)


def score_inputs():
    index_bytes = file_bytes(OUT / "official_response_index.json")
    index = json.loads(index_bytes)
    current = readback()
    if (index["verified_rows"] != ROWS or index["official_scores"] is not None
            or any(index[field] != value for field, value in current.items())):
        raise ValueError("The stored 541-response index differs from the published GPU batches")
    receipt_name = index["full_window_file"]
    if receipt_name != Path(receipt_name).name or not receipt_name.startswith("window_"):
        raise ValueError("Expected a local full-window receipt name")
    receipt_bytes = file_bytes(OUT / receipt_name)
    receipt = json.loads(receipt_bytes)
    if (digest(receipt_bytes) != index["full_window_sha256"] or receipt["tag"] != TAG
            or receipt["profile_sha256"] != index["profile_sha256"] or not receipt["full_response_count"]
            or receipt["verified_rows"] != ROWS or not receipt["state_restored"]
            or receipt["checkpoint_writes"] != 0):
        raise ValueError("Full GPU window receipt differs from the response index")
    docs = [json.loads(line) for line in file_bytes(SOURCE).splitlines()]
    return docs, index["responses"], digest(index_bytes)


def evaluate(docs, responses, process_results, mean, instruction_accuracy):
    keys = [doc["key"] for doc in docs]
    if (len(keys) != ROWS or len(set(keys)) != ROWS or [r["key"] for r in responses] != keys
            or any(type(row["response"]) is not str for row in responses)
            or sum(len(doc["instruction_id_list"]) for doc in docs) != INSTRUCTIONS
            or any(not doc["instruction_id_list"] or len(doc["kwargs"]) != len(doc["instruction_id_list"])
                   for doc in docs)):
        raise ValueError("Exactly 541 original prompts and 834 matching instruction slots are required")

    records = []
    for doc, answer in zip(docs, responses, strict=True):
        metrics = process_results(doc, [answer["response"]])
        count = len(doc["instruction_id_list"])
        if set(metrics) != set(METRICS):
            raise ValueError("The official metric set differs from the task YAML")
        for name, value in metrics.items():
            if name.startswith("prompt_level"):
                if type(value) is not bool:
                    raise ValueError(f"Expected a boolean prompt result for {name}")
            elif type(value) is not list or len(value) != count or any(type(bit) is not bool for bit in value):
                raise ValueError(f"Expected one boolean result per source instruction for {name}")
        records.append({"key": doc["key"], "instruction_ids": doc["instruction_id_list"], **metrics})
    scores = {}
    for name in METRICS:
        reduce = mean if name.startswith("prompt_level") else instruction_accuracy
        scores[name] = reduce([row[name] for row in records])
    return scores, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("check", "score"))
    args = parser.parse_args()
    readiness = dependency_readiness()
    if args.phase == "check" or not readiness["ready"]:
        print(json.dumps({**readiness, "official_checker_imported": False, "official_scores": None}))
        return 2 if args.phase == "score" else 0

    docs, responses, index_sha = score_inputs()
    os.environ["LOCAL_RANK"] = "1"  # Preserve the pinned import's no-download branch.
    checker = import_module("lm_eval.tasks.ifeval.utils")
    from lm_eval.api.metrics import mean
    from lm_eval.defaults import DEFAULT_RANDOM_SEED

    random.seed(DEFAULT_RANDOM_SEED)
    scores, rows = evaluate(docs, responses, checker.process_results, mean, checker.agg_inst_level_acc)
    publish_json(OUT / "official_scores.json", dict(
        **readiness, official_checker_imported=True, tag=TAG, response_index_sha256=index_sha,
        prompt_denominator=ROWS, instruction_denominator=INSTRUCTIONS,
        python_random_seed=DEFAULT_RANDOM_SEED, langdetect_seed="UPSTREAM_DEFAULT",
        official_scores=scores, rows=rows,
    ))
    print(json.dumps(dict(prompt_denominator=ROWS, instruction_denominator=INSTRUCTIONS, official_scores=scores)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
