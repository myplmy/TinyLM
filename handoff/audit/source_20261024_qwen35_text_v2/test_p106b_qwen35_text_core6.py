#!/usr/bin/env python3
"""Synthetic stdlib CPU regressions only; no actual tokenizer/model/GPU import."""
from __future__ import annotations

import ast
import builtins
from contextlib import nullcontext, redirect_stdout
import copy
import io
import json
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_qwen35_text_core6 as run


class Added:
    def __init__(self, **properties):
        self.properties = dict(properties)

    def __str__(self):
        return self.properties["content"]


class Backend:
    def __init__(self, raw):
        self.raw = copy.deepcopy(raw)

    @classmethod
    def from_str(cls, raw):
        value = json.loads(raw)
        if value["model"].get("type") == "BPE":
            value["model"].setdefault("ignore_merges", False)
            value["model"]["merges"] = [pair.split(" ") if isinstance(pair, str) else pair for pair in value["model"]["merges"]]
        return cls(value)

    def to_str(self):
        return json.dumps(self.raw)

    def token_to_id(self, content):
        return self.vocabulary().get(content)

    def vocabulary(self):
        return {**self.raw["model"]["vocab"], **{row["content"]: row["id"] for row in self.raw["added_tokens"]}}

    def add_tokens(self, tokens):
        for token in tokens:
            content = str(token)
            old = self.token_to_id(content)
            if old is None:
                self.raw["added_tokens"].append(dict(token.properties, id=max(self.vocabulary().values()) + 1))

    add_special_tokens = add_tokens


class Frontend:
    def __init__(self, *, tokenizer_object, extra_special_tokens, model_specific_special_tokens, **kwargs):
        self.backend_tokenizer = Backend.from_str(tokenizer_object.to_str())
        self.extra_special_tokens = list(map(str, extra_special_tokens))
        self.named = dict(model_specific_special_tokens)
        for name, value in {**kwargs, **self.named}.items():
            setattr(self, name, value)

    def get_vocab(self):
        return self.backend_tokenizer.vocabulary()

    @property
    def all_special_tokens(self):
        return list({value for value in [self.bos_token, self.eos_token, self.pad_token, self.unk_token,
            *self.extra_special_tokens, *self.named.values()] if value is not None})

    def __getattr__(self, key):
        if key.endswith("_id"):
            content = getattr(self, key[:-3])
            return None if content is None else self.get_vocab()[content]
        raise AttributeError(key)


def tokenizer_fixture():
    props = {index: dict(content="added" + str(index), single_word=False, lstrip=False,
        rstrip=False, normalized=False, special=True) for index in range(4, 37)}
    for index in range(26, 30):
        props[index]["special"] = False
    raw = dict(version="1.0", added_tokens=[dict(value, id=index) for index, value in props.items() if index < 26],
        model=dict(type="BPE", vocab={"base" + str(index): index for index in range(4)},
                   merges=["base0 base1", "base1 base2"]),
        normalizer=dict(type="NFC"), pre_tokenizer=dict(type="Split", pattern="PINNED_PATTERN"),
        post_processor=dict(type="ByteLevel", trim_offsets=False), decoder=dict(type="ByteLevel", trim_offsets=False),
        truncation=None, padding=None)
    metadata = dict(added_tokens_decoder={str(key): value for key, value in props.items()},
        additional_special_tokens=[props[i]["content"] for i in range(5, 18)],
        extra_special_tokens={"named" + str(i) + "_token": props[i + 14]["content"] for i in range(7)},
        bos_token=None, eos_token=props[4]["content"], pad_token=props[4]["content"], unk_token=None,
        model_max_length=262144, clean_up_tokenization_spaces=False, split_special_tokens=False,
        chat_template="DECLARED_BUT_DISABLED", tokenizer_class="OriginalDeclaredClass")
    return raw, metadata


class FakeTensor:
    def __init__(self, values, shape=(2,), dtype="float32"):
        self.values, self.shape, self.dtype = list(values), tuple(shape), dtype

    def detach(self):
        return self

    cpu = detach
    contiguous = detach
    numpy = detach

    def to(self, *, dtype):
        return FakeTensor(self.values, self.shape, dtype)

    def view(self, *args):
        return self

    def tobytes(self):
        return struct.pack("<" + "f" * len(self.values), *self.values)


class FakeTorch:
    float32, uint8 = "float32", "uint8"

    @staticmethod
    def equal(a, b):
        return a.shape == b.shape and a.values == b.values


def inventory_fixture():
    header = {}
    names = ["embed_tokens.weight", "norm.weight"] + ["layers." + str(i) + ".weight" for i in range(318)]
    for prefix, suffixes in ((run.LANGUAGE, names), (run.VISION, ["layer" + str(i) for i in range(153)]),
                             (run.MTP, ["layer" + str(i) for i in range(15)])):
        for suffix in suffixes:
            header[prefix + suffix] = dict(shape=[2], dtype="BF16", data_offsets=[0, 4])
    inventory = run.header_inventory(header)
    source = {name: FakeTensor([1., 2.], dtype="BF16") for name in inventory["mapping"]}
    state = {target: FakeTensor([1., 2.]) for target in inventory["mapping"].values()}
    embedding = state["model.embed_tokens.weight"]
    state["lm_head.weight"] = embedding
    body = SimpleNamespace(state_dict=lambda: state,
        get_input_embeddings=lambda: SimpleNamespace(weight=embedding),
        get_output_embeddings=lambda: SimpleNamespace(weight=state["lm_head.weight"]))
    return header, inventory, source, state, body


class Difference:
    def __init__(self, values):
        self.values = values

    def abs(self):
        return Difference([abs(value) for value in self.values])

    def max(self):
        return max(self.values)


class Logits:
    dtype = "float32"

    def __init__(self, values):
        self.values = list(values)
        self.shape = (1, len(values), 8)

    def __getitem__(self, item):
        return Logits(self.values[item[1]])

    def __sub__(self, other):
        return Difference([a - b for a, b in zip(self.values, other.values)])

    def detach(self):
        return self


class HybridTorch(FakeTorch):
    long = "long"

    @staticmethod
    def tensor(values, **kwargs):
        return SimpleNamespace(values=list(values[0]), shape=(1, len(values[0])))

    @staticmethod
    def allclose(a, b, **kwargs):
        return a.values == b.values


class Instance:
    def __init__(self, **kwargs):
        self.args = kwargs["arguments"]


class SyntheticLM:
    device = "cuda"

    def __init__(self, *, future=False, state=False, history=False):
        self.calls = 0
        self.history = history
        self.forward_flags = []
        def forward(input_ids, **kwargs):
            self.forward_flags.append(kwargs)
            values = input_ids.values
            logits = [sum(values) if future else sum(values[:i + 1]) for i in range(len(values))]
            return SimpleNamespace(logits=Logits(logits), past_key_values=object() if state else None)
        self.model = SimpleNamespace(config=SimpleNamespace(vocab_size=8), __call__=forward)
        self.model = type("SyntheticBody", (), {"config": SimpleNamespace(vocab_size=8),
            "__call__": lambda owner, **kwargs: forward(**kwargs)})()

    def tok_encode(self, text, **kwargs):
        return [ord(char) % 7 + 1 for char in text]

    def loglikelihood(self, requests, **kwargs):
        self.calls += 1
        return [(-float(sum(map(len, request.args))) - (self.calls if self.history else 0), False) for request in requests]


class TokenizerTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.metadata = tokenizer_fixture()

    def build(self, raw=None, metadata=None, frontend=Frontend, backend=Backend):
        original = self.raw if raw is None else raw
        canonical = json.loads(Backend.from_str(json.dumps(original)).to_str())
        shas = tuple(run.object_sha({key: value.get(key) for key in run.PIPELINE}) for value in (original, canonical))
        return run.build_tokenizer(original, self.metadata if metadata is None else metadata,
            api=(backend, Added, frontend), expected_merge_count=2, expected_pipeline_shas=shas)

    def test_complete_composite_contract(self):
        tokenizer, proof = self.build()
        self.assertTrue(proof["passed"])
        self.assertEqual((proof["original_json_added_tokens"], proof["config_added_tokens"]), (22, 33))
        self.assertEqual((len(tokenizer.extra_special_tokens), len(proof["named_tokens"])), (13, 7))
        self.assertEqual((len(tokenizer.get_vocab()), proof["maximum_id"]), (37, 36))
        self.assertEqual(proof["canonical_serialization"]["merge_rules"], 2)
        self.assertTrue(proof["canonical_serialization"]["ordered_reverse_join_exact"])

    def test_original_inputs_unchanged(self):
        before = copy.deepcopy((self.raw, self.metadata))
        self.build()
        self.assertEqual(before, (self.raw, self.metadata))

    def test_config_only_eleven_retained_with_properties(self):
        tokenizer, _ = self.build()
        observed = {row["id"]: row for row in json.loads(tokenizer.backend_tokenizer.to_str())["added_tokens"]}
        for i in range(26, 37):
            self.assertEqual({key: observed[i][key] for key in run.TOKEN_FIELDS}, self.metadata["added_tokens_decoder"][str(i)])

    def test_common_property_change_rejected(self):
        self.metadata["added_tokens_decoder"]["4"]["normalized"] = True
        with self.assertRaises(ValueError):
            self.build()

    def test_config_token_omission_rejected(self):
        del self.metadata["added_tokens_decoder"]["36"]
        with self.assertRaises(ValueError):
            self.build()

    def test_extra_list_omission_rejected(self):
        self.metadata["additional_special_tokens"].pop()
        with self.assertRaises(ValueError):
            self.build()

    def test_named_map_omission_rejected(self):
        self.metadata["extra_special_tokens"].pop("named0_token")
        with self.assertRaises(ValueError):
            self.build()

    def test_native_remapping_rejected(self):
        self.raw["model"]["vocab"]["added26"] = 0
        with self.assertRaises(ValueError):
            self.build()

    def test_wrong_assigned_id_holds(self):
        class WrongID(Backend):
            def token_to_id(self, content):
                found = super().token_to_id(content)
                return found + 1 if content == "added26" and found is not None else found
        with self.assertRaises(run.Hold):
            self.build(backend=WrongID)

    def test_bytelevel_trim_difference_holds(self):
        class Changed(Frontend):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.backend_tokenizer.raw["post_processor"]["trim_offsets"] = True
        with self.assertRaises(run.Hold):
            self.build(frontend=Changed)

    def test_regex_reconstruction_holds(self):
        class Changed(Frontend):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.backend_tokenizer.raw["pre_tokenizer"]["pattern"] = "DIFFERENT_PATTERN"
        with self.assertRaises(run.Hold):
            self.build(frontend=Changed)

    def test_frontend_named_id_change_holds(self):
        class Changed(Frontend):
            def __getattr__(self, key):
                found = super().__getattr__(key)
                return found + 1 if key == "named0_token_id" else found
        with self.assertRaises(run.Hold):
            self.build(frontend=Changed)

    def test_frontend_extra_list_loss_holds(self):
        class Changed(Frontend):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.extra_special_tokens = []
        with self.assertRaises(run.Hold):
            self.build(frontend=Changed)


class ConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.header, self.inventory, self.source, self.state, self.body = inventory_fixture()

    def verify(self):
        return run.verify_consumption(self.body, self.inventory, self.source.__getitem__, FakeTorch)

    def test_every_language_value_and_head_alias(self):
        proof = self.verify()
        self.assertEqual((proof["consumed_language_keys"], proof["state_keys"]), (320, 321))
        self.assertEqual((proof["unused_vision_keys"], proof["unused_mtp_keys"]), (153, 15))
        self.assertEqual(len(proof["unused"]), 168)
        self.assertTrue(all(row["exact_equal"] for row in proof["language_values"]))

    def test_no_unused_tensor_values_read(self):
        called = []
        def read(key):
            called.append(key)
            return self.source[key]
        run.verify_consumption(self.body, self.inventory, read, FakeTorch)
        self.assertEqual(set(called), set(self.inventory["mapping"]))

    def test_different_value_rejected(self):
        self.state["model.norm.weight"].values[0] = 5.
        with self.assertRaisesRegex(ValueError, "value differs"):
            self.verify()

    def test_loaded_shape_rejected(self):
        self.state["model.norm.weight"].shape = (1, 2)
        with self.assertRaisesRegex(ValueError, "shape differs"):
            self.verify()

    def test_dtype_rejected(self):
        self.state["model.norm.weight"].dtype = "bfloat16"
        with self.assertRaises(ValueError):
            self.verify()

    def test_equal_but_untied_head_rejected(self):
        self.state["lm_head.weight"] = FakeTensor([1., 2.])
        with self.assertRaisesRegex(ValueError, "Parameter alias"):
            self.verify()

    def test_missing_language_key_rejected(self):
        self.state.pop("model.norm.weight")
        with self.assertRaises(ValueError):
            self.verify()

    def test_unexpected_body_key_rejected(self):
        self.state["model.visual.weight"] = FakeTensor([1., 2.])
        with self.assertRaises(ValueError):
            self.verify()

    def test_header_extra_key_rejected(self):
        self.header["unknown.weight"] = dict(shape=[2], dtype="BF16", data_offsets=[0, 4])
        with self.assertRaises(ValueError):
            run.header_inventory(self.header)

    def test_header_missing_key_rejected(self):
        self.header.pop(next(iter(self.header)))
        with self.assertRaises(ValueError):
            run.header_inventory(self.header)

    def test_header_invalid_byte_extent_rejected(self):
        next(iter(self.header.values()))["data_offsets"] = [0, 1]
        with self.assertRaises(ValueError):
            run.header_inventory(self.header)

    def test_checkpoint_tied_head_entry_rejected(self):
        self.header["lm_head.weight"] = dict(shape=[2], dtype="BF16", data_offsets=[0, 4])
        with self.assertRaises(ValueError):
            run.header_inventory(self.header)


class CanonicalTests(unittest.TestCase):
    def setUp(self):
        self.raw, _ = tokenizer_fixture()
        canonical = json.loads(Backend.from_str(json.dumps(self.raw)).to_str())
        self.shas = tuple(run.object_sha({key: value.get(key) for key in run.PIPELINE}) for value in (self.raw, canonical))

    def baseline(self, backend=Backend, shas=None, count=2):
        return run.canonical_backend_baseline(self.raw, api=backend, expected_merge_count=count,
            expected_pipeline_shas=self.shas if shas is None else shas)

    def mutated_backend(self, change):
        class Changed(Backend):
            @classmethod
            def from_str(cls, raw):
                result = super().from_str(raw)
                change(result.raw)
                return result
        return Changed

    def test_public_roundtrip_is_the_baseline_before_frontend(self):
        backend, canonical, proof = self.baseline()
        self.assertEqual(json.loads(backend.to_str()), canonical)
        self.assertNotEqual(self.shas[0], self.shas[1])
        self.assertEqual(proof["original_pipeline_sha256"], self.shas[0])
        self.assertEqual(proof["canonical_pipeline_sha256"], self.shas[1])
        self.assertTrue(proof["public_roundtrip_before_frontend"])

    def test_every_merge_is_reverse_joined_in_original_order(self):
        _, _, proof = self.baseline()
        self.assertEqual(proof["merge_rules"], 2)
        self.assertTrue(proof["ordered_reverse_join_exact"])
        self.assertEqual(proof["original_merge_strings_sha256"], proof["reconstructed_merge_strings_sha256"])

    def test_original_json_object_not_changed(self):
        before = copy.deepcopy(self.raw)
        self.baseline()
        self.assertEqual(self.raw, before)

    def test_v1_raw_model_equality_would_reject_serialization_only(self):
        _, canonical, _ = self.baseline()
        self.assertNotEqual(self.raw["model"], canonical["model"])
        self.assertEqual(self.raw["model"]["merges"], [" ".join(pair) for pair in canonical["model"]["merges"]])

    def test_merge_order_change_rejected(self):
        backend = self.mutated_backend(lambda raw: raw["model"]["merges"].reverse())
        with self.assertRaises(run.Hold):
            self.baseline(backend)

    def test_one_merge_omitted_rejected(self):
        backend = self.mutated_backend(lambda raw: raw["model"]["merges"].pop())
        with self.assertRaises(run.Hold):
            self.baseline(backend)

    def test_one_merge_value_changed_rejected(self):
        def change(raw):
            raw["model"]["merges"][0][0] = "changed"
        with self.assertRaises(run.Hold):
            self.baseline(self.mutated_backend(change))

    def test_nonpair_merge_rejected(self):
        backend = self.mutated_backend(lambda raw: raw["model"]["merges"][0].append("third"))
        with self.assertRaises(run.Hold):
            self.baseline(backend)

    def test_ignore_merges_true_not_a_representation_change(self):
        def change(raw):
            raw["model"]["ignore_merges"] = True
        with self.assertRaises(run.Hold):
            self.baseline(self.mutated_backend(change))

    def test_explicit_original_ignore_merges_not_the_pinned_case(self):
        self.raw["model"]["ignore_merges"] = False
        with self.assertRaises(run.Hold):
            self.baseline()

    def test_other_bpe_field_change_rejected(self):
        def change(raw):
            raw["model"]["dropout"] = .1
        with self.assertRaises(run.Hold):
            self.baseline(self.mutated_backend(change))

    def test_vocab_id_change_rejected(self):
        def change(raw):
            raw["model"]["vocab"]["base0"] = 3
        with self.assertRaises(run.Hold):
            self.baseline(self.mutated_backend(change))

    def test_normalizer_change_rejected(self):
        def change(raw):
            raw["normalizer"]["type"] = "DifferentNormalizer"
        with self.assertRaises(run.Hold):
            self.baseline(self.mutated_backend(change))

    def test_bytelevel_option_change_rejected(self):
        def change(raw):
            raw["post_processor"]["trim_offsets"] = True
        with self.assertRaises(run.Hold):
            self.baseline(self.mutated_backend(change))

    def test_original_added_token_property_change_rejected(self):
        def change(raw):
            raw["added_tokens"][0]["normalized"] = True
        with self.assertRaises(run.Hold):
            self.baseline(self.mutated_backend(change))

    def test_wrong_raw_or_canonical_fingerprint_rejected(self):
        for shas in (("0" * 64, self.shas[1]), (self.shas[0], "0" * 64)):
            with self.subTest(shas=shas), self.assertRaises(run.Hold):
                self.baseline(shas=shas)

    def test_complete_merge_count_required(self):
        with self.assertRaises(run.Hold):
            self.baseline(count=3)


class HybridTests(unittest.TestCase):
    def canary(self, **kwargs):
        instance_module = ModuleType("lm_eval.api.instance")
        instance_module.Instance = Instance
        lm = SyntheticLM(**kwargs)
        with patch.dict(sys.modules, {"lm_eval.api.instance": instance_module}):
            proof = run.hybrid_canary(lm, HybridTorch)
        self.assertTrue(all(row == dict(use_cache=False, past_key_values=None, logits_to_keep=0) for row in lm.forward_flags))
        return proof

    def test_stateless_causal_aba_order_prefix_future(self):
        self.assertTrue(self.canary()["passed"])

    def test_future_leak_fails(self):
        with self.assertRaisesRegex(ValueError, "future/prefix"):
            self.canary(future=True)

    def test_returned_state_fails(self):
        with self.assertRaisesRegex(ValueError, "returned state"):
            self.canary(state=True)

    def test_cross_request_history_fails(self):
        with self.assertRaisesRegex(ValueError, "likelihood oracle"):
            self.canary(history=True)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.admission = dict(deadline_epoch=run.LATEST, hard_cap_seconds=600, cleanup_reserve_seconds=30)
        self.now = run.LATEST - 1000

    def test_valid_canary_window(self):
        self.assertEqual(run.window("2026-10-24T08:40:00+09:00", 600, "canary", now=self.now)["hard_cap_seconds"], 600)

    def test_too_late_deadline(self):
        with self.assertRaises(ValueError):
            run.window("2026-10-24T08:41:00+09:00", 600, "canary", now=self.now)

    def test_naive_deadline(self):
        with self.assertRaises(ValueError):
            run.window("2026-10-24T08:00:00", 600, "canary", now=self.now)

    def test_phase_cap(self):
        for mode, cap in (("canary", 601), ("cost", 601), ("full", 7201), ("full", 59), ("cost", True)):
            with self.subTest(mode=mode, cap=cap), self.assertRaises(ValueError):
                run.window("2026-10-24T08:40:00+09:00", cap, mode, now=self.now)

    def test_remaining_subtracts_elapsed(self):
        self.assertEqual(run.remaining(self.admission, 0, elapsed=100, now=self.now), 500)

    def test_absolute_cleanup_reserve(self):
        self.assertEqual(run.remaining(self.admission, 0, elapsed=1, now=run.LATEST - 31), 1)

    def test_expired_cap_rejected(self):
        with self.assertRaises(TimeoutError):
            run.remaining(self.admission, 0, elapsed=600, now=self.now)

    def test_forecast_spent_budget_hold(self):
        cost = dict(actual_counts=run.official.expected_counts("cost"), raw_independent_recount=True,
            task_evaluation_seconds={name: .01 for name in run.official.TASK_COUNTS}, wall_seconds=1., validated_closure_elapsed_seconds=1.1)
        with self.assertRaises(run.Hold):
            run.full_admission(cost, self.admission, 0, elapsed=590, now=self.now)

    def test_fresh_valid_forecast(self):
        cost = dict(actual_counts=run.official.expected_counts("cost"), raw_independent_recount=True,
            task_evaluation_seconds={name: .01 for name in run.official.TASK_COUNTS}, wall_seconds=1., validated_closure_elapsed_seconds=1.1)
        proof = run.full_admission(cost, self.admission, 0, elapsed=10, now=self.now)
        self.assertEqual(proof["remaining_at_admission_seconds"], 590)
        self.assertEqual(proof["forecast_multiplier"], 1.5)

    def test_partial_cost_rejected(self):
        with self.assertRaises(ValueError):
            run.full_admission(dict(actual_counts={}), self.admission, 0, elapsed=0, now=self.now)

    def test_hold_is_not_quality_failure(self):
        report = {}
        run.fail(report, run.Hold("TOKENIZER_CONTRACT"))
        self.assertEqual(report["returncode"], 8)
        self.assertFalse(report["quality_claim"])

    def test_secondary_error_preserves_primary(self):
        report = {}
        first = RuntimeError("primary evaluation failure")
        run.fail(report, OSError("secondary cleanup failure"), first)
        self.assertEqual(report["error"], "primary evaluation failure")
        self.assertEqual(report["secondary_errors"][0]["type"], "OSError")


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p106b_qwen35_synthetic_")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.signature = dict(sha256="A" * 64)
        self.now = run.LATEST - 1000
        self.elapsed = [1.]
        self.admission = dict(deadline_epoch=run.LATEST, deadline="2026-10-24T08:40:00+09:00", hard_cap_seconds=600, cleanup_reserve_seconds=30)
        _, inventory, source, _, body = inventory_fixture()
        self.assets = dict(inventory=inventory)
        consumption = run.verify_consumption(body, inventory, source.__getitem__, FakeTorch)
        proof = dict(key_consumption=consumption, model_class="Qwen3_5ForCausalLM", model_loaded=True,
            body_unchanged=True, owned_cleanup_complete=True, tokenizer_unchanged=True,
            tokenizer_composite_contract=dict(passed=True, original_json_added_tokens=22, config_added_tokens=33,
                extra_list=list(range(13)), named_tokens={str(i):i for i in range(7)}))
        self.report = dict(schema=run.SCHEMA, tag=run.TAG, model=run.MODEL, mode="canary", returncode=0,
            status="QWEN35_CANARY_COMPLETE", source_identity=self.signature, policy=run.policy(), assets=self.assets,
            numerical_canary_passed=True, model_load_attempted=True, admission=self.admission, model_proof=proof,
            numerical_canary=dict(passed=True), hybrid_canary=dict(passed=True))

    def finish(self, **kwargs):
        defaults = dict(identity_fn=lambda: self.signature, verify_fn=lambda pins: None, timer=lambda seconds: nullcontext(),
            clock=lambda: self.elapsed[0], wall=lambda: self.now, idle_fn=lambda: dict(synthetic=True))
        defaults.update(kwargs)
        return run.finalize(self.report, self.directory, 0, self.signature, {}, self.admission, **defaults)

    def test_complete_closure_and_prerequisite(self):
        self.finish()
        self.assertEqual(self.report["returncode"], 0)
        pins = {}
        result = run.closed_prerequisite(self.directory, "canary", self.signature, self.assets, pins)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(len(pins), 2)

    def test_stored0_without_closure_not_admitted(self):
        run.external.write_json(self.directory / "report.json", self.report)
        with self.assertRaises(ValueError):
            run.closed_prerequisite(self.directory, "canary", self.signature, {}, {})

    def test_report_write_time_counts_towards_cap(self):
        def close(path, report, **kwargs):
            run.external.write_json(path, report)
            self.elapsed[0] = 601
        self.finish(close=close)
        self.assertEqual(run.read_json(self.directory / "report.json")["returncode"], 0)
        self.assertEqual(self.report["returncode"], 9)
        self.assertTrue((self.directory / "phase_veto.json").exists())

    def test_closure_write_time_counts_towards_cap(self):
        def write(path, value):
            run.external.write_json(path, value)
            if path.name == "phase_closure.json":
                self.elapsed[0] = 601
        self.finish(write=write)
        self.assertEqual(self.report["returncode"], 9)
        with self.assertRaises(ValueError):
            run.closed_prerequisite(self.directory, "canary", self.signature, {}, {})

    def test_original_failure_survives_writer_error(self):
        def broken(*args, **kwargs):
            raise OSError("writer failed")
        self.finish(primary=RuntimeError("original evaluation error"), close=broken)
        veto = run.read_json(self.directory / "phase_veto.json")
        self.assertEqual(veto["original_error"]["message"], "original evaluation error")
        self.assertEqual(veto["closure_error"]["type"], "OSError")

    def test_source_mutation_veto(self):
        self.finish(identity_fn=lambda: dict(sha256="B" * 64))
        self.assertEqual(self.report["returncode"], 9)

    def test_asset_mutation_veto(self):
        def changed(pins):
            raise ValueError("asset changed")
        self.finish(verify_fn=changed)
        self.assertEqual(self.report["returncode"], 9)

    def test_cleanup_incomplete_veto(self):
        self.report.update(model_load_attempted=True, model_proof=dict(owned_cleanup_complete=False))
        self.finish()
        self.assertEqual(self.report["returncode"], 9)

    def test_cleanup_query_error_veto(self):
        self.report.update(model_load_attempted=True, model_proof=dict(owned_cleanup_complete=True))
        def broken():
            raise RuntimeError("idle query failed")
        self.finish(idle_fn=broken)
        self.assertEqual(self.report["returncode"], 9)

    def test_existing_report_not_overwritten(self):
        old = dict(preserved=True)
        run.external.write_json(self.directory / "report.json", old)
        self.finish()
        self.assertEqual(run.read_json(self.directory / "report.json"), old)
        self.assertEqual(self.report["returncode"], 9)

    def test_veto_blocks_prerequisite(self):
        self.finish()
        run.external.write_json(self.directory / "phase_veto.json", dict(status="VETO"))
        with self.assertRaises(ValueError):
            run.closed_prerequisite(self.directory, "canary", self.signature, {}, {})

    def test_missing_one_language_value_receipt_veto(self):
        self.report["model_proof"]["key_consumption"]["language_values"].pop()
        self.finish()
        self.assertEqual(self.report["returncode"], 9)

    def test_missing_hybrid_proof_veto(self):
        self.report.pop("hybrid_canary")
        self.finish()
        self.assertEqual(self.report["returncode"], 9)

    def test_missing_full_ce_proof_veto(self):
        self.report.pop("numerical_canary")
        self.finish()
        self.assertEqual(self.report["returncode"], 9)

    def test_runtime_tokenizer_mutation_veto(self):
        self.report["model_proof"]["tokenizer_unchanged"] = False
        self.finish()
        self.assertEqual(self.report["returncode"], 9)

    def test_prior_phase_late_veto_rejected(self):
        predecessor = self.directory / "synthetic_canary"
        predecessor.mkdir()
        run.external.write_json(predecessor / "phase_veto.json", dict(status="VETO"))
        self.report["prerequisite_phase_directories"] = [str(predecessor)]
        self.finish()
        self.assertEqual(self.report["returncode"], 9)

    def test_final_read_time_counts_towards_cap(self):
        def read(path):
            result = run.read_json(path)
            if path.name == "phase_closure.json":
                self.elapsed[0] = 601
            return result
        self.finish(read=read)
        self.assertEqual(self.report["returncode"], 9)
        self.assertTrue((self.directory / "phase_veto.json").exists())

    def test_raw_shards_independently_verified_and_pinned(self):
        from scripts.p106b_shards import ShardWriter
        writer = ShardWriter(self.directory, "synthetic", limit=128)
        for i in range(12):
            writer.append(dict(index=i, likelihood=-1.))
        manifest = writer.close(lineage=dict(synthetic=True))
        pins = {}
        run.pin_manifest(self.directory, "synthetic", manifest, pins)
        run.verify_pins(pins)
        self.assertEqual(len(pins), 1 + len(manifest["shards"]))

    def test_old_cost_without_closure_elapsed_not_admitted(self):
        cost = dict(actual_counts=run.official.expected_counts("cost"), raw_independent_recount=True,
            task_evaluation_seconds={name: .01 for name in run.official.TASK_COUNTS}, wall_seconds=1.)
        with self.assertRaises(ValueError):
            run.full_admission(cost, self.admission, 0, elapsed=0, now=self.now)


class SourceTests(unittest.TestCase):
    def test_initial_import_failure_preserved_without_bound_model_helpers(self):
        actual_import = builtins.__import__
        def initial_failure(name, *args, **kwargs):
            if name == "tinylm":
                raise RuntimeError("initial import failure")
            return actual_import(name, *args, **kwargs)
        cuda = SimpleNamespace(empty_cache=lambda: None, memory_allocated=lambda: 0)
        proof = {}
        with patch("builtins.__import__", initial_failure), self.assertRaisesRegex(RuntimeError, "initial import failure"):
            with run.model_runtime(SimpleNamespace(cuda=cuda), {}, None, lambda: None, proof, {}):
                self.fail("an initial import failure must never enter a runtime")
        self.assertTrue(proof["owned_cleanup_complete"])
        self.assertNotIn("model_load_attempted", proof)

    def test_secondary_allocator_failure_does_not_replace_import_error(self):
        actual_import = builtins.__import__
        def initial_failure(name, *args, **kwargs):
            if name == "tinylm":
                raise RuntimeError("initial import failure")
            return actual_import(name, *args, **kwargs)
        def allocator_failure():
            raise OSError("secondary allocator failure")
        proof = {}
        cuda = SimpleNamespace(empty_cache=allocator_failure, memory_allocated=lambda: 0)
        with patch("builtins.__import__", initial_failure), self.assertRaisesRegex(RuntimeError, "initial import failure"):
            with run.model_runtime(SimpleNamespace(cuda=cuda), {}, None, lambda: None, proof, {}):
                self.fail("unreachable runtime")
        self.assertFalse(proof["owned_cleanup_complete"])
        self.assertIn("secondary allocator failure", proof["exit_errors"][0])

    def test_source_ascii_and_no_runtime_patching(self):
        path = ROOT / "scripts/diag_p106b_qwen35_text_core6.py"
        source = path.read_text()
        self.assertTrue(source.isascii())
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(node, (ast.Global, ast.Nonlocal)) for node in ast.walk(tree)))
        forbidden = {"resize_token_embeddings", "save_pretrained", "register", "register_for_auto_class"}
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr in forbidden for node in ast.walk(tree)))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                self.assertFalse(any(isinstance(target, ast.Attribute) and target.attr in
                    ("_model_call", "_loglikelihood_tokens", "forward") for target in node.targets))

    def test_import_and_check_only_do_not_import_backends(self):
        code = """import builtins, sys
original = builtins.__import__
blocked = {'torch','transformers','tokenizers','lm_eval','datasets','safetensors','numpy'}
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in blocked:
        raise AssertionError('backend import forbidden: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from scripts import diag_p106b_qwen35_text_core6 as run
raise SystemExit(run.main(['--check-only']))
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual((report["models"], report["tokenizers"], report["gpu_calls"]), (0, 0, 0))

    def test_bad_execute_arguments_fail_before_any_model(self):
        with redirect_stdout(io.StringIO()) as output:
            code = run.main(["--execute", "--mode", "canary", "--source-sha256", "0" * 64,
                "--deadline", "2026-10-24T08:40:00+09:00", "--max-wall-sec", "601"])
        self.assertEqual(code, 9)
        self.assertFalse(json.loads(output.getvalue())["quality_claim"])

    def test_nonnested_timer_restores_handler(self):
        previous = signal.getsignal(signal.SIGALRM)
        with run.wall_limit(1):
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0., 0.))

    def test_timer_repeats_after_first_timeout_is_caught(self):
        with self.assertRaises(TimeoutError):
            with run.wall_limit(.01):
                try:
                    time.sleep(.03)
                except TimeoutError:
                    time.sleep(.1)


if __name__ == "__main__":
    unittest.main()
