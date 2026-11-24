"""Score matched P077 long-context choices with the native P079 G4 engine."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from time import perf_counter
from unittest.mock import patch
import zipfile

import numpy as np
import pyarrow.parquet as parquet
import torch
from tokenizers import Tokenizer

from scripts import diag_p109_frozen_g4_routes as frozen
from scripts import p077_g4_blocked_runtime as native


ROOT = frozen.ROOT
EVIDENCE = ROOT / "test_result/evidence"
REFERENCE = EVIDENCE / "p077_g4_extended_workspace_cpu_v1_20261121"
TASK_SOURCES = {
    "winogrande": "winogrande_xl/validation-00000-of-00001.parquet",
    "kobest_copa": "copa_test.jsonl",
}
FILLER = {
    "winogrande": (
        "A station logged the temperature at noon. The monthly chart used a fixed scale. "
        "Each measurement occupied a separate row. The figures were checked before publication. "
        "The last column contained a weekly average. The records were arranged in date order. "
    ),
    "kobest_copa": (
        "관측소는 정오에 기온을 기록했다. 월간 도표는 일정한 눈금을 사용했다. "
        "측정값은 별도의 행에 적었다. 발행 전에 수치를 확인했다. "
        "마지막 열에는 주간 평균이 들어 있었다. 기록은 날짜순으로 정리했다. "
    ),
}
CONTEXT, CHOICES_PER_LABEL, SHORT_LIMIT = 2048, 2, 12
CUTOFF = datetime.fromisoformat("2026-11-21T13:00:00+09:00")
CPU_CORES = (2, 4, 6, 8, 10, 12)


def read(path):
    return json.loads(path.read_bytes())


def publish(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write(chr(10))


def arguments(task, row):
    if task == "winogrande":
        before, after = row["sentence"].split("_", 1)
        options = (row["option1"], row["option2"])
        seams = list(re.finditer(r"[,;.!?](?=\s+\S)", before))
        seam = seams[-1].end() if seams else 0
        return [(before + option, " " + after.strip()) for option in options], int(row["answer"]) - 1, seam
    connector = {"원인": "왜냐하면", "결과": "그래서"}[row["question"].strip()]
    premise = row["premise"]
    return [(premise + "  " + connector, " " + row[k]) for k in ("alternative_1", "alternative_2")], row["label"], len(premise)


def encode_pair(tokenizer, context, target):
    # Match the pinned causal adapter's movement of trailing whitespace.
    prefix = context.rstrip()
    target = context[len(prefix):] + target
    head = tokenizer.encode(prefix, add_special_tokens=False)
    together = tokenizer.encode(prefix + target, add_special_tokens=False).ids
    return head, together[len(head.ids):]


def token_boundary(encoded, boundary):
    left = sum(end <= boundary for _, end in encoded.offsets)
    if 0 < left < len(encoded.ids) and all(start >= boundary for start, _ in encoded.offsets[left:]):
        return left
    return None


def contains(sequence, part):
    return any(sequence[i:i + len(part)] == part for i in range(len(sequence) - len(part) + 1))


def filler_tokens(tokenizer, task, count):
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False).ids
    start, end = encode("\n\n---\n"), encode("\n---\n\n")
    text = encode(FILLER[task])
    size = count - len(start) - len(end)
    return start + (text * ((size + len(text) - 1) // len(text)))[:size] + end


def prior_scores():
    embedding = native.bounded.base.prior.embedding
    profiles = embedding.OUT
    raw, profile = (profiles / name for name in ("choice_batches.jsonl", "profile.json"))
    receipt = read(profiles / "gpu_report.json")
    archived = read(frozen.OUT / "profile.json")
    if (embedding.SHA(raw) != receipt["raw_sha256"] or embedding.SHA(profile) != receipt["profile_sha256"]
            or read(profile)["requests"] != archived["tasks"]):
        raise ValueError("existing INT8 embedding scores lack the matching input receipts")
    records = {name: {} for name in TASK_SOURCES}
    with raw.open(encoding="utf-8") as stream:
        for row in map(json.loads, stream):
            if row["arm"] == "int8":
                task = records[row["task"]]
                if row["index"] in task:
                    raise ValueError("duplicate saved batch")
                task[row["index"]] = row["scores"]
    scores = {name: [score[0] for i in range(len(by_batch)) for score in by_batch[i]]
              for name, by_batch in records.items()}
    return archived, scores, receipt["raw_sha256"]


def prepare_task(tokenizer, task, archived, scores):
    path, = (Path(name) for name in archived["files"] if name.endswith(TASK_SOURCES[task]))
    data_sha = frozen.prior.io.digest(path)
    if data_sha != archived["files"][str(path)]["sha256"]:
        raise ValueError("saved evaluation-only data identity differs")
    if task == "winogrande":
        docs = parquet.read_table(path).to_pylist()
    else:
        docs = [json.loads(line) for line in path.read_bytes().splitlines()]

    requests, plans, eligible = [], [], []
    for i, row in enumerate(docs):
        pairs, gold, boundary = arguments(task, row)
        requests.extend([i, option, pair] for option, pair in enumerate(pairs))
        enc = [encode_pair(tokenizer, *pair) for pair in pairs]
        plans.extend(frozen.adapter.plan_tokens(head.ids, target, frozen.VOCAB) for head, target in enc)
        archive_margin = scores[2 * i + gold] - scores[2 * i + 1 - gold]
        if archive_margin < 0.08 or not boundary:
            continue
        (head_a, target_a), (head_b, target_b) = enc
        if len(head_a.ids) != len(head_b.ids) or not (2 <= len(target_a) == len(target_b) <= 8):
            continue
        cut = token_boundary(head_a, boundary)
        if cut is None or cut < 3 or token_boundary(head_b, boundary) != cut or head_a.ids[:cut] != head_b.ids[:cut]:
            continue
        common = head_a.ids[:cut]
        if any(contains(common, target) for _, target in enc):
            continue
        padding = filler_tokens(tokenizer, task, CONTEXT - len(head_a.ids) - len(target_a) + 1)
        if any(contains(padding, target) for _, target in enc):
            continue
        eligible.append(dict(task=task, index=i, gold=gold, cut=cut, archive_margin=archive_margin,
                             contexts=[head.ids for head, _ in enc], targets=[target for _, target in enc], padding=padding))
    encoded_batches = [frozen.adapter.padded_batch(plans[i:i + frozen.BATCH_CHOICES], 0, frozen.VOCAB)
                       for i in range(0, len(plans), frozen.BATCH_CHOICES)]
    prior = archived["tasks"][task]
    request_sha, batch_sha = frozen.checksum(requests), frozen.checksum(encoded_batches)
    if (len(docs) != prior["rows"] or len(plans) != len(scores) or request_sha != prior["request_sha256"]
            or batch_sha != prior["token_batch_sha256"]):
        raise ValueError(f"cannot recover the exact saved {task} requests and token rows")
    eligible.sort(key=lambda row: sha256(f"20261121/{task}/{row['index']}".encode()).digest())
    return eligible, dict(rows=len(docs), data_sha256=data_sha, request_sha256=request_sha,
                          token_batch_sha256=batch_sha, eligible=len(eligible))


def render_forcing(source):
    replace = native.replace_once
    source = replace(source,
        b"        require(fread(tokens.data(), sizeof(uint32_t), prefix, stdin) == prefix && fgetc(stdin) == EOF,",
        b"        std::array<uint32_t,8> targets{};\n"
        b"        require(fread(tokens.data(), sizeof(uint32_t), prefix, stdin) == prefix &&\n"
        b"                fread(targets.data(), sizeof(uint32_t), generate, stdin) == generate && fgetc(stdin) == EOF,")
    return replace(source, b"runtime.next(&ids[i-1], 1, prefix + i - 1)",
                   b"runtime.next(&targets[i-1], 1, prefix + i - 1)")


def score(binary, model, context, target, cpu, out, *, resources=False):
    cap = datetime.now(CUTOFF.tzinfo)
    available = (CUTOFF - cap).total_seconds() - 10
    if available <= 0 or (out / "STOP").exists():
        raise TimeoutError("P077 owner stop or cutoff reached")
    payload = struct.pack(f"<{2 + len(context) + len(target)}I", len(context), len(target), *context, *target)
    descriptor = native.bounded.base.memfile("p077-observed-likelihood")
    try:
        started = perf_counter()
        process = subprocess.run(["taskset", "-c", str(cpu), binary, str(model), str(descriptor)],
                                 input=payload, capture_output=True, pass_fds=(model, descriptor), timeout=min(180, available))
        if process.returncode:
            raise RuntimeError(process.stderr.decode("utf-8", "replace"))
        report = json.loads(process.stdout)
        size = len(target) * frozen.VOCAB * 4
        if os.fstat(descriptor).st_size != size:
            raise RuntimeError("unexpected forced-logit matrix size")
        trace = os.pread(descriptor, size, 0)
    finally:
        os.close(descriptor)
    logits = np.frombuffer(trace, dtype="<f4").reshape(len(target), frozen.VOCAB).astype(np.float64)
    largest = logits.max(axis=-1)
    norm = largest + np.log(np.exp(logits - largest[:, None]).sum(axis=-1))
    logp = logits[np.arange(len(target)), target] - norm
    if not np.isfinite(logp).all():
        raise ValueError("invalid continuation score")
    result = dict(logp=logp.tolist(), sum=float(logp.sum()), greedy=report["ids"], kv_bytes=report["kv_bytes"],
                  logit_sha256=sha256(trace).hexdigest().upper(), seconds=perf_counter() - started)
    if resources:
        result["native"] = {key: report[key] for key in ("model_bytes", "scratch_bytes", "before", "loaded", "prefilled",
                                                             "complete", "seconds")}
    return result


def compare(row, binary, model, cpu, out, placement, *, resources=False):
    scores = []
    for ctx, target in zip(row["contexts"], row["targets"], strict=True):
        cut, fill = row["cut"], row["padding"]
        if placement == "near":
            ctx = fill + ctx
        elif placement == "far":
            ctx = ctx[:cut] + fill + ctx[cut:]
        elif placement == "masked":
            ctx = fill[:cut] + ctx[cut:]
        length = len(ctx) + len(target) - 1
        if placement in ("near", "far") and length != CONTEXT:
            raise ValueError("unmatched long context")
        scores.append(score(binary, model, ctx, target, cpu, out, resources=resources))
    signed = scores[row["gold"]]["sum"] - scores[1 - row["gold"]]["sum"]
    return dict(correct=signed > 0, margin=signed, choices=scores)


def admit(candidates, binaries, model, out):
    chosen, observed = [], []
    for task, rows in candidates.items():
        for gold in (0, 1):
            matched = [row for row in rows if row["gold"] == gold][:SHORT_LIMIT]
            count = 0
            for row in matched:
                a = compare(row, binaries["int8"], model, CPU_CORES[0], out, "short")
                b = compare(row, binaries["int8"], model, CPU_CORES[0], out, "masked")
                passed = a["margin"] >= 0.05 and a["margin"] - b["margin"] >= 0.10
                observed.append(dict(task=task, index=row["index"], gold=gold, short=a, masked=b, admitted=passed))
                if passed:
                    chosen.append(dict(row, short_margin=a["margin"], masked_margin=b["margin"]))
                    count += 1
                if count == CHOICES_PER_LABEL:
                    break
            print(f"P077_SHORT {task} gold={gold} admitted={count} available={len(matched)}", flush=True)
    publish(out / "short.json", observed)
    return chosen


def run_long(chosen, model, binaries, out):
    schedule = [(row, placement, mode) for row in chosen for placement in ("near", "far") for mode in binaries]
    rows_dir = out / "rows"
    rows_dir.mkdir()

    def worker(cpu, jobs):
        completed = []
        for row, placement, mode in jobs:
            result = compare(row, binaries[mode], model, cpu, out, placement)
            expected_kv = 11_859_456 if mode == "int8" else 9_106_944
            if any(choice["kv_bytes"] != expected_kv for choice in result["choices"]):
                raise ValueError("actual KV bytes do not match the selected precision")
            name = f"{row['task']}-{row['index']}-{placement}-{mode}"
            result.update(task=row["task"], index=row["index"], gold=row["gold"], placement=placement, mode=mode)
            publish(rows_dir / f"{name}.json", result)
            completed.append(result)
            print(f"P077_LONG {name} margin={result['margin']:+.6f}", flush=True)
        return completed

    with ThreadPoolExecutor(max_workers=len(CPU_CORES)) as workers:
        groups = [workers.submit(worker, cpu, schedule[i::len(CPU_CORES)]) for i, cpu in enumerate(CPU_CORES)]
        return [row for future in groups for row in future.result()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if (not out.is_relative_to(EVIDENCE) or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or datetime.now(CUTOFF.tzinfo) + timedelta(minutes=20) >= CUTOFF
            or not set(CPU_CORES).issubset(os.sched_getaffinity(0))):
        raise RuntimeError("CPU experiment scope or cutoff differs")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    bounded = native.bounded
    base = bounded.base
    reference = read(REFERENCE / "report.json")
    tokenizer_source = frozen.TOKENIZER.read_bytes()
    if sha256(tokenizer_source).hexdigest().upper() != frozen.TOKENIZER_SHA:
        raise ValueError("previous tokenizer identity differs")
    tokenizer = Tokenizer.from_str(tokenizer_source.decode("utf-8"))
    archived, scores, raw_sha = prior_scores()
    task_rows = {task: prepare_task(tokenizer, task, archived, scores[task]) for task in TASK_SOURCES}
    out.mkdir(exist_ok=False)
    with zipfile.ZipFile(out / "sources_at_execution.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for file in (Path(__file__), Path(native.__file__), bounded.ROOT / base.CPP,
                     ROOT / "scripts/p109_g4_grouped_int8_cache.hpp", ROOT / "scripts/p077_g4_grouped_attention.hpp"):
            archive.write(file, file.relative_to(ROOT).as_posix())
    binaries = {}
    source = (bounded.ROOT / base.CPP).read_bytes()
    for mode, precision in (("int8", 0), ("int4", 3)):
        folder = out / mode
        folder.mkdir()
        with patch.object(bounded, "OUT", folder):
            rendered = render_forcing(native.render(source, CONTEXT, precision, True, True))
            binaries[mode] = bounded.build(rendered, caps=(64,))[64][0]

    with ExitStack() as stack:
        original, model = (base.memfile(name) for name in ("p077-scoring-r4", "p077-scoring-r5"))
        for descriptor in (original, model):
            stack.callback(os.close, descriptor)
        profile = base.READ(bounded.text.OUT / "profile.json")["pins"]["candidate"]
        g4 = base.prior.load_candidate(profile)
        if base.model_blob(g4, original, profile["model_tensor_bytes"]) != reference["model"]:
            raise ValueError("frozen R4 model differs")
        identity = native.extend_positions(original, model, g4)
        if identity != reference["extended_model"]:
            raise ValueError("frozen R5 model differs")
        del g4

        old = read(REFERENCE / "english.json")
        proof = score(binaries["int4"], model, old["encoding"]["ids"], old["native"]["ids"], CPU_CORES[0], out)
        old_sha = read(REFERENCE / "independent_readback.json")["logits"]["sha256"]
        if proof["logit_sha256"] != old_sha or proof["greedy"] != old["native"]["ids"]:
            raise ValueError("forced-input transport did not reproduce the archived logits")
        print(f"P077_FORCED_ORACLE SHA256={old_sha}", flush=True)
        chosen = admit({task: value[0] for task, value in task_rows.items()}, binaries, model, out)
        for row in chosen:
            if len(row["padding"]) < 1024 or row["cut"] >= 1024:
                raise ValueError("near/far evidence does not cross the precision boundary")
        receipts = {task: value[1] for task, value in task_rows.items()}
        publish(out / "fixture.json", dict(tasks=receipts, model=identity, tokenizer=frozen.TOKENIZER_SHA,
                     old_scores_sha256=raw_sha, oracle=proof, chosen=chosen, planned_pairs=4 * len(chosen)))
        results = run_long(chosen, model, binaries, out)
    if torch.cuda.is_initialized() or len(results) != 4 * len(chosen):
        raise RuntimeError("the full CPU run did not close")
    publish(out / "report.json", dict(cpus=list(CPU_CORES), model=identity, selected=len(chosen), rows=results))


if __name__ == "__main__":
    main()
