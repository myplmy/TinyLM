"""CPU feasibility probe of actual Qwen gated-delta rules; not a DVLM implementation."""
import hashlib
import inspect
import json
from pathlib import Path
import time
from scripts import diag_p106b_actd_topk as data

ROOT=data.ROOT;BASE=ROOT/'test_result/evidence/p106b_dvlm_hybrid_visibility_v1_20261113'


def run():
    data.guard();start=time.perf_counter()
    if BASE.exists():raise FileExistsError('fresh hybrid visibility namespace required')
    p=data.qualified.verify();import torch
    import tinylm  # Apply project cache routing before Transformers imports.
    from transformers.models.qwen3_5 import modeling_qwen3_5 as source
    torch.set_num_threads(2);torch.manual_seed(1337)
    if torch.cuda.is_initialized():raise ValueError('CPU feasibility must not initialize CUDA')
    path=Path(inspect.getfile(source));sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest().upper()
    before=sha(path);rec=source.torch_recurrent_gated_delta_rule;chunk=source.torch_chunk_gated_delta_rule
    # Three independent groups. The second continuation must not read the first private branch.
    q=torch.randn(1,48,2,8);k=torch.randn_like(q);v=torch.randn_like(q);g=-torch.rand(1,48,2);beta=torch.sigmoid(torch.randn(1,48,2))
    def invoke(fn,a,b,*,value=v,state=None):
        kwargs=dict(initial_state=state,output_final_state=True,use_qk_l2norm_in_kernel=True)
        return fn(q[:,a:b],k[:,a:b],value[:,a:b],g[:,a:b],beta[:,a:b],**kwargs)
    baseline,allstate=invoke(rec,0,48);changed=v.clone();changed[:,16:32]+=3.;altered,_=invoke(rec,0,48,value=changed)
    prefix,state=invoke(rec,0,16);state_before=state.clone();fork,_=invoke(rec,32,48,state=state.clone());otherfork,_=invoke(rec,32,48,value=changed,state=state.clone())
    keep=torch.cat((torch.arange(16),torch.arange(32,48)))
    serial,_=rec(q[:,keep],k[:,keep],v[:,keep],g[:,keep],beta[:,keep],initial_state=None,output_final_state=True,use_qk_l2norm_in_kernel=True)
    # Padding helper is intentionally a padding helper, not a general branch-attention mask.
    mask=torch.ones(1,1,48,48,dtype=torch.bool);mask[:,:,32:,16:32]=False;x=torch.randn(1,48,4)
    masked=source.apply_mask_to_padding_states(x,mask)
    chunked,_=invoke(chunk,0,48)
    checks=dict(private_branch_changes_naive_later_state=float((baseline[:,32:]-altered[:,32:]).abs().max())>1e-6,
        changing_later_branch_does_not_change_original_prefix=torch.equal(baseline[:,:16],altered[:,:16]),
        forked_prefix_state_is_unchanged=torch.equal(state,state_before),
        fork_is_independent_of_hidden_private_branch=torch.equal(fork,otherfork),
        fork_matches_explicit_prefix_plus_own_branch=torch.allclose(fork,serial[:,16:],atol=1e-5,rtol=1e-4),
        padding_helper_does_not_apply_4d_hpa_mask=torch.equal(x,masked),
        actual_chunk_and_recurrent_rule_close=torch.allclose(chunked,baseline,atol=1e-5,rtol=1e-4))
    metadata=data.qualified.q.read_json(p['assets']['files']['config.json']['resolved_path']);text=metadata.get('text_config',metadata)
    types=text.get('layer_types');counts={name:types.count(name)for name in set(types)}if isinstance(types,list)else None
    report=dict(status='HYBRID_VISIBILITY_CPU_FEASIBILITY_MEASURED',returncode=0 if all(checks.values())else 8,
        checks=checks,actual_source_path=str(path),actual_source_sha256=before,actual_source_unchanged=before==sha(path),
        qualified_profile_sha256=data.inventory.digest(data.qualified.BASE/'profile.json'),teacher_layer_types=counts,
        recurrence_private_branch_max_abs=float((baseline[:,32:]-altered[:,32:]).abs().max()),
        proper_fork_reference_max_abs=float((fork-serial[:,16:]).abs().max()),chunk_vs_recurrent_max_abs=float((chunked-baseline).abs().max()),
        probe_state_shape=list(state.shape),probe_state_bytes=state.numel()*state.element_size(),
        gpu_calls=0,cuda_initialized=torch.cuda.is_initialized(),model_loads=0,checkpoint_reads=0,optimizer_updates=0,checkpoint_writes=0,
        quality_claim=False,dvlm_pts_hpa_adapter_implemented=False,full_checkpoint_hpa_verified=False,
        limitation='Actual source primitives with deterministic synthetic CPU tensors; no pretrained model behavior or intelligence result.',seconds=time.perf_counter()-start)
    if not report['actual_source_unchanged']or report['cuda_initialized']:raise ValueError('CPU source protection failed')
    BASE.mkdir(parents=True);data.write_new(BASE/'report.json',report)
    print('[DVLM_HYBRID_CPU] '+json.dumps(report),flush=True)
    if report['returncode']:raise RuntimeError('hybrid primitive feasibility gate negative')


if __name__=='__main__':run()
