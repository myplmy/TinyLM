#!/usr/bin/env python3
"""Preserve individual HOLDs while rechecking the three real split boundaries.

The old accelerator's failed run remains unchanged. Only its overly broad
inherited-HOLD assertion for a proven boundary EXCLUDE receives this exception.
"""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement as previous

inv = previous.inv
ordered_deletion = previous.ordered_deletion
BOUNDARIES = {"historical_train:709976", "validation:0", "validation:3759"}
BOUNDARY_REASON = "UNRECOVERABLE_ORIGINAL_SPLIT_BOUNDARY"


class FrozenDraftSelector(previous.FrozenDraftSelector):
    def propose(self, row, individual_hold=False):
        key = row["original_text_sha256"]
        inv.require(key in self.records, "source is outside frozen draft")
        frozen = self.records[key]
        if frozen["decision"] != "EXCLUDE":
            return super().propose(row, individual_hold)
        inv.require(all(row[name] == frozen[name] for name in previous.IDENTITY), "source identity/interval changed")
        inv.require(inv.sha(row["text"]) == key, "source body does not match frozen identity")
        inv.require(row["id"] in BOUNDARIES and frozen["reasons"] == [BOUNDARY_REASON]
                    and (not row["complete_eos"] or row["id"] == "validation:0"),
                    "only the three evidenced original split boundaries can reuse EXCLUDE")
        value = self.new_policy.propose(row, individual_hold)
        inv.require(value["decision"] == "EXCLUDE" and value["reasons"] == [BOUNDARY_REASON]
                    and value["text"] == row["text"], "fresh original boundary decision differs")
        inherited = individual_hold or bool(row.get("previous_holds"))
        self.last = dict(original_text_sha256=key, candidate=None if inherited else row["text"],
                         decision="EXCLUDE", integrity=None, reused=False)
        return dict(value, rules=self.new_policy.RULES)


@contextmanager
def refinement(base, baseline_name, new_policy, code_files):
    with patch.object(previous, "FrozenDraftSelector", FrozenDraftSelector):
        with previous.refinement(base, baseline_name, new_policy, code_files) as selector:
            yield selector
