"""Check the optional archive in the native CPU boundary fixture."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import torch

from scripts import diag_p109c_ste_native as diagnostic
from scripts import run_p109c_scratch330 as entry
from scripts import test_p109c_scratch_bundle as fixture
from scripts.run_p109c_with_aoa_archive import EvaluationArchive
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train import packed_document_training, trainer


class AoAArchiveTest(unittest.TestCase):
    def test_native_saves_preserve_training_and_strict_loadable_midpoints(self):
        self.assertFalse(torch.cuda.is_available())
        torch.set_num_threads(1)
        native_args, evaluate = entry.native_args, trainer.evaluate
        native_save = packed_document_training.save_packed_checkpoint
        with (TemporaryDirectory(prefix="p109c_AoA_CPU_") as directory,
              patch.multiple(entry, STEPS=fixture.STEPS, BOUNDARY=fixture.BOUNDARY,
                             MICRO=fixture.MICRO, ACCUM=fixture.ACCUM, WIDTH=fixture.WIDTH,
                             VOCAB=fixture.VOCAB, EVAL_EVERY=1),
              patch.object(entry, "native_args", side_effect=lambda pool, resume:
                           native_args(pool, resume) + ["--anneal-start", "0"]),
              patch.object(trainer, "build_config", fixture.small_model),
              patch.object(trainer, "evaluate", side_effect=lambda model, loader, _, device, **kwargs:
                           evaluate(model, loader, 2, device, **kwargs))):
            root = Path(directory)
            manifest = root / "bundle.json"
            bundle = entry.load_bundle(manifest, fixture.write_manifest(manifest, fixture.make_bundle(root)))
            base = diagnostic.arm(bundle, root / "base", reuse=False)
            comparison = root / "with_archive"
            exports = root / "evaluation_steps"
            exports.mkdir()
            archive = EvaluationArchive(exports, diagnostic.checkpoint(comparison), (1, 2), native_save)
            with patch.object(packed_document_training, "save_packed_checkpoint", archive):
                actual = diagnostic.arm(bundle, comparison, reuse=False)
            self.assertEqual(base["weights"], actual["weights"])
            self.assertEqual(base["updates"], actual["updates"])
            self.assertEqual(list(archive.snapshots), [1, 2])
            self.assertEqual(sorted(path.name for path in exports.glob("*.pt")), ["aoa_step_1.pt", "aoa_step_2.pt"])
            for step, receipt in archive.snapshots.items():
                path = exports / receipt["checkpoint"]
                saved = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
                self.assertEqual(saved["step"], step)
                self.assertEqual(receipt["sha256"], entry.file_sha(path).upper())
                self.assertEqual(receipt["input_slots"], step * fixture.MICRO * fixture.ACCUM * fixture.WIDTH)
                self.assertEqual(set(saved), {"model", "cfg", "step", "tokenizer_sha256"})
                model = TiedMLPTransformer(TMTConfig(**saved["cfg"]))
                model.load_state_dict(saved["model"], strict=True)


if __name__ == "__main__":
    unittest.main()
