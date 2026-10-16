from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import torch
from tinylm.train.mtp_sft import Record
from scripts import diag_p106b_night_train as d
from scripts.p106b_night_learning import Micro


def record(length, targets):
    return Record([1] * length, [-100] * (length - targets) + [2] * targets,
                  [0] * (length - targets) + [1] * targets)


class TrainContract(unittest.TestCase):
    def test_legacy_pad_name_is_real_zero_not_none(self):
        class Tok:
            def token_to_id(self, name): return {'<pad>': 0, '<|im_end|>': 4}.get(name)
            def get_vocab_size(self): return 32768
        self.assertEqual(d.special_ids(Tok()), (0, 4, '<pad>'))

    def test_missing_pad_fails_before_success_receipt(self):
        class Tok:
            def token_to_id(self, name): return 4 if name == '<|im_end|>' else None
            def get_vocab_size(self): return 32768
        with self.assertRaises(ValueError): d.special_ids(Tok())

    def test_identical_pad_eot_refused(self):
        class Tok:
            def token_to_id(self, name): return 4
            def get_vocab_size(self): return 32768
        with self.assertRaises(ValueError): d.special_ids(Tok())

    def test_interleaved_pair_flatten(self):
        natural = [[record(5, 2), record(6, 2)], [record(7, 3), record(8, 3)]]
        rows = d.micro_records(Micro('natural', (1, 0)), natural, [])
        self.assertEqual([r.x_tokens for r in rows], [7, 8, 5, 6])

    def test_update_denominator_both_views_and_replay(self):
        natural = [[record(5, 2), record(6, 2)], [record(7, 3), record(8, 3)]]
        replay = [record(8, 4), record(5, 1)]
        group = [Micro('natural', (0, 1)), Micro('replay', (0, 1))]
        self.assertEqual(d.denominators(group, natural, replay), (15, 3))

    def test_no_natural_denominator(self):
        self.assertEqual(d.denominators([Micro('replay', (0,))], [], [record(5, 2)]), (2, 0))

    def test_scoped_checkpoint_names(self):
        self.assertNotEqual(d.checkpoint('ce'), d.checkpoint('consistent'))
        self.assertIn('night', d.checkpoint('ce').name)
        with self.assertRaises(ValueError): d.checkpoint('base')

    def test_source_identity_check_only_not_model(self):
        info = d.c.info()
        self.assertEqual(info['updates'], 640)
        self.assertEqual(info['weights'], dict(ce=0., consistent=.05))
        self.assertEqual((info['micro_bs'], info['accum'], info['seq']), (8, 16, 1024))
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__': unittest.main()
