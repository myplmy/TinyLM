"""Prepare and produce resumable Ko-IFEval responses from the approved local benchmark."""

import argparse
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import json
from pathlib import Path
import time
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_ifeval_p079_runtime as generation
from scripts import eval_p109c_completed as original
from scripts import eval_p109c_mixed_v2 as v2
from scripts import p109_gpu_supervisor as telemetry
from scripts import run_p109c_scratch330 as native


ROOT = original.ROOT
DATA = ROOT / "HF/SNU_ko-IFEval/data/train-00000-of-00001.parquet"
DATA_SHA = "43751AE9484B904881EDBDD2D5F330CC6E673041028A8E4F8D6F90B07B9DCDF0"
TASK = "d8be9ad5fd1fc3495b67786177adaf3d61f69728"
SCHEMA = "P109C_KO_IFEVAL_REPLIES_ONLY_V1"
ROWS, INSTRUCTIONS, CAP, BATCH = 841, 1435, 1280, 16
STOPS = (2, 4)


def source_pins():
    paths = (Path(__file__), Path(generation.__file__), Path(v2.__file__), Path(original.__file__))
    return {str(path.resolve().relative_to(ROOT)): original.core6.digest(path) for path in paths}


def dataset():
    import pyarrow.parquet as parquet

    if original.core6.digest(original.regular_file(DATA)) != DATA_SHA:
        raise ValueError("the authorized local Korean benchmark changed")
    rows = parquet.read_table(DATA).to_pylist()
    if (len(rows) != ROWS or len({row["key"] for row in rows}) != ROWS
            or sum(len(row["instruction_id_list"]) for row in rows) != INSTRUCTIONS
            or any(not row["prompt"].strip() or len(row["instruction_id_list"]) != len(row["kwargs"]) for row in rows)):
        raise ValueError("the official Korean row, instruction or prompt denominator differs")
    return rows


def prepare(path, training_record, inputs_sha):
    rows, tok = dataset(), original.load_tokenizer()
    by_length = defaultdict(list)
    profile_rows = []
    for row in rows:
        tokens = tok.encode(row["prompt"], add_special_tokens=False).ids
        if not tokens:
            raise ValueError("the official prompt has no model input tokens")
        profile_rows.append(row["key"])
        by_length[len(tokens)].append(dict(key=row["key"], ids=tokens))
    groups = [items[i:i+BATCH] for _, items in sorted(by_length.items(), reverse=True)
              for i in range(0, len(items), BATCH)]
    profile = dict(schema=SCHEMA, official_task_commit=TASK, dataset_sha256=DATA_SHA,
                   training_record=str(training_record), training_manifest_sha256=native.digest(inputs_sha),
                   sources=source_pins(), raw_prompt=True, generation_cap=CAP, stop_ids=STOPS,
                   capacity=max(by_length)+CAP, groups=groups, original_row_order=profile_rows)
    native.publish(path, profile)
    print("KO_IFEVAL_PROFILE", original.core6.digest(path), len(groups), profile["capacity"], flush=True)


@torch.inference_mode()
def replies(model, tok, cases, check):
    xin = torch.tensor([case["ids"] for case in cases], device="cuda")
    out, stop = ([[] for _ in cases], [None] * len(cases))
    past = None
    length = xin.shape[1]
    for index in range(CAP):
        if index % 16 == 0:
            check()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits, past = model(xin, past_kv=past, use_cache=True, logits_last_only=True)
        if generation.past_length(past) != length + index:
            raise ValueError("the benchmark context was reset or truncated")
        xin = logits[:, -1].argmax(-1, keepdim=True)
        for i, value in enumerate(xin.flatten().tolist()):
            if stop[i] is None:
                out[i].append(value)
                if value in STOPS:
                    stop[i] = value
        if all(value is not None for value in stop):
            break
    return [dict(key=case["key"], response=tok.decode(ids, skip_special_tokens=True), ids=ids,
                 input_tokens=len(case["ids"]), stop=value)
            for case, ids, value in zip(cases, out, stop, strict=True)]


def validate_replies(rows, cases, tok):
    if [row["key"] for row in rows] != [case["key"] for case in cases]:
        raise ValueError("a resumed batch does not correspond to the same Korean questions")
    for row, case in zip(rows, cases, strict=True):
        ids = row["ids"]
        end = ids[-1] if ids and ids[-1] in STOPS else None
        if (not 1 <= len(ids) <= CAP or any(type(i) is not int or not 0 <= i < 32768 for i in ids)
                or end != row["stop"] or (end is None and len(ids) != CAP) or any(i in STOPS for i in ids[:-1])
                or row["input_tokens"] != len(case["ids"]) or row["response"] != tok.decode(ids, skip_special_tokens=True)):
            raise ValueError("stored Korean response IDs, sentence or stopping policy differ")


def worker(previous, profile_path, profile_sha, _resume, record, cutoff):
    with (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        profile = json.loads(native.manifest_bytes(profile_path, profile_sha))
        if profile["schema"] != SCHEMA or profile["sources"] != source_pins() or profile["dataset_sha256"] != DATA_SHA:
            raise ValueError("the intended Korean evaluation inputs changed")
        train_dir = Path(profile["training_record"])
        train = original.read_json(original.regular_file(train_dir / "input.json"))
        with patch.object(native, "STEPS", train["steps"]):
            checkpoint, checksum = v2.completed_v2(train_dir, profile["training_manifest_sha256"])
        def check():
            if time.time() >= cutoff:
                raise TimeoutError("the approved Korean response window ended")
        check()
        free, total = torch.cuda.mem_get_info()
        allowed = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < allowed <= total or torch.cuda.device_count() != 1:
            raise RuntimeError("the single assigned GPU lacks the agreed capacity")
        torch.cuda.set_per_process_memory_fraction(allowed / total)
        torch.set_num_threads(3)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        tok = original.load_tokenizer()
        model = original.load_model(checkpoint, train["steps"], "cuda")
        outputs, new_groups = {}, 0
        started = time.monotonic()
        with generation.execution_context(model, profile["capacity"]), sdpa_kernel(SDPBackend.MATH):
            proof = generation.boundary_proof(model, profile["groups"][0][0], profile["capacity"])
            for i, cases in enumerate(profile["groups"]):
                check()
                name = f"part_{i:04d}.json"
                if previous and (previous / name).exists():
                    item = original.read_json(original.regular_file(previous / name))
                    if item["profile_sha256"] != profile_sha or item["model_sha256"] != checksum:
                        raise ValueError("the existing Korean responses came from another evaluation")
                    rows = item["rows"]
                else:
                    rows = replies(model, tok, cases, check)
                    new_groups += 1
                validate_replies(rows, cases, tok)
                native.publish(record / name, dict(profile_sha256=profile_sha, model_sha256=checksum, rows=rows))
                outputs.update((row["key"], row) for row in rows)
                if i % 10 == 0:
                    print("KO_IFEVAL_GROUP", i+1, len(outputs), flush=True)
        if len(outputs) != ROWS or model.cfg.max_seq_len != 1024 or original.core6.digest(checkpoint) != checksum:
            raise RuntimeError("the exact 841 responses and unchanged model are required")
        native.publish(record / "report.json", dict(status="REPLIES_COMPLETE", rows=ROWS, instructions=INSTRUCTIONS,
            profile_sha256=profile_sha, model_sha256=checksum, new_groups=new_groups, context_proof=proof,
            seconds=time.monotonic()-started, scoring_status="NOT_RUN",
            responses=[outputs[key] for key in profile["original_row_order"]]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--profile", required=True, type=Path)
    prep.add_argument("--training-record", required=True, type=Path)
    prep.add_argument("--training-manifest-sha256", required=True)
    run = sub.add_parser("run")
    run.add_argument("--profile", required=True, type=Path)
    run.add_argument("--profile-sha256", required=True)
    run.add_argument("--previous", type=Path)
    run.add_argument("--record", required=True, type=Path)
    run.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    path = args.profile.absolute()
    if args.mode == "prepare":
        prepare(path, args.training_record.absolute(), args.training_manifest_sha256)
        return 0
    if args.stop_by.tzinfo is None:
        parser.error("the authorized limit needs its timezone")
    expected, record = native.digest(args.profile_sha256), args.record.absolute()
    with (patch.object(native, "gpu_worker", partial(worker, args.previous)),
          patch.object(native, "gpu_status", partial(telemetry.gpu_status, record))):
        return native.supervise(path, expected, False, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
