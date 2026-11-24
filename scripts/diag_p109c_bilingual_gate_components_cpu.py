"""Locate the binding constraint in the trained bilingual answer-transfer gate."""

import argparse
from collections import Counter
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from scripts import run_p109c_bilingual_transfer_matched as matched
from tinylm.config import TMTConfig
from tinylm.train.anneal_schedule import quant_anneal_factor, resolve_quant_start


warm, native, prep = matched.warm, matched.native, matched.prep
START = 400
ADDRESSES = tuple(range(START, START + 8 * 17, 17))


def checkpoint(model_file, step, expected, bundle):
    stamp = prep.sha(model_file)
    state = torch.load(model_file, map_location="cpu", weights_only=True, mmap=True)
    context = state[warm.supervised.trainer.CONTEXT_STATE_KEY]
    if (stamp != expected or state["step"] != step or context["cursor"]["cursor"]["optimizer_updates"] != step
            or warm.supervised.state_tools._payload_sha(context) != context["payload_sha256"]
            or context["binding"]["cache"] != bundle.cache):
        raise ValueError("the checkpoint does not match the measured optimizer boundary")
    plan = context["binding"]["recipe"]
    model = warm.supervised.SupervisedG4(TMTConfig(**state["cfg"]))
    model.load_state_dict(state["model"], strict=True)
    model.eval()
    start = resolve_quant_start(bundle.warmup, bundle.steps, plan["anneal_start"])
    model.set_anneal(quant_anneal_factor(step - 1, bundle.steps, plan["sched"], plan["anneal_shape"], start,
                                         plan["anneal_end"]))
    model.freeze_quant()
    return model


def counts(model, bundle, slots):
    tallies = Counter()
    with torch.inference_mode():
        for address in ADDRESSES:
            target = slots.at(address)
            if target is None:
                raise ValueError("each selected future update must have paired labels")
            x, _, segments = bundle.data[slots.lane][address - bundle.warmup].transpose(1, 0, 2)
            populated = int(np.count_nonzero(segments, axis=1).max())
            ids = torch.as_tensor(x[:, :populated].astype(np.int64))
            hidden = bundle.packed_hidden(model, ids, segments[:, :populated], flash=False,
                                          hidden=warm.supervised.base.masked_hidden)
            features = target.features(hidden)
            classes = torch.arange(features.shape[1]).expand(len(features), -1)
            ranked = model.value_link(features, classes).float().argmax(-1)
            correct_sites = ranked.eq(torch.as_tensor(target.value_classes, dtype=torch.long))
            both_sites = correct_sites.reshape(-1, 2).all(-1)
            logits = model._head_logits(features[:, 0]).float()
            choices, unique, gold = target.candidates(logits.device)
            ko, en = logits.argmax(-1).reshape(-1, 2).eq(gold[:, None]).T
            en_choices = logits[1::2].gather(1, choices).masked_fill(~unique, -torch.inf)
            en_choice_right = choices.gather(1, en_choices.argmax(1, keepdim=True)).reshape(-1).eq(gold)
            distinct = unique.sum(-1) > 1
            first_gate = en & ~ko & distinct
            _, accepted = matched.previous.selected_transfer(logits, choices, unique, gold, correct_sites)
            gates = {
                "en_full": en, "ko_full": ko, "en_restricted": en_choice_right, "both_value_sites": both_sites,
                "en_full_ko_wrong_distinct": first_gate, "en_full_ko_wrong_both_sites": first_gate & both_sites,
                "incorrect_en_restricted_both_sites": ~en_choice_right & ~ko & both_sites & distinct,
            }
            if int(accepted) != int(gates["en_full_ko_wrong_both_sites"].sum()):
                raise ValueError("the subgroup count differs from the actual training gate")
            tallies.update({"pairs": len(gold), **{key: int(value.sum()) for key, value in gates.items()}})
    return dict(tallies)


def run():
    started = perf_counter()
    profile, shared, bundle, slots, _ = matched.prepare()
    del shared
    prefix_report = prep.read_json(warm.RECORD / "report.json")
    prefix_file = prep.ROOT / prefix_report["checkpoint"]
    control = matched.RECORD / "control"
    control_rows = prep.read_json(control / "updates.json")
    _, display = warm.supervised.base.native_commands(bundle, f"{matched.TAG}_control", resume=False)
    branch_file = control / "ckpt" / warm.inputs.training.checkpoint_name(display, f"{matched.TAG}_control")
    if (len(control_rows) != matched.END - matched.START or control_rows[-1]["step"] != matched.END
            or any(row["transfer_pairs"] for row in control_rows)):
        raise ValueError("use the already finished and scored control branch")
    checkpoint_stamps = {"prefix160": prefix_report["checkpoint_sha256"], "control320": prep.sha(branch_file)}
    arms = (("prefix160", prefix_file, matched.START), ("control320", branch_file, matched.END))
    results = {}
    for name, path, step in arms:
        model = checkpoint(path, step, checkpoint_stamps[name], bundle)
        results[name] = counts(model, bundle, slots)
        del model
        if checkpoint_stamps[name] != prep.sha(path):
            raise ValueError("the original checkpoint changed during the probe")
    bundle.unchanged()
    return dict(status="TRAINED_VALUE_AND_ANSWER_GATE_CPU_MEASURED", source_sha256=prep.sha(Path(__file__).resolve()),
                results=results, checkpoint_sha256=checkpoint_stamps, placement=profile["sources"],
                source_updates=[item + 1 for item in ADDRESSES], seconds=perf_counter()-started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("the gate diagnostic requires the CPU-only mask")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    summary = run()
    native.publish(args.output.absolute(), summary)
    print(summary["status"], summary["results"], flush=True)


if __name__ == "__main__":
    main()
