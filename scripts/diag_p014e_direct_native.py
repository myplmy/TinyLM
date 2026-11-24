"""Full-model control using only the admitted direct table, never direct body."""
import argparse
from contextlib import nullcontext
import gc
import json
import time
import traceback
import unittest
import weakref
import numpy as np
import torch
from tokenizers import Tokenizer
from scripts import diag_p014e_direct_cuda as owner
from scripts import p014e_direct_head_adapter as adapter
from scripts import diag_p106b_resource_matrix as runtime
from scripts import interactive_research_infer as identity
from tinylm.infer.generate import sample as product_sample

io=owner.io
BASE=owner.BASE/"native_v1"
PROFILE=BASE/"profile.json"
OLD_REPORTS=("test_result/evidence/p014e_native595_g128_v1_20261027/baseline-cuda.json",
             "test_result/evidence/p014e_g270_large_vocab_v2_20261027_safe_loader_v1/deploy-cuda/report.json")
CODE=("scripts/diag_p014e_direct_native.py","scripts/p014e_direct_head_adapter.py",
      "scripts/test_p014e_direct_head_adapter.py","scripts/diag_p014e_direct_cuda.py","scripts/p014e_direct_cuda.py",
      "scripts/p014e_packed_g128.py","scripts/diag_p106b_resource_matrix.py","tinylm/model/transformer.py",
      "tinylm/model/modules.py","tinylm/model/ternary.py","tinylm/config.py","tinylm/infer/generate.py","tinylm/infer/dialogue.py")


def oracle(case):
    value=torch.load(io.ROOT/case["oracle"]["path"],map_location="cpu",weights_only=True)
    if "work_index" in case["oracle"]:
        return value["ternary5_existing_twn"][case["oracle"]["work_index"]]
    return dict(id=value["input"]["id"],ids=value["input"]["ids"],teacher_ids=value["teacher_ids"],logits=value["logits"])


def prepare():
    owner.Budget().check(admission=True);previous=owner.verify()
    if BASE.exists():raise FileExistsError("preserve head-only full-model namespace")
    suite=unittest.defaultTestLoader.loadTestsFromName("scripts.test_p014e_direct_head_adapter")
    checked=unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful() or checked.testsRun!=4:raise RuntimeError("four head/lookup/rollback CPU contracts required")
    import inspect
    required={"return_metadata","stop_token_sequences","mtp_tokens","eos_id","logits_last_only"}
    if not callable(product_sample) or not required<=set(inspect.signature(product_sample).parameters):
        raise ValueError("the unchanged product sampler callable and exact controls are required")
    op_report_path=owner.BASE/"actual/report.json";op=io.read(op_report_path)
    if op["status"]!="DIRECT_PACKED_OPERATOR_NUMERICAL_NEGATIVE" or op["numerical_gate_failures"]!=2:
        raise ValueError("preserve the original body numerical negative")
    table_rows=[r for r in op["rows"] if r["kind"]=="table"]
    if len(table_rows)!=6 or any(not r["original_gate"] for r in table_rows):
        raise ValueError("only the six real table operations may enter native integration")
    models=[];refs={op_report_path,owner.PROFILE}
    for index,(payload_name,report_name) in enumerate(zip(owner.INPUTS,OLD_REPORTS)):
        path=io.ROOT/payload_name;payload=owner.load(path);old_path=io.ROOT/report_name;closed=io.read(old_path)
        result=next(v["result"] for v in closed["variants"] if v["variant"]=="ternary5_existing_twn")
        if closed["exit_code"]!=0 or result["status"]!="FULL_TECHNICAL_SUITE_NOT_QUALITY":
            raise ValueError("closed same-device reference required")
        tokenizer=payload["provenance"]["tokenizer"]
        if io.sha(io.ROOT/tokenizer["path"])!=tokenizer["sha256"]:raise ValueError("explicit original tokenizer changed")
        tok=Tokenizer.from_file(str(io.ROOT/tokenizer["path"]));refs.update((path,old_path,io.ROOT/tokenizer["path"]))
        works=[]
        for wi,row in enumerate(result["records"]):
            name=row["workload"]
            pin=dict(path="runs/deploy/p014e_native595_g128_v1_20261027/baseline_cuda_oracle.pt",work_index=wi) if index==0 else dict(
                path="runs/deploy/p014e_g270_large_vocab_v2_20261027/oracle/cuda/ternary5_existing_twn/"+name+".pt")
            pin["sha256"]=io.sha(io.ROOT/pin["path"]);refs.add(io.ROOT/pin["path"])
            work=dict(id=name,oracle=pin);saved=oracle(work)
            if(saved["id"]!=name or saved["ids"]!=row["observed"]["prompt_ids"]
               or len(saved["ids"]) not in (128,512) or len(saved["logits"])!=4):
                raise ValueError("same exact128/512 old oracle and generation input required")
            work.update(ids=saved["ids"],teacher_ids=saved["teacher_ids"],old_generated_ids=row["observed"]["generated_ids"],
                        old_metadata=row["observed"]["metadata"]);works.append(work)
        answers=[]
        for row in result["answers"]:
            case=row["case"];seen=row["generation"];ids=seen["prompt_ids"]
            if not ids or max(ids)>=payload["cfg"]["vocab_size"]:raise ValueError("native IDs must fit the text head")
            answers.append(dict(case=case,ids=ids,old_answer=seen["answer"],old_generated_ids=seen["generated_ids"],old_metadata=seen["metadata"]))
        if len(works)!=4 or len(answers)!=4:raise ValueError("four full workloads and four native questions required")
        models.append(dict(id="native32k" if index==0 else "student_g270_vocab",payload=payload_name,
            payload_sha256=io.sha(path),tokenizer=tokenizer,expected_vocab=payload["cfg"]["vocab_size"],
            eos_id=2 if index==0 else 1,workloads=works,natural_questions=answers))
        payload=None
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb") as stream:stream.write(owner.PLAN.read_bytes())
    io.write_new(PROFILE,dict(schema="P014E_DIRECT_HEAD_NATIVE_V1",authority_directive=142,
        authority_end=owner.clock.AUTHORITY_END.isoformat(),cleanup_seconds=owner.clock.CLEANUP_SECONDS,max_seconds=1800,
        initial_plan_sha256=io.sha(BASE/"initial_plan.md"),sources={name:io.sha(io.ROOT/name) for name in CODE},
        references={str(path.relative_to(io.ROOT)):io.sha(path) for path in sorted(refs)},models=models,
        CPU_contracts=checked.testsRun,CPU_fixture_only_no_backbone=True,linear_rtol=.00002,linear_atol=.000002,
        full_body="UNCHANGED_ORIGINAL_SCALE_ROW4096_REFERENCE",head_only=True,cache=True,mtp_tokens=1,
        attention="FP32_MATH_TF32_OFF",temperature=0.,top_k=1,max_fixed=16,max_natural=32,
        timing_order=["REFERENCE","DIRECT","DIRECT","REFERENCE"],warmup_requests_per_block=1,measured_requests_per_block=3,
        original_checkpoint_reads=0,checkpoint_writes=0,optimizer_updates=0,quality_adoption=False,
        compile_cache_policy="REUSE_PREVIOUS_OWN_OPERATOR_CACHE_NOT_A_COLD_COMPILE_MEASUREMENT"))
    if torch.cuda.is_initialized():raise RuntimeError("CPU native preparation initialized CUDA")
    print("[DIRECT_NATIVE_PREPARED]four CPU contracts;two original payloads;body negative excluded",flush=True)


def verify():
    owner.verify();p=io.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=owner.clock.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=owner.clock.CLEANUP_SECONDS or p["initial_plan_sha256"]!=io.sha(BASE/"initial_plan.md")):
        raise ValueError("exact native authority/clock/initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if io.sha(io.ROOT/name)!=digest:raise ValueError("frozen native input/source changed: "+name)
    return p


class CountingForward(runtime.FP32Forward):
    def __init__(self,model):super().__init__(model,"cuda");self.calls=0
    def __call__(self,*args,**kwargs):self.calls+=1;return super().__call__(*args,**kwargs)


def generation(model,cfg,tok,ids,count,eos,natural,chatml,budget):
    budget.check();capture=runtime.FixedCapture(tok,ids);forward=CountingForward(model)
    torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
    with torch.no_grad():
        text,metadata=product_sample(forward,cfg,capture,"FROZEN_TOKEN_IDS",max_new=count,
            temperature=0.,top_k=1,device="cuda",use_cache=True,stop_at_eos=natural,eos_id=eos,
            logits_last_only=True,return_metadata=True,mtp_tokens=1,
            stop_token_sequences=[[4]] if natural and chatml else None)
    torch.cuda.synchronize();seconds=time.perf_counter()-start;generated=capture.decoded_ids[len(ids):]
    if len(generated)!=metadata["generated_tokens"] or len(generated)!=forward.calls:
        raise RuntimeError("same non-MTP product forward/token count required")
    if not natural and len(generated)!=count:raise RuntimeError("fixed-length generation incomplete")
    return dict(seconds=seconds,generated_ids=generated,answer=tok.decode(generated,skip_special_tokens=False),
        metadata=metadata,forward_calls=forward.calls,prompt_tokens=len(ids),generated_tokens=len(generated),
        tokens_per_second=len(generated)/seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved(),eos_id=eos,
        timing_scope="IDENTICAL_UNOBSERVED_PRODUCT_SAMPLER_WRAPPER_FP32_MATH_TOKENIZATION_EXCLUDED")


def numeric(model,work,folder,arm,p,budget):
    saved=oracle(work);forward=CountingForward(model);values=[];rows=[]
    token=torch.tensor([work["ids"]],device="cuda");kv=None
    with torch.no_grad():
        logits,kv=forward(token,use_cache=True,logits_last_only=True)
        for step in range(4):
            budget.check();actual=logits.detach().cpu().numpy().copy();wanted=saved["logits"][step].numpy()
            difference=np.abs(actual.astype(np.float64)-wanted.astype(np.float64))
            rows.append(dict(step=step,within_original_tolerance=bool(np.allclose(actual,wanted,rtol=p["linear_rtol"],atol=p["linear_atol"])),
                bit_exact=bool(np.array_equal(actual.view(np.uint32),wanted.view(np.uint32))),
                argmax_equal=bool(np.array_equal(actual.argmax(-1),wanted.argmax(-1))),
                maximum_absolute_error=float(difference.max()),mean_absolute_error=float(difference.mean())))
            values.append(actual)
            if step<3:logits,kv=forward(torch.tensor([[work["teacher_ids"][step]]],device="cuda"),past_kv=kv,use_cache=True,logits_last_only=True)
    packet=io.save_arrays(folder/(arm+"_"+work["id"]+"_logits.npz"),actual=np.stack(values))
    token=kv=logits=None
    return dict(arm=arm,workload=work["id"],rows=rows,actual_packet=packet,old_oracle=work["oracle"],forward_calls=forward.calls)


def actual():
    p=verify();budget=owner.Budget();budget.check(admission=True);out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve head-only native actual")
    out.mkdir();started=time.monotonic();report=dict(schema=p["schema"],status="STARTED",models=[],
        profile_sha256=io.sha(PROFILE),head_only=True,body_direct_kernel_used=False,
        source_payloads_unchanged=False,new_model_loads=0,original_checkpoint_reads=0,
        optimizer_updates=0,checkpoint_writes=0,quality_adoption=False)
    model=payload=operator=tok=None;failure=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        for spec in p["models"]:
            budget.check();folder=out/spec["id"];folder.mkdir();payload=owner.load(io.ROOT/spec["payload"])
            model=owner.direct.reference.load_payload(payload,device="cuda",tile_rows=4096)
            ref=weakref.ref(model);report["new_model_loads"]+=1;cfg=model.cfg
            if cfg.vocab_size!=spec["expected_vocab"] or cfg.max_seq_len!=1024:raise ValueError("exact native head/context required")
            tok=Tokenizer.from_file(str(io.ROOT/spec["tokenizer"]["path"]))
            operator=owner.direct.DirectPackedOperator(payload["embedding"],device="cpu")
            operator.packed_codes=model.packed_embedding.packed_codes
            operator.group_scales=model.packed_embedding.group_scales
            initial=identity.state_fingerprint(model);result=dict(id=spec["id"],numeric=[],timing=[],answers=[],contexts=[],
                initial_state_sha256=initial,storage=runtime.model_storage(model),head_extra_weight_storage_bytes=0)
            report["models"].append(result)
            with torch.no_grad():
                for arm in ("REFERENCE","DIRECT"):
                    context=nullcontext(None) if arm=="REFERENCE" else adapter.direct_head(model,operator)
                    with context as proof:
                        for work in spec["workloads"]:result["numeric"].append(numeric(model,work,folder,arm,p,budget))
                    if proof is not None:result["contexts"].append(proof)
                for work in spec["workloads"]:
                    blocks=[]
                    for block,arm in enumerate(p["timing_order"]):
                        context=nullcontext(None) if arm=="REFERENCE" else adapter.direct_head(model,operator)
                        with context as proof:
                            warm=generation(model,cfg,tok,work["ids"],16,spec["eos_id"],False,False,budget)
                            samples=[generation(model,cfg,tok,work["ids"],16,spec["eos_id"],False,False,budget) for _ in range(3)]
                        if proof is not None:result["contexts"].append(proof)
                        same=all(s["generated_ids"]==work["old_generated_ids"] and s["metadata"]==work["old_metadata"] for s in [warm,*samples])
                        blocks.append(dict(block=block,arm=arm,warmup=warm,samples=samples,all_old_fixed_ids_and_metadata_equal=same))
                    reference=[s["seconds"] for b in blocks if b["arm"]=="REFERENCE" for s in b["samples"]]
                    direct=[s["seconds"] for b in blocks if b["arm"]=="DIRECT" for s in b["samples"]]
                    result["timing"].append(dict(workload=work["id"],blocks=blocks,
                        reference_median_seconds=float(np.median(reference)),direct_median_seconds=float(np.median(direct)),
                        speedup=float(np.median(reference)/np.median(direct))))
                    print("[DIRECT_NATIVE_WORKLOAD]"+spec["id"]+"/"+work["id"],flush=True)
                for arm in ("REFERENCE","DIRECT"):
                    context=nullcontext(None) if arm=="REFERENCE" else adapter.direct_head(model,operator)
                    with context as proof:
                        for case in spec["natural_questions"]:
                            seen=generation(model,cfg,tok,case["ids"],32,spec["eos_id"],True,case["case"]["mode"]=="chatml",budget)
                            result["answers"].append(dict(arm=arm,case=case["case"],generation=seen,old_answer=case["old_answer"],
                                old_generated_ids_equal=seen["generated_ids"]==case["old_generated_ids"],
                                old_metadata_equal=seen["metadata"]==case["old_metadata"]))
                    if proof is not None:result["contexts"].append(proof)
            result.update(final_state_sha256=identity.state_fingerprint(model),
                physical_state_unchanged=identity.state_fingerprint(model)==initial,
                numeric_failures=sum(not row["within_original_tolerance"] for block in result["numeric"] for row in block["rows"]),
                argmax_mismatches=sum(not row["argmax_equal"] for block in result["numeric"] for row in block["rows"]))
            if not result["physical_state_unchanged"]:raise RuntimeError("native physical state changed")
            model.to("cpu");model=operator=payload=tok=cfg=None;gc.collect();torch.cuda.empty_cache()
            result["model_released"]=ref() is None
            if not result["model_released"]:raise RuntimeError("native model remains referenced")
            io.write_new(folder/"report.json",result)
        failures=sum(m["numeric_failures"] for m in report["models"])
        changed=sum(not b["all_old_fixed_ids_and_metadata_equal"] for m in report["models"] for w in m["timing"] for b in w["blocks"])
        changed+=sum(not a["old_generated_ids_equal"] or not a["old_metadata_equal"] for m in report["models"] for a in m["answers"])
        report.update(numerical_gate_failures=failures,changed_generation_records=changed,
            status="DIRECT_HEAD_NATIVE_COMPLETE" if failures==0 and changed==0 else "DIRECT_HEAD_NATIVE_NUMERICAL_OR_ID_NEGATIVE",
            source_payloads_unchanged=all(io.sha(io.ROOT/s["payload"])==s["payload_sha256"] for s in p["models"]))
        if not report["source_payloads_unchanged"]:raise RuntimeError("closed source payload changed")
    except BaseException as error:
        failure=str(error);report.update(status="DIRECT_HEAD_NATIVE_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        model=payload=operator=tok=cfg=None;gc.collect()
        cleanup_error=owner.cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;io.write_new(out/"report.json",report)
    print("[DIRECT_NATIVE_END]"+json.dumps(dict(status=report["status"],models=len(report["models"]),error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="check":verify();print("[DIRECT_NATIVE_CHECK]head-only admission,old oracles and clock",flush=True)
    else:actual()


if __name__=="__main__":main()
