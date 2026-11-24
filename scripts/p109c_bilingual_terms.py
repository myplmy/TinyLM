"""Bind the original bilingual supervision to its exact packed P109C slots."""

from dataclasses import dataclass
import json

import numpy as np
import torch
from torch.nn import functional as F

from scripts import diag_p109c_bilingual_aux_packed as audited
from scripts import diag_p109c_v2_bilingual_native as inputs


prep, mixed = inputs.prep, inputs.mixed


@dataclass(frozen=True)
class BilingualTargets:
    rows: np.ndarray
    sites: np.ndarray
    value_classes: np.ndarray
    context_rows: np.ndarray
    context_positions: np.ndarray
    context_targets: np.ndarray
    choices: np.ndarray
    unique: np.ndarray
    gold: np.ndarray

    def features(self, hidden):
        rows = torch.as_tensor(self.rows, device=hidden.device)
        sites = torch.as_tensor(self.sites, device=hidden.device)
        return hidden[rows[:, None], sites]

    def candidates(self, device):
        return (torch.as_tensor(self.choices, dtype=torch.long, device=device),
                torch.as_tensor(self.unique, dtype=torch.bool, device=device),
                torch.as_tensor(self.gold, dtype=torch.long, device=device))


class BilingualSlots:
    def __init__(self, bundle, layout_sha):
        self.bundle = bundle
        self.lane = len(bundle.data) - 1
        profile = json.loads(inputs.native.manifest_bytes(inputs.LAYOUT, layout_sha))
        source = inputs.placement.PAIR_SOURCE
        if (profile["input_manifest_sha256"] != bundle.digest or prep.sha(source) != profile["pair_archive_sha256"]
                or len(profile["placements"]) != len(bundle.data[self.lane])):
            raise ValueError("the packed bilingual labels and slots must belong to the sealed v2 layout")
        self.placements = profile["placements"]
        with np.load(source, allow_pickle=False) as archive:
            self.tokens, self.labels, self.context, self.sites = (archive[k] for k in ("tokens", "labels", "context", "sites"))
            self.options, self.unique, self.targets = (archive[k] for k in ("options", "unique", "targets"))
        width = np.arange(self.tokens.shape[1])+1
        self.lengths = np.where((self.tokens != 0) | (self.labels != prep.IGNORE), width, 0).max(axis=1)

    def at(self, address):
        number = address - self.bundle.warmup
        if number < 0:
            return None
        block = self.placements[number]
        if (block["update"] != address + 1
                or tuple(self.bundle.schedule[address, block["new_bilingual_slot"]]) != (self.lane, number)):
            raise ValueError("the bilingual slot lost its source update or position")
        if not block["pairs"]:
            return None
        pair, start_rows, ko, en = np.asarray(block["pairs"], dtype=np.int64).T
        side = np.arange(2)
        indexes = (pair[:, None]*2+side).ravel()
        rows = (start_rows[:, None]+side).ravel()
        offsets = np.column_stack((ko, en)).ravel()
        sites, lengths = self.sites[indexes], self.lengths[indexes]
        choices, unique = self.options[pair], self.unique[pair]
        target = self.targets[pair].astype(np.int64)
        gold = choices[np.arange(len(pair)), target]
        if (not unique[np.arange(len(pair)), target].all()
                or not np.array_equal(self.labels[indexes, sites[:, 0]], np.repeat(gold, 2))):
            raise ValueError("first token class and value-location class were conflated or lost")
        coords = audited.selections(self.tokens[indexes], sites, self.context[indexes], self.labels[indexes],
                                    rows, offsets, lengths)
        x, y, segments = self.bundle.data[self.lane][number].transpose(1, 0, 2)
        if (not np.array_equal(y[coords["answer_rows"], coords["answer_pos"]], coords["answer_targets"])
                or not np.array_equal(x[coords["context_rows"], coords["context_pos"]+1], coords["context_targets"])
                or not np.all(segments[rows[:, None], coords["sites"]]
                              == np.repeat(np.arange(1, len(pair)+1), 2)[:, None])):
            raise ValueError("a packed bilingual target crossed an original example")
        return BilingualTargets(rows, coords["sites"], coords["value_classes"], coords["context_rows"],
                                coords["context_pos"], coords["context_targets"], choices, unique, gold)


def auxiliary(model, hidden, target, transfer_weight):
    """Return context NLL sum, value-link CE and separately counted detached-teacher transfer."""
    features = target.features(hidden)
    device = hidden.device
    locations = torch.arange(features.shape[1], device=device).expand(len(features), -1)
    value_logits = model.value_link(features, locations).float()
    value_gold = torch.as_tensor(target.value_classes, dtype=torch.long, device=device)
    value_ce = F.cross_entropy(value_logits, value_gold)
    context_rows = torch.as_tensor(target.context_rows, device=device)
    context_positions = torch.as_tensor(target.context_positions, device=device)
    context_labels = torch.as_tensor(target.context_targets, dtype=torch.long, device=device).unsqueeze(0)
    context_hidden = hidden[context_rows, context_positions].unsqueeze(0)
    context_nll, _ = mixed.target_nll(model, context_hidden, context_labels, rows=512)
    kept = value_logits.detach().argmax(1).eq(value_gold)
    stats = dict(bilingual_pairs=len(target.gold), context_targets=len(target.context_targets),
                 location_targets=len(value_gold), location_correct=int(kept.sum()), transfer_pairs=0)
    transfer = value_ce.new_zeros(())
    if transfer_weight:
        choices, unique, gold = target.candidates(device)
        first = model._head_logits(features[:, 0]).float()
        if first.shape != (len(value_gold), model.cfg.vocab_size):
            raise ValueError("transfer gating requires full-vocabulary prediction")
        transfer, accepted = audited.original.selected_transfer(first, choices, unique, gold, kept)
        stats["transfer_pairs"] = int(accepted)
        transfer = transfer * (transfer_weight / len(gold))
    stats["location_ce"] = float(value_ce.detach())
    stats["weighted_transfer"] = float(transfer.detach())
    return context_nll.sum(), value_ce, transfer, stats
