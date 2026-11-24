"""Continue two native arms from the same supervised prefix, varying transfer."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import gc
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import run_p109c_bilingual_from_raw100 as warm
from scripts import run_p109c_bilingual_value_transfer as previous
from tinylm.config import TMTConfig


prep, supervised, inputs, native = warm.prep, warm.supervised, warm.inputs, warm.native
terms, data, trial = warm.terms, previous.data, previous.trial
TAG = "p109c_bilingual_native_transfer_matched_chat32_v2_20261124"
RECORD = prep.EVIDENCE / TAG
WARM_PROFILE = prep.ROOT / "handoff/audit/P109C_BILINGUAL_SUPERVISED_FROM_RAW100_V3_20261124.json"
START, END = warm.END, 320
ARMS = {"control": 0., "transfer": previous.PAIR_WEIGHT}
COURSE, LOCATION = .25, .02
EXPOSURE = ("source_update", "reserved_batches", "empty_batches", "actual_forwards", "raw_targets",
            "course_inputs", "answer_targets", "answer_weights", "context_targets", "location_targets",
            "relation_questions", "decimal_targets", "raw_context_weight", "route_visits")


class SavedBoundary(Exception):
    """The matched continuation has written its final checkpoint."""


def evaluation_panel(slots):
    original_path = previous.baseline.INPUT / "validation.json"
    original = trial.read_json(original_path)
    translated_profile, (tokenizer, symbols, _, translated) = previous.crossed.prepare()
    panel = dict(exchange=original["exchange"], question_switch=original["question_switch"], translated=translated)
    prompts = {tuple(prompt) for rows in panel.values() for row in rows for prompt in row["prompts"]}
    lookups = {np.asarray(prompt, dtype=np.uint16).tobytes() for prompt in prompts}
    widths = {len(prompt) for prompt in prompts}
    overlaps = sum(row[:int(site) + 1].tobytes() in lookups
                   for row, site in zip(slots.tokens, slots.sites[:, 0], strict=True) if int(site) + 1 in widths)
    if overlaps:
        raise ValueError(f"the evaluation prompts overlap {overlaps} added bilingual training prefixes")
    proof = dict(original_sha256=trial.file_sha(original_path), translation=translated_profile,
                 prompt_counts={name: len(rows) * 2 for name, rows in panel.items()},
                 distinct_prompts=len(prompts), bilingual_training_prefix_overlaps=overlaps)
    return proof, tokenizer, symbols, panel


def prepare():
    shared, bundle, slots = warm.prepare()
    if shared != prep.read_json(WARM_PROFILE) or not START < END < bundle.steps or END % warm.BOUNDARY:
        raise ValueError("the comparison requires the sealed shared 160-update plan")
    heldout, tokenizer, symbols, panel = evaluation_panel(slots)
    addresses = []
    for address in range(START, END):
        batch, target = bundle.schedule[address], slots.at(address)
        addresses.append(dict(source_update=address + 1, reserved_batches=len(batch),
                              empty_batches=int((batch[:, 0] == -2).sum()),
                              raw_targets=int((batch[:, 0] == -1).sum()) * supervised.base.MICRO_TOKENS,
                              context_targets=len(target.context_targets) if target else 0,
                              location_targets=len(target.value_classes) if target else 0,
                              bilingual_pairs=len(target.gold) if target else 0))
    pins = dict(shared["sources"])
    for module in (previous, previous.crossed, data):
        path = Path(module.__file__).resolve()
        pins[str(path.relative_to(prep.ROOT))] = prep.sha(path)
    here = Path(__file__).resolve()
    pins[str(here.relative_to(prep.ROOT))] = prep.sha(here)
    plan = dict(tag=TAG, sources=pins, parent_profile_sha256=prep.sha(WARM_PROFILE), heldout=heldout, arms=ARMS,
                source_updates=addresses, start_update=START, end_update=END, boundary=warm.BOUNDARY,
                validation_batches=shared["validation_batches"], course_ce=COURSE, value_ce=LOCATION)
    return plan, shared, bundle, slots, (tokenizer, symbols, panel)


def source_checkpoint(shared, plan):
    report, terminal = (prep.read_json(warm.RECORD / name) for name in ("report.json", "supervisor.json"))
    if (report["status"] != "SHARED_SUPERVISED_PREFIX_COMPLETE" or report["profile"] != shared
            or prep.sha(WARM_PROFILE) != plan["parent_profile_sha256"] or report["optimizer_update"] != START
            or report["actual_updates"] != START - warm.START or terminal["returncode"] != 0
            or terminal["stop_reason"] is not None or terminal["card_after_exit"]["compute_pids"]):
        raise ValueError("the comparison requires the completed and returned supervised prefix")
    path = prep.ROOT / report["checkpoint"]
    if path.resolve(strict=True) != path or prep.sha(path) != report["checkpoint_sha256"]:
        raise ValueError("the shared checkpoint file differs from the parent report")
    state = torch.load(path, map_location="cpu", mmap=True, weights_only=True)
    key = supervised.trainer.CONTEXT_STATE_KEY
    ctx = state[key]
    if (state["step"] != START or ctx["cursor"]["cursor"]["next_update"] != START
            or ctx["payload_sha256"] != report["context_payload_sha256"]
            or ctx["payload_sha256"] != supervised.state_tools._payload_sha(ctx)
            or ctx["binding"]["recipe"]["p109c_bilingual_supervised"] != shared
            or state[warm.ORIGIN] != report["origin"]):
        raise ValueError("the optimizer, curriculum and RNG must be those of the same parent")
    return state, report


def branch_context(context, target):
    tools = supervised.state_tools
    old = context["binding"]
    tools._validate_binding(old)
    tools._validate_binding(target)
    permitted = {"p109c_bilingual_supervised", "tag"}
    if (any(old.get(key) != target.get(key) for key in set(old) | set(target) if key not in {"recipe", "binding_sha256"})
            or any(old["recipe"].get(key) != target["recipe"].get(key)
                   for key in set(old["recipe"]) | set(target["recipe"]) if key not in permitted)):
        raise ValueError("the comparison changed the shared native optimizer or data binding")
    result = dict(context, binding=target)
    result["payload_sha256"] = tools._payload_sha(result)
    return result


def run_arm(name, record, cutoff, plan, parent, origin, bundle, slots, progress):
    tag = f"{TAG}_{name}"
    record.mkdir()
    folder = record / "ckpt"
    folder.mkdir()
    _, display = supervised.base.native_commands(bundle, tag, resume=True)
    checkpoint = folder / inputs.training.checkpoint_name(display, tag)
    key = supervised.trainer.CONTEXT_STATE_KEY
    original_binding = supervised.state_tools.make_binding
    original_save = supervised.saves.save_packed_checkpoint
    original_aux = terms.auxiliary
    applied = []
    arm = dict(plan, active_arm=name, active_transfer=ARMS[name], parent=origin)
    tools = supervised.state_tools
    parent_binding = parent[key]["binding"]
    previous_route = parent_binding["recipe"][supervised.routed.RECIPE_KEY]
    recipe = dict(parent_binding["recipe"], tag=tag, p109c_bilingual_supervised=arm)
    expected_binding = {field: value for field, value in parent_binding.items() if field != "binding_sha256"}
    expected_binding["recipe"] = tools._canonical(recipe)
    expected_binding["binding_sha256"] = tools._sha(expected_binding)
    derived = dict(parent, **{key: branch_context(parent[key], expected_binding)})
    original_save(checkpoint, derived)
    del derived
    print(json.dumps(dict(arm=name, rebound_update=START)), file=progress, flush=True)

    def adopt(layout, recipe, cache, device):
        bound = original_binding(layout, dict(recipe, **{supervised.routed.RECIPE_KEY: previous_route}), cache, device)
        if bound != expected_binding:
            changed = [field for field in expected_binding if bound[field] != expected_binding[field]]
            raise ValueError(f"the native CLI comparison binding differs in {changed}")
        return bound

    def transfer(model, hidden, target, transfer_weight):
        if transfer_weight != 0:
            raise ValueError("the driver owns the only variable transfer coefficient")
        context, location, loss, stats = original_aux(model, hidden, target, transfer_weight=previous.PAIR_WEIGHT)
        stats["transfer_eligible"] = stats["transfer_pairs"]
        if name == "control":
            loss = torch.zeros_like(loss)
            stats.update(transfer_pairs=0, weighted_transfer=0.)
        return context, location, loss, stats

    def observe(row):
        index = len(applied)
        updated = {"bilingual_pairs": 0, "transfer_eligible": 0, "transfer_pairs": 0, "weighted_transfer": 0., **row}
        if (row["step"] != START + index + 1
                or any(updated[k] != value for k, value in plan["source_updates"][index].items())
                or row["actual_forwards"] != row["reserved_batches"] - row["empty_batches"]
                or updated["transfer_pairs"] != (updated["transfer_eligible"] if name == "transfer" else 0)):
            raise ValueError("the native journal differed from the matched optimizer plan")
        applied.append(updated)
        print(json.dumps(dict(arm=name, step=row["step"], eligible=updated["transfer_eligible"])),
              file=progress, flush=True)

    def save(main, path, payload):
        if path != main:
            return
        if path != checkpoint or payload["step"] != START + len(applied):
            raise ValueError("the applied native journal and checkpoint must end together")
        payload["p109c_matched_transfer_origin"] = dict(origin, arm=name, transfer_weight=ARMS[name])
        original_save(path, payload)
        if payload["step"] == END:
            raise SavedBoundary()

    try:
        with (patch.object(supervised.state_tools, "make_binding", adopt), patch.object(terms, "auxiliary", transfer),
              patch.object(supervised, "COURSE_SHARE", COURSE), patch.object(supervised, "VALUE_WEIGHT", LOCATION)):
            supervised.native_training(bundle, slots, record, tag, cutoff, profile=arm, addresses=range(bundle.steps),
                                       resume=True, save=save, observe=observe)
    except SavedBoundary:
        pass
    else:
        raise RuntimeError("the partial arm passed its sealed stop without saving")
    if len(applied) != END - START:
        raise ValueError("the native arm did not apply every planned optimizer update")
    return checkpoint, applied


def score(checkpoint, setup, record, progress, name, cutoff):
    tokenizer, symbols, panel = setup
    state = torch.load(checkpoint, map_location="cpu", mmap=True, weights_only=True)
    key = supervised.trainer.CONTEXT_STATE_KEY
    if (state["step"] != END or state[key]["cursor"]["cursor"]["optimizer_updates"] != END
            or state[key]["payload_sha256"] != supervised.state_tools._payload_sha(state[key])):
        raise ValueError("the evaluation must use the final matched-arm checkpoint")
    model = supervised.SupervisedG4(TMTConfig(**state["cfg"])).to("cuda").eval()
    model.load_state_dict(state["model"], strict=True)
    model.clear_quant()
    unique = list(dict.fromkeys(tuple(prompt) for rows in panel.values() for row in rows for prompt in row["prompts"]))
    answers = {}
    for offset in range(0, len(unique), data.BATCH):
        if time.time() >= cutoff:
            raise TimeoutError("the authorized evaluation window ended")
        block = unique[offset:offset + data.BATCH]
        decoded = data.decoded(model, tokenizer, symbols, [list(prompt) for prompt in block])
        answers.update(zip(block, decoded, strict=True))
        print(json.dumps(dict(arm=name, decoded_unique=len(answers))), file=progress, flush=True)

    def recorded(_model, _tokenizer, _symbols, prompts):
        return [answers[tuple(prompt)] for prompt in prompts]

    metrics = {}
    with patch.object(data, "decoded", recorded):
        for subject, rows in panel.items():
            report = data.evaluate(model, tokenizer, symbols, rows, paired=True)
            native.publish(record / f"{subject}.json", report)
            metrics[subject] = {key: value for key, value in report.items() if key != "rows"}
    return dict(checkpoint=str(checkpoint.relative_to(prep.ROOT)), checkpoint_sha256=prep.sha(checkpoint),
                generation=metrics, unique_generated=len(answers), last_validation=state[key]["control"]["history"][-1])


def worker(path, digest, _resume, record, cutoff):
    with (inputs.training.locked_record(record),
          (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress,
          redirect_stdout(log), redirect_stderr(log)):
        sealed = json.loads(native.manifest_bytes(path, digest))
        plan, shared, bundle, slots, panel = prepare()
        if plan != sealed or torch.cuda.device_count() != 1 or time.time() >= cutoff:
            raise ValueError("the matched arms require the sealed data, approved GPU and time")
        state, report = source_checkpoint(shared, plan)
        warm.inherit_threads(state)
        origin = dict(checkpoint_sha256=report["checkpoint_sha256"], context_sha256=report["context_payload_sha256"])
        free, total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("no usable GPU allocation budget")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        exposures, outcomes = {}, {}
        for name in ARMS:
            subdir = record / name
            torch.cuda.reset_peak_memory_stats()
            checkpoint, updates = run_arm(name, subdir, cutoff, plan, state, origin, bundle, slots, progress)
            training_peak = torch.cuda.max_memory_allocated() / 2**20
            native.publish(subdir / "updates.json", updates)
            exposures[name] = [{key: row[key] for key in EXPOSURE} for row in updates]
            gc.collect()
            torch.cuda.empty_cache()
            out = score(checkpoint, panel, subdir, progress, name, cutoff)
            outcomes[name] = dict(out, updates=len(updates), training_peak_allocated_mib=training_peak,
                                  transfer_eligible=sum(row["transfer_eligible"] for row in updates),
                                  transferred_pairs=sum(row["transfer_pairs"] for row in updates),
                                  bilingual_pairs=sum(row["bilingual_pairs"] for row in updates))
            gc.collect()
            torch.cuda.empty_cache()
        if exposures["control"] != exposures["transfer"]:
            raise ValueError("the arms executed different input or forward exposure")
        native.publish(record / "report.json", dict(status="MATCHED_NATIVE_TRANSFER_MEASURED", profile=plan,
                                                    shared=origin, outcomes=outcomes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        plan, *_ = prepare()
        native.publish(args.profile, plan)
        print(prep.sha(args.profile), len(plan["source_updates"]), flush=True)
        return 0
    if (not args.profile_sha256 or not args.stop_by or not args.stop_by.tzinfo
            or args.stop_by > inputs.AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("the sealed profile and approved CUDA device and time are required")
    return inputs.supervisor.supervise(worker, args.profile.absolute(), args.profile_sha256, RECORD, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
