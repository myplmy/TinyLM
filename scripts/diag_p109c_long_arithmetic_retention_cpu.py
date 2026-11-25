"""Measure trained long-answer retention and KV memory across frozen input lengths."""

from argparse import ArgumentParser
import ctypes
from datetime import datetime
import gc
import json
import os
from pathlib import Path
from time import monotonic, time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_kv_owner_stream_cpu as streaming
from scripts import diag_p109c_seen_long_answers_cpu as bare


REF = bare.REF
PRE = streaming.previous
OUT = REF.EVIDENCE / "p109c_long_arithmetic_retention_cpu_20261126"
END = datetime.fromisoformat("2026-11-26T06:48:00+09:00")
ARMS = {
    "bare_fp32": ("bare", 1024, "fp32"),
    "medium_fp32": ("medium", 1024, "fp32"),
    "long_fp32": ("long", 2048, "fp32"),
    "long_bf16": ("long", 2048, "bf16"),
    "long_bf16_owner": ("long", 2048, "bf16"),
}
BACKGROUND = {
    "ko": (
        "나무 사이로 바람이 지나가고 낮은 가지 위에 작은 잎이 흔들립니다.",
        "바닷가에 밀려온 물이 모래를 적시고 바위 옆에 얕은 웅덩이를 남깁니다.",
        "비가 그친 뒤 좁은 흙길 가장자리에서 젖은 풀 냄새가 납니다.",
        "구름 사이로 들어온 햇빛이 숲 바닥과 돌 표면을 비춥니다.",
        "언덕 아래 보이는 지붕은 안개가 걷히면서 천천히 선명해집니다.",
        "정원에 핀 꽃가루가 공중에 떠다니고 벽 옆이 그늘집니다.",
        "들판의 마른 풀은 바람이 약해지자 다시 제자리에 섭니다.",
        "낮이 끝날 무렵 잔잔한 호수에 하늘과 나무의 모습이 비칩니다.",
    ),
    "en": (
        "Wind passes through the trees and small leaves stir on the low branches.",
        "A tide dampens the sandy shore and leaves shallow pools beside the rocks.",
        "After the rain, damp grass scents the edge of a narrow earthen trail.",
        "Sunlight through the clouds reaches the forest floor and the stones.",
        "The roofs below the hill come into view as the haze gradually lifts.",
        "Pollen drifts through the garden and the space beside the wall is shaded.",
        "Dry grass in the meadow settles as the wind begins to ease.",
        "The still lake reflects the sky and the trees toward the end of the day.",
    ),
}


def padded(tokenizer, case):
    enc = lambda value: tokenizer.encode(value, add_special_tokens=False).ids
    lang = case["language"]
    header = enc("<|im_start|>user\n")
    confirmation = "확인했습니다." if lang == "ko" else "Acknowledged."
    suffix = enc(f"<|im_end|>\n<|im_start|>assistant\n{confirmation}<|im_end|>\n") + case["ids"]
    blocks = [enc(line + "\n") for line in BACKGROUND[lang]]
    count = 1792 - len(header) - len(suffix)
    repetitions = 1 + count // sum(map(len, blocks))
    background = (sum(blocks, []) * repetitions)[-count:]
    result = {"bare": case["ids"]}
    for name, target in (("medium", 896), ("long", 1792)):
        width = target - len(header) - len(suffix)
        result[name] = header + background[-width:] + suffix
        if len(result[name]) != target or result[name][-len(case["ids"]):] != case["ids"]:
            raise ValueError("the common prompt suffix and target need to remain exact")
    if result["medium"][len(header):] != result["long"][-(896-len(header)):]:
        raise ValueError("the medium history needs to match the same final long history")
    return result


def prepare(tokenizer):
    in_path, out_path = (bare.OUT / name for name in ("inputs.json", "report.json"))
    inputs, previous = map(REF.completed.read_json, (in_path, out_path))
    if (previous["status"] != "COMPLETE" or previous["input_sha256"] != REF.file_sha(in_path)
            or inputs["body_sha256"] != REF.CHECKPOINT_SHA256
            or inputs["source_sha256"] != REF.file_sha(Path(bare.__file__))):
        raise ValueError("the retained short answer must come from the frozen v3 positive check")
    positive = {row["id"]: row for row in previous["rows"] if row["usable"] and row["exact_ids"]}
    cases = []
    for lang, group in inputs["cases"].items():
        chosen = sorted((case for case in group if case["id"] in positive), key=lambda case: case["id"])[:3]
        if len(chosen) != 3:
            raise ValueError("three ID-exact positive controls per language are required")
        for case in chosen:
            cases.append(dict(case, input_variants=padded(tokenizer, case), prior=positive[case["id"]]["metadata"]))
    return cases, REF.file_sha(out_path)


class ChunkedCalls:
    def __init__(self, target, cfg, cutoff):
        self.target, self.cfg, self.cutoff = target, cfg, cutoff
        self.prefill_seconds, self.prefill_cache, self.final_cache = 0., 0, 0

    def __call__(self, tokens, *, past_kv, **options):
        if past_kv is None:
            begin = monotonic()
            for block in tokens.split(PRE.CHUNK, dim=1):
                self.check_time()
                logits, past_kv = self.target(block, past_kv=past_kv, **options)
            self.prefill_seconds = monotonic() - begin
            self.prefill_cache = PRE.cache_size(past_kv)
        else:
            self.check_time()
            logits, past_kv = self.target(tokens, past_kv=past_kv, **options)
        self.final_cache = PRE.cache_size(past_kv)
        return logits, past_kv

    def check_time(self):
        if time() >= self.cutoff:
            raise TimeoutError("the long answer comparison reached its CPU cutoff")


@torch.inference_mode()
def run(cases, tokenizer, cutoff):
    trim = ctypes.CDLL(None).malloc_trim
    trim.argtypes, trim.restype = [ctypes.c_size_t], ctypes.c_int
    model = streaming.model_for("long_bf16")
    highest = 0

    def observe(*_):
        nonlocal highest
        highest = max(highest, PRE.memory()["VmRSS"])

    hooks = [layer.register_forward_hook(observe) for layer in model.layers]
    results = {}
    try:
        for index, case in enumerate(cases):
            rows = {}
            order = tuple(ARMS) if index % 2 == 0 else tuple(reversed(ARMS))
            for arm in order:
                variant, model.cfg.max_seq_len, model.cfg.kv_dtype = ARMS[arm]
                target = streaming.OwnerStream(model) if arm == "long_bf16_owner" else model
                wrapped = ChunkedCalls(target, model.cfg, cutoff)
                gc.collect()
                trim(0)
                initial = highest = PRE.memory()["VmRSS"]
                begin = monotonic()
                row = bare.score(wrapped, tokenizer, dict(case, ids=case["input_variants"][variant]))
                peak = max(highest, PRE.memory()["VmRSS"])
                row.update(sampled_rss_peak=peak, initial_rss=initial, growth=peak-initial,
                           prefill_kv_bytes=wrapped.prefill_cache, final_kv_bytes=wrapped.final_cache,
                           prefill_seconds=wrapped.prefill_seconds, seconds=monotonic()-begin)
                rows[arm] = row
                del wrapped, target
            results[case["id"]] = rows
            if not rows["bare_fp32"]["usable"] or identity(rows["bare_fp32"]["metadata"]) != identity(case["prior"]):
                raise ValueError("the short FP32 path failed to reproduce the admitted positive answer")
            REF.native.publish(OUT / f"{case['id']}.json", rows)
            print(case["language"], case["id"][:12], {key: row["usable"] for key, row in rows.items()}, flush=True)
    finally:
        for hook in hooks:
            hook.remove()
    return results


def identity(meta):
    return meta["generated_ids"], meta["finish_reason"]


def summarize(results):
    by_arm = {
        arm: dict(usable=sum(rows[arm]["usable"] for rows in results.values()),
                  max_sampled_rss=max(rows[arm]["sampled_rss_peak"] for rows in results.values()),
                  max_growth=max(rows[arm]["growth"] for rows in results.values()))
        for arm in ARMS
    }
    pairs = [(rows["long_bf16"], rows["long_bf16_owner"]) for rows in results.values()]
    parity = sum(identity(a["metadata"]) == identity(b["metadata"]) for a, b in pairs)
    saved = [a["sampled_rss_peak"] - b["sampled_rss_peak"] for a, b in pairs]
    meets_memory = by_arm["long_bf16_owner"]["max_sampled_rss"] <= by_arm["medium_fp32"]["max_sampled_rss"]
    return dict(arms=by_arm, cases=len(results), owner_parity=parity, owner_peak_rss_savings_bytes=saved,
                medium_memory_met=meets_memory, candidate_met=meets_memory and parity == len(results)
                and by_arm["long_bf16_owner"]["usable"] == len(results))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 and return before the matched raw validation phase")
    tokenizer = REF.completed.load_tokenizer()
    cases, source = prepare(tokenizer)
    body = REF.checkpoint()
    OUT.mkdir(exist_ok=False)
    inputs = OUT / "inputs.json"
    REF.native.publish(inputs, dict(cases=cases, arms=ARMS, window=args.stop_by.isoformat(), training_positive_sha=source,
                                    background=BACKGROUND, source_sha256=REF.file_sha(Path(__file__)),
                                    model_sha256=REF.CHECKPOINT_SHA256, chunk=PRE.CHUNK, max_new=PRE.MAX_NEW,
                                    owner_source=REF.file_sha(Path(streaming.__file__))))
    with sdpa_kernel(SDPBackend.MATH):
        results = run(cases, tokenizer, args.stop_by.timestamp())
    if REF.file_sha(body) != REF.CHECKPOINT_SHA256:
        raise ValueError("v3 model bytes changed")
    summary = summarize(results)
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=REF.file_sha(inputs), summary=summary))
    print("P109C_LONG_ARITHMETIC_RETENTION", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
