"""Verify saved Korean responses and apply the pinned, local KBS scorer offline."""

import argparse
from hashlib import sha1
import importlib.metadata
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
from unittest.mock import patch

from scripts import eval_p109c_ko_ifeval_replies as ko


SOURCES = {
    "ko-ifeval.yaml": "6cd0c091cae31bab9df064c4babd9bb6a3180383",
    "utils.py": "a08aee7123dd23a8e13e7551b7e2010d931d964d",
    "instructions_util.py": "8c2bd1503c0ca1ba7096da1a5910fe3287336c4b",
    "instructions.py": "f3a39c32e9ec407793ee51c98c38e8b43ff8d896",
    "instructions_registry.py": "4e64ea1ae2d87f0ec1b33ebfe1eb878b32c5788f",
}
PRESENTATIONS = {True: "plain", False: "chatml"}


def load_inputs(replies_path, replies_sha, profile_path, profile_sha):
    report = json.loads(ko.native.manifest_bytes(replies_path, replies_sha))
    profile = json.loads(ko.native.manifest_bytes(profile_path, profile_sha))
    published = report["responses"]
    data = ko.dataset()
    roster = [doc["key"] for doc in data]
    if (report["status"] != "REPLIES_COMPLETE" or report["rows"] != ko.ROWS
            or report["instructions"] != ko.INSTRUCTIONS or report["profile_sha256"] != profile_sha
            or profile["schema"] != ko.SCHEMA or profile["dataset_sha256"] != ko.DATA_SHA
            or profile["official_task_commit"] != ko.TASK or profile["generation_cap"] != ko.CAP
            or profile["original_row_order"] != roster or [row["key"] for row in published] != roster):
        raise ValueError("the scored answers must cover exactly the frozen dataset and presentation")
    by_key = {row["key"]: row for row in published}
    all_cases = [case for batch in profile["groups"] for case in batch]
    if len(all_cases) != ko.ROWS or {case["key"] for case in all_cases} != set(roster):
        raise ValueError("the frozen presentation lost or duplicated official input rows")
    tokenizer = ko.original.load_tokenizer()
    ko.validate_replies([by_key[case["key"]] for case in all_cases], all_cases, tokenizer)
    return data, published, dict(dataset_sha256=ko.DATA_SHA, task_commit=ko.TASK,
                                 checkpoint_sha256=report["model_sha256"], presentation=PRESENTATIONS[profile["raw_prompt"]],
                                 profile_sha256=profile_sha, replies_sha256=replies_sha)


def verify_local_task(root):
    if root.resolve(strict=True) != root or {path.name for path in root.iterdir()} != SOURCES.keys():
        raise ValueError("the local task directory must contain only the five reviewed source files")
    for filename, expected in SOURCES.items():
        path = ko.original.regular_file(root / filename)
        data = path.read_bytes()
        digest = sha1(f"blob {len(data)}".encode() + bytes([0]) + data).hexdigest()
        if digest != expected:
            raise ValueError(f"the local KBS source bytes differ: {filename}")


def score_rows(task, zip_rows):
    totals = {}
    per_instruction = {mode: [] for mode in ("strict", "loose")}
    individual = []
    for document, response in zip_rows:
        scored = task.process_results(document, [response["response"]])
        row = {"key": document["key"]}
        for mode, arrays in per_instruction.items():
            flags = scored[f"inst_level_{mode}_acc"]
            passed = scored[f"prompt_level_{mode}_acc"]
            if (len(flags) != len(document["instruction_id_list"]) or any(type(flag) is not bool for flag in flags)
                    or type(passed) is not bool or passed != all(flags)):
                raise ValueError("the pinned official scorer produced inconsistent booleans")
            arrays.append(flags)
            row[mode] = flags
        individual.append(row)
    for mode, arrays in per_instruction.items():
        seen = sum(map(len, arrays))
        correct = sum(sum(flags) for flags in arrays)
        if len(arrays) != ko.ROWS or seen != ko.INSTRUCTIONS:
            raise ValueError("the official aggregate denominators differ")
        official = task.agg_inst_level_acc(arrays)
        if not math.isclose(official, correct / seen, abs_tol=1e-12):
            raise ValueError("the official instruction aggregate disagrees with the independent sum")
        totals[mode] = dict(prompt_correct=sum(all(flags) for flags in arrays), prompt_rows=len(arrays),
                            instructions_correct=correct, instruction_rows=seen)
    return totals, individual


def score(root, documents, responses):
    verify_local_task(root)
    if any(name in sys.modules for name in ("instructions", "instructions_registry", "instructions_util")):
        raise ValueError("start a fresh evaluator process without another IFEval task loaded")
    import langdetect
    import nltk
    from packaging.version import Version

    if Version(nltk.__version__) < Version("3.9.1"):
        raise ValueError("the pinned scorer expects the current local punkt_tab route")
    nltk.data.find("tokenizers/punkt_tab")

    def reject_download(*args, **kwargs):
        raise RuntimeError("the offline evaluator may use only the existing punkt_tab files")

    random.seed(1337)
    langdetect.DetectorFactory.seed = 1337
    module = importlib.util.spec_from_file_location("kbs_ko_ifeval_pinned_utils", root / "utils.py")
    task = importlib.util.module_from_spec(module)
    with (patch.object(sys, "path", [str(root), *sys.path]), patch.object(sys, "dont_write_bytecode", True),
          patch.object(nltk, "download", reject_download),
          patch.dict(sys.modules, {module.name: task})):
        module.loader.exec_module(task)
        result = score_rows(task, zip(documents, responses, strict=True))
    verify_local_task(root)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check-replies", "score"))
    parser.add_argument("--replies", required=True, type=Path)
    parser.add_argument("--replies-sha256", required=True)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--task-dir", type=Path)
    parser.add_argument("--record", required=True, type=Path)
    args = parser.parse_args()
    if args.record.exists() or args.record.is_symlink() or (args.mode == "score" and not args.task_dir):
        parser.error("the evaluator requires a fresh output and a pinned local scoring source")
    replies_sha, profile_sha = map(ko.native.digest, (args.replies_sha256, args.profile_sha256))
    documents, responses, lineage = load_inputs(args.replies.absolute(), replies_sha, args.profile.absolute(), profile_sha)
    if args.mode == "check-replies":
        result = dict(status="FROZEN_REPLIES_VERIFIED", rows=ko.ROWS, instructions=ko.INSTRUCTIONS, **lineage)
    else:
        totals, rows = score(args.task_dir.absolute(), documents, responses)
        versions = {name: importlib.metadata.version(name) for name in ("nltk", "langdetect", "immutabledict")}
        result = dict(status="KBS_OFFICIAL_SCORING_COMPLETE", packages=versions, sources=SOURCES,
                      totals=totals, rows=rows, **lineage)
    args.record.mkdir(exist_ok=False)
    ko.native.publish(args.record / "report.json", result)
    print(result["status"], flush=True)


if __name__ == "__main__":
    main()
