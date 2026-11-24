"""Test a joint output-row edit under explicit complete-response protection."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import train_p108_guarded_output_sidecar as previous
from scripts import run_p109c_scratch330 as publish
from scripts.eval_p109b_first_use import DecodeSuffix, strict
from tinylm.infer.generate import sample


TAG = "p108_joint_guarded_output_cpu_v1_20261123"
OUT = previous.OUT.with_name(TAG)
MARGIN = .025


def projected(model, encoded):
    x, y = torch.tensor([encoded.x]), torch.tensor(encoded.y)
    take = y >= 0
    hidden = model(x, return_hidden=True)[0, take]
    keys = F.linear(hidden, model._emb_up_w().t())
    return keys.double(), model._head_logits(hidden).double(), y[take]


def constraint_rows(keys, scores, labels, ids, margin):
    """Each mutable competitor and the strongest immutable competitor get a constraint."""
    held = scores.clone()
    held[:, ids] = -torch.inf
    held.scatter_(1, labels[:, None], -torch.inf)
    differences = scores.gather(1, labels[:, None]) - torch.cat(
        (scores[:, ids], held.max(1, keepdim=True).values), dim=1)
    rows, rhs = [], []
    impossible = 0
    width = keys.shape[-1]
    positions = {int(token): index for index, token in enumerate(ids)}
    for i, (label, key) in enumerate(zip(labels, keys, strict=True)):
        winner = positions.get(int(label))
        for competitor in range(len(ids) + 1):
            if competitor == winner:
                continue
            row = np.zeros((len(ids), width), dtype=np.float64)
            if winner is not None:
                row[winner] -= key.numpy()
            if competitor < len(ids):
                row[competitor] += key.numpy()
            gap = float(differences[i, competitor])
            required = min(MARGIN, max(gap, 0.) * .25) if margin == "protect" else MARGIN
            limit = gap - required
            norm = float(np.linalg.norm(row))
            if norm > 1e-12:
                rows.append(row.ravel() / norm)
                rhs.append(limit / norm)
            elif limit < 0:
                impossible += 1
    return rows, rhs, impossible


def project(target, constraints, limit, check):
    """Move an edit toward feasibility by coordinate updates of the inequality dual."""
    matrix = np.stack(constraints)
    limits = np.asarray(limit)
    values = target.ravel().copy()
    dual = np.zeros(len(limits))
    for iteration in range(3072):
        if iteration % 32 == 0:
            check()
            violation = float(np.max(matrix @ values - limits))
            if violation <= 1e-7:
                return values.reshape(target.shape), iteration, violation
        for i, (row, bound) in enumerate(zip(matrix, limits, strict=True)):
            change = max(-dual[i], float(row @ values) - bound)
            values -= change * row
            dual[i] += change
    return values.reshape(target.shape), iteration + 1, float(np.max(matrix @ values - limits))


def output_patch(model, ids, delta):
    original = model._head_logits

    def head(hidden):
        scores = original(hidden)
        h = F.linear(hidden, model._emb_up_w().t())
        scores[..., ids] += h @ delta.T
        return scores

    return patch.object(model, "_head_logits", head)


class FixedPrompt(DecodeSuffix):
    def encode(self, prompt):
        return SimpleNamespace(ids=self.input_ids)


def record_outputs(model, tok, requests, check):
    results = []
    for name, view, ids, reference in requests:
        check()
        capture = FixedPrompt(tok, list(ids))
        answer, meta = sample(model, model.cfg, capture, "", max_new=8, temperature=0., top_k=0,
                              device="cpu", eos_id=2, stop_token_sequences=[[4]], logits_last_only=True,
                              return_metadata=True)
        results.append(dict(root=name, view=view, target=reference, answer=answer, ids=capture.ids,
                            stop=meta["finish_reason"], correct=(strict(answer) == reference
                                                               and capture.ids[-1:] == [4])))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    parser.add_argument("--rounding-slack", type=float, default=0.)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("explicit CPU-only mode and authorized timezone-aware deadline are required")
    if not 0. <= args.rounding_slack <= .001:
        parser.error("rounding slack must be between zero and 0.001 in normalized constraint units")
    tag = TAG if not args.rounding_slack else TAG.replace("_v1_", "_fp16_slack_v2_")
    out = OUT.with_name(tag)

    def check():
        if time.time() >= args.stop_by.timestamp():
            raise TimeoutError("the authorized CPU edit window elapsed")
    check()
    began = time.monotonic()
    torch.set_num_threads(2)
    plan, (tok, _special, cases, dev, _new, _selected) = previous.prepare()
    source = previous.OUT / "trained_overlay.pt"
    source_sha = previous.trial.file_sha(source)
    saved = torch.load(source, weights_only=True, map_location="cpu")
    checkpoint = previous.solver.first.CHECKPOINT
    checksum = previous.trial.file_sha(checkpoint)
    data = torch.load(checkpoint, weights_only=True, map_location="cpu")
    model = previous.prior.TiedMLPTransformer(previous.prior.TMTConfig(**data["config"])).eval()
    model.load_state_dict(data["model"], strict=True)
    model.requires_grad_(False)
    if previous.trial.state_sha(model.state_dict()) != saved["body_sha256"]:
        raise ValueError("the edit belongs to a different frozen base body")
    model.freeze_quant()
    tokens = torch.tensor(saved["ids"], dtype=torch.long)
    initial = saved["delta"].float()
    starting = torch.load(previous.INITIAL, weights_only=True, map_location="cpu")
    if (not torch.equal(torch.as_tensor(starting["ids"]), tokens)
            or starting["body_sha256"] != saved["body_sha256"]):
        raise ValueError("the two immutable output deltas disagree")
    anchor = (2 * initial - starting["delta"].float()).double().numpy()

    guard = {root: cases["validation"][root] for root in plan["base"]["guard"]}
    focus = {root: dev[root] for root in plan["targets"]}
    A, rhs, missing = [], [], 0
    checked = 0
    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
        for values in guard.values():
            for view in previous.prior.VIEWS:
                check()
                keys, scores, y = projected(model, values["records"][view])
                after = scores.clone()
                after[:, tokens] += keys @ initial.double().T
                if not torch.equal(after.argmax(1), y):
                    continue
                rows, bounds, fixed = constraint_rows(keys, after, y, tokens, "protect")
                A.extend(rows)
                rhs.extend(bounds)
                missing += fixed
                checked += len(y)
        if not checked:
            raise ValueError("the existing protected edit has no full known-correct guard response")
        for item in focus.values():
            keys, scores, y = projected(model, item["records"]["correction"])
            scores[:, tokens] += keys @ initial.double().T
            rows, bounds, fixed = constraint_rows(keys, scores, y, tokens, "fit")
            A.extend(rows)
            rhs.extend(bounds)
            missing += fixed
        bounds = np.asarray(rhs)
        candidate, iterations, residual = project(anchor - initial.double().numpy(), A,
                                                   bounds - args.rounding_slack, check)
        actual = (initial.double() + torch.from_numpy(candidate)).half().float()
        realized = (actual - initial).double().numpy().ravel()
        max_error = float(np.max(np.stack(A) @ realized - bounds))
        artifact = dict(tag=tag, base_checkpoint_sha256=checksum, old_overlay_sha256=source_sha,
                        code_sha256=previous.trial.file_sha(Path(__file__)),
                        mutable_rows=tokens.tolist(), guard_positions=checked, inequalities=len(rhs),
                        rounding_slack=args.rounding_slack,
                        impossible_unchanged_constraints=missing, max_projected_violation=residual,
                        projected_iterations=iterations, max_fp16_violation=max_error,
                        elapsed_seconds=time.monotonic()-began)
        if not missing and max_error <= 1e-5:
            requests = [(root, view, values["prompts"][view], values["gold"])
                        for root, values in cases["test"].items() for view in previous.prior.VIEWS]
            with output_patch(model, tokens, initial):
                before = record_outputs(model, tok, requests, check)
            with output_patch(model, tokens, actual):
                after = record_outputs(model, tok, requests, check)
            artifact.update(status="PAIRED_GENERATION_COMPLETE", before=before, after=after,
                            before_correct=sum(row["correct"] for row in before),
                            after_correct=sum(row["correct"] for row in after),
                            lost_correct=sum(a["correct"] and not b["correct"] for a,b in zip(before,after,strict=True)),
                            altered_protected_sequences=sum(a["correct"] and a["ids"]!=b["ids"]
                                                            for a,b in zip(before,after,strict=True)))
        else:
            artifact.update(status="NO_FEASIBLE_FP16_PROPOSAL", changed_base_weights=False)
    if previous.trial.file_sha(checkpoint) != checksum or previous.trial.file_sha(source) != source_sha:
        raise ValueError("an original checkpoint or sidecar changed")
    out.mkdir(exist_ok=False)
    publish.publish(out / "report.json", artifact)
    print(tag, artifact["status"], artifact["max_fp16_violation"], flush=True)


if __name__ == "__main__":
    main()
