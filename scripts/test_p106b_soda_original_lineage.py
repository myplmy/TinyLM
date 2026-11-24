"""Exact source linkage and split isolation for the saved SODA input shape."""

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from scripts import p106b_soda_original_lineage as lineage
from scripts.p106b_soda_dialogue_view import BOUNDARY, PROFILE


def aya(row_id, story, first="First detail.", second="Second detail.", **overrides):
    return dict(PROFILE, id=row_id, inputs=f"Mira: {first}\n\nSol: {second}{BOUNDARY}", targets=story) | overrides


def original(index, story, split="train", first="First detail.", second="Second detail.", speakers=None):
    return dict(split=split, original_index=index, narrative=story,
                speakers=["Mira", "Sol"] if speakers is None else speakers, dialogue=[first, second])


def checked(rows, *, train=(), valid=(), test=()):
    return lineage.match_exact(lineage.aya_probes(rows), dict(train=train, valid=valid, test=test))["rows"]


def write_parts(path, **parts):
    pins = {}
    for split, rows in parts.items():
        filename = path / f"{split}.parquet"
        pq.write_table(pa.Table.from_pylist(rows), filename)
        pins[split] = (len(rows), sha256(filename.read_bytes()).hexdigest())
    return pins


class Lineage(unittest.TestCase):
    def test_only_outer_whitespace_and_nfc_are_equivalent(self):
        a, b = checked(
            [aya(6, "Café scene", "Café: red."), aya(7, "Café scene", "Café: blue.")],
            train=[original(19, " Cafe\u0301 scene ", first=" Cafe\u0301: red. ")],
        )
        self.assertEqual((a["status"], a["original_index"], a["row_ordinal"]), ("EXACT_TRAIN_LINK", 19, 0))
        self.assertEqual(b["status"], "HOLD_NO_EXACT_MATCH")
        self.assertNotIn("narrative", a)
        self.assertEqual(a["aya_row_sha256"], lineage.hash_json(aya(6, "Café scene", "Café: red.")))

    def test_same_original_group_is_independent_of_aya_id_and_content_variant(self):
        a, b = checked(
            [aya(987, "First exact story"), aya(2, "Second exact story")],
            train=[original(42, "First exact story"), original(92, "Other story"), original(42, "Second exact story")],
        )
        self.assertNotEqual(a["row_ordinal"], b["row_ordinal"])
        self.assertNotEqual(a["aya_row_sha256"], b["aya_row_sha256"])
        self.assertEqual(a["source_group_id"], b["source_group_id"])

    def test_order_and_speaker_are_required(self):
        a, = checked([aya(71, "Same story")],
                      train=[original(33, "Same story", first="Second detail.", second="First detail."),
                             original(34, "Same story", speakers=["Sol", "Mira"])])
        self.assertEqual(a["status"], "HOLD_NO_EXACT_MATCH")

    def test_ambiguous_even_if_same_original_index_and_split(self):
        a, = checked([aya(71, "Exact story")],
                      train=[original(7, "Exact story"), original(7, "Exact story")])
        self.assertEqual((a["status"], a["match_count"]), ("HOLD_MULTIPLE_ORIGINAL_ROWS", 2))
        self.assertNotIn("source_group_id", a)

    def test_unique_content_is_held_when_root_crosses_official_split(self):
        a, = checked([aya(71, "Exact story")], train=[original(7, "Exact story")],
                     valid=[original(7, "Different narrative", "valid")])
        self.assertEqual((a["status"], a["root_splits"]),
                         ("HOLD_ORIGINAL_INDEX_SPLIT_CONFLICT", ["train", "valid"]))
        self.assertNotIn("source_group_id", a)

    def test_evaluation_only_and_invalid_index_keep_separate_outcomes(self):
        a, b = checked([aya(71, "Original test story"), aya(74, "Missing root story")],
                       train=[original(-1, "Missing root story")],
                       test=[original(7, "Original test story", "test")])
        self.assertEqual((a["status"], a["official_split"]), ("EXACT_EVALUATION_LINK", "test"))
        self.assertEqual(b["status"], "HOLD_INVALID_ORIGINAL_INDEX")
        self.assertNotIn("source_group_id", b)

    def test_out_of_scope_aya_template_does_not_receive_a_group(self):
        a, = checked([aya(71, "Supplied story", template_id=4)], train=[original(7, "Supplied story")])
        self.assertEqual(a["status"], "HOLD_UNSUPPORTED_AYA_INPUT")
        self.assertNotIn("source_group_id", a)

    def test_all_partitions_and_correct_declared_splits_required(self):
        p = lineage.aya_probes([aya(25, "Exact story")])
        with self.assertRaisesRegex(ValueError, "All official split streams"):
            lineage.match_exact(p, {"train": ()})
        with self.assertRaisesRegex(ValueError, "Declared split disagrees"):
            lineage.match_exact(p, {"train": (), "valid": [original(5, "Exact story")], "test": ()})

    def test_no_alias_for_duplicate_aya_ids(self):
        row = aya(71, "Supplied story")
        with self.assertRaisesRegex(ValueError, "distinct"):
            lineage.aya_probes([row, row])

    def test_physical_parquet_and_aya_identity_are_both_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            pins = write_parts(path, train=[original(7, "Exact story")],
                               valid=[original(78, "Another story", "valid")],
                               test=[original(79, "Final story", "test")])
            raw = path / "aya.jsonl"
            raw.write_text(json.dumps({"raw_row": aya(17, "Exact story")}) + "\n", encoding="utf-8")
            raw_sha = sha256(raw.read_bytes()).hexdigest()
            probes = lineage.read_aya(raw, raw_sha)
            with self.assertRaisesRegex(ValueError, "local Aya JSONL digest"):
                lineage.read_aya(raw, "0" * 64)
            with patch.object(lineage, "RELEASE", pins):
                rec = lineage.audit_release(path, probes)
                self.assertEqual(rec["status_counts"], {"EXACT_TRAIN_LINK": 1})
                self.assertEqual(rec["official_rows_seen"], {"train": 1, "valid": 1, "test": 1})
                self.assertEqual((rec["corpus_admitted_rows"], rec["teacher_calls"]), (0, 0))
                with (path / "test.parquet").open("ab") as stream:
                    stream.write(b"changed")
                with self.assertRaisesRegex(ValueError, "Release SHA-256 differs"):
                    lineage.audit_release(path, probes)

    def test_parquet_row_extent_must_agree_with_release_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _, digest = write_parts(path, train=[original(10, "Exact story")])["train"]
            with self.assertRaisesRegex(ValueError, "Release row count or columns differ"):
                with lineage.pinned_rows(path / "train.parquet", 2, digest):
                    self.fail("wrong release extent yielded rows")


if __name__ == "__main__":
    unittest.main()
