#!/usr/bin/env python3
"""Root-run stdlib/mock/source contracts; author did not execute these tests.

No lm_eval/torch/model/tokenizer library import, GPU, checkpoint, benchmark data,
network, package registration or official source modification. Temporary fake
source/archive fixtures do not alter the owner's downloaded source tree.
"""
from __future__ import annotations

import ast
import builtins
from contextlib import contextmanager
import hashlib
import io
import json
import math
from pathlib import Path
import runpy
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_official_lm_adapter as bridge


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value)
    return path


class FakeTokenizer:
    def __init__(self):
        self.calls = []
        self.table = {"": [], "A": [10], "A B": [10, 20], " B": [21], "B": [22],
                      "A C": [10, 23, 24], " C": [25], "C": [26], "<bos>A": [1, 10],
                      " ": [27], "x": [28], "xA": [28, 10]}

    def encode(self, text, *, add_special_tokens=False):
        self.calls.append((text, add_special_tokens))
        return SimpleNamespace(ids=list(self.table[text]))

    def decode(self, ids, **kwargs):
        return ",".join(map(str, ids))

    def get_vocab_size(self):
        return 64

    def token_to_id(self, token):
        return {"<pad>": 0, "<bos>": 1, "<eos>": 2}.get(token)


def official_method_fixture():
    """Execute ONLY two pure methods read from pinned source, not its imports.

    This checks real upstream whitespace/joint/empty-prefix code without
    pretending the installed package/dependencies or actual models were run.
    """
    path = bridge.SOURCE / "lm_eval/api/model.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TemplateLM")
    selected = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in ("_encode_pair", "loglikelihood")]
    if len(selected) != 2 or any(node.decorator_list for node in selected):
        raise AssertionError("pinned pure TemplateLM methods changed")
    namespace = {"tqdm": lambda values, **_kwargs: values}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    class FixtureBase:
        def __init__(self):
            self.cache_events = []
            self.cache_hook = SimpleNamespace(add_partial=lambda *args: self.cache_events.append(args))
    return type("PinnedPureTemplateFixture", (FixtureBase,), {name: namespace[name] for name in ("_encode_pair", "loglikelihood")})


def fake_adapter(base, callback=None, batch_size=1):
    tokenizer = FakeTokenizer()
    callback = callback or (lambda batch: [(-float(len(tokens)), True) for tokens in batch["continuation_ids"]])
    core = bridge.LikelihoodCore(vocab_size=64, pad_id=0, score_batch=callback, batch_size=batch_size)
    adapter = bridge._adapter_type(base)(core=core, tokenizer=tokenizer, prefix_id=1, eos_id=2,
        provenance={"tokenizer_sha256": "A" * 64, "device": "mock-not-a-device"})
    return adapter, tokenizer


class ImportAndUpstreamContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = official_method_fixture()

    def test_import_is_stdlib_only_with_no_asset_reads(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "lm_eval", "tokenizers", "transformers", "tinylm", "requests"}:
                raise AssertionError("unexpected heavy import: " + name)
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded), patch.object(Path, "open", side_effect=AssertionError("asset read")):
            result = runpy.run_path(str(ROOT / "scripts/p106b_official_lm_adapter.py"), run_name="source_import_fixture")
        self.assertEqual(result["COMMIT"], "d6de81643928d653435c431bae19945d41d32520")

    def test_pair_method_is_inherited_unmodified_and_joint_tokenized(self):
        seen = []
        adapter, tokenizer = fake_adapter(self.template, lambda batch: seen.append(batch) or [(-1.0, True)])
        self.assertIs(type(adapter)._encode_pair, self.template._encode_pair)
        self.assertEqual(adapter.loglikelihood([SimpleNamespace(args=("A ", "B"))], disable_tqdm=True), [(-1.0, True)])
        self.assertEqual(tokenizer.calls, [("A B", False), ("A", False)])
        self.assertEqual(seen[0]["input_ids"], [[10]])
        self.assertEqual(seen[0]["continuation_ids"], [[20]])
        self.assertNotEqual(seen[0]["continuation_ids"], [tokenizer.table[" B"]])

    def test_empty_context_uses_prefix_and_does_not_duplicate_literal_bos(self):
        seen = []
        adapter, _ = fake_adapter(self.template, lambda batch: seen.append(batch) or [(-1.0, True)])
        adapter.loglikelihood([SimpleNamespace(args=("", "A"))], disable_tqdm=True)
        adapter.loglikelihood([SimpleNamespace(args=("", "<bos>A"))], disable_tqdm=True)
        self.assertEqual([batch["input_ids"] for batch in seen], [[[1]], [[1]]])
        self.assertEqual([batch["continuation_ids"] for batch in seen], [[[10]], [[10]]])

    def test_invalid_or_empty_candidate_fails_instead_of_zero_score(self):
        callback = Mock()
        adapter, _ = fake_adapter(self.template, callback)
        for args in (("A", ""), ("", ""), ("A", None), ("A", "B", "C")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                adapter.loglikelihood([SimpleNamespace(args=args)], disable_tqdm=True)
        callback.assert_not_called()

    def test_results_are_ordered_sums_without_pmi_or_normalization(self):
        adapter, _ = fake_adapter(self.template)
        rows = [SimpleNamespace(args=("A", " C")), SimpleNamespace(args=("A", " B"))]
        self.assertEqual(adapter.loglikelihood(rows, disable_tqdm=True), [(-2.0, True), (-1.0, True)])
        self.assertEqual([event[1] for event in adapter.cache_events], [("A", " C"), ("A", " B")])
        self.assertEqual(adapter.diagnostics()["continuation_tokens_scored"], 3)
        self.assertIn("SUM_CONTINUATION_LOGPROB_ONLY", adapter.diagnostics()["normalization"])

    def test_unsupported_tasks_chat_options_and_closed_adapter_fail(self):
        adapter, _ = fake_adapter(self.template)
        for name in ("loglikelihood_rolling", "generate_until", "apply_chat_template"):
            with self.subTest(name=name), self.assertRaises(NotImplementedError):
                getattr(adapter, name)([])
        with self.assertRaises(ValueError):
            adapter.chat_template(True)
        with self.assertRaises(ValueError):
            adapter.tok_encode("A", add_special_tokens=1)
        adapter.close()
        with self.assertRaises(RuntimeError):
            adapter.loglikelihood([SimpleNamespace(args=("A", " B"))])


class TokenAndOracleContract(unittest.TestCase):
    def test_left_context_truncation_preserves_every_continuation(self):
        plan = bridge.plan_tokens([3, 4, 5, 6], [7, 8], 10, max_length=4)
        self.assertEqual(plan.input_ids, (4, 5, 6, 7))
        self.assertEqual(plan.labels, (-100, -100, 7, 8))
        self.assertEqual((plan.target_start, plan.truncated_context_tokens, plan.kept_context_tokens), (2, 1, 3))

    def test_full_1024_target_boundary_uses_1024_inputs_not_1023(self):
        plan = bridge.plan_tokens([1], [3] * 1024, 4)
        self.assertEqual(len(plan.input_ids), 1024)
        self.assertEqual(len(plan.continuation_ids), 1024)
        self.assertEqual(plan.target_start, 0)
        self.assertEqual(plan.input_ids[0], 1)
        self.assertEqual(plan.labels, (3,) * 1024)
        with self.assertRaisesRegex(ValueError, "rolling"):
            bridge.plan_tokens([1], [3] * 1025, 4)

    def test_right_pad_masks_only_unused_future_slots_not_question_context(self):
        short = bridge.plan_tokens([1], [2], 5)
        long = bridge.plan_tokens([1, 2], [3, 4], 5)
        batch = bridge.padded_batch([short, long], 0, 5)
        self.assertEqual(batch["input_ids"], [[1, 0, 0], [1, 2, 3]])
        self.assertEqual(batch["labels"], [[2, -100, -100], [-100, 3, 4]])
        self.assertEqual(batch["attention_mask"], [[1, 0, 0], [1, 1, 1]])
        self.assertEqual(batch["lengths"], [1, 3])
        self.assertEqual(batch["target_starts"], [0, 1])

    def test_dense_logit_oracle_is_sum_and_all_token_greedy(self):
        plan = bridge.plan_tokens([0, 1], [2, 1], 3)
        logits = [[100.0, -100.0, 0.0], [0.0, 0.0, 2.0], [0.0, 3.0, 0.0], [999.0, 999.0, 999.0]]
        ll, greedy = bridge.logits_oracle(plan, logits, 3)
        # Direct per-label softmax calculation, independent of planner slicing.
        expected = math.log(math.exp(2) / (2 + math.exp(2))) + math.log(math.exp(3) / (2 + math.exp(3)))
        self.assertAlmostEqual(ll, expected, places=12)  # Pure Python FP64 fixture, not a GPU tolerance.
        self.assertTrue(greedy)
        logits[2] = [4.0, 3.0, 0.0]
        self.assertFalse(bridge.logits_oracle(plan, logits, 3)[1])

    def test_greedy_ties_match_first_argmax_and_nonfinite_is_error(self):
        first = bridge.plan_tokens([0], [0], 3)
        second = bridge.plan_tokens([0], [1], 3)
        self.assertTrue(bridge.logits_oracle(first, [[0, 0, 0]], 3)[1])
        self.assertFalse(bridge.logits_oracle(second, [[0, 0, 0]], 3)[1])
        for row in ([0, float("nan"), 0], [0, float("inf"), 0], [0, 0]):
            with self.assertRaises(ValueError):
                bridge.logits_oracle(first, [row], 3)

    def test_long_candidate_is_preflighted_before_any_candidate_forward(self):
        callback = Mock()
        core = bridge.LikelihoodCore(vocab_size=10, pad_id=0, score_batch=callback, max_length=4)
        with self.assertRaisesRegex(ValueError, "continuation"):
            core.score_encoded([(("a", "b"), [1], [2]), (("a", "long"), [1], [2] * 5)])
        callback.assert_not_called()
        self.assertEqual(core.diagnostics()["requests_scored"], 0)

    def test_invalid_ids_zero_context_and_fake_callback_results_fail(self):
        for context, continuation in (([], [1]), ([1], []), ([True], [1]), ([1], [10]), ([1], [-1])):
            with self.subTest(context=context, continuation=continuation), self.assertRaises(ValueError):
                bridge.plan_tokens(context, continuation, 10)
        for score in ((float("nan"), True), (1.0, True), (-1.0, 1), (True, False)):
            core = bridge.LikelihoodCore(vocab_size=10, pad_id=0, score_batch=lambda _batch: [score])
            with self.subTest(score=score), self.assertRaises(ValueError):
                core.score_encoded([(None, [1], [2])])


class ProvenanceAndLifetimeContract(unittest.TestCase):
    def fake_source(self, root):
        source = root / "source"
        files = {name: ("# fake source " + name + "\n").encode() for name in bridge.CRITICAL_FILES}
        for name, body in files.items():
            put(source, name, body)
        archive = root / "official_source.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            for name, body in files.items():
                member = tarfile.TarInfo("lm-evaluation-harness-" + bridge.COMMIT + "/" + name)
                member.size = len(body)
                stream.addfile(member, io.BytesIO(body))
        sha = hashlib.sha256(archive.read_bytes()).hexdigest().upper()
        receipt = dict(schema="TINYLM_OFFICIAL_EVAL_SOURCE_RECEIPT_V1", repo_id="EleutherAI/lm-evaluation-harness",
            revision=bridge.COMMIT, archive_sha256=sha, archive_bytes=archive.stat().st_size,
            archive_path=str(archive), source_root=str(source), source_tree_sha256=bridge.SOURCE_TREE_SHA256)
        manifest = put(root, "manifest.json", json.dumps(receipt).encode())
        return source, archive, manifest, receipt

    def test_manifest_archive_and_critical_source_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="p106b_harness_mock_") as temporary:
            root = Path(temporary)
            source, archive, manifest, receipt = self.fake_source(root)
            with patch.object(bridge, "ARCHIVE_SHA256", receipt["archive_sha256"]), patch.object(bridge, "ARCHIVE_BYTES", receipt["archive_bytes"]):
                verified = bridge.verify_harness_source(manifest, source)
                self.assertEqual(set(verified["critical_files"]), set(bridge.CRITICAL_FILES))
                self.assertIn("NOT_FRESH_FULL_TREE_AUDIT", verified["verification_scope"])
                with (source / "lm_eval/api/model.py").open("ab") as stream:
                    stream.write(b"# tampered mock\n")
                with self.assertRaisesRegex(ValueError, "archive와"):
                    bridge.verify_harness_source(manifest, source)
            with self.assertRaises(ValueError):
                bridge.verify_harness_source(manifest, source)  # Real production archive pin rejects fake fixture.

    def test_installed_same_version_wrong_runtime_source_or_metadata_rejected(self):
        with tempfile.TemporaryDirectory(prefix="p106b_runtime_mock_") as temporary:
            root = Path(temporary)
            source, _, manifest, receipt = self.fake_source(root)
            with patch.object(bridge, "ARCHIVE_SHA256", receipt["archive_sha256"]), patch.object(bridge, "ARCHIVE_BYTES", receipt["archive_bytes"]):
                verified = bridge.verify_harness_source(manifest, source)
            api = source / "lm_eval/api/model.py"
            template = SimpleNamespace(_encode_pair=lambda: None, loglikelihood=lambda: None)
            module = SimpleNamespace(__file__=str(api), TemplateLM=template)
            distribution = SimpleNamespace(version=bridge.VERSION, read_text=lambda _name: None, locate_file=lambda _name: root / "dist")
            with patch.object(bridge.inspect, "getsourcefile", return_value=str(api)):
                checked = bridge.verify_imported_framework(module, verified, distribution)
            self.assertEqual(checked["runtime_api_model_path"], str(api))
            distribution.version = "0.0.wrong"
            with self.assertRaisesRegex(ValueError, "버전"):
                bridge.verify_imported_framework(module, verified, distribution)
            distribution.version = bridge.VERSION
            with self.assertRaisesRegex(ValueError, "경로"):
                bridge.verify_imported_framework(module, verified, distribution, runtime_root=root / "other")

    def test_wrong_metadata_is_rejected_before_lm_eval_import(self):
        with patch.object(bridge, "verify_harness_source", return_value={}), \
             patch.object(bridge.importlib.metadata, "distribution", return_value=SimpleNamespace(version="wrong")), \
             patch.object(bridge.importlib, "import_module", side_effect=AssertionError("lm_eval imported")) as imported:
            with self.assertRaisesRegex(ValueError, "metadata"):
                bridge.prepare_harness()
        imported.assert_not_called()

    def test_explicit_installed_copy_root_is_allowed_only_with_matching_source(self):
        with tempfile.TemporaryDirectory(prefix="p106b_installed_mock_") as temporary:
            root = Path(temporary)
            source, _, manifest, receipt = self.fake_source(root)
            with patch.object(bridge, "ARCHIVE_SHA256", receipt["archive_sha256"]), patch.object(bridge, "ARCHIVE_BYTES", receipt["archive_bytes"]):
                verified = bridge.verify_harness_source(manifest, source)
            installed = root / "venv_site_packages"
            for name in bridge.RUNTIME_FILES:
                put(installed, name, (source / name).read_bytes())
            api = installed / "lm_eval/api/model.py"
            module = SimpleNamespace(__file__=str(api), TemplateLM=SimpleNamespace(_encode_pair=lambda: None, loglikelihood=lambda: None))
            origin = {"url": "file:///fake/pinned.whl", "archive_info": {"hashes": {"sha256": "a" * 64}}}
            distribution = SimpleNamespace(version=bridge.VERSION, read_text=lambda _name: json.dumps(origin), locate_file=lambda _name: installed)
            with patch.object(bridge.inspect, "getsourcefile", return_value=str(api)):
                result = bridge.verify_imported_framework(module, verified, distribution, runtime_root=installed)
            self.assertEqual(result["distribution_direct_url"], origin)
            with self.assertRaisesRegex(ValueError, "경로"):
                bridge.verify_imported_framework(module, verified, distribution)  # No implicit arbitrary site-packages fallback.

    def test_wrong_top_level_search_path_is_rejected_before_package_import(self):
        with tempfile.TemporaryDirectory(prefix="p106b_import_path_mock_") as temporary:
            root = Path(temporary)
            source, _, manifest, receipt = self.fake_source(root)
            with patch.object(bridge, "ARCHIVE_SHA256", receipt["archive_sha256"]), patch.object(bridge, "ARCHIVE_BYTES", receipt["archive_bytes"]):
                verified = bridge.verify_harness_source(manifest, source)
            with patch.object(bridge, "verify_harness_source", return_value=verified), \
                 patch.object(bridge.importlib.metadata, "distribution", return_value=SimpleNamespace(version=bridge.VERSION)), \
                 patch.object(bridge.importlib.util, "find_spec", return_value=SimpleNamespace(origin=str(root / "wrong/lm_eval/__init__.py"))), \
                 patch.object(bridge.importlib, "import_module", side_effect=AssertionError("wrong lm_eval imported")) as imported:
                with self.assertRaisesRegex(ValueError, "검색 경로"):
                    bridge.prepare_harness(source_root=source, manifest_path=manifest)
            imported.assert_not_called()

    def test_harness_failure_precedes_strict_model_loader_import(self):
        with patch.object(bridge, "prepare_harness", side_effect=ValueError("source mismatch")):
            with self.assertRaisesRegex(ValueError, "source mismatch"):
                with bridge.research_adapter("native595-f"):
                    self.fail("model runtime must not open")

    def test_existing_runtime_vocabulary_cfg_and_identity_are_not_guessed(self):
        cfg = SimpleNamespace(max_seq_len=1024, vocab_size=64, mtp_aux=False, attn_kind="softmax_cla")
        model = SimpleNamespace(training=False, cfg=cfg, emb=SimpleNamespace(weight=SimpleNamespace(shape=(64, 8))))
        runtime = dict(model=model, cfg=cfg, tokenizer=FakeTokenizer(), torch="mock-never-imported",
            precision="FP32_MATH", checkpoint_sha256="A" * 64, tokenizer_sha256="B" * 64)
        validator = Mock()
        self.assertEqual(bridge.validate_loaded_runtime(runtime, validator), 64)
        validator.assert_called_once_with(runtime["tokenizer"], {"vocab_size": 64}, allow_extra_special=False)
        model.emb.weight.shape = (63, 8)
        with self.assertRaisesRegex(ValueError, "어휘"):
            bridge.validate_loaded_runtime(runtime, validator)
        model.emb.weight.shape = (64, 8)
        cfg.mtp_aux = True
        with self.assertRaises(ValueError):
            bridge.validate_loaded_runtime(runtime, validator)

    def test_bridge_releases_model_references_before_existing_loader_exit(self):
        adapter = Mock()
        @contextmanager
        def selected(spec):
            self.assertEqual(spec, "resolved")
            try:
                yield {"runtime": "fake"}
            finally:
                adapter.close.assert_called_once()
        module = SimpleNamespace(resolve_model=lambda name: "resolved", selected_runtime=selected)
        with patch.dict(sys.modules, {"scripts.interactive_research_infer": module}), \
             patch.object(bridge, "prepare_harness", return_value=("template", {"source": "mock"})), \
             patch.object(bridge, "_from_prepared", return_value=adapter):
            with bridge.research_adapter("native595-f") as actual:
                self.assertIs(actual, adapter)
        adapter.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
