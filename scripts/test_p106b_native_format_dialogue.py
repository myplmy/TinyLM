#!/usr/bin/env python3
"""고정 대화 회수의 CPU 합성 회귀. 실제 CP·모델·GPU는 열지 않는다."""
from __future__ import annotations
import ast
from contextlib import contextmanager,nullcontext,redirect_stdout
import copy
import io
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_native_format_dialogue as d


class Budget:
    def __init__(self):
        self.started=time.monotonic(); self.end=self.started+100; self.reserve=0
    def check(self,stage):
        if self.remaining() <= 0: raise TimeoutError(stage)
    def remaining(self): return self.end-time.monotonic()


def cases():
    return [dict(id="q"+str(i),language="ko" if i < 8 else "en",
        group="USER_REPORTED_FAILURE" if i < 6 else "FIXED_GENERAL",question="질문"+str(i)) for i in range(12)]


def observed(code=0):
    return dict(actual_child_exit=code,launch_state="STARTED",child_group_quiescent=True,
        stdout_complete=True,subreaper_restored=True,forced_cleanup=False,original_error=None,cleanup_errors=[])


def state():
    child=dict(status="TRAIN2289_COMPLETE",updates=2289,totals=dict(targets=300023808,x_tokens=300023808),
        synthetic=False,scratch_core_sha256=d.training.CORE,original_weights_copied=False,
        cfg=dict(n_layers=14,dim=768,vocab_size=32768,max_seq_len=1024,mtp_aux=False),
        final_core_sha256="B"*64,checkpoint="runs/ckpt/fixture.pt",checkpoint_sha256="C"*64,
        quantization_route=copy.deepcopy(d.official.ROUTE))
    profile=dict(schema=d.PROFILE,root_approved=True,source_sha256="A"*64,
        training_source_sha256=d.TRAINING_SHA,official_source_sha256=d.OFFICIAL_SHA,
        cases=copy.deepcopy(d.CASES_REF),generation_contract=copy.deepcopy(d.CONTRACT),deadline=d.END.isoformat(),
        cleanup_reserve_sec=120,entry_free_mib=13000,arm="fmt_muon",
        training_profile=dict(path="train_profile.json",sha256="D"*64),
        training_f4=dict(path="f4.json",sha256="E"*64),
        closed_train=dict(path="train/report.json",sha256="F"*64,actual_supervisor_exit=0,
            terminal_sha256="1"*64,actual_parent_wall_sec=100.))
    return dict(profile=profile,profile_ref=dict(path="profile.json",sha256="2"*64),profile_sha256="2"*64,
        source_identity=dict(sha256="A"*64,files={}),train=child,train_spec=profile["closed_train"],
        cases=cases(),training_state=dict(source_identity=dict(sha256=d.TRAINING_SHA)),
        training_args=SimpleNamespace(mode="train"))


def prompt_contract():
    d.interactive.validate_import_environment(ROOT)
    return SimpleNamespace(**runpy.run_path(str(ROOT/"tinylm/infer/dialogue.py"),run_name="_dialogue_contract_fixture"))


class Tokenizer:
    def get_vocab_size(self): return 32768
    def token_to_id(self,name): return {"<eos>":2,"<|im_start|>":3,"<|im_end|>":4}.get(name)
    def encode(self,text): return SimpleNamespace(ids=[10+ord(c)%30000 for c in text])
    def decode(self,ids,skip_special_tokens=True):
        return "".join("" if skip_special_tokens and v in (2,3,4) else
            {2:"<eos>",3:"<|im_start|>",4:"<|im_end|>"}.get(v,"답") for v in ids)


def runtime():
    cuda=SimpleNamespace(synchronize=lambda:None,reset_peak_memory_stats=lambda:None,
        memory_allocated=lambda:2**20,memory_reserved=lambda:2**21,
        max_memory_allocated=lambda:2**21,max_memory_reserved=lambda:2**22)
    return dict(torch=SimpleNamespace(no_grad=nullcontext,cuda=cuda,manual_seed=lambda _:None),
        model=object(),route=SimpleNamespace(assert_active=lambda:None),
        cfg=SimpleNamespace(vocab_size=32768,max_seq_len=1024),tokenizer=Tokenizer())


def tools(*,tokens=None,reason=None,calls=None):
    contract=prompt_contract()
    capture,forward=d.interactive.precision_types(ROOT)
    def sample(model,cfg,captured,prompt,**kwargs):
        if calls is not None: calls.append(dict(kwargs))
        generated=list(tokens) if tokens is not None else [77,4 if kwargs["stop_token_sequences"] else 2]
        finished=reason or ("STOP_SEQUENCE" if generated[-1] == 4 else "EOS" if generated[-1] == 2 else "MAX_NEW")
        captured.decode(captured.encode(prompt).ids+generated)
        trace=dict(finish_reason=finished,generated_tokens=len(generated),max_new=128,eos_token_available=True,
            stop_at_eos_requested=True,stop_at_eos_effective=True)
        if kwargs["stop_token_sequences"]:
            trace.update(stop_token_sequences=[[4]],matched_stop_sequence=[4] if finished == "STOP_SEQUENCE" else None)
        return "",trace
    return contract,sample,capture,forward


def route_receipt():
    return dict(mode="ternary",metadata=copy.deepcopy(d.official.ROUTE),tlinear_instances=1,
        owned_tlinear_instances=1,refreshed_tlinear_instances=1,
        forward_methods=["_guarded_forward"],refresh_methods=["_ternary_refresh"])


def proof(s):
    return dict(cpu_and_gpu_core_sha256=s["train"]["final_core_sha256"],
        final_core_sha256=s["train"]["final_core_sha256"],checkpoint_sha256=s["train"]["checkpoint_sha256"],
        cfg=copy.deepcopy(s["train"]["cfg"]),contract=copy.deepcopy(d.official.CONTRACT),scratch_core_sha256=d.training.CORE,
        cpu_key_shape_dtype_layout_alias_verified=True,all_checkpoint_floats_finite=True,
        updates=2289,targets=300023808,route=route_receipt(),final_route=route_receipt())


class MetadataTests(unittest.TestCase):
    def test_protected_environment_paths_never_reach_reader(self):
        for name in ("datasets/TinyDataset/x",".claude/x","ai_dev_tool/00.md"):
            with self.subTest(name=name),patch.object(d.official,"read_ref",side_effect=AssertionError("접근 금지")) as read:
                with self.assertRaises(ValueError): d.read_ref(dict(path=name,sha256="A"*64),Budget())
                read.assert_not_called()
    def test_actual_cases_pin_and_original_source_still_frozen(self):
        self.assertEqual(d.official.digest(ROOT/d.CASES_REF["path"]),d.CASES_REF["sha256"])
        self.assertEqual(d.training.source_identity()["sha256"],d.TRAINING_SHA)
        self.assertEqual(d.official.source_identity()["sha256"],d.OFFICIAL_SHA)
    def test_unfinished_or_nonzero_parent_holds_before_loader(self):
        s=state()
        for change in ("actual_exit","returncode","forced","updates","targets"):
            profile=copy.deepcopy(s["profile"])
            parent=dict(returncode=0,supervision=observed(),worker=copy.deepcopy(s["train"]))
            if change == "actual_exit": profile["closed_train"]["actual_supervisor_exit"]=8
            if change == "returncode": parent["returncode"]=9
            if change == "forced": parent["supervision"]["forced_cleanup"]=True
            if change == "updates": parent["worker"]["updates"]=2288
            if change == "targets": parent["worker"]["totals"]["targets"]-=1
            with self.subTest(change=change),patch.object(d.official,"read_ref",return_value=parent),\
                    patch.object(d.training,"read_closed",side_effect=AssertionError("완주 전 CP 접근 금지")) as closed:
                with self.assertRaises(d.Hold): d.closed_train(profile,s["training_state"],Budget())
                closed.assert_not_called()
    def test_closed_train_reuses_actual_read_closed(self):
        s=state(); parent=dict(returncode=0,supervision=observed(),worker=s["train"])
        with patch.object(d.official,"read_ref",return_value=parent),\
                patch.object(d.training,"read_closed",return_value=parent) as closed:
            self.assertEqual(d.closed_train(s["profile"],s["training_state"],Budget()),s["train"])
        self.assertEqual(closed.call_args.args[-1],"train")
    def test_wrong_reference_sha_remains_error(self):
        s=state()
        with patch.object(d.official,"read_ref",side_effect=ValueError("SHA 불일치")),self.assertRaises(ValueError):
            d.closed_train(s["profile"],s["training_state"],Budget())
    def test_metadata_fixed_cases_and_contract_before_runtime(self):
        s=state(); args=SimpleNamespace(source_sha256="A"*64,profile="profile.json",profile_sha256="2"*64)
        def read(ref,budget): return s["cases"] if ref == d.CASES_REF else s["profile"]
        with patch.object(d,"source_identity",return_value=s["source_identity"]),\
                patch.object(d.training,"source_identity",return_value=dict(sha256=d.TRAINING_SHA)),\
                patch.object(d.official,"source_identity",return_value=dict(sha256=d.OFFICIAL_SHA)),\
                patch.object(d.official,"read_ref",side_effect=read),\
                patch.object(d.training,"metadata",return_value=s["training_state"]),\
                patch.object(d,"closed_train",return_value=s["train"]),\
                patch.object(d.official,"strict_runtime",side_effect=AssertionError("모델 금지")):
            self.assertEqual(d.metadata(args,Budget())["cases"],s["cases"])
            s["profile"]["generation_contract"]["max_new"]=256
            with self.assertRaises(ValueError): d.metadata(args,Budget())


class GenerationTests(unittest.TestCase):
    def test_actual_prompt_paths_and_fixed_sample_options(self):
        active=runtime(); case=cases()[0]; calls=[]; shared=tools(calls=calls)
        plain=d.emit(active,case,"plain",Budget(),tools=shared)
        chat=d.emit(active,case,"chatml",Budget(),tools=shared)
        self.assertEqual(plain["prompt"],case["question"])
        self.assertEqual(chat["prompt"],"<|im_start|>user\n"+case["question"]+"<|im_end|>\n<|im_start|>assistant\n")
        self.assertEqual((calls[0]["max_new"],calls[0]["temperature"],calls[0]["top_k"],calls[0]["mtp_tokens"]),(128,0.,1,1))
        self.assertIsNone(calls[0]["stop_token_sequences"]); self.assertEqual(calls[1]["stop_token_sequences"],[[4]])
        self.assertTrue(all(row["stop_at_eos"] and row["eos_id"] == 2 and row["logits_last_only"] for row in calls))
    def test_raw_special_token_answer_is_preserved(self):
        row=d.emit(runtime(),cases()[0],"plain",Budget(),tools=tools(tokens=[4,77,2]))
        self.assertEqual(row["answer"],"<|im_end|>답<eos>")
        self.assertEqual(row["display_answer"],"답")
        self.assertEqual(row["generated_ids"],[4,77,2]); self.assertFalse(row["quality_claim"])
    def test_eos_at128_is_reached_but_not_length_stop(self):
        row=d.emit(runtime(),cases()[0],"chatml",Budget(),tools=tools(tokens=[77]*127+[2]))
        self.assertTrue(row["max_new_reached"]); self.assertFalse(row["stopped_at_length_cap"])
        self.assertEqual(row["trace"]["finish_reason"],"EOS")
    def test_cap128_is_valid_observation_not_quality(self):
        row=d.emit(runtime(),cases()[0],"plain",Budget(),tools=tools(tokens=[77]*128))
        self.assertTrue(row["max_new_reached"]); self.assertTrue(row["stopped_at_length_cap"])
        self.assertFalse(row["quality_claim"])
    def test_request129_or_wrong_end_is_rejected(self):
        for generated,reason in (([77]*129,"MAX_NEW"),([77,2],"STOP_SEQUENCE"),([77,4],"EOS")):
            with self.subTest(reason=reason),self.assertRaises(ValueError):
                d.emit(runtime(),cases()[0],"chatml",Budget(),tools=tools(tokens=generated,reason=reason))
    def test_earlier_eos_or_chatml_eot_cannot_be_hidden(self):
        for mode,generated in (("plain",[2,77,2]),("chatml",[4,77,2])):
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                d.emit(runtime(),cases()[0],mode,Budget(),tools=tools(tokens=generated,reason="EOS"))
    def test_prefix_or_count_mismatch_rejected(self):
        row=d.emit(runtime(),cases()[0],"plain",Budget(),tools=tools())
        for key,value in (("all_ids",[9]),("generated_ids",[9]),("prompt_ids_sha256","F"*64)):
            bad=copy.deepcopy(row); bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): d.validate_record(bad,cases()[0],"plain")
    def test_context_overflow_has_no_sampler_call(self):
        active=runtime(); active["cfg"].max_seq_len=128; calls=[]
        with self.assertRaises(ValueError): d.emit(active,cases()[0],"plain",Budget(),tools=tools(calls=calls))
        self.assertEqual(calls,[])
    def test_request_deadline_before_generation(self):
        budget=Budget(); budget.end=0; calls=[]
        with self.assertRaises(TimeoutError): d.emit(runtime(),cases()[0],"plain",budget,tools=tools(calls=calls))
        self.assertEqual(calls,[])
    def test_nonfinite_allocator_or_time_rejected(self):
        row=d.emit(runtime(),cases()[0],"plain",Budget(),tools=tools())
        row["generation_wall_sec"]=math.nan
        with self.assertRaises(ValueError): d.validate_record(row,cases()[0],"plain")
        row["generation_wall_sec"]=1.; row["allocator"]["allocated_mib"]=math.inf
        with self.assertRaises(ValueError): d.validate_record(row,cases()[0],"plain")


class WorkerTests(unittest.TestCase):
    def run_worker(self,directory,*,mutate_core=False):
        s=state(); active=runtime(); model_proof=proof(s)
        @contextmanager
        def strict(current,budget):
            self.assertIs(current,s)
            yield active,model_proof
            if mutate_core: model_proof["final_core_sha256"]="E"*64
        memory=SimpleNamespace(summary=lambda:dict(samples=2,continuous_peak_verified=False,missing_queries=0))
        with patch.object(d,"immutable"),patch.object(d.official,"strict_runtime",side_effect=strict) as loader,\
                patch.object(d.training,"MemorySamples",return_value=nullcontext(memory)),\
                patch.object(d,"generation_tools",return_value=tools()),redirect_stdout(io.StringIO()):
            child=d.execute_worker(SimpleNamespace(output=directory),s,Budget())
        return s,child,loader
    def test24_answers_strict_loader_no_optimizer_and_readback(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            directory=Path(temporary); s,child,loader=self.run_worker(directory)
            self.assertEqual(child["requests"],24); loader.assert_called_once()
            rows=list(d.official.manifests_rows(directory/"answers",child["answers_manifest"],Budget()))
            self.assertEqual([(r["case_id"],r["mode"]) for r in rows],[(c["id"],m) for c in s["cases"] for m in d.MODES])
            self.assertTrue(all(spec["bytes"] < 20_000_000 for spec in child["answers_manifest"]["shards"]))
            child["requests"]=23
            with self.assertRaises(ValueError): d.validate_worker(child,s,directory,Budget())
    def test_core_mutation_after_generation_is_veto(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary,self.assertRaises(ValueError):
            self.run_worker(Path(temporary),mutate_core=True)
    def test_partial_generation_keeps_raw_and_original_error(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            directory=Path(temporary); s=state()
            @contextmanager
            def strict(*args): yield runtime(),proof(s)
            memory=SimpleNamespace(summary=lambda:dict(samples=1,continuous_peak_verified=False))
            count=[0]; real_emit=d.emit
            def failing(*args,**kwargs):
                count[0]+=1
                if count[0] == 3: raise TimeoutError("요청 시간 초과")
                return real_emit(*args,**kwargs)
            with patch.object(d,"immutable"),patch.object(d.official,"strict_runtime",side_effect=strict),\
                    patch.object(d.training,"MemorySamples",return_value=nullcontext(memory)),\
                    patch.object(d,"generation_tools",return_value=tools()),patch.object(d,"emit",side_effect=failing),\
                    redirect_stdout(io.StringIO()),self.assertRaisesRegex(TimeoutError,"요청 시간"):
                d.execute_worker(SimpleNamespace(output=directory),s,Budget())
            self.assertEqual(count[0],3)
            self.assertEqual(len(list((directory/"answers").glob("*.jsonl"))),1)
            self.assertFalse((directory/"answers/answers_shards_manifest.json").exists())


class ParentTests(unittest.TestCase):
    def test_worker_wrong_parent_never_loads_or_changes_old_output(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); output="test_result/evidence/"+d.PREFIX+"wrong_owner"
            directory=root/output; directory.mkdir(parents=True)
            work_end=time.monotonic()+200
            invocation=dict(parent_pid=0,parent_starttime=1,source_sha256="A"*64,
                profile_sha256="2"*64,work_end=work_end)
            (directory/"invocation.json").write_bytes(d.canonical(invocation))
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            with patch.object(d,"safe",side_effect=lambda name:root/name),patch.object(d,"metadata",return_value=state()),\
                    patch.object(d,"execute_worker",side_effect=AssertionError("소유 확인 전 실행 금지")) as execute,\
                    redirect_stdout(io.StringIO()):
                argv=["--profile","unused","--profile-sha256","2"*64,"--source-sha256","A"*64,"--output",output,
                    "--worker","--parent-started",str(time.monotonic()-.1),"--work-end",str(work_end)]
                self.assertEqual(d.main(argv),9)
            execute.assert_not_called()
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})
    def test_delayed_final_stdout_leaves_append_only_veto(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); (root/"test_result/evidence").mkdir(parents=True)
            output="test_result/evidence/"+d.PREFIX+"slow_stdout"
            s=state(); s["profile"]["cleanup_reserve_sec"]=.01; worker=dict(fixture=True)
            def supervised(command,directory,budget):
                (directory/"worker.json").write_bytes(d.canonical(worker))
                return observed()
            def budget_factory(*args,**kwargs):
                budget=Budget(); budget.end=time.monotonic()+.15; budget.reserve=.01
                return budget
            real_print=print; calls=[0]
            def delayed(*args,**kwargs):
                calls[0]+=1
                if calls[0] == 1: time.sleep(.3)
                real_print(*args,**kwargs)
            with patch.object(d,"ROOT",root),patch.object(d,"safe",side_effect=lambda name:root/name),\
                    patch.object(d,"metadata",return_value=s),patch.object(d,"immutable"),patch.object(d,"validate_worker"),\
                    patch.object(d.official,"read_ref",return_value=worker),\
                    patch.object(d.training,"supervise",side_effect=supervised),\
                    patch.object(d.supervisor,"Budget",side_effect=budget_factory),\
                    patch("builtins.print",side_effect=delayed),redirect_stdout(io.StringIO()):
                argv=["--profile","unused","--profile-sha256","2"*64,"--source-sha256","A"*64,
                    "--output",output,"--execute"]
                self.assertEqual(d.main(argv),9)
            report=json.loads((root/output/"report.json").read_bytes())
            self.assertEqual(report["returncode"],0)
            terminal=[json.loads(line) for line in (root/output/"terminal.jsonl").read_text().splitlines()]
            self.assertEqual(terminal[0],dict(event="OBSERVATION",returncode=0))
            self.assertEqual(terminal[-1]["event"],"TERMINAL_VETO")
            self.assertEqual(terminal[-1]["error"]["type"],"TimeoutError")
    def test_source_only_is_stdlib_and_writes_nothing(self):
        command=[str(Path(sys.executable).resolve()),"-I","-B","-c",
            "import runpy,sys; n=runpy.run_path("+repr(str(ROOT/"scripts/diag_p106b_native_format_dialogue.py"))+
            ",run_name='probe'); assert n['main'](['--source-only'])==0; assert 'torch' not in sys.modules"]
        result=subprocess.run(command,capture_output=True,text=True,timeout=10,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        info=json.loads(result.stdout); self.assertEqual(info["files_written"],0)
    def test_missing_profile_is_hold_no_model(self):
        with patch.object(d.official,"strict_runtime",side_effect=AssertionError("모델 금지")) as loader,redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(["--check-only"]),8)
        loader.assert_not_called()
    def test_actual_worker_argv_is_new_companion_and_old_files_preserved(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root=Path(temporary); (root/"test_result/evidence").mkdir(parents=True)
            output="test_result/evidence/"+d.PREFIX+"argv"
            s=state(); seen=observed(9)
            with patch.object(d,"safe",side_effect=lambda name:root/name),\
                    patch.object(d,"metadata",return_value=s),patch.object(d,"immutable"),\
                    patch.object(d.training,"supervise",return_value=seen) as run,redirect_stdout(io.StringIO()):
                argv=["--profile","unused.json","--profile-sha256","2"*64,"--source-sha256","A"*64,
                    "--output",output,"--max-wall-sec","900","--execute"]
                self.assertEqual(d.main(argv),9)
                command=run.call_args.args[0]
                self.assertEqual(command[5],str(ROOT/"scripts/diag_p106b_native_format_dialogue.py"))
                self.assertIn("--worker",command); self.assertIn("--work-end",command); self.assertNotIn("--execute",command)
                old={p.name:p.read_bytes() for p in (root/output).iterdir()}
                self.assertEqual(d.main(argv),9)
                self.assertEqual(old,{p.name:p.read_bytes() for p in (root/output).iterdir()})
    def test_check_only_no_generation_or_write(self):
        with patch.object(d,"metadata",return_value=state()),patch.object(d,"execute_worker",
                side_effect=AssertionError("생성 금지")) as execute,redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.main(["--profile","unused","--profile-sha256","2"*64,
                "--source-sha256","A"*64,"--check-only"]),0)
        self.assertEqual(json.loads(output.getvalue())["files_written"],0); execute.assert_not_called()
    def test_late_deadline_is_rejected(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(["--profile","unused","--profile-sha256","2"*64,"--source-sha256","A"*64,
                "--deadline","2026-10-26T08:00:01+00:00","--check-only"]),9)
    def test_ast_and_new_language_boundaries(self):
        for name in ("scripts/diag_p106b_native_format_dialogue.py","scripts/test_p106b_native_format_dialogue.py"):
            text=(ROOT/name).read_text(encoding="utf-8"); ast.parse(text)
            self.assertFalse(any(0x3400<=ord(c)<=0x9fff or 0x3040<=ord(c)<=0x30ff or 0xf900<=ord(c)<=0xfaff for c in text))


if __name__ == "__main__":
    unittest.main()
