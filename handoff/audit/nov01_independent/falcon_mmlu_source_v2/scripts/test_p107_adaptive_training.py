"""완료 경계·실제 optimizer·재개·실패 폐기를 CPU에서 검증한다. 품질 시험이 아니다."""
from contextlib import contextmanager
import copy
import hashlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from torch import nn

from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer, SyntheticDocumentStream

torch.set_num_threads(1)


FixtureSource = SyntheticDocumentStream


class ToyAttention(nn.Module):
    def __init__(self, vocab=64):
        super().__init__()
        self.embedding = nn.Embedding(vocab, 8)
        self.dropout = nn.Dropout(.2)
        self.head = nn.Linear(8, vocab)

    def forward(self, tokens, attention_mask):
        h = self.embedding(tokens)
        mask = attention_mask[:, 0].to(h.dtype)
        mixed = mask @ h / mask.sum(-1, keepdim=True)
        return self.head(self.dropout(mixed))


def predictions(logits, targets):
    return logits.argmax(-1).to('cpu')


def make(mode='adaptive', *, model=None, source=None, policy_seed=23):
    torch.manual_seed(1337)
    model = ToyAttention() if model is None else model
    config = PolicyConfig(64, .5, .2, 2, 'keep', policy_seed, 34, 13, 'A'*64, 'B'*64)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
    return AdaptiveMNTPTrainer(model, [optimizer], source or FixtureSource(),
        policy_config=config, mode=mode, masked_micros=2, signature='C'*64, collect_ids=predictions)


def digest_model(model):
    digest = hashlib.sha256()
    for name, p in model.state_dict().items():
        digest.update(name.encode()); digest.update(p.cpu().numpy().tobytes())
    return digest.hexdigest()


class TrainingBoundaryTests(unittest.TestCase):
    def assert_tree(self, left, right):
        self.assertEqual(type(left), type(right))
        if isinstance(left, torch.Tensor):
            self.assertTrue(torch.equal(left, right))
        elif isinstance(left, dict):
            self.assertEqual(set(left), set(right))
            for name in left:self.assert_tree(left[name], right[name])
        elif isinstance(left, (tuple, list)):
            self.assertEqual(len(left), len(right))
            for a,b in zip(left,right):self.assert_tree(a,b)
        else:self.assertEqual(left,right)

    def test_real_update_and_committed_statistics(self):
        trainer = make(); before=digest_model(trainer.model)
        rows=[trainer.update() for _ in range(3)]
        self.assertNotEqual(before,digest_model(trainer.model))
        self.assertEqual(3,trainer.cursor)
        self.assertEqual(6,trainer.policy.observed_micro_batches)
        self.assertEqual(sum(r['masked_targets'] for r in rows),int(trainer.policy.lifetime_total.sum()))
        self.assertTrue(bool((trainer.policy.weights != 1).any()))
        self.assertTrue(all(p.grad is None for p in trainer.model.parameters()))

    def test_observe_only_preserves_uniform_model_updates(self):
        uniform=make('uniform'); first=[]
        for _ in range(4):first.append(uniform.update())
        target=uniform.state_dict()
        observe=make('observe');second=[]
        for _ in range(4):second.append(observe.update())
        self.assertEqual([r['masked_targets'] for r in first],[r['masked_targets'] for r in second])
        self.assertEqual([r['loss'] for r in first],[r['loss'] for r in second])
        self.assert_tree(target['model'],observe.state_dict()['model'])
        self.assert_tree(target['optimizers'],observe.state_dict()['optimizers'])

    def test_serialized_full_boundary_resume_including_dropout(self):
        trainer=make()
        trainer.update(); trainer.update()
        saved=trainer.state_dict()
        buffer=io.BytesIO();torch.save(saved,buffer);buffer.seek(0)
        loaded=torch.load(buffer,weights_only=True,map_location='cpu')
        expected_rows=[trainer.update() for _ in range(3)];expected=trainer.state_dict()
        resumed=make();resumed.load_state_dict(loaded)
        actual_rows=[resumed.update() for _ in range(3)];actual=resumed.state_dict()
        self.assertEqual([r['loss'] for r in expected_rows],[r['loss'] for r in actual_rows])
        self.assertEqual([r['masked_targets'] for r in expected_rows],[r['masked_targets'] for r in actual_rows])
        for key in ('model','optimizers','policy','source','rng'):
            self.assert_tree(expected[key],actual[key])

    def test_uniform_resume(self):
        trainer=make('uniform');trainer.update();state=trainer.state_dict()
        trainer.update();expected=trainer.state_dict()
        resumed=make('uniform');resumed.load_state_dict(state);resumed.update()
        self.assert_tree(expected['model'],resumed.state_dict()['model'])
        self.assert_tree(expected['uniform_rng'],resumed.state_dict()['uniform_rng'])

    def test_no_source_document_guessing(self):
        source=FixtureSource()
        source.next_update=lambda: [(torch.ones(2,5,dtype=torch.long),None)]*4
        trainer=make(source=source)
        with self.assertRaises((ValueError,AttributeError)):trainer.update()
        self.assertEqual(0,trainer.cursor)

    def test_zero_target_rolls_back_without_forced_selection(self):
        trainer=make()
        state=trainer.state_dict()
        with patch('tinylm.train.adaptive_training.mntp_batch',side_effect=ValueError('zero-target')):
            with self.assertRaises(ValueError):trainer.update()
        self.assertFalse(trainer.dirty)
        for key in ('model','optimizers','policy','source','rng'):
            self.assert_tree(state[key],trainer.state_dict()[key])

    def test_failure_after_forward_requires_full_restore(self):
        trainer=make();state=trainer.state_dict()
        with patch.object(trainer.model,'forward',side_effect=RuntimeError('fixture forward error')):
            with self.assertRaises(RuntimeError):trainer.update()
        self.assertTrue(trainer.dirty)
        with self.assertRaises(ValueError):trainer.update()
        with self.assertRaises(ValueError):trainer.state_dict()
        trainer.load_state_dict(state);self.assertFalse(trainer.dirty);trainer.update()

    def test_partial_optimizer_failure_is_not_a_successful_update(self):
        trainer=make();state=trainer.state_dict()
        def corrupt():
            with torch.no_grad():next(trainer.model.parameters()).add_(1)
            raise RuntimeError('partial optimizer')
        with patch.object(trainer.optimizers[0],'step',side_effect=corrupt):
            with self.assertRaises(RuntimeError):trainer.update()
        self.assertTrue(trainer.dirty)
        self.assertEqual(0,trainer.cursor)
        with self.assertRaises(ValueError):trainer.state_dict()
        trainer.load_state_dict(state);self.assert_tree(state['model'],trainer.state_dict()['model'])

    def test_bad_signature_or_policy_cursor_refused(self):
        trainer=make();state=trainer.state_dict();state['signature']='D'*64
        with self.assertRaises(ValueError):trainer.load_state_dict(state)
        state=trainer.state_dict();state['cursor']=1
        with self.assertRaises(ValueError):trainer.load_state_dict(state)

    def test_missing_optimizer_parameter_refused(self):
        model=ToyAttention();config=make().config
        optimizer=torch.optim.SGD([next(model.parameters())],lr=.01)
        with self.assertRaises(ValueError):
            AdaptiveMNTPTrainer(model,[optimizer],FixtureSource(),policy_config=config,
                mode='uniform',masked_micros=2,signature='C'*64)

    def test_invalid_learner_state_refused_before_weight_copy(self):
        trainer=make();state=trainer.state_dict();before=digest_model(trainer.model)
        name=next(iter(state['model']));state['model'][name]=torch.zeros(1)
        with self.assertRaises(ValueError):trainer.load_state_dict(state)
        self.assertEqual(before,digest_model(trainer.model))


if __name__=='__main__':
    unittest.main(verbosity=2)
