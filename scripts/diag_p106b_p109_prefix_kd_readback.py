"""Read back paired held results and exact token work for prefix extraction."""

from collections import defaultdict, Counter
import os
from pathlib import Path

import torch

from scripts import diag_p106b_p109_actual_prefix_kd as prior


TAG = "p106b_p109_prefix_kd_readback_v1_20261119"
OUT = prior.OUT.with_name(TAG)


def compare(left, right):
    assert [r["id"] for r in left] == [r["id"] for r in right]
    groups = defaultdict(list)
    for a,b in zip(left,right,strict=True):
        assert (a["language"],a["family"],a["count"]) == (b["language"],b["family"],b["count"])
        groups[(a["language"],a["family"])].append((a,b))
    rows = []
    for (lang,family),pairs in sorted(groups.items()):
        count = sum(l["count"] for l,_ in pairs)
        nll = sum(r["sum_nll"]-l["sum_nll"] for l,r in pairs)/count
        right_shift = sum(r["correct"]-l["correct"] for l,r in pairs)
        rows.append(dict(language=lang,family=family,docs=len(pairs),tokens=count,kd_minus_ce_nll=nll,
                         kd_minus_ce_top1=right_shift))
    return rows


def work(rows,docs):
    keys = {tuple(r["teacher_prefix"]) for r in rows}
    already = set()
    longest = {}
    for row in rows:
        if row["stable"]:
            query = tuple(row["teacher_prefix"])
            d = row["doc"]
            assert tuple(docs[d]["teacher_ids"][:len(query)]) == query
            already.add(query)
            if len(query) > len(longest.get(d,())):
                longest[d] = query
    fallback = keys - already
    full = set(longest.values())
    assert keys == already | fallback and not(full & fallback)
    original_tokens = sum(map(len,keys))
    one_pass_tokens = sum(map(len,full)) + sum(map(len,fallback))
    batch_count = sum((count+31)//32 for count in Counter(map(len,keys)).values())
    return dict(original_unique_queries=len(keys), original_teacher_tokens=original_tokens,
                original_batches=batch_count, covered_unique_queries=len(already),
                one_pass_document_calls=len(full), fallback_calls=len(fallback),
                projected_teacher_tokens=one_pass_tokens,
                projected_reduction=1-one_pass_tokens/original_tokens)


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    torch.set_num_threads(1)
    profile_path, report_path = prior.OUT/"profile.json", prior.OUT/"report.json"
    raw, report = prior.read(profile_path), prior.read(report_path)
    receipt,_,rows = prior.data_and_receipt()
    assert receipt == raw["data"] and report["source_preserved"] and report["same_initial_and_first_ce"]
    groups = {}
    for step,left in report["arms"]["ce"]["held"].items():
        right = report["arms"]["prefix_kd"]["held"][step]
        paired = compare(left["documents"],right["documents"])
        for lang in ("en","ko"):
            values = [r for r in paired if r["language"]==lang]
            weighted = sum(r["kd_minus_ce_nll"]*r["tokens"] for r in values)/sum(r["tokens"] for r in values)
            assert abs(weighted-(right["summary"][lang]["nll"]-left["summary"][lang]["nll"]))<1e-12
        groups[step]=paired
    costs = work(rows,receipt["documents"])
    assert costs["original_unique_queries"]==report["teacher"]["unique_prefixes"]
    assert costs["original_batches"]==report["teacher"]["forward_batches"]
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    prior.write(OUT/"report.json",dict(tag=TAG, profile_sha=prior.sha(profile_path), report_sha=prior.sha(report_path),
          script_sha=prior.sha(Path(__file__)), paired_topic_rows=groups, teacher_work=costs,
          new_model_execution=0, one_pass_actual=False))
    print("P109_PREFIX_KD_READBACK",costs, groups["64"],flush=True)


if __name__=="__main__":
    main()
