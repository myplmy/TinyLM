"""CPU logit arithmetic only; no model, training, GPU or production mutation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import time

os.environ["CUDA_VISIBLE_DEVICES"]=""
os.environ["OMP_NUM_THREADS"]="1"
os.environ["MKL_NUM_THREADS"]="1"
import torch
import torch.nn.functional as F
from tinylm.train.mtp_sft import ce_sum
from tinylm.train.trainer import _kd_kl

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/"paper2610_numeric_v1"
DEADLINE=datetime(2026,10,26,7,15,tzinfo=timezone.utc).timestamp()

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def fixed_hard(z):
    return F.softplus(torch.logsumexp(z[1:]-z[0],dim=0))

def value_grad(z,fn):
    value=fn(z)
    grad=torch.autograd.grad(value,z)[0]
    return float(value.detach()),grad.detach()

def main():
    torch.set_num_threads(1)
    started=time.monotonic()
    assert time.time()<DEADLINE and not OUT.exists()
    paths=["tinylm/train/mtp_sft.py","tinylm/train/trainer.py","tinylm/train/fused_ce.py",
           "handoff/audit/oct26_research/paper2610_numeric.py"]
    pins={p:digest(ROOT/p) for p in paths}
    OUT.mkdir()
    source=dict(schema="P102A_SOFTMAX_NUMERIC_PREFLIGHT_V1",source_pins=pins,
        model_or_gpu_calls=0,optimizer_steps=0,checkpoint_reads=0,
        fixed_production_code=False,max_wall_sec=120,
        deadline_utc="2026-10-26T07:15:00Z",
        hypothesis="Observe arithmetic counterexamples, not the incidence or cause in a TinyLM training run.",
        local_pdf_sha256=digest("/mnt/c/Users/Uranus/Downloads/2610.31642v1.pdf"),
        paper="https://arxiv.org/html/2610.31642v1",
        soft_scope="Equation9 near equal moderate-logit FP32 only, using current torch p/q; not a general replacement.")
    (OUT/"preflight.json").write_text(json.dumps(source,indent=2)+chr(10))
    hard=[]
    label=torch.tensor([0],dtype=torch.long)
    for vocab in [3,32768]:
        for margin in [6.,18.,40.]:
            for path in ["f32_direct","f32_ce_sum","bf16_ce_sum","f64_direct"]:
                assert time.monotonic()-started<120 and time.time()<DEADLINE
                dtype=torch.bfloat16 if path.startswith("bf16") else torch.float64 if path.startswith("f64") else torch.float32
                original=torch.zeros(vocab,dtype=dtype)
                original[0]=margin+math.log(vocab-1)
                standard=original.clone().requires_grad_(True)
                stable=original.clone().requires_grad_(True)
                oracle=original.double().requires_grad_(True)
                if path.endswith("ce_sum"):
                    standard_fn=lambda z:ce_sum(z[None],label)
                    fixed_fn=lambda z:fixed_hard(z.float())
                else:
                    standard_fn=lambda z:F.cross_entropy(z[None],label)
                    fixed_fn=fixed_hard
                loss,g=value_grad(standard,standard_fn)
                fix,fg=value_grad(stable,fixed_fn)
                ref,rg=value_grad(oracle,fixed_hard)
                assert all(math.isfinite(x) for x in [loss,fix,ref,float(g.sum()),float(fg.sum())])
                hard.append(dict(vocab=vocab,path=path,requested_margin=margin,
                    actual_margin=float(original[0].double()-torch.logsumexp(original[1:].double(),0)),
                    stock_loss=loss,fixed_loss=fix,fp64_stable_loss=ref,
                    stock_target_grad=float(g[0]),fixed_target_grad=float(fg[0]),fp64_target_grad=float(rg[0]),
                    stock_grad_sum_fp64=float(g.double().sum()),fixed_grad_sum_fp64=float(fg.double().sum()),
                    stock_max_abs_error=float((g.double()-rg).abs().max()),
                    fixed_max_abs_error=float((fg.double()-rg).abs().max())))
    soft=[]
    for vocab in [3,32768]:
        teacher=torch.tensor([2.,1.,0.]) if vocab==3 else torch.linspace(-2,2,vocab)
        for temperature in [1.,4.]:
            for near in [False,True]:
                student=teacher.clone()
                if near:
                    delta=1e-7 if vocab==3 else 1e-6
                    student[0]-=delta;student[1]+=delta
                x=student.clone().requires_grad_(True)
                loss,gradient=value_grad(x,lambda z:_kd_kl(z[None],teacher[None],temperature,chunk=0,fp32=True))
                ts=teacher/temperature; ss=student/temperature
                p=F.softmax(ts,-1);q=F.softmax(ss,-1)
                delta=ss-ts
                centered=delta-(p*delta).sum()
                log_ratio=centered-torch.log1p((p*torch.expm1(centered)).sum())
                difference=p*torch.expm1(log_ratio)
                proposed=(difference-q*difference.sum())*temperature
                reference=(F.softmax(student.double()/temperature,-1)-F.softmax(teacher.double()/temperature,-1))*temperature
                assert bool(torch.isfinite(proposed).all())
                if not near:
                    assert bool(proposed.eq(0).all()) and bool(reference.eq(0).all())
                soft.append(dict(vocab=vocab,T=temperature,near_equal=near,actual_kd_kl_forward=loss,
                    stock_grad_l2=float(torch.linalg.vector_norm(gradient.double())),
                    equation9_near_equal_grad_l2=float(torch.linalg.vector_norm(proposed.double())),
                    reference_grad_l2=float(torch.linalg.vector_norm(reference)),
                    stock_max_abs_error=float((gradient.double()-reference).abs().max()),
                    near_equation9_max_abs_error=float((proposed.double()-reference).abs().max()),
                    stock_sum_fp64=float(gradient.double().sum()),proposed_sum_fp64=float(proposed.double().sum()),
                    same_logits_exact_zero_verified=not near))
    assert all(digest(ROOT/p)==h for p,h in pins.items())
    assert time.monotonic()-started<120 and time.time()<DEADLINE
    report=dict(schema="P102A_SOFTMAX_NUMERIC_CPU_V1",returncode=0,
        status="NUMERIC_COUNTEREXAMPLES_ONLY",hard_cases=hard,soft_cases=soft,
        hard_case_count=len(hard),soft_case_count=len(soft),torch_version=torch.__version__,
        whole_sec=time.monotonic()-started,source_pins_unchanged=True,
        models_loaded=0,gpu_calls=0,optimizer_steps=0,checkpoint_reads=0,
        production_changes=0,benchmarks_or_model_quality_claim=False,
        real_training_logit_margin_incidence="NOT_MEASURED",
        fused_kernels_and_shared_head_gradients="NOT_TESTED",
        soft_fix_forward_kl_or_general_large_gap_api="NOT_IMPLEMENTED",
        soft_prototype_is_paper_v1_near_equal_arithmetic_only=True)
    (OUT/"report.json").write_text(json.dumps(report,indent=2)+chr(10))
    notable=next(r for r in hard if r["vocab"]==3 and r["path"]=="f32_ce_sum" and r["requested_margin"]==18)
    print(json.dumps(dict(status=report["status"],hard=len(hard),soft=len(soft),
        seconds=report["whole_sec"],notable=notable,
        equal_soft=[r for r in soft if not r["near_equal"]]),indent=2))

if __name__=="__main__":
    main()

