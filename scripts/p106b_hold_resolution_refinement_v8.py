#!/usr/bin/env python3
"""Freshly detect the observed UI tails in otherwise frozen draft bodies."""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement_v7 as previous
from scripts import p106b_hold_resolution_policy_v20 as policy


@contextmanager
def refinement(base, baseline_name, new_policy, code_files):
    with patch.object(previous, "policy", policy):
        with previous.refinement(base, baseline_name, new_policy, code_files) as selector:
            yield selector
