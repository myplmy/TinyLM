#!/usr/bin/env python3
"""Synthetic CPU tests only: no real caches, parent checkpoint or CUDA."""
from __future__ import annotations
import ast
import copy
from contextlib import nullcontext, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_alm_train as study


def cached_row():
    ids=[3,20,21,4]
    return dict(row_id="synthetic0",language="ko",semantic_root_id="synthetic",
        prepared_row_sha256="A"*64,cache_row_sha256="B"*64,source_row_sha256="C"*64,
        source_row={"messages":[]},student=dict(ids=ids,labels=[-100,20,21,4],turn_ids=[0,1,1,1],ids_sha256=study.sha(ids)),
        eot_ce=True,eot_kd=False,ce_targets=3,kd_chunks=1,covered_bytes=2,
        answer_projection=dict(answer_byte_count=2),
        alignment=dict(chunks=[dict(student_shifted_indices=[0,1],student_raw_indices=[1,2],turn_id=1,
            teacher_raw_indices=[4,5],byte_start=0,byte_end=2,teacher_raw_logprob_sum=-1.2)]))


def prepared_fixture(context=None):
    context=study.resolve_context(context)
    value=dict(parent_name="native595-f",study_policy=study.policy(),
        parent_entry=dict(checkpoint=dict(path="runs/ckpt/synthetic.pt",sha256="A"*64),
            core_sha256="B"*64,header=dict(cfg=dict(width=2,layers=[0]),quantization_route="float")),
        tokenizer=dict(path="HF/synthetic_tokenizer.json",sha256="C"*64),row_sha256=["D"*64],
        cache_reports={"HF/synthetic_cache/report.json":"E"*64},
        evaluation_sha256="F"*64,evaluation_admission={"synthetic":True})
    if context.profile!=study.LEGACY_PROFILE:
        from scripts.p106b_weight_route import route_metadata
        route=route_metadata(context.profile.weight_route)
        value.update(parent_name=context.profile.parent_name,quantization_route=route,
            evaluation_selection_schema=study.EVAL_SELECTION_SCHEMA,**study.profile_fields(context))
        value['parent_entry']['header']['quantization_route']=route
        if context.profile==study.TERNARY_PROFILE:
            value['parent_entry'].update(core_sha256='6'*64,
                checkpoint=dict(path='runs/ckpt/synthetic_q.pt',sha256='7'*64))
    return value


def identity_fixture(context=None):
    p=prepared_fixture(context);common=study.study_identity(p,"1"*64,{"synthetic.py":"2"*64},context)
    return p,common


def closed_fixture(common,mode,arm,status,pin=None,context=None):
    context=study.resolve_context(context)
    phase=study.phase_identity(common,mode,arm,pin)
    return dict(schema=context.profile.schema,tag=context.profile.tag,mode=mode,arm=arm,status=status,returncode=0,
        study_identity=common,phase_identity=phase,phase_identity_sha256=study.sha(phase),
        source_code_sha256=common["source_code_sha256"],preparation_sha256=common["preparation_sha256"],
        sources_unchanged=True,inputs_unchanged=True,parent_checkpoint_unchanged=True,
        **(dict(quantization_route=common['quantization_route']) if context.profile!=study.LEGACY_PROFILE else {}),
        **study.profile_fields(context))


def calibration_fixture(common,context=None):
    report=closed_fixture(common,"calibrate",None,"ALM_GRADIENT_CALIBRATED",context=context)
    report.update(global_stats=dict(ce_norm=2.,kd_norm=1.),weight=.5,rho=.25,temperature=100.,
        optimizer_updates=0,core_before=common["parent_core_sha256"],core_after=common["parent_core_sha256"],
        rng_unchanged=True)
    pin=study.calibration_pin(report,common,"test_result/synthetic/calibrate/report.json","3"*64,context)
    return report,pin


def cost_fixture(common,arm,pin,context=None):
    report=closed_fixture(common,"cost",arm,"ALM_COST_COMPLETE",pin,context)
    report.update(updates=2,optimizer_updates=2,checkpoint_writes=0,
        initial_core_sha256=common["parent_core_sha256"],weight=pin["weight"] if arm=="alm" else 0.,
        initial_optimizer_state_empty=True,initial_gradients_all_none=True,
        initial_rng=dict(cpu="4"*64,cuda="5"*64),
        optimizer_groups=[{"synthetic":True}],optimizer_groups_after=[{"synthetic":True}])
    return report


def training_fixture(common,arm,pin,context=None):
    context=study.resolve_context(context)
    report=closed_fixture(common,"train",arm,"ALM_TRAIN_COMPLETE",pin,context)
    report.update(updates=32,optimizer_updates=32,checkpoint_writes=1,
        initial_core_sha256=common["parent_core_sha256"],weight=pin["weight"] if arm=="alm" else 0.,
        initial_optimizer_state_empty=True,initial_gradients_all_none=True,
        checkpoint=str(study.checkpoint_path(arm,context).relative_to(context.root)),
        optimizer_groups=[{"synthetic":True}],optimizer_groups_after=[{"synthetic":True}])
    report["checkpoint_experiment"]=dict(schema=context.profile.schema,tag=context.profile.tag,arm=arm,
        phase_identity=report["phase_identity"],phase_identity_sha256=report["phase_identity_sha256"],
        study_identity_sha256=study.sha(common),preparation_sha256=common["preparation_sha256"],
        parent=common["parent_checkpoint"],source_code_sha256=common["source_code_sha256"],
        weight=report["weight"],temperature=100.,rho=.25,optimizer_groups=report["optimizer_groups"],
        **(dict(quantization_route_sha256=study.sha(common['quantization_route'])) if context.profile!=study.LEGACY_PROFILE else {}),
        **study.profile_fields(context))
    return report


class StudyTests(unittest.TestCase):
    def test_import_has_no_top_level_model_or_asset_actions(self):
        tree=ast.parse(Path(study.__file__).read_text())
        imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any((isinstance(n,ast.ImportFrom) and (n.module or '').startswith(('torch','tinylm')))
                             or (isinstance(n,ast.Import) and any(v.name=='torch' for v in n.names)) for n in imports))

    def test_binding_keeps_whole_shift_and_eot_ce_not_kd(self):
        row=study.frozen_record(cached_row())
        self.assertEqual(row['record'],dict(x=[3,20,21],y=[20,21,4],segments=[1,1,1]))
        self.assertEqual(row['chunks'],[dict(positions=[0,1],teacher_logprob=-1.2,byte_count=2,teacher_target_count=2)])
        self.assertEqual(row['ce_targets'],3)

    def test_binding_rejects_double_shift_overlap_turn_and_eot(self):
        mutations=[lambda r:r['alignment']['chunks'][0].update(student_shifted_indices=[1,2]),
                   lambda r:r['alignment']['chunks'][0].update(student_shifted_indices=[0,2],student_raw_indices=[1,3]),
                   lambda r:r['alignment']['chunks'].append(copy.deepcopy(r['alignment']['chunks'][0])),
                   lambda r:r['alignment']['chunks'][0].update(turn_id=2),
                   lambda r:r['alignment']['chunks'][0].update(student_shifted_indices=[2],student_raw_indices=[3]),
                   lambda r:r['alignment']['chunks'][0].update(teacher_raw_logprob_sum=.00001),
                   lambda r:r['alignment']['chunks'][0].update(teacher_raw_logprob_sum=-3.4e38)]
        for change in mutations:
            row=cached_row();change(row)
            with self.subTest(change=change),self.assertRaises(ValueError):study.frozen_record(row)

    def test_binding_rejects_source_id_and_count_mismatch(self):
        for field,value in [('ce_targets',4),('kd_chunks',2),('eot_ce',False),('eot_kd',True)]:
            row=cached_row();row[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.frozen_record(row)
        row=cached_row();row['student']['ids'][1]=22
        with self.assertRaises(ValueError):study.frozen_record(row)

    def test_same_record_object_lookup_and_full_source_mutation_guard(self):
        row=study.frozen_record(cached_row());records,bindings=study.records_for([row])
        facade=study.ALMCore(bindings,.5);facade.configure([records])
        x,y,s=facade.pad_records(records,0,'cpu',fixed_width=8,batch_size=1)
        self.assertEqual(x.shape,(1,8));self.assertEqual(y[0].tolist(),[20,21,4,-100,-100,-100,-100,-100])
        self.assertEqual(facade.current,[dict(row=0,positions=[0,1],teacher_logprob=-1.2,
            byte_count=2,teacher_target_count=2,language='ko',row_id='synthetic0')])
        facade.configure([records]);records[0].x[0]=7
        with self.assertRaisesRegex(ValueError,'mutated'):facade.pad_records(records,0,'cpu')

    def test_source_object_replacement_and_micro_order_rejected(self):
        rows=[study.frozen_record(cached_row()) for _ in range(2)]
        records,bindings=study.records_for(rows);facade=study.ALMCore(bindings,.5);facade.configure([records])
        with self.assertRaises(ValueError):facade.pad_records(list(reversed(records)),0,'cpu')

    def test_facade_whole_update_and_unequal_micro_gradient_parity(self):
        import torch
        from tinylm.train import alm
        other=cached_row();ids=[3,20,21,22,4]
        other.update(ce_targets=4,kd_chunks=2,covered_bytes=3,answer_projection=dict(answer_byte_count=3),
            student=dict(ids=ids,labels=[-100,20,21,22,4],turn_ids=[0,1,1,1,1],ids_sha256=study.sha(ids)),
            alignment=dict(chunks=[dict(student_shifted_indices=[0],student_raw_indices=[1],turn_id=1,
                teacher_raw_indices=[4],byte_start=0,byte_end=1,teacher_raw_logprob_sum=-.3),
                dict(student_shifted_indices=[1,2],student_raw_indices=[2,3],turn_id=1,
                teacher_raw_indices=[5,6],byte_start=1,byte_end=3,teacher_raw_logprob_sum=-.9)]))
        rows=[study.frozen_record(cached_row()),study.frozen_record(other)]
        records,bindings=study.records_for(rows);facade=study.ALMCore(bindings,.3);facade.configure([[r] for r in records])
        self.assertEqual((facade.denominator,facade.chunks),(7,3))
        raw=torch.tensor([[.2,.4,.8,0.],[.3,.7,.6,.1]],dtype=torch.double,requires_grad=True)
        mask=torch.tensor([[True,True,True,False],[True,True,True,True]])
        chunks=[dict(c,row=i) for i,row in enumerate(rows) for c in row['chunks']]
        kl,k=alm.chunk_kl(raw,mask,chunks,temperature=study.TEMPERATURE)
        full=alm.normalized_loss(raw[mask].sum(),7,kl,k,weight=.3);full.backward();expected=raw.grad.clone()
        part=raw.detach().clone().requires_grad_();loss=0.
        for i in range(2):
            kd,_=alm.chunk_kl(part[i:i+1],mask[i:i+1],[dict(c,row=0) for c in rows[i]['chunks']],temperature=study.TEMPERATURE)
            loss=loss+facade.normalized_loss({1:part[i][mask[i]].sum(),'kl':kd},{1:7},{})
        loss.backward()
        self.assertTrue(torch.allclose(expected,part.grad,atol=1e-13,rtol=0))
        self.assertAlmostEqual(float(full.detach()),float(loss.detach()),places=12)

    def test_ce_only_has_no_kd_backward(self):
        import torch
        row=study.frozen_record(cached_row());records,bindings=study.records_for([row])
        facade=study.ALMCore(bindings,0.);facade.configure([records])
        ce=torch.tensor(6.,requires_grad=True);kl=torch.tensor(7.,requires_grad=True)
        facade.normalized_loss({1:ce,'kl':kl},{1:3},{}).backward()
        self.assertAlmostEqual(float(ce.grad),1/3,places=7);self.assertIsNone(kl.grad)

    def test_gradient_stats_reports_zero_and_opposite_directions(self):
        import torch
        a={'x':torch.tensor([1.,2.])};b={'x':torch.tensor([-1.,-2.])}
        report=study.gradient_stats(torch,a,b)
        self.assertEqual(report['cosine'],-1.)
        zero=study.gradient_stats(torch,a,{'x':torch.zeros(2)})
        self.assertIsNone(zero['cosine']);self.assertEqual(zero['kd_norm'],0.)

    def test_last_block_includes_unregistered_mlp_and_deduplicates_attention(self):
        import torch
        from types import SimpleNamespace
        mlp=torch.nn.Linear(2,2);attn=torch.nn.Linear(2,2)
        class Layer(torch.nn.Module):
            def __init__(self):
                super().__init__();self.attn=attn;self.mlp=[mlp]
            @property
            def attn_mod(self):return self.attn
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__();self.layers=torch.nn.ModuleList([Layer()]);self.coda_mlps=torch.nn.ModuleList([mlp])
            def visit_schedule(self):return [0]
        model=Model();index,params=study.last_block_parameters(model)
        self.assertEqual(index,0)
        self.assertEqual({id(p) for p in params},{id(p) for p in model.parameters()})
        self.assertEqual(len(params),4)

    def test_optimizer_sets_all_weight_decay_zero_and_original_lr_ratio(self):
        import torch
        parameter=torch.nn.Parameter(torch.ones(2,2));other=torch.nn.Parameter(torch.ones(2))
        class Model(torch.nn.Module):
            def __init__(self):super().__init__();self.matrix=parameter;self.other=other
        class Optimizer:
            def __init__(self,p,lr):self.param_groups=[dict(params=[p],lr=lr,weight_decay=.1)]
        adam=Optimizer(other,1e-4);muon=Optimizer(parameter,4e-4);muon.scale_mode='rms'
        with patch('scripts.diag_p101a_sft_mtp.optimizers',return_value=(adam,muon)):
            a,m=study.optimizers(Model())
        self.assertAlmostEqual(a.param_groups[0]['lr'],1e-5)
        self.assertAlmostEqual(m.param_groups[0]['lr'],4e-5)
        self.assertEqual(a.param_groups[0]['weight_decay'],0.)
        self.assertEqual(m.param_groups[0]['weight_decay'],0.)

    def test_new_checkpoint_path_not_parent_or_inference_runtime(self):
        self.assertIn(study.TAG,str(study.checkpoint_path('alm')))
        with self.assertRaises(ValueError):study.checkpoint_path('parent')
        tree=ast.parse(Path(study.__file__).read_text())
        calls=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertNotIn('selected_runtime',calls)
        self.assertIn('one_update',calls)

    def test_writer_preserves_original_and_20mb_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'small.json';study.write_new(path,{'a':1})
            with self.assertRaises(FileExistsError):study.write_new(path,{'a':2})
            with patch.object(study,'LIMIT',2):
                with self.assertRaises(ValueError):study.write_new(Path(folder)/'other.json',{'a':1})

    def test_no_execution_on_missing_or_wrong_phase(self):
        for args in (['--mode','train'],['--execute','--mode','train','--arm','parent','--source-sha256','A'],
                     ['--prepare','--execute']):
            with self.subTest(args=args),self.assertRaises(SystemExit):study.main(args)


class ObjectiveObservationTests(unittest.TestCase):
    def test_ce_components_never_call_kl_at_student_q1(self):
        import torch
        from tinylm.train import alm
        row=study.frozen_record(cached_row());records,bindings=study.records_for([row]);events=[]
        facade=study.ALMCore(bindings,0.,events.append);facade.configure([records])
        _,y,seg=facade.pad_records(records,0,'cpu',fixed_width=3,batch_size=1)
        raw=torch.zeros((1,3),requires_grad=True);mask=y.ne(-100)
        with patch.object(alm,'target_nll',return_value=(raw,mask)),patch.object(alm,'chunk_kl',side_effect=AssertionError('unused KL')) as kl:
            sums,counts=facade.components(None,None,y,seg,horizons=())
            loss=facade.normalized_loss(sums,{1:3},{})
            loss.backward()
        kl.assert_not_called();self.assertIsNone(sums['kl']);self.assertEqual(counts['kl'],1)
        self.assertTrue(torch.isfinite(loss));self.assertTrue(torch.allclose(raw.grad,torch.full_like(raw,1/3)))
        self.assertIsNone(facade.events[0]['kl_sum'])
        self.assertEqual(facade.events[0]['kl_status'],'NOT_COMPUTED_CE_ONLY')
        self.assertTrue(events[0]['observations'][0]['student_q1_boundary'])
        self.assertAlmostEqual(events[0]['observations'][0]['coefficient'],1/3)

    def test_alm_boundary_preserves_observation_before_core_rejects(self):
        import torch
        from tinylm.train import alm
        records,bindings=study.records_for([study.frozen_record(cached_row())]);events=[]
        facade=study.ALMCore(bindings,.5,events.append);facade.configure([records])
        _,y,seg=facade.pad_records(records,0,'cpu',fixed_width=3,batch_size=1)
        with patch.object(alm,'target_nll',return_value=(torch.zeros((1,3),requires_grad=True),y.ne(-100))):
            with self.assertRaises(alm.StudentProbabilityBoundary):facade.components(None,None,y,seg,horizons=())
        self.assertEqual(events[0]['observations'][0]['coefficient_sign'],'boundary')
        self.assertIsNone(events[0]['observations'][0]['coefficient'])

    def test_coefficient_matches_binary_kl_autograd_for_both_signs_and_teacher_one(self):
        import torch
        from tinylm.train import alm
        signs=set()
        for nll,teacher,weight in ((4.,-1.,.7),(1.,-100.,10.),(4.,0.,.7),(0.,0.,.7),(1e-8,-1e-7,.7)):
            with self.subTest(nll=nll,teacher=teacher):
                raw=torch.tensor([[nll]],dtype=torch.double,requires_grad=True)
                kl,k=alm.chunk_kl(raw,torch.ones_like(raw,dtype=torch.bool),
                    [dict(row=0,positions=[0],teacher_logprob=teacher)],temperature=study.TEMPERATURE)
                loss=alm.normalized_loss(raw.sum(),7,kl,k,weight=weight);loss.backward()
                event=study.chunk_observation(nll,teacher,7,1,weight,targets=1,byte_count=2,language='ko')
                self.assertTrue(math.isclose(event['coefficient'],float(raw.grad),rel_tol=1e-9,abs_tol=1e-11))
                signs.add(event['coefficient_sign'])
        self.assertEqual(signs,{'positive','negative'})

    def test_underflow_retains_raw_logq_and_ce_only_boundary_finite(self):
        row=study.chunk_observation(100000.,-100001.,10,2,.5,targets=2,byte_count=3,language='en')
        self.assertTrue(row['student_exp_underflow']);self.assertEqual(row['student_logq'],-1000.)
        self.assertEqual(row['teacher_raw_logprob_sum'],-100001.)
        ce=study.chunk_observation(0.,-4.,10,2,0.,targets=2,byte_count=3,language='ko')
        self.assertEqual(ce['coefficient'],.1);self.assertEqual(ce['coefficient_sign'],'positive')

    def test_signal_and_coverage_keep_languages_and_mass_units_separate(self):
        values=[study.chunk_observation(1.,-100.,10,2,10.,targets=2,byte_count=3,language='ko',teacher_targets=1),
                study.chunk_observation(4.,0.,10,2,.5,targets=1,byte_count=2,language='en',teacher_targets=3)]
        result=study.signal_summary(values)
        self.assertEqual(result['ko']['by_sign']['negative'],dict(chunks=1,student_targets=2,teacher_targets=1,bytes=3))
        self.assertEqual(result['en']['teacher_targets'],3)
        coverage=study.coverage_summary([dict(coverage=dict(ko=dict(ce_targets=4,answer_bytes=5,covered_bytes=3,
            student_kd_targets=2,teacher_kd_targets=1)))])
        self.assertEqual(coverage['ko']['ce_only_targets'],2)
        self.assertEqual(coverage['ko']['uncovered_answer_bytes'],2)
        self.assertEqual(coverage['ko']['answer_content_byte_acceptance'],.6)
        self.assertIsNone(coverage['en']['answer_content_byte_acceptance'])

    def test_binding_rejects_byte_overlap_outside_answer_and_empty_teacher_chunk(self):
        for change in (lambda row:row.update(covered_bytes=3),
                       lambda row:row['alignment']['chunks'][0].update(byte_start=1,byte_end=3),
                       lambda row:row['alignment']['chunks'][0].update(teacher_raw_indices=[]),
                       lambda row:row['alignment']['chunks'][0].update(teacher_raw_indices=[4,6])):
            row=cached_row();change(row)
            with self.subTest(change=change),self.assertRaises(ValueError):study.frozen_record(row)


class IdentityTests(unittest.TestCase):
    def test_common_identity_binds_preparation_parent_tokenizer_cache_rows_and_policy(self):
        p,common=identity_fixture();self.assertEqual(common['policy']['updates'],32)
        for change in (lambda v:v.update(row_sha256=['6'*64]),
                       lambda v:v['parent_entry'].update(core_sha256='6'*64),
                       lambda v:v['tokenizer'].update(sha256='6'*64),
                       lambda v:v['cache_reports'].update({'HF/other/report.json':'6'*64})):
            value=copy.deepcopy(p);change(value)
            self.assertNotEqual(study.sha(study.study_identity(value,'1'*64,common['source_code_sha256'])),study.sha(common))
        changed=copy.deepcopy(p);changed['study_policy']['micro']=4
        with self.assertRaises(ValueError):study.study_identity(changed,'1'*64,{})
        self.assertNotEqual(study.sha(study.study_identity(p,'9'*64,common['source_code_sha256'])),study.sha(common))

    def test_phase_arm_and_exact_calibration_receipt_sha_are_part_of_identity(self):
        _,common=identity_fixture();_,pin=calibration_fixture(common)
        report=cost_fixture(common,'ce',pin);study.validate_cost(report,common,'ce',pin)
        for field,value in (('sha256','9'*64),('weight',.6),('path','test_result/other/report.json')):
            other=dict(pin);other[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.validate_cost(report,common,'ce',other)
        with self.assertRaises(ValueError):study.validate_cost(report,common,'alm',pin)
        with self.assertRaises(ValueError):study.phase_identity(common,'calibrate','ce')
        with self.assertRaises(ValueError):study.phase_identity(common,'train','ce')
        with self.assertRaises(ValueError):study.phase_identity(common,'evaluate','parent',pin)

    def test_closed_report_rejects_same_code_but_different_preparation_parent_or_mutated_inputs(self):
        _,common=identity_fixture();report,_=calibration_fixture(common)
        for change in (lambda r:r.update(preparation_sha256='9'*64),
                       lambda r:r['study_identity'].update(parent_core_sha256='9'*64),
                       lambda r:r['study_identity'].update(preparation_sha256='9'*64),
                       lambda r:r.update(sources_unchanged=False),lambda r:r.update(inputs_unchanged=False),
                       lambda r:r.update(parent_checkpoint_unchanged=False),lambda r:r.update(returncode=9)):
            wrong=copy.deepcopy(report);change(wrong)
            with self.subTest(change=change),self.assertRaises(ValueError):study.calibration_pin(wrong,common,'p','S')

    def test_calibration_rejects_changed_formula_temperature_rho_core_and_optimizer_updates(self):
        _,common=identity_fixture();report,_=calibration_fixture(common)
        for change in (lambda r:r.update(weight=.6),lambda r:r.update(temperature=99.),lambda r:r.update(rho=.5),
                       lambda r:r.update(optimizer_updates=1),lambda r:r.update(core_after='9'*64),
                       lambda r:r.update(rng_unchanged=False),lambda r:r['global_stats'].update(kd_norm=0.),
                       lambda r:r['global_stats'].update(ce_norm=float('nan'))):
            wrong=copy.deepcopy(report);change(wrong)
            with self.subTest(change=change),self.assertRaises(ValueError):study.calibration_pin(wrong,common,'p','S')

    def test_cost_requires_two_updates_no_checkpoint_and_fresh_same_parent(self):
        _,common=identity_fixture();_,pin=calibration_fixture(common);report=cost_fixture(common,'alm',pin)
        for field,value in (('updates',1),('optimizer_updates',1),('checkpoint_writes',1),('weight',0.),
                            ('initial_core_sha256','9'*64),('initial_optimizer_state_empty',False),
                            ('initial_gradients_all_none',False),('initial_rng',None),('optimizer_groups_after',[])):
            wrong=copy.deepcopy(report);wrong[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.validate_cost(wrong,common,'alm',pin)

    def test_training_receipt_requires_exact_checkpoint_experiment(self):
        _,common=identity_fixture();_,pin=calibration_fixture(common);report=training_fixture(common,'alm',pin)
        study.validate_training(report,common,'alm',pin)
        for field,value in (('arm','ce'),('tag','other'),('preparation_sha256','9'*64),('weight',.6),
                            ('source_code_sha256',{}),('parent',{}),('temperature',1.),('rho',.5),
                            ('study_identity_sha256','9'*64),('optimizer_groups',[])):
            wrong=copy.deepcopy(report);wrong['checkpoint_experiment'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.validate_training(wrong,common,'alm',pin)
        wrong=copy.deepcopy(report);wrong['checkpoint']='runs/ckpt/other.pt'
        with self.assertRaises(ValueError):study.validate_training(wrong,common,'alm',pin)

    def test_child_header_accepts_only_json_tuple_equivalence_and_exact_experiment(self):
        p,common=identity_fixture();_,pin=calibration_fixture(common)
        experiment=training_fixture(common,'ce',pin)['checkpoint_experiment']
        payload=dict(model={},cfg=dict(width=2,layers=(0,)),step=32,experiment=experiment,
            tokenizer_sha256=p['tokenizer']['sha256'],tokenizer_lineage='chat32',quantization_route='float')
        study.child_header(payload,p,experiment)
        for change in (lambda v:v['cfg'].update(width=3),lambda v:v['experiment'].update(arm='alm'),
                       lambda v:v.update(step=31),lambda v:v.update(tokenizer_sha256='9'*64),
                       lambda v:v.update(quantization_route='ternary'),lambda v:v.update(opt={})):
            wrong=copy.deepcopy(payload);change(wrong)
            with self.subTest(change=change),self.assertRaises(ValueError):study.child_header(wrong,p,experiment)

    def test_closed_json_and_input_hashes_are_actual_bytes_not_only_declared_sha(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'value.json';study.write_new(path,{'synthetic':1})
            value,actual=study.closed_read(path)
            self.assertEqual(value,{'synthetic':1});self.assertEqual(actual,hashlib.sha256(path.read_bytes()).hexdigest().upper())
            with patch.object(study,'digest',side_effect=['A','B']):
                with self.assertRaisesRegex(ValueError,'changed'):study.closed_read(path)
        with patch.object(study,'digest',return_value='A'):
            self.assertEqual(study.verify_pins({'HF/synthetic.json':'A'}),{'HF/synthetic.json':'A'})
            with self.assertRaisesRegex(ValueError,'changed'):study.verify_pins({'HF/synthetic.json':'B'})

    def test_input_paths_refuse_traversal_other_run_directories_and_protected_paths(self):
        for name in ('HF/../datasets/x','/HF/x','datasets/TinyDataset/a','runs/logs/x','scripts/x'):
            with self.subTest(name=name),self.assertRaises(ValueError):study.input_path(name)

    def test_phase_input_inventory_includes_preparation_shards_and_prerequisite_exact_bytes(self):
        with patch.object(study,'BASE',study.ROOT/'HF/synthetic'):
            p=dict(input_pins={'HF/source.json':'A'},prepared_artifact_pins={'HF/synthetic/aligned.jsonl':'B'})
            pins=study.phase_input_pins(p,'C',{'test_result/synthetic/report.json':'D'})
        self.assertEqual(pins,{'HF/source.json':'A','HF/synthetic/aligned.jsonl':'B',
            'HF/synthetic/report.json':'C','test_result/synthetic/report.json':'D'})


class AdmissionAndMetricTests(unittest.TestCase):
    def test_expired_initial_or_post_idle_deadline_prevents_cuda_transfer(self):
        for expire_at in (1,2):
            calls=[]
            class Guard:
                def check(self,stage):
                    calls.append(stage)
                    if len(calls)==expire_at:raise TimeoutError('synthetic absolute deadline')
            model=SimpleNamespace(cuda=lambda:(_ for _ in ()).throw(AssertionError('CUDA not allowed')))
            with self.subTest(expire_at=expire_at),self.assertRaises(TimeoutError):study.cuda_admission(model,Guard(),lambda:None)

    def test_cuda_admission_checks_after_slow_idle_before_transfer(self):
        clock=[0];calls=[]
        class Guard:
            def check(self,stage):
                calls.append(stage)
                if clock[0]>10:raise TimeoutError(stage)
        def idle():clock[0]=11
        with self.assertRaises(TimeoutError):study.cuda_admission(SimpleNamespace(cuda=lambda:calls.append('CUDA')),Guard(),idle)
        self.assertNotIn('CUDA',calls)

    def test_existing_guard_absolute_deadline_catches_slow_cpu_admission(self):
        from datetime import timedelta
        from scripts import diag_p101a_padding_gpu as updater
        clock=[study.DEADLINE-timedelta(seconds=1)];called=[]
        guard=updater.Guard(study.DEADLINE,60)
        def idle():clock[0]=study.DEADLINE
        with patch.object(updater,'utc_now',side_effect=lambda:clock[0]):
            with self.assertRaises(TimeoutError):
                study.cuda_admission(SimpleNamespace(cuda=lambda:called.append('CUDA')),guard,idle)
        self.assertEqual(called,[])

    def test_child_hash_and_deadline_gate_precede_any_tensor_load(self):
        calls=[]
        fake=SimpleNamespace(load=lambda stream,**kw:(calls.append((stream.read(),kw)) or {'synthetic':True}))
        guard=SimpleNamespace(check=lambda stage:None)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'not_a_checkpoint.json';study.write_new(path,{'owned_fixture':True})
            with self.assertRaisesRegex(ValueError,'SHA'):study.child_payload(fake,path,'0'*64,guard)
            self.assertEqual(calls,[])
            value=study.child_payload(fake,path,study.digest(path),guard)
            self.assertEqual(value,{'synthetic':True});self.assertEqual(calls[0][1],dict(map_location='cpu',weights_only=True))
            calls.clear()
            def expired(stage):
                if stage=='before CPU child tensor load':raise TimeoutError(stage)
            with self.assertRaises(TimeoutError):study.child_payload(fake,path,study.digest(path),SimpleNamespace(check=expired))
            self.assertEqual(calls,[])

    def test_strict_and_collapsed_whitespace_metrics_are_distinct(self):
        for answer in (' A  B ','A\nB','A B'):
            result=study.grade(answer,['A  B'])
            self.assertFalse(result['strict_whitespace_exact']);self.assertFalse(result['exact_original'])
            self.assertTrue(result['whitespace_normalized_exact'])
        exact=study.grade('A  B',['A  B']);self.assertTrue(exact['strict_whitespace_exact'])
        self.assertNotIn('whitespace_exact',exact)

    def test_real_prompt_gate_and_long_reference_disclosure_do_not_filter_cases(self):
        class Tokens:
            def encode(self,text):return SimpleNamespace(ids=list(text.encode('utf-8')))
        rows=[dict(messages=[dict(role='user',content='Q'),dict(role='assistant',content='a'*65)],
                   meta=dict(language='ko',answers=[dict(text='a'*65)])),
              dict(messages=[dict(role='user',content='R'),dict(role='assistant',content='b')],
                   meta=dict(language='en',answers=[dict(text='b'*65),dict(text='b')]))]
        with patch.object(study,'USER_QUESTIONS',()):
            result=study.evaluation_admission(dict(evaluation_rows=rows),Tokens(),render=lambda q:'P:'+q+'|')
            self.assertEqual(len(result['cases']),2);self.assertEqual(result['long_reference_cases'],1)
            self.assertEqual(result['cases'][0]['reference_lengths'][0]['body_tokens'],65)
            self.assertEqual(len(result['cases'][1]['reference_lengths']),2)
            with self.assertRaisesRegex(ValueError,'no replacement/truncation'):
                study.evaluation_admission(dict(evaluation_rows=rows),Tokens(),max_seq=67,render=lambda q:'P:'+q+'|')

    def test_unstable_joint_prefix_is_unknown_not_false_length_pass(self):
        class Tokens:
            def encode(self,text):return SimpleNamespace(ids=[0] if text=='P' else [1,2])
        row=dict(messages=[dict(role='user',content='Q'),dict(role='assistant',content='A')],
                 meta=dict(language='ko',answers=[dict(text='A')]))
        with patch.object(study,'USER_QUESTIONS',()):
            result=study.evaluation_admission(dict(evaluation_rows=[row]),Tokens(),render=lambda q:'P')
        value=result['cases'][0]['reference_lengths'][0]
        self.assertIsNone(value['body_tokens']);self.assertIsNone(value['exceeds_max_new'])
        self.assertFalse(value['joint_prefix_stable'])
        self.assertEqual(result['unknown_reference_length_cases'],1)

    def test_generation_must_match_the_actual_admitted_prompt_bytes_and_length(self):
        admitted=dict(prompt_tokens=10,prompt_sha256='A'*64)
        study.generation_admission(dict(admitted),admitted)
        for field,value in (('prompt_tokens',11),('prompt_sha256','B'*64)):
            wrong=dict(admitted);wrong[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.generation_admission(wrong,admitted)

    def test_execute_full_wall_includes_setup_failure_and_never_enters_runtime(self):
        clock=[10.];code={'synthetic':'A'}
        class Guard:
            def __init__(self,*args):self.started=clock[0]
            def check(self,stage):pass
        def auth(cap):clock[0]+=2.;return {'synthetic':True}
        def pins(*args):clock[0]+=3.;return code
        def load(*args):clock[0]+=7.;raise ValueError('synthetic preparation failed')
        from scripts import diag_p101a_padding_gpu as updater
        from scripts import p106b_gate_runtime as gate
        with tempfile.TemporaryDirectory() as folder,patch.object(study,'EVIDENCE',Path(folder)),\
             patch.object(study.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(study,'authority',side_effect=auth),\
             patch.object(study,'sources',side_effect=pins),patch.object(study,'load_prepared',side_effect=load),\
             patch.object(updater,'Guard',Guard),patch.object(gate,'wall_limit',side_effect=lambda cap:nullcontext()),\
             patch.object(study,'runtime',side_effect=AssertionError('must not enter model runtime')) as runtime,redirect_stdout(io.StringIO()):
            rc=study.execute(SimpleNamespace(mode='calibrate',arm=None,max_wall_sec=60,source_sha256=study.sha(code)))
            report=study.read(Path(folder)/'calibrate/report.json')
            self.assertEqual(rc,9);self.assertEqual(report['wall_seconds'],12.)
            self.assertFalse(report['inputs_unchanged']);runtime.assert_not_called()

    def test_prepare_wall_starts_before_import_and_cpu_selection(self):
        clock=[10.]
        from scripts import diag_p101a_padding_gpu as updater
        from scripts import p106b_gate_runtime as gate
        class Guard:
            def __init__(self,*args):self.started=clock[0]
        def auth(cap):clock[0]+=3.;return {'synthetic':True}
        def select(guard,started,admission,context):
            clock[0]+=7.
            self.assertEqual(guard.started,10.);self.assertEqual(started,10.)
            return dict(wall=clock[0]-started)
        with patch.object(study.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(study,'authority',side_effect=auth),\
             patch.object(updater,'Guard',Guard),patch.object(gate,'wall_limit',side_effect=lambda cap:nullcontext()),\
             patch.object(study,'_prepare',side_effect=select):
            self.assertEqual(study.prepare(60)['wall'],10.)

    def test_optimizer_receipt_names_hash_hyperparameters_and_json_roundtrip(self):
        import torch
        model=torch.nn.Linear(2,2)
        adam=SimpleNamespace(param_groups=[dict(params=[model.bias],lr=1e-5,weight_decay=0.,betas=(.9,.95),eps=1e-8,amsgrad=False)])
        muon=SimpleNamespace(param_groups=[dict(params=[model.weight],lr=4e-5,weight_decay=0.,momentum=.95,
            nesterov=True,ns_steps=5,scale_mode='rms')])
        result=study.optimizer_receipt(model,(adam,muon))
        self.assertEqual(result[0]['names'],['bias']);self.assertEqual(result[0]['names_sha256'],study.sha(['bias']))
        self.assertEqual(result[0]['hyperparameters']['betas'],[.9,.95])
        self.assertIs(result[0]['hyperparameters']['amsgrad'],False)
        self.assertEqual(result[1]['elements'],4);self.assertEqual(result[1]['hyperparameters']['ns_steps'],5)
        self.assertEqual(result,json.loads(study.canonical(result)))

    def test_execute_child_passes_exact_closed_checkpoint_sha_before_runtime(self):
        from contextlib import contextmanager
        from scripts import diag_p101a_padding_gpu as updater
        from scripts import p106b_gate_runtime as gate
        class Guard:
            def __init__(self,*args):self.started=0
            def check(self,stage):pass
        with tempfile.TemporaryDirectory() as folder,patch.object(study,'ROOT',Path(folder)),\
             patch.object(study,'BASE',Path(folder)/'HF/synthetic'),\
             patch.object(study,'EVIDENCE',Path(folder)/'test_result/synthetic'):
            p,common=identity_fixture();p.update(input_pins={},prepared_artifact_pins={})
            cal,pin=calibration_fixture(common)
            pin['path']='test_result/synthetic/calibrate/report.json'
            train=training_fixture(common,'alm',pin);train.update(final_core_sha256='6'*64,checkpoint_sha256='7'*64)
            calls=[]
            @contextmanager
            def runtime(*args,**kwargs):
                calls.append(args)
                yield SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda:None)),object(),object(),object()
            def closed(path):
                return (cal,'3'*64) if path.parent.name=='calibrate' else (train,'8'*64)
            with patch.object(study,'authority',return_value={}),patch.object(study,'sources',return_value=common['source_code_sha256']),\
                 patch.object(study,'load_prepared',return_value=(p,[],'1'*64)),patch.object(study,'closed_read',side_effect=closed),\
                 patch.object(study,'verify_pins',side_effect=lambda pins,guard,context:pins),patch.object(study,'runtime',side_effect=runtime),\
                 patch.object(study,'evaluate',return_value=dict(status='ALM_EVALUATION_COMPLETE')),\
                 patch.object(updater,'Guard',Guard),patch.object(gate,'wall_limit',side_effect=lambda cap:nullcontext()),\
                 redirect_stdout(io.StringIO()):
                rc=study.execute(SimpleNamespace(mode='evaluate',arm='alm',max_wall_sec=60,
                    source_sha256=study.sha(common['source_code_sha256'])))
            report=study.read(study.EVIDENCE/'evaluate_alm/report.json')
            self.assertEqual(rc,0);self.assertEqual(calls[0][-1],'7'*64)
            self.assertEqual(calls[0][2],study.checkpoint_path('alm'))
            self.assertEqual(calls[0][4],train['checkpoint_experiment'])
            self.assertEqual(report['inputs_before'][train['checkpoint']],'7'*64)
            self.assertEqual(report['inputs_before'],report['inputs_after'])


class StudyProfileTests(unittest.TestCase):
    def test_profiles_are_immutable_separate_namespaces_and_default_is_legacy(self):
        from dataclasses import FrozenInstanceError, replace
        default=study.study_context()
        self.assertEqual((default.profile.tag,default.base,default.evidence),(study.TAG,study.BASE,study.EVIDENCE))
        contexts=[study.study_context(p.name) for p in study.STUDY_PROFILES]
        self.assertEqual(len({study.checkpoint_path('ce',c) for c in contexts}),3)
        self.assertEqual(len({c.base for c in contexts}),3)
        for context in contexts:
            with self.assertRaises(FrozenInstanceError):context.profile.weight_route='float'
            with self.assertRaises(FrozenInstanceError):context.base=Path('/tmp')
        with self.assertRaises(ValueError):study.study_context('unknown')
        with self.assertRaises(ValueError):study.resolve_context(replace(contexts[-1],base=contexts[1].base))

    def test_cli_selects_profile_explicitly_and_default_retains_old_api(self):
        for name in ('float_v1','float_v2','ternary_v1'):
            args=[] if name=='float_v1' else ['--study',name]
            output=io.StringIO()
            with patch.object(study,'sources',return_value={'synthetic.py':'A'*64}),redirect_stdout(output):
                self.assertEqual(study.main(args),0)
            receipt=json.loads(output.getvalue())
            self.assertEqual(receipt['tag'],study.study_context(name).profile.tag)
            self.assertEqual((receipt['model_loads'],receipt['gpu_calls']),(0,0))
        with self.assertRaises(ValueError):
            study.execute(SimpleNamespace(study='float_v2'),study.study_context('ternary_v1'))

    def test_source_closure_includes_fixture_package_and_runtime_owners(self):
        code=study.sources()
        required={'scripts/diag_p106b_alm_train.py','scripts/test_p106b_alm_train.py',
            'scripts/test_p106b_weight_route.py','scripts/p106b_weight_route.py',
            'scripts/diag_p101a_padding_gpu.py','scripts/interactive_research_infer.py',
            'tinylm/__init__.py','tinylm/paths.py','tinylm/model/__init__.py',
            'tinylm/model/ternary_kernel.py','tinylm/train/__init__.py','tinylm/train/trainer.py',
            'tinylm/train/lr_finder.py','tinylm/audit_io.py','tinylm/chat/canonical.py'}
        self.assertTrue(required<=set(code));self.assertEqual(len(code),len(study.SOURCE_NAMES))
        self.assertTrue(all(name.startswith(('scripts/','tinylm/')) and name.endswith('.py') for name in code))
        self.assertTrue(all(len(value)==64 for value in code.values()))
        # Read only the producer's literal source contract, never a live cache.
        tree=ast.parse((study.ROOT/'scripts/diag_p106b_alm_cache.py').read_text(encoding='utf-8'))
        producer=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='CODE' for t in n.targets))
        self.assertTrue(set(producer)<=set(code))
        self.assertFalse({'scripts/diag_p106b_alm_train.py','scripts/test_p106b_alm_train.py'}&set(producer))

    def test_new_parent_route_header_and_profile_crossing_rejected(self):
        for name in ('float_v2','ternary_v1'):
            context=study.study_context(name);p,common=identity_fixture(context)
            self.assertEqual(common['study_profile']['quantization_scope'],'TLINEAR_WEIGHTS_ONLY')
            self.assertEqual(common['study_profile']['embedding_head_policy'],'FP32_TIED_EMBEDDING_AND_HEAD')
            for change in (lambda p:p.update(parent_name='native595-q' if name=='float_v2' else 'native595-f'),
                           lambda p:p['parent_entry']['header']['quantization_route'].update(mode='ternary' if name=='float_v2' else 'float'),
                           lambda p:p.update(study_profile_sha256='0'*64),
                           lambda p:p.update(evaluation_selection_schema='NEW_SCHEMA'),
                           lambda p:p.update(quantization_route={})): 
                wrong=copy.deepcopy(p);change(wrong)
                with self.subTest(name=name,change=change),self.assertRaises(ValueError):
                    study.study_identity(wrong,'1'*64,{},context)

    def test_calibration_cost_and_child_cannot_cross_new_or_legacy_profiles(self):
        contexts=[study.study_context(p.name) for p in study.STUDY_PROFILES]
        fixtures=[]
        for c in contexts:
            p,common=identity_fixture(c);cal,pin=calibration_fixture(common,c)
            study.validate_cost(cost_fixture(common,'alm',pin,c),common,'alm',pin,c)
            train=training_fixture(common,'alm',pin,c);study.validate_training(train,common,'alm',pin,c)
            payload=dict(model={},cfg=p['parent_entry']['header']['cfg'],step=32,
                experiment=train['checkpoint_experiment'],tokenizer_sha256=p['tokenizer']['sha256'],
                tokenizer_lineage='chat32',quantization_route=p['parent_entry']['header']['quantization_route'])
            study.child_header(payload,p,train['checkpoint_experiment'],c)
            fixtures.append((p,common,cal,pin,train,payload))
        for i,c in enumerate(contexts):
            p,common,_,pin,train,_=fixtures[i]
            for j,other in enumerate(contexts):
                if i==j:continue
                _,_,cal,foreign_pin,foreign_train,foreign_payload=fixtures[j]
                with self.subTest(receiver=c.profile.name,sender=other.profile.name):
                    with self.assertRaises(ValueError):study.calibration_pin(cal,common,'p','S',c)
                    with self.assertRaises(ValueError):study.validate_training(foreign_train,common,'alm',pin,c)
                    with self.assertRaises(ValueError):study.child_header(foreign_payload,p,train['checkpoint_experiment'],c)
                    if c.profile!=study.LEGACY_PROFILE:
                        with self.assertRaises(ValueError):study.phase_identity(common,'train','alm',foreign_pin)

    def test_new_receipts_reject_route_mutation_and_calibration_from_other_preparation(self):
        context=study.study_context('ternary_v1');_,common=identity_fixture(context)
        cal,pin=calibration_fixture(common,context)
        wrong=copy.deepcopy(cal);wrong['quantization_route']['mode']='float'
        with self.assertRaises(ValueError):study.calibration_pin(wrong,common,'p','S',context)
        other=copy.deepcopy(common);other['preparation_sha256']='9'*64
        _,foreign_pin=calibration_fixture(other,context)
        with self.assertRaises(ValueError):study.phase_identity(common,'train','alm',foreign_pin)
        changed=dict(pin,weight=.6)
        # The exact pin is also part of each closed cost receipt.
        with self.assertRaises(ValueError):
            study.validate_cost(cost_fixture(common,'alm',pin,context),common,'alm',changed,context)

    def test_eval64_is_literal_legacy_selection_not_profile_schema(self):
        rows=[dict(meta=dict(language=lang,semantic_root_id=f'{lang}-{i}')) for lang in ('ko','en') for i in range(64)]
        old=[]
        for lang in ('ko','en'):
            pool=[r for r in rows if r['meta']['language']==lang]
            pool.sort(key=lambda r:study.sha(['P106B_ALM_REFERENCE_TRAIN_V1',1337,'FIXED_DEV',r['meta']['semantic_root_id']]))
            old.extend(pool[:32])
        for profile in study.STUDY_PROFILES:
            self.assertEqual(profile.metadata()['evaluation_selection_schema'],'P106B_ALM_REFERENCE_TRAIN_V1')
            self.assertEqual(study.fixed_evaluation_rows(list(reversed(rows))),old)
        self.assertEqual(len(study.fixed_evaluation_rows(rows)),64)

    def test_old_preparation_source_pin_is_not_runtime_reusable(self):
        context=study.study_context('ternary_v1')
        p=prepared_fixture(context)
        p.update(schema=context.profile.schema,tag=context.profile.tag,status='ALM_TRAIN_PREPARED',
            source_code_sha256={'old.py':'old'},inputs_unchanged=True)
        with patch.object(study,'closed_read',return_value=(p,'1'*64)),\
             patch.object(study,'sources',return_value={'current.py':'new'}):
            with self.assertRaisesRegex(ValueError,'same-code'):study.load_prepared(context)

    def test_new_context_reaches_every_execute_phase_and_child_path_without_global_retag(self):
        from contextlib import contextmanager
        from scripts import diag_p101a_padding_gpu as updater
        from scripts import p106b_gate_runtime as gate
        class Guard:
            def __init__(self,*args):self.started=0
            def check(self,stage):pass
        legacy=(study.TAG,study.SCHEMA,study.BASE,study.EVIDENCE)
        for name in ('float_v2','ternary_v1'):
            with tempfile.TemporaryDirectory() as folder:
                context=study.study_context(name,root=Path(folder))
                p,common=identity_fixture(context);p.update(input_pins={},prepared_artifact_pins={})
                cal,pin=calibration_fixture(common,context)
                pin['path']=str((context.evidence/'calibrate/report.json').relative_to(context.root))
                reports={'calibrate':(cal,'3'*64)}
                for arm in ('ce','alm'):
                    cost=cost_fixture(common,arm,pin,context)
                    cost.update(wall_seconds=1.,training_seconds=.1)
                    train=training_fixture(common,arm,pin,context)
                    train.update(final_core_sha256='8'*64,checkpoint_sha256='9'*64)
                    reports['cost_'+arm]=(cost,'4'*64)
                    reports['train_'+arm]=(train,'5'*64)
                entries=[];loaded=[]
                @contextmanager
                def runtime(*args,context):
                    entries.append((args,context))
                    yield SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda:None)),object(),object(),object()
                def load(received):
                    loaded.append(received);return p,[],'1'*64
                def train(*args,**kwargs):
                    self.assertEqual(kwargs['context'],context)
                    kwargs['observer'](dict(event='synthetic_update_only'))
                    return reports[('cost_' if kwargs['cost'] else 'train_')+args[4]][0]
                def calibration(*args):
                    args[-1](dict(event='synthetic_calibration_only'))
                    return cal
                def closed(path):
                    self.assertEqual(path.parent.parent,context.evidence)
                    return reports[path.parent.name]
                phases=[('calibrate',None),('cost','ce'),('cost','alm'),('train','ce'),('train','alm'),
                        ('evaluate','parent'),('evaluate','ce'),('evaluate','alm')]
                with patch.object(study,'authority',return_value={}),\
                     patch.object(study,'sources',return_value=common['source_code_sha256']),\
                     patch.object(study,'load_prepared',side_effect=load),\
                     patch.object(study,'closed_read',side_effect=closed),\
                     patch.object(study,'verify_pins',side_effect=lambda pins,guard,context:pins),\
                     patch.object(study,'runtime',side_effect=runtime),\
                     patch.object(study,'calibrate',side_effect=calibration),patch.object(study,'do_train',side_effect=train),\
                     patch.object(study,'evaluate',return_value=dict(status='ALM_EVALUATION_COMPLETE')) as evaluate,\
                     patch.object(updater,'Guard',Guard),patch.object(gate,'wall_limit',side_effect=lambda cap:nullcontext()),\
                     redirect_stdout(io.StringIO()):
                    for mode,arm in phases:
                        args=SimpleNamespace(study=name,mode=mode,arm=arm,max_wall_sec=60,
                            source_sha256=study.sha(common['source_code_sha256']))
                        rc=study.execute(args,context)
                        key=mode+('_'+arm if arm else '')
                        receipt=study.read(context.evidence/key/'report.json')
                        self.assertEqual(rc,0,(name,key,receipt.get('error_type'),receipt.get('error')))
                        self.assertEqual(receipt['tag'],context.profile.tag)
                        self.assertEqual(receipt['study_identity'],common)
                        self.assertIn(str((context.base/'report.json').relative_to(context.root)),receipt['inputs_before'])
                self.assertEqual(loaded,[context]*8)
                self.assertTrue(all(entry[1]==context for entry in entries))
                for arm,entry in zip(('ce','alm'),entries[-2:]):
                    self.assertEqual(entry[0][2],study.checkpoint_path(arm,context))
                    self.assertEqual(entry[0][-1],'9'*64)
                self.assertTrue(all(call.args[-1]==context for call in evaluate.call_args_list))
                self.assertEqual((study.TAG,study.SCHEMA,study.BASE,study.EVIDENCE),legacy)

    def test_runtime_uses_same_route_for_cpu_child_and_gpu_context_without_cuda(self):
        import torch
        from scripts import p106b_weight_route as route
        from scripts import interactive_research_infer as ui
        from scripts.test_p106b_weight_route import Mini
        guard=SimpleNamespace(check=lambda stage:None)
        for name in ('float_v2','ternary_v1'):
            context=study.study_context(name);p,common=identity_fixture(context)
            _,pin=calibration_fixture(common,context)
            experiment=training_fixture(common,'alm',pin,context)['checkpoint_experiment']
            initial=Mini();initial.cfg.grad_checkpoint=True;initial.cfg.max_seq_len=1024
            core=ui.state_fingerprint(initial);p['parent_entry']['core_sha256']=core
            payload=dict(model={k:v.detach().clone() for k,v in initial.state_dict().items()},
                cfg=p['parent_entry']['header']['cfg'],step=32,experiment=experiment,
                tokenizer_sha256=p['tokenizer']['sha256'],tokenizer_lineage='chat32',
                quantization_route=route.route_metadata(context.profile.weight_route))
            token=SimpleNamespace(token_to_id=lambda token:0)
            with torch.random.fork_rng(devices=[]),patch.object(ui,'validate_import_environment'),\
                 patch.object(ui,'resolve_model',return_value=SimpleNamespace(arm=context.profile.weight_route)),\
                 patch.object(ui,'read_selected_payload',return_value=payload),patch.object(ui,'validate_cfg'),\
                 patch.object(ui,'local_tokenizer',return_value=token),\
                 patch('tinylm.config.TMTConfig',return_value=initial.cfg),\
                 patch('tinylm.model.TiedMLPTransformer',side_effect=lambda cfg:Mini()),\
                 patch.object(study,'evaluation_admission',return_value=p['evaluation_admission']),\
                 patch.object(study,'child_payload',return_value=payload),\
                 patch.object(study,'cuda_admission',side_effect=lambda m,g,i:m) as admission,\
                 patch.object(torch.cuda,'empty_cache'),\
                 patch.object(route,'weight_route',wraps=route.weight_route) as contexts,\
                 patch.object(route,'load_routed_state',wraps=route.load_routed_state) as loads:
                with study.runtime(p,guard,Path('/synthetic/never_opened.pt'),core,experiment,'A'*64,context=context) as active:
                    self.assertEqual(active[3].mode,context.profile.weight_route)
                    active[3].assert_active()
                self.assertEqual([call.args[1] for call in contexts.call_args_list],[context.profile.weight_route]*3)
                self.assertEqual([call.args[2] for call in loads.call_args_list],[context.profile.weight_route]*2)
                admission.assert_called_once()
        self.assertFalse(torch.cuda.is_initialized())


class TernaryIntegrationTests(unittest.TestCase):
    def test_hard_one_forward_and_surrogate_window_not_numerical_derivative(self):
        import torch
        import torch.nn.functional as F
        from scripts import p106b_weight_route as route
        from scripts.test_p106b_weight_route import Mini
        model=Mini();x=torch.tensor([[.3,-.7]],requires_grad=True)
        with route.weight_route(model,'ternary'):
            model.set_anneal(1.);model.refresh_quant()
            w=model.a.weight.detach();wg=w.reshape(2,1,2);aw=wg.abs()
            mask=(aw>=model.cfg.twn_thr_ratio*aw.mean(2,keepdim=True)).to(w.dtype)
            alpha=(aw*mask).sum(2,keepdim=True)/mask.sum(2,keepdim=True).clamp_min(1)
            expected=(wg.sign()*mask*alpha).reshape_as(w)
            self.assertTrue(torch.equal(model.a._wq.detach(),expected))
            output=model.a(x);output.sum().backward()
            window=1/(1+(aw/(model.cfg.ste_clip*alpha).clamp_min(1e-8)).pow(4))
            torch.testing.assert_close(model.a.weight.grad,x.detach().expand_as(w)*window.reshape_as(w),rtol=0,atol=0)
            torch.testing.assert_close(output,F.linear(x,expected),rtol=0,atol=0)
            torch.testing.assert_close(x.grad,expected.sum(0,keepdim=True),rtol=0,atol=0)
            self.assertFalse(torch.equal(model.a.weight.grad,x.detach().expand_as(w)))

    def test_checkpoint_recompute_update_refresh_and_strict_reload(self):
        import torch
        from torch.utils.checkpoint import checkpoint
        from scripts import p106b_weight_route as route
        from scripts.test_p106b_weight_route import Mini
        plain,recomputed=Mini(),Mini()
        inputs=[torch.tensor([[.3,-.8]],requires_grad=True) for _ in range(2)]
        saved=None
        for model,x,use_checkpoint in zip((plain,recomputed),inputs,(False,True)):
            optimizer=torch.optim.SGD(model.parameters(),lr=.03)
            with route.weight_route(model,'ternary') as active:
                model.set_anneal(1.)
                with patch.object(model,'refresh_quant',wraps=model.refresh_quant) as refresh:
                    y=checkpoint(model,x,use_reentrant=False) if use_checkpoint else model(x)
                    y.square().sum().backward()
                    self.assertGreaterEqual(refresh.call_count,2 if use_checkpoint else 1)
                if use_checkpoint:
                    torch.testing.assert_close(y,expected,rtol=0,atol=0)
                    torch.testing.assert_close(x.grad,inputs[0].grad,rtol=0,atol=0)
                    for p,g in zip(model.parameters(),gradients):torch.testing.assert_close(p.grad,g,rtol=0,atol=0)
                else:
                    expected=y.detach().clone();gradients=[p.grad.clone() for p in model.parameters()]
                old_cache=model.a._wq
                optimizer.step();optimizer.zero_grad(set_to_none=True)
                model.clear_quant();model.refresh_quant()
                self.assertIsNot(model.a._wq,old_cache)
                self.assertTrue(all(p.grad is None for p in model.parameters()))
                # A deterministic optimizer-like update changes the hard codes.
                with torch.no_grad():model.a.weight.copy_(torch.tensor([[.9,.1],[-.7,-.4]]))
                model.clear_quant();model.refresh_quant()
                self.assertEqual(model.a._wq[0,1].item(),0.)
                model.eval()
                with torch.no_grad():model.freeze_quant();after=model(x.detach()).clone()
                saved=dict(model={k:v.detach().clone() for k,v in model.state_dict().items()},
                    quantization_route=route.route_metadata('ternary'))
            self.assertTrue(active.cache_invalidated);self.assertIsNone(model.a._wq)
        fresh=Mini();before=[p.detach().clone() for p in fresh.parameters()]
        with route.weight_route(fresh,'ternary'):
            with self.assertRaises(ValueError):route.load_routed_state(fresh,dict(saved,quantization_route=route.route_metadata('float')),'ternary')
            for p,b in zip(fresh.parameters(),before):self.assertTrue(torch.equal(p,b))
            route.load_routed_state(fresh,saved,'ternary');self.assertIsNone(fresh.a._wq)
            fresh.set_anneal(1.);fresh.eval()
            with torch.no_grad():fresh.freeze_quant();torch.testing.assert_close(fresh(inputs[0].detach()),after,rtol=0,atol=0)
        self.assertFalse(torch.cuda.is_initialized())


class UpdaterConnectionTests(unittest.TestCase):
    def run_mock_train(self,*,cost,arm='ce',bad_rng=False,dirty_grad=False,bad_optimizer=False,context=None):
        from dataclasses import make_dataclass
        from scripts import diag_p101a_padding_gpu as updater
        from scripts import diag_p101a_sft_mtp as original
        from scripts import interactive_research_infer as ui
        context=study.resolve_context(context)
        p,common=identity_fixture(context);cal,pin=calibration_fixture(common,context)
        p['whole_exposure']=dict(actual_x_tokens=4*1024*3,ce_targets=4*1024*3,kd_chunks=4*1024)
        phase=study.phase_identity(common,'cost' if cost else 'train',arm,pin)
        row=study.frozen_record(cached_row())
        rows=[dict(row,row_id='synthetic'+str(i),language='ko' if i%2==0 else 'en') for i in range(1024)]
        class Parameter:
            requires_grad=True
            grad=1 if dirty_grad else None
            def numel(self):return 1
            def detach(self):return self
            def cpu(self):return 'SYNTHETIC_NOT_MODEL_WEIGHT'
        parameter=Parameter()
        class Model:
            cfg=make_dataclass('Cfg',[('width',int),('layers',tuple)])(2,(0,))
            def parameters(self):return iter([parameter])
            def named_parameters(self):return iter([('synthetic',parameter)])
            def state_dict(self):return {'synthetic':parameter}
        opt=SimpleNamespace(state={},param_groups=[dict(params=[parameter],lr=1e-5,weight_decay=0.)])
        calls=[];saved=[];observed=[];rng=dict(cpu='4'*64,cuda='5'*64)
        def batches(records,epoch):
            for start in range(0,1024,128):
                yield [records[index:index+8] for index in range(start,start+128,8)]
        def update(torch,facade,model,opts,groups,plan,policy,precision,guard,journal,block,index,stage):
            self.assertEqual((len(groups),len(groups[0]),policy,precision),(16,8,'fixed1024','bf16_eager'))
            self.assertEqual(facade.denominator,128*3);self.assertEqual(facade.chunks,128)
            for micro in groups:
                facade.pad_records(micro,0,'cpu',fixed_width=3,batch_size=8)
                facade.events.append(dict(kd_chunks=len(micro),kl_sum=.5*len(micro) if facade.weight else None,
                    coverage=facade.current_coverage))
            facade.observer(dict(event='synthetic_update'))
            calls.append((index,stage))
            return dict(update=index,loss=2.,assistant_targets=plan['assistant_targets'],
                actual_x_tokens=plan['actual_x_tokens'],whole_update_seconds=.01),None
        def save(payload,stream):
            saved.append(payload);stream.write(b'OWNED_SYNTHETIC_RECEIPT_NOT_CHECKPOINT')
        fake=SimpleNamespace(save=save)
        guard=SimpleNamespace(check=lambda stage:None)
        with tempfile.TemporaryDirectory() as folder,patch.object(study,'optimizers',return_value=(opt,)),\
             patch.object(study,'sources',return_value=common['source_code_sha256']),\
             patch.object(study,'checkpoint_path',return_value=Path(folder)/'synthetic.pt'),\
             patch.object(study,'ROOT',Path(folder)),patch.object(original,'batches',side_effect=batches),\
             patch.object(updater,'one_update',side_effect=update),patch.object(updater,'rng_identity',return_value=rng),\
             patch.object(ui,'state_fingerprint',return_value=common['parent_core_sha256']),redirect_stdout(io.StringIO()):
            run_context=study.study_context(context.profile.name,root=Path(folder))
            report=study.do_train(fake,Model(),p,rows,arm,cal,guard,None,cost=cost,phase=phase,
                observer=observed.append,expected_rng={'other':True} if bad_rng else rng,
                expected_optimizer_groups=[{'different':True}] if bad_optimizer else None,context=run_context)
        return report,calls,saved,observed

    def test_cost_reuses_existing_updater_two_times_ce_only_with_no_checkpoint(self):
        report,calls,saved,observed=self.run_mock_train(cost=True)
        self.assertEqual(calls,[(0,'cost'),(1,'cost')]);self.assertEqual(saved,[])
        self.assertEqual(report['checkpoint_writes'],0);self.assertEqual(report['updates'],2)
        self.assertTrue(all(row['kl'] is None and row['objective']==row['loss'] for row in report['history']))
        self.assertEqual([value['update'] for value in observed],[0,1])

    def test_four_epochs_32_updates_and_weight_only_identity_from_same_updater(self):
        report,calls,saved,observed=self.run_mock_train(cost=False,arm='alm')
        self.assertEqual(len(calls),32);self.assertEqual([v[0] for v in calls],list(range(32)))
        self.assertEqual(len(saved),1);self.assertEqual(saved[0]['step'],32)
        self.assertEqual(saved[0]['experiment'],report['checkpoint_experiment'])
        self.assertEqual(saved[0]['experiment']['study_identity_sha256'],saved[0]['experiment']['phase_identity']['study_identity_sha256'])
        self.assertEqual(report['actual_x_tokens'],4*1024*3)
        self.assertEqual(report['history'][0]['objective'],2.+.5*.5)
        self.assertEqual([value['epoch'] for value in observed],[i//8 for i in range(32)])
        self.assertEqual([value['update'] for value in observed],list(range(32)))

    def test_dirty_initial_gradients_or_different_initial_rng_reject_before_first_update(self):
        for flags in (dict(dirty_grad=True),dict(bad_rng=True),dict(bad_optimizer=True)):
            with self.subTest(flags=flags),self.assertRaises(ValueError):self.run_mock_train(cost=True,**flags)

    def test_new_profiles_reuse_same_updater_for_two_cost_and_32_training_steps(self):
        for name in ('float_v2','ternary_v1'):
            for arm in ('ce','alm'):
                context=study.study_context(name)
                for cost in (True,False):
                    with self.subTest(name=name,arm=arm,cost=cost):
                        report,calls,saved,_=self.run_mock_train(cost=cost,arm=arm,context=context)
                        self.assertEqual(len(calls),2 if cost else 32)
                        self.assertEqual(report['study_profile'],context.profile.metadata())
                        self.assertEqual(report['weight'],.5 if arm=='alm' else 0.)
                        self.assertEqual(report['quantization_route']['mode'],context.profile.weight_route)
                        if not cost:
                            self.assertEqual(saved[0]['quantization_route'],report['quantization_route'])
                            self.assertEqual(saved[0]['experiment']['study_profile_sha256'],study.sha(context.profile.metadata()))


if __name__=='__main__':unittest.main()
