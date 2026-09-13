#!/usr/bin/env python3
"""Regression tests for scripts/check_change_scope.py."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().with_name("check_change_scope.py")
SPEC = importlib.util.spec_from_file_location("tinylm_change_scope", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
SCOPE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCOPE
SPEC.loader.exec_module(SCOPE)


class ScopeTests(unittest.TestCase):
    def test_literal_and_directory_prefix(self) -> None:
        allowed = [
            SCOPE.parse_authorization("docs/a.md=user request"),
            SCOPE.parse_authorization("proposal/**=approved proposal work"),
        ]
        self.assertEqual(
            SCOPE.audit(
                ["docs/a.md", "proposal/x/y.md"],
                allowed,
                environment_approval=None,
            ),
            [],
        )

    def test_outside_path_fails(self) -> None:
        allowed = [SCOPE.parse_authorization("docs/a.md=user request")]
        errors = SCOPE.audit(["docs/b.md"], allowed, environment_approval=None)
        self.assertTrue(any("outside" in error for error in errors))

    def test_environment_path_needs_separate_approval(self) -> None:
        allowed = [SCOPE.parse_authorization(".codex/**=proposal")]
        errors = SCOPE.audit([".codex/hooks.json"], allowed, environment_approval=None)
        self.assertTrue(any("environment" in error for error in errors))
        self.assertEqual(
            SCOPE.audit(
                [".codex/hooks.json"],
                allowed,
                environment_approval="user approved proposal B",
            ),
            [],
        )

    def test_protected_dataset_is_always_rejected(self) -> None:
        allowed = [SCOPE.parse_authorization("datasets/TinyDataset/**=wrong")]
        errors = SCOPE.audit(
            ["datasets/TinyDataset/file.json"],
            allowed,
            environment_approval="approval",
        )
        self.assertTrue(any("protected dataset" in error for error in errors))

    def test_parent_traversal_and_broad_glob_fail(self) -> None:
        for raw in ("../x=user", "**=user", "docs/*.md=user"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    SCOPE.parse_authorization(raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
