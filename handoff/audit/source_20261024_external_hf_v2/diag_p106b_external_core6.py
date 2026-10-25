#!/usr/bin/env python3
"""Opt-in external HF Core6 evaluation; check-only never opens a model.

Uses the existing pinned official tasks, HFLM and independent raw recount.
GGUF models are deliberately unsupported by this HF-only driver.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import sysconfig
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_official_core6 as official

TAG = "p106b_external_core6_v2_s1337"
OUTPUT = ROOT / "test_result/evidence" / TAG
SCHEMA = "P106B_EXTERNAL_HF_CORE6_V2"
LATEST_DEADLINE = datetime.fromisoformat("2026-10-24T08:40:00+09:00").timestamp()
MAX_BYTES = 20_000_000
ATOL, RTOL = official.ATOL, official.RTOL
REGISTRY = {
    "qwen06": dict(path="HF/models--Qwen3-0.6B-Base", model_type="qwen3",
        revision="da87bfb608c14b7cf20ba1ce41287e8de496c0cd", weight="model.safetensors",
        weight_sha256="CD2A512003E2F9F3CD3C32A9C3573F820BB28C940F73C57B1DDAA983D9223EBA"),
    "gemma270": dict(path="HF/models--google--gemma-3-270m/snapshots/9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1",
        model_type="gemma3_text", revision="9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1", weight="model.safetensors",
        weight_sha256="ABB58EB73AECE5163624090D5383C59CBCDB9E9539EC84CB864F74386C4B21D5"),
    "gemma1b": dict(path="HF/models--google--gemma-3-1b-pt/snapshots/fcf18a2a879aab110ca39f8bffbccd5d49d8eb29",
        model_type="gemma3_text", revision="fcf18a2a879aab110ca39f8bffbccd5d49d8eb29", weight="model.safetensors",
        weight_sha256="EE5250F6EB1AA7CFB729DFD4DC8D9964FD772324776C6D00BF2BC674C069CB27"),
    "qwen3508": dict(path="HF/models--Qwen--Qwen3.5-0.8B-Base/snapshots/dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68",
        model_type="qwen3_5", revision="dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68",
        weight="model.safetensors-00001-of-00001.safetensors",
        weight_sha256="C2B1E5A17D9C1E27685D92ED9B382911EBB99955ECD89052D1721241ADFBAB6C",
        hold="Nested conditional-generation/text-only loading, key mapping and no-state-cache oracle are not verified."),
}
SMALL_ASSETS = ("config.json", "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "generation_config.json", "added_tokens.json",
    "tokenizer.model", "vocab.json", "merges.txt", "model.safetensors.index.json")
REQUIRED_SMALL = {"config.json", "tokenizer.json", "tokenizer_config.json"}
IMAGE_SPECIALS = {name: (262144, "<image_soft_token>") for name in ("gemma270", "gemma1b")}
SOURCES = ("scripts/diag_p106b_external_core6.py", "scripts/test_p106b_external_core6.py",
    "scripts/diag_p106b_official_core6.py", "scripts/p106b_official_lm_adapter.py",
    "scripts/p106b_official_tasks.py", "scripts/prepare_p106b_official_eval.py",
    "scripts/interactive_research_infer.py", "scripts/p106b_shards.py",
    "data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/models/huggingface.py")


class AdmissionHold(ValueError):
    """A missing prerequisite is not a model quality failure."""


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest().upper()


def identity():
    files = {name: digest(ROOT / name) for name in SOURCES}
    return dict(files=files, sha256=hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest().upper())


def policy():
    result = official.policy()
    result.update(batch_size=1, backend="PINNED_OFFICIAL_HFLM_PREINSTANTIATED_LOCAL_HF",
        precision="FP32; MODEL_EAGER_AND_SDPA_MATH; TF32_OFF", gguf_supported=False,
        model_comparison="OFFICIAL_TASK_CONTRACT; EXTERNAL_PRETRAINING_NOT_MATCHED")
    return result


def json_ready(value):
    """Preserve structured loading evidence; never stringify unknown objects."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("nonfinite report value")
        return value
    if isinstance(value, dict):
        if any(type(key) is not str for key in value):
            raise TypeError("report object keys must be strings")
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((json_ready(item) for item in value),
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False))
    raise TypeError("unsupported report value type: " + type(value).__name__)


def write_json(path, value):
    raw = (json.dumps(json_ready(value), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(raw) >= MAX_BYTES:
        raise ValueError("evidence file must be below 20,000,000 bytes")
    with Path(path).open("xb") as stream:
        stream.write(raw)


def close_report(path, report, primary_error=None):
    """A secondary evidence failure must not replace the original exception."""
    try:
        write_json(path, report)
    except Exception as closure_error:
        minimal = {key: report.get(key) for key in ("schema", "tag", "model", "mode", "started_at", "ended_at")}
        minimal.update(status=report.get("status") if primary_error is not None else "EXTERNAL_REPORT_CLOSURE_ERROR",
            returncode=9, quality_claim=False,
            original_error=None if primary_error is None else dict(type=type(primary_error).__name__, message=str(primary_error)[:2000]),
            report_closure_error=dict(type=type(closure_error).__name__, message=str(closure_error)[:1000]))
        fallback = Path(path) if not Path(path).exists() else Path(path).with_name("report_closure_failure.json")
        try:
            write_json(fallback, minimal)
        except Exception as fallback_error:
            print("[REPORT_CLOSURE_ERROR] " + json.dumps(dict(minimal,
                fallback_error=type(fallback_error).__name__ + ": " + str(fallback_error)[:1000]), ensure_ascii=False), file=sys.stderr)
        if primary_error is None:
            raise


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size >= MAX_BYTES:
        raise AdmissionHold("bounded regular prerequisite report required: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def phase_wall_limit(seconds):
    """Bound the entire owned phase, including preflight and model cleanup."""
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*_args):
        raise TimeoutError("external evaluation phase wall limit exceeded; partial evidence retained")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def validate_execution(model, mode, deadline, max_wall_sec, *, now=None):
    if model not in REGISTRY or mode not in {"canary", "cost", "full"}:
        raise AdmissionHold("explicit preregistered HF model and phase required")
    if REGISTRY[model].get("hold"):
        raise AdmissionHold("qwen3508 HOLD: " + REGISTRY[model]["hold"])
    try:
        parsed = datetime.fromisoformat(deadline)
    except (TypeError, ValueError) as exc:
        raise AdmissionHold("explicit ISO8601 deadline required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AdmissionHold("deadline must include a UTC offset")
    stop = parsed.timestamp()
    bounds = {"canary": (300, 600), "cost": (600, 600), "full": (60, 7200)}[mode]
    if type(max_wall_sec) is not int or not bounds[0] <= max_wall_sec <= bounds[1]:
        raise AdmissionHold("phase wall limit differs: " + str(bounds))
    now = time.time() if now is None else now
    if stop > LATEST_DEADLINE or now + max_wall_sec > stop:
        raise AdmissionHold("whole phase wall limit does not fit the authorized 08:40 deadline")
    return dict(deadline=parsed.isoformat(), deadline_epoch=stop, hard_cap_seconds=max_wall_sec)


def asset_identity(model):
    spec = REGISTRY[model]
    declared = ROOT / spec["path"]
    allowed = (ROOT / "HF").resolve()
    directory = declared.resolve(strict=True)
    if not directory.is_relative_to(allowed):
        raise AdmissionHold("resolved model directory is outside the approved HF root")
    names = [spec["weight"]] + [name for name in SMALL_ASSETS if (declared / name).exists()]
    if not REQUIRED_SMALL.issubset(names):
        raise AdmissionHold("complete local config/tokenizer assets required")
    files = {}
    for name in names:
        logical = declared / name
        resolved = logical.resolve(strict=True)
        if not resolved.is_file() or not resolved.is_relative_to(allowed):
            raise AdmissionHold("asset does not resolve to a regular approved HF file")
        files[name] = dict(path=str(logical), resolved_path=str(resolved), bytes=resolved.stat().st_size,
            sha256=digest(resolved))
    if files[spec["weight"]]["sha256"] != spec["weight_sha256"]:
        raise AdmissionHold("preregistered external HF weight SHA differs")
    model_metadata = read_json(files["config.json"]["resolved_path"])
    if model_metadata.get("model_type") != spec["model_type"]:
        raise AdmissionHold("local model architecture differs from registry")
    if "text_config" in model_metadata:
        raise AdmissionHold("nested model config needs a separately verified explicit loader")
    return dict(revision=spec["revision"], declared_directory=str(declared), resolved_directory=str(directory),
        files=files, weight_pin="ROOT_READ_ONLY_SHA256_20261023",
        metadata_pin="INITIAL_CANARY_BASELINE_THEN_EXACT_COST_FULL_AND_EXIT_COMPARISON")


def phase_prerequisites(model, mode, signature, assets):
    if mode == "canary":
        return {}
    canary_path = OUTPUT / model / "canary/report.json"
    canary = read_json(canary_path)
    common = dict(schema=SCHEMA, tag=TAG, model=model, source_identity=signature, policy=policy(), assets=assets, returncode=0)
    if (any(canary.get(key) != value for key, value in common.items())
            or canary.get("mode") != "canary" or canary.get("status") != "EXTERNAL_CANARY_COMPLETE"):
        raise AdmissionHold("matching closed external numerical canary required")
    if canary.get("numerical_canary", {}).get("passed") is not True:
        raise AdmissionHold("full-label and batch1/batch2 oracle not complete")
    result = dict(canary_report_sha256=digest(canary_path))
    if mode == "full":
        cost_path = OUTPUT / model / "cost/report.json"
        cost = read_json(cost_path)
        if (any(cost.get(key) != value for key, value in common.items())
                or cost.get("mode") != "cost"
                or cost.get("status") != "EXTERNAL_LIMITED_COST_DIAGNOSTIC"
                or cost.get("actual_counts") != official.expected_counts("cost")
                or cost.get("raw_independent_recount") is not True
                or cost.get("prerequisites", {}).get("canary_report_sha256") != result["canary_report_sha256"]):
            raise AdmissionHold("matching complete cost evidence required before full")
        timing = cost.get("task_evaluation_seconds", {})
        if set(timing) != set(official.TASK_COUNTS) or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0
                for v in timing.values()):
            raise AdmissionHold("positive measured per-task cost required")
        startup = cost.get("pre_evaluation_seconds")
        if isinstance(startup, bool) or not isinstance(startup, (int, float)) or not math.isfinite(startup) or startup <= 0:
            raise AdmissionHold("measured startup/pre-evaluation cost required")
        result.update(cost_report_sha256=digest(cost_path), forecast_seconds=
            1.3 * sum(official.TASK_COUNTS[name] * seconds / 32 for name, seconds in timing.items()) + startup + 60,
            forecast_policy="PER_TASK_FIRST32_LINEAR_X1.3_PLUS_MEASURED_STARTUP_PLUS60; ESTIMATE_NOT_GUARANTEE")
    return result


def admit_forecast(prerequisites, admission, *, now=None):
    forecast = prerequisites.get("forecast_seconds", 0)
    now = time.time() if now is None else now
    if forecast > admission["hard_cap_seconds"] or now + forecast > admission["deadline_epoch"]:
        raise AdmissionHold("measured full forecast exceeds phase budget or deadline")


def hflm_source_identity(hflm):
    from scripts.p106b_official_lm_adapter import SOURCE
    actual = Path(sys.modules[hflm.__module__].__file__).absolute()
    expected = Path(sysconfig.get_paths()["purelib"]) / "lm_eval/models/huggingface.py"
    source = SOURCE / "lm_eval/models/huggingface.py"
    if actual != expected or digest(actual) != digest(source):
        raise AdmissionHold("installed HFLM source/path differs from the pinned official source")
    return dict(path=str(actual), sha256=digest(actual), pinned_source=str(source))


def audit_tokenizer_vocabulary(model, vocabulary, base_vocabulary, head_size, *,
        token_metadata=None, tokenizer_metadata=None, special_map=None):
    """Permit only the exact declared image special outside a text head."""
    if type(head_size) is not int or head_size < 2 or not vocabulary or not base_vocabulary:
        raise AdmissionHold("nonempty native/base vocabularies and actual text head required")
    if any(type(i) is not int or not 0 <= i < head_size for i in base_vocabulary.values()):
        raise AdmissionHold("base tokenizer IDs exceed the actual text head")
    if any(vocabulary.get(name) != index for name, index in base_vocabulary.items()):
        raise AdmissionHold("native vocabulary does not preserve the base vocabulary")
    token_metadata, tokenizer_metadata, special_map = token_metadata or {}, tokenizer_metadata or {}, special_map or {}
    outside = []
    for name, index in vocabulary.items():
        if type(index) is not int or index < 0:
            raise AdmissionHold("native vocabulary contains an invalid token ID")
        if index < head_size:
            continue
        if (index, name) != IMAGE_SPECIALS.get(model) or index != head_size:
            raise AdmissionHold("unregistered out-of-head tokenizer ID")
        added = [row for row in token_metadata.get("added_tokens", []) if row.get("id") == index]
        decoder = tokenizer_metadata.get("added_tokens_decoder", {}).get(str(index), {})
        declarations = (tokenizer_metadata.get("image_token"),
            tokenizer_metadata.get("extra_special_tokens", {}).get("image_token"), special_map.get("image_token"))
        if (len(added) != 1 or added[0].get("content") != name or added[0].get("special") is not True
                or decoder.get("content") != name or decoder.get("special") is not True
                or any(value != name for value in declarations)):
            raise AdmissionHold("out-of-head image special is not exactly declared in all local metadata")
        outside.append(dict(id=index, content=name, special=True, usable_as_text_input_or_target=False))
    return dict(base_vocab_size=len(base_vocabulary), native_vocab_size=len(vocabulary),
        head_size=head_size, out_of_head_added_specials=outside,
        actual_id_policy="EVERY_ENCODED_CONTEXT_CONTINUATION_PREFIX_PAD_EOS_MUST_FIT_TEXT_HEAD")


def tokenizer_admission(model, tokenizer, assets, head_size):
    backend = getattr(tokenizer, "backend_tokenizer", None)
    if backend is None:
        raise AdmissionHold("an inspectable native base tokenizer is required")
    vocabulary = tokenizer.get_vocab()
    base = backend.get_vocab(with_added_tokens=False)
    metadata = [{}, {}, {}]
    if any(type(index) is not int or not 0 <= index < head_size for index in vocabulary.values()):
        # Existing tokenizer metadata can exceed the evidence-output size cap.
        # Only the explicitly admitted local metadata files are read here.
        for index, name in enumerate(("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json")):
            descriptor = assets.get("files", {}).get(name)
            if descriptor is None:
                raise AdmissionHold("exact out-of-head special metadata is absent: " + name)
            metadata[index] = json.loads(Path(descriptor["resolved_path"]).read_text(encoding="utf-8"))
    return audit_tokenizer_vocabulary(model, vocabulary, base, head_size,
        token_metadata=metadata[0], tokenizer_metadata=metadata[1], special_map=metadata[2])


def head_guard_type(hflm, head_size):
    """Keep official encoding/scoring; reject every unusable ID before forward."""
    from scripts.p106b_official_lm_adapter import token_ids, plan_tokens
    class HeadBoundHFLM(hflm):
        def assert_special_ids(self):
            for label, value in (("prefix", self.prefix_token_id), ("pad", self.tokenizer.pad_token_id), ("eos", self.eot_token_id)):
                try:
                    token_ids([value], head_size)
                except ValueError as exc:
                    raise AdmissionHold("actual " + label + " ID exceeds the text head") from exc

        def tok_encode(self, *args, **kwargs):
            encoded = super().tok_encode(*args, **kwargs)
            token_ids(encoded, head_size, empty=True)
            return encoded

        def _loglikelihood_tokens(self, requests, *args, **kwargs):
            requests = list(requests)
            self.assert_special_ids()
            # Validate the complete call before the official scorer can forward
            # any candidate, including direct encoded callers and empty-prefix use.
            for _, context, continuation in requests:
                plan_tokens(context, continuation, head_size, self.max_length)
            return super()._loglikelihood_tokens(requests, *args, **kwargs)
    return HeadBoundHFLM


@contextmanager
def model_runtime(model, torch, assets, *, proof=None):
    import tinylm  # noqa: F401 -- apply process-local HF paths before HF imports.
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    cache_policy = configure_hf_cache()
    from scripts.interactive_research_infer import state_fingerprint
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from lm_eval.models.huggingface import HFLM
    spec, body, lm = REGISTRY[model], None, None
    proof = {} if proof is None else proof
    proof.update(cache_policy=cache_policy, hflm_source=hflm_source_identity(HFLM),
        source_assets_unchanged=False, body_unchanged=False, model_load_attempted=False, model_loaded=False)
    caught = None
    try:
        path = str(ROOT / spec["path"])
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        proof["model_load_attempted"] = True
        body, loading = AutoModelForCausalLM.from_pretrained(path, local_files_only=True,
            trust_remote_code=False, use_safetensors=True, dtype=torch.float32,
            attn_implementation="eager", use_cache=False, output_loading_info=True)
        proof["model_loaded"] = True
        loading = json_ready(loading)
        proof["loading_info"] = loading
        if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise AdmissionHold("strict external loading_info must have no missing/extra/mismatched/error keys")
        hf_config = body.config
        if (hf_config.model_type != spec["model_type"] or hf_config.use_cache
                or hf_config._attn_implementation != "eager" or any(p.dtype != torch.float32 for p in body.parameters())):
            raise AdmissionHold("external FP32/eager/no-KV model contract differs")
        vocab = hf_config.vocab_size
        if (type(vocab) is not int or body.get_input_embeddings().weight.shape[0] != vocab
                or body.get_output_embeddings().weight.shape[0] != vocab):
            raise AdmissionHold("config and actual input/output text head vocab differ")
        proof["tokenizer_admission"] = tokenizer_admission(model, tokenizer, assets, vocab)
        body.eval()
        before = state_fingerprint(body)
        proof.update(initial_core_sha256=before, parameters=sum(p.numel() for p in body.parameters()),
            vocab_size=vocab, tokenizer_size=len(tokenizer), tokenizer_vocab_size=tokenizer.vocab_size,
            model_class=type(body).__name__, tokenizer_class=type(tokenizer).__name__, loading_info=loading,
            use_cache=False, attn_implementation=hf_config._attn_implementation,
            model_source_sha256=digest(sys.modules[type(body).__module__].__file__))
        body.to("cuda")
        lm = head_guard_type(HFLM, vocab)(pretrained=body, tokenizer=tokenizer, backend="causal", max_length=1024,
            batch_size=1, device="cuda", logits_cache=False, add_bos_token=False,
            softmax_dtype=torch.float32, mixed_precision_dtype=None, trust_remote_code=False)
        lm.assert_special_ids()
        if state_fingerprint(body) != before:
            raise ValueError("HFLM construction changed external model values")
        proof.update(prefix_token_id=lm.prefix_token_id, pad_token_id=lm.tokenizer.pad_token_id,
            eos_token_id=lm.eot_token_id, device=str(lm.device))
        yield lm, proof
    except BaseException as exc:
        caught = exc
        raise
    finally:
        failures = []
        if body is not None and "initial_core_sha256" in proof:
            try:
                proof["final_core_sha256"] = state_fingerprint(body)
                proof["body_unchanged"] = proof["final_core_sha256"] == proof["initial_core_sha256"]
                if not proof["body_unchanged"]:
                    failures.append("external model body changed")
            except BaseException as exc:
                failures.append("final body fingerprint: " + str(exc)[:300])
        try:
            proof["source_assets_unchanged"] = asset_identity(model) == assets
            if not proof["source_assets_unchanged"]:
                failures.append("external source assets changed")
        except BaseException as exc:
            failures.append("final asset verification: " + str(exc)[:300])
        try:
            proof["hflm_source_unchanged"] = hflm_source_identity(HFLM) == proof["hflm_source"]
            if not proof["hflm_source_unchanged"]:
                failures.append("installed HFLM source changed")
            if body is not None and "model_source_sha256" in proof:
                proof["model_source_unchanged"] = digest(sys.modules[type(body).__module__].__file__) == proof["model_source_sha256"]
                if not proof["model_source_unchanged"]:
                    failures.append("external Transformers model source changed")
        except BaseException as exc:
            failures.append("final backend source verification: " + str(exc)[:300])
        try:
            if lm is not None:
                lm._model = None
            if body is not None:
                body.to("cpu")
        except BaseException as exc:
            failures.append("external model cleanup: " + str(exc)[:300])
        finally:
            lm = body = None
            gc.collect()
            torch.cuda.empty_cache()
        proof["exit_verification_errors"] = failures
        if failures and caught is None:
            raise ValueError("; ".join(failures))


def compare_scores(left, right):
    if len(left) != len(right) or not left:
        raise ValueError("complete nonempty likelihood lists required")
    rows = []
    for a, b in zip(left, right):
        if any(not isinstance(v, (tuple, list)) or len(v) != 2 or type(v[1]) is not bool
               or isinstance(v[0], bool) or not isinstance(v[0], (int, float))
               or not math.isfinite(v[0]) or v[0] > 0 for v in (a, b)):
            raise ValueError("finite complete likelihood and greedy bool required")
        rows.append(dict(left=list(a), right=list(b), absolute_difference=abs(a[0] - b[0]),
            close=math.isclose(a[0], b[0], abs_tol=ATOL, rel_tol=RTOL) and a[1] == b[1]))
    if not all(row["close"] for row in rows):
        raise ValueError("external numerical likelihood oracle negative")
    return rows


def canary_batches(lm, requests):
    """Use the pinned HFLM's actual batch property, restoring it on failure."""
    original = lm.batch_size_per_gpu
    try:
        lm.batch_size_per_gpu = 1
        if lm.batch_size != 1:
            raise ValueError("pinned HFLM batch1 setting did not take effect")
        singles = lm.loglikelihood(requests, disable_tqdm=True)
        lm.batch_size_per_gpu = 2
        if lm.batch_size != 2:
            raise ValueError("pinned HFLM batch2 setting did not take effect")
        pairs = lm.loglikelihood(requests, disable_tqdm=True)
    finally:
        lm.batch_size_per_gpu = original
    return singles, pairs


def numerical_canary(lm, torch):
    from lm_eval.api.instance import Instance
    from scripts.p106b_official_lm_adapter import plan_tokens, padded_batch
    literal_prefix = lm.tok_decode([lm.prefix_token_id], skip_special_tokens=False)
    literal_ids = lm.tok_encode(literal_prefix + "Hello", add_special_tokens=False)
    if not literal_prefix or not literal_ids or literal_ids[0] != lm.prefix_token_id:
        raise AdmissionHold("literal native BOS/EOS probe must round-trip to the exact prefix ID")
    cases = [("Question: one plus one?\nAnswer:", " two"), ("", "Hello"),
        ("질문: 사과의 색은?\n답:", " 빨강"), ("A B C D\n", " A B"),
        ("", literal_prefix + "Hello"), ("A", " a longer continuation with several words")]
    requests = [Instance(request_type="loglikelihood", doc={}, arguments=pair, idx=i,
        metadata=("synthetic_external_canary", i, 1)) for i, pair in enumerate(cases)]
    singles, pairs = canary_batches(lm, requests)
    batch_checks = compare_scores(singles, pairs)
    plans, vocab = [], lm.model.config.vocab_size
    for context, continuation in cases:
        if context:
            ctx, cont = lm._encode_pair(context, continuation)
        else:
            cont = lm.tok_encode(continuation, add_special_tokens=False)
            if not cont:
                raise ValueError("synthetic continuation encoded to no tokens")
            ctx, cont = ([lm.prefix_token_id], cont) if cont[0] != lm.prefix_token_id else (cont[:1], cont[1:])
        plans.append(plan_tokens(ctx, cont, vocab, 1024))
    direct = []
    for offset in range(0, len(plans), 2):
        batch = padded_batch(plans[offset:offset + 2], lm.tokenizer.pad_token_id, vocab)
        inputs = torch.tensor(batch["input_ids"], device="cuda", dtype=torch.long)
        labels = torch.tensor(batch["labels"], device="cuda", dtype=torch.long)
        logits = lm.model(input_ids=inputs, use_cache=False).logits
        if logits.dtype != torch.float32 or tuple(logits.shape) != (*inputs.shape, vocab):
            raise ValueError("full FP32 B*T*V logits required by independent label oracle")
        losses = torch.nn.functional.cross_entropy(logits.reshape(-1, vocab), labels.reshape(-1),
            ignore_index=-100, reduction="none").reshape_as(labels)
        if not bool(torch.isfinite(losses).all()):
            raise ValueError("nonfinite independent full-label loss")
        for index in range(inputs.shape[0]):
            mask = labels[index] != -100
            direct.append((float(-losses[index].sum()), bool(logits[index].argmax(-1)[mask].eq(labels[index][mask]).all())))
        del inputs, labels, logits, losses
    return dict(passed=True, quality_claim=False, arguments=[list(row) for row in cases],
        batch_sizes=[1, 2], batch1_vs_batch2=batch_checks, full_label_ce=compare_scores(singles, direct),
        pad_id=lm.tokenizer.pad_token_id, vocab_size=vocab, atol=ATOL, rtol=RTOL,
        token_plans=[dict(input_ids=list(p.input_ids), labels=list(p.labels)) for p in plans])


def recount_raw(task, target, manifest, expected):
    from scripts.p106b_shards import verify
    verify(target, manifest)
    rows = []
    for spec in manifest["shards"]:
        with (target / spec["path"]).open(encoding="utf-8") as stream:
            rows.extend(json.loads(line) for line in stream)
    audit = official.audit_samples(task, rows, expected)
    audit["choice_likelihoods"] = sum(len(row["filtered_resps"]) for row in rows)
    return audit


def evaluate_tasks(lm, torch, target, report, tasks, mode):
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    from scripts.p106b_shards import ShardWriter
    counts = official.expected_counts(mode)
    manager, timing = TaskManager(), {}
    report.update(actual_counts={}, official_results={}, sample_manifests={}, independent_audits={},
        task_evaluation_seconds=timing, raw_independent_recount=False)
    lengths = ShardWriter(target, "token_lengths")
    try:
        with official.length_observer(lm, lengths) as summary:
            for name, task in tasks.items():
                tick = time.monotonic()
                result = simple_evaluate(model=lm, tasks=[task], num_fewshot=0, task_manager=manager,
                    batch_size=1, device="cuda", use_cache=None, cache_requests=False,
                    limit=32 if mode == "cost" else None, bootstrap_iters=100000, log_samples=True,
                    apply_chat_template=False, fewshot_as_multiturn=False, random_seed=1337,
                    numpy_random_seed=1337, torch_random_seed=1337, fewshot_random_seed=1337)
                torch.cuda.synchronize()
                timing[name] = time.monotonic() - tick
                if set(result["samples"]) != {name}:
                    raise ValueError("official task identity differs")
                rows = result.pop("samples")[name]
                memory_audit = official.audit_samples(task, rows, counts[name])
                writer = ShardWriter(target, name + "_samples")
                try:
                    for row in rows:
                        writer.append(official.plain(row))
                finally:
                    if writer._total_rows:
                        manifest = writer.close(lineage=dict(model=report["model"], task=name, mode=mode, tag=TAG))
                        report["sample_manifests"][name] = manifest
                audit = recount_raw(task, target, manifest, counts[name])
                if any(audit[key] != value for key, value in memory_audit.items()):
                    raise ValueError("disk raw recount differs from in-memory audit")
                for metric, key in (("acc", "correct"), ("acc_norm", "correct_norm")):
                    score = result["results"][name].get(metric + ",none")
                    if score is not None and not math.isclose(score, audit[key] / counts[name], abs_tol=1e-12):
                        raise ValueError("official metric differs from full raw independent recount")
                report["independent_audits"][name] = audit
                report["official_results"][name] = official.plain(result)
                report["actual_counts"][name] = counts[name]
                print(json.dumps(dict(event="EXTERNAL_OFFICIAL_TASK_CLOSED", model=report["model"],
                    mode=mode, task=name, rows=counts[name], seconds=timing[name]), sort_keys=True), flush=True)
            report["token_lengths_summary"] = summary
    finally:
        if lengths._total_rows:
            report["lengths_manifest"] = lengths.close(lineage=dict(model=report["model"], mode=mode, tag=TAG))
    if report["actual_counts"] != counts:
        raise ValueError("no omitted official task/row is allowed")
    report["choice_likelihoods"] = sum(a["choice_likelihoods"] for a in report["independent_audits"].values())
    if mode == "full" and (sum(counts.values()) != 19965 or report["choice_likelihoods"] != 67106):
        raise ValueError("full evaluation must have exactly 19965 rows and 67106 choice likelihoods")
    report.update(raw_independent_recount=True, evaluation_seconds=sum(timing.values()))


def execute(model, mode, expected_source, deadline, max_wall_sec):
    signature = identity()
    if signature["sha256"] != expected_source:
        raise AdmissionHold("preregistered external evaluation source differs")
    admission = validate_execution(model, mode, deadline, max_wall_sec)
    target = OUTPUT / model / mode
    if target.exists() or target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise FileExistsError("existing complete/partial or linked output is preserved")
    target.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, tag=TAG, model=model, mode=mode, status="STARTED", returncode=9,
        policy=policy(), source_identity=signature, admission=admission, quality_claim=False,
        training=False, optimizer_updates=0, checkpoint_writes=0,
        started_at=datetime.now(timezone.utc).isoformat())
    began = time.monotonic()
    primary_error = None
    try:
        with phase_wall_limit(max_wall_sec):
            assets = asset_identity(model)
            report["assets"] = assets
            pre = phase_prerequisites(model, mode, signature, assets)
            report["prerequisites"] = pre
            admit_forecast(pre, admission)
            for key, value in official.OFFLINE.items():
                os.environ[key] = value
            from scripts.prepare_p106b_official_eval import configure_hf_cache, COMMIT, MANIFEST_SHA
            configure_hf_cache()
            from scripts.p106b_official_tasks import load_tasks
            tasks, specs, framework = load_tasks()
            report.update(framework_commit=COMMIT, data_manifest_sha256=MANIFEST_SHA,
                framework_provenance=framework, task_specs=specs)
            from scripts.interactive_research_infer import require_idle_gpu
            report["gpu_idle_before_model"] = require_idle_gpu()
            admit_forecast(pre, admission)
            if time.time() + 30 >= admission["deadline_epoch"]:
                raise AdmissionHold("insufficient deadline margin before external model loading")
            import torch
            from torch.nn.attention import sdpa_kernel, SDPBackend
            torch.set_num_threads(4)
            torch.manual_seed(1337)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            with sdpa_kernel(SDPBackend.MATH), torch.no_grad():
                proof = {}
                report["model_proof"] = proof
                with model_runtime(model, torch, assets, proof=proof) as (lm, proof):
                    report["numerical_canary"] = numerical_canary(lm, torch)
                    report["pre_evaluation_seconds"] = time.monotonic() - began
                    if mode != "canary":
                        evaluate_tasks(lm, torch, target, report, tasks, mode)
            report["sources_unchanged"] = identity() == signature
            if not report["sources_unchanged"]:
                raise ValueError("external evaluation source changed during execution")
            report.update(status={"canary": "EXTERNAL_CANARY_COMPLETE", "cost": "EXTERNAL_LIMITED_COST_DIAGNOSTIC",
                "full": "EXTERNAL_OFFICIAL_CORE6_FULL_COMPLETE"}[mode], returncode=0)
    except BaseException as exc:
        primary_error = exc
        report.update(status="EXTERNAL_PREREQUISITE_HOLD" if isinstance(exc, AdmissionHold) else "EXTERNAL_EVALUATION_ERROR",
            error_type=type(exc).__name__, error=str(exc)[:2000])
        raise
    finally:
        try:
            report["sources_unchanged"] = identity() == signature
        except BaseException as exc:
            report["sources_unchanged"] = False
            report["source_exit_verification_error"] = str(exc)[:300]
        source_error = report["returncode"] == 0 and not report["sources_unchanged"]
        if source_error:
            report.update(status="EXTERNAL_EVALUATION_ERROR", returncode=9,
                error_type="ValueError", error="external evaluation source changed before report closure")
        report.update(ended_at=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - began)
        close_report(target / "report.json", report,
            primary_error=primary_error if primary_error is not None else ValueError(report["error"]) if source_error else None)
        if source_error:
            raise ValueError(report["error"])
    return {key: report[key] for key in ("status", "model", "mode", "wall_seconds")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--model", choices=tuple(REGISTRY))
    parser.add_argument("--mode", choices=("canary", "cost", "full"))
    parser.add_argument("--source-sha256")
    parser.add_argument("--deadline")
    parser.add_argument("--max-wall-sec", type=int)
    args = parser.parse_args(argv)
    if args.execute:
        if any(getattr(args, name) is None for name in ("model", "mode", "source_sha256", "deadline", "max_wall_sec")):
            parser.error("execute requires explicit model/mode/source-sha256/deadline/max-wall-sec")
        result = execute(args.model, args.mode, args.source_sha256, args.deadline, args.max_wall_sec)
    else:
        result = dict(status="SOURCE_ONLY", tag=TAG, models=0, source_identity=identity(),
            policy=policy(), registry=REGISTRY, latest_deadline="2026-10-24T08:40:00+09:00",
            unsupported_gguf=["gpt2_q4km", "bonsai2_2b_ptq1", "qwen35_08b_iq2xxs"])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
