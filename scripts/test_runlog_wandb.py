#!/usr/bin/env python3
from __future__ import annotations

import unittest

import runlog


class RunlogWandbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.full = [
            "/home/uranus/miniforge3/envs/tlm_torch/bin/python",
            "run100m.py", "train", "--steps", "2289", "--micro-bs", "8",
            "--accum", "16", "--seq", "1024", "--tag", "p097_ctrl_v2",
        ]
        self.wsl = {"WSL_DISTRO_NAME": "Ubuntu"}

    def test_full_wsl_training_selects_exact_tag(self) -> None:
        spec = runlog._training_wandb_spec(self.full, self.wsl)
        self.assertEqual(spec["tag"], "p097_ctrl_v2")
        self.assertEqual(spec["draw_tokens"], 300_023_808)
        self.assertEqual(spec["project"], "tinylm")

    def test_short_probe_is_not_uploaded(self) -> None:
        cmd = list(self.full)
        cmd[cmd.index("--steps") + 1] = "250"
        self.assertIsNone(runlog._training_wandb_spec(cmd, self.wsl))

    def test_non_wsl_and_explicit_disable_are_not_uploaded(self) -> None:
        self.assertIsNone(runlog._training_wandb_spec(self.full, {}))
        self.assertIsNone(runlog._training_wandb_spec(
            self.full, {"WSL_DISTRO_NAME": "Ubuntu", "TL_WANDB_AUTO": "0"}
        ))

    def test_non_training_command_is_not_uploaded(self) -> None:
        cmd = [self.full[0], "scripts/eval_bench_suite.py", "--task", "hellaswag"]
        self.assertIsNone(runlog._training_wandb_spec(cmd, self.wsl))


if __name__ == "__main__":
    unittest.main(verbosity=2)
