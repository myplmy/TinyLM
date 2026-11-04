"""CPU authority/preflight/resume and existing-session command seams."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import copy
from datetime import timedelta
import json
import unittest
from unittest.mock import patch
import torch

from scripts import train_p107_documents as cli
from scripts import test_p107_adaptive_training as old_fixture
from tinylm.train.document_input import DocumentInput


def valid_profile():
    return dict(schema=cli.SCHEMA, tag=cli.TAG, authority_directive=107,
        deadline=cli.DEADLINE.isoformat(), model='native595-q', recipe=copy.deepcopy(cli.RECIPE),
        profile_path=cli.PROFILE_PATH, source_pins={'explicit.py':'A'*64},
        input_root=cli.INPUT_ROOT, output=cli.OUTPUT, snapshot=cli.SNAPSHOT,
        max_wall_sec=cli.MAX_WALL, allocator_cap_bytes=cli.ALLOCATOR,
        shared_gpu_increase_bytes=cli.VRAM_INCREASE, corpus_training=False,
        purpose='SYNTHETIC_TECHNICAL')


def continuation():
    row = dict(loss=2.5, masked_targets=7, causal_targets=14, schedule_lrs=[[.001]], seconds=1.)
    report = dict(final_state_hashes={'model':'A'*64,'policy':'B'*64}, updates=[row])
    prior = dict(report, status='COMPLETE', actual_exit=0, profile_sha256='C'*64)
    return report, prior


class DocumentCLITests(unittest.TestCase):
    def test_valid_profile_and_start_deadline(self):
        value = valid_profile();now = cli.DEADLINE-timedelta(hours=1)
        self.assertIs(cli.validate_profile_object(value, value['source_pins'], now), value)
        with self.assertRaises(TimeoutError):
            cli.validate_profile_object(value, value['source_pins'], cli.DEADLINE-timedelta(seconds=100))
        self.assertIs(cli.validate_profile_object(value, value['source_pins'], cli.DEADLINE,
                                                 check_start_budget=False), value)
        with self.assertRaises(ValueError):cli.validate_profile_object(value, value['source_pins'], now.replace(tzinfo=None))

    def test_profile_recipe_purpose_parent_and_sources_are_exact(self):
        for key, bad in (('corpus_training', True), ('purpose', 'TRAIN_ADMITTED'),
                         ('model', 'new595-broad-q'), ('source_pins', {'different':'A'*64})):
            value = valid_profile();value[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                cli.validate_profile_object(value, {'explicit.py':'A'*64}, cli.DEADLINE-timedelta(hours=1))
        value = valid_profile();value['recipe']['batch'] = 8.0
        with self.assertRaises(ValueError):
            cli.validate_profile_object(value, value['source_pins'], cli.DEADLINE-timedelta(hours=1))

    def test_foreign_profile_is_refused_before_any_read(self):
        with patch.object(cli.manual, 'small_json', side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError):cli.validate('other_session/profile.json', 'A'*64)

    def test_wrong_profile_sha_cannot_reach_sources_or_model(self):
        with patch.object(cli.manual, 'small_json', return_value=(valid_profile(), 'A'*64)), \
             patch.object(cli, 'source_pins', side_effect=AssertionError('must not inspect sources')):
            with self.assertRaises(ValueError):
                cli.main(['--profile',cli.PROFILE_PATH,'--profile-sha256','B'*64,'--mode','run','--execute'])

    def test_exact_resume_ignores_only_runtime_cost(self):
        report, prior = continuation();prior = copy.deepcopy(prior)
        prior['updates'][-1]['seconds'] = 99.
        self.assertEqual(cli.compare_resume(report, prior, 'C'*64), 'EXACT')

    def test_changed_state_is_never_an_exact_resume(self):
        report, prior = continuation();prior = copy.deepcopy(prior)
        prior['final_state_hashes']['model'] = 'D'*64
        with self.assertRaises(ValueError):cli.compare_resume(report, prior, 'C'*64)

    def test_changed_loss_or_targets_rejects_resume_comparison(self):
        for field in ('loss','masked_targets','causal_targets','schedule_lrs'):
            report, prior = continuation();prior = copy.deepcopy(prior)
            prior['updates'][-1][field] = [] if field == 'schedule_lrs' else 99
            with self.subTest(field=field), self.assertRaises(ValueError):cli.compare_resume(report, prior, 'C'*64)

    def test_incomplete_or_missing_prior_is_not_a_comparison_pass(self):
        report, prior = continuation();prior['status'] = 'ERROR';prior['actual_exit'] = 9
        self.assertEqual(cli.compare_resume(report, prior, 'C'*64), 'PRIOR_INCOMPLETE_NOT_A_COMPARISON_PASS')
        self.assertEqual(cli.compare_resume(report, None, 'C'*64), 'NO_PRIOR_COMPLETE_REFERENCE_NOT_A_COMPARISON_PASS')

    def test_different_prior_profile_rejected(self):
        report, prior = continuation()
        with self.assertRaises(ValueError):cli.compare_resume(report, prior, 'D'*64)

    def test_file_packet_uses_existing_components_and_exact_state(self):
        torch.set_num_threads(1)
        packet = DocumentInput((tuple(range(35,64)),tuple(range(63,34,-1))),
            ('a','b'),('synthetic','synthetic'),('A'*64,'B'*64),
            json.dumps(dict(vocab_size=64, manifest_sha256='D'*64)))
        recipe = dict(cli.RECIPE, batch=2, micros=4, length=16, vocab=64,
                      masked_micros=2, mask_rate=.5, seed=23, horizon=4, warmup=1)
        def make():
            torch.manual_seed(123)
            model = old_fixture.ToyAttention()
            return cli.make_session(model, packet, recipe, 'E'*64,
                optimizer_factory=lambda m:[torch.optim.AdamW(m.parameters(), lr=.001)],
                collect_ids=lambda logits,targets:logits.argmax(-1).cpu(), autocast_dtype=None)
        first = make();first.update();state = first.state_dict();expected = first.update()
        second = make();second.load_state_dict(state);actual = second.update()
        for key in ('loss','causal_targets','masked_targets','executed_input_tokens','schedule_lrs'):
            self.assertEqual(expected[key], actual[key])
        for name,value in first.trainer.model.state_dict().items():
            self.assertTrue(torch.equal(value, second.trainer.model.state_dict()[name]))
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__':
    unittest.main()
