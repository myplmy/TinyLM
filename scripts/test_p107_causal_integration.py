"""Old default equivalence, causal-only KD, frozen teacher and boundary contracts."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import tinylm
import copy
import importlib.util
import unittest
from unittest.mock import patch
import torch
from tinylm.train.adaptive_training import AdaptiveMNTPTrainer, SyntheticDocumentStream, KD_SCHEMA
from tinylm.train.causal_teacher import CausalTeacherKL
from scripts import test_p107_adaptive_training as fixture

torch.set_num_threads(1)
ARCHIVE=ROOT/'handoff/audit/nov01_afternoon/adaptive_training_before_kd_v1.py'


def archived_class():
    spec=importlib.util.spec_from_file_location('tinylm.train._p107_before_kd',ARCHIVE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AdaptiveMNTPTrainer


def learner(cls=AdaptiveMNTPTrainer, *, kd=True, coefficient=.1, identity='E'*64):
    torch.manual_seed(1337)
    model=fixture.ToyAttention()
    teacher=fixture.ToyAttention().eval().requires_grad_(False)
    config=fixture.make().config
    # make() resets the common RNG; both old and new paths start identically.
    args=dict(policy_config=config,mode='adaptive',masked_micros=2,
              signature='C'*64,collect_ids=fixture.predictions)
    if kd:
        args['causal_distillation']=CausalTeacherKL(teacher,vocab_size=64,
            student_tokenizer_sha256='D'*64,teacher_tokenizer_sha256='D'*64,
            teacher_identity_sha256=identity,coefficient=coefficient,chunk_rows=3)
    trainer=cls(model,[torch.optim.AdamW(model.parameters(),lr=.001)],SyntheticDocumentStream(),**args)
    return trainer,teacher


class CausalIntegrationTests(unittest.TestCase):
    assert_tree=fixture.TrainingBoundaryTests.assert_tree

    def test_default_none_matches_archived_implementation_exactly(self):
        legacy,_=learner(archived_class(),kd=False)
        old_rows=[legacy.update() for _ in range(4)]
        old_state=legacy.state_dict()
        current,_=learner(kd=False)
        rows=[current.update() for _ in range(4)]
        for a,b in zip(old_rows,rows):
            self.assertEqual(set(a),set(b))
            for key in ('loss','masked_targets','causal_targets','pre_clip_gradient_norm','policy_commit'):
                self.assert_tree(a[key],b[key])
        self.assert_tree(old_state,current.state_dict())

    def test_teacher_called_only_for_causal_and_stays_frozen(self):
        trainer,teacher=learner();before=copy.deepcopy(teacher.state_dict())
        with patch.object(teacher,'forward',wraps=teacher.forward) as calls:
            row=trainer.update()
        self.assertEqual(calls.call_count,2)
        self.assertEqual(row['causal_kd_micro_batches'],2)
        self.assertEqual(row['teacher_forwards'],2)
        self.assertEqual(row['model_forwards'],4)
        self.assertEqual(row['observed_micro_batches'],2)
        self.assertGreater(row['causal_kl_mean'],0)
        self.assert_tree(before,teacher.state_dict())
        self.assertTrue(all(p.grad is None for p in teacher.parameters()))

    def test_kd_full_boundary_resume_matches_with_dropout(self):
        trainer,_=learner();trainer.update();saved=trainer.state_dict()
        expected=[trainer.update() for _ in range(3)];end=trainer.state_dict()
        resumed,_=learner();resumed.load_state_dict(saved)
        rows=[resumed.update() for _ in range(3)]
        self.assertEqual(saved['schema'],KD_SCHEMA)
        for a,b in zip(expected,rows):
            for key in ('loss','masked_targets','causal_targets','causal_ce_mean','causal_kl_mean'):
                self.assertEqual(a[key],b[key])
        self.assert_tree(end,resumed.state_dict())

    def test_different_teacher_or_coefficient_refused_before_mutation(self):
        trainer,_=learner();saved=trainer.state_dict()
        for other in (learner(coefficient=.2)[0],learner(identity='F'*64)[0],learner(kd=False)[0]):
            before=copy.deepcopy(other.model.state_dict())
            with self.assertRaises(ValueError):other.load_state_dict(saved)
            self.assert_tree(before,other.model.state_dict())
        legacy,_=learner(archived_class(),kd=False)
        with self.assertRaises(ValueError):legacy.load_state_dict(saved)

    def test_kd_does_not_silently_accept_old_non_kd_boundary(self):
        old,_=learner(kd=False);trainer,_=learner()
        with self.assertRaises(ValueError):trainer.load_state_dict(old.state_dict())

    def test_contract_mutation_rejected(self):
        trainer,_=learner();trainer.causal_distillation.contract['coefficient']=.3
        with self.assertRaises(ValueError):trainer.update()
        with self.assertRaises(ValueError):trainer.state_dict()

    def test_teacher_forward_failure_requires_full_restore(self):
        trainer,teacher=learner();saved=trainer.state_dict()
        with patch.object(teacher,'forward',side_effect=RuntimeError('teacher fixture failure')):
            with self.assertRaises(RuntimeError):trainer.update()
        self.assertTrue(trainer.dirty)
        with self.assertRaises(ValueError):trainer.update()
        trainer.load_state_dict(saved)
        self.assertFalse(trainer.dirty)
        trainer.update()


if __name__=='__main__':unittest.main(verbosity=2)
