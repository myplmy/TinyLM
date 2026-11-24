"""All14 matched single-layer proposals: predict full-vocab endpoint transfer."""
import argparse
import gc
import json
import time
import traceback
import unittest
import numpy as np
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import p108e_io as native
from scripts import p108e_endpoint_prediction as mathematics
from scripts import p108e_replay as replay
from scripts import p108e_evaluation as panel_owner
from scripts import p108e_policy as packet_owner
from scripts import diag_p108e_evaluate as replies
from scripts import diag_p108e_official as resource_owner
from scripts import p108d_compare as norm_owner
from scripts import diag_p108c_scope as archive
from scripts import p108_weight_space as identity
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p108b_tinylm import TinyAdapter
from scripts.p106b_shards import ShardWriter

BASE=native.BASE/"endpoint_predict_v1"
PROFILE=BASE/"profile.json"
PREDICTORS=("CURRENT_RIVAL_LINEAR","ENDPOINT_LINEAR_003","ENDPOINT_LINEAR_001","ENDPOINT_QUADRATIC_003")
CODE=tuple(sorted(set(replies.CODE)|{
    "scripts/diag_p108e_endpoint.py","scripts/p108e_endpoint_prediction.py",
    "scripts/test_p108e_endpoint_prediction.py","scripts/diag_p108e_official.py","scripts/p108d_compare.py"}))


def inputs():
    p=replies.verify();common=archive.read(native.GEOMETRY/"report.json")
    source=native.BASE/"policies/ADAPT_ONE/round0/PREDICTIONS_BEFORE_NATIVE_PROBES.json"
    original_proposals=archive.read(source)["all_layer_proposals"]
    if len(original_proposals)!=14 or {r["layer"]for r in original_proposals}!=set(range(14)):
        raise ValueError("all14 already-closed original proposals required")
    refs={replies.PROFILE,native.GEOMETRY/"report.json",source,replies.BASE/"data.json"}
    refs.update(native.ROOT/r["coordinate_pin"]["path"]for r in original_proposals)
    refs.update(native.ROOT/common[key]["path"]for key in ("baseline_endpoint","guard_logits","original_logits_reused"))
    for row in common["layers"]:
        refs.update(native.ROOT/row[key]["path"]for key in ("basis","observed","reduced_planes"))
    return p,common,sorted(original_proposals,key=lambda r:r["layer"]),refs


def prepare():
    resource_owner.Budget(1800).check(admission=True)
    if BASE.exists():raise FileExistsError("preserve endpoint predictor namespace")
    suite=unittest.defaultTestLoader.loadTestsFromName("scripts.test_p108e_endpoint_prediction")
    tested=unittest.TextTestRunner(verbosity=2).run(suite)
    if not tested.wasSuccessful()or tested.testsRun!=4:raise RuntimeError("four endpoint/physical-step/tie contracts required")
    p,common,proposals,refs=inputs();BASE.mkdir()
    with(BASE/"initial_plan.md").open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    archive.write_new(PROFILE,dict(schema="P108E_ALL14_ENDPOINT_PREDICTOR_V1",authority_directive=142,
        authority_end=native.time_owner.AUTHORITY_END.isoformat(),cleanup_seconds=native.time_owner.CLEANUP_SECONDS,
        model=p["model"],origin=p["origin"],CPU_contracts=tested.testsRun,
        sources={name:archive.sha(native.ROOT/name)for name in CODE},
        references={str(path.relative_to(native.ROOT)):archive.sha(path)for path in sorted(refs)},
        initial_plan_sha256=archive.sha(BASE/"initial_plan.md"),layers=list(range(14)),
        common_net=native.COMMON_BUDGET,norm_rtol=2e-5,epsilons=[.001,.003],
        primary_predictor="ENDPOINT_LINEAR_003",predictors=list(PREDICTORS),
        hinge_tie_resolution=1e-5,native_logit_tolerance=.002,guard_logit_tolerance=.002,
        max_seconds=1800,maximum_free_answer_states=2,free_calls_per_state=199,
        selections="ACTUAL_FIT_BEST_UNION_PREDECLARED_PRIMARY_PREDICTOR_BEST",
        all_predictions_frozen_before_full_step=True,official_or_DEV_labels_for_selection=False,
        new_QP_solves=0,new_VJP_calls=0,optimizer_updates=0,checkpoint_writes=0,
        original_14_proposal_coordinates_reused=True,quality_adoption=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU endpoint admission initialized CUDA")
    print("[ENDPOINT_PREPARED]four CPU contracts;all14 fixed directions/sameNET;no model",flush=True)


def verify():
    p=archive.read(PROFILE);replies.verify()
    if(p["authority_directive"]!=142 or p["authority_end"]!=native.time_owner.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=native.time_owner.CLEANUP_SECONDS
       or p["initial_plan_sha256"]!=archive.sha(BASE/"initial_plan.md")):
        raise ValueError("exact endpoint authority/initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if archive.sha(native.ROOT/name)!=digest:raise ValueError("endpoint input changed: "+name)
    return p


def endpoints(active,physical,rows,budget):
    residuals=[];logits=[]
    for row in rows:
        budget.check();observed=[]
        def retain(_module,args):observed.append(args[0][0,row["start"]:].detach().cpu().numpy().copy())
        hook=active["model"].norm_f.register_forward_pre_hook(retain)
        try:raw,_=native.native_forward(active,physical,row)
        finally:hook.remove()
        if len(observed)!=1:raise RuntimeError("one native final residual visit required")
        residuals.append(observed[0]);logits.append(raw.detach().cpu().numpy().copy());raw=None
    return np.concatenate(residuals),np.concatenate(logits)


def head(active,residuals,packed,counts):
    values=[];cursor=0;model=active["model"];device=model.norm_f_scale.device
    for row in packed:
        size=len(row["targets"])
        x=torch.from_numpy(np.asarray(residuals[cursor:cursor+size],dtype=np.float32)).to(device)[None]
        out=model._head_logits(model.norm_f(x)*model.norm_f_scale)[0]
        values.append(out.detach().cpu().numpy().copy());counts["head_only_calls"]+=1
        cursor+=size;x=out=None
    if cursor!=len(residuals):raise ValueError("complete same target windows required")
    return np.concatenate(values)


def top_packet(path,logits,gold):
    order=np.argsort(logits,axis=1)[:,-8:][:,::-1]
    return archive.save_arrays(path,ids=order,logits=np.take_along_axis(logits,order,axis=1),
        gold_logits=logits[np.arange(len(gold)),gold],winners=logits.argmax(axis=1))


def actual():
    p=verify();budget=resource_owner.Budget(p["max_seconds"]);budget.check(admission=True)
    out=BASE/"actual"
    if out.exists():raise FileExistsError("preserve previous endpoint run")
    out.mkdir();started=time.monotonic();parent,common,proposals,_=inputs()
    _,packed,singles,dialogs,baseline,_,_,_=replies.sources()
    geometry=archive.read(native.PROFILE);guard_packed=geometry["guard_packed"]
    bases,blocks,features,original_logits,guard_logits=replies.policy.load_initial(common)
    r0=features["endpoint"];layout=native.target_indices(packed);gold=layout["gold"]
    _,original_margin,original_rivals,_=native.score_logits(original_logits,packed)
    counts=dict(model_forwards=0,head_only_calls=0,new_generated_answers=0,new_VJP_calls=0)
    report=dict(schema=p["schema"],status="STARTED",candidates=[],actual_points=[],generated_states=[],counts=counts,
        source_profile_sha256=archive.sha(PROFILE),entry_resources=cleanup_owner.resources(),
        optimizer_updates=0,checkpoint_writes=0,official_or_DEV_labels_used_for_selection=False)
    active=model=physical=adapter=after=counter=None;failure=None;writer=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with manual.selected_runtime(manual.resolve_model(p["model"]))as active:
            try:
                model=active["model"];physical=native.modules(active)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise ValueError("original core differs")
                original={i:m.weight.detach().cpu().numpy().copy()for i,m in physical.items()}
                def count_forward(_module,_args):counts["model_forwards"]+=1
                counter=model.register_forward_pre_hook(count_forward);torch.cuda.reset_peak_memory_stats()
                with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                    rr,gg=endpoints(active,physical,packed[:1],budget)
                    if not np.array_equal(rr,r0[:len(rr)])or not np.array_equal(gg,original_logits[:len(gg)]):
                        raise RuntimeError("native original endpoint/logit canary differs")
                    rr=gg=None
                    composed=head(active,r0,packed,counts)
                    error=float(np.max(np.abs(composed-original_logits)))
                    if error>p["native_logit_tolerance"]or np.any(composed.argmax(1)!=original_logits.argmax(1)):
                        raise RuntimeError("actual final norm/head assembly differs")
                    report["head_canary_maximum_error"]=error;composed=None
                    candidates=[];all_predictions=[]
                    for proposal in proposals:
                        budget.check();layer=proposal["layer"];directory=out/("layer"+str(layer).zfill(2));directory.mkdir()
                        coords=replies.packet(proposal["coordinate_pin"])
                        if any(np.any(coords["theta"+str(i).zfill(2)]!=0)for i in range(14)if i!=layer):
                            raise ValueError("original one-layer proposal changed another coordinate owner")
                        theta=coords["theta"+str(layer).zfill(2)]
                        ideal=replies.policy.mathematics.reconstruct(theta,bases[layer]["left"],bases[layer]["right"])
                        final,delta,matching=norm_owner.match_norm(original[layer],ideal,native.COMMON_BUDGET)
                        candidates.append(dict(layer=layer,after=final,delta=delta,theta=theta*matching["scalar"],
                            matching=matching,directory=directory))
                        report["candidates"].append(dict(layer=layer,matching=matching,
                            after_sha256=identity.tensor_sha(torch.from_numpy(final)),coordinate_source=proposal["coordinate_pin"]))
                    archive.write_new(out/"ALL14_STATES_BEFORE_FD.json",dict(candidates=report["candidates"],
                        source_profile_sha256=archive.sha(PROFILE),no_native_full_step_observed=True))
                    for candidate in candidates:
                        budget.check();layer=candidate["layer"];directory=candidate["directory"];fd={};fd_meta=[]
                        for epsilon in p["epsilons"]:
                            observed={};step={}
                            for sign in (1,-1):
                                small=(original[layer].astype(np.float64)+sign*epsilon*candidate["delta"]).astype(np.float32)
                                after={i:original[i]for i in range(14)};after[layer]=small
                                step[sign]=mathematics.physical_coordinate(original[layer],small,candidate["delta"])
                                with replay.install_after(active,physical,after):
                                    observed[sign],unused=endpoints(active,physical,packed,budget)
                                unused=None
                            d,q=mathematics.secants(r0,observed[1],observed[-1],step[1]["scalar"],step[-1]["scalar"])
                            pin=archive.save_arrays(directory/("fd_"+str(int(epsilon*1000)).zfill(3)+".npz"),
                                plus=observed[1],minus=observed[-1])
                            fd[epsilon]=dict(d=d,q=q)
                            fd_meta.append(dict(epsilon=epsilon,plus=step[1],minus=step[-1],packet=pin))
                        expected={"CURRENT_RIVAL_LINEAR":original_margin+blocks[layer]@candidate["theta"]}
                        predicted_endpoints={"ENDPOINT_LINEAR_003":r0+fd[.003]["d"],
                            "ENDPOINT_LINEAR_001":r0+fd[.001]["d"],
                            "ENDPOINT_QUADRATIC_003":r0+fd[.003]["d"]+fd[.003]["q"]}
                        pred_rows=[]
                        for name in PREDICTORS:
                            if name=="CURRENT_RIVAL_LINEAR":
                                margins=expected[name];score=replies.policy.mathematics.score(margins,layout["offsets"]);top=None
                            else:
                                logits=head(active,predicted_endpoints[name],packed,counts)
                                score,margins,_,_=native.score_logits(logits,packed)
                                top=top_packet(directory/(name+"_top8.npz"),logits,gold);logits=None
                            pred_rows.append(dict(predictor=name,score=score,margins=margins.tolist(),top8=top))
                        candidate.update(fd=fd,predicted=pred_rows,predicted_endpoints=predicted_endpoints,FD=fd_meta)
                        all_predictions.append(dict(layer=layer,matching=candidate["matching"],FD=fd_meta,predictions=pred_rows,
                            linear_epsilon_relative_disagreement=float(np.linalg.norm(fd[.001]["d"]-fd[.003]["d"])/max(np.linalg.norm(fd[.003]["d"]),1e-30)),
                            quadratic_epsilon_relative_disagreement=float(np.linalg.norm(fd[.001]["q"]-fd[.003]["q"])/max(np.linalg.norm(fd[.003]["q"]),1e-30))))
                        print("[ENDPOINT_PREDICTIONS_CLOSED]layer="+str(layer),flush=True)
                    selections={}
                    for name in PREDICTORS:
                        rows=[dict(layer=r["layer"],score=next(t["score"]for t in r["predictions"]if t["predictor"]==name))for r in all_predictions]
                        selections[name]=mathematics.choose(rows,resolution=p["hinge_tie_resolution"])["layer"]
                    archive.write_new(out/"ALL14_PREDICTIONS_BEFORE_FULL_STEP.json",dict(rows=all_predictions,
                        selected_layers=selections,primary_predictor=p["primary_predictor"],full_step_observed=False))
                    for candidate in candidates:
                        budget.check();layer=candidate["layer"];directory=candidate["directory"]
                        after={i:original[i]for i in range(14)};after[layer]=candidate["after"]
                        with replay.install_after(active,physical,after):
                            residual,logits=endpoints(active,physical,packed,budget)
                            normal,_=native.collect(active,physical,guard_packed,budget,features=None)
                        score,margin,rivals,winners=native.score_logits(logits,packed)
                        normal_error=float(np.max(np.abs(normal-guard_logits)))
                        guard_mismatch=int(np.sum(normal.argmax(1)!=guard_logits.argmax(1)))
                        norms=float(np.linalg.norm(residual.astype(np.float64)-r0))
                        comparisons=[]
                        for pred in candidate["predicted"]:
                            name=pred["predictor"];err=np.asarray(pred["margins"])-margin
                            comparisons.append(dict(predictor=name,margin_RMSE=float(np.sqrt(np.mean(err**2))),
                                gold_question_absolute_error=abs(pred["score"]["questions_all_gold"]-score["questions_all_gold"]),
                                endpoint_relative_error=None if name=="CURRENT_RIVAL_LINEAR"else
                                float(np.linalg.norm(candidate["predicted_endpoints"][name]-residual)/max(norms,1e-30))))
                        point=dict(layer=layer,score=score,matching=candidate["matching"],comparisons=comparisons,
                            native_top8=top_packet(directory/"actual_top8.npz",logits,gold),
                            native_endpoint=archive.save_arrays(directory/"actual_endpoint.npz",values=residual),
                            guard_argmax_mismatches=guard_mismatch,guard_logit_maximum_error=normal_error,
                            eligible=guard_mismatch==0 and normal_error<=p["guard_logit_tolerance"],
                            original_rival_switches=int(np.sum(rivals!=original_rivals)),
                            after_sha256=identity.tensor_sha(torch.from_numpy(candidate["after"])))
                        archive.write_new(directory/"report.json",point);report["actual_points"].append(point)
                        print("[ENDPOINT_FULL_STEP]"+json.dumps(dict(layer=layer,score=score,eligible=point["eligible"])),flush=True)
                    eligible=[r for r in report["actual_points"]if r["eligible"]]
                    if not eligible:raise RuntimeError("no protected physically eligible actual proposal")
                    actual_best=mathematics.choose(eligible,resolution=p["hinge_tie_resolution"])["layer"]
                    chosen=sorted({actual_best,selections[p["primary_predictor"]]})
                    if len(chosen)>p["maximum_free_answer_states"]:raise RuntimeError("too many selected free-answer states")
                    decision=dict(actual_best=actual_best,predicted_best=selections,free_answer_layers=chosen,
                        selected_before_any_new_free_reply=True,official_or_DEV_used=False,
                        top1_actual_question_regret={name:max(r["score"]["questions_all_gold"]for r in eligible)-
                            next(r["score"]["questions_all_gold"]for r in report["actual_points"]if r["layer"]==layer)
                            for name,layer in selections.items()})
                    archive.write_new(out/"FROZEN_FREE_ANSWER_SELECTION.json",decision);report["decision"]=decision
                    fits=[r for r in singles if r["evaluation_panel"]=="FIT"]
                    calibration=archive.read(archive.OLD/"data.json")["calibration_questions"]
                    adapter=TinyAdapter(active,fits,calibration,budget=budget)
                    report["calibration_reference_forwards"]=adapter.counts["model_forwards"]
                    for layer in chosen:
                        budget.check();point=next(r for r in report["actual_points"]if r["layer"]==layer)
                        if not point["eligible"]:
                            report["generated_states"].append(dict(layer=layer,status="NOT_RUN_PROTECTION_GATE"));continue
                        candidate=candidates[layer];directory=out/("chosen_layer"+str(layer).zfill(2));directory.mkdir()
                        after={i:original[i]for i in range(14)};after[layer]=candidate["after"]
                        lossless=archive.save_arrays(directory/"after_xor.npz",xor=packet_owner.after_xor(original[layer],after[layer]))
                        writer=ShardWriter(directory,"answers",limit=2_000_000);records=[]
                        with replay.install_after(active,physical,after)as proof:
                            edited_core=manual.state_fingerprint(model)
                            native_logits,_=native.collect(active,physical,packed,budget,features=None)
                            tf_pin=archive.save_arrays(directory/"native_TF.npz",logits=native_logits)
                            for row in singles:
                                answer=adapter.generate(row,max_new=row["max_new"],variant="ENDPOINT_LAYER"+str(layer))
                                answer.update(baseline_answer=baseline[row["id"]]["answer"],mode="SINGLE")
                                writer.append(answer);records.append(answer)
                            for dialog in dialogs:
                                history=[]
                                for row in dialog:
                                    answer=adapter.generate(row,max_new=row["max_new"],variant="ENDPOINT_LAYER"+str(layer),history=history)
                                    answer.update(baseline_answer=baseline[row["id"]]["answer"],mode="OWN_HISTORY")
                                    writer.append(answer);records.append(answer)
                                    history=panel_owner.extend_history(history,row,answer["answer"])
                        manifest=writer.close(lineage=dict(source_profile=archive.sha(PROFILE),
                            edited_core_sha256=edited_core,selection_before_replies=True,training_allowed=False));writer=None
                        summaries={family:dict(rows=sum(r["evaluation_panel"]==family for r in records),
                            exact=sum(r["evaluation_panel"]==family and r["exact"]is True for r in records),
                            scored=sum(r["evaluation_panel"]==family and r["exact"]is not None for r in records))
                            for family in sorted({r["evaluation_panel"]for r in records})}
                        closed=dict(layer=layer,status="ENDPOINT_CHOSEN_ACTUAL_REPLIES_COMPLETE",summaries=summaries,
                            after_xor=lossless,original_weight_sha256=common["layers"][layer]["original_weight_sha256"],
                            after_weight_sha256=point["after_sha256"],edited_core_sha256=edited_core,
                            native_TF=tf_pin,replay=proof,answers_manifest=manifest)
                        archive.write_new(directory/"report.json",closed);report["generated_states"].append(closed)
                        counts["new_generated_answers"]+=len(records)
                        print("[ENDPOINT_CHOSEN_ANSWERS]"+json.dumps(dict(layer=layer,summaries=summaries)),flush=True)
                    report.update(status="ALL14_ENDPOINT_PREDICTION_COMPLETE",original_core_restored=True,
                        peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                        peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                    if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise RuntimeError("original not restored")
                    adapter.close();adapter=None;counter.remove();counter=None;physical=model=None
            finally:
                if counter is not None:counter.remove();counter=None
                if adapter is not None:adapter.close();adapter=None
                physical=model=after=None
        active=None
    except BaseException as error:
        failure=str(error);report.update(status="ALL14_ENDPOINT_PREDICTION_ERROR",error=failure,traceback=traceback.format_exc());error.__traceback__=None
    finally:
        if writer is not None:report["partial_answers_manifest"]=writer.close(lineage=dict(partial=True))
        if adapter is not None:adapter.close()
        active=model=physical=adapter=after=counter=None;gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started;archive.write_new(out/"report.json",report)
    print("[ENDPOINT_END]"+json.dumps(dict(status=report["status"],counts=counts,error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","preflight","check","actual"));args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="preflight":
        resource_owner.Budget(1800).check(admission=True);inputs()
        if torch.cuda.is_initialized():raise RuntimeError("CPU preflight initialized CUDA")
        print("[ENDPOINT_PREFLIGHT]old fourteen coordinates reused;no model",flush=True)
    elif args.action=="check":verify();print("[ENDPOINT_CHECK]source/authority/fixed FD and sameNET",flush=True)
    else:actual()


if __name__=="__main__":main()
