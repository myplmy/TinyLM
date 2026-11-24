"""Run the native P109C optimizer with the sealed bilingual supervision."""

from dataclasses import dataclass, replace
from functools import partial
import sys
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109c_bilingual_terms as terms
from scripts import p109c_packed_relation_objective as relation
from tinylm import cli
from tinylm.train import context_micro_tokens, packed_document_training as saves


base, prep = terms.mixed, terms.prep
trainer, state_tools, routed = base.trainer, base.context_training_state, base.routed
native = base.native
value_head = terms.audited.original.baseline.ValueLink
COURSE_SHARE = .25
VALUE_WEIGHT = .02


@dataclass(frozen=True)
class CourseMicrobatch:
    segments: np.ndarray
    positives: np.ndarray
    kinds: np.ndarray
    groups: list
    decimal: list
    bilingual: terms.BilingualTargets | None


def course_microbatch(bundle, slots, address, lane, index):
    x, y, segments = bundle.data[lane][index].transpose(1, 0, 2)
    aux = bundle.aux[lane][index]
    groups = relation.relation_groups_for(aux, prep.BATCH)
    kinds = base.label_kinds(y, segments)
    relation.keep_relation_winners(kinds, segments, groups)
    if any(kinds[row, column] != 1 for row, column, _ in aux["decimal"]):
        raise ValueError("decimal supervision must align with the first answer")
    bilingual = slots.at(address) if lane == slots.lane else None
    if lane == slots.lane and bilingual is None:
        raise ValueError("a scheduled bilingual batch must have sealed targets")
    return x, y, CourseMicrobatch(segments, np.flatnonzero(y.ravel() != prep.IGNORE),
                                  kinds, groups, aux["decimal"], bilingual)


def course_objective(model, bundle, x, y, rows, batch, stats):
    use_relative = len(batch.groups) > 1 or batch.bilingual is not None
    hidden_fn = partial(bundle.packed_hidden, hidden=base.masked_hidden) if use_relative else base.masked_hidden
    hidden = hidden_fn(model, x, batch.segments, flash=True)
    nll, valid = base.prior.course_target_nll(
        model, hidden, y, rows * 2, torch.as_tensor(batch.positives, device=y.device))
    kinds = torch.as_tensor(batch.kinds, device=y.device)
    plain = nll.masked_select(kinds.ne(0)).sum()
    loss = sum(nll.masked_select(kinds.eq(i)).sum() * stats["answer_weights"][i - 1] for i in (1, 2, 3))
    if batch.groups:
        weight = base.prior.role_loss.WEIGHTS["ALL_AXES"] / stats["relation_questions"]
        for scores, gold in relation.relation_scores(nll, valid, y, batch.segments, batch.groups, prep.END):
            loss = loss + weight * base.prior.contrast_row(scores, gold)
    if batch.decimal:
        r, c = torch.as_tensor([event[:2] for event in batch.decimal], device=x.device).T
        labels = [event[2] for event in batch.decimal]
        auxiliary, count, correct, _ = base.prior.joint_decimal.objective(
            model.decimal_head, hidden[r, c, None], y[r, c, None], labels, [[0]] * len(labels))
        if count != len(labels):
            raise ValueError("the decimal loss lost a sealed target")
        stats["decimal_correct"] += correct
        loss = loss + (.02 / stats["decimal_targets"]) * auxiliary
    if batch.bilingual is not None:
        context, location, transfer, metrics = terms.auxiliary(model, hidden, batch.bilingual, transfer_weight=0.)
        if metrics["context_targets"] != stats["context_targets"] or metrics["location_targets"] != stats["location_targets"]:
            raise ValueError("the prepared bilingual target totals changed inside the objective")
        stats.update(metrics, context_nll=float(context.detach()))
        plain = plain + context
        loss = loss + stats["raw_context_weight"] * context + VALUE_WEIGHT * location + transfer
    return plain, loss


class SupervisedG4(base.MixedG4):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.value_link = value_head(cfg.dim)


def native_training(bundle, slots, record, tag, cutoff, *, profile, addresses, resume, save, observe):
    """Append real native optimizer updates, preserving the bound absolute input address."""
    original_objective = trainer._ce_recomputed
    make_binding = state_tools.make_binding
    split_params = base.muon.split_params
    commands, name = base.native_commands(bundle, tag, resume)
    for flag in ("--eval-every", "--save-every"):
        commands[commands.index(flag) + 1] = str(profile["boundary"])
    checkpoint = record / "ckpt" / terms.inputs.training.checkpoint_name(name, tag)
    model = stats = None
    pending = {}

    def build_model(cfg):
        nonlocal model
        model = SupervisedG4(cfg)
        return model

    def bind(plan, recipe, cache, device):
        if (plan.steps != bundle.steps or plan.tokens_per_update != prep.ACCUM * base.MICRO_TOKENS
                or cache != bundle.cache or recipe["ce_recompute_rows"] != 1024
                or recipe.get("ste_update_cache") or recipe.get("packed_document_profile")):
            raise ValueError("the bilingual objective requires the sealed native optimizer geometry")
        bundle.unchanged()
        return make_binding(plan, dict(recipe, p109c_bilingual_supervised=profile), cache, device)

    def split(model):
        matrices, others = split_params(model)
        auxiliary = [model.decimal_head.weight, *model.value_link.parameters()]
        ids = {id(weight) for weight in auxiliary}
        return [weight for weight in matrices if id(weight) not in ids], [*others, *auxiliary]

    class Cursor(base.MicroTokensCursor):
        def prepare(self):
            nonlocal stats
            if pending or model.training_route is not None or time.time() >= cutoff:
                raise RuntimeError("incomplete update or expired experiment window")
            update = super().prepare()
            address = addresses[update.update]
            schedule = bundle.schedule[address]
            raw_indexes = schedule[schedule[:, 0] == -1, 1]
            raw_rows = iter(bundle.raw_batch(raw_indexes))
            batches, answers = [], np.zeros(4, dtype=np.int64)
            context = locations = relations = decimals = occupied = empty = 0
            for (lane, index), (tx, ty) in zip(schedule, update.batches, strict=True):
                batch = None
                if lane == -1:
                    raw = next(raw_rows)
                    x, y = tx.new_tensor(raw[:, :-1]), ty.new_tensor(raw[:, 1:])
                elif lane == -2:
                    x, y = tx, ty
                    empty += 1
                else:
                    x, y, batch = course_microbatch(bundle, slots, address, lane, index)
                    x, y = tx.new_tensor(x.astype(np.int64)), ty.new_tensor(y.astype(np.int64))
                    occupied += int(np.count_nonzero(batch.segments))
                    answers += np.bincount(batch.kinds.ravel(), minlength=4)
                    relations += len(batch.groups)
                    decimals += len(batch.decimal)
                    if batch.bilingual is not None:
                        context += len(batch.bilingual.context_targets)
                        locations += len(batch.bilingual.value_classes)
                pending[id(y)] = (int(lane), batch)
                batches.append((x, y))
            n_raw = len(raw_indexes) * base.MICRO_TOKENS
            course = COURSE_SHARE if address >= bundle.warmup else 0.
            active = sum(w for w, n in zip(base.KIND_WEIGHTS, answers[1:], strict=True) if n)
            if not n_raw or (course and not active):
                raise ValueError("the sealed update must contain source supervision")
            weights = [float(course * w / (active * n)) if n else 0.
                       for w, n in zip(base.KIND_WEIGHTS, answers[1:], strict=True)]
            stats = dict(source_update=address + 1, raw_targets=n_raw, course_inputs=occupied,
                         answer_targets=[int(n) for n in answers[1:]], answer_weights=weights,
                         context_targets=context, location_targets=locations, relation_questions=relations,
                         decimal_targets=decimals, decimal_correct=0, raw_context_weight=(1. - course) / (n_raw + context),
                         reserved_batches=len(batches), empty_batches=empty,
                         valid_ce_targets=n_raw + int(answers[1:].sum()) + context)
            model.training_route = routed.route_for(model.cfg, model.owner, "uniform_r2", 1337, address, bundle.steps)
            model.training_forwards = 0
            self._pending = replace(update, batches=tuple(batches))
            return self._pending

        def finish(self, *, optimizer_applied):
            expected = stats["reserved_batches"] - stats["empty_batches"]
            if not optimizer_applied or pending or model.training_forwards != expected:
                raise RuntimeError("the native optimizer or real forward count differs from the sealed update")
            applied = super().finish(optimizer_applied=True)
            grad = [float(p.grad.detach().norm()) for p in model.value_link.parameters() if p.grad is not None]
            if stats["location_targets"] and (len(grad) != 2 or min(grad) <= 0):
                raise RuntimeError("both value-link projections must receive a nonzero gradient")
            visits = len(model.training_route)
            model.training_route = None
            observe(dict(stats, step=applied["update"] + 1, actual_forwards=model.training_forwards,
                         route_visits=visits, forward_tensor_slots=expected * base.MICRO_TOKENS,
                         forward_layer_slots=expected * base.MICRO_TOKENS * visits, value_gradient=grad))
            return applied

    def objective(model, x, y, rows):
        if not model.training:
            return original_objective(model, x, y, rows)
        lane, batch = pending.pop(id(y))
        if lane == -2:
            return torch.zeros((), dtype=torch.float32, device=x.device, requires_grad=True)
        if lane == -1:
            nll, _ = base.target_nll(model, model(x, return_hidden=True), y, rows=rows)
            plain = nll.sum()
            loss = plain * stats["raw_context_weight"]
        else:
            plain, loss = course_objective(model, bundle, x, y, rows, batch, stats)
        return (plain.detach() / stats["valid_ce_targets"] + (loss - loss.detach())) * prep.ACCUM

    original_evaluate = trainer.evaluate

    def validate(model, loader, batches, device, **kwargs):
        return original_evaluate(model, loader, profile["validation_batches"], device, **kwargs)

    with (patch.object(sys, "argv", ["tinylm", *commands]), patch.object(trainer, "prepare", bundle.prepare),
          patch.object(trainer, "CKPT", checkpoint.parent), patch.object(trainer, "LOGS", record / "native_logs"),
          patch.object(trainer, "TiedMLPTransformer", build_model),
          patch.object(context_micro_tokens, "MicroTokensCursor", Cursor),
          patch.object(state_tools, "make_binding", bind), patch.object(base.muon, "split_params", split),
          patch.object(trainer, "_ce_recomputed", objective), patch.object(trainer, "evaluate", validate),
          patch.object(saves, "save_packed_checkpoint", partial(save, checkpoint))):
        cli.main()
