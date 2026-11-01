#!/usr/bin/env python3
"""Freshly check old terminal drafts for the independent formula counter."""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement_v6 as previous
from scripts import p106b_hold_resolution_policy_v19 as policy


@contextmanager
def refinement(base, baseline_name, new_policy, code_files):
    with patch.object(previous, "policy", policy):
        with previous.refinement(base, baseline_name, new_policy, code_files) as selector:
            yield selector
