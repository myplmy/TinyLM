"""Test one-pass Qwen prefix features in the same actual P109 student run."""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import sys
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_p109_actual_prefix_kd as prior
from scripts import diag_p106b_p109_prefix_onepass as onepass

base = prior.base
TAG = "p106b_p109_prefix_onepass_student_v1_20261119"
OUT = prior.OUT.with_name(TAG)


def inputs():
    receipt, arrays, rows = prior.data_and_receipt()
    profile = prior.read(prior.OUT/"profile.json")
    one = prior.read(onepass.OUT/"profile.json")
    result = prior.read(onepass.OUT/"report.json")
    assert profile["data"]==receipt and profile["sources"]==prior.contract()
    assert result["source_preserved"] and result["comparison"]["top1_changes"]==0
    assert result["comparison"]["hidden_violations"]>0
    plan, order, count = onepass.job_plan(rows,receipt["documents"])
    assert one["plan_sha"]==base.state_sha(dict(plan))
    current = dict(tag=TAG,source=prior.sha(Path(__file__)), prior=prior.contract(),
                   exact_student_report_sha=prior.sha(prior.OUT/"report.json"),
                   onepass_feature_report_sha=prior.sha(onepass.OUT/"report.json"),
                   onepass_feature_profile_sha=prior.sha(onepass.OUT/"profile.json"),
                   data_sha=receipt["data_sha"], teacher_plan_sha=one["plan_sha"])
    return current,receipt,arrays,(plan,order,count)


@torch.no_grad()
def capture(current, groups):
    from transformers import AutoModelForCausalLM

    teacher, loading = AutoModelForCausalLM.from_pretrained(
        str(base.TEACHER),local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32,
        attn_implementation="eager",use_cache=False,output_loading_info=True)
    assert not any(loading.get(n) for n in ("missing_keys","unexpected_keys","mismatched_keys","error_msgs"))
    assert teacher.config.model_type=="qwen3" and not teacher.config.use_cache
    teacher.eval().requires_grad_(False)
    w = teacher.get_output_embeddings().weight.detach()
    assert w.shape==(151936,1024) and w.dtype==torch.float32
    assert w.data_ptr()==teacher.get_input_embeddings().weight.data_ptr()
    assert base.old.tensor_sha(torch,w)==current["prior"]["teacher_fp32_head_sha256"]
    head = base.head.initialize_head(torch,w,prior.read(base.OUT/"mapping.json")).detach().cuda()
    del w
    teacher.cuda()
    versions = {name:p._version for name,p in teacher.named_parameters()}
    features, metrics = onepass.gather_prefixes(teacher,*groups)
    assert versions=={name:p._version for name,p in teacher.named_parameters()}
    return head,features,metrics


def actual(current, receipt, arrays, groups):
    assert base.idle() and torch.cuda.device_count()==1 and torch.cuda.mem_get_info()[0]>=10*(1<<30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    head,features,teacher_work = capture(current,groups)
    torch.cuda.empty_cache()
    with sdpa_kernel(SDPBackend.MATH),patch.object(prior,"OUT",OUT):
        trial = prior.train("onepass_kd",prior.ALPHA,receipt["documents"],tuple(t.cuda() for t in arrays),head,features)
    exact = prior.read(prior.OUT/"report.json")["arms"]["prefix_kd"]
    assert current["exact_student_report_sha"]==prior.sha(prior.OUT/"report.json")
    assert trial["initial"]==exact["initial"] and trial["history"][0]["ce"]==exact["history"][0]["ce"]
    for a,b in zip(trial["history"],exact["history"],strict=True):
        assert (a["ce_tokens"],a["kd_tokens"])==(b["ce_tokens"],b["kd_tokens"])
    comparison = {}
    for step, item in trial["held"].items():
        comparison[step] = {}
        for lang, row in item["summary"].items():
            original = exact["held"][str(step)]["summary"][lang]
            assert original["count"]==row["count"]
            comparison[step][lang] = dict(nll_delta=row["nll"]-original["nll"],top1_delta=row["correct"]-original["correct"])
    same = current["prior"]==prior.contract()
    prior.write(OUT/"report.json",dict(arm=trial,source_preserved=same,teacher_work=teacher_work,
          held_vs_exact=comparison,same_model=trial["final"]==exact["final"],
          same_optimizers=trial["optimizers"]==exact["optimizers"],checkpoint_writes=0))
    print("P109_PREFIX_ONEPASS_STUDENT",teacher_work,comparison[prior.UPDATES],trial["final"]==exact["final"],flush=True)
    return 0 if same else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(base.CUTOFF.tzinfo)+timedelta(seconds=155)<base.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    current,*args = inputs()
    if phase=="prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        prior.write(OUT/"profile.json",current)
        return 0
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG")==":4096:8" and current==prior.read(OUT/"profile.json")
    return actual(current,*args)


if __name__=="__main__":
    sys.exit(main())
