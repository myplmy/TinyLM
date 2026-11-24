"""Measure native one-pass teacher prefixes against independent prefix forwards."""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import os
from pathlib import Path
import sys
from time import perf_counter
from unittest.mock import patch

import torch
from torch.nn import functional as F

from scripts import diag_p106b_p109_actual_prefix_kd as prior
from scripts import diag_p106b_p109_prefix_kd_readback as audit


base = prior.base
TAG = "p106b_p109_prefix_onepass_v1_20261119"
OUT = prior.OUT.with_name(TAG)
ATOL, RTOL = 1e-5, 1e-4


def job_plan(rows, docs):
    ordered = list(dict.fromkeys(tuple(r["teacher_prefix"]) for r in rows))
    index = {q:i for i,q in enumerate(ordered)}
    stable_by_doc = defaultdict(set)
    for row in rows:
        if row["stable"]:
            q = tuple(row["teacher_prefix"])
            d = row["doc"]
            assert tuple(docs[d]["teacher_ids"][:len(q)]) == q
            stable_by_doc[d].add(q)
    contexts, emitted = {}, set()
    for group in stable_by_doc.values():
        context = max(group,key=len)
        todo = contexts.setdefault(context, [])
        for q in sorted(group,key=lambda x:(len(x),x)):
            if q not in emitted:
                todo.append((index[q],len(q)-1))
                emitted.add(q)
    for q in ordered:
        if q not in emitted:
            contexts[q] = [(index[q],len(q)-1)]
    selected = sorted(i for todo in contexts.values() for i,_ in todo)
    assert selected == list(range(len(ordered)))
    by_length = defaultdict(list)
    for ctx,todo in contexts.items():
        by_length[len(ctx)].append((ctx,todo))
    ordering = [index[tuple(r["teacher_prefix"])] for r in rows]
    return by_length,ordering,len(ordered)


def frozen_input():
    d,_,rows = prior.data_and_receipt()
    source = prior.OUT/"profile.json"
    evidence = prior.OUT/"report.json"
    computed = audit.OUT/"report.json"
    old = prior.read(source)
    stats = prior.read(computed)
    assert d==old["data"] and old["sources"]==prior.contract()
    assert stats["report_sha"]==prior.sha(evidence) and stats["profile_sha"]==prior.sha(source)
    plan,order,count = job_plan(rows,d["documents"])
    contexts = sum(len(x) for x in plan.values())
    tokens = sum(k*len(x) for k,x in plan.items())
    assert tokens == stats["teacher_work"]["projected_teacher_tokens"] and count==stats["teacher_work"]["original_unique_queries"]
    profile = dict(tag=TAG, old=old["sources"], prior_profile_sha=prior.sha(source), prior_result_sha=prior.sha(evidence),
                   cpu_cost_sha=prior.sha(computed), self_sha=prior.sha(Path(__file__)), plan_sha=base.state_sha(dict(plan)),
                   contexts=contexts, tokens=tokens, outputs=len(rows), atol=ATOL, rtol=RTOL)
    return profile,rows,plan,order,count


@torch.no_grad()
def gather_prefixes(teacher, plan, order, count):
    data = torch.empty((count,1024),device="cuda",dtype=torch.float32)
    begin = perf_counter()
    batches = 0
    for _,contexts in sorted(plan.items()):
        for start in range(0,len(contexts),32):
            group = contexts[start:start+32]
            ids = torch.tensor([q for q,_ in group],dtype=torch.long,device="cuda")
            hidden = teacher.model(input_ids=ids,use_cache=False)
            assert hidden.past_key_values is None
            keys, batch_rows, positions = [], [], []
            for row,(_,slots) in enumerate(group):
                for i,t in slots:
                    keys.append(i)
                    batch_rows.append(row)
                    positions.append(t)
            data[keys] = hidden.last_hidden_state[batch_rows,positions]
            batches += 1
    torch.cuda.synchronize()
    return data[order], dict(seconds=perf_counter()-begin,batches=batches)


@torch.no_grad()
def compare(reference, candidate, head, rows):
    assert reference.shape==candidate.shape==(len(rows),1024)
    delta = (candidate-reference).abs()
    limits = ATOL+RTOL*reference.abs()
    violations = delta.gt(limits)
    report = dict(hidden_elements=delta.numel(), hidden_violations=int(violations.sum()),
                  hidden_rows_violated=int(violations.any(1).sum()), hidden_max_abs=float(delta.max()),
                  hidden_max_scaled=float((delta/limits).max()), logits_violations=0,
                  logits_max_abs=0., max_abs_nll=0., top1_changes=0)
    targets = torch.tensor([row["target"] for row in rows],dtype=torch.long,device="cuda")
    for i in range(0,len(rows),64):
        region = slice(i,i+64)
        left,right = F.linear(reference[region],head),F.linear(candidate[region],head)
        gap = (left-right).abs()
        report["logits_violations"] += int(gap.gt(ATOL+RTOL*left.abs()).sum())
        report["logits_max_abs"] = max(report["logits_max_abs"],float(gap.max()))
        report["top1_changes"] += int(left.argmax(1).ne(right.argmax(1)).sum())
        x,y = (F.cross_entropy(score,targets[region],reduction="none") for score in (left,right))
        report["max_abs_nll"] = max(report["max_abs_nll"],float((x-y).abs().max()))
    assert torch.isfinite(reference).all() and torch.isfinite(candidate).all()
    return report


def actual(profile,rows,plan,order,count):
    from transformers import AutoModelForCausalLM

    assert base.idle() and torch.cuda.device_count()==1 and torch.cuda.mem_get_info()[0]>=10*(1<<30)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    loaded = []
    native_loader = AutoModelForCausalLM.from_pretrained

    def retain(*args,**kwargs):
        result = native_loader(*args,**kwargs)
        loaded.append(result[0])
        return result

    with patch.object(AutoModelForCausalLM,"from_pretrained",side_effect=retain):
        head, reference, original = base.extract_features(
            dict(profile["old"],targets=rows),prior.read(base.OUT/"mapping.json"))
    assert len(loaded)==1
    teacher = loaded[0]
    versions = {name:p._version for name,p in teacher.named_parameters()}
    candidate, actual_work = gather_prefixes(teacher,plan,order,count)
    assert versions=={name:p._version for name,p in teacher.named_parameters()}
    checked = compare(reference,candidate,head,rows)
    same = profile["old"]==prior.contract()
    prior.write(OUT/"report.json",dict(reference=original,one_pass=actual_work,comparison=checked,source_preserved=same,
          peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),
          training_updates=0, checkpoint_writes=0))
    print("P109_PREFIX_ONEPASS_RESULT",original,actual_work,checked,flush=True)
    return 0 if same else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(base.CUTOFF.tzinfo)+timedelta(seconds=210)<base.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    p,*args = frozen_input()
    if phase=="prepare":
        assert not torch.cuda.is_initialized()
        OUT.mkdir(exist_ok=False)
        prior.write(OUT/"profile.json",p)
        print("P109_PREFIX_ONEPASS_CPU",p["contexts"],p["tokens"],flush=True)
        return 0
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG")==":4096:8" and p==prior.read(OUT/"profile.json")
    return actual(p,*args)


if __name__=="__main__":
    sys.exit(main())
