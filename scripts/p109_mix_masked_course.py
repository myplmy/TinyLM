"""Route fixed-width supervised course batches through the native G4 trainer."""

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109_train_visit_policy as routed
from scripts import p106b_joint_decimal as joint_decimal
from scripts import p106b_subject_role_loss as role_loss
from tinylm.train import context_training_state, trainer
from tinylm.train import muon
from tinylm.train.context_micro_tokens import MicroTokensCursor
from tinylm.train.recomputed_ce import target_nll


RECIPE_KEY = "p109_masked_course"
IGNORE = -100


class MappedRows:
    """Read one ordered microbatch at a time from the caller's sealed NPY file."""

    def __init__(self, path, sha256):
        self.sha256 = sha256
        self._array = np.load(path, mmap_mode="r", allow_pickle=False)
        if (not isinstance(self._array, np.memmap) or self._array.dtype != np.dtype("<i4")
                or self._array.ndim != 3 or self._array.shape[1] != 2
                or not len(self._array) or not self._array.shape[2]):
            raise ValueError("ordered course must be a nonempty little-endian int32 [rows, 2, width] NPY")
        self.width = self._array.shape[2]

    def __len__(self):
        return len(self._array)

    def __getitem__(self, index):
        return tuple(tuple(row) for row in self._array[index].tolist())

    def validate(self, vocab_size):
        for start in range(0, len(self), 256):
            block = self._array[start:start + 256]
            x, y = block[:, 0], block[:, 1]
            supervised = y != IGNORE
            if (np.any(x < 0) or np.any(x >= vocab_size)
                    or np.any(supervised & ((y < 0) | (y >= vocab_size)))
                    or not supervised.any(axis=1).all()):
                raise ValueError("mapped course needs valid tokens and supervised next-token labels")
            if np.any(supervised[:, :-1] & (y[:, :-1] != x[:, 1:])):
                raise ValueError("a mapped supervised label disagrees with the next input token")


@dataclass(frozen=True)
class Course:
    start_update: int
    micro_slots: tuple[int, ...]
    rows: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...] | MappedRows
    vocab_size: int

    def __post_init__(self):
        if type(self.start_update) is not int or self.start_update < 0:
            raise ValueError("a zero-based course start update is required")
        if type(self.vocab_size) is not int or self.vocab_size < 2:
            raise ValueError("invalid course vocabulary")
        if (type(self.micro_slots) is not tuple or not self.micro_slots
                or any(type(index) is not int or index < 0 for index in self.micro_slots)
                or tuple(sorted(set(self.micro_slots))) != self.micro_slots):
            raise ValueError("sorted, distinct course microbatch slots are required")
        if isinstance(self.rows, MappedRows):
            self.rows.validate(self.vocab_size)
            return
        if type(self.rows) is not tuple or not self.rows:
            raise ValueError("immutable course rows are required")
        for row in self.rows:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError("each course row needs immutable x and y")
            x, y = row
            if (type(x) is not tuple or type(y) is not tuple or not x or len(x) != len(y)
                    or any(type(value) is not int or not 0 <= value < self.vocab_size for value in x)
                    or any(type(value) is not int or not (value == IGNORE or 0 <= value < self.vocab_size)
                           for value in y)
                    or not any(value != IGNORE for value in y)):
                raise ValueError("course rows need valid tokens and supervised next-token labels")
            if any(label != IGNORE and label != following for label, following in zip(y, x[1:])):
                raise ValueError("a supervised label disagrees with the next input token")

    def binding(self):
        if isinstance(self.rows, MappedRows):
            schema, digest = "P109_MASKED_COURSE_NPY_V1", self.rows.sha256
        else:
            encoded_rows = json.dumps(self.rows, separators=(",", ":")).encode("ascii")
            schema, digest = "P109_MASKED_COURSE_V1", hashlib.sha256(encoded_rows).hexdigest().upper()
        return dict(schema=schema, start_update=self.start_update,
                    micro_slots=list(self.micro_slots), vocab_size=self.vocab_size,
                    course_rows_sha256=digest,
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper())


@dataclass(frozen=True)
class AllAxesCourse:
    layout: Course
    end_id: int
    gold_by_question: tuple[int, ...]

    def __post_init__(self):
        if (type(self.end_id) is not int or not 0 <= self.end_id < self.layout.vocab_size
                or len(self.layout.rows) % 16 or len(self.layout.micro_slots) % 4):
            raise ValueError("ALL_AXES needs complete four-question graphs and a valid response end")
        golds = self.gold_by_question
        if (type(golds) is not tuple or len(golds) * 4 != len(self.layout.rows)
                or any(type(gold) is not int for gold in golds)
                or any(set(golds[start:start + 4]) != {0, 1, 2, 3} for start in range(0, len(golds), 4))):
            raise ValueError("each question needs its explicit gold candidate index")
        for graph_start in range(0, len(self.layout.rows), 16):
            groups = []
            for index in range(graph_start, graph_start + 16):
                tokens, targets = self.layout.rows[index]
                indices = [column for column, token in enumerate(targets) if token != IGNORE]
                begin, end = indices[0], indices[-1] + 1
                answer = targets[begin:end]
                if len(answer) < 2 or answer[-1] != self.end_id or self.end_id in answer[:-1] or IGNORE in answer:
                    raise ValueError("ALL_AXES requires contiguous answer content and one supervised response end")
                groups.append((tokens[:begin + 1], answer))
            expected_answers = tuple(answer for _, answer in groups[:4])
            if len(set(expected_answers)) != 4:
                raise ValueError("a relation graph needs four distinct candidate answers")
            question_prefixes = set()
            for question in range(4):
                start = question * 4
                candidates = groups[start:start + 4]
                prefixes = {prefix for prefix, _ in candidates}
                if len(prefixes) != 1 or tuple(answer for _, answer in candidates) != expected_answers:
                    raise ValueError("each question needs one common prefix and the same ordered answers")
                question_prefixes.update(prefixes)
            if len(question_prefixes) != 4:
                raise ValueError("a relation graph needs four distinct question prefixes")

    def binding(self):
        loss_source = Path(role_loss.__file__).read_bytes()
        return dict(layout=self.layout.binding(), end_id=self.end_id, weight=role_loss.WEIGHTS["ALL_AXES"],
                    gold_by_question=list(self.gold_by_question),
                    loss_sha256=hashlib.sha256(loss_source).hexdigest().upper())


def contrast_row(scores, gold):
    """Apply the existing ALL_AXES loss to one complete question."""
    canonical = role_loss.negative_mask("ALL_AXES", device=scores.device)
    question = torch.arange(4, device=scores.device).eq(gold).unsqueeze(1)
    return role_loss.masked_row_contrast_sum(scores.expand(1, 4, 4), canonical & question)


def course_target_nll(model, hidden, targets, rows, positions=None):
    if positions is None:
        return target_nll(model, hidden, targets, rows=rows)
    scored_hidden = hidden.flatten(0, 1).index_select(0, positions).unsqueeze(0)
    scored_targets = targets.flatten().index_select(0, positions).unsqueeze(0)
    nll, _ = target_nll(model, scored_hidden, scored_targets, rows=rows)
    restored = nll.new_zeros(targets.numel()).index_copy(0, positions, nll.flatten())
    return restored.view_as(targets), targets.ne(IGNORE)


def relation_loss_terms(model, x, y, rows, end_id, gold, positions=None):
    nll, valid = course_target_nll(model, model(x, return_hidden=True), y, rows, positions)
    content = valid & y.ne(end_id)
    scores = -(nll * content).sum(dim=1) / content.sum(dim=1)
    return nll[gold].sum() / valid[gold].sum(), contrast_row(scores, gold)


@dataclass(frozen=True)
class DecimalLabels:
    by_row: MappingProxyType
    sha256: str

    @classmethod
    def load(cls, path, sha256, course, tokenizer, end_id):
        raw = np.load(path, allow_pickle=False, mmap_mode="r")
        if (not isinstance(raw, np.memmap) or raw.dtype != np.dtype("<i4")
                or raw.shape != (len(course.rows), 3)):
            raise ValueError("decimal labels need int32 [row, (position, left, right)]")
        labels = {}
        for index, (position, left, right) in enumerate(raw.tolist()):
            if (position, left, right) == (-1, -1, -1):
                continue
            total, _, _, carry = joint_decimal.decimal_parts(left, right)
            _, targets = course.rows[index]
            valid = [column for column, token in enumerate(targets) if token != IGNORE]
            answer = targets[position:valid[-1] + 1]
            if (position != valid[0] or len(answer) < 2 or answer[-1] != end_id
                    or IGNORE in answer or end_id in answer[:-1]
                    or tokenizer.decode(list(answer[:-1]), skip_special_tokens=False).strip() != str(total)):
                raise ValueError("decimal supervision requires the exact last prompt position and verified integer")
            labels[index] = (1000 + total + 200 * carry, position)
        if not labels:
            raise ValueError("the decimal course needs at least one verified addition row")
        return cls(MappingProxyType(labels), sha256)

    def binding(self):
        return dict(sha256=self.sha256, rows=len(self.by_row), version=joint_decimal.VERSION,
                    reduction="LABELED_ROWS_IN_UPDATE", beta=1,
                    source_sha256=hashlib.sha256(Path(joint_decimal.__file__).read_bytes()).hexdigest().upper())


class DecimalG4(routed.RoutedG4):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.decimal_head = joint_decimal.new_head(cfg.dim)


def run_native(course: Course, native_args, *, all_axes: AllAxesCourse | None = None,
               compact_course_ce=False, mixed_ce_recompute_rows=None, exact_course_rows=False,
               decimal: DecimalLabels | None = None, reuse_quantization=False):
    """Reuse the normal optimizer, checkpoint and absolute update cursor."""
    standard_binding = context_training_state.make_binding
    binding = course.binding()
    if exact_course_rows:
        binding["exact_course_rows"] = True
    course_updates = {}
    relation_batches = {}
    compact_batches = {}
    decimal_batches = {}
    if decimal is not None:
        if not exact_course_rows or max(decimal.by_row) >= len(course.rows):
            raise ValueError("decimal supervision must bind to the ordered plain course")
        binding["decimal"] = decimal.binding()
    if compact_course_ce:
        binding["course_ce_positions"] = "SUPERVISED_POSITIONS_ONLY_V1"
    if mixed_ce_recompute_rows is not None:
        if type(mixed_ce_recompute_rows) is not int or mixed_ce_recompute_rows < 1:
            raise ValueError("the mixed-phase CE block must have a positive number of rows")
        binding["mixed_ce_recompute_rows"] = mixed_ce_recompute_rows
    initial_ce_rows = None
    mixed_update = False
    layouts = (course,)
    if all_axes is not None:
        relation = all_axes.layout
        if (relation.start_update != course.start_update or relation.vocab_size != course.vocab_size
                or set(relation.micro_slots).intersection(course.micro_slots)):
            raise ValueError("course layouts must share the stage and vocabulary with separate slots")
        layouts += (relation,)
        binding["all_axes"] = all_axes.binding()
    occupied = {slot for layout in layouts for slot in layout.micro_slots}
    normal_ce = trainer._ce_recomputed
    standard_split_params = muon.split_params
    model_type = DecimalG4 if decimal is not None else routed.RoutedG4
    quantization_preparations = []

    if reuse_quantization:
        from scripts import diag_p109b_ste_exact_micro as ste

        binding["quantization_reuse"] = dict(mode="PER_MICRO_VJP",
            source_sha256=hashlib.sha256(Path(ste.__file__).read_bytes()).hexdigest().upper())

        class ReuseG4(model_type):
            def __init__(self, cfg):
                super().__init__(cfg)
                if cfg.grad_checkpoint or cfg.use_ternary_kernel or getattr(cfg, "ternary_kernel_triton", False):
                    raise ValueError("course STE reuse needs eager FP32 surrogates without activation checkpointing")
                self.course_quantization = None

            def refresh_quant(self):
                if not self.training:
                    if self.course_quantization is not None:
                        raise RuntimeError("discard the training quantization cache before evaluation")
                    return super().refresh_quant()
                if self.training_route is None:
                    raise RuntimeError("quantization reuse needs an active training update")
                if self.course_quantization is None:
                    self.course_quantization = ste.UpdateQuantizationReuse(self)
                    self.course_quantization.refresh()
                    quantization_preparations.append(len(self.course_quantization.buffers))
                else:
                    self.course_quantization.refresh()

            def clear_quant(self):
                super().clear_quant()
                self.course_quantization = None

        model_type = ReuseG4

    def split_params(model):
        matrices, others = standard_split_params(model)
        if decimal is None:
            return matrices, others
        head_weight = model.decimal_head.weight
        return [weight for weight in matrices if weight is not head_weight], [*others, head_weight]

    def bind_course(plan, recipe, cache, device):
        nonlocal initial_ce_rows
        if (course.start_update >= plan.steps or max(occupied) >= plan.base_accum or len(occupied) == plan.base_accum
                or any((layout.rows.width != plan.full_length if isinstance(layout.rows, MappedRows)
                        else any(len(x) != plan.full_length for x, _ in layout.rows)) for layout in layouts)
                or (all_axes is not None and plan.micro_bs != 4)):
            raise ValueError("course layout must fit the fixed source and keep an ordinary microbatch")
        if exact_course_rows and any(len(layout.rows) != (plan.steps - course.start_update)
                                     * len(layout.micro_slots) * plan.micro_bs for layout in layouts):
            raise ValueError("each ordered course must supply exactly its declared slot exposures")
        if (not recipe["ce_recompute_rows"] or recipe.get("packed_document_profile")
                or recipe.get("mtp_aux") or recipe.get("kd")):
            raise ValueError("this course diagnostic requires the fixed native recomputed NTP path")
        if reuse_quantization and recipe.get("ste_update_cache"):
            raise ValueError("select only one STE reuse path")
        initial_ce_rows = recipe["ce_recompute_rows"]
        meta = (Path(cache["cache_dir"]) / "meta.json").read_bytes()
        if (hashlib.sha256(meta).hexdigest().upper() != cache["files"]["meta.json"]["sha256"]
                or int(json.loads(meta)["vocab"]) != course.vocab_size):
            raise ValueError("course vocabulary differs from the sealed cache")
        return standard_binding(plan, dict(recipe, **{RECIPE_KEY: binding}), cache, device)

    def course_ce(model, x, y, rows):
        if model.training and mixed_update and mixed_ce_recompute_rows is not None:
            rows = mixed_ce_recompute_rows
        selected = relation_batches.pop(id(y), None)
        positions = compact_batches.pop(id(y), None)
        decimal_case = decimal_batches.pop(id(y), None)
        if decimal_case is not None:
            hidden = model(x, return_hidden=True)
            nll, valid = course_target_nll(model, hidden, y, rows, positions)
            index, labels, windows, weight = decimal_case
            aux, count, correct, _ = joint_decimal.objective(model.decimal_head, hidden, y, labels, windows)
            course_updates[index]["decimal_correct"] += correct
            course_updates[index]["decimal_loss_sum"] += float(aux.detach())
            course_updates[index]["decimal_events"] += count
            return nll.sum() / valid.sum() + weight * (aux - aux.detach())
        if selected is None:
            if positions is not None:
                nll, _ = course_target_nll(model, model(x, return_hidden=True), y, rows, positions)
                return nll.sum() / positions.numel()
            return normal_ce(model, x, y, rows)
        update_index, gold, weight = selected
        positive_ce, ranking = relation_loss_terms(model, x, y, rows, all_axes.end_id, gold, positions)
        course_updates[update_index]["contrast_loss"].append(
            dict(positive_ce=float(positive_ce.detach()), ranking=float(ranking.detach())))
        # The native trainer meters this value as CE. Route only the auxiliary gradient through it.
        return positive_ce + weight * (ranking - ranking.detach())

    class CourseCursor(MicroTokensCursor):
        def prepare(self):
            nonlocal mixed_update
            if relation_batches or compact_batches or decimal_batches:
                raise RuntimeError("a prepared course microbatch was left unconsumed")
            update = super().prepare()
            mixed_update = update.update >= course.start_update
            if not mixed_update:
                return update
            batches = list(update.batches)
            batch_size = self.plan.micro_bs
            selected_rows = []
            selected_relation_rows = []
            selected_golds = []
            supervised = 0
            candidate_targets = 0
            course_head_positions = 0
            decimal_targets = 0
            if decimal is not None:
                count = len(course.micro_slots) * batch_size
                first_plain = (update.update - course.start_update) * count
                decimal_targets = sum(index in decimal.by_row for index in range(first_plain, first_plain + count))
            for layout in layouts:
                is_relation = layout is not course
                first = (update.update - layout.start_update) * len(layout.micro_slots) * batch_size
                for position, slot in enumerate(layout.micro_slots):
                    x_template, y_template = batches[slot]
                    start = first + position * batch_size
                    indices = range(start, start + batch_size)
                    if not exact_course_rows:
                        indices = [(index % len(layout.rows)) for index in indices]
                    x, y = zip(*(layout.rows[index] for index in indices))
                    new_y = y_template.new_tensor(y)
                    batches[slot] = (x_template.new_tensor(x), new_y)
                    if compact_course_ce:
                        positions = [row * update.length + column for row, labels in enumerate(y)
                                     for column, label in enumerate(labels) if label != IGNORE]
                        compact_batches[id(new_y)] = y_template.new_tensor(positions)
                        course_head_positions += len(positions)
                    else:
                        course_head_positions += new_y.numel()
                    if is_relation:
                        gold = all_axes.gold_by_question[indices[0] // batch_size]
                        weight = role_loss.WEIGHTS["ALL_AXES"] * self.plan.base_accum / len(layout.micro_slots)
                        relation_batches[id(new_y)] = (update.update, gold, weight)
                        selected_golds.append(gold)
                        selected_relation_rows.extend(indices)
                        candidate_targets += sum(label != IGNORE and label != all_axes.end_id for row in y for label in row)
                        supervised += sum(label != IGNORE for label in y[gold])
                    else:
                        selected_rows.extend(indices)
                        supervised += sum(label != IGNORE for row in y for label in row)
                        if decimal_targets:
                            cases = [decimal.by_row.get(index) for index in indices]
                            if any(case is not None for case in cases):
                                labels = [case[0] if case is not None else None for case in cases]
                                windows = [[case[1]] if case is not None else [] for case in cases]
                                decimal_batches[id(new_y)] = (update.update, labels, windows,
                                                               self.plan.base_accum / decimal_targets)
            self._pending = replace(update, batches=tuple(batches))
            counts = dict(course_input_slots=(len(selected_rows) + len(selected_relation_rows)) * update.length,
                          course_supervised_targets=supervised, course_head_positions=course_head_positions,
                          ordered_course_rows=selected_rows)
            if all_axes is not None:
                counts.update(contrast_questions=len(selected_relation_rows) // 4,
                              contrast_candidate_targets=candidate_targets,
                              ordered_contrast_rows=selected_relation_rows,
                              ordered_contrast_golds=selected_golds, contrast_loss=[])
            if decimal is not None:
                counts.update(decimal_events=0, decimal_correct=0, decimal_loss_sum=0.0)
            course_updates[update.update] = counts
            return self._pending

    with (patch.object(routed, "MicroTokensCursor", CourseCursor),
          patch.object(context_training_state, "make_binding", bind_course),
          patch.object(muon, "split_params", split_params),
          patch.object(trainer, "_ce_recomputed", course_ce)):
        receipt = routed.run_native("uniform_r2", native_args, build_model=model_type)
    if relation_batches or compact_batches or decimal_batches:
        raise RuntimeError("the final update did not consume every prepared course microbatch")
    receipt["course"] = binding
    if reuse_quantization:
        if len(quantization_preparations) != len(receipt["updates"]) or not all(quantization_preparations):
            raise RuntimeError("quantization reuse must prepare exactly once per completed update")
        for update, tensors in zip(receipt["updates"], quantization_preparations, strict=True):
            update["prepared_quantization_tensors"] = tensors
    for update in receipt["updates"]:
        update.update(course_updates.get(update["index"], dict(course_input_slots=0,
                                                                 course_supervised_targets=0,
                                                                 ordered_course_rows=[])))
        update["ordinary_input_slots"] = update["draw_tokens"] - update["course_input_slots"]
        if mixed_ce_recompute_rows is not None:
            update["ce_recompute_rows"] = (mixed_ce_recompute_rows if update["index"] >= course.start_update
                                           else initial_ce_rows)
    return receipt
