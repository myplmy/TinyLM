"""Collect frozen FINAL200 first responses from the three local P109C comparators."""

import argparse
from contextlib import contextmanager
import ctypes as C
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import time

from scripts import diag_p106b_external_core6 as hf_assets
from scripts import diag_p106b_final_holdout as holdout
from scripts import diag_p106b_hf_resources as hf_generation
from scripts import diag_p106b_prism_native_raw as prism
from scripts import diag_p106b_qwen35_text_core6 as qwen
from scripts import eval_p109c_completed as frozen
from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
from scripts.p106b_shards import ShardWriter, verify


ROOT = frozen.ROOT
EVIDENCE = ROOT / "test_result/evidence"
PANEL = EVIDENCE / "p109c_comparator_assets_cpu_v1_20261121/report.json"
MODELS = ("gemma270", "qwen3508", "bonsai2b")
AUTHORITY = datetime.fromisoformat("2026-11-25T17:00:00+09:00").timestamp()
CONTEXT = 1024


def read_inputs(model):
    cases, contract = frozen.final200_inputs()
    model_spec = frozen.read_json(PANEL)["panel"][model]
    for field in ("weights", "tokenizer", "config"):
        entry = model_spec.get(field)
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        path = (ROOT / entry["path"]).resolve(strict=True)
        if (not path.is_relative_to((ROOT / "HF").resolve()) or not path.is_file()
                or path.stat().st_size != entry["bytes"] or prism.digest(path) != entry["sha256"]):
            raise ValueError(f"original external {model} {field} changed")
    if model == "bonsai2b":
        assets = prism.verify()
        old = frozen.read_json(prism.ASSETS)
        if (old["model"] != model_spec["weights"]["path"]
                or old["model_sha256"] != model_spec["weights"]["sha256"]
                or prism.digest(prism.ASSETS) not in assets["pins"].values()):
            raise ValueError("qualified Prism profile and P109C Bonsai must use the same GGUF")
        assets = dict(bundle=old["bundle"], model=old["model"], vocab=assets["vocab"],
                      profile_sha256=prism.digest(prism.PROFILE))
    else:
        assets = qwen.asset_identity() if model == "qwen3508" else hf_assets.asset_identity(model)
        key = qwen.WEIGHT if model == "qwen3508" else hf_assets.REGISTRY[model]["weight"]
        if (assets["files"][key]["sha256"] != model_spec["weights"]["sha256"]
                or assets["revision"] != model_spec["revision"]):
            raise ValueError("original comparator and loader asset pins differ")
    return cases, dict(final200=contract, model=model, model_spec=model_spec,
                       comparator_panel_sha256=prism.digest(PANEL),
                       source_sha256=prism.digest(Path(__file__)),
                       max_new=holdout.data.MAX_NEW, context=CONTEXT,
                       prompt_policy="verbatim question, localized Question/Answer delimiters, model BOS policy",
                       decoding="greedy, natural end token or hard ceiling, no response truncation",
                       routed_inference=("Prism PTQ1_0 all GPU layers and incremental KV" if model == "bonsai2b"
                                         else "HF eager FP32 TF32 off and cached greedy")), assets


def render(case):
    question, answer = ("질문", "답변") if case["language"] == "ko" else ("Question", "Answer")
    return f"{question}: {case['prompt']}\n{answer}:"


@contextmanager
def hf_runtime(model, assets, proof):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Qwen3_5ForCausalLM, Qwen3_5TextConfig

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    options = dict(local_files_only=True, trust_remote_code=False, use_safetensors=True,
                   dtype=torch.float32, attn_implementation="eager", output_loading_info=True)
    if model == "qwen3508":
        from safetensors import safe_open

        path = str(qwen.MODEL_DIR)
        declared = qwen.read_json(assets["files"]["config.json"]["resolved_path"])["text_config"]
        config = Qwen3_5TextConfig.from_pretrained(path, local_files_only=True)
        for name, value in declared.items():
            if name not in ("dtype", "transformers_version") and getattr(config, name) != value:
                raise ValueError(f"Qwen text config differs at {name}")
        config.transformers_weights = qwen.INDEX
        config.use_cache = False
        tokenizer, proof["tokenizer_contract"] = qwen.build_tokenizer(
            qwen.read_json(assets["files"]["tokenizer.json"]["resolved_path"]),
            qwen.read_json(assets["files"]["tokenizer_config.json"]["resolved_path"]))
        body, loading = Qwen3_5ForCausalLM.from_pretrained(path, config=config, **options)
        with safe_open(assets["files"][qwen.WEIGHT]["resolved_path"], framework="pt", device="cpu") as weights:
            proof["weight_consumption"] = qwen.verify_consumption(body, assets["inventory"], weights.get_tensor, torch)
    else:
        path = assets["declared_directory"]
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        body, loading = AutoModelForCausalLM.from_pretrained(path, **options)
    if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
        raise ValueError("external model did not load strictly")
    vocab = body.config.vocab_size
    proof["tokenizer_admission"] = hf_assets.tokenizer_admission(model, tokenizer, assets, vocab)
    if (body.get_input_embeddings().weight.shape[0] != vocab
            or body.get_output_embeddings().weight.shape[0] != vocab
            or any(item.dtype != torch.float32 for item in body.parameters())):
        raise ValueError("external input/output vocabulary or FP32 parameter contract differs")
    body.eval()
    before = state_fingerprint(body)
    proof.update(model_class=type(body).__name__, vocabulary=vocab, core_sha256=before)
    try:
        body.to("cuda")
        yield body, tokenizer, vocab
    finally:
        body.to("cpu")
        torch.cuda.empty_cache()
        proof["unchanged_core"] = state_fingerprint(body) == before
        if not proof["unchanged_core"]:
            raise ValueError("external model tensors changed during generation")


def hf_emit(active, question, *, max_new):
    body, tokenizer, vocab = active
    ids = tokenizer.encode(question, add_special_tokens=True)
    if not ids or len(ids) + max_new > CONTEXT or min(ids) < 0 or max(ids) >= vocab:
        raise ValueError("bounded untruncated HF vocabulary input required")
    result = hf_generation.generate(body, tokenizer, ids, "cuda", max_new, True, None, False)
    generated = result["generated_ids"]
    stopped = result["finish_reason"] == "EOS"
    content = generated[:-1] if stopped else generated
    answer = tokenizer.decode(content, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    return answer, dict(generated_ids=generated, generated_tokens=len(generated),
                        finish_reason=result["finish_reason"], prompt_tokens=len(ids),
                        terminal_ids=generated[-1:] if stopped else [])


class PrismGreedy(prism.native.NativeModel):
    """Independent prompts with the existing Prism sequence-zero incremental decode."""

    def __enter__(self):
        super().__enter__()
        try:
            self.is_end = self.api.llama_vocab_is_eog
            self.is_end.argtypes = [C.c_void_p, C.c_int32]
            self.is_end.restype = C.c_bool
            return self
        except BaseException:
            self.close()
            raise

    def next_token(self, ids):
        import numpy as np

        self.check()
        tokens = (C.c_int32 * len(ids))(*ids)
        batch = self.api.llama_batch_get_one(tokens, len(ids))
        if self.api.llama_decode(self.context, batch) != 0:
            raise ValueError("Prism incremental decode returned an error")
        self.api.llama_synchronize(self.context)
        pointer = self.api.llama_get_logits_ith(self.context, -1)
        if not pointer:
            raise ValueError("Prism decode omitted the last-position output")
        logits = np.ctypeslib.as_array(pointer, shape=(self.vocab_size,))
        if not np.isfinite(logits).all():
            raise ValueError("nonfinite Prism logits")
        return int(np.argmax(logits))


def prism_emit(active, question, *, max_new):
    ids = active.tokenize(question, add_special=True)
    if len(ids) + max_new > active.context_limit or len(ids) > active.batch_limit:
        raise ValueError("bounded untruncated Prism input required")
    memory = active.api.llama_get_memory(active.context)
    if not memory:
        raise ValueError("Prism sequence isolation requires a live memory handle")
    active.api.llama_memory_clear(memory, True)
    active.api.llama_synchronize(active.context)
    both = []
    feed = ids
    stopped = False
    for _ in range(max_new):
        token = active.next_token(feed)
        stopped = bool(active.is_end(active.vocab, token))
        both.append(token)
        if stopped:
            break
        feed = [token]
    content = both[:-1] if stopped else both
    answer = b"".join(active.piece(token) for token in content).decode("utf-8", errors="replace")
    return answer, dict(generated_ids=both, generated_tokens=len(both),
                        finish_reason="EOS" if stopped else "MAX_NEW", prompt_tokens=len(ids),
                        terminal_ids=both[-1:] if stopped else [])


def collect(cases, active, emit, writer, report, check):
    for case in cases:
        check()
        start = time.perf_counter()
        answer, metadata = emit(active, render(case), max_new=holdout.data.MAX_NEW)
        writer.append(dict(case, model=report["contract"]["model"], answer=answer, metadata=metadata,
                           seconds=time.perf_counter() - start,
                           reference_match=holdout.data.reference_match(answer, case),
                           review_signals=holdout.data.review_signals(answer, metadata, case),
                           semantic_review="NOT_RUN"))
        report["completed_rows"] += 1
        if report["completed_rows"] % 20 == 0:
            print(report["contract"]["model"], report["completed_rows"], case["id"], flush=True)


def run(model, output, stop):
    def check():
        if time.time() >= stop:
            raise TimeoutError("external FINAL200 deadline reached")

    def interrupt(_number, _frame):
        raise InterruptedError("external FINAL200 was stopped")

    check()
    cases, contract, assets = read_inputs(model)
    output = output.resolve()
    if not output.is_relative_to(EVIDENCE) or output == EVIDENCE:
        raise ValueError("new external evaluation record must stay in test_result/evidence")
    entry = require_idle_gpu()
    output.mkdir(parents=True, exist_ok=False)
    proof = {}
    report = dict(contract=contract, pid=os.getpid(), entry=entry, completed_rows=0,
                  runtime=proof, started=datetime.now().astimezone().isoformat(), status="STARTED")
    writer = ShardWriter(output, "responses")
    handler = signal.signal(signal.SIGTERM, interrupt)
    try:
        if model == "bonsai2b":
            with PrismGreedy(assets["bundle"], ROOT / assets["model"], vocab_size=assets["vocab"],
                             n_ctx=CONTEXT, check=check) as native:
                proof.update(vocabulary=native.vocab_size, bundle_profile=assets["profile_sha256"])
                collect(cases, native, prism_emit, writer, report, check)
        else:
            with hf_runtime(model, assets, proof) as active:
                collect(cases, active, hf_emit, writer, report, check)
        spec = contract["model_spec"]["weights"]
        if prism.digest(ROOT / spec["path"]) != spec["sha256"]:
            raise ValueError("comparator weight pin changed during generation")
        report["status"] = "RESPONSES_COMPLETE_SEMANTIC_REVIEW_NOT_RUN"
    except BaseException as error:
        report.update(status="INCOMPLETE", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        signal.signal(signal.SIGTERM, handler)
        if report["completed_rows"]:
            result = writer.close(lineage=contract)
            verify(output, result)
            report["responses"] = result
        report["finished"] = datetime.now().astimezone().isoformat()
        prism.write(output / "report.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=MODELS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--deadline", type=datetime.fromisoformat)
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1")
    if args.output is None and args.deadline is None:
        cases, contract, _assets = read_inputs(args.model)
        print(json.dumps(dict(questions=len(cases), expected_model=args.model, contract=contract), ensure_ascii=False))
        return 0
    if args.output is None or args.deadline is None or args.deadline.utcoffset() is None:
        parser.error("actual run requires an isolated output and a timezone-aware deadline")
    stop = args.deadline.timestamp()
    if not time.time() < stop <= AUTHORITY:
        parser.error("actual run must finish within the user's current authorization")
    run(args.model, args.output, stop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
