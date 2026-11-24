"""CPU cache/RNG/control checkpoint composition; no native model or GPU."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from tinylm.data.loader import Loader
from tinylm.train.context_curriculum import ContextPlan
from tinylm.train.context_micro_tokens import MicroTokensCursor
from tinylm.train import context_training_state as state


class CheckpointContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise ValueError('CPU tests CUDA forbidden')
    @classmethod
    def tearDownClass(cls):
        if torch.cuda.is_initialized():raise ValueError('CPU state tests initialized CUDA')
    def setUp(self):
        self.original_torch_rng=torch.get_rng_state().clone()
        # Retain newly-created scratch instead of deleting any file.
        self.cache=Path(tempfile.mkdtemp(prefix='tinylm-context-state-v1-',dir='/tmp'))
        (self.cache/'meta.json').write_text(json.dumps(dict(token_dtype='uint16',vocab=32)))
        (np.arange(256,dtype=np.uint16)%32).tofile(self.cache/'train.bin')
        ((np.arange(128,dtype=np.uint16)*3)%32).tofile(self.cache/'val.bin')
        self.plan=ContextPlan(((1,4),(2,8),(3,16)),micro_bs=2,base_accum=2,full_length=16)
        self.identity=state.cache_identity(self.cache)
        self.recipe=dict(context_curriculum='1:4,2:8,3:16',resume=False,steps=3,
            micro_bs=2,accum=2,seq=16,lr=.01,seed=17,compile_=False)
    def tearDown(self):torch.set_rng_state(self.original_torch_rng)
    def objects(self,seed=17,recipe=None):
        tr=Loader('train',2,16,'cpu',self.cache,seed=seed)
        va=Loader('val',2,16,'cpu',self.cache,seed=99)
        cursor=MicroTokensCursor(self.plan,tr,source_sha256=self.identity['identity_sha256'])
        binding=state.make_binding(self.plan,self.recipe if recipe is None else recipe,self.identity,'cpu')
        return tr,va,cursor,binding
    def checkpoint(self):
        tr,va,cursor,binding=self.objects()
        cursor.prepare();cursor.finish(optimizer_applied=False)
        va();torch.rand(7)
        control=dict(completed_updates=1,best_val=3.0,best_step=1,since_improve=0,
            history=[dict(step=1,val_loss=3.0)],n_skip=1,gmax=.5,gpeak=.5)
        payload=state.capture_training_state(cursor,va,binding,control)
        return tr,va,cursor,binding,control,payload
    def same_rng(self,a,b):self.assertTrue(torch.equal(a,b))
    def native_control(self):
        return dict(completed_updates=1,best_val=3.,best_step=1,since_improve=0,
            history=[dict(step=1,val_loss=3.)],n_skip=0,gmax=.5,gpeak=.5,
            loss_accumulators=dict(kd_l=0.,kd_ce=0.,kd_n=0,no_l=3.,no_ce=3.,no_n=1))
    def test_native_NTP_control_fields_preserve_prospective_best_and_accumulators(self):
        control=self.native_control();checked=state.validate_trainer_control(control,1,1)
        self.assertEqual(checked,control);checked['history'][0]['val_loss']=2.
        self.assertEqual(control['history'][0]['val_loss'],3.)
    def test_native_control_rejects_missing_boolean_skip_and_history_inconsistencies(self):
        bad=[]
        row=self.native_control();row.pop('gmax');bad.append(row)
        row=self.native_control();row['n_skip']=True;bad.append(row)
        row=self.native_control();row['loss_accumulators']['no_n']=2;bad.append(row)
        row=self.native_control();row['history']=[];bad.append(row)
        row=self.native_control();row['best_val']=2.;bad.append(row)
        for value in bad:
            with self.assertRaises(ValueError):state.validate_trainer_control(value,1,1)
    def test_context_CLI_and_unsupported_objectives_reject_before_real_data_or_model(self):
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from tinylm import cli
        from tinylm.train.trainer import train
        with patch.object(sys,'argv',['tinylm','train','--help']):
            buffer=io.StringIO()
            with redirect_stdout(buffer),self.assertRaises(SystemExit)as cm:cli.main()
            self.assertEqual(cm.exception.code,0)
        self.assertIn('--context-curriculum',buffer.getvalue())
        arguments=dict(preset='unused',arch='dense',data='never-read',n_tokens=0,steps=3,
            micro_bs=2,seq=16,accum=2,lr=.001,eval_every=1,context_curriculum='1:4,2:8,3:16')
        with patch('tinylm.train.trainer.prepare',side_effect=AssertionError('real data is forbidden')):
            for extra in(dict(kd=True),dict(mtp_aux=True),dict(ema=.9),dict(early_stop=1),dict(connectivity_mode='dynamic')):
                with self.assertRaises(ValueError):train(**arguments,**extra)
    def test_three_actual_cache_files_are_hashed_and_changed_bytes_change_identity(self):
        for name,row in self.identity['files'].items():
            content=(self.cache/name).read_bytes()
            self.assertEqual(row['sha256'],hashlib.sha256(content).hexdigest().upper())
            self.assertEqual(row['bytes'],len(content))
        self.assertEqual(self.identity,state.cache_identity(self.cache))
        path=self.cache/'val.bin';path.write_bytes(path.read_bytes()+bytes([0,0]))
        self.assertNotEqual(self.identity,state.cache_identity(self.cache))
    def test_missing_cache_component_is_not_blessed_as_verified(self):
        other=self.cache/'missing';other.mkdir()
        (other/'meta.json').write_text('{}');(other/'train.bin').write_bytes(bytes([1,0]))
        with self.assertRaises(ValueError):state.cache_identity(other)
    def test_recipe_normalizes_plan_paths_dtype_and_ignores_only_resume(self):
        recipe=dict(self.recipe,resume=True,path=Path('relative'),dtype=torch.float32)
        binding=state.make_binding(self.plan,recipe,self.identity,'cpu')
        self.assertNotIn('resume',binding['recipe'])
        self.assertEqual(binding['recipe']['path'],'relative')
        self.assertEqual(binding['recipe']['dtype'],'torch.float32')
        self.assertEqual(binding['recipe']['context_curriculum'],self.plan.contract())
        changed=dict(recipe,lr=.02)
        self.assertNotEqual(binding,state.make_binding(self.plan,changed,self.identity,'cpu'))
    def test_forged_cache_identity_and_unsupported_recipe_objects_are_rejected(self):
        bad=deepcopy(self.identity);bad['identity_sha256']='A'*64
        with self.assertRaises(ValueError):state.make_binding(self.plan,self.recipe,bad,'cpu')
        for value in(object(),float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                state.make_binding(self.plan,dict(self.recipe,lr=value),self.identity,'cpu')
    def test_validation_uses_disposable_generators_and_preserves_all_live_RNGs(self):
        tr,va,cursor,binding,control,payload=self.checkpoint()
        cpu=torch.get_rng_state().clone();train=deepcopy(tr.rng.bit_generator.state)
        val=deepcopy(va.rng.bit_generator.state)
        validated=state.validate_training_state(payload,binding,self.plan,1)
        self.same_rng(cpu,torch.get_rng_state())
        self.assertEqual(train,tr.rng.bit_generator.state);self.assertEqual(val,va.rng.bit_generator.state)
        self.assertEqual(validated['control'],control)
        self.assertIsNone(validated['cuda_rng'])
    def test_restore_matches_next_train_validation_and_Torch_draws(self):
        tr,va,cursor,binding,control,payload=self.checkpoint()
        expected=cursor.prepare();expected_val=va();expected_torch=torch.rand(19)
        _,other_va,other_cursor,other_binding=self.objects(seed=771)
        actual_control=state.restore_training_state(payload,other_binding,self.plan,1,other_cursor,other_va)
        actual=other_cursor.prepare();actual_val=other_va();actual_torch=torch.rand(19)
        self.assertEqual(control,actual_control)
        for a,b in zip(expected.batches,actual.batches):
            self.assertTrue(all(torch.equal(x,y)for x,y in zip(a,b)))
        self.assertTrue(all(torch.equal(x,y)for x,y in zip(expected_val,actual_val)))
        self.same_rng(expected_torch,actual_torch)
    def test_checksum_missing_fields_and_wrong_container_step_precede_RNG_mutation(self):
        _,_,_,binding,_,payload=self.checkpoint()
        initial=torch.get_rng_state().clone()
        variants=[]
        bad=deepcopy(payload);bad['cpu_rng'][0]^=1;variants.append(bad)
        bad=deepcopy(payload);del bad['validation_rng'];variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError):state.validate_training_state(bad,binding,self.plan,1)
            self.same_rng(initial,torch.get_rng_state())
        for step in(True,-1,2,4):
            with self.assertRaises(ValueError):state.validate_training_state(payload,binding,self.plan,step)
            self.same_rng(initial,torch.get_rng_state())
    def test_wrong_recipe_cache_and_current_runtime_are_rejected(self):
        _,_,_,binding,_,payload=self.checkpoint()
        different=state.make_binding(self.plan,dict(self.recipe,lr=.02),self.identity,'cpu')
        with self.assertRaises(ValueError):state.validate_training_state(payload,different,self.plan,1)
        bad=deepcopy(payload);bad['binding']['runtime']['threads']+=1
        bad['binding']['binding_sha256']=state._sha({key:value for key,value in bad['binding'].items()
                                                   if key!='binding_sha256'})
        bad['payload_sha256']=state._payload_sha(bad)
        with self.assertRaises(ValueError):state.validate_training_state(bad,bad['binding'],self.plan,1)
    def test_boolean_control_counter_and_nonfinite_history_are_rejected(self):
        _,va,cursor,binding=self.objects()
        cursor.prepare();cursor.finish(optimizer_applied=False)
        for control in(dict(completed_updates=True),dict(completed_updates=1,best_val=float('inf'))):
            with self.assertRaises(ValueError):state.capture_training_state(cursor,va,binding,control)
    def test_midupdate_capture_and_wrong_validation_generator_are_rejected(self):
        _,va,cursor,binding=self.objects()
        cursor.prepare()
        with self.assertRaises(RuntimeError):state.capture_training_state(cursor,va,binding,dict(completed_updates=0))
        _,_,_,binding,_,payload=self.checkpoint()
        _,other_va,other_cursor,_=self.objects()
        other_va.rng=np.random.Generator(np.random.MT19937(0))
        with self.assertRaises(ValueError):
            state.restore_training_state(payload,binding,self.plan,1,other_cursor,other_va)
        self.assertEqual(other_cursor.next_update,0)
    def test_save_load_composition_with_two_optimizers_and_stochastic_synthetic_next_steps(self):
        from tinylm.train.muon import Muon
        def parameters():
            return(torch.nn.Parameter(torch.linspace(-.4,.7,128).reshape(32,4)),
                   torch.nn.Parameter(torch.linspace(-.2,.2,128).reshape(4,32)))
        def optimizers(p,q):return torch.optim.AdamW([p],lr=.001),Muon([q],lr=.002,scale_mode='rms')
        def advance(p,q,opts,cursor,val):
            update=cursor.prepare()
            for x,y in update.batches:
                hidden=torch.nn.functional.dropout(p[x],p=.3,training=True)
                loss=torch.nn.functional.cross_entropy((hidden@q).reshape(-1,32),y.reshape(-1),reduction='sum')/64
                loss.backward()
            for optimizer in opts:optimizer.step();optimizer.zero_grad(set_to_none=True)
            cursor.finish(optimizer_applied=True);val()
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(1337)
            _,va,cursor,binding=self.objects();p,q=parameters();opts=optimizers(p,q)
            advance(p,q,opts,cursor,va)
            payload=state.capture_training_state(cursor,va,binding,dict(completed_updates=1,best_val=3.))
            blob=dict(parameters=[p.detach().clone(),q.detach().clone()],
                optimizer=[o.state_dict()for o in opts],context=payload)
            stream=io.BytesIO();torch.save(blob,stream);stream.seek(0)
            saved=torch.load(stream,map_location='cpu',weights_only=True)
            for _ in range(2):advance(p,q,opts,cursor,va)
            expected_rng=torch.get_rng_state().clone();expected_cursor=cursor.state_dict()
            p2,q2=parameters();other_opts=optimizers(p2,q2)
            with torch.no_grad():
                p2.copy_(saved['parameters'][0]);q2.copy_(saved['parameters'][1])
            for optimizer,value in zip(other_opts,saved['optimizer']):optimizer.load_state_dict(value)
            _,other_va,other_cursor,other_binding=self.objects(seed=999)
            state.restore_training_state(saved['context'],other_binding,self.plan,1,other_cursor,other_va)
            for _ in range(2):advance(p2,q2,other_opts,other_cursor,other_va)
            self.assertTrue(torch.equal(p.detach().view(torch.uint8),p2.detach().view(torch.uint8)))
            self.assertTrue(torch.equal(q.detach().view(torch.uint8),q2.detach().view(torch.uint8)))
            self.same_rng(expected_rng,torch.get_rng_state());self.assertEqual(expected_cursor,other_cursor.state_dict())
            self.assertEqual(va.rng.bit_generator.state,other_va.rng.bit_generator.state)
    def test_restore_and_validation_do_not_modify_the_caller_checkpoint(self):
        _,_,_,binding,_,payload=self.checkpoint();original=deepcopy(payload)
        _,va,cursor,_=self.objects(seed=999)
        state.restore_training_state(payload,binding,self.plan,1,cursor,va)
        self.assertEqual(state._payload_sha(payload),state._payload_sha(original))
        self.same_rng(payload['cpu_rng'],original['cpu_rng'])
    def test_stale_binding_checksum_is_rejected_even_if_payload_checksum_is_recomputed(self):
        _,_,_,binding,_,payload=self.checkpoint()
        bad=deepcopy(payload);bad['binding']['recipe']['lr']=.02
        bad['payload_sha256']=state._payload_sha(bad)
        initial=torch.get_rng_state().clone()
        with self.assertRaisesRegex(ValueError,'binding checksum'):
            state.validate_training_state(bad,bad['binding'],self.plan,1)
        self.same_rng(initial,torch.get_rng_state())


if __name__=='__main__':unittest.main()
