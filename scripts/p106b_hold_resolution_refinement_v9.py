#!/usr/bin/env python3
"""Fresh source call-loss checks also apply to previously terminal drafts."""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement_v8 as previous
from scripts import p106b_hold_resolution_policy_v21 as policy
from scripts import p106b_hold_resolution_refinement as base

v4 = previous.previous.previous.previous.previous


class FrozenDraftSelector(v4.FrozenDraftSelector):
    def propose(self, row, individual_hold=False):
        key = row["original_text_sha256"]
        base.inv.require(key in self.records, "source is outside frozen draft")
        frozen = self.records[key]
        losses = (policy.proven_source_call_losses(row["text"], frozen.get("text", row["text"]))
                  if frozen["decision"] in {"KEEP", "EDIT"} else {})
        if not losses:
            return super().propose(row, individual_hold)
        self.records[key] = dict(frozen, decision="PENDING")
        try:
            value = super().propose(row, individual_hold)
        finally:
            self.records[key] = frozen
        self.last["rechecked_source_function_parentheses_loss"] = losses
        return value


@contextmanager
def refinement(directory, baseline_name, new_policy, code_files):
    with patch.object(v4, "FrozenDraftSelector", FrozenDraftSelector), \
            patch.object(previous, "policy", policy), \
            patch.object(base.guards, "unicode_examples_preserved", policy.unicode_examples_preserved):
        with previous.refinement(directory, baseline_name, new_policy, code_files) as selector:
            yield selector
