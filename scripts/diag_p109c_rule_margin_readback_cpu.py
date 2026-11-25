"""Read condition sensitivity in the three already-frozen P109C bodies."""

from argparse import ArgumentParser
from datetime import datetime
import os
from pathlib import Path
from statistics import median

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_rule_counterfactual_training_cpu as prior
from scripts import diag_p109c_rule_label_position_cpu as scoring


TAG = "p109c_rule_margin_readback_cpu_20261125"
PROFILE = prior.reference.EVIDENCE / f"{TAG}_profile.json"
OUT = prior.reference.EVIDENCE / f"{TAG}.json"
END = datetime.fromisoformat("2026-11-25T13:00:00+09:00")
METRICS = ("body", "body_mean", "with_eot")


def check(cutoff):
    if (not datetime.now().astimezone() < cutoff <= END or os.sched_getaffinity(0) != prior.CPUS
            or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        raise ValueError("the permitted CPU mode or deadline differs")


def prepare():
    old, tokenizer, checkpoint, train, heldout, *_ = prior.prepare()
    completed = prior.reference.completed
    if old != completed.read_json(prior.PROFILE):
        raise ValueError("the original frozen fixture differs")
    report = completed.read_json(prior.RECORD / "report.json")
    if report["status"] != "COMPLETE" or report["profile"] != old:
        raise ValueError("the source comparison is incomplete")
    seen = [row for row in train if int(row["id"].rsplit("-", maxsplit=1)[-1]) in (0, 5, 10, 15)]
    if len(seen) != 64 or len(heldout) != 40:
        raise ValueError("the sealed family coverage differs")
    profile = dict(
        tag=TAG, seen_pairs=len(seen), heldout_pairs=len(heldout), max_source_updates=64,
        sources={path.name: prior.reference.file_sha(path) for path in
                 (Path(__file__), Path(scoring.__file__), Path(prior.__file__), prior.PROFILE, prior.RECORD / "report.json")},
        source_models={"baseline": prior.reference.CHECKPOINT_SHA256,
                       **{arm: record["body_sha256"] for arm, record in report["training"].items()}},
        panels={"seen": prior.json_digest(seen), "heldout": prior.json_digest(heldout)},
        selection="Four fixed serial positions per language and trained family, all held-out pairs.",
        primary="Signed body-logp difference of differences; separate from two correct argmaxes.",
        cpu_affinity=sorted(prior.CPUS), threads=prior.THREADS,
    )
    return profile, tokenizer, checkpoint, {"seen": seen, "heldout": heldout}


def load_model(name, profile, checkpoint):
    model = prior.reference.completed.load_model(checkpoint, 2942, "cpu")
    if name != "baseline":
        path = prior.reference.completed.regular_file(prior.RECORD / f"{name}_body.pt")
        if prior.reference.file_sha(path) != profile["source_models"][name]:
            raise ValueError("a trained diagnostic body has changed")
        payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        if (payload["schema"] != "P109C_CPU_PAIRED_RULE_DIAGNOSTIC" or payload["arm"] != name
                or payload["post_updates"] != 64 or payload["parent_sha256"] != profile["source_models"]["baseline"]):
            raise ValueError("a trained diagnostic header differs")
        model.clear_quant()
        model.load_state_dict(payload["model"], strict=True)
        model.freeze_quant()
    return model


def read_case(model, tokenizer, case):
    measurements = []
    labels = prior.reference.LABELS[case["language"]]
    for prompt in case["prompts"]:
        prefix, answers = scoring.continuations(tokenizer, scoring.chat(prompt), labels)
        yes, no = [scoring.scores(model, prefix, answer, 4) for answer in answers]
        body = yes["body"] - no["body"]
        measurements.append(dict(body=body, body_mean=yes["body_mean"] - no["body_mean"],
                                 with_eot=body + yes["eot"] - no["eot"]))
    return dict(id=case["id"], family=case["family"], language=case["language"], yes=measurements[0], no=measurements[1])


def summarize(rows):
    result = {}
    for language in ("all", "en", "ko"):
        subset = [row for row in rows if language == "all" or row["language"] == language]
        result[language] = {}
        for metric in METRICS:
            values = [(row["yes"][metric], row["no"][metric]) for row in subset]
            result[language][metric] = dict(
                pairs=len(values), same_side=sum((a > 0) == (b > 0) for a, b in values),
                direction=sum(a > b for a, b in values), both_correct=sum(a > 0 > b for a, b in values),
                median_shift=median(a - b for a, b in values), median_offset=median((a + b) / 2 for a, b in values),
            )
    return result


@torch.inference_mode()
def run(profile, tokenizer, checkpoint, panels, cutoff):
    torch.set_num_threads(prior.THREADS)
    torch.set_num_interop_threads(1)
    reports = {}
    with sdpa_kernel(SDPBackend.MATH):
        for name in profile["source_models"]:
            model = load_model(name, profile, checkpoint)
            arms = {}
            for panel, cases in panels.items():
                rows = []
                for case in cases:
                    check(cutoff)
                    rows.append(read_case(model, tokenizer, case))
                arms[panel] = dict(summary=summarize(rows), rows=rows)
                print(f"{name} {panel} {arms[panel]['summary']['all']['body']}", flush=True)
            reports[name] = arms
            del model
    prior.reference.native.publish(OUT, dict(profile=profile, profile_sha256=prior.reference.file_sha(PROFILE),
                                            models=reports))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    check(args.stop_by)
    profile, *assets = prepare()
    if args.action == "seal":
        prior.reference.native.publish(PROFILE, profile)
        print(prior.reference.file_sha(PROFILE), flush=True)
    elif (args.profile_sha256 != prior.reference.file_sha(PROFILE)
          or profile != prior.reference.completed.read_json(PROFILE)):
        parser.error("the frozen score request and input hash differ")
    else:
        run(profile, *assets, args.stop_by)


if __name__ == "__main__":
    main()
