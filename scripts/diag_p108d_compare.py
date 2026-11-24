"""Reuse the closed D capture for matched-net and selective-support comparisons."""
import argparse
import gc
import json
import time
import traceback
import unittest
import numpy as np
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend

from scripts import diag_p108d_winner as study
from scripts import p108d_winner as mathematics
from scripts import p108d_compare as comparison
from scripts import diag_p108c_scope as io
from scripts import p108c_limits as limits
from scripts import p108_wsp_attention as edits
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p108b_tinylm import TinyAdapter
from scripts.p106b_shards import ShardWriter

BASE=study.BASE/"comparison_v1"
PROFILE=BASE/"profile.json"
SOLVE=BASE/"solve"
ACTUAL=BASE/"actual"
CODE=("scripts/p108d_compare.py","scripts/test_p108d_compare.py","scripts/diag_p108d_compare.py",
      "scripts/diag_p108d_winner.py","scripts/p108d_winner.py","scripts/p108b_tinylm.py",
      "scripts/p108_wsp_attention.py","scripts/p108c_limits.py")


def prepare():
    limits.Budget(1800).check(admission=True)
    if BASE.exists():raise FileExistsError("preserve comparison namespace")
    parent=study.verify()
    closed=io.read(study.VALIDATE/"report.json")
    if closed["status"]!="WINNER_NATIVE_VALIDATION_COMPLETE" or not closed["original_core_restored"]:
        raise ValueError("closed two previous candidate answers required")
    suite=unittest.defaultTestLoader.loadTestsFromName("scripts.test_p108d_compare")
    checked=unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful() or checked.testsRun!=7:raise RuntimeError("seven independent compare contracts required")
    capture,arrays,head=study.captured()
    paths={study.PROFILE,study.SOLVE/"report.json",study.VALIDATE/"report.json",study.CAPTURE/"report.json"}
    paths.update(io.ROOT/p["path"] for p in capture["head_packets"]+[capture["features"]])
    for row in io.read(study.SOLVE/"report.json")["arms"]:
        paths.add(io.ROOT/row["packet"]["path"])
        paths.add(io.ROOT/row["solver"]["path"])
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb")as stream:stream.write(io.PLAN.read_bytes())
    io.write_new(PROFILE,dict(schema="P108D_MATCHED_NET_SUPPORT_V1",authority_directive=142,
        authority_end=limits.AUTHORITY_END.isoformat(),cleanup_seconds=limits.CLEANUP_SECONDS,
        parent_profile_sha256=io.sha(study.PROFILE),model=parent["model"],origin=parent["origin"],
        initial_plan_sha256=io.sha(BASE/"initial_plan.md"),
        code={p:io.sha(io.ROOT/p) for p in CODE},references={str(p.relative_to(io.ROOT)):io.sha(p)for p in sorted(paths)},
        CPU_contracts=checked.testsRun,counts=[512,256],random_seeds=[1337,2024,2718],
        target_norm=study.COMMON_BUDGET,norm_rtol=2e-5,ray_raw_violation_target=0.,
        ray_absolute_signed_gap_limit=1e-5,maximum_native_arms=10,
        CPU_max_seconds=1800,native_max_seconds=1800,max_new=64,native_logit_tolerance=.002,
        source_role="FIT24_ONLY_FOR_EDIT_AND_SUPPORT_PRIOR_DEV96_FOR_DIAGNOSIS",
        final_or_official_used=False,body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0))
    if torch.cuda.is_initialized():raise RuntimeError("CPU compare preparation initialized CUDA")
    print("[COMPARE_PREPARED]two matched-net and eight matched-column arms;old capture reused",flush=True)


def verify():
    p=io.read(PROFILE);study.verify()
    if(p["authority_end"]!=limits.AUTHORITY_END.isoformat()or p["authority_directive"]!=142
       or p["cleanup_seconds"]!=limits.CLEANUP_SECONDS or p["initial_plan_sha256"]!=io.sha(BASE/"initial_plan.md")):
        raise ValueError("exact comparison authority and initial plan required")
    for name,digest in {**p["code"],**p["references"]}.items():
        if io.sha(io.ROOT/name)!=digest:raise ValueError("comparison input changed: "+name)
    return p


def solve():
    p=verify();budget=limits.Budget(p["CPU_max_seconds"]);budget.check(admission=True)
    if SOLVE.exists():raise FileExistsError("preserve previous CPU comparison")
    SOLVE.mkdir();started=time.monotonic()
    capture,arrays,head=study.captured();gate=capture["gate"]
    required=arrays["original_rms"]*.10
    parent=io.read(study.SOLVE/"report.json");arms=[];repairs=[];rejected=[]

    def save_arm(name,direction,*,selection=None,solver=None):
        directory=SOLVE/name;directory.mkdir()
        after,actual,physical=comparison.match_norm(arrays["original_before"],direction,p["target_norm"])
        scores=(arrays["residuals"]+gate*(arrays["keys"]@actual.T))@head.T
        margins,rivals=mathematics.winner_margins(scores,arrays["gold"])
        physical.update(predicted_gold_argmax_correct=int(np.sum(scores.argmax(axis=1)==arrays["gold"])),
            maximum_raw_violation=float((required-margins).max()),
            protected_output_norm=float(np.linalg.norm(actual@arrays["protected_keys"].T)))
        if selection is not None:
            outside=np.ones(2048,dtype=bool);outside[selection["selected_indices"]]=False
            if np.any(actual[:,outside]!=0):raise RuntimeError("sparse materialization escaped fixed columns")
        packet=io.save_arrays(directory/"packet.npz",before=arrays["original_before"],after=after)
        prediction=io.save_arrays(directory/"prediction.npz",margins=margins,winners=scores.argmax(axis=1))
        row=dict(name=name,physical=physical,packet=packet,prediction=prediction,
                 selection=selection,solver=solver,FIT_used=True,DEV_used_for_selection=False)
        io.write_new(directory/"physical.json",row);arms.append(row)
        print("[COMPARE_CPU_ARM]"+json.dumps(dict(name=name,norm=physical["actual_norm"],
            correct=physical["predicted_gold_argmax_correct"],changed=physical["changed"])),flush=True)

    protected_direction=None
    for row in parent["arms"]:
        budget.check()
        packet=io.load_arrays(io.ROOT/row["packet"]["path"])
        direction=packet["after"].astype(np.float64)-packet["before"].astype(np.float64)
        old=io.read(io.ROOT/row["solver"]["path"])
        dual_lower=old["history"][-1]["dual"]["dual_objective"]
        after,repaired=comparison.repair_ray(arrays["original_before"],direction,head,
            arrays["residuals"],arrays["keys"],arrays["gold"],gate,required,dual_lower,check=budget.check)
        if after is not None:
            repaired["packet"]=io.save_arrays(SOLVE/(row["protection"]+"_ray_packet.npz"),
                before=arrays["original_before"],after=after)
        repaired["source_arm"]=row["name"]
        repairs.append(repaired)
        io.write_new(SOLVE/(row["protection"]+"_ray_report.json"),repaired)
        save_arm(row["protection"]+"_MATCHED_NET",direction)
        if row["protection"]=="NORMAL7_FULL_PREFIX":protected_direction=direction
    if protected_direction is None:raise ValueError("closed normal7 protected direction required")
    for count in p["counts"]:
        for seed in [None,*p["random_seeds"]]:
            budget.check()
            selected,selection=comparison.column_selection(protected_direction,arrays["protected_keys"],count,seed=seed)
            name=("SCORE"if seed is None else "RANDOM"+str(seed))+"_"+str(count)+"_MATCHED_NET"
            reduced,result=mathematics.solve_winners(head,arrays["residuals"],arrays["keys"][:,selected],
                arrays["gold"],gate,required,protected=arrays["protected_keys"][:,selected],
                rounds=32,max_iter=5000,tolerance=1e-5,check=budget.check)
            solver_pin=io.write_new(SOLVE/(name+"_solver.json"),result)
            io.write_new(SOLVE/(name+"_selection.json"),selection)
            if not np.isfinite(reduced).all()or np.linalg.norm(reduced)<=0:
                rejected.append(dict(name=name,reason=result["status"],selection=selection,solver=solver_pin))
                continue
            full=np.zeros_like(arrays["original_before"],dtype=np.float64)
            full[:,selected]=reduced
            save_arm(name,full,selection=selection,solver=solver_pin)
    if len(arms)>p["maximum_native_arms"]or torch.cuda.is_initialized():raise RuntimeError("CPU comparison scope violation")
    report=dict(schema=p["schema"],status="MATCHED_NET_CPU_COMPLETE",arms=arms,ray_repairs=repairs,
        rejected=rejected,maximum_norm_relative_error=max(a["physical"]["relative_norm_error"]for a in arms),
        source_profile_sha256=io.sha(PROFILE),wall_seconds=time.monotonic()-started,
        model_forwards=0,new_generations=0,optimizer_updates=0,checkpoint_writes=0)
    io.write_new(SOLVE/"report.json",report)
    print("[COMPARE_CPU_END]"+json.dumps(dict(arms=len(arms),rejected=len(rejected),
        wall_seconds=report["wall_seconds"])),flush=True)


def actual():
    p=verify();budget=limits.Budget(p["native_max_seconds"]);budget.check(admission=True)
    if ACTUAL.exists():raise FileExistsError("preserve native comparison")
    cpu=io.read(SOLVE/"report.json")
    if cpu["status"]!="MATCHED_NET_CPU_COMPLETE"or len(cpu["arms"])>10:raise ValueError("closed fixed CPU arms required")
    ACTUAL.mkdir();started=time.monotonic()
    capture,arrays,head=study.captured()
    parent,fits,packed,guards,dev,baseline,refs=study.source()
    data=io.read(io.OLD/"data.json")
    report=dict(schema=p["schema"],status="STARTED",arms=[],source_profile_sha256=io.sha(PROFILE),
        CPU_report_sha256=io.sha(SOLVE/"report.json"),entry_resources=cleanup_owner.resources(),
        optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,final_or_official_used=False)
    active=model=adapter=module=delta_native=None;failure=None
    try:
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with manual.selected_runtime(manual.resolve_model(p["model"]))as active:
            try:
                model=active["model"];module,gate=study.module_and_structure(active)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise ValueError("original core differs")
                adapter=TinyAdapter(active,fits,data["calibration_questions"],budget=budget)
                preparation_forwards=adapter.counts["model_forwards"]
                canary=adapter.generate(fits[0],max_new=p["max_new"],variant="ORIGINAL_CANARY")
                if canary["generation"]["generated_ids"]!=baseline[fits[0]["id"]]["generation"]["generated_ids"]:
                    raise ValueError("original greedy canary differs")
                for arm in cpu["arms"]:
                    budget.check();directory=ACTUAL/arm["name"];directory.mkdir()
                    packet=io.load_arrays(io.ROOT/arm["packet"]["path"])
                    if io.sha(io.ROOT/arm["packet"]["path"])!=arm["packet"]["sha256"]or not np.array_equal(packet["before"],module.weight.detach().cpu().numpy()):
                        raise ValueError("native packet source differs")
                    delta_native=torch.from_numpy(packet["after"]-packet["before"]).to(module.weight)
                    writer=ShardWriter(directory,"answers",limit=2_000_000)
                    offset=0;cells=[];pins=[];maximum=0.;mismatches=0;before_counts=dict(adapter.counts)
                    with edits.edit(model,active["route"],[("mlp:13",delta_native)])as proof:
                        physical=module.weight.detach().cpu().double().numpy()-packet["before"].astype(np.float64)
                        with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                            for row in packed:
                                budget.check();saved,native=study.observe(active,module,row)
                                size=len(row["targets"]);keys=arrays["keys"][offset:offset+size]
                                if not np.array_equal(saved["keys"],keys):raise RuntimeError("native same-prefix key differs")
                                residual=arrays["residuals"][offset:offset+size]+gate*(keys@physical.T)
                                rms=np.sqrt(np.mean(residual**2,axis=1)+capture["norm_eps"])
                                predicted=residual@head.T/rms[:,None]
                                maximum=max(maximum,float(np.max(np.abs(predicted-native))))
                                mismatches+=int(np.sum(predicted.argmax(axis=1)!=native.argmax(axis=1)))
                                gold=np.asarray(row["targets"])
                                cells.append(dict(id=row["id"],all_canonical_argmax_correct=bool(np.all(native.argmax(axis=1)==gold)),
                                    content_correct=int(np.sum(native[:-1].argmax(axis=1)==gold[:-1])),content_total=size-1,
                                    EOT_correct=bool(native[-1].argmax()==gold[-1])))
                                pins.append(io.save_arrays(directory/("tf_"+str(offset).zfill(3)+".npz"),
                                    native_logits=native,predicted_logits=predicted.astype(np.float32)))
                                offset+=size
                            if mismatches or maximum>p["native_logit_tolerance"]:raise RuntimeError("native predicted winner/logit mismatch")
                            for row in fits+dev+guards:
                                answer=adapter.generate(row,max_new=p["max_new"],variant=arm["name"])
                                answer["baseline_answer"]=baseline[row["id"]]["answer"]
                                answer["baseline_exact"]=baseline[row["id"]]["exact"]
                                writer.append(answer)
                    manifest=writer.close(lineage=dict(source_profile=io.sha(PROFILE),packet=arm["packet"],
                        FIT_used=True,DEV_previously_exposed=True))
                    generated=io.closed_answers(directory,manifest)
                    summaries={}
                    for name,rows in (("FIT",fits),("DEV",dev),("GUARD",guards)):
                        summaries[name]=dict(rows=len(rows),exact=sum(generated[r["id"]]["exact"]for r in rows),
                            baseline_exact=sum(bool(baseline[r["id"]]["exact"])for r in rows),
                            corrected=sum(not baseline[r["id"]]["exact"]and generated[r["id"]]["exact"]for r in rows),
                            harmed=sum(baseline[r["id"]]["exact"]and not generated[r["id"]]["exact"]for r in rows))
                    receipt=dict(name=arm["name"],physical=arm["physical"],native_actual_norm=float(np.linalg.norm(physical)),
                        requested_after_bitexact=bool(np.array_equal(packet["after"],packet["before"].astype(np.float64)+physical)),
                        replay=proof,maximum_logit_error=maximum,argmax_mismatches=mismatches,
                        teacher_forcing=cells,TF_packets=pins,summaries=summaries,answers_manifest=manifest,
                        counts={k:adapter.counts[k]-before_counts[k]for k in before_counts})
                    io.write_new(directory/"report.json",receipt);report["arms"].append(receipt)
                    delta_native=None
                    print("[COMPARE_NATIVE_ARM]"+json.dumps(dict(name=arm["name"],summaries=summaries,
                        norm=receipt["native_actual_norm"],logit_error=maximum)),flush=True)
                report.update(status="MATCHED_NET_NATIVE_COMPLETE",counts=dict(adapter.counts),
                    preparation_reference_forwards=preparation_forwards,original_core_restored=True,
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise RuntimeError("model not restored")
                adapter.close();adapter=None;module=model=None
            finally:
                if adapter is not None:adapter.close()
                adapter=module=model=None
        active=None
    except BaseException as error:
        failure=str(error);report.update(status="MATCHED_NET_NATIVE_ERROR",error=failure,traceback=traceback.format_exc())
        error.__traceback__=None
    finally:
        if adapter is not None:adapter.close()
        active=model=adapter=module=delta_native=None;gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:
            failure=failure or str(cleanup_error)
            report.update(status="MATCHED_NET_NATIVE_CLEANUP_ERROR",error=failure)
        report["wall_seconds"]=time.monotonic()-started;io.write_new(ACTUAL/"report.json",report)
        print("[COMPARE_NATIVE_END]"+json.dumps({k:report.get(k)for k in(
            "status","wall_seconds","cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}),flush=True)
    if failure is not None:raise RuntimeError("preserved native comparison failure: "+failure)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("preflight","prepare","check","solve","actual"));phase=parser.parse_args().phase
    if phase=="preflight":
        study.verify();limits.Budget(1800).check(admission=True)
        if io.read(study.VALIDATE/"report.json")["status"]!="WINNER_NATIVE_VALIDATION_COMPLETE":
            raise ValueError("closed original comparison required")
        if torch.cuda.is_initialized():raise RuntimeError("CPU preflight initialized CUDA")
        print("[COMPARE_PREFLIGHT]closed D capture/answers;new source;model0",flush=True)
    elif phase=="prepare":prepare()
    elif phase=="check":verify();print("[COMPARE_CHECK]immutable sources;model0",flush=True)
    elif phase=="solve":
        try:solve()
        except BaseException as error:
            if SOLVE.exists()and not(SOLVE/"report.json").exists():
                io.write_new(SOLVE/"report.json",dict(status="MATCHED_NET_CPU_ERROR",error=str(error),
                    traceback=traceback.format_exc(),CUDA_initialized=torch.cuda.is_initialized()))
            raise
    else:actual()


if __name__=="__main__":main()
