#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ROUTING = load("check_doc_routing")
NEW = load("new_proposal")


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".agents").mkdir()
        (self.root / "proposal").mkdir()
        (self.root / "ai_dev_tool").mkdir()
        (self.root / ".agents" / "project.json").write_text(
            json.dumps({"documentRouting": {"proposal": {
                "defaultDir": "proposal", "template": "proposal/_TEMPLATE.md",
                "filenamePattern": "YYYYMMDD_slug.md", "temporaryPrefix": "temp_",
                "temporaryRequiresExplicitPath": True,
            }}}), encoding="utf-8"
        )
        (self.root / "proposal" / "ok.md").write_text("ok", encoding="utf-8")
        (self.root / "ai_dev_tool" / "explicit.md").write_text("ok", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_route_passes(self):
        self.assertEqual(ROUTING.validate(["proposal=proposal/ok.md"], {}, root=self.root), [])

    def test_outside_route_needs_exact_authority(self):
        docs = ["proposal=ai_dev_tool/explicit.md"]
        self.assertTrue(ROUTING.validate(docs, {}, root=self.root))
        self.assertEqual(
            ROUTING.validate(docs, {"ai_dev_tool/explicit.md": "user named this file"}, root=self.root), []
        )

    def test_protected_path_rejected_before_access(self):
        errors = ROUTING.validate(["proposal=datasets/TinyDataset/x.md"], {}, root=self.root)
        self.assertTrue(any("protected" in error for error in errors))

    def test_proposal_renderer_rebases_readme_link(self):
        rendered = NEW.render(
            "# {한 줄 제목}\n> {YYYY-MM-DD} {실험계획 / 아키텍처 / 스킬 / 작업방식}\n"
            "[`proposal/README.md`](README.md)",
            title="제목", date="2099-01-01", category="작업방식",
            destination=Path("ai_dev_tool/example.md"),
        )
        self.assertIn("(../proposal/README.md)", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
