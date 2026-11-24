#!/usr/bin/env python3
"""Independent, opt-in Qwen3.5 text-only official Core6 connector.

Import/check-only is stdlib-only. The owner alone executes tokenizer/model/GPU
phases. Existing drivers, libraries, model assets and task definitions are never
patched. A report0 alone is not successful closure or proof of process exit0.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import struct
import sys
import sysconfig
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_external_core6 as external
from scripts import diag_p106b_official_core6 as official

TAG, SCHEMA = "p106b_qwen35_text_core6_v3_s1337", "P106B_QWEN35_TEXT_CORE6_V3"
CLOSURE_SCHEMA = SCHEMA + "_CLOSURE"
MODEL = "qwen3508"
REVISION = "dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68"
MODEL_DIR = ROOT / external.REGISTRY[MODEL]["path"]
WEIGHT = "model.safetensors-00001-of-00001.safetensors"
INDEX = "model.safetensors.index.json"
WEIGHT_SHA = external.REGISTRY[MODEL]["weight_sha256"]
SMALL_PINS = {
    "config.json": "B90B86F35C8E6925EF74EE04D0E758F0A845C83A42089AD82BBAA948DE9B4204",
    "tokenizer.json": "FE000E3ED39ED12B8D2481D527D44F93C65D37E87645D2DCC80D1BF9D50D2927",
    "tokenizer_config.json": "E611FBCCC7C29EF3B1CAFB1CB7EA548D189968632901D678FD62BE68C47885DE",
    INDEX: "CE9A885EFDF27D3664FDEF5D512AD365216F1074051EF840C7CD8E5431495D0A",
}
OUTPUT = ROOT / "test_result/evidence" / TAG
LATEST = datetime.fromisoformat("2026-10-24T08:40:00+09:00").timestamp()
LANGUAGE, VISION, MTP = "model.language_model.", "model.visual.", "mtp."
TOKEN_FIELDS = ("content", "single_word", "lstrip", "rstrip", "normalized", "special")
PIPELINE = ("model", "normalizer", "pre_tokenizer", "post_processor", "decoder", "truncation", "padding")
MERGE_RULES = 247587
RAW_PIPELINE_SHA = "4824E7B0F0A2ACD9B4B1521A7BD24979839E53E45CDE345B57CF157A8C0AAC39"
CANONICAL_PIPELINE_SHA = "FEE1F6066DBDEBCC449FE6E53984CAA0621845F4F6BD5DF6897DEBBF55B8E363"
OWN_FILES = ("scripts/diag_p106b_qwen35_text_core6.py", "scripts/test_p106b_qwen35_text_core6.py",
    "tinylm/__init__.py", "tinylm/paths.py")
TRANSFORMERS_FILES = ("__init__.py", "configuration_utils.py", "modeling_utils.py", "core_model_loading.py",
    "conversion_mapping.py", "utils/loading_report.py", "models/auto/modeling_auto.py",
    "models/qwen3_5/configuration_qwen3_5.py", "models/qwen3_5/modeling_qwen3_5.py",
    "tokenization_utils_base.py", "tokenization_utils_tokenizers.py")
HARNESS_SOURCE = "data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source"
HARNESS_DEFINITIONS = ("lm_eval/api/task.py", "lm_eval/config/task.py", "lm_eval/api/metrics.py",
    "lm_eval/evaluator.py", "lm_eval/tasks/_yaml_loader.py", "lm_eval/models/utils.py")
TASK_DEFINITIONS = ("piqa/piqa.yaml", "arc/arc_easy.yaml", "arc/arc_challenge.yaml",
    "hellaswag/hellaswag.yaml", "hellaswag/utils.py", "winogrande/default.yaml",
    "winogrande/preprocess_winogrande.py", "super_glue/boolq/default.yaml")
CONTRACT = ("REPORT0_IS_NOT_SUCCESS; ROOT_REQUIRES_REAL_PROCESS_EXIT0_AND_CLOSURE_AND_NO_VETO_AND_EXTERNAL_HARDCAP; "
            "NO_ATOMIC_FS_PROCESS_EXIT_OR_POST_LAST_READ_TAMPER_PROOF")
digest = external.digest


class Hold(ValueError):
    """An explicit operational/contract prerequisite, never a quality result."""


def finite(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def object_sha(value):
    return hashlib.sha256(json.dumps(external.json_ready(value), sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest().upper()


def read_json(path, limit=19_999_999):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("bounded regular nonsymlink JSON required: " + str(path))
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def identity():
    files = dict(external.identity()["files"])
    files.update({name: digest(ROOT / name) for name in OWN_FILES})
    files.update({HARNESS_SOURCE + "/" + name: digest(ROOT / HARNESS_SOURCE / name) for name in HARNESS_DEFINITIONS})
    files.update({HARNESS_SOURCE + "/lm_eval/tasks/" + name: digest(ROOT / HARNESS_SOURCE / "lm_eval/tasks" / name)
                  for name in TASK_DEFINITIONS})
    dist = importlib.metadata.distribution("transformers")
    if dist.version != "5.14.1":
        raise ValueError("this connector requires the inspected Transformers 5.14.1 source")
    for name in TRANSFORMERS_FILES:
        path = Path(dist.locate_file("transformers")) / name
        files[str(path)] = digest(path)
    versions = {name: importlib.metadata.version(name) for name in
                ("transformers", "torch", "safetensors", "tokenizers", "lm_eval", "accelerate")}
    return dict(files=files, versions=versions, sha256=object_sha(dict(files=files, versions=versions)))


def verify_pins(pins):
    for name, sha in pins.items():
        path = Path(name)
        if digest(path if path.is_absolute() else ROOT / path) != sha:
            raise ValueError("pinned input changed: " + name)


def imported_source_identity(signature):
    receipts = {}
    for name, sha in signature["files"].items():
        if "/transformers/" not in name:
            continue
        relative = name.split("/transformers/", 1)[1]
        module_name = "transformers" if relative == "__init__.py" else "transformers." + relative[:-3].replace("/", ".")
        module = sys.modules.get(module_name)
        if module is None or Path(module.__file__).absolute() != Path(name).absolute() or digest(module.__file__) != sha:
            raise ValueError("actual imported Transformers source/path differs: " + module_name)
        receipts[module_name] = dict(path=str(module.__file__), sha256=sha)
    return receipts


def harness_definition_identity(signature):
    receipts = {}
    runtime = Path(sysconfig.get_paths()["purelib"])
    for name in HARNESS_DEFINITIONS:
        path = runtime / name
        expected = signature["files"][HARNESS_SOURCE + "/" + name]
        if digest(path) != expected:
            raise ValueError("installed official task/metric/evaluator source differs: " + name)
        module = sys.modules.get(name[:-3].replace("/", "."))
        if module is not None and Path(module.__file__).absolute() != path.absolute():
            raise ValueError("actual official task/metric/evaluator import path differs: " + name)
        receipts[str(path)] = expected
    return receipts


def policy():
    result = external.policy()
    result.update(model=MODEL, revision=REVISION, loader="OFFICIAL_QWEN3_5_TEXT_CLASS_AND_OFFICIAL_PREFIX_CONVERSION",
        tokenizer="OFFICIAL_SERIALIZED_BACKEND_PLUS_CONFIG33_EXTRA13_NAMED7_COMPOSITE_CONTRACT",
        consumed_language_keys=320, unused_vision_keys=153, unused_mtp_keys=15,
        key_value_verification="ALL_LANGUAGE_KEYS_EXACT_FP32_VALUES_AND_TIED_HEAD_ALIAS",
        hybrid_state="USE_CACHE_FALSE_PAST_NONE_NO_CROSS_REQUEST_STATE",
        closure=CONTRACT)
    return result


def header_inventory(header, *, counts=(320, 153, 15)):
    rows = {key: value for key, value in header.items() if key != "__metadata__"}
    groups = {prefix: {key: value for key, value in rows.items() if key.startswith(prefix)}
              for prefix in (LANGUAGE, VISION, MTP)}
    if tuple(len(groups[p]) for p in groups) != counts or sum(map(len, groups.values())) != len(rows):
        raise ValueError("exact language/vision/MTP inventory required; unknown keys are forbidden")
    for key, value in rows.items():
        shape, offsets = value.get("shape"), value.get("data_offsets")
        if (not isinstance(shape, list) or any(type(n) is not int or n <= 0 for n in shape)
                or value.get("dtype") not in ("BF16", "F32") or not isinstance(offsets, list)
                or len(offsets) != 2 or any(type(n) is not int or n < 0 for n in offsets)
                or offsets[1] - offsets[0] != math.prod(shape) * (4 if value["dtype"] == "F32" else 2)):
            raise ValueError("invalid tensor header: " + key)
    mapping = {key: "model." + key[len(LANGUAGE):] for key in groups[LANGUAGE]}
    if len(set(mapping.values())) != len(mapping) or "lm_head.weight" in rows:
        raise ValueError("one-to-one official language-prefix mapping and absent tied-head checkpoint alias required")
    return dict(language=groups[LANGUAGE], unused={**groups[VISION], **groups[MTP]}, mapping=mapping,
        consumed_keys=len(mapping), unused_vision_keys=len(groups[VISION]), unused_mtp_keys=len(groups[MTP]),
        nonuse_scope="NOT_MODEL_PARAMETERS_OR_TEXT_SCORING; NOT_A_CLAIM_OF_ZERO_FILE_IO")


def read_header(path):
    with Path(path).open("rb") as stream:
        length_raw = stream.read(8)
        if len(length_raw) != 8:
            raise ValueError("truncated safetensors header length")
        length = struct.unpack("<Q", length_raw)[0]
        if not 2 <= length < 2_000_000:
            raise ValueError("bounded safetensors header required")
        raw = stream.read(length)
        if len(raw) != length:
            raise ValueError("truncated safetensors header")
    header = json.loads(raw)
    inventory = header_inventory(header)
    inventory.update(header_bytes=length, header_sha256=hashlib.sha256(raw).hexdigest().upper())
    return inventory


def asset_identity():
    allowed = (ROOT / "HF").resolve()
    directory = MODEL_DIR.resolve(strict=True)
    if not directory.is_relative_to(allowed):
        raise ValueError("model directory escaped the approved HF root")
    files = {}
    for name, expected in {WEIGHT: WEIGHT_SHA, **SMALL_PINS}.items():
        logical, resolved = MODEL_DIR / name, (MODEL_DIR / name).resolve(strict=True)
        if not resolved.is_file() or not resolved.is_relative_to(allowed) or digest(resolved) != expected:
            raise ValueError("exact pinned original model asset required: " + name)
        files[name] = dict(path=str(logical), resolved_path=str(resolved), bytes=resolved.stat().st_size, sha256=expected)
    inventory = read_header(files[WEIGHT]["resolved_path"])
    index = read_json(files[INDEX]["resolved_path"])
    expected_keys = set(inventory["language"]) | set(inventory["unused"])
    if (set(index.get("weight_map", {})) != expected_keys or set(index["weight_map"].values()) != {WEIGHT}
            or index.get("metadata", {}).get("total_size") != sum(row["data_offsets"][1] - row["data_offsets"][0]
                for row in [*inventory["language"].values(), *inventory["unused"].values()])):
        raise ValueError("pinned official index must bind all 488 original keys to exactly the pinned shard")
    return dict(revision=REVISION, files=files, inventory=inventory, weight_index_keys=len(expected_keys))


def tokenizer_declarations(raw, metadata, *, expected_counts=(22, 33, 13, 7)):
    decoder = {int(key): dict(value) for key, value in metadata["added_tokens_decoder"].items()}
    original = {row["id"]: {key: row[key] for key in TOKEN_FIELDS} for row in raw["added_tokens"]}
    extras, named = metadata["additional_special_tokens"], metadata["extra_special_tokens"]
    if (tuple(map(len, (original, decoder, extras, named))) != expected_counts
            or len(set(extras)) != len(extras) or any(set(value) != set(TOKEN_FIELDS) for value in decoder.values())
            or any(type(i) is not int or i < 0 for i in decoder)
            or any(decoder.get(i) != value for i, value in original.items())):
        raise ValueError("exact common token properties/config decoder/extra list/named map required")
    if any(not isinstance(row["content"], str) or not row["content"]
           or any(type(row[key]) is not bool for key in TOKEN_FIELDS[1:]) for row in decoder.values()):
        raise ValueError("declared AddedToken content and boolean attributes required")
    vocabulary = dict(raw["model"]["vocab"])
    for index, row in sorted(decoder.items()):
        if row["content"] in vocabulary and vocabulary[row["content"]] != index:
            raise ValueError("declared token remaps an existing native ID")
        vocabulary[row["content"]] = index
    if len(set(vocabulary.values())) != len(vocabulary):
        raise ValueError("declared vocabulary IDs collide")
    declared = {row["content"]: row for row in decoder.values()}
    if any(token not in declared or not declared[token]["special"] for token in [*extras, *named.values()]):
        raise ValueError("all frontend special tokens must be declared special tokens")
    return dict(decoder=decoder, original=original, extras=extras, named=named, vocabulary=vocabulary)


def canonical_backend_baseline(raw, *, api=None, expected_merge_count=MERGE_RULES,
                               expected_pipeline_shas=(RAW_PIPELINE_SHA, CANONICAL_PIPELINE_SHA)):
    """Public roundtrip baseline, before config additions or the HF frontend.

    Only two lossless representation changes are admitted: omitted
    ignore_merges -> its official False default, and each original merge string
    -> a pair whose ordered space-join exactly reconstructs that same string.
    Never edit the original JSON, reconstruct a regex, or discard any rule.
    """
    if api is None:
        from tokenizers import Tokenizer
    else:
        Tokenizer = api
    backend = Tokenizer.from_str(json.dumps(raw, ensure_ascii=False))
    canonical = json.loads(backend.to_str())
    original_model, public_model = raw["model"], canonical["model"]
    if (original_model.get("type") != "BPE" or "ignore_merges" in original_model
            or public_model.get("ignore_merges") is not False
            or {key: value for key, value in original_model.items() if key != "merges"}
               != {key: value for key, value in public_model.items() if key not in ("merges", "ignore_merges")}
            or any(canonical.get(key) != raw.get(key) for key in PIPELINE if key != "model")
            or canonical.get("added_tokens") != raw.get("added_tokens")):
        raise Hold("TOKENIZER_CANONICAL_HOLD: unregistered original-to-public backend transformation")
    original_merges, public_merges = original_model.get("merges"), public_model.get("merges")
    if (not isinstance(original_merges, list) or not isinstance(public_merges, list)
            or len(original_merges) != expected_merge_count or len(public_merges) != expected_merge_count
            or any(not isinstance(value, str) for value in original_merges)
            or any(not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(value, str) for value in pair)
                   for pair in public_merges)):
        raise Hold("TOKENIZER_CANONICAL_HOLD: complete original strings and public ordered merge pairs required")
    reconstructed = [" ".join(pair) for pair in public_merges]
    if reconstructed != original_merges:
        raise Hold("TOKENIZER_CANONICAL_HOLD: every merge must reverse-join exactly in its original position")
    raw_sha = object_sha({key: raw.get(key) for key in PIPELINE})
    canonical_sha = object_sha({key: canonical.get(key) for key in PIPELINE})
    if (raw_sha, canonical_sha) != tuple(expected_pipeline_shas):
        raise Hold("TOKENIZER_CANONICAL_HOLD: pinned raw/public pipeline fingerprints differ")
    receipt = dict(public_roundtrip_before_frontend=True, original_json_expected_sha256=SMALL_PINS["tokenizer.json"],
        original_pipeline_sha256=raw_sha, canonical_pipeline_sha256=canonical_sha,
        original_ignore_merges_present=False, public_ignore_merges=False, merge_rules=expected_merge_count,
        ordered_reverse_join_exact=True, original_merge_strings_sha256=object_sha(original_merges),
        reconstructed_merge_strings_sha256=object_sha(reconstructed), public_merge_pairs_sha256=object_sha(public_merges),
        allowed_representation_changes=["OMITTED_IGNORE_MERGES_TO_FALSE", "MERGE_STRINGS_TO_ORDERED_PAIRS"],
        all_other_model_pipeline_and_original_added_tokens_exact=True)
    return backend, canonical, receipt


def validate_tokenizer(tokenizer, raw, metadata, declarations, *, baseline=None):
    if baseline is None:
        _, canonical, receipt = canonical_backend_baseline(raw)
    else:
        canonical, receipt = baseline
    observed = json.loads(tokenizer.backend_tokenizer.to_str())
    if any(observed.get(key) != canonical.get(key) for key in PIPELINE):
        raise Hold("TOKENIZER_PIPELINE_HOLD: exact pre-frontend public canonical BPE/pipeline required")
    observed_added = {row["id"]: {key: row[key] for key in TOKEN_FIELDS} for row in observed["added_tokens"]}
    if observed_added != declarations["decoder"] or tokenizer.get_vocab() != declarations["vocabulary"]:
        raise Hold("TOKENIZER_IDS_HOLD: exact 33 declared ID/property records required; no resize/remap/drop")
    if list(tokenizer.extra_special_tokens) != declarations["extras"]:
        raise Hold("TOKENIZER_FRONTEND_HOLD: the entire legacy extra13 list must survive in the official V5 list")
    for name, value in declarations["named"].items():
        if getattr(tokenizer, name, None) != value or getattr(tokenizer, name + "_id", None) != declarations["vocabulary"][value]:
            raise Hold("TOKENIZER_FRONTEND_HOLD: every named7 token and native ID is required")
    for name in ("bos_token", "eos_token", "pad_token", "unk_token"):
        if getattr(tokenizer, name) != metadata.get(name):
            raise Hold("TOKENIZER_FRONTEND_HOLD: declared control token differs: " + name)
    expected_specials = {token for token in (metadata.get("bos_token"), metadata.get("eos_token"),
        metadata.get("pad_token"), metadata.get("unk_token"), *declarations["extras"], *declarations["named"].values()) if token is not None}
    if (set(tokenizer.all_special_tokens) != expected_specials
            or tokenizer.model_max_length != metadata["model_max_length"]
            or tokenizer.clean_up_tokenization_spaces != metadata["clean_up_tokenization_spaces"]
            or tokenizer.split_special_tokens != metadata["split_special_tokens"]
            or tokenizer.chat_template != metadata.get("chat_template")):
        raise Hold("TOKENIZER_FRONTEND_HOLD: complete frontend special/options contract differs")
    return dict(passed=True, backend_class=type(tokenizer).__name__, original_json_added_tokens=len(declarations["original"]),
        config_added_tokens=len(observed_added), extra_list=list(tokenizer.extra_special_tokens),
        named_tokens=dict(declarations["named"]), composed_backend_sha256=object_sha(observed),
        original_pipeline_sha256=object_sha({key: raw.get(key) for key in PIPELINE}),
        canonical_serialization=receipt,
        vocabulary_size=len(declarations["vocabulary"]), maximum_id=max(declarations["vocabulary"].values()),
        tokenizer_class_metadata=metadata["tokenizer_class"], declared_composition_not_raw_byte_identity=True)


def build_tokenizer(raw, metadata, *, api=None, expected_counts=(22, 33, 13, 7), expected_merge_count=MERGE_RULES,
                    expected_pipeline_shas=(RAW_PIPELINE_SHA, CANONICAL_PIPELINE_SHA)):
    """Public APIs only: original backend + exact declared additions + V5 frontend.

    No model-specific regex reconstruction, attribute injection, ID mapping or
    dropping config-only tokens. Legacy extra13 and named7 use separate official
    V5 constructor arguments, avoiding their mutually exclusive old spelling.
    """
    if api is None:
        import tinylm  # Apply project cache routing for standalone tokenizer callers.
        from tokenizers import Tokenizer, AddedToken
        from transformers import TokenizersBackend
    else:
        Tokenizer, AddedToken, TokenizersBackend = api
    declarations = tokenizer_declarations(raw, metadata, expected_counts=expected_counts)
    backend, canonical, receipt = canonical_backend_baseline(raw, api=Tokenizer,
        expected_merge_count=expected_merge_count, expected_pipeline_shas=expected_pipeline_shas)
    for index, row in sorted(declarations["decoder"].items()):
        if index not in declarations["original"]:
            token = AddedToken(**row)
            (backend.add_special_tokens if row["special"] else backend.add_tokens)([token])
        if backend.token_to_id(row["content"]) != index:
            raise Hold("TOKENIZER_IDS_HOLD: public backend registration changed a declared ID")
    tokenizer = TokenizersBackend(tokenizer_object=backend,
        **{name: metadata.get(name) for name in ("bos_token", "eos_token", "pad_token", "unk_token")},
        extra_special_tokens=[AddedToken(**declarations["decoder"][declarations["vocabulary"][token]])
                              for token in declarations["extras"]],
        model_specific_special_tokens=dict(declarations["named"]),
        model_max_length=metadata["model_max_length"], clean_up_tokenization_spaces=metadata["clean_up_tokenization_spaces"],
        split_special_tokens=metadata["split_special_tokens"], chat_template=metadata.get("chat_template"))
    return tokenizer, validate_tokenizer(tokenizer, raw, metadata, declarations, baseline=(canonical, receipt))


def verify_consumption(body, inventory, read_tensor, torch):
    state = body.state_dict()
    expected = set(inventory["mapping"].values()) | {"lm_head.weight"}
    if set(state) != expected or any(value.dtype != torch.float32 for value in state.values()):
        raise ValueError("exact mapped language state plus one tied-head alias, all FP32, required")
    embedding = body.get_input_embeddings().weight
    head = body.get_output_embeddings().weight
    if head is not embedding or tuple(head.shape) != tuple(embedding.shape):
        raise ValueError("the absent checkpoint head must be the actual input embedding Parameter alias")
    receipts = []
    for source, target in sorted(inventory["mapping"].items()):
        actual = state[target].detach().cpu().contiguous()
        wanted = read_tensor(source).detach().cpu().to(dtype=torch.float32).contiguous()
        if tuple(actual.shape) != tuple(inventory["language"][source]["shape"]) or tuple(wanted.shape) != tuple(actual.shape):
            raise ValueError("loaded/checkpoint language shape differs: " + source)
        if not torch.equal(actual, wanted):
            raise ValueError("actual loaded language value differs after FP32 conversion: " + source)
        raw = actual.view(torch.uint8).numpy().tobytes()
        receipts.append(dict(source=source, target=target, shape=list(actual.shape),
            original_dtype=inventory["language"][source]["dtype"], loaded_dtype="float32",
            fp32_value_sha256=hashlib.sha256(raw).hexdigest().upper(), exact_equal=True))
        del actual, wanted, raw
    return dict(passed=True, consumed_language_keys=len(receipts), state_keys=len(state),
        language_values=receipts, tied_head_alias=True, unused=inventory["unused"],
        unused_vision_keys=inventory["unused_vision_keys"], unused_mtp_keys=inventory["unused_mtp_keys"],
        nonuse_scope=inventory["nonuse_scope"], unaccounted_keys=0)


def audited_hflm_type(hflm, vocab, torch, writer, check):
    from scripts.p106b_official_lm_adapter import plan_tokens
    parent = external.head_guard_type(hflm, vocab)
    class AuditedQwenHFLM(parent):
        def _model_call(self, inps, attn_mask=None, labels=None):
            check()
            if attn_mask is not None or labels is not None:
                raise ValueError("causal likelihood only; no seq2seq or loss-mask forwarding")
            with torch.no_grad(), torch.autocast(device_type=self.device.type, enabled=False):
                output = self.model(input_ids=inps, use_cache=False, past_key_values=None, logits_to_keep=0)
            if output.past_key_values is not None or output.logits.dtype != torch.float32 or tuple(output.logits.shape) != (*inps.shape, vocab):
                raise ValueError("stateless full FP32 B*T*V output required")
            check()
            return output.logits

        def _loglikelihood_tokens(self, requests, *args, **kwargs):
            requests = list(requests)
            for key, context, continuation in requests:
                plan = plan_tokens(context, continuation, vocab, self.max_length)
                writer.append(dict(context_tokens=len(context), continuation_tokens=len(continuation),
                    truncated_context_tokens=plan.truncated_context_tokens, key_sha256=object_sha(key)))
            return super()._loglikelihood_tokens(requests, *args, **kwargs)
    return AuditedQwenHFLM


@contextmanager
def model_runtime(torch, assets, writer, check, proof, signature):
    body = lm = None
    primary = None
    try:
        import tinylm  # Apply project-local HF policy before any HF import.
        from scripts.prepare_p106b_official_eval import configure_hf_cache
        proof["cache_policy"] = configure_hf_cache()
        from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
        from lm_eval.models.huggingface import HFLM
        from safetensors import safe_open
        from scripts.interactive_research_infer import state_fingerprint
        proof["hflm_source"] = external.hflm_source_identity(HFLM)
        original_config = read_json(assets["files"]["config.json"]["resolved_path"])
        if original_config.get("model_type") != "qwen3_5" or original_config["architectures"] != ["Qwen3_5ForConditionalGeneration"]:
            raise ValueError("pinned outer conditional-generation config required")
        text_config = Qwen3_5TextConfig.from_pretrained(str(MODEL_DIR), local_files_only=True)
        for key, value in original_config["text_config"].items():
            if key not in ("dtype", "transformers_version") and getattr(text_config, key) != value:
                raise ValueError("official extracted text config differs: " + key)
        text_config.use_cache = False
        # Official storage-only selector; do not let another filename shadow this index.
        text_config.transformers_weights = INDEX
        raw = read_json(assets["files"]["tokenizer.json"]["resolved_path"])
        metadata = read_json(assets["files"]["tokenizer_config.json"]["resolved_path"])
        proof["tokenizer_load_attempted"] = True
        tokenizer, proof["tokenizer_composite_contract"] = build_tokenizer(raw, metadata)
        proof["tokenizer_loaded"] = True
        proof["imported_transformers_sources"] = imported_source_identity(signature)
        check()
        proof["model_load_attempted"] = True
        body, loading = Qwen3_5ForCausalLM.from_pretrained(str(MODEL_DIR), config=text_config,
            local_files_only=True, trust_remote_code=False, use_safetensors=True, dtype=torch.float32,
            attn_implementation="eager", output_loading_info=True, ignore_mismatched_sizes=False)
        proof["loading_info"] = external.json_ready(loading)
        if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise ValueError("official language loader has missing/extra/mismatched/error keys")
        with safe_open(assets["files"][WEIGHT]["resolved_path"], framework="pt", device="cpu") as source:
            proof["key_consumption"] = verify_consumption(body, assets["inventory"], source.get_tensor, torch)
        if (type(body).__name__ != "Qwen3_5ForCausalLM" or body.config.model_type != "qwen3_5_text"
                or body.config.vocab_size != 248320 or tuple(body.get_input_embeddings().weight.shape) != (248320, 1024)
                or body.config.use_cache or body.config._attn_implementation != "eager"
                or any(p.dtype != torch.float32 for p in body.parameters())):
            raise ValueError("actual text body/head/FP32/eager/cache contract differs")
        proof["tokenizer_admission"] = external.tokenizer_admission(MODEL, tokenizer, assets, body.config.vocab_size)
        body.eval()
        proof["initial_core_sha256"] = state_fingerprint(body)
        proof.update(model_loaded=True, model_class=type(body).__name__, parameters=sum(p.numel() for p in body.parameters()),
            language_layers=body.config.layer_types, backend_functions=[dict(layer=index,
                chunk=layer.linear_attn.chunk_gated_delta_rule.__module__ + "." + layer.linear_attn.chunk_gated_delta_rule.__name__,
                conv=None if layer.linear_attn.causal_conv1d_fn is None else layer.linear_attn.causal_conv1d_fn.__module__)
                for index, layer in enumerate(body.model.layers) if hasattr(layer, "linear_attn")])
        body.to("cuda")
        lm = audited_hflm_type(HFLM, body.config.vocab_size, torch, writer, check)(pretrained=body, tokenizer=tokenizer,
            backend="causal", max_length=1024, batch_size=1, device="cuda", logits_cache=False,
            add_bos_token=False, softmax_dtype=torch.float32, mixed_precision_dtype=None, trust_remote_code=False)
        lm.assert_special_ids()
        if (lm.prefix_token_id, lm.eot_token_id, tokenizer.pad_token_id) != (248044, 248044, 248044):
            raise ValueError("declared native empty-prefix/EOS/PAD IDs must remain exactly 248044")
        validate_tokenizer(lm.tokenizer, raw, metadata, tokenizer_declarations(raw, metadata))
        if state_fingerprint(body) != proof["initial_core_sha256"]:
            raise ValueError("official HFLM construction changed model values")
        proof.update(prefix_token_id=lm.prefix_token_id, eos_token_id=lm.eot_token_id, pad_token_id=tokenizer.pad_token_id)
        yield lm
    except BaseException as exc:
        primary = exc
        raise
    finally:
        failures = []
        if lm is not None:
            try:
                final_tokenizer = validate_tokenizer(lm.tokenizer, raw, metadata, tokenizer_declarations(raw, metadata))
                proof["tokenizer_unchanged"] = final_tokenizer == proof["tokenizer_composite_contract"]
                if not proof["tokenizer_unchanged"]:
                    failures.append("runtime tokenizer changed")
            except BaseException as exc:
                proof["tokenizer_unchanged"] = False
                failures.append("runtime tokenizer verification: " + str(exc)[:300])
        if body is not None and "initial_core_sha256" in proof:
            try:
                proof["final_core_sha256"] = state_fingerprint(body)
                proof["body_unchanged"] = proof["final_core_sha256"] == proof["initial_core_sha256"]
                if not proof["body_unchanged"]:
                    failures.append("model body changed")
            except BaseException as exc:
                failures.append("body verification: " + str(exc)[:300])
        try:
            if lm is not None:
                lm._model = None
            if body is not None:
                body.to("cpu")
        except BaseException as exc:
            failures.append("owned model cleanup: " + str(exc)[:300])
        finally:
            lm = body = None
            try:
                gc.collect()
                torch.cuda.empty_cache()
                zero_owned_allocation = torch.cuda.memory_allocated() == 0
            except BaseException as exc:
                failures.append("owned allocator cleanup: " + str(exc)[:300])
                zero_owned_allocation = False
        proof["exit_errors"] = failures
        proof["owned_cleanup_complete"] = not failures and zero_owned_allocation
        if failures and primary is None:
            raise ValueError("; ".join(failures))


def hybrid_canary(lm, torch, *, check=lambda: None):
    """Synthetic numerical/state trace only; never benchmark quality."""
    from lm_eval.api.instance import Instance
    cases = [("Alpha prefix", " answer"), ("Different context", " continuation"), ("", "Hello")]
    requests = [Instance(request_type="loglikelihood", doc={}, arguments=pair, idx=i,
        metadata=("qwen35_hybrid_canary", i, 1)) for i, pair in enumerate(cases)]
    a = lm.loglikelihood([requests[0]], disable_tqdm=True)
    lm.loglikelihood([requests[1]], disable_tqdm=True)
    repeated = lm.loglikelihood([requests[0]], disable_tqdm=True)
    aba = external.compare_scores(a, repeated)
    ordered = lm.loglikelihood(requests, disable_tqdm=True)
    reversed_scores = lm.loglikelihood(list(reversed(requests)), disable_tqdm=True)
    order = external.compare_scores(ordered, list(reversed(reversed_scores)))
    ids = lm.tok_encode("Prefix for a causal state check", add_special_tokens=False)
    tail1 = lm.tok_encode(" one future", add_special_tokens=False)
    tail2 = lm.tok_encode(" another different future", add_special_tokens=False)
    if not ids or not tail1 or not tail2:
        raise ValueError("nonempty synthetic prefix/future token plans required")
    def forward(sequence):
        check()
        inputs = torch.tensor([sequence], dtype=torch.long, device=lm.device)
        output = lm.model(input_ids=inputs, use_cache=False, past_key_values=None, logits_to_keep=0)
        if (output.past_key_values is not None or output.logits.dtype != torch.float32
                or tuple(output.logits.shape) != (1, len(sequence), lm.model.config.vocab_size)):
            raise ValueError("hybrid forward returned state or non-FP32 logits")
        return output.logits.detach()
    prefix = forward(ids)
    first, second = forward(ids + tail1), forward(ids + tail2)
    checks = []
    for label, value in (("prefix_vs_future1", first), ("prefix_vs_future2", second)):
        observed = value[:, :len(ids), :]
        close = torch.allclose(prefix, observed, atol=official.ATOL, rtol=official.RTOL)
        difference = float((prefix - observed).abs().max())
        checks.append(dict(test=label, close=bool(close), maximum_absolute_difference=difference))
        if not close or not math.isfinite(difference):
            raise ValueError("hybrid future/prefix numerical oracle negative: " + label)
    del prefix, first, second
    return dict(passed=True, quality_claim=False, aba=aba, request_order=order, prefix_future=checks,
        state_output_none=True, use_cache=False, atol=official.ATOL, rtol=official.RTOL)


def pin_manifest(directory, stem, manifest, pins):
    from scripts.p106b_shards import verify
    verify(directory, manifest)
    pins[str(directory / (stem + "_shards_manifest.json"))] = digest(directory / (stem + "_shards_manifest.json"))
    pins.update({str(directory / row["path"]): row["sha256"] for row in manifest["shards"]})


def evaluate(lm, torch, directory, report, tasks, mode, check, pins):
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    from scripts.p106b_shards import ShardWriter
    harness_definition_identity(report["source_identity"])
    expected, manager = official.expected_counts(mode), TaskManager()
    report.update(actual_counts={}, independent_audits={}, official_results={}, sample_manifests={}, task_evaluation_seconds={})
    for name, task in tasks.items():
        check()
        tick = time.perf_counter()
        result = simple_evaluate(model=lm, tasks=[task], num_fewshot=0, task_manager=manager, batch_size=1,
            device="cuda", use_cache=None, cache_requests=False, limit=32 if mode == "cost" else None,
            bootstrap_iters=100000, log_samples=True, apply_chat_template=False, fewshot_as_multiturn=False,
            random_seed=1337, numpy_random_seed=1337, torch_random_seed=1337, fewshot_random_seed=1337)
        torch.cuda.synchronize()
        report["task_evaluation_seconds"][name] = time.perf_counter() - tick
        if set(result["samples"]) != {name}:
            raise ValueError("official result task identity differs")
        rows = result.pop("samples")[name]
        in_memory = official.audit_samples(task, rows, expected[name])
        writer = ShardWriter(directory, name + "_samples", limit=19_999_999)
        primary = None
        try:
            for row in rows:
                writer.append(official.plain(row))
        except BaseException as exc:
            primary = exc
            raise
        finally:
            if writer._total_rows:
                try:
                    manifest = writer.close(lineage=dict(tag=TAG, model=MODEL, task=name, mode=mode))
                    report["sample_manifests"][name] = manifest
                    pin_manifest(directory, name + "_samples", manifest, pins)
                except BaseException as exc:
                    report.setdefault("writer_errors", []).append(dict(task=name, type=type(exc).__name__, message=str(exc)[:1000]))
                    if primary is None:
                        raise
        audit = external.recount_raw(task, directory, manifest, expected[name])
        if any(audit[key] != value for key, value in in_memory.items()):
            raise ValueError("raw disk recount differs from in-memory official audit")
        for metric, count in (("acc", "correct"), ("acc_norm", "correct_norm")):
            score = result["results"][name].get(metric + ",none")
            if score is not None and not math.isclose(score, audit[count] / expected[name], abs_tol=1e-12):
                raise ValueError("official metric differs from independent whole raw recount")
        report["independent_audits"][name], report["actual_counts"][name] = audit, expected[name]
        report["official_results"][name] = official.plain(result)
        check()
    choices = sum(row["choice_likelihoods"] for row in report["independent_audits"].values())
    if report["actual_counts"] != expected or (mode == "full" and (sum(expected.values()), choices) != (19965, 67106)):
        raise ValueError("complete exact Core6 denominator and choice count required")
    report.update(raw_independent_recount=True, actual_rows=sum(expected.values()), choice_likelihoods=choices)


def window(deadline, max_wall_sec, mode, *, now=None):
    parsed = datetime.fromisoformat(deadline)
    now = time.time() if now is None else now
    upper = 7200 if mode == "full" else 600
    if mode not in ("canary", "cost", "full") or parsed.tzinfo is None or parsed.timestamp() > LATEST:
        raise ValueError("explicit registered phase and timezone deadline no later than 08:40 required")
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= upper or not finite(now):
        raise ValueError("explicit valid phase cap and observed clock required")
    available = min(max_wall_sec, int(parsed.timestamp() - now - 30))
    if available < 60:
        raise Hold("DEADLINE_BUDGET: less than 60 seconds remain after cleanup reserve")
    return dict(deadline=parsed.isoformat(), deadline_epoch=parsed.timestamp(), hard_cap_seconds=available, cleanup_reserve_seconds=30)


def remaining(admission, started, *, elapsed=None, now=None):
    elapsed = time.perf_counter() - started if elapsed is None else elapsed
    now = time.time() if now is None else now
    if not finite(elapsed) or not finite(now):
        raise ValueError("finite nonnegative observed elapsed/wall clocks required")
    value = min(admission["hard_cap_seconds"] - elapsed, admission["deadline_epoch"] - 30 - now)
    if not finite(value, positive=True):
        raise TimeoutError("whole phase including cleanup/report/closure exceeded cap/deadline")
    return value


@contextmanager
def wall_limit(seconds):
    if not finite(seconds, positive=True) or any(signal.getitimer(signal.ITIMER_REAL)):
        raise ValueError("positive, nonnested owner phase timer required")
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*args):
        raise TimeoutError("owned Qwen35 phase wall limit exceeded")
    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds, .05)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def fail(report, error, primary=None):
    original = error if primary is None else primary
    if error is not original:
        report.setdefault("secondary_errors", []).append(dict(type=type(error).__name__, message=str(error)[:1000]))
    report.update(status="QWEN35_HOLD" if isinstance(original, Hold) and error is original else "QWEN35_PARTIAL",
        returncode=130 if isinstance(original, KeyboardInterrupt) else 8 if isinstance(original, Hold) and error is original else 9,
        quality_claim=False, error_type=type(original).__name__, error=str(original)[:2000],
        timed_out=isinstance(original, TimeoutError))
    return original


def finalize(report, directory, started, signature, pins, admission, *, primary=None, idle_fn=None,
             identity_fn=identity, verify_fn=verify_pins, timer=wall_limit, clock=time.perf_counter, wall=time.time,
             write=external.write_json, read=read_json, hash_fn=digest, close=external.close_report):
    directory = Path(directory)
    report_path, closure_path, veto_path = (directory / name for name in ("report.json", "phase_closure.json", "phase_veto.json"))
    budget = lambda: remaining(admission, started, elapsed=clock() - started, now=wall())
    saved = None
    try:
        with timer(budget()):
            report["sources_unchanged"] = identity_fn() == signature
            verify_fn(pins)
            report["inputs_unchanged"] = True
            if not report["sources_unchanged"]:
                raise ValueError("source changed at closure")
            for predecessor in report.get("prerequisite_phase_directories", []):
                veto = Path(predecessor) / "phase_veto.json"
                if veto.exists() or veto.is_symlink():
                    raise ValueError("a prerequisite gained a veto before terminal closure")
            if report.get("model_load_attempted"):
                proof = report.get("model_proof", {})
                if proof.get("owned_cleanup_complete") is not True:
                    raise ValueError("owned model cleanup incomplete")
                if proof.get("model_loaded") and proof.get("body_unchanged") is not True:
                    raise ValueError("loaded body verification incomplete")
                if idle_fn is None:
                    raise ValueError("owned GPU cleanup point query missing")
                report["gpu_idle_after_cleanup"] = idle_fn()
            if report["returncode"] == 0:
                verify_model_proof(report, report["assets"])
            budget()
            report.update(ended_at=datetime.now(timezone.utc).isoformat(), wall_seconds=clock() - started,
                closure_contract=CONTRACT)
            close(report_path, report, primary_error=primary)
            budget()
            saved = read(report_path)
            if saved != external.json_ready(report):
                raise ValueError("stored report/fallback differs from the terminal report")
            report_sha = hash_fn(report_path)
            observed, wall_epoch = clock() - started, wall()
            remaining(admission, started, elapsed=observed, now=wall_epoch)
            closure = dict(schema=CLOSURE_SCHEMA, tag=TAG, model=MODEL, mode=report["mode"], returncode=report["returncode"],
                status="CLOSED_WITHIN_OBSERVED_BOUNDS", source_sha256=signature["sha256"], report_sha256=report_sha,
                admission=admission, observed_elapsed_seconds=observed, observed_wall_epoch=wall_epoch,
                contract=CONTRACT, report_closed_re_read=True, atomicity_claim=False, root_actual_exit0_required=True)
            write(closure_path, closure)
            if read(closure_path) != closure or hash_fn(report_path) != report_sha or veto_path.exists() or veto_path.is_symlink():
                raise ValueError("terminal closure/report changed or veto exists")
            closure_sha = hash_fn(closure_path)
            budget()
        budget()
        report.update(phase_closure_verified=True, phase_closure_sha256=closure_sha, phase_completion_wall_seconds=clock() - started)
        remaining(admission, started, elapsed=report["phase_completion_wall_seconds"], now=wall())
    except BaseException as exc:
        original = primary if primary is not None else exc
        fail(report, exc, original)
        report.update(returncode=130 if isinstance(original, KeyboardInterrupt) else 9, status="QWEN35_CLOSURE_VETO",
            phase_closure_verified=False, closure_error=dict(type=type(exc).__name__, message=str(exc)[:1000]))
        veto = dict(schema=CLOSURE_SCHEMA, tag=TAG, model=MODEL, mode=report["mode"], status="VETO", returncode=report["returncode"],
            original_error=dict(type=type(original).__name__, message=str(original)[:2000]), closure_error=report["closure_error"],
            source_sha256=signature["sha256"], preserved_report_returncode=None if saved is None else saved.get("returncode"), contract=CONTRACT)
        try:
            write(veto_path, veto)
        except BaseException as veto_error:
            print(json.dumps(dict(event="QWEN35_VETO_WRITE_FAILED", veto=veto, error=str(veto_error)[:1000])), file=sys.stderr, flush=True)
    return report


def closed_prerequisite(directory, mode, signature, assets, pins):
    directory = Path(directory)
    if (directory / "phase_veto.json").exists() or (directory / "phase_veto.json").is_symlink():
        raise ValueError("vetoed phase cannot be a prerequisite")
    path, closure_path = directory / "report.json", directory / "phase_closure.json"
    report, closure = read_json(path), read_json(closure_path)
    expected = dict(schema=SCHEMA, tag=TAG, model=MODEL, mode=mode, returncode=0,
        status="QWEN35_" + mode.upper() + "_COMPLETE", source_identity=signature, policy=policy(), assets=assets,
        sources_unchanged=True, inputs_unchanged=True, numerical_canary_passed=True)
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("exact closed same-source/model/assets/policy prerequisite required")
    verify_model_proof(report, assets)
    expected_closure = dict(schema=CLOSURE_SCHEMA, tag=TAG, model=MODEL, mode=mode, returncode=0,
        status="CLOSED_WITHIN_OBSERVED_BOUNDS", source_sha256=signature["sha256"], report_sha256=digest(path),
        admission=report["admission"], contract=CONTRACT, report_closed_re_read=True, atomicity_claim=False,
        root_actual_exit0_required=True)
    if any(closure.get(key) != value for key, value in expected_closure.items()):
        raise ValueError("final closure required; stored report0 is insufficient")
    admission = report["admission"]
    if (type(admission.get("hard_cap_seconds")) is not int or not 60 <= admission["hard_cap_seconds"] <= (7200 if mode == "full" else 600)
            or admission.get("cleanup_reserve_seconds") != 30 or not finite(admission.get("deadline_epoch"))
            or admission["deadline_epoch"] > LATEST or not finite(report.get("wall_seconds"))
            or not finite(closure.get("observed_elapsed_seconds")) or report["wall_seconds"] > closure["observed_elapsed_seconds"]):
        raise ValueError("invalid closed phase time contract")
    remaining(admission, 0, elapsed=closure.get("observed_elapsed_seconds"), now=closure.get("observed_wall_epoch"))
    pins.update({str(path): digest(path), str(closure_path): digest(closure_path)})
    if (directory / "phase_veto.json").exists():
        raise ValueError("veto appeared while reading prerequisite")
    return dict(report, validated_closure_elapsed_seconds=closure["observed_elapsed_seconds"])


def verify_model_proof(report, assets):
    proof = report.get("model_proof", {})
    inventory = assets.get("inventory", {})
    consumption = proof.get("key_consumption", {})
    tokenizer = proof.get("tokenizer_composite_contract", {})
    required = dict(passed=True, consumed_language_keys=320, state_keys=321, tied_head_alias=True,
                    unused_vision_keys=153, unused_mtp_keys=15, unaccounted_keys=0)
    if (report.get("model_load_attempted") is not True or any(consumption.get(k) != v for k, v in required.items())
            or consumption.get("unused") != inventory.get("unused")
            or proof.get("model_class") != "Qwen3_5ForCausalLM"
            or any(proof.get(key) is not True for key in
                   ("model_loaded", "body_unchanged", "owned_cleanup_complete", "tokenizer_unchanged"))
            or report.get("numerical_canary", {}).get("passed") is not True
            or report.get("hybrid_canary", {}).get("passed") is not True
            or tokenizer.get("passed") is not True or tokenizer.get("original_json_added_tokens") != 22
            or tokenizer.get("config_added_tokens") != 33 or len(tokenizer.get("extra_list", [])) != 13
            or len(tokenizer.get("named_tokens", {})) != 7):
        raise ValueError("complete strict language/tied-head/tokenizer/hybrid/CE/cleanup proof required")
    rows = consumption.get("language_values", [])
    if (len(rows) != 320 or {row.get("source") for row in rows} != set(inventory.get("mapping", {}))
            or any(row.get("target") != inventory["mapping"][row["source"]]
                   or row.get("shape") != inventory["language"][row["source"]]["shape"]
                   or row.get("original_dtype") != inventory["language"][row["source"]]["dtype"]
                   or row.get("exact_equal") is not True or row.get("loaded_dtype") != "float32"
                   or not isinstance(row.get("fp32_value_sha256"), str) or len(row["fp32_value_sha256"]) != 64 for row in rows)):
        raise ValueError("every language tensor must have its own exact FP32 value receipt")


def full_admission(cost, admission, started, *, elapsed=None, now=None):
    timing = cost.get("task_evaluation_seconds", {})
    cost_elapsed = cost.get("validated_closure_elapsed_seconds")
    if (cost.get("actual_counts") != official.expected_counts("cost") or cost.get("raw_independent_recount") is not True
            or set(timing) != set(official.TASK_COUNTS) or any(not finite(v, positive=True) for v in timing.values())
            or not finite(cost.get("wall_seconds"), positive=True) or cost["wall_seconds"] < sum(timing.values())
            or not finite(cost_elapsed, positive=True) or cost_elapsed < cost["wall_seconds"]):
        raise ValueError("exact six-task fresh cost32 timing and raw recount required")
    overhead = cost_elapsed - sum(timing.values())
    forecast = 1.5 * sum(official.TASK_COUNTS[k] * v / 32 for k, v in timing.items()) + overhead + 120
    available = remaining(admission, started, elapsed=elapsed, now=now)
    if forecast > available:
        raise Hold("FORECAST_BUDGET: fresh full extrapolation exceeds remaining cap/deadline")
    return dict(forecast_seconds=forecast, remaining_at_admission_seconds=available,
        forecast_multiplier=1.5, observed_non_eval_overhead_seconds=overhead, fixed_overhead_reserve_seconds=120)


def execute(mode, expected_source, deadline, max_wall_sec, *, prior_process_exit0=False):
    started = time.perf_counter()
    admission = window(deadline, max_wall_sec, mode)
    with wall_limit(max(.001, remaining(admission, started) - 20)):
        signature = identity()
        if signature["sha256"] != expected_source:
            raise ValueError("preregistered complete source identity differs")
        if mode != "canary" and prior_process_exit0 is not True:
            raise Hold("OWNER_EXIT_WITNESS: root must explicitly confirm prerequisite process exit0")
        directory = OUTPUT / mode
        if any(p.is_symlink() for p in (directory, *directory.parents)):
            raise ValueError("linked output path refused")
        directory.mkdir(parents=True, exist_ok=False)
    pins = {}
    report = dict(schema=SCHEMA, tag=TAG, model=MODEL, mode=mode, source_identity=signature, policy=policy(), admission=admission,
        status="STARTED", returncode=9, quality_claim=False, training=False, optimizer_updates=0, checkpoint_writes=0,
        model_load_attempted=False, sources_unchanged=False, inputs_unchanged=False,
        started_at=datetime.now(timezone.utc).isoformat(), owner_prior_exit0_asserted=prior_process_exit0,
        closure_contract=CONTRACT, immutable_pins=pins, prerequisite_phase_directories=[],
        contamination="PRETRAINING_OVERLAP_NOT_AUDITED")
    primary, idle_fn, torch, writer = None, None, None, None
    def check():
        if remaining(admission, started) <= 20:
            raise TimeoutError("preserving terminal cleanup/report reserve")
    try:
        with wall_limit(max(.001, remaining(admission, started) - 20)):
            assets = asset_identity()
            report["assets"] = assets
            pins.update({item["resolved_path"]: item["sha256"] for item in assets["files"].values()})
            canary = cost = None
            if mode != "canary":
                canary = closed_prerequisite(OUTPUT / "canary", "canary", signature, assets, pins)
                report["prerequisite_phase_directories"].append(str(OUTPUT / "canary"))
                report["canary_report_sha256"] = digest(OUTPUT / "canary/report.json")
                if mode == "full":
                    cost = closed_prerequisite(OUTPUT / "cost", "cost", signature, assets, pins)
                    report["prerequisite_phase_directories"].append(str(OUTPUT / "cost"))
                    if cost.get("canary_report_sha256") != report["canary_report_sha256"]:
                        raise ValueError("fresh cost must descend from this exact canary")
                    report["forecast"] = full_admission(cost, admission, started)
            for name, value in official.OFFLINE.items():
                os.environ[name] = value
            import tinylm  # Explicit existing project cache policy, no environment-file writes.
            from scripts.prepare_p106b_official_eval import configure_hf_cache, ASSETS, MANIFEST_SHA, COMMIT
            report["cache_policy"] = configure_hf_cache()
            from scripts.p106b_official_tasks import load_tasks
            tasks, specs, framework = load_tasks()
            report.update(framework_commit=COMMIT, task_specs=specs, framework_provenance=framework, data_manifest_sha256=MANIFEST_SHA)
            report["harness_definition_sources"] = harness_definition_identity(signature)
            pins.update(report["harness_definition_sources"])
            pins[str(ASSETS / "manifest.json")] = MANIFEST_SHA
            for spec in specs:
                pins[str(spec["official_yaml"])] = digest(spec["official_yaml"])
                pins[str(spec["data_file"])] = spec["data_sha256"]
            check()
            from scripts.interactive_research_infer import require_idle_gpu
            idle_fn = require_idle_gpu
            report["gpu_idle_before_model"] = idle_fn()
            import torch
            from torch.nn.attention import sdpa_kernel, SDPBackend
            from scripts.p106b_shards import ShardWriter
            torch.set_num_threads(4); torch.manual_seed(1337)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            proof = report["model_proof"] = {}
            writer = ShardWriter(directory, "token_lengths", limit=19_999_999)
            report["runtime_open_attempted"] = True
            try:
                with sdpa_kernel(SDPBackend.MATH), torch.no_grad():
                    with model_runtime(torch, assets, writer, check, proof, signature) as lm:
                        report["numerical_canary"] = external.numerical_canary(lm, torch)
                        report["hybrid_canary"] = hybrid_canary(lm, torch, check=check)
                        report["numerical_canary_passed"] = True
                        report["length_rows_before_tasks"] = writer._total_rows
                        report["pre_evaluation_seconds"] = time.perf_counter() - started
                        if cost is not None:
                            report["forecast_after_startup"] = full_admission(cost, admission, started)
                        if mode != "canary":
                            evaluate(lm, torch, directory, report, tasks, mode, check, pins)
                            if writer._total_rows - report["length_rows_before_tasks"] != report["choice_likelihoods"]:
                                raise ValueError("actual length trace does not cover every official choice exactly once")
            finally:
                report["model_load_attempted"] = proof.get("model_load_attempted", False)
                report["tokenizer_load_attempted"] = proof.get("tokenizer_load_attempted", False)
            report.update(status="QWEN35_" + mode.upper() + "_COMPLETE", returncode=0, quality_claim=mode == "full")
            check()
    except BaseException as exc:
        primary = fail(report, exc, primary)
    finally:
        try:
            with wall_limit(remaining(admission, started)):
                if writer is not None and writer._total_rows:
                    report["length_manifest"] = writer.close(lineage=dict(tag=TAG, model=MODEL, mode=mode))
                    pin_manifest(directory, "token_lengths", report["length_manifest"], pins)
        except BaseException as exc:
            primary = fail(report, exc, primary)
        finalize(report, directory, started, signature, pins, admission, primary=primary, idle_fn=idle_fn)
    return {key: report.get(key) for key in ("status", "returncode", "mode", "actual_rows", "choice_likelihoods", "wall_seconds",
        "phase_closure_verified", "phase_closure_sha256", "phase_completion_wall_seconds", "error_type", "error", "closure_contract")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--mode", choices=("canary", "cost", "full"))
    parser.add_argument("--source-sha256")
    parser.add_argument("--deadline")
    parser.add_argument("--max-wall-sec", type=int)
    parser.add_argument("--prior-process-exit0", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.execute:
            if any(getattr(args, name) is None for name in ("mode", "source_sha256", "deadline", "max_wall_sec")):
                parser.error("execute requires explicit phase/source/deadline/cap")
            result = execute(args.mode, args.source_sha256, args.deadline, args.max_wall_sec,
                             prior_process_exit0=args.prior_process_exit0)
        else:
            result = dict(status="SOURCE_ONLY", model=MODEL, tag=TAG, policy=policy(), source_identity=identity(),
                models=0, tokenizers=0, gpu_calls=0, installs=0, downloads=0, latest_deadline="2026-10-24T08:40:00+09:00")
    except BaseException as exc:
        result = dict(status="QWEN35_ADMISSION_HOLD" if isinstance(exc, Hold) else "QWEN35_ADMISSION_ERROR",
            returncode=8 if isinstance(exc, Hold) else 130 if isinstance(exc, KeyboardInterrupt) else 9,
            error_type=type(exc).__name__, error=str(exc)[:2000], quality_claim=False)
    print(json.dumps(external.json_ready(result), ensure_ascii=False, sort_keys=True), flush=True)
    return result.get("returncode", 0)


if __name__ == "__main__":
    raise SystemExit(main())
