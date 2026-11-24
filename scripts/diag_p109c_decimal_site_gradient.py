"""Measure the new carry loss on its actual packed row and common prefix."""

import argparse
from math import fsum, isclose, sqrt
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from torch.nn import functional as F

from scripts import prepare_p109c_decimal_exposure as admission
from scripts import run_p109c_bilingual_from_raw100 as prefix
from tinylm.config import TMTConfig
from tinylm.train.anneal_schedule import quant_anneal_factor, resolve_quant_start


PREP, CORE, NATIVE = admission.PREP, admission.CORE, admission.native
PLACEMENT = admission.sources.ROOT / "handoff/audit/P109C_VERIFIED_DECIMAL_LABEL_EXPOSURE_20261124.json"


def probe():
    start = perf_counter()
    terminal = PREP.read_json(prefix.RECORD / "supervisor.json")
    receipt = PREP.read_json(prefix.RECORD / "report.json")
    model_path = PREP.ROOT / receipt["checkpoint"]
    if (terminal["returncode"] != 0 or terminal["stop_reason"] is not None
            or terminal["card_after_exit"]["compute_pids"] or receipt["optimizer_update"] != prefix.END
            or PREP.sha(model_path) != receipt["checkpoint_sha256"]):
        raise ValueError("the completed common prefix is required")
    state = torch.load(model_path, map_location="cpu", weights_only=True, mmap=True)
    context = state[CORE.trainer.CONTEXT_STATE_KEY]
    recipe = context["binding"]["recipe"]
    if (state["step"] != prefix.END or context["payload_sha256"] != receipt["context_payload_sha256"]
            or context["payload_sha256"] != CORE.state_tools._payload_sha(context)):
        raise ValueError("the native common checkpoint state and journal differ")
    placement = PREP.read_json(PLACEMENT)
    bundle, layout = NATIVE.inputs.load_inputs()
    if (placement["manifest_sha256"] != bundle.digest or placement["layout_sha256"] != layout["derived_schedule_sha256"]
            or placement["status"] != "SAME_PACKED_TEXT_DECIMAL_LABELS_VERIFIED"):
        raise ValueError("the verified events must point to this exact packed schedule")
    lane = placement["lane"]
    phase = next(piece for piece in placement["phases"] if piece["first_update"] == state["step"] + 1)
    for address in range(phase["first_update"] - 1, phase["last_update"]):
        sites = [(int(index), placement["events_by_slot"].get(str(index), []))
                 for key, index in bundle.schedule[address] if key == lane]
        sites = [(index, events) for index, events in sites if events]
        if sites:
            break
    else:
        raise ValueError("the target phase does not contain the sealed additional carry labels")
    index, events = sites[0]
    x, y, segments = bundle.data[lane][index].transpose(1, 0, 2)
    row = max(range(PREP.BATCH), key=lambda i: sum(i == r for r, _, _ in events))
    entries = [(pos, label) for line, pos, label in events if line == row]
    last = int(np.flatnonzero(segments[row])[-1]) + 1
    x, y, segments = x[row:row + 1, :last], y[row:row + 1, :last], segments[row:row + 1, :last]
    kinds = NATIVE.base.label_kinds(y, segments)[0]
    positions, labels = zip(*entries, strict=True)
    if any(kinds[pos] != 1 for pos in positions):
        raise ValueError("the additional objective must use exact first-answer positions")
    related = np.isin(segments[0], segments[0, list(positions)]) & (kinds > 0)
    active = np.flatnonzero(related)
    slots = CORE.terms.BilingualSlots(bundle, layout["layout_sha256"])
    targets = NATIVE.read_targets(bundle, slots, address)
    weights = NATIVE.load_loss_schedule(bundle, "fixed", "fixed").weights(address, targets)
    if (targets["decimals"] != 0 or not isclose(phase["phase_matched_weight"] * phase["new_active_updates"],
                                               phase["old_auxiliary_mass"])):
        raise ValueError("the selected row must be in the first added-only optimizer update")

    model = CORE.SupervisedG4(TMTConfig(**state["cfg"])).train()
    model.load_state_dict(state["model"], strict=True)
    seed = recipe["seed"]
    model.training_route = CORE.routed.route_for(model.cfg, model.owner, "uniform_r2", seed, address, bundle.steps)
    anneal = quant_anneal_factor(address, bundle.steps, recipe["sched"], recipe["anneal_shape"],
                                resolve_quant_start(bundle.warmup, bundle.steps, recipe["anneal_start"]),
                                recipe["anneal_end"])
    model.set_anneal(anneal)
    hidden = NATIVE.base.masked_hidden(model, torch.as_tensor(x.astype(np.int64)), segments, flash=False)
    logits = model._head_logits(hidden[0, active]).float()
    desired = torch.tensor(y[0, active], dtype=torch.long)
    ce_weights = torch.tensor(weights["answer_weights"], dtype=torch.float32)[kinds[active] - 1]
    ce = (F.cross_entropy(logits, desired, reduction="none") * ce_weights).sum()
    values = hidden[0, list(positions), None]
    tokens = torch.tensor(y[0, list(positions)], dtype=torch.long).unsqueeze(1)
    loss, n, correct, _ = admission.decimal.objective(model.decimal_head, values, tokens, labels, [[0]] * len(entries))
    if n != len(entries):
        raise ValueError("the existing decimal head lost an admitted target")
    aux = loss * (phase["phase_matched_weight"] / sum(len(items) for _, items in sites))
    body = tuple(p for name, p in model.named_parameters() if not name.startswith(("decimal_head.", "value_link.")))
    ordinary = torch.autograd.grad(ce, body, retain_graph=True, allow_unused=True)
    special = torch.autograd.grad(aux, body, allow_unused=True)

    def norm(grads):
        return sqrt(fsum(float(t.square().sum()) for t in grads if t is not None))

    a, b = norm(ordinary), norm(special)
    dot = fsum(float(torch.dot(g.flatten(), h.flatten())) for g, h in zip(ordinary, special, strict=True)
               if g is not None and h is not None)
    bundle.unchanged()
    return dict(status="ACTUAL_PACKED_ROW_CPU_GRADIENT_MEASURED", optimizer_updates=0, update=address+1,
                checkpoint_sha256=receipt["checkpoint_sha256"], admission_sha256=PREP.sha(PLACEMENT),
                source=admission.sources.source(Path(__file__).resolve()), physical_row=row, packed_width=last,
                whole_update_events=sum(len(e) for _, e in sites), row_events=n, labels_correct=correct,
                active_answer_targets=int(len(active)), anneal=anneal, answer_ce=float(ce.detach()),
                weighted_decimal_loss=float(aux.detach()), answer_ce_body_l2=a, auxiliary_body_l2=b,
                gradient_cosine=dot/(a*b) if a and b else None, elapsed_seconds=perf_counter()-start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("this diagnostic requires the CPU-only device mask")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    result = probe()
    CORE.native.publish(args.output.absolute(), result)
    print(result, flush=True)


if __name__ == "__main__":
    main()
