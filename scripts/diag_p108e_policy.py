"""Bounded single/reselected/joint physical edits from native rival geometry."""
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
from scripts import p108e_math as mathematics
from scripts import p108e_policy as selection
from scripts import diag_p108e_geometry as geometry
from scripts import diag_p108c_scope as archive
from scripts import p108_value_edit as autograd_owner
from scripts import p108_weight_space as identity
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner

PROFILE=native.BASE/"policy_profile.json"
CODE=("scripts/diag_p108e_policy.py","scripts/p108e_policy.py","scripts/test_p108e_policy.py")+geometry.CODE
POLICIES=("SINGLE13","ADAPT_ONE","JOINT14")


def prepare():
    native.Budget(1800).check(admission=True);parent=geometry.verify()
    if PROFILE.exists():raise FileExistsError("preserve policy admission")
    completed=archive.read(native.GEOMETRY/"report.json")
    if(completed["status"]!="ALL_LAYER_MARGIN_GEOMETRY_COMPLETE"or completed["FD_failed"]
       or not completed["original_core_restored"]or completed["cuda_allocated_after_bytes"]
       or completed["cuda_reserved_after_bytes"]):raise ValueError("closed all14 native derivative gate required")
    suite=unittest.defaultTestLoader.loadTestsFromName("scripts.test_p108e_policy")
    checked=unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful()or checked.testsRun!=5:raise RuntimeError("five policy/XOR contracts required")
    refs={native.PROFILE,native.GEOMETRY/"report.json",native.GEOMETRY/"native_VJP_details.json"}
    refs.update(native.ROOT/completed[key]["path"]for key in ("guard_logits","baseline_endpoint"))
    for layer in completed["layers"]:
        refs.update(native.ROOT/layer[key]["path"]for key in ("basis","observed","reduced_planes"))
    initial=native.BASE/"policy_initial_plan.md"
    with initial.open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    archive.write_new(PROFILE,dict(schema="P108E_BOUNDED_MARGIN_POLICY_V1",authority_directive=142,
        authority_end=native.time_owner.AUTHORITY_END.isoformat(),cleanup_seconds=native.time_owner.CLEANUP_SECONDS,
        model=parent["model"],origin=parent["origin"],initial_plan_sha256=archive.sha(initial),
        sources={name:archive.sha(native.ROOT/name)for name in sorted(set(CODE))},
        references={str(path.relative_to(native.ROOT)):archive.sha(path)for path in sorted(refs)},
        CPU_contracts=checked.testsRun,policies=list(POLICIES),rounds=4,probe_slots_per_round=9,
        grid=[1.,.875,.75,.625,.5,.375,.25,.125,0.],adaptive_grid=[1.,.5,.25],
        top_layers=3,common_budget=native.COMMON_BUDGET,actual_norm_rtol=2e-5,
        desired_margin=.10,hinge_resolution=1e-5,guard_logit_tolerance=.002,
        policy_max_seconds=1800,dual_cap=1e4,dual_max_iter=5000,
        criterion="FULL_GOLD_QUESTIONS_THEN_FULL_VOCAB_HINGE_THEN_PHYSICAL_NORM",
        final_or_official_used=False,DEV_used_for_selection=False,new_generated_answers=0,
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,
        original_geometry_charged_once_separately=True,
        repeated_coefficient_states_reuse_in_round_cache=True))
    if torch.cuda.is_initialized():raise RuntimeError("CPU policy preparation initialized CUDA")
    print("[E_POLICY_PREPARED]three policies;four rounds/nine probes;prior geometry reused",flush=True)


def verify():
    geometry.verify();p=archive.read(PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=native.time_owner.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=native.time_owner.CLEANUP_SECONDS
       or p["initial_plan_sha256"]!=archive.sha(native.BASE/"policy_initial_plan.md")):
        raise ValueError("exact policy scope, clock and initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if archive.sha(native.ROOT/name)!=digest:raise ValueError("policy source changed: "+name)
    return p


def load_initial(completed):
    bases=native.load_bases(completed);blocks={};features={}
    for layer in completed["layers"]:
        index=layer["layer"]
        blocks[index]=archive.load_arrays(native.ROOT/layer["reduced_planes"]["path"])["values"]
        observed=archive.load_arrays(native.ROOT/layer["observed"]["path"])
        features[index]=dict(keys=observed["target_keys"],values=observed["original_values"])
    features["endpoint"]=archive.load_arrays(native.ROOT/completed["baseline_endpoint"]["path"])["values"]
    logits=archive.load_arrays(native.ROOT/completed["original_logits_reused"]["path"])["logits"]
    guards=archive.load_arrays(native.ROOT/completed["guard_logits"]["path"])["logits"]
    return bases,blocks,features,logits,guards


def save_features(path,features):
    arrays={"endpoint":features["endpoint"]}
    for layer in range(14):
        for field in ("keys","values"):arrays[field+"_"+str(layer).zfill(2)]=features[layer][field]
    return archive.save_arrays(path,**arrays)


def probe(active,physical,packed,guards,original,bases,coordinates,baseline_guard,budget,counts):
    requested,after,materialized=native.materialized(original,coordinates,bases)
    if materialized["actual_norm"]>native.COMMON_BUDGET*(1+2e-5):raise RuntimeError("physical original-centred budget exceeded")
    before=counts["model_forwards"]
    with native.install(active,physical,requested)as proof:
        for layer,receipt in enumerate(proof):
            if receipt["after_sha256"]!=identity.tensor_sha(torch.from_numpy(after[layer])):
                raise RuntimeError("CPU/native FP32 materialization bits differ")
        with sdpa_kernel(SDPBackend.MATH):
            raw,features=native.collect(active,physical,packed,budget,features="targets")
            normal,_=native.collect(active,physical,guards,budget,features=None)
    score,margin,rivals,winners=native.score_logits(raw,packed)
    metadata=dict(score=score,actual_norm=materialized["actual_norm"],physical=materialized,replay=proof,
        guard_argmax_mismatches=int(np.sum(normal.argmax(axis=1)!=baseline_guard.argmax(axis=1))),
        guard_logit_max_error=float(np.max(np.abs(normal-baseline_guard))),
        model_forwards=counts["model_forwards"]-before,coefficient_signature=selection.signature(coordinates))
    return dict(meta=metadata,logits=raw,guard_logits=normal,features=features,coordinates=coordinates,
                after=after,margins=margin,rivals=rivals,winners=winners)


def explanatory_step(before,after,blocks,gate):
    contributions={};local=[]
    predicted=np.zeros_like(before["margins"])
    for layer in range(14):
        change=after["coordinates"][layer]-before["coordinates"][layer]
        component=blocks[layer]@change;predicted+=component
        contributions[str(layer)]=component.tolist()
        old=before["features"][layer];new=after["features"][layer]
        difference=after["after"][layer].astype(np.float64)-before["after"][layer].astype(np.float64)
        direct=gate[layer]*(old["keys"]@difference.T)
        incoming=gate[layer]*((new["keys"].astype(np.float64)-old["keys"])@after["after"][layer].T)
        observed=gate[layer]*(new["values"].astype(np.float64)-old["values"])
        local.append(dict(layer=layer,direct_parameter_output_norm=float(np.linalg.norm(direct)),
            upstream_input_output_norm=float(np.linalg.norm(incoming)),actual_branch_output_change=float(np.linalg.norm(observed)),
            linear_branch_closure_max_error=float(np.max(np.abs(observed-direct-incoming)))))
    positions=np.arange(len(predicted));gold=native.target_indices(
        archive.read(native.PROFILE)["packed"])["gold"]
    fixed=after["logits"][positions,gold]-after["logits"][positions,before["rivals"]]
    delta_fixed=fixed-before["margins"]
    return dict(per_layer_predicted_margin_change=contributions,
        predicted_total_margin_change=predicted.tolist(),actual_fixed_rival_margin_change=delta_fixed.tolist(),
        nonlinear_fixed_rival_rmse=float(np.sqrt(np.mean((delta_fixed-predicted)**2))),
        actual_new_rival_margin_change=(after["margins"]-before["margins"]).tolist(),
        rival_switches=int(np.sum(after["rivals"]!=before["rivals"])),local_branch_decomposition=local,
        final_residual_change_norm=float(np.linalg.norm(after["features"]["endpoint"].astype(np.float64)-before["features"]["endpoint"])))


def run_policy(name):
    p=verify();parent=geometry.verify();budget=native.Budget(p["policy_max_seconds"]);budget.check(admission=True)
    out=native.BASE/"policies"/name
    if out.exists():raise FileExistsError("preserve completed/partial policy "+name)
    out.mkdir(parents=True);started=time.monotonic();common=archive.read(native.GEOMETRY/"report.json")
    bases,initial_blocks,initial_features,original_logits,guard_logits=load_initial(common)
    packed=parent["packed"];guards=parent["guard_packed"];layout=native.target_indices(packed)
    baseline_score,baseline_margin,baseline_rivals,baseline_winners=native.score_logits(original_logits,packed)
    counts=dict(model_forwards=0,native_VJP_calls=0,actual_probe_calls=0,cached_probe_slots=0,new_generated_answers=0)
    report=dict(schema=p["schema"],status="STARTED",policy=name,rounds=[],counts=counts,
        source_profile_sha256=archive.sha(PROFILE),common_geometry_report_sha256=archive.sha(native.GEOMETRY/"report.json"),
        common_geometry_charged_once=True,entry_resources=cleanup_owner.resources(),
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,final_or_official_used=False,
        gradient_basis_truncation_limits_are_not_global_layer_optima=True)
    active=model=physical=counter=None;failure=None
    try:
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with manual.selected_runtime(manual.resolve_model(p["model"]))as active,autograd_owner.freeze_parameters(active["model"]):
            try:
                model=active["model"];physical=native.modules(active)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise ValueError("original core differs")
                original={layer:module.weight.detach().cpu().numpy().copy()for layer,module in physical.items()}
                for layer in common["layers"]:
                    if identity.tensor_sha(physical[layer["layer"]].weight)!=layer["original_weight_sha256"]:
                        raise ValueError("original physical owner differs")
                def count_forward(_module,_args):counts["model_forwards"]+=1
                counter=model.register_forward_pre_hook(count_forward);torch.cuda.reset_peak_memory_stats()
                with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                    canary,_=native.native_forward(active,physical,packed[0])
                    if not np.array_equal(canary.detach().cpu().numpy(),original_logits[:len(packed[0]["targets"])]):
                        raise RuntimeError("original canonical-window canary differs")
                    canary=None
                zeros={layer:np.zeros(initial_blocks[layer].shape[1])for layer in range(14)}
                current=dict(meta=dict(score=baseline_score,actual_norm=0.,guard_argmax_mismatches=0,
                    guard_logit_max_error=0.,alpha=0.,layer=-1),logits=original_logits,guard_logits=guard_logits,
                    features=initial_features,coordinates=zeros,after=original,margins=baseline_margin,
                    rivals=baseline_rivals,winners=baseline_winners)
                path=0.;gates={layer:float(model.layers[layer].gates[1].detach())for layer in range(14)}
                stop_reason="ROUND_LIMIT"
                for iteration in range(p["rounds"]):
                    budget.check();directory=out/("round"+str(iteration));directory.mkdir()
                    if current["meta"]["score"]["questions_all_gold"]==24 and current["meta"]["score"]["mean_hinge"]<=p["hinge_resolution"]:
                        stop_reason="ALL_CANONICAL_WINNER_CONSTRAINTS_RESOLVED";break
                    if iteration==0:
                        blocks=initial_blocks;details=archive.read(native.GEOMETRY/"native_VJP_details.json")["rows"]
                        geometry_source="REUSED_COMMON_ORIGINAL"
                    else:
                        requested,_,_=native.materialized(original,current["coordinates"],bases)
                        with native.install(active,physical,requested):
                            three,details,recomputed=geometry.native_gradients(active,physical,packed,
                                {layer:bases[layer]["right"]for layer in range(14)},budget,
                                lefts={layer:bases[layer]["left"]for layer in range(14)})
                        counts["native_VJP_calls"]+=sum(row["native_vjp_calls"]for row in details)
                        if not np.array_equal(recomputed,current["logits"]):raise RuntimeError("same current-state derivative logits differ")
                        blocks={layer:three[layer].reshape(62,-1)for layer in range(14)}
                        geometry_source="CURRENT_NATIVE_RELINEARIZATION"
                        archive.write_new(directory/"native_VJP_details.json",dict(rows=details))
                        for layer,matrix in blocks.items():
                            archive.save_arrays(directory/("planes_layer"+str(layer).zfill(2)+".npz"),values=matrix)
                    proposals=[]
                    allowed_sets=([([13],13)]if name=="SINGLE13"else
                                  [([layer],layer)for layer in range(14)]if name=="ADAPT_ONE"else
                                  [(list(range(14)),-1)])
                    for allowed,layer in allowed_sets:
                        candidate,record=mathematics.proposal(blocks,current["coordinates"],current["margins"],allowed,
                            p["common_budget"],desired=p["desired_margin"],dual_cap=p["dual_cap"],max_iter=p["dual_max_iter"])
                        if "predicted_margins"not in record:continue
                        predicted=mathematics.score(np.asarray(record["predicted_margins"]),layout["offsets"])
                        coordinate_pin=archive.save_arrays(directory/("proposal_layer"+str(layer)+".npz"),
                            **{"theta"+str(index).zfill(2):value for index,value in candidate.items()})
                        proposals.append(dict(layer=layer,coordinates=candidate,coordinate_pin=coordinate_pin,
                            QP=record,predicted_score=predicted))
                    if not proposals:stop_reason="NO_LOCAL_CANDIDATE";break
                    proposals.sort(key=lambda item:(-item["predicted_score"]["questions_all_gold"],
                        item["predicted_score"]["mean_hinge"],item["QP"]["coefficient_norm"],item["layer"]))
                    chosen_proposals=proposals[:p["top_layers"]]if name=="ADAPT_ONE"else proposals
                    proposal_receipts=[{k:v for k,v in row.items()if k!="coordinates"}for row in proposals]
                    archive.write_new(directory/"PREDICTIONS_BEFORE_NATIVE_PROBES.json",dict(
                        geometry_source=geometry_source,all_layer_proposals=proposal_receipts,
                        selected_predicted_layers=[row["layer"]for row in chosen_proposals],
                        current_score=current["meta"]["score"],uses_only_current_rival_linearization=True,
                        DEV_or_final_or_official_used=False))
                    cache={selection.signature(current["coordinates"]):current};probes=[];runtimes=[]
                    slots=0
                    for proposal in chosen_proposals:
                        alphas=p["adaptive_grid"]if name=="ADAPT_ONE"else p["grid"]
                        for alpha in alphas:
                            budget.check();slots+=1
                            if slots>p["probe_slots_per_round"]:raise RuntimeError("probe slot budget exceeded")
                            coordinates=selection.mix(current["coordinates"],proposal["coordinates"],alpha)
                            key=selection.signature(coordinates)
                            if key in cache:
                                observed=cache[key];counts["cached_probe_slots"]+=1;cached=True
                            else:
                                observed=probe(active,physical,packed,guards,original,bases,coordinates,guard_logits,budget,counts)
                                counts["actual_probe_calls"]+=1;cache[key]=observed;cached=False
                            metadata=dict(observed["meta"],alpha=alpha,layer=proposal["layer"],cached=cached,
                                          slot=slots,coefficient_signature=key)
                            predicted_margin=current["margins"].copy()
                            for layer in range(14):predicted_margin+=blocks[layer]@(coordinates[layer]-current["coordinates"][layer])
                            indices=np.arange(62);gold=layout["gold"]
                            fixed=observed["logits"][indices,gold]-observed["logits"][indices,current["rivals"]]
                            metadata.update(predicted_current_rival_margin=predicted_margin.tolist(),
                                actual_current_rival_margin=fixed.tolist(),actual_full_vocab_margin=observed["margins"].tolist(),
                                fixed_rival_RMSE=float(np.sqrt(np.mean((fixed-predicted_margin)**2))),
                                rival_switches=int(np.sum(observed["rivals"]!=current["rivals"])))
                            top=np.argpartition(observed["logits"],-8,axis=1)[:,-8:]
                            metadata["top8_packet"]=archive.save_arrays(directory/("probe"+str(slots).zfill(2)+"_top8.npz"),
                                ids=top,logits=np.take_along_axis(observed["logits"],top,axis=1),
                                gold_logits=observed["logits"][indices,gold],winners=observed["winners"])
                            probes.append(metadata);runtimes.append(observed)
                    selected,reason=selection.select(probes,current["meta"],budget=p["common_budget"],
                        hinge_resolution=p["hinge_resolution"],guard_logit_tolerance=p["guard_logit_tolerance"])
                    round_report=dict(round=iteration,geometry_source=geometry_source,probe_slots=slots,probes=probes,
                                      selection_reason=reason,selected=None)
                    if selected is None:
                        archive.write_new(directory/"report.json",round_report);report["rounds"].append(round_report)
                        stop_reason=reason;break
                    index=next(i for i,row in enumerate(probes)if row is selected)
                    chosen=runtimes[index]
                    chosen=dict(chosen,meta=dict(selected))
                    step_path=selection.physical_path(current["after"],chosen["after"]);path+=step_path
                    explanation=explanatory_step(current,chosen,blocks,gates)
                    explanation_pin=archive.write_new(directory/"accepted_transfer.json",explanation)
                    coordinate_pin=archive.save_arrays(directory/"accepted_coordinates.npz",
                        **{"theta"+str(layer).zfill(2):value for layer,value in chosen["coordinates"].items()})
                    features_pin=save_features(directory/"accepted_features.npz",chosen["features"])
                    logits_pin=archive.save_arrays(directory/"accepted_logits.npz",logits=chosen["logits"])
                    normal_pin=archive.save_arrays(directory/"accepted_guard_logits.npz",logits=chosen["guard_logits"])
                    round_report["selected"]=dict(meta=selected,coordinates=coordinate_pin,features=features_pin,
                        logits=logits_pin,normal_logits=normal_pin,transfer=explanation_pin,
                        step_PATH=step_path,cumulative_PATH=path)
                    archive.write_new(directory/"report.json",round_report);report["rounds"].append(round_report)
                    current=chosen
                    print("[E_POLICY_ACCEPTED]"+json.dumps(dict(policy=name,round=iteration,layer=selected["layer"],
                        alpha=selected["alpha"],score=selected["score"],NET=selected["actual_norm"],PATH=path)),flush=True)
                    cache.clear();probes.clear();runtimes.clear()
                final_pin=archive.save_arrays(out/"final_coordinates.npz",
                    **{"theta"+str(layer).zfill(2):value for layer,value in current["coordinates"].items()})
                final_patches=[]
                requested,after,actual_physical=native.materialized(original,current["coordinates"],bases)
                with native.install(active,physical,requested):
                    edited_core=manual.state_fingerprint(model)
                    for layer in range(14):
                        patch=selection.after_xor(original[layer],after[layer])
                        restored=selection.restore_xor(original[layer],patch)
                        if not np.array_equal(restored.view(np.uint32),after[layer].view(np.uint32)):
                            raise RuntimeError("lossless final weight-patch roundtrip failed")
                        if identity.tensor_sha(torch.from_numpy(restored))!=identity.tensor_sha(physical[layer].weight):
                            raise RuntimeError("stored final XOR patch differs from actual native weight bits")
                        final_patches.append(dict(layer=layer,packet=archive.save_arrays(out/("final_after_xor_layer"+str(layer).zfill(2)+".npz"),xor=patch),
                            before_sha256=identity.tensor_sha(torch.from_numpy(original[layer])),
                            after_sha256=identity.tensor_sha(physical[layer].weight)))
                total_changed=sum(row["changed"]for row in actual_physical["layers"])
                report.update(status="BOUNDED_MARGIN_POLICY_COMPLETE",stop_reason=stop_reason,final_score=current["meta"]["score"],
                    final_guard_error=current["meta"]["guard_logit_max_error"],final_coordinates=final_pin,
                    final_physical=actual_physical,cumulative_PATH=path,final_patches=final_patches,
                    edited_core_sha256=edited_core,changed_parameter_values=total_changed,
                    changed_percent_of_model=100*total_changed/common["native_unique_parameter_count"],
                    original_core_restored=True,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise RuntimeError("original core not restored")
                counter.remove();counter=None;physical.clear();physical=model=None
            finally:
                if counter is not None:counter.remove()
                if physical is not None:physical.clear()
                counter=physical=model=None
        active=None
    except BaseException as error:
        failure=str(error);report.update(status="BOUNDED_MARGIN_POLICY_ERROR",error=failure,traceback=traceback.format_exc())
        error.__traceback__=None
    finally:
        if counter is not None:counter.remove()
        if physical is not None:physical.clear()
        active=counter=physical=model=None;gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:
            failure=failure or str(cleanup_error);report.update(status="E_POLICY_CLEANUP_ERROR",error=failure)
        report["wall_seconds"]=time.monotonic()-started;archive.write_new(out/"report.json",report)
        print("[E_POLICY_END]"+json.dumps({key:report.get(key)for key in(
            "policy","status","final_score","counts","wall_seconds","cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}),flush=True)
    if failure is not None:raise RuntimeError("preserved policy failure: "+failure)


def all_policies():
    p=verify();results=[]
    for name in p["policies"]:
        try:run_policy(name);results.append(dict(policy=name,process_result="COMPLETE"))
        except BaseException as error:
            results.append(dict(policy=name,process_result="ERROR",error=str(error)));error.__traceback__=None
    archive.write_new(native.BASE/"policy_batch_report.json",dict(results=results,independent_policies_continued=True))
    if any(row["process_result"]!="COMPLETE"for row in results):raise RuntimeError("one or more independent policies failed")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("preflight","prepare","check","actual"))
    phase=parser.parse_args().phase
    if phase=="preflight":
        geometry.verify();native.Budget(1800).check(admission=True)
        if archive.read(native.GEOMETRY/"report.json")["status"]!="ALL_LAYER_MARGIN_GEOMETRY_COMPLETE":
            raise ValueError("closed native geometry required")
        if torch.cuda.is_initialized():raise RuntimeError("CPU preflight initialized CUDA")
        print("[E_POLICY_PREFLIGHT]closed all14 geometry;model0",flush=True)
    elif phase=="prepare":prepare()
    elif phase=="check":verify();print("[E_POLICY_CHECK]exact bounded source;model0",flush=True)
    else:all_policies()


if __name__=="__main__":main()
