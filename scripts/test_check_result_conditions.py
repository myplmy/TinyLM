#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check_result_conditions.py")
SPEC = importlib.util.spec_from_file_location("check_result_conditions", MODULE_PATH)
assert SPEC and SPEC.loader
crc = importlib.util.module_from_spec(SPEC)
sys_modules = __import__("sys").modules
sys_modules[SPEC.name] = crc
SPEC.loader.exec_module(crc)


BASE = {
    "pool_id": ("ko-en-600M", "ko-en-600M"),
    "actual_pool_tokens": ("597000000", "597000000"),
    "pool_override": ("true", "true"),
    "steps": ("10", "10"),
    "micro_bs": ("2", "2"),
    "accum": ("3", "3"),
    "seq": ("4", "4"),
    "actual_draw_tokens": ("240", "240"),
    "sampler_with_replacement": ("true", "true"),
    "expected_unique_tokens": ("200", "200"),
    "sequential_epoch_claim": ("false", "false"),
    "scheduler": ("wsd", "wsd"),
    "warmup": ("5", "5"),
    "anneal_start": ("0.55", "0.55"),
    "decay_fraction": ("0.2", "0.2"),
    "absolute_schedule_horizon": ("5..10", "5..10"),
    "train_language_expected": ("ko/en=50/50", "ko/en=50/50"),
    "train_language_observed": ("same draw by seed 1337", "same draw by seed 1337"),
    "eval_dataset": ("paired full-val", "paired full-val"),
    "eval_language": ("ko=5.5%,en=94.5%", "ko=5.5%,en=94.5%"),
    "tokenizer": ("internal-ko-en-v32768", "internal-ko-en-v32768"),
    "grad_ckpt": ("false", "false"),
    "optimizer": ("muon", "muon"),
    "muon_lr_mult": ("20", "25"),
}


def block(*, overrides=None, claim="DIRECT_PAIRED", not_run="NONE") -> str:
    rows = dict(BASE)
    rows.update(overrides or {})
    axes = set(rows)
    matched = sorted(k for k, pair in rows.items() if pair[0] == pair[1])
    changed = sorted(axes - set(matched))
    body = [
        "<!-- TINYLM_CONDITION_SIGNATURE_V1 id=fixture -->",
        "| field | arm_a | arm_b | evidence |",
        "| --- | --- | --- | --- |",
    ]
    body.extend(f"| {key} | {a} | {b} | fixture |" for key, (a, b) in rows.items())
    body.extend(
        [
            "| comparator_tag | arm-a | arm-b | fixture |",
            f"| matched_axes | {','.join(matched)} | — | fixture |",
            f"| changed_axes | {','.join(changed) or 'NONE'} | — | fixture |",
            "| unmeasured_axes | NONE | — | fixture |",
            f"| not_run_claims | {not_run} | — | fixture |",
            f"| permitted_claim | {claim} | — | fixture |",
            "<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->",
        ]
    )
    return "\n".join(body)


class ConditionSignatureTest(unittest.TestCase):
    def validate(self, text: str) -> list[str]:
        sigs, errors = crc.parse_signatures(text)
        self.assertEqual(len(sigs), 1)
        return errors + crc.validate_signature(sigs[0])

    def test_direct_paired_passes(self):
        self.assertEqual(self.validate(block()), [])

    def test_draw_formula_mismatch_fails(self):
        errors = self.validate(block(overrides={"actual_draw_tokens": ("239", "240")}))
        self.assertTrue(any("steps*micro_bs" in e for e in errors))

    def test_wsd_horizon_change_cannot_be_direct(self):
        errors = self.validate(
            block(
                overrides={
                    "steps": ("10", "20"),
                    "actual_draw_tokens": ("240", "480"),
                    "absolute_schedule_horizon": ("5..10", "5..20"),
                }
            )
        )
        self.assertTrue(any("cannot be DIRECT_PAIRED" in e for e in errors))

    def test_zero_korean_eval_requires_not_run_claim(self):
        errors = self.validate(block(overrides={"eval_language": ("ko=0%,en=100%", "ko=0%,en=100%")}))
        self.assertTrue(any("KOREAN_QUALITY" in e for e in errors))
        self.assertEqual(
            self.validate(
                block(
                    overrides={"eval_language": ("ko=0%,en=100%", "ko=0%,en=100%")},
                    not_run="KOREAN_QUALITY",
                )
            ),
            [],
        )

    def test_missing_required_field_fails(self):
        text = block().replace("| tokenizer | internal-ko-en-v32768 | internal-ko-en-v32768 | fixture |\n", "")
        self.assertTrue(any("missing fields: tokenizer" in e for e in self.validate(text)))

    def test_cli_requires_explicit_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.md"
            path.write_text(block(), encoding="utf-8")
            self.assertEqual(crc.main([str(path)]), 0)
            self.assertEqual(crc.main([str(path.with_name("missing.md"))]), 1)


if __name__ == "__main__":
    unittest.main()
