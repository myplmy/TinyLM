#!/usr/bin/env python3
from __future__ import annotations

import os
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import wandb_sync
import wandb_backfill

ROOT = Path(__file__).resolve().parent.parent


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

    def test_posix_uses_approved_wsl_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            wandb_sync.os, "name", "posix"
        ):
            self.assertEqual(
                wandb_sync.key_file_path(),
                Path("/mnt/z/TinyLM_private/weave_apikey_only.txt"),
            )

    def test_windows_keeps_legacy_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            wandb_sync.os, "name", "nt"
        ):
            self.assertEqual(
                wandb_sync.key_file_path(),
                wandb_sync.WINDOWS_DEFAULT_KEY_FILE,
            )

    def test_read_key_emits_no_secret_or_shape_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.txt"
            secret = "example-secret-value-that-must-never-be-printed"
            path.write_text(secret + "\n", encoding="utf-8")
            output = io.StringIO()
            with mock.patch.dict(
                os.environ, {"TL_WANDB_KEY_FILE": str(path)}, clear=False
            ), redirect_stdout(output):
                self.assertEqual(wandb_sync.read_key(), secret)
            self.assertEqual(output.getvalue(), "")
            self.assertFalse(hasattr(wandb_sync, "mask"))

    def test_exact_tag_is_suffix_not_substring(self) -> None:
        stem = "m100s10_ko-en-control-v2_300M_p097_ctrl_v2"
        self.assertTrue(wandb_sync._tag_matches(stem, "p097_ctrl_v2", exact=True))
        self.assertFalse(wandb_sync._tag_matches(stem, "p097_ctrl", exact=True))
        self.assertTrue(wandb_sync._tag_matches(stem, "p097_ctrl", exact=False))

    def test_payload_preserves_optimizer_and_cla_contract(self) -> None:
        source = {
            "optimizer": "muon",
            "muon_scale": "rms",
            "muon_lr_mult": 4.0,
            "matrix_weight_decay_effective": 0.0,
            "cla_group": 2,
            "final": {"val_loss": 3.5},
            "history": [{"step": 1, "val_loss": 4.0}],
        }
        config, summary, history = wandb_sync.payload("fixture", source)
        self.assertEqual(
            {key: config[key] for key in (
                "optimizer", "muon_scale", "muon_lr_mult",
                "matrix_weight_decay_effective", "cla_group",
            )},
            {
                "optimizer": "muon", "muon_scale": "rms", "muon_lr_mult": 4.0,
                "matrix_weight_decay_effective": 0.0, "cla_group": 2,
            },
        )
        self.assertEqual(summary["final_val_loss"], 3.5)
        self.assertEqual(history[0]["step"], 1)

    def test_upload_uses_non_deprecated_reinit_contract(self) -> None:
        class Run:
            def __init__(self):
                self.summary = {}

            def finish(self):
                return None

        class Context:
            def __init__(self):
                self.kwargs = []

            def init(self, **kwargs):
                self.kwargs.append(kwargs)
                return Run()

            def log(self, _point, step=None):
                return step

        context = Context()
        wandb_sync.upload_runs(
            context,
            [("fixture", {"final": {"val_loss": 3.5}, "history": []})],
            project="tinylm",
        )
        self.assertEqual(context.kwargs[0]["reinit"], "finish_previous")

    def test_bounded_backfill_manifest_and_remote_ids(self) -> None:
        rows = wandb_backfill.load_manifest(
            ROOT / "scripts" / "wandb_backfill_tags.tsv"
        )
        self.assertEqual(len(rows), 7)
        self.assertEqual(len({tag for tag, _reason in rows}), 7)

        class Run:
            def __init__(self, run_id):
                self.id = run_id

        class Api:
            def runs(self, path, filters, per_page):
                self.args = (path, filters, per_page)
                return [Run("one"), Run("two")]

        api = Api()
        found = wandb_backfill.remote_ids(
            api, entity="entity", project="tinylm",
            names=["one", "two", "three"],
        )
        self.assertEqual(found, {"one", "two"})
        self.assertEqual(api.args[0], "entity/tinylm")


if __name__ == "__main__":
    unittest.main(verbosity=2)
