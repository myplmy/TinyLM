"""Check the new formal-role counter on frozen terminals before any reuse."""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement_v9 as previous
from scripts import p106b_hold_resolution_policy_v23 as policy


class FrozenDraftSelector(previous.FrozenDraftSelector):
    def propose(self, row, individual_hold=False):
        key = row["original_text_sha256"]
        previous.base.inv.require(key in self.records, "source is outside frozen draft")
        frozen = self.records[key]
        holes = (policy.observed_formal_holes(frozen.get("text", row["text"]))
                 if frozen["decision"] in {"KEEP", "EDIT"} else [])
        if not holes:
            return super().propose(row, individual_hold)
        self.records[key] = dict(frozen, decision="PENDING")
        try:
            value = super().propose(row, individual_hold)
        finally:
            self.records[key] = frozen
        self.last["rechecked_frozen_terminal_observed_formal_roles"] = holes
        return value


@contextmanager
def refinement(directory, baseline_name, new_policy, code_files):
    with patch.object(previous, "FrozenDraftSelector", FrozenDraftSelector), \
            patch.object(previous, "policy", policy), \
            patch.object(previous.base.guards, "code_preserved", policy.code_preserved):
        with previous.refinement(directory, baseline_name, new_policy, code_files) as selector:
            yield selector
