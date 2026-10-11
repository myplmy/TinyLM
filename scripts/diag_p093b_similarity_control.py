#!/usr/bin/env python3
"""Last-state cosine intervention with the complete next-token readout preserved."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p093b_causal_probe as cause
from scripts import diag_p093b_native_repair as old
from scripts import diag_p093b_generation_attribution as saved
from scripts import diag_p093b_live_trace as live
TAG="p093b_similarity_control_v1_s1337"
CODE=("scripts/diag_p093b_similarity_control.py","scripts/p093b_similarity_control.py",
      "scripts/test_p093b_similarity_control.py",*cause.CODE)
CAUSE=ROOT/"test_result/evidence/p093b_causal_v1_s1337/causal_intervene/report.json"
CAUSE_SHA="4E87B8398ADA06D2A8D5FD7682CB7ED3D5E95502159DB8D0ED3D6090035C9C89"


def directory(tag,mode):return old.directory(tag,"similarity_"+mode)


def execute(info,out):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.p093b_causal_probe import controlled_forward,output_metrics
    from scripts.p093b_similarity_control import head_basis,reflect,cosine
    from scripts import p093b_native_repair as native
    from scripts.p106b_education_followup import ARMS
    from scripts.diag_p093b_calibration_recovery import PARENT_SHA
    from scripts.p106b_gate_runtime import idle_before_gpu
    from scripts.p106b_shards import ShardWriter,verify
    start=time.perf_counter()
    if old.digest(CAUSE)!=CAUSE_SHA:raise ValueError("exact causal source changed")
    src=saved.source();live.verify_factor_pin(src)
    tokp=ROOT/ARMS["a"]["tokenizer"]
    if old.digest(old.PARENT)!=PARENT_SHA or old.digest(tokp)!=ARMS["a"]["tok_sha"]:raise ValueError("pinned parent/tokenizer changed")
    idle_before_gpu()
    model,cfg,dev=load_model("dense",str(old.PARENT),"cuda")
    if cfg.tie_mlp or cfg.train_repeat!=1. or model.visit_schedule()!=list(range(16)) or getattr(model,"_emb_fmt",None) is not None:
        raise ValueError("unchanged independent R1 native factorized readout required")
    torch.set_num_threads(4)
    q,residual=head_basis(model._emb_up_w(),model.norm_f_scale)
    info.update(model_loading="MEASURED",readout_dim=list(q.shape),nullspace_dim=q.shape[0]-q.shape[1],
        basis_residual=residual,precision="FP32/math IEEE",parent_sha256=PARENT_SHA)
    original=[model.layers[i].mlp[0] for i in src["input"]["group_layers"]]
    refs=[id(m) for m in original]
    shared=native.shared_native(original,cfg)
    adapters=old.load_adapters(saved.BASE,"rank64",shared,cfg,src["input"])
    tok=Tokenizer.from_file(str(tokp));eos=tok.token_to_id("<eos>")
    panel=cause.cases(cause.source_rows(),tok)
    writer=ShardWriter(out,"similarity_rows");rows=[]
    try:
        with torch.no_grad():
            for subject in ("parent","shared","rank64"):
                context=nullcontext() if subject=="parent" else native.patched_group(model,src["input"]["group_layers"],shared,adapters if subject=="rank64" else None)
                with context:
                    for c in panel:
                        prefix=c["anchor"]+c["bodies"][8]
                        previous=prefix[:-len(c["block"])]
                        if not previous or prefix[-1]!=previous[-1]:raise ValueError("same-phase last token mismatch")
                        a,hs,_=controlled_forward(model,prefix)
                        _,hp,_=controlled_forward(model,previous)
                        x,prev=hs[(15,0)],hp[(15,0)]
                        altered,stats=reflect(x,q)
                        b,_,_=controlled_forward(model,prefix,patches={15:altered})
                        metrics_a=output_metrics(a,c["focus"],eos,tok.decode)
                        metrics_b=output_metrics(b,c["focus"],eos,tok.decode)
                        scale=model.norm_f_scale.detach().double().cpu()
                        def analytical_hidden(v):
                            z=v.double()
                            return z/(z.square().mean()+model.norm_f.eps).sqrt()*scale
                        delta=float((a-b).abs().max());bound=1e-4+1e-5*float(a.abs().max())
                        row={"subject":subject,"case":c["case"],"question":c["question"],
                            "prefix_ids":prefix,"previous_phase_prefix_ids":previous,
                            "original_last":x.tolist(),"reflected_last":altered.tolist(),"previous_phase_last":prev.tolist(),
                            "before_cosine_to_previous_phase":cosine(x,prev),
                            "after_cosine_to_previous_phase":cosine(altered,prev),
                            "analytical_final_RMS_scale_cosine_before":cosine(analytical_hidden(x),analytical_hidden(prev)),
                            "analytical_final_RMS_scale_cosine_after":cosine(analytical_hidden(altered),analytical_hidden(prev)),
                            "final_hidden_stat_scope":"FP64 analytical RMS+scale; actual GPU logits verified separately",
                            "same_last_token_id":prefix[-1],"reflection":stats,
                            "original_metrics":metrics_a,"reflected_metrics":metrics_b,
                            "max_logit_abs_difference":delta,"argmax_match":int(a.argmax())==int(b.argmax()),
                            "numeric_bound":bound,"within_bound":delta<=bound,
                            "scope":"one final-position intervention, not free-running whole-sequence repair"}
                        writer.append(row);rows.append(row)
                        print("[SIMILARITY_CONTROL] "+json.dumps({k:v for k,v in row.items() if k not in ("prefix_ids","previous_phase_prefix_ids","original_last","reflected_last","previous_phase_last")},ensure_ascii=False),flush=True)
    finally:
        manifest=writer.close(lineage=info) if writer._total_rows else None
        if manifest:verify(out,manifest)
        old.write(out/"partial.json",{"input":info,"manifest":manifest,"complete_rows":len(rows),"new_generations":0})
    restored=[id(model.layers[i].mlp[0]) for i in src["input"]["group_layers"]]==refs
    complete=len(rows)==12 and restored
    invariance=all(r["argmax_match"] and r["within_bound"] for r in rows)
    return {"input":info,"status":"SIMILARITY_CONTROL_COMPLETE" if complete else "INCOMPLETE",
        "manifest":manifest,"rows":[{k:v for k,v in r.items() if k not in ("original_last","reflected_last","previous_phase_last","prefix_ids","previous_phase_prefix_ids")} for r in rows],
        "whole_wall_sec":time.perf_counter()-start,"readout_invariance":invariance,"in_memory_restored":restored,
        "new_generations":0,"optimizer_updates":0,"checkpoint_writes":0,
        "causality":"output-equivalent final-state changes test necessity of the measured cosine, not early-layer mechanisms"},0 if complete and invariance else 8


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("contract","intervene","readback"),required=True)
    p.add_argument("--tag",default=TAG);p.add_argument("--execute",action="store_true")
    p.add_argument("--check-only",action="store_true");p.add_argument("--max-wall-sec",type=int,default=120)
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=120:p.error("bounded60..120 seconds")
    info={"schema":"P093B_SIMILARITY_NULL_CONTROL_V1","code_sha256":{n:old.digest(ROOT/n) for n in dict.fromkeys(CODE)},
        "causal_source_sha256":CAUSE_SHA,"tag":args.tag,"mode":args.mode,"model_loading":"NOT_RUN",
        "max_wall_sec":args.max_wall_sec,"new_generations":0,"optimizer_updates":0,"checkpoint_writes":0}
    if args.check_only or not args.execute:print("[PREFLIGHT] "+json.dumps(info));return 0
    out=directory(args.tag,args.mode)
    if out.exists():print("[HOLD] existing evidence preserved");return 8
    out.mkdir(parents=True)
    try:
        if args.mode=="contract":
            r=subprocess.run([sys.executable,"-B","-X","utf8","-m","unittest","scripts.test_p093b_similarity_control","-v"],timeout=args.max_wall_sec,cwd=ROOT)
            if r.returncode:raise ValueError("CPU algebra contract failed")
            result={"input":info,"status":"CPU_CONTRACT_PASS"};rc=0
        elif args.mode=="readback":
            target=directory(args.tag,"intervene")
            src=json.loads((target/"report.json").read_text())
            if src.get("status")!="SIMILARITY_CONTROL_COMPLETE" or src["input"]["code_sha256"]!=info["code_sha256"]:raise FileNotFoundError("same-code complete control required")
            from scripts.p106b_shards import verify
            verify(target,src["manifest"])
            result={"input":info,"status":"SIMILARITY_READBACK_COMPLETE","source_sha256":old.digest(target/"report.json"),"readout_invariance":src["readout_invariance"]}
            rc=0 if src["readout_invariance"] else 8
        else:
            contract=json.loads((directory(args.tag,"contract")/"report.json").read_text())
            if contract.get("status")!="CPU_CONTRACT_PASS" or contract["input"]["code_sha256"]!=info["code_sha256"]:raise FileNotFoundError("fresh CPU contract required")
            with cause.budget(args.max_wall_sec):result,rc=execute(info,out)
    except BaseException as exc:
        rc=130 if isinstance(exc,KeyboardInterrupt) else 8 if isinstance(exc,(TimeoutError,FileNotFoundError,FileExistsError)) else 9
        result={"input":info,"status":"PARTIAL_OR_HOLD" if rc in (8,130) else "TOOL_FAILURE","reason":str(exc),"error_type":type(exc).__name__}
    old.write(out/"report.json",result)
    print("[EXPERIMENT_FINAL] "+json.dumps({"mode":args.mode,"status":result["status"],"exit_code":rc,"new_generations":0,"optimizer_updates":0,"checkpoint_writes":0}))
    return rc


if __name__=="__main__":raise SystemExit(main())
