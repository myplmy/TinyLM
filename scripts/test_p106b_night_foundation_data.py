"""Pure CPU fixtures; never open a cache, QA corpus, checkpoint or model."""
from pathlib import Path
import copy
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_foundation_data as data


def small_contract(**kwargs):
    return data.make_contract(2 * data.UPDATE_TARGETS * 4 + 501,
                              data.TRAIN_SHA, data.VAL_SHA, **kwargs)


class FoundationContractTests(unittest.TestCase):
    def test_actual_declared_cache_gives2281_updates_and298975232_targets(self):
        contract = data.make_contract(data.NATIVE_TRAIN_TOKENS, data.TRAIN_SHA, data.VAL_SHA)
        self.assertEqual(contract['steps'], 2281)
        self.assertEqual(contract['actual_draw_tokens'], 298975232)
        self.assertEqual(contract['native_windows'], 2281 * 128)
        self.assertEqual(contract['selected_raw_window_tokens'], 2281 * 128 * 1025)
        self.assertAlmostEqual(contract['pool_ratio'], 2.00014896, places=8)
        self.assertEqual(contract['native_val_tokens'], 3005000)
        self.assertEqual(contract['native_train_file'], data.NATIVE_TRAIN)
        self.assertFalse(contract['new_unique_source_tokens_claim'])

    def test_all_selected_windows_inbounds_and_nonoverlapping_including_target(self):
        contract = small_contract()
        offsets = sorted(contract['native_train_offsets'])
        self.assertEqual(len(offsets), 4 * 128)
        self.assertTrue(all(offset % 1025 == 0 for offset in offsets))
        self.assertGreaterEqual(offsets[0], 0)
        self.assertLessEqual(offsets[-1] + 1025, contract['native_train_tokens'])
        self.assertTrue(all(b - a >= 1025 for a, b in zip(offsets, offsets[1:])))

    def test_local_seed_reproduces_full_candidate_shuffle_without_global_rng_change(self):
        before = random.getstate()
        first = small_contract(seed=1337)
        self.assertEqual(before, random.getstate())
        second = small_contract(seed=1337)
        self.assertEqual(first, second)
        other = small_contract(seed=1441)
        self.assertNotEqual(first['native_train_offsets'], other['native_train_offsets'])
        candidates = list(range(0, first['native_train_tokens'] - 1025 + 1, 1025))
        random.Random(1337).shuffle(candidates)
        self.assertEqual(first['native_train_offsets'], candidates[:first['native_windows']])

    def test_max_steps_is_a_cap_without_reinterpreting_pool_size(self):
        contract = small_contract(max_steps=2)
        self.assertEqual(contract['steps'], 2)
        self.assertEqual(contract['actual_pool_tokens'], 2 * data.UPDATE_TARGETS * 4 + 501)
        self.assertEqual(contract['actual_draw_tokens'], 2 * data.UPDATE_TARGETS)
        self.assertGreaterEqual(contract['pool_ratio'], 4.)

    def test_zero_update_and_invalid_input_counts_refused(self):
        for value in (0, -1, True, 4., 2 * data.UPDATE_TARGETS - 1):
            with self.assertRaises(ValueError):
                data.make_contract(value, data.TRAIN_SHA, data.VAL_SHA)
        for value in (0, -1, True, 1., 2290):
            with self.assertRaises(ValueError):
                small_contract(max_steps=value)
        for value in (True, 1.5, '1337'):
            with self.assertRaises(ValueError):
                small_contract(seed=value)

    def test_locked_qa_train_val_hashes_and_original_parent(self):
        for train_sha, val_sha, qa_sha in (('F' * 64, data.VAL_SHA, data.LOCKED_QA_SHA),
                (data.TRAIN_SHA, 'F' * 64, data.LOCKED_QA_SHA),
                (data.TRAIN_SHA, data.VAL_SHA, 'F' * 64)):
            with self.assertRaises(ValueError):
                data.make_contract(2 * data.UPDATE_TARGETS * 4, train_sha, val_sha, qa_sha)
        contract = data.make_contract(2 * data.UPDATE_TARGETS, data.TRAIN_SHA.lower(), data.VAL_SHA.lower())
        self.assertEqual(contract['parent_sha256'], data.PARENT_SHA)
        self.assertEqual(contract['parent'], str(data.PARENT.relative_to(data.ROOT)))
        self.assertEqual(contract['qa_report_sha256'], data.LOCKED_QA_SHA)

    def test_cpt_and_qa_have_separate_fresh_optimizer_contracts(self):
        contract = small_contract()
        self.assertEqual((contract['adam_lr'], contract['muon_lr']), (1e-4, 4e-4))
        self.assertEqual((contract['scheduler'], contract['quant_anneal']), ('constant', 1.))
        self.assertTrue(contract['fresh_optimizer_moments'])
        self.assertEqual(contract['compile'], 'default')
        self.assertTrue(contract['grad_checkpoint'])
        self.assertFalse(contract['mtp'])
        qa = contract['qa_followup']
        self.assertEqual((qa['updates'], qa['native_x_tokens']), (640, 5242880))
        self.assertEqual((qa['adam_lr'], qa['muon_lr'], qa['consistency_weight']), (5e-5, 2e-4, 0.))
        self.assertEqual(qa['natural_views'], [0, 1])
        self.assertTrue(qa['fresh_optimizer_moments'])

    def test_groups_are16_by8_offset_list_indices_exactly_once(self):
        contract = small_contract()
        groups = list(data.native_groups(contract))
        self.assertEqual(len(groups), 4)
        self.assertTrue(all(len(update) == 16 and all(len(micro) == 8 for micro in update) for update in groups))
        indices = [i for update in groups for micro in update for i in micro]
        self.assertEqual(indices, list(range(4 * 128)))
        actual_offsets = [contract['native_train_offsets'][i] for i in indices]
        self.assertEqual(actual_offsets, contract['native_train_offsets'])

    def test_start_update_returns_same_frozen_suffix_without_contract_mutation(self):
        contract = small_contract()
        before = copy.deepcopy(contract)
        full = list(data.native_groups(contract))
        self.assertEqual(list(data.native_groups(contract, start_update=2)), full[2:])
        self.assertEqual(list(data.native_groups(contract, start_update=4)), [])
        self.assertEqual(contract, before)
        for start in (-1, 5, True, 1.5):
            with self.assertRaises(ValueError):
                list(data.native_groups(contract, start_update=start))

    def test_offset_duplicate_bounds_hash_and_exposure_tampering_refused(self):
        contract = small_contract()
        for change in ('duplicate', 'bounds', 'stride', 'hash', 'draw', 'ratio', 'parent', 'qa'):
            altered = copy.deepcopy(contract)
            if change == 'duplicate':
                altered['native_train_offsets'][1] = altered['native_train_offsets'][0]
            elif change == 'bounds':
                altered['native_train_offsets'][0] = altered['native_train_tokens']
            elif change == 'stride':
                altered['native_train_offsets'][0] += 1
            elif change == 'hash':
                altered['native_train_offsets'].reverse()
            elif change == 'draw':
                altered['actual_draw_tokens'] += 1
            elif change == 'ratio':
                altered['pool_ratio'] = 1.9
            elif change == 'parent':
                altered['parent'] = 'different.pt'
            else:
                altered['qa_followup']['consistency_weight'] = .05
            with self.assertRaises(ValueError, msg=change):
                list(data.native_groups(altered))


if __name__ == '__main__':
    unittest.main()
