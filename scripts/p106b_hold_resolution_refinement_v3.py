#!/usr/bin/env python3
"""Recheck old partial-deletion drafts and newly observed style-value losses.

Every other reused body still passes fresh source identity, ordered characters,
code, Unicode and style checks. The frozen source record is never modified.
"""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement_v2 as previous
from scripts import p106b_hold_resolution_policy_v13 as style

inv = previous.inv
ordered_deletion = previous.ordered_deletion
BOUNDARIES, BOUNDARY_REASON = previous.BOUNDARIES, previous.BOUNDARY_REASON
QUARANTINE = "QUARANTINE_ACTUAL_VALUE_HOLE_AND_PREMISE_DEPENDENTS"


class FrozenDraftSelector(previous.FrozenDraftSelector):
    def propose(self, row, individual_hold=False):
        key = row["original_text_sha256"]
        inv.require(key in self.records, "source is outside frozen draft")
        frozen = self.records[key]
        terminal = frozen["decision"] in {"KEEP", "EDIT"}
        old_body = frozen.get("text", row["text"])
        partial = terminal and any(change["reason"] == QUARANTINE for change in frozen["changes"])
        style_loss = terminal and not style.semantic_style_preserved(row["text"], old_body)
        if partial or style_loss:
            # The original in-memory record and all source files stay intact.
            # Temporarily route this one source through the existing fresh path.
            self.records[key] = dict(frozen, decision="PENDING")
            try:
                value = super().propose(row, individual_hold)
            finally:
                self.records[key] = frozen
            self.last["rechecked_frozen_terminal"] = dict(partial_quarantine=partial, style_loss=style_loss)
        else:
            value = super().propose(row, individual_hold)
        if value["decision"] in {"KEEP", "EDIT"}:
            clean = value.get("candidate", value["text"])
            inv.require(style.semantic_style_preserved(row["text"], clean), "automatic draft loses a source style value")
            self.last["integrity"]["semantic_style_guard"] = True
        return value


@contextmanager
def refinement(base, baseline_name, new_policy, code_files):
    with patch.object(previous, "FrozenDraftSelector", FrozenDraftSelector):
        with previous.refinement(base, baseline_name, new_policy, code_files) as selector:
            yield selector
