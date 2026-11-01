#!/usr/bin/env python3
"""Recheck previously terminal drafts for newly observed literal value holes."""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement_v3 as previous
from scripts import p106b_hold_resolution_policy_v16 as policy

inv = previous.inv
ordered_deletion = previous.ordered_deletion
BOUNDARIES, BOUNDARY_REASON = previous.BOUNDARIES, previous.BOUNDARY_REASON
QUARANTINE = previous.QUARANTINE


class FrozenDraftSelector(previous.FrozenDraftSelector):
    def propose(self, row, individual_hold=False):
        key = row["original_text_sha256"]
        inv.require(key in self.records, "source is outside frozen draft")
        frozen = self.records[key]
        terminal = frozen["decision"] in {"KEEP", "EDIT"}
        holes = policy.literal_holes(frozen.get("text", row["text"])) if terminal else []
        if holes:
            self.records[key] = dict(frozen, decision="PENDING")
            try:
                value = super().propose(row, individual_hold)
            finally:
                self.records[key] = frozen
            self.last["rechecked_frozen_terminal_literal_holes"] = holes
            return value
        return super().propose(row, individual_hold)


@contextmanager
def refinement(base, baseline_name, new_policy, code_files):
    with patch.object(previous.previous, "FrozenDraftSelector", FrozenDraftSelector):
        with previous.previous.refinement(base, baseline_name, new_policy, code_files) as selector:
            yield selector
