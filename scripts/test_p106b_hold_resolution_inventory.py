#!/usr/bin/env python3
"""Fail closed on changed source bytes, decoded body and interval boundaries."""
from array import array
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inventory


class LiteralCodec:
    def text(self, ids):
        text = "".join(chr(i) for i in ids)
        return text, text.encode("utf-8")


class SourceLinkTests(unittest.TestCase):
    def reader_and_row(self, ids, text):
        values = array("H", ids)
        if sys.byteorder != "little":
            values.byteswap()
        raw = values.tobytes()
        reader = inventory.OriginalReader.__new__(inventory.OriginalReader)
        reader.banks = {"source": b"XX" + raw + b"YY"}
        reader.codec = LiteralCodec()
        row = dict(source="source", source_ids=[1, len(ids) + 1],
                   source_ids_sha256=hashlib.sha256(raw).hexdigest().upper(),
                   original_text_sha256=inventory.sha(text))
        return reader, row

    def test_terminal_eos_is_not_part_of_review_text(self):
        reader, row = self.reader_and_row([ord("가"), ord("A"), 2], "가A")
        self.assertEqual(reader.text(row), ("가A", True, True))

    def test_unfinished_source_keeps_its_final_character(self):
        reader, row = self.reader_and_row([ord("가"), ord("A")], "가A")
        self.assertEqual(reader.text(row), ("가A", False, True))

    def test_changed_source_interval_is_rejected(self):
        reader, row = self.reader_and_row([65, 2], "A")
        row["source_ids"] = [0, 2]
        with self.assertRaisesRegex(ValueError, "interval bytes"):
            reader.text(row)

    def test_decoded_body_sha_cannot_be_replaced(self):
        reader, row = self.reader_and_row([65, 2], "B")
        with self.assertRaisesRegex(ValueError, "original body"):
            reader.text(row)

    def test_library_decode_cannot_silently_replace_utf8(self):
        reader, row = self.reader_and_row([65, 2], "A")
        class ReplacingCodec:
            def text(self, ids):
                return "A", b"B"
        reader.codec = ReplacingCodec()
        with self.assertRaisesRegex(ValueError, "UTF-8 bytes"):
            reader.text(row)


if __name__ == "__main__":
    unittest.main()
