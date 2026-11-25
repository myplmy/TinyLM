"""Use the first differing answer token in the existing per-fact rank objective."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_conditional_margin_cpu as reference


REF, PRIOR = reference.REF, reference.prior
OUT = REF.EVIDENCE / "p109c_first_branch_margin_cpu_20261126"
END = datetime.fromisoformat("2026-11-26T06:46:00+09:00")
ORIGINAL_UPDATE = reference.update_batch
SOURCE = reference.OUT / "report.json"


def branch_positions(rows):
    stakes = []
    offset = 0
    for yes, no in zip(rows[::2], rows[1::2], strict=True):
        ytokens, ys, yl, _ = yes
        ntokens, ns, nl, _ = no
        if (ys != ns or ytokens[:ys+1] != ntokens[:ns+1]
                or len(ytokens) != ys+yl+2 or len(ntokens) != ns+nl+2):
            raise ValueError("two candidate rows must share the fixed question prefix and EOT layout")
        for step, (left, right) in enumerate(zip(ytokens[ys+1:], ntokens[ns+1:])):
            if left != right:
                stakes.append((offset + step, left, right))
                break
        else:
            raise ValueError("the accepted and rejected token continuations must diverge")
        offset += yl+nl+2
    return stakes


def update_with_branch(model, rows, replay, derivatives):
    original_head = model._head_logits
    observed = []

    def capture(hidden):
        logits = original_head(hidden)
        observed.append(logits)
        return logits

    with patch.object(model, "_head_logits", capture):
        ce, raw, body_yes, body_no, _, counts = ORIGINAL_UPDATE(model, rows, replay)
    if len(observed) != 1:
        raise ValueError("the equal-compute comparison requires one fixed shared output calculation")
    logits = observed[0].float()
    positions, accepted_yes, accepted_no = torch.tensor(branch_positions(rows), dtype=torch.long).T
    branch = logits[positions, accepted_yes] - logits[positions, accepted_no]
    yes, no = branch[::2], branch[1::2]
    with torch.no_grad():
        magnitude = lambda a, b: float(torch.cat(((.5-a).sigmoid(), (.5+b).sigmoid())).mean() * .5)
        derivatives.append([magnitude(body_yes, body_no), magnitude(yes, no)])
    return ce, raw, yes, no, yes-no, counts


def run(profile, tokenizer, checkpoint, encoded, heldout, original, replay, val, baseline, cutoff):
    derivatives = []
    torch.manual_seed(profile["seed"])
    model = REF.completed.load_model(checkpoint, 2942, "cpu")

    def update(owner, rows, past):
        return update_with_branch(owner, rows, past, derivatives)

    with (sdpa_kernel(SDPBackend.MATH), patch.multiple(reference, OUT=OUT, update_batch=update)):
        training = reference.train_arm(model, "per_fact", profile, encoded, replay, cutoff)
        weight = OUT / "first_branch_body.pt"
        with weight.open("xb") as stream:
            torch.save(dict(model=model.state_dict(), parent_sha256=profile["parent_sha256"], post_updates=PRIOR.STEPS,
                            schema="P109C_FIRST_BRANCH_MARGIN_V1"), stream)
        assessment = PRIOR.assess(model, tokenizer, heldout, original, val, cutoff)
        margins = reference.read_margins(model, tokenizer, heldout, cutoff)
    original_arm = baseline["arms"]["per_fact"]
    summary = dict(training=training, weights_sha256=REF.file_sha(weight),
                   generated=reference.generation_counts(assessment["new_rules"]["rows"]),
                   previous=reference.generation_counts(assessment["previous_dev"]["rows"]),
                   scores=margins["summary"], raw_nll=assessment["raw_val_nll"])
    gain = {lang: summary["generated"][lang]["both_correct"] - original_arm["generated"][lang]["both_correct"]
            for lang in ("all", "ko", "en")}
    raw_delta = summary["raw_nll"] - baseline["parent_raw_nll"]
    gates = dict(free=gain["all"] >= 4 and gain["ko"] >= 2 and gain["en"] >= 0,
                 old_rules=all(summary["previous"][lang]["both_correct"] >= original_arm["previous"][lang]["both_correct"]
                               for lang in ("ko", "en")), raw_parent=raw_delta <= .005)
    if REF.file_sha(checkpoint) != profile["parent_sha256"]:
        raise ValueError("the frozen parent body changed")
    REF.native.publish(OUT / "assessment.json", dict(assessment=assessment, margins=margins["rows"]))
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", summary=summary, gains=gain,
                                                raw_delta_parent=raw_delta, gates=gates,
                                                sensitivity_per_micro=derivatives,
                                                inputs_sha256=REF.file_sha(OUT / "inputs.json")))
    print("P109C_FIRST_BRANCH", json.dumps(dict(gains=gain, raw_delta=raw_delta, gates=gates)), flush=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 and return before fixed raw validation")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile, tokenizer, checkpoint, encoded, heldout, old, replay, val = reference.prepare()
    baseline = REF.completed.read_json(SOURCE)
    if (profile != REF.completed.read_json(reference.PROFILE) or baseline["status"] != "COMPLETE"
            or baseline["profile_sha256"] != REF.file_sha(reference.PROFILE)):
        raise ValueError("the three completed prior arms must match the current training inputs")
    if any(len(branch_positions(rows)) != 2 for rows in encoded):
        raise ValueError("both facts in every prior training pair require defined branch comparisons")
    OUT.mkdir(exist_ok=False)
    REF.native.publish(OUT / "inputs.json", dict(previous_profile=profile, previous_report_sha256=REF.file_sha(SOURCE),
                                                source_sha256=REF.file_sha(Path(__file__)),
                                                objective="per_fact_margin_from_first_differing_token",
                                                gates=dict(all=4, ko=2, en=0, old_rules=0, raw_parent=.005)))
    run(profile, tokenizer, checkpoint, encoded, heldout, old, replay, val, baseline, args.stop_by.timestamp())


if __name__ == "__main__":
    main()
