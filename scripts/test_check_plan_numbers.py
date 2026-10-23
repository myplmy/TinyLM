#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


PATH = Path(__file__).with_name("check_plan_numbers.py")
SPEC = importlib.util.spec_from_file_location("check_plan_numbers", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DiagnosticReferenceTests(unittest.TestCase):
    def test_exact_diagnostic_path_is_removed_but_original_remains(self):
        refs = {"P091": {"draft.md", "report.md"}}
        missing, diagnostic = MODULE.unresolved_refs(
            refs, have={}, diagnostic_refs={("P091", "report.md"): "explains failure"}
        )
        self.assertEqual(missing, {"P091": ["draft.md"]})
        self.assertEqual(diagnostic, {"P091": ["report.md"]})

    def test_diagnostic_entry_does_not_exempt_other_number_or_file(self):
        refs = {"P091": {"other.md"}, "P092": {"report.md"}}
        missing, _ = MODULE.unresolved_refs(
            refs, have={}, diagnostic_refs={("P091", "report.md"): "narrow"}
        )
        self.assertEqual(missing, {"P091": ["other.md"], "P092": ["report.md"]})

    def test_existing_plan_wins_before_diagnostic_filter(self):
        missing, diagnostic = MODULE.unresolved_refs(
            {"P091": {"report.md"}}, have={"P091": ["P091_x.md"]},
            diagnostic_refs={("P091", "report.md"): "old diagnostic"},
        )
        self.assertEqual((missing, diagnostic), ({}, {}))

    def pinned(self, reason, *, mutate=False):
        with tempfile.TemporaryDirectory(prefix='tinylm-plan-ref-') as folder:
            root=Path(folder);target=root/'review.md'
            target.write_text('원문 서지의 P162-163. Photo.\n',encoding='utf-8')
            expected=hashlib.sha256(target.read_bytes()).hexdigest().upper()
            registry=root/'refs.tsv'
            registry.write_text('plan_id\tpath\treason\nP162\treview.md\t'+reason.replace('DIGEST',expected)+'\n',encoding='utf-8')
            if mutate:target.write_text(target.read_text()+'새 실험 P162 계획\n',encoding='utf-8')
            with patch.object(MODULE,'ROOT',root):
                return MODULE.load_diagnostic_refs(registry)

    def test_exact_content_pin_is_accepted(self):
        rows,errors=self.pinned('sha256=DIGEST; 원문 쪽수이며 실험 참조가 아님')
        self.assertFalse(errors);self.assertEqual(set(rows),{('P162','review.md')})

    def test_modified_file_fails_closed(self):
        rows,errors=self.pinned('sha256=DIGEST; 원문 쪽수',mutate=True)
        self.assertFalse(rows);self.assertTrue(any('content pin differs'in e for e in errors))

    def test_wrong_content_pin_fails_closed(self):
        rows,errors=self.pinned('sha256='+'0'*64+'; 원문 쪽수')
        self.assertFalse(rows);self.assertTrue(errors)

    def test_malformed_content_pin_fails_closed(self):
        rows,errors=self.pinned('sha256=not-a-digest; 원문 쪽수')
        self.assertFalse(rows);self.assertTrue(any('malformed'in e for e in errors))

    def test_legacy_unpinned_registry_stays_compatible(self):
        rows,errors=self.pinned('기존 정확 파일/번호 진단 문맥')
        self.assertFalse(errors);self.assertTrue(rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
