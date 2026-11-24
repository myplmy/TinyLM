"""Freeze exact edited states before any reply; compare matched physical norms."""
import argparse
import gc
import json
import time
import traceback
import unittest
from collections import Counter
import numpy as np
import torch
from torch.nn.attention import sdpa_kernel,SDPBackend
from scripts import p108e_io as native
from scripts import p108e_evaluation as evaluation
from scripts import p108e_policy as packet_owner
from scripts import p108e_replay as replay
from scripts import diag_p108e_policy as policy
from scripts import diag_p108c_scope as archive
from scripts import p108_weight_space as identity
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as cleanup_owner
from scripts.p108b_tinylm import TinyAdapter
from scripts.p106b_shards import ShardWriter

BASE=native.BASE/"evaluation_v1"
PROFILE=BASE/"profile.json"
STATES=[name+suffix for name in policy.POLICIES for suffix in ("_FINAL","_MATCHED_NET")]+["AFFINE_FIXED_SPAN"]
CODE=("scripts/diag_p108e_evaluate.py","scripts/p108e_evaluation.py","scripts/p108e_replay.py",
      "scripts/test_p108e_evaluation.py","scripts/test_p108e_replay.py","scripts/p108b_tinylm.py",
      "scripts/p106b_shards.py","scripts/interactive_research_infer.py")+policy.CODE


def packet(pin):
    path=native.ROOT/pin["path"]
    if archive.sha(path)!=pin["sha256"]:raise ValueError("frozen physical packet changed")
    return archive.load_arrays(path)


def archived_answers(directory,manifest):
    rows=[]
    for shard in manifest["shards"]:
        path=directory/shard["path"]
        if archive.sha(path)!=shard["sha256"]:raise ValueError("old answer shard changed")
        rows.extend(json.loads(line)for line in path.read_text().splitlines())
    if len(rows)!=manifest["rows"]:raise ValueError("old complete answer count differs")
    return rows


def sources():
    parent=policy.verify();origin,fits,packed,guards,_,dev,baseline,refs=native.source()
    boundary_path=archive.BASE/"boundary_data_v1.json"
    sentence_path=archive.BASE/"sentence_control_profile_v1.json"
    boundary=archive.read(boundary_path);sentences=archive.read(sentence_path)["questions"]
    singles,dialogs=evaluation.panels(fits,dev,guards,boundary,sentences)
    refs.update({policy.PROFILE,native.GEOMETRY/"report.json",boundary_path,sentence_path})
    for name in ("boundary_actual_v1","sentence_control_actual_v1"):
        directory=archive.BASE/name;closed=archive.read(directory/"report.json")
        refs.add(directory/"report.json")
        for shard in closed["answers_manifest"]["shards"]:refs.add(directory/shard["path"])
        for row in archived_answers(directory,closed["answers_manifest"]):
            if row["arm"]=="ORIGINAL":baseline[row["id"]]=row
    specs={}
    for name in policy.POLICIES:
        path=native.BASE/"policies"/name/"report.json";closed=archive.read(path)
        if closed["status"]!="BOUNDED_MARGIN_POLICY_COMPLETE"or not closed["original_core_restored"]:
            raise ValueError("closed and restored policy required")
        refs.add(path);refs.add(native.ROOT/closed["final_coordinates"]["path"])
        refs.update(native.ROOT/r["packet"]["path"]for r in closed["final_patches"])
        specs[name]=closed
    path=native.BASE/"span_control_v1/report.json";span=archive.read(path)
    if span["physical_predicted_gold"]!=62:raise ValueError("same-span classification witness required")
    refs.update({path,native.ROOT/span["physical_packet"]["path"],native.ROOT/span["coefficient_packet"]["path"]})
    for row in singles+[r for dialog in dialogs for r in dialog]:
        old=baseline[row["id"]]
        if old["question"]!=row["question"]or old["generation"]["max_new"]!=row["max_new"]:
            raise ValueError("cached original prompt or generation bound differs")
    return parent,packed,singles,dialogs,baseline,specs,span,refs


def prepare():
    native.Budget(1800).check(admission=True)
    if BASE.exists():raise FileExistsError("preserve exact-state evaluation namespace")
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n)for n in (
        "scripts.test_p108e_replay","scripts.test_p108e_evaluation"))
    tested=unittest.TextTestRunner(verbosity=2).run(suite)
    if not tested.wasSuccessful()or tested.testsRun!=7:raise RuntimeError("seven exact-replay/norm/history contracts required")
    p,packed,singles,dialogs,baseline,specs,span,refs=sources()
    from tinylm.chat.serialize import serialize
    tokenizer=manual.local_tokenizer(manual.verify_manifest());lengths={}
    for row in singles+[r for d in dialogs for r in d]:
        text=serialize(dict(messages=manual.prompt_messages(row["question"])),"chatml",add_generation_prompt=True)
        lengths[row["id"]]=len(tokenizer.encode(text).ids)
        if lengths[row["id"]]+row["max_new"]>1024:raise ValueError("single input would truncate")
    for dialog in dialogs:
        if sum(lengths[r["id"]]+r["max_new"]+32 for r in dialog)>1024:
            raise ValueError("conservative own-history context exceeds1024")
    BASE.mkdir()
    with (BASE/"initial_plan.md").open("xb")as stream:stream.write(archive.PLAN.read_bytes())
    data=archive.write_new(BASE/"data.json",dict(singles=singles,dialogs=dialogs,training_allowed=False,
        prior_exposed_diagnostic=True,official_or_final_for_selection=False))
    archive.write_new(PROFILE,dict(schema="P108E_EXACT_STATE_REPLY_COMPARISON_V1",authority_directive=142,
        authority_end=native.time_owner.AUTHORITY_END.isoformat(),cleanup_seconds=native.time_owner.CLEANUP_SECONDS,
        model=p["model"],origin=p["origin"],initial_plan_sha256=archive.sha(BASE/"initial_plan.md"),
        sources={name:archive.sha(native.ROOT/name)for name in sorted(set(CODE))},
        references={str(path.relative_to(native.ROOT)):archive.sha(path)for path in sorted(refs)},
        data=data,states=STATES,CPU_contracts=tested.testsRun,max_seconds=3600,
        common_net=native.COMMON_BUDGET,norm_rtol=2e-5,native_logit_tolerance=.002,
        single_calls=187,own_history_calls=12,expected_generated_replies=1393,
        all_after_states_sealed_before_new_replies=True,reuse_original_answers=True,
        new_CANARY_replies=1,maximum_single_prompt_tokens=max(lengths.values()),
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,training_allowed=False,
        official=False,quality_adoption=False,DEV_or_official_for_reselection=False))
    if torch.cuda.is_initialized():raise RuntimeError("CPU admission initialized CUDA")
    print("[E_REPLY_PREPARED]seven contracts;seven frozen policies;199 calls each;no model",flush=True)


def verify():
    p=archive.read(PROFILE);policy.verify()
    if(p["authority_directive"]!=142 or p["authority_end"]!=native.time_owner.AUTHORITY_END.isoformat()
       or p["cleanup_seconds"]!=native.time_owner.CLEANUP_SECONDS
       or archive.sha(BASE/"initial_plan.md")!=p["initial_plan_sha256"]
       or archive.sha(native.ROOT/p["data"]["path"])!=p["data"]["sha256"]):
        raise ValueError("exact admitted authority, initial plan and questions required")
    for name,digest in {**p["sources"],**p["references"]}.items():
        if archive.sha(native.ROOT/name)!=digest:raise ValueError("reply input changed: "+name)
    return p


def decode_policy(original,closed):
    after={}
    for row in closed["final_patches"]:
        layer=row["layer"]
        if identity.tensor_sha(torch.from_numpy(original[layer]))!=row["before_sha256"]:
            raise ValueError("XOR parent tensor identity differs")
        arrays=packet(row["packet"])
        if set(arrays)!={"xor"}:raise ValueError("one lossless XOR array required")
        after[layer]=packet_owner.restore_xor(original[layer],arrays["xor"])
        if identity.tensor_sha(torch.from_numpy(after[layer]))!=row["after_sha256"]:
            raise ValueError("decoded policy after differs")
    if set(after)!=set(range(14)):raise ValueError("complete14 physical states required")
    return after


def physical_summary(original,after):
    layers=[]
    for layer in range(14):
        delta=after[layer].astype(np.float64)-original[layer].astype(np.float64)
        layers.append(dict(layer=layer,norm=float(np.linalg.norm(delta)),changed=int(np.sum(delta!=0))))
    return dict(actual_norm=float(np.sqrt(sum(r["norm"]**2 for r in layers))),layers=layers)


def seal_states(original,specs,span,budget):
    sealed=[];directory=BASE/"sealed";directory.mkdir()
    for name in policy.POLICIES:
        after=decode_policy(original,specs[name])
        sealed.append(dict(name=name+"_FINAL",source_policy=name,patches=specs[name]["final_patches"],
            edited_core_sha256=specs[name]["edited_core_sha256"],physical=physical_summary(original,after),
            same_norm=False))
        budget.check();matched,receipt=evaluation.match_all(original,after,native.COMMON_BUDGET)
        pins=[]
        for layer in range(14):
            pin=archive.save_arrays(directory/(name+"_layer"+str(layer).zfill(2)+".npz"),
                xor=packet_owner.after_xor(original[layer],matched[layer]))
            pins.append(dict(layer=layer,packet=pin,
                before_sha256=identity.tensor_sha(torch.from_numpy(original[layer])),
                after_sha256=identity.tensor_sha(torch.from_numpy(matched[layer]))))
        sealed.append(dict(name=name+"_MATCHED_NET",source_policy=name,patches=pins,
            physical=physical_summary(original,matched),matching=receipt,same_norm=True))
        after=matched=None
    span_packet=packet(span["physical_packet"])
    after={i:original[i]for i in range(14)};after[13]=span_packet["after"]
    if identity.tensor_sha(torch.from_numpy(original[13]))!=span["before_sha256"]:
        raise ValueError("affine witness parent differs")
    sealed.append(dict(name="AFFINE_FIXED_SPAN",physical_packet=span["physical_packet"],
        physical=physical_summary(original,after),same_norm=False,classification_witness_not_minimum_certificate=True))
    if [s["name"]for s in sealed]!=STATES:raise RuntimeError("frozen state order differs")
    archive.write_new(directory/"report.json",dict(states=sealed,before_first_new_reply=True,
        source_profile_sha256=archive.sha(PROFILE),no_new_answer_used=True))
    return sealed


def reconstruct(original,state):
    if "physical_packet"in state:
        after={i:original[i]for i in range(14)};after[13]=packet(state["physical_packet"])["after"]
        return after
    return decode_policy(original,dict(final_patches=state["patches"]))


def actual():
    p=verify();budget=native.Budget(p["max_seconds"]);budget.check(admission=True)
    if (BASE/"actual").exists():raise FileExistsError("preserve previous native replies")
    out=BASE/"actual";out.mkdir();started=time.monotonic()
    _,packed,singles,dialogs,baseline,specs,span,_=sources()
    common=archive.read(native.GEOMETRY/"report.json")
    bases,blocks,_,original_logits,_=policy.load_initial(common)
    layout=native.target_indices(packed);gold=layout["gold"]
    _,original_margins,original_rivals,_=native.score_logits(original_logits,packed)
    report=dict(schema=p["schema"],status="STARTED",states=[],source_profile_sha256=archive.sha(PROFILE),
        entry_resources=cleanup_owner.resources(),body_optimizer_updates=0,value_optimizer_updates=0,
        checkpoint_writes=0,training_allowed=False,no_reselection=True,official=False)
    active=model=physical=adapter=after=counter=None;failure=None;counts=Counter();writer=None
    try:
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        with manual.selected_runtime(manual.resolve_model(p["model"]))as active:
            try:
                model=active["model"];physical=native.modules(active)
                if manual.state_fingerprint(model)!=p["origin"]["core_sha256"]:raise ValueError("original core differs")
                original={i:m.weight.detach().cpu().numpy().copy()for i,m in physical.items()}
                states=seal_states(original,specs,span,budget)
                def count_forward(_module,_args):counts["model_forwards"]+=1
                counter=model.register_forward_pre_hook(count_forward);torch.cuda.reset_peak_memory_stats()
                fits=[r for r in singles if r["evaluation_panel"]=="FIT"]
                calibration=archive.read(archive.OLD/"data.json")["calibration_questions"]
                adapter=TinyAdapter(active,fits,calibration,budget=budget)
                report["calibration_reference_forwards"]=adapter.counts["model_forwards"]
                canary=adapter.generate(fits[0],max_new=64,variant="ORIGINAL_CANARY")
                if canary["generation"]["generated_ids"]!=baseline[fits[0]["id"]]["generation"]["generated_ids"]:
                    raise ValueError("original product-generation canary differs")
                for state in states:
                    budget.check();directory=out/state["name"];directory.mkdir();begin=time.monotonic()
                    after=reconstruct(original,state);before_counts=dict(adapter.counts)
                    prediction=np.zeros(62);projection_residuals=[]
                    for layer in range(14):
                        delta=after[layer].astype(np.float64)-original[layer].astype(np.float64)
                        left,right=bases[layer]["left"],bases[layer]["right"]
                        theta=left.T@delta@right.T
                        prediction+=blocks[layer]@theta.reshape(-1)
                        projection_residuals.append(float(np.linalg.norm(delta-left@theta@right)))
                    writer=ShardWriter(directory,"answers",limit=2_000_000);records=[]
                    with replay.install_after(active,physical,after)as receipt:
                        edited_sha=manual.state_fingerprint(model)
                        if "edited_core_sha256"in state and edited_sha!=state["edited_core_sha256"]:
                            raise RuntimeError("sealed final core not reproduced")
                        with sdpa_kernel(SDPBackend.MATH):
                            actual_logits,_=native.collect(active,physical,packed,budget,features=None)
                        score,margin,rivals,winners=native.score_logits(actual_logits,packed)
                        if state["name"].endswith("_FINAL"):
                            old_score=specs[state["source_policy"]]["final_score"]
                            if(score["questions_all_gold"]!=old_score["questions_all_gold"]
                               or score["positions_gold"]!=old_score["positions_gold"]):
                                raise RuntimeError("exact original policy TF result not reproduced")
                        affine_control=None
                        if state["name"]=="AFFINE_FIXED_SPAN":
                            capture,arrays,head=native.origin.captured()
                            displacement=after[13].astype(np.float64)-original[13].astype(np.float64)
                            residual=arrays["residuals"]+capture["gate"]*(arrays["keys"]@displacement.T)
                            rms=np.sqrt(np.mean(residual**2,axis=1)+capture["norm_eps"])
                            affine_logits=residual@head.T/rms[:,None]
                            affine_control=dict(maximum_logit_error=float(np.max(np.abs(affine_logits-actual_logits))),
                                argmax_mismatches=int(np.sum(affine_logits.argmax(axis=1)!=winners)),
                                physical_predicted_gold=int(np.sum(affine_logits.argmax(axis=1)==gold)))
                            if(affine_control["maximum_logit_error"]>p["native_logit_tolerance"]
                               or affine_control["argmax_mismatches"]or affine_control["physical_predicted_gold"]!=62):
                                raise RuntimeError("same-span affine classification witness not reproduced")
                        fixed=actual_logits[np.arange(62),gold]-actual_logits[np.arange(62),original_rivals]
                        tf_pin=archive.save_arrays(directory/"native_TF.npz",logits=actual_logits,
                            original_fixed_rival_prediction=original_margins+prediction,
                            actual_fixed_rival_margin=fixed,actual_new_rival_margin=margin)
                        for row in singles:
                            answer=adapter.generate(row,max_new=row["max_new"],variant=state["name"])
                            answer.update(baseline_answer=baseline[row["id"]]["answer"],
                                baseline_generation=baseline[row["id"]]["generation"],mode="SINGLE")
                            writer.append(answer);records.append(answer)
                        for dialog in dialogs:
                            history=[]
                            for row in dialog:
                                answer=adapter.generate(row,max_new=row["max_new"],variant=state["name"],history=history)
                                answer.update(baseline_answer=baseline[row["id"]]["answer"],
                                    baseline_actual_history=baseline[row["id"]].get("actual_history",[]),
                                    mode="OWN_HISTORY",same_history_as_original=history==baseline[row["id"]].get("actual_history",[]))
                                writer.append(answer);records.append(answer)
                                history=evaluation.extend_history(history,row,answer["answer"])
                    manifest=writer.close(lineage=dict(source_profile=archive.sha(PROFILE),
                        edited_core_sha256=edited_sha,training_allowed=False,all_states_presealed=True))
                    writer=None
                    summaries={}
                    for family in sorted({r["evaluation_panel"]for r in records}):
                        rows=[r for r in records if r["evaluation_panel"]==family]
                        summaries[family]=dict(rows=len(rows),scored=sum(r["exact"]is not None for r in rows),
                            exact=sum(r["exact"]is True for r in rows),diagnostics=identity.summarize(rows))
                    result=dict(name=state["name"],physical=state["physical"],edited_core_sha256=edited_sha,
                        replay=receipt,TF_score=score,native_TF=tf_pin,
                        affine_control=affine_control,
                        original_linear_fixed_rival_RMSE=float(np.sqrt(np.mean((fixed-original_margins-prediction)**2))),
                        original_rival_switches=int(np.sum(rivals!=original_rivals)),
                        projected_physical_residual_norms=projection_residuals,
                        counts={k:adapter.counts[k]-before_counts[k]for k in before_counts},
                        summaries=summaries,answers_manifest=manifest,wall_seconds=time.monotonic()-begin,
                        original_core_restored=manual.state_fingerprint(model)==p["origin"]["core_sha256"])
                    if not result["original_core_restored"]or len(records)!=199:raise RuntimeError("state recovery or reply count differs")
                    archive.write_new(directory/"report.json",result);report["states"].append(result)
                    after=None;records=None
                    print("[E_REPLY_STATE]"+json.dumps(dict(name=state["name"],TF=score,
                        FIT=result["summaries"]["FIT"]["exact"],DEV=result["summaries"]["DEV"]["exact"],
                        GUARD=result["summaries"]["GUARD"]["exact"],wall_seconds=result["wall_seconds"])),flush=True)
                report.update(status="EXACT_STATE_REPLY_COMPARISON_COMPLETE",original_core_restored=True,
                    counts=dict(counts),generated_replies=sum(s["counts"]["generated_calls"]for s in report["states"]),
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                adapter.close();adapter=None;counter.remove();counter=None;physical=model=None
            finally:
                if counter is not None:counter.remove();counter=None
                if adapter is not None:adapter.close();adapter=None
                physical=model=after=None
        active=None
    except BaseException as error:
        failure=str(error);report.update(status="EXACT_STATE_REPLY_COMPARISON_ERROR",error=failure,traceback=traceback.format_exc())
        error.__traceback__=None
    finally:
        if writer is not None:report["partial_answers_manifest"]=writer.close(lineage=dict(partial=True,training_allowed=False))
        if adapter is not None:adapter.close()
        active=model=physical=adapter=after=counter=None;gc.collect()
        cleanup_error=cleanup_owner.cleanup(report)
        if cleanup_error is not None:failure=failure or str(cleanup_error);report["cleanup_error"]=str(cleanup_error)
        report["wall_seconds"]=time.monotonic()-started
        archive.write_new(out/"report.json",report)
    print("[E_REPLY_END]"+json.dumps(dict(status=report["status"],states=len(report["states"]),error=failure)),flush=True)
    if failure:raise RuntimeError(failure)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","preflight","check","actual"))
    args=parser.parse_args()
    if args.action=="prepare":prepare()
    elif args.action=="preflight":
        native.Budget(1800).check(admission=True);sources()
        if torch.cuda.is_initialized():raise RuntimeError("preflight initialized CUDA")
        print("[E_REPLY_PREFLIGHT]closed policy bits and cached question panels;no model",flush=True)
    elif args.action=="check":verify();print("[E_REPLY_CHECK]frozen sources and authority match",flush=True)
    else:actual()


if __name__=="__main__":main()
