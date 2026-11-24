"""Frozen all-layer native rival geometry; no body/value training or CP export."""
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
from scripts import p108e_calculus as calculus
from scripts import diag_p108c_scope as archive
from scripts import p108_value_edit as autograd_owner
from scripts import p108_weight_space as identity
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner

CODE=("scripts/p108e_io.py","scripts/p108e_math.py","scripts/p108e_calculus.py",
      "scripts/test_p108e_io.py","scripts/test_p108e_math.py","scripts/test_p108e_calculus.py",
      "scripts/diag_p108e_geometry.py","scripts/p108c_limits.py","scripts/p108_wsp_attention.py",
      "scripts/diag_p108d_winner.py","scripts/p108_value_edit.py")


def prepare():
    native.Budget(1800).check(admission=True)
    if native.BASE.exists():raise FileExistsError("preserve new SQP namespace")
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name)for name in (
        "scripts.test_p108e_math","scripts.test_p108e_calculus","scripts.test_p108e_io"))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful()or result.testsRun!=11:raise RuntimeError("eleven independent CPU contracts required")
    parent,fits,packed,guards,guard_packed,dev,baseline,refs=native.source()
    refs.update({native.origin.PROFILE,native.origin.CAPTURE/"report.json",
                 native.origin.VALIDATE/"report.json",archive.BASE/"margin_actual_v1/ORIGINAL_logits.npz"})
    native.BASE.mkdir()
    with (native.BASE/"initial_plan.md").open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    archive.write_new(native.PROFILE,dict(schema="P108E_NATIVE_MARGIN_GEOMETRY_V1",authority_directive=142,
        authority_end=native.time_owner.AUTHORITY_END.isoformat(),cleanup_seconds=native.time_owner.CLEANUP_SECONDS,
        model=parent["origin"]["name"],origin=parent["origin"],packed=packed,guard_packed=guard_packed,
        sources={name:archive.sha(native.ROOT/name)for name in CODE},
        references={str(path.relative_to(native.ROOT)):archive.sha(path)for path in sorted(refs)},
        initial_plan_sha256=archive.sha(native.BASE/"initial_plan.md"),CPU_contracts=result.testsRun,
        geometry_max_seconds=1800,common_budget=native.COMMON_BUDGET,
        rank_rtol=1e-8,prompt_extra=16,left_energy=.9999,left_rank_cap=128,
        FD_epsilons=[.001,.003],FD_absolute_tolerance=.02,FD_relative_tolerance=.05,
        native_precision="FP32_MATH_TF32_OFF",max_owned_artifact_bytes=1_900_000_000,
        minimum_filesystem_free_bytes=5_000_000_000,body_optimizer_updates=0,value_optimizer_updates=0,
        checkpoint_writes=0,final_or_official_used=False,FIT_for_edit=True,prior_DEV_not_blind=True))
    if torch.cuda.is_initialized():raise RuntimeError("CPU SQP preparation initialized CUDA")
    print("[E_PREPARED]11 CPU contracts;all14 native geometry;62 margin VJP;no model",flush=True)


def verify():
    p=archive.read(native.PROFILE)
    if(p["authority_directive"]!=142 or p["authority_end"]!=native.time_owner.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=native.time_owner.CLEANUP_SECONDS or
       p["initial_plan_sha256"]!=archive.sha(native.BASE/"initial_plan.md")):
        raise ValueError("exact E authority and frozen initial plan required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if archive.sha(native.ROOT/name)!=digest:raise ValueError("E source changed: "+name)
    return p


def native_gradients(active,physical,rows,rights,budget,*,lefts=None):
    blocks={layer:[]for layer in physical};details=[];raw=[]
    weights={layer:module.weight for layer,module in physical.items()}
    for row in rows:
        budget.check();autograd_owner.refresh_autograd_views(active["model"],active["route"])
        with torch.enable_grad(),sdpa_kernel(SDPBackend.MATH):
            logits,_=native.native_forward(active,physical,row)
            raw.append(logits.detach().cpu().numpy().copy())
            projected,record=calculus.projected_vjps(logits,row["targets"],weights,rights,lefts=lefts)
        for layer in physical:blocks[layer].append(projected[layer])
        details.append(dict(id=row["id"],**record));logits=None
        print("[E_VJP_PROGRESS]"+row["id"],flush=True)
    return {layer:np.concatenate(values)for layer,values in blocks.items()},details,np.concatenate(raw)


def actual():
    p=verify();budget=native.Budget(p["geometry_max_seconds"]);budget.check(admission=True)
    out=native.GEOMETRY
    if out.exists():raise FileExistsError("preserve prior native geometry")
    out.mkdir();started=time.monotonic();counts=dict(model_forwards=0,native_VJP_calls=0,new_generated_answers=0)
    report=dict(schema=p["schema"],status="STARTED",layers=[],counts=counts,
        source_profile_sha256=archive.sha(native.PROFILE),entry_resources=cleanup_owner.resources(),
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,final_or_official_used=False)
    active=model=physical=counter=None;failure=None
    try:
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with manual.selected_runtime(manual.resolve_model(p["model"]))as active,autograd_owner.freeze_parameters(active["model"]):
            try:
                model=active["model"];physical=native.modules(active)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise ValueError("original model core differs")
                def count_forward(_module,_args):counts["model_forwards"]+=1
                counter=model.register_forward_pre_hook(count_forward)
                torch.cuda.reset_peak_memory_stats()
                layout=native.target_indices(p["packed"])
                with sdpa_kernel(SDPBackend.MATH):
                    original,fit_features=native.collect(active,physical,p["packed"],budget,features="full")
                    guard_logits,normal_features=native.collect(active,physical,p["guard_packed"],budget,features="full")
                previous=archive.load_arrays(archive.BASE/"margin_actual_v1/ORIGINAL_logits.npz")["logits"]
                old_normal=archive.load_arrays(archive.OLD/"target_protection_v1/protected_keys.npz")["keys"]
                if not np.array_equal(original,previous):raise RuntimeError("original62 full logits differ")
                if not np.array_equal(normal_features[13]["keys"],old_normal):raise RuntimeError("original239 normal keys differ")
                report["original_logits_reused"]=dict(path=str((archive.BASE/"margin_actual_v1/ORIGINAL_logits.npz").relative_to(native.ROOT)),
                    sha256=archive.sha(archive.BASE/"margin_actual_v1/ORIGINAL_logits.npz"),bitexact=True)
                report["guard_logits"]=archive.save_arrays(out/"guard_logits.npz",logits=guard_logits)
                report["baseline_endpoint"]=archive.save_arrays(out/"baseline_endpoint.npz",values=fit_features["endpoint"])
                rights={};basis_records={}
                for layer in range(14):
                    budget.check();directory=out/("layer"+str(layer).zfill(2));directory.mkdir()
                    full=fit_features[layer]["keys"];target=full[layout["target_from_full"]]
                    protected=normal_features[layer]["keys"]
                    right,record=mathematics.right_basis(target,full,protected,layout["full_weights"],
                        prompt_extra=p["prompt_extra"],rank_rtol=p["rank_rtol"])
                    rights[layer]=right
                    original_pin=archive.save_arrays(directory/"observations.npz",target_keys=target,
                        protected_keys=protected,original_values=fit_features[layer]["values"])
                    full_pins=native.save_array_chunks(directory,"all_fit_keys",full,rows=512)
                    basis_records[layer]=dict(layer=layer,right_geometry=record,
                        observed=original_pin,all_fit_keys=full_pins,
                        original_weight_sha256=identity.tensor_sha(physical[layer].weight),
                        gate=float(model.layers[layer].gates[1].detach()))
                    print("[E_RIGHT_BASIS]"+json.dumps(dict(layer=layer,rank=len(right),
                        normal_rank=record["normal_rank"],residual=record["target_span_relative_residual"])),flush=True)
                raw_blocks,details,raw_logits=native_gradients(active,physical,p["packed"],rights,budget)
                counts["native_VJP_calls"]=sum(row["native_vjp_calls"]for row in details)
                if counts["native_VJP_calls"]!=62 or not np.array_equal(raw_logits,original):
                    raise RuntimeError("same62 native geometry and original gradients required")
                archive.write_new(out/"native_VJP_details.json",dict(rows=details))
                reduced={};bases={}
                for layer in range(14):
                    budget.check();directory=out/("layer"+str(layer).zfill(2))
                    raw=raw_blocks[layer]
                    left,covariance,left_record=mathematics.left_basis(raw,layout["target_weights"],
                        retention=p["left_energy"],rank_cap=p["left_rank_cap"])
                    projected=left.T[None]@raw
                    reduced[layer]=projected.reshape(len(raw),-1)
                    bases[layer]=dict(left=left,right=rights[layer])
                    record=basis_records[layer]
                    record.update(left_geometry=left_record,
                        basis=archive.save_arrays(directory/"basis.npz",left=left,right=rights[layer]),
                        covariance=archive.save_arrays(directory/"left_covariance.npz",covariance=covariance),
                        original_projected_planes=native.save_array_chunks(directory,"raw_planes",raw,rows=16),
                        reduced_planes=archive.save_arrays(directory/"reduced_planes.npz",values=reduced[layer]))
                    report["layers"].append(record)
                    archive.write_new(directory/"report.json",record)
                original_weights={layer:module.weight.detach().cpu().numpy().copy()for layer,module in physical.items()}
                zeros={layer:np.zeros(reduced[layer].shape[1])for layer in range(14)}
                positions=[]
                for row in p["packed"]:
                    positions.extend((row,index)for index in range(len(row["targets"])))
                rivals=np.concatenate([np.asarray(row["rivals"])for row in details])
                derivatives=[]
                for layer in range(14):
                    budget.check();plane_norm=np.linalg.norm(reduced[layer],axis=1)
                    chosen=int(plane_norm.argmax())
                    if plane_norm[chosen]<=1e-14:
                        derivatives.append(dict(layer=layer,status="ZERO_NATIVE_SENSITIVITY"));continue
                    row,local_position=positions[chosen]
                    direction=reduced[layer][chosen]/plane_norm[chosen]
                    for epsilon in p["FD_epsilons"]:
                        observed=[];physical_norms=[];raw_outputs=[]
                        for sign in (-1,1):
                            theta={index:value.copy()for index,value in zeros.items()}
                            theta[layer]=direction*(sign*epsilon)
                            requested,after,physical_receipt=native.materialized(original_weights,theta,bases)
                            with native.install(active,physical,requested):
                                with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                                    logits,_=native.native_forward(active,physical,row)
                                    values=logits.detach().cpu().numpy().copy()
                                    observed.append(float(values[local_position,row["targets"][local_position]]-
                                                          values[local_position,rivals[chosen]]))
                                    raw_outputs.append(values);logits=None
                            physical_norms.append(physical_receipt["actual_norm"])
                        slope=(observed[1]-observed[0])/(2*epsilon);prediction=float(plane_norm[chosen])
                        error=abs(slope-prediction);allowed=p["FD_absolute_tolerance"]+p["FD_relative_tolerance"]*abs(prediction)
                        pin=archive.save_arrays(out/("FD_layer"+str(layer).zfill(2)+"_"+str(epsilon)+".npz"),
                            minus_logits=raw_outputs[0],plus_logits=raw_outputs[1])
                        derivatives.append(dict(layer=layer,case_id=row["id"],position=local_position,
                            global_position=chosen,gold=row["targets"][local_position],rival=int(rivals[chosen]),
                            epsilon=epsilon,predicted=prediction,observed=slope,error=error,allowed=allowed,
                            passed=error<=allowed,physical_norms=physical_norms,packet=pin))
                archive.write_new(out/"finite_difference.json",dict(rows=derivatives))
                failed=[row for row in derivatives if row.get("passed")is False]
                if failed:raise RuntimeError("native projected VJP finite-difference gate failed")
                total_parameters=sum(parameter.numel()for parameter in model.parameters())
                report.update(status="ALL_LAYER_MARGIN_GEOMETRY_COMPLETE",finite_difference=derivatives,
                    all14_searched=True,FD_failed=len(failed),original_normal13_bitexact=True,
                    native_unique_parameter_count=total_parameters,
                    eligible_down_parameter_count=sum(module.weight.numel()for module in physical.values()),
                    original_score=native.score_logits(original,p["packed"])[0],
                    original_core_restored=True,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise RuntimeError("original core changed")
                counter.remove();counter=None
                physical.clear();physical=model=None
            finally:
                if counter is not None:counter.remove()
                if physical is not None:physical.clear()
                counter=physical=model=None
        active=None
    except BaseException as error:
        failure=str(error);report.update(status="ALL_LAYER_MARGIN_GEOMETRY_ERROR",error=failure,traceback=traceback.format_exc())
        error.__traceback__=None
    finally:
        if counter is not None:counter.remove()
        if physical is not None:physical.clear()
        active=counter=physical=model=None;gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:
            failure=failure or str(cleanup_error);report.update(status="E_GEOMETRY_CLEANUP_ERROR",error=failure)
        report["wall_seconds"]=time.monotonic()-started;archive.write_new(out/"report.json",report)
        print("[E_GEOMETRY_END]"+json.dumps({key:report.get(key)for key in(
            "status","counts","FD_failed","wall_seconds","cuda_allocated_after_bytes","cuda_reserved_after_bytes","error")}),flush=True)
    if failure is not None:raise RuntimeError("preserved all-layer geometry failure: "+failure)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("phase",choices=("preflight","prepare","check","actual"))
    phase=parser.parse_args().phase
    if phase=="preflight":
        native.Budget(1800).check(admission=True);native.source()
        if torch.cuda.is_initialized():raise RuntimeError("CPU preflight initialized CUDA")
        print("[E_PREFLIGHT]closed24 FIT/7 normal;all14 owner source;model0",flush=True)
    elif phase=="prepare":prepare()
    elif phase=="check":verify();print("[E_CHECK]exact source/authority;model0",flush=True)
    else:actual()


if __name__=="__main__":main()
