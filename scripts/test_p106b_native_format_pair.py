#!/usr/bin/env python3
"""형식 두 풀 builder의 작은 bin·토크나이저 DI CPU 회귀."""
from __future__ import annotations
from collections import Counter
from contextlib import contextmanager
import copy
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unicodedata
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_native_format_pair as pair


class Codec:
    vocab = 256
    specials = {0: "<pad>", 1: "<bos>", 2: "<eos>", 3: "<x>"}
    def __init__(self):
        self.backend = self
        self.encoded = []
        self.after_decode = None

    def encode(self, text, *, add_special_tokens):
        if add_special_tokens is not False:
            raise AssertionError("자동 special 추가가 켜졌다")
        self.encoded.append(text)
        values, position = [], 0
        while position < len(text):
            matched = False
            for index, literal in self.specials.items():
                if text.startswith(literal, position):
                    values.append(index)
                    position += len(literal)
                    matched = True
                    break
            if not matched:
                values.append(ord(text[position]) + 35)
                position += 1
        return SimpleNamespace(ids=values)

    def text(self, ids):
        values = list(ids)
        if any(type(v) is not int or not 0 <= v < self.vocab for v in values):
            raise ValueError("합성 어휘 범위를 벗어났다")
        text = "".join(self.specials[v] if v in self.specials else chr(v-35) for v in values)
        if self.after_decode:
            hook, self.after_decode = self.after_decode, None
            hook()
        return text, text.encode("utf-8")

    def raw(self, ids):
        return self.text(ids)[1]


class PairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native_format_pair_cpu_")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def fixture(self, *, docs=None, holds=None, val_full="UNMATCHED_FULL", val_prefix="UNMATCHED_PREFIX",
                minimum=1, mutate_ids=None, mutate_rows=None, source_extra=b""):
        codec = Codec()
        docs = docs or ["alpha\nReferences\n", "beta [[tag]]", "gamma"]
        source_ids, rows, cursor = [], [], 0
        pending, changed, removed_count, structured = 0, 0, 0, 0
        for index, text in enumerate(docs):
            ids = codec.encode(text, add_special_tokens=False).ids
            candidate, removed, review, structure = pair.fmt.transform(text)
            stop = cursor + len(ids)
            rows.append(dict(eos_segment_index=index, cache_segment_ids=[cursor, stop],
                original_text_sha256=pair.sha(text), candidate_text_sha256=pair.sha(candidate),
                text=candidate, normalization_changed=(text != unicodedata.normalize("NFC",
                    text.replace("\r\n", "\n").replace("\r", "\n"))),
                removed_empty_terminal_headings=removed, review_reasons=review,
                semantic_truth="NOT_REVIEWED", training_admission="NOT_ADMITTED"))
            source_ids.extend(ids+[2])
            cursor = stop + 1
            pending += bool(review); changed += candidate != text; removed_count += len(removed)
            structured += bool(structure)
        if mutate_ids:
            source_ids = mutate_ids(source_ids)
        inputs = self.root / "data_cache/inputs"
        inputs.mkdir(parents=True)
        source = inputs / "train.bin"
        source.write_bytes(pair.native.ids_bytes(source_ids)+source_extra)
        source_sha = pair.file_sha(source)
        tokenizer = inputs / "tokenizer.json"
        tokenizer.write_text('{"synthetic":true}')
        tok_sha = pair.file_sha(tokenizer)
        val = inputs / "val.bin"
        val_ids = (codec.encode(val_prefix, add_special_tokens=False).ids + [2]
                   + codec.encode(val_full, add_special_tokens=False).ids + [2]
                   + codec.encode("UNMATCHED_SUFFIX", add_special_tokens=False).ids)
        val.write_bytes(pair.native.ids_bytes(val_ids))
        lineage = dict(source="data_cache/inputs/train.bin", source_sha256=source_sha,
                       tokenizer_sha256=tok_sha, training_admission="NOT_ADMITTED")
        if mutate_rows:
            mutate_rows(rows)
        manifests = {}
        for key, stem in (("format_candidate", "documents"), ("review_queue", "positions")):
            writer = pair.ShardWriter(inputs / key, stem, limit=2048)
            selected = rows if key == "format_candidate" else [
                {k: row[k] for k in ("eos_segment_index", "cache_segment_ids", "original_text_sha256", "review_reasons")}
                for row in rows if row["review_reasons"]]
            if not selected:
                raise AssertionError("합성 검토 queue가 한 행 이상 필요하다")
            for row in selected:
                writer.append(row)
            manifests[key] = writer.close(lineage=lineage)
        report = dict(schema="P106B_WHOLE_NATIVE_FORMAT_CANDIDATE_V1", **lineage,
            documents=len(docs), source_ids=len(source_ids), through_id_exclusive=len(source_ids),
            remaining_ids=0, full_eos_pool_transformed=True, counts=dict(changed_documents=changed,
                pending_review_documents=pending, remaining_structure_documents=structured,
                empty_terminal_heading_lines_removed=removed_count),
            manifests=manifests)
        pair.write_json(inputs / "report.json", report)
        entries = holds(rows, source_sha) if callable(holds) else (holds or [])
        pair.write_json(inputs / "holds.json", dict(schema="P106B_NATIVE_FORMAT_HOLDS_V1",
                        source_sha256=source_sha, holds=entries))
        policy = dict(schema=pair.POLICY, approved_train_reuse=True, scope="TRAIN_FORMAT_COMPARISON_ONLY",
            full_semantic_review=False, review_queue_policy="PRESERVE_NOT_AUTOMATIC_HOLD",
            reserved_action="EXCLUDE_BOTH", minimum_ids_per_arm=minimum,
            source_code_sha256=pair.source_identity()["sha256"])
        for key, name in (("source", "train.bin"), ("report", "report.json"), ("tokenizer", "tokenizer.json"),
                          ("validation", "val.bin"), ("holds", "holds.json")):
            path = inputs / name
            policy[key] = dict(path="data_cache/inputs/" + name, sha256=pair.file_sha(path))
        policy_path = self.root / "data_cache/policy.json"
        pair.write_json(policy_path, policy)
        codec.encoded.clear()
        return codec, policy, rows

    def build(self, codec, *, budget=None):
        return pair.build("data_cache/policy.json", "data_cache/prepared",
                          root=self.root, codec=codec, budget=budget)

    def events(self, result):
        directory = self.root / "data_cache/prepared/ledger"
        return [json.loads(line) for spec in result["ledger"]["shards"]
                for line in (directory / spec["path"]).read_text().splitlines()]

    def test_same_roster_independent_offsets_and_unchanged_slices(self):
        codec, _, _ = self.fixture()
        result = self.build(codec)
        rows = self.events(result)
        output = self.root / "data_cache/prepared"
        self.assertEqual((output / "original.bin").read_bytes(),
                         (self.root / "data_cache/inputs/train.bin").read_bytes())
        self.assertNotEqual(rows[1]["original"]["offset_ids"], rows[1]["format"]["offset_ids"])
        self.assertNotIn("beta [[tag]]", codec.encoded)
        self.assertEqual(codec.encoded.count("alpha\n"), 1)
        self.assertEqual(result["counts"]["encoded_changed_documents"], 1)
        self.assertEqual(result["counts"]["unchanged_token_slices_reused"], 2)
        self.assertEqual(result["training_admission"], "SYNTHETIC_ONLY_NOT_ADMITTED")
        self.assertTrue(all(row["kept"] for row in rows))
        self.assertTrue((output / "partial.json").is_file())
        self.assertTrue((output / "complete.json").is_file())
        self.assertFalse((output / "failed.json").exists())

    def test_review_queue_is_not_automatic_badness_or_hold(self):
        codec, _, _ = self.fixture()
        result = self.build(codec)
        self.assertEqual(result["kept_documents"], 3)
        self.assertEqual(result["counts"]["pending_review_documents"], 1)

    def test_original_sha_hold_is_applied_to_both_arms(self):
        def holds(rows, _):
            return [dict(id="held", original_text_sha256=rows[0]["original_text_sha256"],
                         match_scope="ALL_IDENTICAL_ORIGINAL_TEXT")]
        codec, _, _ = self.fixture(holds=holds)
        result = self.build(codec)
        events = self.events(result)
        self.assertFalse(events[0]["kept"])
        self.assertEqual(events[0]["holds"], ["held"])
        self.assertNotIn("original", events[0])
        self.assertNotIn("format", events[0])
        self.assertEqual(result["kept_documents"], 2)

    def test_numeric_hold_must_bind_same_source_sha(self):
        def holds(rows, source_sha):
            return [dict(id="numeric", source_sha256="A"*64, eos_segment_index=0)]
        codec, _, _ = self.fixture(holds=holds)
        with self.assertRaisesRegex(ValueError, "같은 source"):
            self.build(codec)

    def test_hold_span_and_eos_conflict_is_not_released(self):
        def holds(rows, source_sha):
            return [dict(id="conflict", source_sha256=source_sha,
                         cache_segment_ids=rows[0]["cache_segment_ids"], eos_segment_index=1)]
        codec, _, _ = self.fixture(holds=holds)
        with self.assertRaisesRegex(ValueError, "충돌"):
            self.build(codec)
        self.assertFalse((self.root / "data_cache/prepared/complete.json").exists())

    def test_unresolved_hold_stops_partial(self):
        codec, _, _ = self.fixture(holds=[dict(id="unresolved", original_text_sha256="F"*64,
                                              match_scope="ALL_IDENTICAL_ORIGINAL_TEXT")])
        with self.assertRaisesRegex(ValueError, "미해결"):
            self.build(codec)
        self.assertTrue((self.root / "data_cache/prepared/failed.json").is_file())

    def test_cleaning_created_val_duplicate_is_common_exclusion(self):
        codec, _, _ = self.fixture(val_full="alpha\n")
        result = self.build(codec)
        event = self.events(result)[0]
        self.assertFalse(event["kept"])
        self.assertIn("FORMAT_FULL_CANONICAL_EOS_IDS", event["exclusions"])
        self.assertNotIn("ORIGINAL_FULL_CANONICAL_EOS_IDS", event["exclusions"])
        self.assertEqual(result["kept_documents"], 2)

    def test_existing_val_edge_fragment_excludes_both(self):
        codec, _, _ = self.fixture(val_prefix="beta")
        result = self.build(codec)
        self.assertIn("ORIGINAL_VAL_PREFIX_PARTIAL_IDS", self.events(result)[1]["exclusions"])
        self.assertFalse(self.events(result)[1]["kept"])

    def test_reserved_literal_and_id_are_counted_and_excluded(self):
        codec, _, _ = self.fixture(docs=["alpha<pad>", "beta [[tag]]", "gamma"])
        result = self.build(codec)
        event = self.events(result)[0]
        self.assertFalse(event["kept"])
        self.assertEqual(event["reserved"]["original_ids"]["0"], 1)
        self.assertEqual(event["reserved"]["original_literals"]["<pad>"], 1)

    def test_body_eos_or_missing_final_eos_is_refused(self):
        codec, _, _ = self.fixture(mutate_ids=lambda values: [2] + values[1:])
        with self.assertRaisesRegex(ValueError, "EOS2"):
            self.build(codec)

    def test_wrong_dimension_is_refused_even_with_bound_hash(self):
        codec, policy, _ = self.fixture(source_extra=b"x")
        with self.assertRaises(ValueError):
            self.build(codec)
        self.assertFalse((self.root / "data_cache/prepared/complete.json").exists())

    def test_missing_final_eos_is_refused(self):
        codec, _, _ = self.fixture(mutate_ids=lambda values: values[:-1]+[99])
        with self.assertRaisesRegex(ValueError, "EOS2"):
            self.build(codec)

    def test_all_identical_sha_hold_excludes_every_matching_segment(self):
        def holds(rows, _):
            return [dict(id="all-alpha", original_text_sha256=rows[0]["original_text_sha256"],
                         match_scope="ALL_IDENTICAL_ORIGINAL_TEXT")]
        codec, _, _ = self.fixture(docs=["alpha", "alpha", "beta [[tag]]"], holds=holds)
        result = self.build(codec)
        self.assertEqual(result["holds"]["all-alpha"], 2)
        self.assertEqual([row["kept"] for row in self.events(result)], [False, False, True])

    def test_input_streams_close_on_failure(self):
        codec, _, _ = self.fixture(mutate_rows=lambda rows: rows[0].update(eos_segment_index=1))
        opened, original_open = [], Path.open
        def tracked(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            if path.suffix == ".jsonl" and path.parent.name in ("format_candidate", "ledger"):
                opened.append(stream)
            return stream
        with patch.object(Path, "open", tracked), self.assertRaises(ValueError):
            self.build(codec)
        self.assertTrue(opened)
        self.assertTrue(all(stream.closed for stream in opened))

    def test_policy_mutation_during_build_is_refused(self):
        codec, _, _ = self.fixture()
        path = self.root / "data_cache/policy.json"
        codec.after_decode = lambda: path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError, "policy"):
            self.build(codec)
        self.assertTrue((self.root / "data_cache/prepared/failed.json").exists())

    def test_absolute_deadline_rejects_late_or_naive_time(self):
        with patch.object(sys, "stdout", StringIO()):
            for deadline in ("2026-10-26T08:01:00+00:00", "2026-10-26T08:00:00"):
                self.assertEqual(pair.main(["--check-only", "--policy", "missing", "--deadline", deadline]), 9)

    def test_roster_index_order_or_gap_is_refused(self):
        codec, _, _ = self.fixture(mutate_rows=lambda rows: rows[0].update(eos_segment_index=1))
        with self.assertRaisesRegex(ValueError, "순서"):
            self.build(codec)

    def test_decoded_original_and_candidate_body_checks(self):
        codec, _, _ = self.fixture(mutate_rows=lambda rows: rows[0].update(original_text_sha256="A"*64))
        with self.assertRaisesRegex(ValueError, "원문 SHA"):
            self.build(codec)

    def test_candidate_matches_exact_original_transform(self):
        codec, _, _ = self.fixture(mutate_rows=lambda rows: rows[0].update(text="changed"))
        with self.assertRaisesRegex(ValueError, "transform"):
            self.build(codec)

    def test_edit_spans_link_normalized_tail_and_reject_wrong_span(self):
        original = "alpha\r\nReferences\r\n"
        text, removed, _, _ = pair.fmt.transform(original)
        spans = pair.edit_spans(original, text, removed)
        self.assertEqual(spans[0]["operation"], "NFC_NEWLINES")
        self.assertEqual(spans[1]["normalized_char_span"], [6, 17])
        with self.assertRaises(ValueError):
            pair.edit_spans(original, text, [dict(text="wrong", reason="fixture")])

    def test_minimum_two_pool_threshold_and_shortage(self):
        self.assertEqual(pair.MIN_IDS, 600047616)
        codec, _, _ = self.fixture(minimum=100000)
        with self.assertRaisesRegex(ValueError, "부족"):
            self.build(codec)
        self.assertTrue((self.root / "data_cache/prepared/failed.json").is_file())

    def test_source_mutation_after_consumption_is_refused(self):
        codec, policy, _ = self.fixture()
        original = pair.verify_inputs
        calls = []
        def verify(*args):
            calls.append(1)
            if len(calls) == 2:
                path = self.root / policy["source"]["path"]
                raw = path.read_bytes()
                path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            return original(*args)
        with patch.object(pair, "verify_inputs", side_effect=verify), self.assertRaises(ValueError):
            self.build(codec)
        self.assertFalse((self.root / "data_cache/prepared/complete.json").exists())

    def test_candidate_shard_mutation_after_read_is_refused(self):
        codec, _, _ = self.fixture()
        path = self.root / "data_cache/inputs/format_candidate/documents_000000.jsonl"
        original = codec.encode
        def encode(text, **kwargs):
            result = original(text, **kwargs)
            if text == "alpha\n":
                raw = path.read_bytes()
                path.write_bytes(raw.replace(b"alpha", b"Alpha"))
            return result
        codec.encode = encode
        with self.assertRaises(ValueError):
            self.build(codec)
        self.assertTrue((self.root / "data_cache/prepared/failed.json").is_file())

    def test_timeout_preserves_partial_without_complete(self):
        codec, _, _ = self.fixture()
        clock = [0.]
        active = pair.Budget(10, time.time()+100, clock=lambda: clock[0])
        codec.after_decode = lambda: clock.__setitem__(0, 11.)
        with self.assertRaises(TimeoutError):
            self.build(codec, budget=active)
        self.assertTrue((self.root / "data_cache/prepared/failed.json").exists())
        self.assertFalse((self.root / "data_cache/prepared/complete.json").exists())

    def test_output_readback_detects_binary_change(self):
        codec, _, _ = self.fixture()
        result = self.build(codec)
        output = self.root / "data_cache/prepared"
        path = output / "format.bin"
        raw = path.read_bytes()
        path.write_bytes(bytes([raw[0] ^ 1])+raw[1:])
        with self.assertRaises(ValueError):
            pair.verify_outputs(output, result, pair.Budget(10, time.time()+100))

    def test_policy_absence_val_requirement_and_source_hash_gate(self):
        with self.assertRaises(pair.Hold):
            pair.metadata("data_cache/missing.json", root=self.root, synthetic=True)
        codec, policy, _ = self.fixture()
        original_policy = copy.deepcopy(policy)
        policy.pop("validation")
        (self.root / "data_cache/policy.json").write_text(json.dumps(policy))
        with self.assertRaises(ValueError):
            self.build(codec)
        original_policy["source"]["sha256"] = "A"*64
        (self.root / "data_cache/policy.json").write_text(json.dumps(original_policy))
        with self.assertRaises(ValueError):
            self.build(codec)

    def test_old_output_is_never_overwritten_or_marked_failed(self):
        output = self.root / "data_cache/existing"
        output.mkdir(parents=True)
        (output / "old.bin").write_bytes(b"keep")
        policy = dict(source_code_sha256="A"*64)
        with patch.object(pair, "metadata", return_value=(policy, {}, {"holds": []})), \
             patch.object(pair, "source_identity", return_value={"sha256": "A"*64}), \
             patch.object(pair, "safe", side_effect=lambda name: output if name == "data_cache/existing" else self.root/"policy"), \
             patch.object(pair, "file_sha", return_value="B"*64), \
             patch.object(pair, "build", side_effect=FileExistsError("기존 출력")), \
             patch.object(sys, "stdout", StringIO()):
            code = pair.main(["--execute", "--policy", "policy", "--policy-sha256", "B"*64,
                              "--output", "data_cache/existing"])
        self.assertEqual(code, 9)
        self.assertEqual([p.name for p in output.iterdir()], ["old.bin"])
        self.assertEqual((output / "old.bin").read_bytes(), b"keep")

    def test_protected_paths_and_symlinks_are_refused(self):
        for name in ("datasets/TinyDataset/source", "../source", ".claude/source", "CLAUDE.md", "ai_dev_tool/00_private"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pair.safe(name, self.root)
        target = self.root / "target"
        target.write_text("value")
        (self.root / "link").symlink_to(target)
        with self.assertRaises(ValueError):
            pair.safe("link", self.root)


if __name__ == "__main__":
    unittest.main()

