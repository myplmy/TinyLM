#!/usr/bin/env python3
"""새 native 학습 부모의 격리 CPU 회귀. 모델·GPU·원 대량 캐시는 실행하지 않는다."""
from __future__ import annotations
import ast
import base64
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout
from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import signal
import select
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_native_format_training as d


def put(root,name,value):
    target = root/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(d.canonical(value))
    return dict(path=name,sha256=d.pair.file_sha(target))


def groups(kind="Muon"):
    return [
        dict(optimizer="AdamW",group=0,lr=.001,weight_decay=.0001,parameters=1,
             names_sha256="A"*64,scale_mode=None,runtime_lr=.0001,runtime_weight_decay=.0001,lr_multiplier=10.),
        dict(optimizer=kind,group=0,lr=.004,weight_decay=0.,parameters=2,
             names_sha256="B"*64,scale_mode="rms",runtime_lr=.0004,runtime_weight_decay=0.,lr_multiplier=10.)]


class Budget:
    def __init__(self):
        self.started=time.monotonic(); self.reserve=.1; self.end=self.started+100
    def check(self,stage):
        if self.remaining() <= 0:
            raise TimeoutError(stage)
    def remaining(self):
        return self.end-time.monotonic()


class Sink:
    def __init__(self): self.events=[]
    def append(self,row): self.events.append(row)


class Adapter:
    synthetic=True
    def __init__(self, *, gradient=2.,targets=8192):
        self.route=SimpleNamespace(assert_active=lambda:None)
        self.gradient,self.targets=gradient,targets
        self.steps,self.micros=0,0
        self.policy=None
    def begin(self,policy): self.policy=policy
    def backward(self,chosen,denominator):
        assert len(chosen)==8 and denominator==d.TARGETS
        self.micros+=1
        return 8192.,self.targets,8192
    def finish(self): self.steps+=1; return self.gradient
    def lrs(self): return [[.001*self.policy["lr_factor"]],[.004*self.policy["lr_factor"]]]


class Fixture:
    def __init__(self,root):
        self.root,self.stack=root,ExitStack()
        self.stack.enter_context(patch.object(d,"ROOT",root))
        self.stack.enter_context(patch.object(d.native,"VAL",root/"data_cache/val.bin"))
        self.stack.enter_context(patch.object(d.native,"PARENT",root/"runs/ckpt/geometry.pt"))
        self.stack.enter_context(patch.object(d.pair,"MIN_IDS",16))
        self.stack.enter_context(patch.object(d,"source_identity",return_value=dict(sha256="A"*64,files={})))
        self.stack.enter_context(patch.object(d.pair,"source_identity",return_value=dict(sha256="B"*64,files={})))
        self.token=put(root,"data_cache/tokenizer.json",{})
        self.val=put(root,"data_cache/val.bin",[])
        parent=root/"runs/ckpt/geometry.pt"
        parent.parent.mkdir(parents=True); parent.write_bytes(b"geometry-only-fixture")
        self.holds=put(root,"data_cache/holds.json",dict(schema="P106B_NATIVE_FORMAT_HOLDS_V1",
            source_sha256=d.pair.SOURCE_SHA,holds=[]))
        self.policy=dict(schema=d.pair.POLICY,approved_train_reuse=True,scope="TRAIN_FORMAT_COMPARISON_ONLY",
            full_semantic_review=False,review_queue_policy="PRESERVE_NOT_AUTOMATIC_HOLD",
            reserved_action="EXCLUDE_BOTH",minimum_ids_per_arm=16,
            tokenizer=dict(path=self.token["path"],sha256=d.native.TOKENIZER_SHA),
            validation=dict(path=self.val["path"],sha256=d.native.VAL_SHA),holds=self.holds)
        self.policy_ref=put(root,"data_cache/pair_policy.json",self.policy)
        cache=root/"data_cache/pair"
        cache.mkdir()
        for name in ("original","format"):
            (cache/(name+".bin")).write_bytes(b"\3\0"*31+b"\2\0")
        self.complete=dict(schema=d.pair.SCHEMA,synthetic=False,
            training_admission="CPU_CACHE_PREPARED_NOT_TRAIN_OR_QUALITY_PASS",
            unit="EOS_CACHE_SEGMENTS_NOT_ORIGINAL_URL_DOCUMENTS",policy_sha256=self.policy_ref["sha256"],
            source_identity=dict(sha256="B"*64),kept_documents=1,holds={},
            ledger=dict(lineage=dict(source_sha256=d.pair.SOURCE_SHA,policy_sha256=self.policy_ref["sha256"],
                source_code_sha256="B"*64,same_roster_and_order=True)),
            arms={a:dict(tokens=32) for a in ("original","format")},
            output_readback=dict(kept_documents=1,tokens=dict(original=32,format=32)))
        self.complete_ref=put(root,"data_cache/pair/complete.json",self.complete)
        self.profile=dict(schema=d.PROFILE,recipe=d.RECIPE,
            arms=[dict(id="raw_muon",corpus="original",optimizer="muon",required=True),
                  dict(id="fmt_muon",corpus="format",optimizer="muon",required=True),
                  dict(id="fmt_normuon",corpus="format",optimizer="normuon",required=False)],
            normuon=dict(beta2=.95,eps=1e-10,implementation="TINYLM_ADAPTED_POST_NS_ROW_EMA"),
            train_deadline=d.TRAIN_END.isoformat(),final_deadline=d.END.isoformat(),
            cleanup_reserve_sec=120,evaluation_reserve_sec=3600,minimum_pair_training_sec=15000,
            entry_free_mib=13000,validation=self.policy["validation"],tokenizer=self.policy["tokenizer"],
            geometry_parent=dict(path="runs/ckpt/geometry.pt",sha256=d.native.PARENT_SHA,
                use="CONFIG_AND_TOKEN_METADATA_ONLY"),pair_complete=self.complete_ref,pair_policy=self.policy_ref)
        self.args=SimpleNamespace(mode="cost",arm="raw_muon",budget=None,budget_sha256=None)
        self.refresh()
    def refresh(self):
        self.args.profile="data_cache/profile.json"
        self.args.profile_sha256=put(self.root,self.args.profile,self.profile)["sha256"]
        self.args.f4="data_cache/f4.json"
        self.args.f4_sha256=put(self.root,self.args.f4,dict(schema="P106B_NATIVE_FORMAT_F4_V1",
            root_approved=True,source_sha256="A"*64,profile_sha256=self.args.profile_sha256,
            allowed_modes=["cost","train"]))["sha256"]
    def close(self): self.stack.close()


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="native_training_",dir="/tmp")
        self.root=Path(self.tmp.name); self.fixture=Fixture(self.root)
    def tearDown(self):
        self.fixture.close(); self.tmp.cleanup()
    def test_exact_fixture_and_no_runtime(self):
        with patch.object(d.native,"modules",side_effect=AssertionError("모델 금지")):
            state=d.metadata(self.fixture.args)
        self.assertEqual(state["complete"]["output_readback"]["tokens"],dict(original=32,format=32))
    def test_missing_profile_is_hold(self):
        self.fixture.args.profile="data_cache/absent.json"
        with self.assertRaises(d.Hold): d.metadata(self.fixture.args)
    def test_large_checkpoint_does_not_inherit_text_fsize_limit(self):
        self.fixture.args.mode="train"
        with patch.object(d.resource,"getrlimit",return_value=(20_000_000,20_000_000)),self.assertRaises(d.Hold):
            d.metadata(self.fixture.args)
    def test_same_length_source_pin_change_rejected(self):
        target=self.root/self.fixture.args.profile
        data=target.read_bytes()
        changed=data.replace(b'"micro":8',b'"micro":9')
        self.assertEqual(len(data),len(changed)); target.write_bytes(changed)
        with self.assertRaisesRegex(ValueError,"SHA"): d.metadata(self.fixture.args)
    def test_recipe_and_default_normuon_are_rejected(self):
        self.fixture.profile["normuon"]["implementation"]="OFFICIAL_DEFAULT"
        self.fixture.refresh()
        with self.assertRaises(ValueError): d.metadata(self.fixture.args)
    def test_profile_order_preserved(self):
        self.fixture.profile["arms"][:2]=self.fixture.profile["arms"][:2][::-1]
        self.fixture.refresh()
        self.assertEqual(d.metadata(self.fixture.args)["profile"]["arms"],self.fixture.profile["arms"])
    def test_root_can_require_same_format_two_optimizers(self):
        self.fixture.profile["arms"][0]["required"]=False
        self.fixture.profile["arms"][2]["required"]=True
        self.fixture.refresh()
        state=d.metadata(self.fixture.args)
        self.assertEqual([(a["corpus"],a["optimizer"]) for a in state["profile"]["arms"] if a["required"]],
            [("format","muon"),("format","normuon")])
    def test_missing_token_lineage_is_hold(self):
        (self.root/self.fixture.token["path"]).unlink()
        with self.assertRaises(d.Hold): d.metadata(self.fixture.args)
    def test_partial_or_undersized_cache_rejected(self):
        (self.root/"data_cache/pair/failed.json").write_bytes(b"{}")
        with self.assertRaises(ValueError): d.metadata(self.fixture.args)
    def test_bin_size_and_shared_roster_rejected(self):
        (self.root/"data_cache/pair/original.bin").write_bytes(b"tiny")
        with self.assertRaises(ValueError): d.metadata(self.fixture.args)
    def test_pool_below_twice_full_target_is_rejected(self):
        self.fixture.complete["arms"]["original"]["tokens"]=15
        self.fixture.complete["output_readback"]["tokens"]["original"]=15
        (self.root/"data_cache/pair/original.bin").write_bytes(b"\3\0"*14+b"\2\0")
        self.fixture.profile["pair_complete"]=put(self.root,"data_cache/pair/complete.json",self.fixture.complete)
        self.fixture.refresh()
        with self.assertRaises(ValueError): d.metadata(self.fixture.args)
    def test_unresolved_hold_rejected(self):
        holds=dict(schema="P106B_NATIVE_FORMAT_HOLDS_V1",source_sha256=d.pair.SOURCE_SHA,
            holds=[dict(id="hold0",eos_segment_index=0,source_sha256=d.pair.SOURCE_SHA)])
        self.fixture.policy["holds"]=put(self.root,"data_cache/holds.json",holds)
        self.fixture.policy_ref=put(self.root,"data_cache/pair_policy.json",self.fixture.policy)
        self.fixture.profile["pair_policy"]=self.fixture.policy_ref
        self.fixture.complete["policy_sha256"]=self.fixture.policy_ref["sha256"]
        self.fixture.complete["ledger"]["lineage"]["policy_sha256"]=self.fixture.policy_ref["sha256"]
        self.fixture.profile["pair_complete"]=put(self.root,"data_cache/pair/complete.json",self.fixture.complete)
        self.fixture.refresh()
        with self.assertRaisesRegex(ValueError,"HOLD"): d.metadata(self.fixture.args)
    def test_source_metadata_restoration(self):
        state=d.metadata(self.fixture.args)
        d.immutable_metadata(self.fixture.args,state,Budget())
        state["profile_sha256"]="F"*64
        with self.assertRaises(ValueError): d.immutable_metadata(self.fixture.args,state,Budget())
    def test_path_protection(self):
        for name in ("../escape","datasets/TinyDataset/train.bin",".claude/x","ai_dev_tool/00.md"):
            with self.subTest(name=name),self.assertRaises(ValueError): d.path(name)


class OptimizerTests(unittest.TestCase):
    def make(self):
        self.parameter=object()
        adam=SimpleNamespace(state={},param_groups=[dict(params=[object()],lr=.001,weight_decay=.0001)])
        defaults=dict(lr=.004,momentum=.95,nesterov=True,ns_steps=5,weight_decay=0.,scale_mode="rms")
        muon=SimpleNamespace(state={},defaults=defaults,scale_mode="rms",
            param_groups=[dict(defaults,params=[self.parameter])])
        self.original=(adam,muon)
        return lambda model,endpoint:(self.original,groups())
    def test_muon_is_original_object(self):
        opts,receipt,kind=d.optimizer_pair(None,dict(optimizer="muon"),{},make=self.make())
        self.assertIs(opts,self.original); self.assertEqual(kind["kind"],"ORIGINAL_MUON")
    def test_normuon_preserves_original_group_and_adam(self):
        make=self.make()
        class Replacement:
            def __init__(self,params,**kwargs):
                self.state={}; self.scale_mode=kwargs["scale_mode"]
                self.param_groups=[dict(group,beta2=kwargs["beta2"],eps=kwargs["eps"]) for group in params]
        opts,receipt,kind=d.optimizer_pair(None,dict(optimizer="normuon"),
            dict(normuon=dict(beta2=.95,eps=1e-10)),make=make,constructor=Replacement)
        self.assertIs(opts[0],self.original[0]); self.assertIs(opts[1].param_groups[0]["params"][0],self.parameter)
        self.assertEqual(opts[1].param_groups[0]["scale_mode"],"rms")
        self.assertEqual(receipt[1]["optimizer"],"NorMuon")
        self.assertTrue(kind["none_gradient_policy"].endswith("SKIP"))
    def test_group_or_fresh_state_change_rejected(self):
        make=self.make(); self.original[1].state["old"]=1
        with self.assertRaises(ValueError): d.optimizer_pair(None,dict(optimizer="muon"),{},make=make)
    def test_normuon_cannot_change_rms_or_weight_decay(self):
        make=self.make()
        class Bad:
            def __init__(self,params,**kwargs):
                self.state={}; self.scale_mode="rms"
                self.param_groups=[dict(params[0],weight_decay=.1,beta2=.95,eps=1e-10)]
        with self.assertRaises(ValueError):
            d.optimizer_pair(None,dict(optimizer="normuon"),dict(normuon=dict(beta2=.95,eps=1e-10)),
                make=make,constructor=Bad)


class LoopTests(unittest.TestCase):
    def run_loop(self,cost=True,adapter=None,offsets=None,budget=None):
        adapter=adapter or Adapter(); sink=Sink()
        offsets=list(range(d.UPDATES*128)) if offsets is None else offsets
        with redirect_stdout(io.StringIO()),patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()-100):
            result=d.update_loop(adapter,offsets,sink,budget or Budget(),cost=cost)
        return result,sink,adapter
    def test_cost_exact_eight_updates_no_extra_target(self):
        value,sink,adapter=self.run_loop()
        self.assertEqual((value["updates"],value["totals"]["targets"],adapter.micros),(8,1048576,128))
        self.assertEqual(sink.events[-1]["offsets"][-1],1023)
    def test_full2289_targets_offsets_schedule(self):
        value,sink,adapter=self.run_loop(False)
        self.assertEqual(value["totals"],dict(targets=300023808,x_tokens=300023808))
        self.assertEqual((adapter.steps,adapter.micros),(2289,36624))
        self.assertEqual(sink.events[-1]["schedule"],d.native.schedule(2288,updates=2289))
        self.assertEqual(sink.events[-1]["offsets"][-1],2289*128-1)
    def test_missing_offsets_or_target_rejected(self):
        for adapter,offsets in ((Adapter(),[0]*127),(Adapter(targets=1),None)):
            with self.subTest(target=adapter.targets),self.assertRaises(ValueError):
                self.run_loop(adapter=adapter,offsets=offsets)
    def test_nonfinite_gradient_and_numerator_rejected(self):
        for value in (math.nan,math.inf,-1.):
            with self.subTest(value=value),self.assertRaises(ValueError): self.run_loop(adapter=Adapter(gradient=value))
        adapter=Adapter(); adapter.backward=lambda *_:(math.nan,8192,8192)
        with self.assertRaises(ValueError): self.run_loop(adapter=adapter)
    def test_timeout_before_optimizer_update(self):
        budget=Budget(); budget.end=0
        adapter=Adapter()
        with self.assertRaises(TimeoutError): self.run_loop(adapter=adapter,budget=budget)
        self.assertEqual(adapter.steps,0)
    def test_train_deadline_before_micro(self):
        with patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()),self.assertRaises(TimeoutError):
            d.update_loop(Adapter(),[0]*128,Sink(),Budget(),cost=False)
    def test_native_adapter_reuses_micro_and_rejects_gradient_before_step(self):
        first,second=SimpleNamespace(step=lambda:None),SimpleNamespace(step=lambda:None)
        first.step=unittest.mock.Mock(); second.step=unittest.mock.Mock()
        for opt in (first,second):
            opt.zero_grad=unittest.mock.Mock()
            opt.param_groups=[dict(lr=.004)]
        model=SimpleNamespace(set_anneal=unittest.mock.Mock(),parameters=lambda:[])
        torch=SimpleNamespace(nn=SimpleNamespace(utils=SimpleNamespace(clip_grad_norm_=lambda *_:math.nan)),
            isfinite=lambda _:False)
        adapter=d.NativeAdapter(torch,model,None,[],(first,second),None)
        adapter.begin(dict(lr_factor=.5,anneal=.75))
        self.assertEqual(first.param_groups[0]["lr"],.002)
        first.zero_grad.assert_called_once_with(set_to_none=True)
        with self.assertRaises(ValueError): adapter.finish()
        first.step.assert_not_called(); second.step.assert_not_called()
        with patch.object(d.native,"native_records",return_value=["native-records"]) as records,\
                patch.object(d.native,"backward_micro",return_value=(1.,8192,8192)) as backward:
            self.assertEqual(adapter.backward([3]*8,d.TARGETS),(1.,8192,8192))
            records.assert_called_once_with([], [3]*8)
            self.assertEqual(backward.call_args.args[3],d.TARGETS)


class ExecutionBoundaryTests(unittest.TestCase):
    def test_partial_update_cannot_evaluate_or_save_checkpoint(self):
        @dataclass
        class Config:
            grad_checkpoint: bool=True
        @contextmanager
        def routed(*args):
            yield torch,model,Config(),None,d.CORE,SimpleNamespace(assert_active=lambda:None)
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary,ExitStack() as stack:
            root=Path(temporary)
            output=root/"evidence"; output.mkdir()
            args=SimpleNamespace(mode="train",arm="raw",output=output)
            state=dict(source_identity=dict(sha256="A"),profile_sha256="B",complete_sha256="C",
                cache="data_cache/pair",profile=dict(arms=[dict(id="raw",corpus="original",optimizer="muon")],
                    geometry_parent={}))
            closed=unittest.mock.Mock()
            class Tokens(list):
                pass
            tokens=Tokens([0]*2048); tokens._mmap=SimpleNamespace(close=closed)
            model=SimpleNamespace(train=lambda:None,clear_quant=lambda:None,set_anneal=lambda _:None)
            torch=SimpleNamespace(compile=lambda *a,**k:None,
                cuda=SimpleNamespace(reset_peak_memory_stats=lambda:None,synchronize=lambda:None,
                    max_memory_allocated=lambda:0,max_memory_reserved=lambda:0),save=unittest.mock.Mock())
            opts=(SimpleNamespace(param_groups=[dict(lr=.001,params=[])]),
                  SimpleNamespace(param_groups=[dict(lr=.004,params=[])]))
            contract=[[dict(lr=.001)],[dict(lr=.004)]]
            cost=dict(offsets={},actual_optimizer_groups=groups(),optimizer_contract=contract)
            stack.enter_context(patch.object(d,"ROOT",root))
            stack.enter_context(patch.object(d,"full_cache"))
            stack.enter_context(patch.object(d,"fresh_admission",return_value={}))
            stack.enter_context(patch.object(d,"budget_admission",return_value=dict(current_cost=cost)))
            stack.enter_context(patch.dict(sys.modules,{"numpy":SimpleNamespace(memmap=lambda *a,**k:tokens)}))
            stack.enter_context(patch.object(d.native,"make_offsets",return_value=([0]*128,{})))
            stack.enter_context(patch.object(d.native,"modules",return_value=(
                SimpleNamespace(state_fingerprint=lambda _:d.CORE),None,None)))
            stack.enter_context(patch.object(d.native,"routed_runtime",side_effect=routed))
            stack.enter_context(patch.object(d,"optimizer_pair",return_value=(opts,groups(),{})))
            stack.enter_context(patch.object(d,"MemorySamples",return_value=nullcontext()))
            stack.enter_context(patch.object(d,"update_loop",return_value=dict(updates=2288,
                totals=dict(targets=2288*d.TARGETS,x_tokens=2288*d.TARGETS))))
            evaluate=stack.enter_context(patch.object(d.native,"native_probe",side_effect=AssertionError("평가 금지")))
            with self.assertRaisesRegex(ValueError,"완주"):
                d.execute_training(args,state,Budget())
            evaluate.assert_not_called(); torch.save.assert_not_called(); closed.assert_called_once()
            self.assertFalse((root/"runs/ckpt").exists())
    def test_fresh_gpu_admission_uses_root_budget_only(self):
        from scripts import diag_p106_vram_sample as sample
        from scripts import diag_p106_full_coload_accum as apps
        with patch.object(sample,"read_memory",return_value=(100,12999)),\
                patch.object(apps,"_compute_apps",return_value=[]),self.assertRaises(d.Hold):
            d.fresh_admission(dict(entry_free_mib=13000),Budget())
        with patch.object(sample,"read_memory",return_value=(100,13000)),\
                patch.object(apps,"_compute_apps",return_value=["foreign"]),self.assertRaises(d.Hold):
            d.fresh_admission(dict(entry_free_mib=13000),Budget())
        with patch.object(sample,"read_memory",return_value=(math.nan,13000)),\
                patch.object(apps,"_compute_apps",return_value=[]),self.assertRaises(ValueError):
            d.fresh_admission(dict(entry_free_mib=13000),Budget())
    def test_memory_cleanup_keeps_original_exception(self):
        memory=d.MemorySamples()
        memory.thread=SimpleNamespace(join=lambda **_:None,is_alive=lambda:True)
        primary=ValueError("원래 예외")
        memory.__exit__(ValueError,primary,None)
        self.assertEqual(primary.args,("원래 예외",))
        self.assertEqual(primary.supported_cleanup_errors[0]["type"],"OSError")
    def test_file_cleanup_keeps_original_and_attempts_all_closes(self):
        primary=ValueError("원래 검산 오류"); attempted=[]
        def bad():
            attempted.append("first")
            raise OSError("닫기 오류")
        d.close_preserving(primary,[("부분 shard",bad),("token map",lambda:attempted.append("second"))])
        self.assertEqual(primary.args,("원래 검산 오류",))
        self.assertEqual(attempted,["first","second"])
        self.assertEqual(primary.supported_cleanup_errors[0]["type"],"OSError")


def cost_receipt():
    return dict(status="COST8_COMPLETE",updates=8,synthetic=False,checkpoint=None,native32=None,
        step_seconds=[5.]+[1.]*7,pre_training_seconds=10.,whole_worker_seconds=30.,
        late=dict(seconds=.1,optimizer_updates=0,micro_batches=1,targets=8192,finite=True,
                  core_before="C"*64,core_after="C"*64),cache_audit=dict(seconds=.1))


class CostTests(unittest.TestCase):
    def test_cold_preparation_late_and_actual_exit_wall_all_charged(self):
        value=d.forecasts(cost_receipt(),35.)
        self.assertAlmostEqual(value,10+5+1.6*2288*1.35+13)
    def test_partial_and_nonfinite_cost_rejected(self):
        for key,value in (("updates",7),("synthetic",True),("pre_training_seconds",math.nan)):
            cost=cost_receipt(); cost[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): d.forecasts(cost,35.)
    def budget_state(self):
        arms=[dict(id="raw",corpus="original",optimizer="muon",required=True),
              dict(id="fmt",corpus="format",optimizer="muon",required=True),
              dict(id="nor",corpus="format",optimizer="normuon",required=False)]
        state=dict(source_identity=dict(sha256="A"),profile_sha256="B",f4_sha256="C",complete_sha256="D",
            profile=dict(arms=arms,minimum_pair_training_sec=15000,evaluation_reserve_sec=3600))
        approval=dict(schema="P106B_NATIVE_FORMAT_COST_ADMISSION_V1",root_approved=True,
            source_sha256="A",profile_sha256="B",f4_sha256="C",pair_complete_sha256="D",
            admitted_arms=["raw","fmt"],cost_reports={a["id"]:dict(name=a["id"]) for a in arms},
            conservative_seconds_by_arm={a["id"]:6000. for a in arms},completed_train_reports={},
            unmeasured_post_training_reserve_sec_per_arm=300)
        def closed(spec,state,name,mode):
            arm=d.arm_for(state,name); value=cost_receipt()
            value.update(arm=name,corpus=arm["corpus"],optimizer=arm["optimizer"],
                scratch_core_sha256=d.CORE,offsets=dict(offsets_bytes_sha256="same-format"),
                actual_optimizer_groups=groups("NorMuon" if arm["optimizer"] == "normuon" else "Muon"),
                optimizer_contract=[[dict(lr=.001,weight_decay=.0001,betas=[.9,.95],eps=1e-8)],
                    [dict(lr=.004,weight_decay=0.,momentum=.95,nesterov=True,ns_steps=5,scale_mode="rms",
                        **(dict(beta2=.95,eps=1e-10) if arm["optimizer"] == "normuon" else {}))]])
            return dict(worker=value,root_actual_parent_wall_seconds=35.)
        return state,approval,closed
    def test_pair_forecast_admission_and_insufficient_window(self):
        state,approval,closed=self.budget_state()
        args=SimpleNamespace(budget="budget.json",budget_sha256="X",arm="raw")
        with patch.object(d,"read",return_value=(approval,"X")),patch.object(d,"read_closed",side_effect=closed):
            with patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()-16000):
                self.assertEqual(d.budget_admission(args,state)["pending_forecast_seconds"],12000.)
            with patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()-14999),self.assertRaises(d.Hold):
                d.budget_admission(args,state)
    def test_optional_arm_waits_required_and_already_done_not_rerun(self):
        state,approval,closed=self.budget_state(); approval["admitted_arms"].append("nor")
        args=SimpleNamespace(budget="budget.json",budget_sha256="X",arm="nor")
        with patch.object(d,"read",return_value=(approval,"X")),patch.object(d,"read_closed",side_effect=closed),\
                patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()-30000):
            with self.assertRaises(d.Hold): d.budget_admission(args,state)
            approval["completed_train_reports"]={name:{} for name in ("raw","fmt")}
            self.assertEqual(d.budget_admission(args,state)["completed_arms"],["raw","fmt"])
            args.arm="raw"
            with self.assertRaises(d.Hold): d.budget_admission(args,state)
    def test_root_cannot_undercut_actual_cost(self):
        state,approval,closed=self.budget_state(); approval["conservative_seconds_by_arm"]["raw"]=1.
        with patch.object(d,"read",return_value=(approval,"X")),patch.object(d,"read_closed",side_effect=closed),\
                self.assertRaises(ValueError):
            d.budget_admission(SimpleNamespace(budget="b",budget_sha256="s",arm="raw"),state)
    def test_required_normuon_needs_no_raw_run_and_same_format_contract(self):
        state,approval,closed=self.budget_state()
        state["profile"]["arms"][0]["required"]=False
        state["profile"]["arms"][2]["required"]=True
        approval["admitted_arms"]=["fmt","nor"]
        args=SimpleNamespace(budget="b",budget_sha256="s",arm="nor")
        with patch.object(d,"read",return_value=(approval,"s")),\
                patch.object(d,"read_closed",side_effect=closed),\
                patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()-16000):
            value=d.budget_admission(args,state)
            self.assertEqual(value["admitted_arms"],["fmt","nor"])
            self.assertEqual(value["completed_arms"],[])
        def changed(spec,state,name,mode):
            value=closed(spec,state,name,mode)
            if name == "nor": value["worker"]["optimizer_contract"][0][0]["eps"]=1e-7
            return value
        with patch.object(d,"read",return_value=(approval,"s")),patch.object(d,"read_closed",side_effect=changed),\
                self.assertRaises(ValueError):
            d.budget_admission(args,state)


class ClosureTests(unittest.TestCase):
    def create(self,root):
        state=dict(source_identity=dict(sha256="A"),profile_sha256="B",f4_sha256="C",complete_sha256="D",
            complete=dict(arms=dict(original=dict(tokens=d.pair.MIN_IDS))),
            profile=dict(arms=[dict(id="raw",corpus="original",optimizer="muon",required=True)]))
        child=cost_receipt()
        route=dict(mode="ternary",metadata=dict(scope="TLINEAR_WEIGHTS_ONLY"),tlinear_instances=1,
            owned_tlinear_instances=1,refreshed_tlinear_instances=1)
        child.update(schema=d.SCHEMA,mode="cost",arm="raw",corpus="original",optimizer="muon",
            source_sha256="A",profile_sha256="B",pair_complete_sha256="D",scratch_core_sha256=d.CORE,
            original_weights_copied=False,totals=dict(targets=8*d.TARGETS,x_tokens=8*d.TARGETS),
            actual_optimizer_groups=groups(),route=route,quantization_route=route["metadata"],
            memory=dict(samples=1,sampled_global_peak_mib=100),
            offsets=dict(pool_tokens=d.pair.MIN_IDS,crops=d.UPDATES*128,draw_tokens=d.TOTAL,
                twice_draw=2*d.TOTAL,seed=1337,window_tokens=1025,offsets_bytes_sha256="E"*64))
        child["cache_audit"].update(quality_forwards=0,optimizer_updates=0,finite=True,
            core_before="F"*64,core_after="F"*64,route=route)
        writer=d.ShardWriter(root/"updates","updates",limit=19_999_999)
        for index in range(8):
            policy=d.native.schedule(index,updates=d.UPDATES); offsets=list(range(index*128,(index+1)*128))
            writer.append(dict(update=index+1,targets=d.TARGETS,x_tokens=d.TARGETS,synthetic=False,
                schedule=policy,actual_lrs=d.native.actual_lrs(groups(),policy["lr_factor"]),
                gradient_norm=.5,ce=1.,clipped=False,step_seconds=child["step_seconds"][index],
                offsets=offsets,offsets_sha256=d.sha(offsets)))
        child["event_manifest"]=writer.close(lineage={})
        worker=put(root,"worker.json",child)
        observed=dict(actual_child_exit=0,launch_state="STARTED",child_group_quiescent=True,stdout_complete=True,
            subreaper_restored=True,forced_cleanup=False,original_error=None,cleanup_errors=[])
        report=dict(schema=d.SCHEMA,mode="cost",arm="raw",returncode=0,source_sha256="A",profile_sha256="B",
            f4_sha256="C",pair_complete_sha256="D",supervision=observed,worker=child,
            worker_sha256=worker["sha256"],whole_parent_seconds=34.)
        put(root,"report.json",report)
        d.supervisor.append_terminal(root,dict(event="OBSERVATION",returncode=0))
        spec=dict(path="report.json",sha256=d.pair.file_sha(root/"report.json"),actual_supervisor_exit=0,
            actual_parent_wall_sec=35.,terminal_sha256=d.pair.file_sha(root/"terminal.jsonl"))
        return state,child,spec
    def test_actual_ledger_and_parent_terminal_closure(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary,patch.object(d.native,"modules",
                side_effect=AssertionError("모델 금지")):
            root=Path(temporary); state,child,spec=self.create(root)
            with patch.object(d,"ROOT",root):
                self.assertEqual(d.read_closed(spec,state,"raw","cost")["root_actual_parent_wall_seconds"],35.)
                d.supervisor.append_terminal(root,dict(event="TERMINAL_VETO",returncode=9))
                with self.assertRaises(ValueError): d.read_closed(spec,state,"raw","cost")
                spec["terminal_sha256"]=d.pair.file_sha(root/"terminal.jsonl")
                with self.assertRaisesRegex(ValueError,"종결"): d.read_closed(spec,state,"raw","cost")
    def test_partial_or_changed_worker_never_reopens_main(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); state,child,spec=self.create(root)
            with patch.object(d,"ROOT",root):
                changed=(root/"worker.json").read_bytes().replace(b'"updates":8',b'"updates":7')
                (root/"worker.json").write_bytes(changed)
                with self.assertRaises(ValueError): d.read_closed(spec,state,"raw","cost")
                spec["actual_supervisor_exit"]=False
                with self.assertRaises(ValueError): d.read_closed(spec,state,"raw","cost")
    def test_checkpoint_experiment_binds_full_targets_and_corpus(self):
        child=dict(updates=d.UPDATES,totals=dict(targets=d.TOTAL),scratch_core_sha256=d.CORE,
            arm="fmt_nor",corpus="format",optimizer="normuon",source_sha256="A",
            profile_sha256="B",pair_complete_sha256="C",final_core_sha256="D")
        value=d.checkpoint_experiment(child)
        self.assertEqual(value["targets"],300023808); self.assertEqual(value["core_sha256"],"D")
        self.assertFalse(value["original_training_weights_copied"])
        child["updates"]=2288
        with self.assertRaises(ValueError): d.checkpoint_experiment(child)


class OwnershipTests(unittest.TestCase):
    def test_pgid_reuse_or_foreign_exe_never_authorizes_signal(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); (root/"200").mkdir()
            (root/"200/environ").write_bytes(b"OTHER=1")
            saved=dict(pid=100,pgid=100,session=100,starttime=10)
            row=dict(pid=200,pgid=100,session=100,starttime=20,ppid=1,state="S")
            executable=str(Path(sys.executable).resolve())
            with patch.object(d.os,"readlink",return_value="/foreign"),\
                    patch.object(Path,"read_bytes",side_effect=AssertionError("타 환경 읽기 금지")):
                self.assertEqual(d.owned_members(saved,{},[executable],"secret",proc_root=root,stat=lambda _:row),[])
            with patch.object(d.os,"readlink",return_value=executable):
                self.assertEqual(d.owned_members(saved,{},[executable],"secret",proc_root=root,stat=lambda _:row),[])
    def test_known_pid_starttime_change_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); (root/"200").mkdir()
            saved=dict(pid=100,pgid=100,session=100,starttime=10)
            row=dict(pid=200,pgid=100,session=100,starttime=20,ppid=1,state="S")
            with self.assertRaises(ValueError):
                d.owned_members(saved,{200:dict(starttime=19)},[sys.executable],"secret",proc_root=root,stat=lambda _:row)
    def test_actual_child_exit_0_8_9_and_lossless_stdout(self):
        for code in (0,8,9):
            with self.subTest(code=code),tempfile.TemporaryDirectory(dir="/tmp") as temporary:
                directory=Path(temporary)
                command=[str(Path(sys.executable).resolve()),"-I","-B","-c",
                    "import os,time; os.write(1,b'raw\\xff\\x00'); time.sleep(.1); raise SystemExit("+str(code)+")"]
                budget=d.supervisor.Budget(10,time.time()+10,started=time.monotonic(),reserve=.5)
                result=d.supervise(command,directory,budget)
                self.assertEqual(result["actual_child_exit"],code)
                self.assertTrue(result["child_group_quiescent"]); self.assertFalse(result["forced_cleanup"])
                self.assertEqual(d.supervision_ok(result),code==0)
                actual=b"".join(base64.b64decode(row["bytes"]) for row in d.rows(directory/"stdout",result["stdout_manifest"]))
                self.assertEqual(actual,b"raw\xff\x00")
    def test_timeout_term_ignore_requires_kill_and_is_not_success(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            budget=d.supervisor.Budget(7,time.time()+7,started=time.monotonic(),reserve=6.)
            command=[str(Path(sys.executable).resolve()),"-I","-B","-c",
                "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); signal.signal(signal.SIGINT,signal.SIG_IGN); time.sleep(20)"]
            original_stop=d.smoke.stop_process_group
            def stopped(*args):
                return [*original_stop(*args),"MASK_RESTORE_ERROR:fixture"]
            with patch.object(d.smoke,"stop_process_group",side_effect=stopped):
                result=d.supervise(command,Path(temporary),budget)
            self.assertEqual(result["actual_child_exit"],-signal.SIGKILL)
            self.assertEqual(result["original_error"]["type"],"TimeoutError")
            self.assertTrue(result["forced_cleanup"]); self.assertTrue(result["child_group_quiescent"])
            self.assertFalse(d.supervision_ok(result))
            self.assertTrue(any(error["type"]=="CleanupAuditError" for error in result["cleanup_errors"]))
    def test_leader_first_compiler_child_reaped_and_forced_veto(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            child="import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); signal.signal(signal.SIGINT,signal.SIG_IGN); time.sleep(20)"
            leader="import subprocess,sys,time; subprocess.Popen([sys.executable,'-I','-B','-c',"+repr(child)+"]); time.sleep(.25)"
            budget=d.supervisor.Budget(10,time.time()+10,started=time.monotonic(),reserve=.5)
            result=d.supervise([str(Path(sys.executable).resolve()),"-I","-B","-c",leader],Path(temporary),budget)
            self.assertEqual(result["actual_child_exit"],0); self.assertTrue(result["forced_cleanup"])
            self.assertTrue(result["child_group_quiescent"]); self.assertGreaterEqual(len(result["observed_descendants"]),2)
            self.assertTrue(result["reaped"]); self.assertFalse(d.supervision_ok(result))
    def test_spawn_error_and_bool_exit_are_not_success(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            def bad(*args,**kwargs): raise OSError("가짜 생성 오류")
            result=d.supervise([sys.executable],Path(temporary),Budget(),factory=bad)
            self.assertEqual(result["launch_state"],"PENDING"); self.assertIsNone(result["actual_child_exit"])
            self.assertFalse(d.supervision_ok(result)); self.assertTrue(result["subreaper_restored"])
        self.assertFalse(d.supervision_ok(dict(actual_child_exit=False)))
    def test_stale_pgid_without_current_owner_is_not_signaled(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            process=SimpleNamespace(pid=450000,returncode=0,stdout=io.BytesIO(),
                poll=lambda:0,wait=lambda **_:0)
            saved=dict(pid=450000,ppid=os.getpid(),pgid=450000,session=450000,starttime=1,state="Z")
            with patch.object(d.supervisor.proc,"proc_stat",return_value=saved),\
                    patch.object(d,"owned_members",return_value=[]),\
                    patch.object(d.smoke,"owned_group_alive",return_value=True),\
                    patch.object(d.os,"killpg") as signaled:
                result=d.supervise([sys.executable],Path(temporary),Budget(),factory=lambda *a,**k:process)
            signaled.assert_not_called()
            self.assertEqual(result["actual_child_exit"],0)
            self.assertTrue(result["cleanup_errors"]); self.assertFalse(d.supervision_ok(result))
    def test_term_to_parent_preserves_interrupt_and_reaps_child(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            program=("import json,runpy,subprocess,sys,time\n"
                "n=runpy.run_path("+repr(str(ROOT/"scripts/diag_p106b_native_format_training.py"))+",run_name='owned')\n"
                "def start(*a,**k):\n"
                " p=subprocess.Popen(*a,**k); print('READY',flush=True); return p\n"
                "b=n['supervisor'].Budget(10,time.time()+10,started=time.monotonic(),reserve=1)\n"
                "with n['supervisor'].termination_guard():\n"
                " r=n['supervise']([sys.executable,'-I','-B','-c','import time; time.sleep(20)'],"
                "__import__('pathlib').Path("+repr(temporary)+"),b,factory=start)\n"
                "print(json.dumps(r),flush=True)\n"
                "raise SystemExit(0 if n['supervision_ok'](r) else 9)\n")
            process=subprocess.Popen([str(Path(sys.executable).resolve()),"-I","-B","-c",program],
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            try:
                self.assertTrue(select.select([process.stdout],[],[],5)[0])
                self.assertEqual(process.stdout.readline().strip(),"READY")
                time.sleep(.1); process.send_signal(signal.SIGTERM)
                output,_=process.communicate(timeout=8)
                self.assertEqual(process.returncode,9,output)
                result=json.loads(output)
                self.assertEqual(result["original_error"]["type"],"InterruptedError")
                self.assertEqual(result["actual_child_exit"],-signal.SIGTERM)
                self.assertTrue(result["forced_cleanup"]); self.assertTrue(result["child_group_quiescent"])
            finally:
                if process.poll() is None:
                    process.kill(); process.wait(timeout=5)
                if process.stdout is not None: process.stdout.close()


class MainTests(unittest.TestCase):
    def test_source_identity_and_language_ast(self):
        identity=d.source_identity()
        self.assertGreater(len(identity["files"]),40)
        for name in ("scripts/diag_p106b_native_format_training.py","scripts/test_p106b_native_format_training.py"):
            text=(ROOT/name).read_text(encoding="utf-8"); ast.parse(text)
            self.assertFalse(any(0x3400<=ord(c)<=0x9fff or 0xf900<=ord(c)<=0xfaff
                or 0x3040<=ord(c)<=0x30ff or 0x31f0<=ord(c)<=0x31ff for c in text))
    def test_check_only_imports_no_torch_or_cuda(self):
        command=[str(Path(sys.executable).resolve()),"-I","-B","-c",
            "import runpy,sys; ns=runpy.run_path("+repr(str(ROOT/"scripts/diag_p106b_native_format_training.py"))+
            ",run_name='isolated'); assert 'torch' not in sys.modules; print('CPU_IMPORT_ONLY')"]
        result=subprocess.run(command,capture_output=True,text=True,timeout=10,check=False)
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stdout.strip(),"CPU_IMPORT_ONLY")
    def test_worker_argv_reapplies_exact_companion(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); output="test_result/evidence/"+d.PREFIX+"argv"
            (root/"test_result/evidence").mkdir(parents=True)
            state=dict(source_identity=dict(sha256="A"*64,files={}),profile_sha256="B",f4_sha256="C",
                complete_sha256="D",profile=dict(cleanup_reserve_sec=120,arms=[dict(id="raw")]))
            actual_budget=d.supervisor.Budget
            def new_budget(seconds,deadline,**kwargs):
                return actual_budget(seconds,time.time()+seconds,**kwargs)
            observed=dict(actual_child_exit=9,launch_state="STARTED",forced_cleanup=False,
                child_group_quiescent=True,stdout_complete=True,subreaper_restored=True,original_error=None,cleanup_errors=[])
            with patch.object(d,"ROOT",root),patch.object(d,"metadata",return_value=state),\
                    patch.object(d,"immutable_metadata"),patch.object(d.supervisor,"Budget",side_effect=new_budget),\
                    patch.object(d,"supervise",return_value=observed) as run,redirect_stdout(io.StringIO()):
                argv=["--mode","cost","--arm","raw","--profile","profile.json","--profile-sha256","B",
                      "--f4","f4.json","--f4-sha256","C","--max-wall-sec","600","--output",output,"--execute"]
                self.assertEqual(d.main(argv),9)
                command=run.call_args.args[0]
                self.assertIn("--worker",command); self.assertNotIn("--execute",command)
                self.assertEqual(command[5],str(root/"scripts/diag_p106b_native_format_training.py"))
                before={p.name:p.read_bytes() for p in (root/output).iterdir()}
                self.assertEqual(d.main(argv),9)
                self.assertEqual(before,{p.name:p.read_bytes() for p in (root/output).iterdir()})
    def test_total_budget_covers_delayed_stdout_and_preserves_veto(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            directory=Path(temporary)
            budget=d.supervisor.Budget(.15,time.time()+.15,started=time.monotonic(),reserve=.01)
            with self.assertRaises(TimeoutError):
                with d.supervisor.total_budget(budget):
                    d.supervisor.write_once(directory/"receipt.json",dict(ok=True),budget)
                    time.sleep(.25)
            d.supervisor.append_terminal(directory,dict(event="TERMINAL_VETO",returncode=9))
            self.assertTrue((directory/"receipt.json").is_file())
            self.assertIn("TERMINAL_VETO",(directory/"terminal.jsonl").read_text())
    def test_train_process_deadline_is16_and_check_only_writes_nothing(self):
        state=dict(source_identity=dict(sha256="A"),profile=dict(cleanup_reserve_sec=120,arms=[dict(id="raw")]))
        deadline=[]
        actual_budget=d.supervisor.Budget
        def admitted(seconds,epoch,**kwargs):
            deadline.append(epoch)
            return actual_budget(seconds,epoch,**kwargs)
        with patch.object(d,"metadata",return_value=state),\
                patch.object(d,"budget_admission",return_value=dict(estimates_seconds=dict(raw=1))),\
                patch.object(d.supervisor,"Budget",side_effect=admitted),\
                patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()-30000),\
                patch.object(d.native,"modules",side_effect=AssertionError("모델 금지")),\
                redirect_stdout(io.StringIO()) as output:
            argv=["--mode","train","--arm","raw","--profile","missing.json","--profile-sha256","B",
                  "--f4","missing_f4.json","--f4-sha256","C","--max-wall-sec","600","--check-only"]
            self.assertEqual(d.main(argv),0)
        self.assertEqual(deadline,[d.TRAIN_END.timestamp()])
        self.assertEqual(json.loads(output.getvalue())["files_written"],0)
    def test_arm_larger_than_cli_wall_is_hold_before_runtime(self):
        state=dict(source_identity=dict(sha256="A"),profile=dict(cleanup_reserve_sec=120,arms=[dict(id="raw")]))
        with patch.object(d,"metadata",return_value=state),\
                patch.object(d,"budget_admission",return_value=dict(estimates_seconds=dict(raw=1000))),\
                patch.object(d.time,"time",return_value=d.TRAIN_END.timestamp()-30000),\
                patch.object(d.native,"modules",side_effect=AssertionError("모델 금지")),\
                redirect_stdout(io.StringIO()) as output:
            argv=["--mode","train","--arm","raw","--profile","missing.json","--profile-sha256","B",
                  "--f4","missing_f4.json","--f4-sha256","C","--max-wall-sec","600","--check-only"]
            self.assertEqual(d.main(argv),8)
        self.assertEqual(json.loads(output.getvalue())["error_type"],"Hold")


if __name__ == "__main__":
    unittest.main()
