"""Persistent edits/resume on the existing CPU trainer fixture; no quality claim."""
import copy
import unittest
import torch
from scripts import test_p107_adaptive_training as fixture
from scripts import p108b_boundary as b


class BoundaryTests(unittest.TestCase):
    assert_tree=fixture.TrainingBoundaryTests.assert_tree

    def fixture(self):
        trainer=fixture.make();trainer.update()
        controller=b.BoundaryController(trainer,refresh=lambda model:None)
        return trainer,controller

    def recipe(self):return dict(id='fixture:train1',source_role='TRAIN_CORRECTION')

    def test_rejected_edit_restores_full_training_rng_source_and_optimizer(self):
        trainer,controller=self.fixture();before=trainer.state_dict()
        def validate(model):
            torch.rand(4);trainer.source.next_update()
            return dict(accept=False,measurements=dict(protected_loss=1))
        result=controller.try_edit({'head.weight':torch.ones_like(trainer.model.head.weight)*.01},
            validate=validate,recipe=self.recipe(),moment_policy='keep')
        self.assertEqual(result['status'],'REJECTED_METRICS');self.assert_tree(before,trainer.state_dict())

    def test_accepted_edit_persists_but_validation_rng_and_source_do_not(self):
        trainer,controller=self.fixture();before=trainer.state_dict();ident=id(trainer.model.head.weight)
        delta=torch.zeros_like(trainer.model.head.weight);delta[0,0]=.1
        def validate(model):
            torch.rand(3);trainer.source.next_update();return dict(accept=True,measurements=dict(gain=1))
        result=controller.try_edit({'head.weight':delta},validate=validate,recipe=self.recipe(),moment_policy='keep')
        after=trainer.state_dict();self.assertEqual(result['status'],'ACCEPTED_PERSISTENT')
        self.assertEqual(id(trainer.model.head.weight),ident);self.assertEqual(result['changed_entries'],1)
        for key in('optimizers','rng','source','cursor','policy'):self.assert_tree(before[key],after[key])
        expected=before['model']['head.weight'].clone();expected[0,0]+=.1
        self.assertTrue(torch.equal(after['model']['head.weight'],expected))

    def test_validation_exception_rolls_back_and_can_continue_next_batch(self):
        trainer,controller=self.fixture();before=trainer.state_dict()
        def broken(model):torch.rand(3);raise RuntimeError('bad validation')
        with self.assertRaises(b.BoundaryEditError)as context:
            controller.try_edit({'head.weight':torch.ones_like(trainer.model.head.weight)},validate=broken,
                recipe=self.recipe(),moment_policy='keep')
        self.assertTrue(context.exception.receipt['full_boundary_restored_before_commit'])
        self.assert_tree(before,trainer.state_dict());trainer.update()

    def test_masked_moments_clear_only_changed_coordinates_and_keep_step(self):
        trainer,controller=self.fixture();before=trainer.state_dict();parameter=trainer.model.head.weight
        delta=torch.zeros_like(parameter);delta[1,2]=.1
        receipt=controller.try_edit({'head.weight':delta},validate=lambda model:dict(accept=True,measurements={}),
            recipe=self.recipe(),moment_policy='reset_changed')
        self.assertTrue(receipt['cleared_optimizer_coordinates'])
        state=trainer.optimizers[0].state[parameter]
        self.assertEqual(float(state['exp_avg'][1,2]),0);self.assertEqual(float(state['exp_avg_sq'][1,2]),0)
        self.assertEqual(float(state['step']),1)
        self.assertNotEqual(float(state['exp_avg'][0,0]),0)

    def test_edit_then_exact_full_resume_matches_next_updates_and_history(self):
        trainer,controller=self.fixture();delta=torch.zeros_like(trainer.model.head.weight);delta[0,1]=.05
        controller.try_edit({'head.weight':delta},validate=lambda model:dict(accept=True,measurements=dict(gain=1)),
            recipe=self.recipe(),moment_policy='keep')
        saved=controller.state_dict();expected=[controller.update()['loss']for _ in range(2)];end=controller.state_dict()
        other=fixture.make();resumed=b.BoundaryController(other,refresh=lambda model:None);resumed.load_state_dict(saved)
        actual=[resumed.update()['loss']for _ in range(2)]
        self.assertEqual(expected,actual);self.assert_tree(end,resumed.state_dict())

    def test_non_boundary_final_source_and_nonfinite_edits_fail_closed(self):
        trainer,controller=self.fixture();parameter=trainer.model.head.weight
        with self.assertRaises(ValueError):controller.try_edit({'head.weight':torch.full_like(parameter,float('nan'))},
            validate=lambda model:None,recipe=self.recipe(),moment_policy='keep')
        with self.assertRaises(ValueError):controller.try_edit({'head.weight':torch.zeros_like(parameter)},
            validate=lambda model:None,recipe=dict(id='bad',source_role='FINAL'),moment_policy='keep')
        trainer.active=True
        with self.assertRaises(ValueError):controller.try_edit({'head.weight':torch.zeros_like(parameter)},
            validate=lambda model:None,recipe=self.recipe(),moment_policy='keep')
        trainer.active=False

    def test_nonfinite_measurements_and_changed_gradient_flags_roll_back(self):
        trainer,controller=self.fixture();before=trainer.state_dict();delta=torch.ones_like(trainer.model.head.weight)*.01
        for change_flag in(False,True):
            def invalid(model):
                if change_flag:model.head.weight.requires_grad_(False)
                return dict(accept=True,measurements=dict(gain=float('nan')))
            with self.assertRaises(b.BoundaryEditError):controller.try_edit({'head.weight':delta},validate=invalid,
                recipe=self.recipe(),moment_policy='keep')
            self.assertTrue(trainer.model.head.weight.requires_grad);self.assert_tree(before,trainer.state_dict())

    def test_zero_edit_preserves_negative_zero_bytes(self):
        before=torch.tensor([[-0.,1.]],dtype=torch.float32)
        after,masks=b.candidate_values(dict(model={'w':before}),{'w':torch.nn.Parameter(before.clone())},{'w':torch.zeros_like(before)})
        self.assertTrue(torch.equal(before.view(torch.uint8),after['w'].view(torch.uint8)))
        self.assertFalse(bool(masks['w'].any()))


if __name__=='__main__':unittest.main()
