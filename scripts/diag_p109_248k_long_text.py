"""Measure a long, complete native request on the sealed P109 packed models."""

from contextlib import ExitStack
import os
from pathlib import Path
from statistics import median
import struct
import subprocess
from time import time
from types import SimpleNamespace
from unittest.mock import patch

import torch

from scripts import diag_p109_qwen_248k_text as prior
from scripts import diag_p109_qwen35_248k_scale_calibration as tuned
from scripts.p109_compact_qwen_tokenizer import CompactQwenTokenizer


ROOT, engine, io = prior.ROOT, prior.engine, prior.io
TAG = "p109_248k_long256_text_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
CE = OUT.with_name("p109_qwen_248k_ce_scale_matched_v1_20261119")
MODELS = {
    "ce_48": (CE / "ce_calibrated_5trit.pt", CE / "train.json"),
    "kd_48": (tuned.EXPORT, tuned.OUT / "report.json"),
}
PLAN = ROOT / "test_plan/P109_16층-공유-재귀-프리셋-통합.md"
PREFIX, GENERATE, LIMIT = 768, 256, 1024
CUTOFF = prior.learned.parent.CUTOFF.timestamp()


def authority(seconds=0):
    if time() + seconds >= CUTOFF or (OUT / "STOP").exists():
        raise RuntimeError("outside the approved execution window or stop marker exists")


def model_sources():
    assets = {}
    for name, (payload, receipt) in MODELS.items():
        observed = io.load(receipt)
        digest = io.digest(payload)
        if observed["packed_sha256"] != digest or len(observed["history"]) != tuned.STEPS:
            raise ValueError(f"packed calibration receipt differs for {name}")
        assets[name] = dict(path=str(payload.relative_to(ROOT)), sha256=digest,
                            receipt=str(receipt.relative_to(ROOT)), history=len(observed["history"]))
    return assets


def requests():
    source = io.load(io.LONG)["runs"]["split_model"][0]["outputs"]
    if io.digest(prior.TOKENIZER) != io.load(io.OUT / "profile.json")["compact_sha256"]:
        raise ValueError("compiled 248K tokenizer differs from its full vocabulary proof")
    planned = {}
    with CompactQwenTokenizer(prior.TOKENIZER) as tokenizer:
        for language in ("english", "korean"):
            sequence = tokenizer.encode((source[language]["decoded"] + "\n") * 3).ids
            ids = sequence[:PREFIX]
            text = tokenizer.decode(ids, skip_special_tokens=False)
            if (len(ids) != PREFIX or tokenizer.encode(text).ids != ids or
                    any(not 0 <= u < prior.learned.ASSIGNED for u in ids)):
                raise ValueError(f"exact length or roundtrip differs for {language}")
            planned[language] = dict(text=text, ids=ids)
    return planned


def render():
    for source in prior.render():
        source = engine.replace(source, b"generate <= 8", f"generate <= {GENERATE}".encode("ascii"))
        source = engine.replace(source, b"std::array<uint32_t,8> ids",
                                f"std::array<uint32_t,{GENERATE}> ids".encode("ascii"))
        yield engine.replace(source, b"std::array<double,8> times",
                             f"std::array<double,{GENERATE}> times".encode("ascii"))


def worker_source():
    source = Path(prior.text.__file__).read_bytes()
    source = engine.replace(source, b"ROOT = Path(__file__).resolve().parents[1]",
                            f"ROOT = Path({str(ROOT)!r})".encode("utf-8"))
    return engine.replace(source, b"GEN = common.GEN", f"GEN = {GENERATE}".encode("ascii"))


def checks(binary):
    bad_shapes = ((1, GENERATE + 1), (LIMIT, GENERATE), (PREFIX, 0))
    proofs = []
    for prefix, count in bad_shapes:
        proc = subprocess.run([str(binary), "-1", "-1"], input=struct.pack("<2I", prefix, count),
                              capture_output=True, timeout=8)
        if proc.returncode != 1 or b"unsupported request shape" not in proc.stderr:
            raise ValueError("out-of-contract request was not rejected before model mapping")
        proofs.append(dict(prefix=prefix, requested=count, actual_exit=proc.returncode))
    return proofs


def compare(binary, reference, worker, assets, name, language, request):
    authority()
    counterfactual, _ = engine.native(reference, assets[0], request["ids"], GENERATE)
    with patch.object(engine, "OUT", OUT), patch.object(engine, "text", SimpleNamespace(__file__=worker)):
        row = engine.full_request(binary, assets, request["text"].encode("utf-8"),
                                  f"{name}_{language}", 1)
    ids, base = row["ids"], counterfactual["ids"]
    if (row.pop("source_ids") != request["ids"] or len(ids) != len(row["step_seconds"])
            or not 0 < len(ids) <= GENERATE or not 0 < len(base) <= GENERATE):
        raise ValueError("request tokenization, generated IDs or per-step record differs")
    if any(not 0 <= token < prior.learned.ASSIGNED for token in ids + base):
        raise ValueError("decoder emitted unassigned IDs")
    for sequence in (ids, base):
        stopped = sequence[-1] == prior.learned.EOS
        if ((len(sequence) < GENERATE and not stopped) or
                prior.learned.EOS in sequence[:-1]):
            raise ValueError("greedy request did not honor the length/EOS contract")
    shared = next((i for i, pair in enumerate(zip(ids, base)) if pair[0] != pair[1]),
                  min(len(ids), len(base)))
    row.update(emitted=len(ids), reference_emitted=len(base), reference_ids=base,
               reference_step_seconds=counterfactual["seconds"],
               reference_peak=max(counterfactual[phase][key] for phase in
                                  ("before", "loaded", "prefilled", "complete") for key in ("rss", "vm_hwm")),
               same_output=ids == base, same_prefix_tokens=shared,
               first_difference=None if ids == base else shared + 1,
               first_token_seconds=row["step_seconds"][0],
               tail_32_median_seconds=median(row["step_seconds"][max(1, len(ids)-32):]) if len(ids)>1 else None)
    print("P109_LONG_REQUEST", name, language, row["emitted"], row["peak"],
          row["same_prefix_tokens"], round(row["seconds"], 3), flush=True)
    return row


@torch.inference_mode()
def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("the long-text deployment witness requires isolated CPU")
    authority(460)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    info, planned = model_sources(), requests()
    worker = OUT / "long_text_worker.py"
    paths = {Path(__file__), PLAN, Path(prior.__file__), Path(prior.text.__file__),
             Path(engine.__file__), engine.BODY, engine.LOOKUP, engine.EXTENSION, engine.SCALAR,
             prior.WRAPPER, ROOT / "scripts/p109_g4_grouped_int8_cache.hpp",
             ROOT / "scripts/p109_g270_text_exec.py", ROOT / "scripts/p109_compact_qwen_tokenizer.py",
             prior.TOKENIZER, io.LONG, *(f for pair in MODELS.values() for f in pair)}
    pins = {str(p.relative_to(ROOT)): io.digest(p) for p in sorted(paths)}
    OUT.mkdir()
    with worker.open("xb") as stream:
        stream.write(worker_source())
    pins[str(worker.relative_to(ROOT))] = io.digest(worker)
    io.write(OUT / "profile.json", dict(tag=TAG, approval="WIP176", sources=pins, assets=info,
             profile_context=LIMIT, request_prefix=PREFIX, generation_cap=GENERATE, requests=planned))
    print("P109_LONG_READY", list(info), list(planned), PREFIX, GENERATE, flush=True)
    with (patch.object(engine, "OUT", OUT), patch.object(engine, "render", render),
          patch.object(engine, "WRAPPER", prior.WRAPPER)):
        reference, int8, worker_bin = engine.compile_binaries()
    rejections = checks(int8)
    results = {}
    model_artifacts = {}
    with ExitStack() as stack:
        tok = engine.prefill.base.memfile("p109_long_tok")
        stack.callback(os.close, tok)
        engine.text.store(tok, prior.TOKENIZER.read_bytes())
        engine.seal(tok)
        for name, (asset, _) in MODELS.items():
            with ExitStack() as candidate:
                fd = engine.prefill.base.memfile(f"p109_long_{name}")
                candidate.callback(os.close, fd)
                model = prior.learned.load_payload(torch.load(asset, map_location="cpu", weights_only=True),
                                                   device="cpu", tile_rows=4096)
                model.cfg.kv_dtype = "fp32"
                model_artifacts[name] = prior.serialize(model, fd)
                del model
                results[name] = {}
                for language, request in planned.items():
                    row = compare(worker_bin, reference, worker, (fd, tok), name, language, request)
                    if row["model_bytes"] != model_artifacts[name]["bytes"]:
                        raise ValueError("native mapped model size differed")
                    results[name][language] = row
    if torch.cuda.is_initialized() or any(io.digest(ROOT / p) != sha for p, sha in pins.items()):
        raise ValueError("a pinned source changed or CUDA initialized")
    io.write(OUT / "report.json", dict(tag=TAG, requests=results, guards=rejections,
             assets=model_artifacts, highest_rss=max(r["peak"] for rows in results.values() for r in rows.values()),
             source_preserved=True, cuda_initialized=False, checkpoint_writes=0))


if __name__ == "__main__":
    main()
