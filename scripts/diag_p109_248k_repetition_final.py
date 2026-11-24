"""Test fixed P108B greedy penalties on two sealed 248K deployment candidates."""

import argparse
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
import json
import os
import subprocess
from time import perf_counter, time
from unittest.mock import patch

from tokenizers import Tokenizer
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_248k_long_text as long_text
from scripts import p108b_decode as decoders
from scripts import p108_weight_space as metrics
from scripts.p014e_packed_g128 import PackedGroupLinear


ROOT, io = long_text.ROOT, long_text.io
ce = long_text.prior.learned
TAG = "p109_248k_long_decoder_final192_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
PANEL = ROOT / "test_result/evidence/p108b_layer_transfer_v2_s1337/final_language.json"
PANEL_RECEIPT = PANEL.with_name("evaluation_profile_v1.json")
PENALTIES = {d.name: d.repetition_penalty for d in decoders.registered() if d.temperature == 0}
MAX_NEW, MAX_BATCH = 64, 16


def window(seconds=0):
    if time() + seconds >= long_text.CUTOFF or (OUT / "STOP").exists():
        raise RuntimeError("approved execution window or the owned stop marker")


def device_bound():
    window()
    free, total = torch.cuda.mem_get_info()
    if total - free > 13_000_000_000:
        raise RuntimeError("device use crossed the 13 GB operating boundary")


def prepare():
    window()
    if OUT.exists():
        raise FileExistsError(OUT)
    assets = long_text.model_sources()
    receipt, panel = io.load(PANEL_RECEIPT), io.load(PANEL)
    if (io.digest(PANEL) != receipt["final_data_sha256"] or
            panel["role"] != "FINAL_EVALUATION_ONLY_NOT_EDITOR_INPUT" or
            PENALTIES != {"GREEDY": 1., "GREEDY_R110": 1.1, "GREEDY_R120": 1.2}):
        raise ValueError("original held prompts or registered penalties differ")
    tok_receipt = io.load(ce.qwen.ASSET)["assets"]["qwen35_hf"]
    tokenizer_path = ROOT / tok_receipt["path"]
    if io.digest(tokenizer_path) != tok_receipt["file_sha256"]:
        raise ValueError("Qwen tokenizer SHA differs")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    if tokenizer.get_vocab_size() != ce.ASSIGNED or tokenizer.token_to_id("<|endoftext|>") != ce.EOS:
        raise ValueError("assigned IDs or EOS differ")
    rows = panel["rows"]
    if (len(rows) != 192 or len({r["id"] for r in rows}) != 192 or
            {r["split"] for r in rows} != {"final_test"} or
            sum(r["expected"] is not None for r in rows) != 128 or
            any(sum(r["language"] == lang for r in rows) != 96 for lang in ("en", "ko"))):
        raise ValueError("the same 192 first prompts and 128 gold responses are required")
    buckets = defaultdict(list)
    for row in rows:
        en = row["language"] == "en"
        question = row["question"]
        prompt = f"Question: {question}\nAnswer:" if en else f"질문: {question}\n답변:"
        ids = tokenizer.encode(prompt, add_special_tokens=False).ids
        if (not 0 < len(ids) <= 256 or ce.EOS in ids or
                any(not 0 <= i < ce.ASSIGNED for i in ids)):
            raise ValueError("first prompt token range or length differs")
        buckets[len(ids)].append(dict(row, ids=ids))
    batches = []
    for width, items in sorted(buckets.items()):
        limit = min(MAX_BATCH, 1024 // width)
        batches.extend(items[start:start + limit] for start in range(0, len(items), limit))
    files = {Path(__file__), long_text.PLAN, PANEL, PANEL_RECEIPT, Path(long_text.__file__),
             Path(decoders.__file__), Path(metrics.__file__), tokenizer_path, ce.qwen.ASSET,
             ROOT / "scripts/p014e_packed_g128.py", ROOT / "tinylm/model/transformer.py",
             ROOT / "tinylm/model/modules.py", *(f for pair in long_text.MODELS.values() for f in pair)}
    sources = {str(path.relative_to(ROOT)): io.digest(path) for path in sorted(files)}
    if torch.cuda.is_initialized():
        raise ValueError("preparation initialized CUDA")
    OUT.mkdir()
    io.write(PROFILE, dict(tag=TAG, approval="WIP176", sources=sources, assets=assets,
                         tokenizer=str(tokenizer_path.relative_to(ROOT)), penalties=PENALTIES,
                         max_new=MAX_NEW, batches=batches, row_count=len(rows), strict_rows=128))
    print("P109_REPETITION_READY", len(rows), len(batches), max(buckets), flush=True)


def load_profile():
    profile = io.load(PROFILE)
    if any(io.digest(ROOT / p) != v for p, v in profile["sources"].items()):
        raise ValueError("a sealed input or source changed")
    return profile


def install_tiles(model, stack):
    """Keep the original packed forward's arithmetic and tile sizes."""
    count = 0
    for module in model.modules():
        if isinstance(module, PackedGroupLinear):
            rows = {(a, min(a + module.tile_rows, module.out_f)): module.unpack_rows(
                     a, min(a + module.tile_rows, module.out_f))
                    for a in range(0, module.out_f, module.tile_rows)}
            stack.enter_context(patch.object(module, "unpack_rows", lambda a, b, tiles=rows: tiles[a, b]))
            count += 1
    table = model.packed_embedding
    get_rows = table.rows
    embedding = {a: get_rows(slice(a, min(a + table.head_rows, table.vocab_size)))
                 for a in range(0, table.vocab_size, table.head_rows)}

    def cached_lookup(index):
        if isinstance(index, slice):
            return embedding[index.start]
        return get_rows(index)

    stack.enter_context(patch.object(table, "rows", cached_lookup))
    if count != 69:
        raise ValueError("shared body physical matrix count differed")
    return count, len(embedding)


def two_steps(model, tokens):
    values = []
    cache = None
    for _ in range(2):
        scores, cache = model(tokens, past_kv=cache, use_cache=True, logits_last_only=True)
        scores = scores[:, -1, :ce.ASSIGNED]
        tokens = scores.argmax(dim=-1, keepdim=True)
        values.append((scores, cache))
    return values


def prove_tiles(actual, expected):
    for (scores, cache), (old_scores, old_cache) in zip(actual, expected, strict=True):
        if not torch.equal(scores, old_scores) or set(cache) != set(old_cache) or len(cache) != 14:
            raise ValueError("cached output tiles changed real deployed logits or owner slots")
        for key, tensor_pair in cache.items():
            if any(not torch.equal(a, b) or a.dtype != torch.float32
                   for a, b in zip(tensor_pair, old_cache[key], strict=True)):
                raise ValueError("FP32 key/value cache identity changed")


def generate(model, rows, penalty):
    tokens = torch.tensor([row["ids"] for row in rows], dtype=torch.long, device="cuda")
    count = len(rows)
    cache = None
    output = []
    done = torch.zeros((count, 1), dtype=torch.bool, device="cuda")
    seen = torch.zeros((count, ce.ASSIGNED), dtype=torch.bool, device="cuda") if penalty != 1 else None
    for _ in range(MAX_NEW):
        scores, cache = model(tokens, past_kv=cache, use_cache=True, logits_last_only=True)
        scores = scores[:, -1, :ce.ASSIGNED]
        if seen is not None:
            scores = torch.where(seen, torch.where(scores < 0, scores * penalty, scores / penalty), scores)
        chosen = scores.argmax(dim=-1, keepdim=True)
        tokens = torch.where(done, ce.EOS, chosen)
        done = done | tokens.eq(ce.EOS)
        if seen is not None:
            seen.scatter_(1, tokens, ~done)
        output.append(tokens)
        if bool(done.all()):
            break
    return torch.cat(output, dim=1).tolist()


def run_model(name, profile):
    candidate = long_text.MODELS[name][0]
    model = ce.load_payload(torch.load(candidate, map_location="cpu", weights_only=True),
                            device="cuda", tile_rows=4096)
    model.cfg.kv_dtype = "fp32"
    route = list(model.visit_schedule())
    if route != list(range(14)) + list(range(2, 16)):
        raise ValueError("inference visits differ from the deployed R2")
    tokenizer = Tokenizer.from_file(str(ROOT / profile["tokenizer"]))
    batches = profile["batches"]
    probe = torch.tensor([v["ids"] for v in batches[0]], dtype=torch.long, device="cuda")
    previous = two_steps(model, probe)
    raw = []
    with ExitStack() as changes:
        matrix_count, embedding_tiles = install_tiles(model, changes)
        prove_tiles(two_steps(model, probe), previous)
        del previous, probe
        for policy, penalty in PENALTIES.items():
            device_bound()
            path = OUT / f"{name}_{policy}.jsonl"
            started = perf_counter()
            with path.open("x", encoding="utf-8") as stream:
                for index, batch in enumerate(batches, 1):
                    device_bound()
                    result = generate(model, batch, penalty)
                    for row, ids in zip(batch, result, strict=True):
                        end = ids.index(ce.EOS) if ce.EOS in ids else len(ids)
                        stopped = end != len(ids)
                        ids = ids[:end]
                        answer = tokenizer.decode(ids, skip_special_tokens=True)
                        exact = None if row["expected"] is None else metrics.exact_answer(answer, row["expected"])
                        details = metrics.repetition_metrics(ids, answer, row["question"])
                        value = dict(id=row["id"], language=row["language"], protected=row["protected"],
                                     family=row["family"], ids=ids, answer=answer, exact=exact,
                                     diagnostics=details, finish="EOS" if stopped else "MAX_NEW")
                        print(json.dumps(value, ensure_ascii=False, allow_nan=False), file=stream, flush=True)
                    if index % 16 == 0 or index == len(batches):
                        print("P109_REPETITION_PROGRESS", name, policy, index, len(batches), flush=True)
            raw.append(dict(policy=policy, reply_sha256=io.digest(path), seconds=perf_counter() - started))
    return dict(physical_matrices=matrix_count, embedding_tiles=embedding_tiles, bitwise_tile_check=True,
                route=route, files=raw, checkpoint_writes=0)


def gpu(name):
    window(580)
    if not ce.idle() or torch.cuda.device_count() != 1 or torch.cuda.mem_get_info()[0] < 4 * 2**30:
        raise RuntimeError("one idle selected GPU and 4 GiB free required")
    profile = load_profile()
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    device = OUT / f"{name}_device_100ms.csv"
    with device.open("xb") as stream:
        sampler = subprocess.Popen((*ce.DEVICE, f"--loop-ms={ce.INTERVAL_MS}"), stdout=stream)
        try:
            with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
                result = run_model(name, profile)
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    samples = ce.read_samples(device)
    if not samples:
        raise RuntimeError("empty device trace")
    load_profile()
    result.update(device_peak=max(samples, key=lambda row: row["occupied_mib"]),
                  device_samples=len(samples), device_sha256=io.digest(device), profile_sha256=io.digest(PROFILE))
    io.write(OUT / f"{name}_result.json", result)
    print("P109_REPETITION_DONE", name, result["device_peak"], flush=True)


def summarize():
    profile = load_profile()
    expected = {row["id"]: row for batch in profile["batches"] for row in batch}
    result = {}
    for name in long_text.MODELS:
        binding = io.load(OUT / f"{name}_result.json")
        if (binding["profile_sha256"] != io.digest(PROFILE) or
                binding["device_sha256"] != io.digest(OUT / f"{name}_device_100ms.csv")):
            raise ValueError("candidate results differ from saved receipts")
        result[name] = dict(device=binding, arms={})
        correct_base = set()
        for file in binding["files"]:
            policy = file["policy"]
            path = OUT / f"{name}_{policy}.jsonl"
            if io.digest(path) != file["reply_sha256"]:
                raise ValueError("raw verbose outputs differ")
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            if len(rows) != len(expected) or {r["id"] for r in rows} != set(expected):
                raise ValueError("reply coverage differs")
            for row in rows:
                ref = expected[row["id"]]
                gold = ref["expected"]
                exact = None if gold is None else metrics.exact_answer(row["answer"], gold)
                if (row["exact"] != exact or row["diagnostics"] !=
                        metrics.repetition_metrics(row["ids"], row["answer"], ref["question"])):
                    raise ValueError("strict score, echo or loop could not be replayed")
            correct = {r["id"] for r in rows if r["exact"]}
            if policy == "GREEDY":
                correct_base = correct
            summary = {}
            for lang in ("en", "ko"):
                selected = [r for r in rows if r["language"] == lang]
                summary[lang] = dict(replies=len(selected), correct=sum(bool(r["exact"]) for r in selected),
                                    protected_correct=sum(bool(r["exact"]) and r["protected"] for r in selected),
                                    loops=sum(bool(r["diagnostics"]["loop_indicator"]) and
                                              not (r["protected"] and r["exact"]) for r in selected),
                                    echoes=sum(r["diagnostics"]["question_echo"] for r in selected),
                                    empty=sum(r["diagnostics"]["empty"] for r in selected),
                                    eos=sum(r["finish"] == "EOS" for r in selected))
            result[name]["arms"][policy] = dict(languages=summary, lost=sorted(correct_base - correct),
                                                gained=sorted(correct - correct_base), gpu_seconds=file["seconds"])
    io.write(OUT / "report.json", result)
    for name, record in result.items():
        print("P109_REPETITION_RECOUNT", name, record["arms"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "summarize"))
    parser.add_argument("--model", choices=tuple(long_text.MODELS))
    args = parser.parse_args()
    uses_gpu = args.mode == "run"
    if uses_gpu != (args.model is not None) or os.environ.get("CUDA_VISIBLE_DEVICES") != ("0" if uses_gpu else ""):
        parser.error("run selects one model and GPU 0, CPU modes require isolation")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if args.mode == "prepare":
        prepare()
    elif args.mode == "summarize":
        summarize()
    else:
        gpu(args.model)


if __name__ == "__main__":
    main()
