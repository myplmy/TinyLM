"""Measure 1,024-token KV storage on the exact INT8 G4 deployment candidate."""

from datetime import datetime, timedelta
from hashlib import sha256
import os
from pathlib import Path
import resource
from statistics import median

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_g4_embedding_storage as embedding
from scripts.diag_p106b_resource_matrix import model_storage
from tinylm.data.prepare import load_tokenizer


TAG = "p109_g4_int8_kv1024_v1_20261119"
OUT = embedding.OUT.with_name(TAG)
ORIGIN = embedding.ORIGIN
DEPLOY = embedding.deploy
CONTEXT, GENERATED = 1017, 8
PRECISIONS = {
    "fp32": torch.float32,
    "fp16": torch.float16,
    "bf16": torch.bfloat16,
}
NOTES = {
    "english": (
        "For this exercise the orchard box has the label cedar. Keep this label for later.\n",
        ("A gardener cleaned the spade.", "One cart stood next to the gate.",
         "Fresh paper was placed on the counter.", "Rain slowed the delivery."),
        "\nWhich label is on the orchard box? Answer with the label only.\nAnswer:",
        "cedar",
    ),
    "korean": (
        "이 기록에서 정원 상자의 표지는 도토리다. 뒤에 물으면 이 표지를 답한다.\n",
        ("빗물 때문에 배달이 늦어졌다.", "작업자가 문을 닫고 의자를 옮겼다.",
         "정원사는 도구를 책상에 놓았다.", "기차는 다리를 천천히 건넜다."),
        "\n정원 상자의 표지는 무엇인가? 표지만 쓰시오.\n답:",
        "도토리",
    ),
}


def inputs(tokenizer):
    ids = torch.randint(35, 32768, (CONTEXT,), generator=torch.Generator().manual_seed(49653))
    cases = {"synthetic": (ids.tolist(), None)}
    for case, (intro, filler, query, label) in NOTES.items():
        lines = [f"{i + 1}. {filler[i % len(filler)]}" for i in range(160)]
        prefix = tokenizer.encode(intro + "\n".join(lines), add_special_tokens=False).ids
        suffix = tokenizer.encode(query, add_special_tokens=False).ids
        keep = CONTEXT - len(suffix)
        assert len(prefix) >= keep > len(tokenizer.encode(intro).ids)
        cases[case] = (prefix[:keep] + suffix, label)
    return cases


def contract():
    previous = embedding.verify()
    receipt = embedding.READ(embedding.OUT / "cpu_report.json")
    assert receipt["profile_sha256"] == embedding.SHA(embedding.OUT / "profile.json")
    assert receipt["arms"]["int8"]["effective_table_sha256"] == previous["table_sha256"]["int8"]
    return {
        "tag": TAG,
        "sources": {
            **previous["sources"],
            "scripts/diag_p109_g4_int8_kv1024.py": embedding.SHA(Path(__file__)),
        },
        "previous_cpu": embedding.SHA(embedding.OUT / "cpu_report.json"),
        "previous_profile": receipt["profile_sha256"],
        "table_sha256": previous["table_sha256"]["int8"],
        "model_tensor_bytes": receipt["arms"]["int8"]["model_tensor_bytes"],
        "checkpoint_step": previous["checkpoint_step"],
        "prefix_tokens": CONTEXT,
        "generated_tokens": GENERATED,
    }


def load_candidate(profile):
    origin, step = ORIGIN.load_model()
    assert step == profile["checkpoint_step"]
    assert origin.cfg.max_seq_len >= CONTEXT + GENERATED - 1
    payload = embedding.PACK.export_payload(
        origin, provenance={"tag": TAG}, head_rows=embedding.HEAD_ROWS
    )
    model = embedding.PACK.load_payload(payload)
    model.quantize_embedding("int8")
    model.cfg.emb_chunk = embedding.HEAD_ROWS
    digest = sha256()
    for start in range(0, model.cfg.vocab_size, embedding.HEAD_ROWS):
        tile = model._emb_rows(slice(start, start + embedding.HEAD_ROWS))
        digest.update(tile.contiguous().view(torch.uint8).numpy())
    assert digest.hexdigest().upper() == profile["table_sha256"]
    assert model_storage(model)["unique_storage_bytes"] == profile["model_tensor_bytes"]
    assert len(model.visit_schedule()) == 28
    return model


def trace(model, prompt, dtype):
    scores, shapes, ranges = [], [], []

    def observe(_module, _args, output):
        logits, cache = output
        assert logits.shape == (1, 1, model.cfg.vocab_size)
        pairs = list(cache.values())
        length = CONTEXT + len(shapes)
        assert len(pairs) == 14
        assert all(t.dtype == PRECISIONS[dtype] and t.shape[2] == length for pair in pairs for t in pair)
        finite = all(bool(torch.isfinite(t).all()) for pair in pairs for t in pair)
        assert finite and torch.isfinite(logits).all()
        shapes.append(length)
        ranges.append([max(float(pair[i].abs().amax()) for pair in pairs) for i in range(2)])
        scores.append(logits.flatten().detach().clone())

    model.cfg.kv_dtype = dtype
    with model.register_forward_hook(observe):
        result = DEPLOY.request(model, prompt, "", max_new=GENERATED, stop=False, audit=True)
    assert shapes == list(range(CONTEXT, CONTEXT + GENERATED))
    result["kv_tokens"] = shapes
    result["max_abs_key"] = max(key for key, value in ranges)
    result["max_abs_value"] = max(value for key, value in ranges)
    result["continuation"] = prompt.decode(result["ids"])
    return scores, result


def compare(reference, observed, ref_ids, ids):
    magnitudes = []
    first_change = None
    for step, (left, right) in enumerate(zip(reference, observed, strict=True)):
        magnitudes.append(float((left - right).abs().max()))
        if ref_ids[step] != ids[step]:
            first_change = step + 1
            break
    return {
        "first_changed_output": first_change,
        "compared_steps_with_common_history": len(magnitudes),
        "max_abs_logit_difference": max(magnitudes),
        "max_abs_by_step": magnitudes,
    }


@torch.inference_mode()
def run():
    profile = contract()
    OUT.mkdir(exist_ok=False)
    affinity = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {affinity})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    tokenizer = load_tokenizer("ko-en", 32768)
    cases = inputs(tokenizer)
    assert len({tuple(ids) for ids, _ in cases.values()}) == len(cases)
    assert all(len(ids) == CONTEXT for ids, _ in cases.values())
    baseline_memory = DEPLOY.snapshot()
    model = load_candidate(profile)
    loaded_memory = DEPLOY.snapshot()
    profile.update(
        affinity=affinity,
        cases={k: {"ids": ids, "expected_label": label} for k, (ids, label) in cases.items()},
    )
    embedding.WRITE(OUT / "profile.json", profile)
    rows = {}
    with DEPLOY.native_unpack(model) as native, sdpa_kernel(SDPBackend.MATH):
        for i, (case, (ids, _)) in enumerate(cases.items()):
            prompt = DEPLOY.PreparedPrompt(ids, tokenizer)
            order = tuple(PRECISIONS)
            audits = {dtype: trace(model, prompt, dtype) for dtype in order[i:] + order[:i]}
            ref_scores, ref = audits["fp32"]
            rows[case] = {dtype: record for dtype, (_, record) in audits.items()}
            for dtype, (scores, record) in audits.items():
                expected_bytes = CONTEXT + GENERATED - 1
                expected_bytes *= 14 * 2 * model.cfg.n_kv_heads * model.cfg.head_dim
                expected_bytes *= torch.empty((), dtype=PRECISIONS[dtype]).element_size()
                assert record["kv_sizes"][-1] == expected_bytes
                record["model_and_kv_bytes"] = profile["model_tensor_bytes"] + expected_bytes
                record["comparison_to_fp32"] = compare(ref_scores, scores, ref["ids"], record["ids"])
                check = record["comparison_to_fp32"]
                print("P109_KV1024_TRACE", case, dtype, expected_bytes,
                      check["max_abs_logit_difference"], check["first_changed_output"], flush=True)
        timings = {dtype: [] for dtype in PRECISIONS}
        prompt = DEPLOY.PreparedPrompt(cases["synthetic"][0], tokenizer)
        for order in (tuple(PRECISIONS), tuple(reversed(PRECISIONS))):
            for dtype in order:
                model.cfg.kv_dtype = dtype
                request = DEPLOY.request(model, prompt, "", max_new=GENERATED, stop=False, audit=False)
                assert request["ids"] == rows["synthetic"][dtype]["ids"]
                timings[dtype].append({
                    "wall": request["wall"],
                    "first_token": request["first_token"],
                    "decode_total": sum(request["decode"]),
                })
    assert not torch.cuda.is_initialized()
    assert contract() == {k: v for k, v in profile.items() if k not in ("affinity", "cases")}
    summary = {
        dtype: {key: median(r[key] for r in samples) for key in samples[0]}
        for dtype, samples in timings.items()
    }
    embedding.WRITE(OUT / "report.json", {
        "profile_sha256": embedding.SHA(OUT / "profile.json"),
        "requests": rows,
        "timings": timings,
        "timing_medians": summary,
        "loaded_memory": loaded_memory,
        "baseline_memory": baseline_memory,
        "experiment_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "native_body": native,
        "checkpoint_writes": 0,
        "cuda_initialized": False,
    })
    print("P109_KV1024_COMPLETE", summary, flush=True)


if __name__ == "__main__":
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("this deployment comparison requires CUDA_VISIBLE_DEVICES to be empty")
    if datetime.now(ORIGIN.CUTOFF.tzinfo) + timedelta(seconds=300) >= ORIGIN.CUTOFF:
        raise RuntimeError("insufficient time in the authorized window")
    run()
