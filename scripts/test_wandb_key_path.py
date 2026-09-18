#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

import wandb_sync


class WandbKeyPathTests(unittest.TestCase):
    def test_explicit_path_wins_on_every_platform(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"TL_WANDB_KEY_FILE": "~/private/key.txt"},
            clear=False,
        ):
            self.assertEqual(
                wandb_sync.key_file_path(),
                Path("~/private/key.txt").expanduser(),
            )

    def test_posix_requires_explicit_secret_path(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            wandb_sync.os, "name", "posix"
        ):
            with self.assertRaisesRegex(FileNotFoundError, "TL_WANDB_KEY_FILE"):
                wandb_sync.key_file_path()

    def test_windows_keeps_legacy_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            wandb_sync.os, "name", "nt"
        ):
            self.assertEqual(
                wandb_sync.key_file_path(),
                wandb_sync.WINDOWS_DEFAULT_KEY_FILE,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
