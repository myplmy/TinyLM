#!/usr/bin/env python3
"""Recheck old terminal call proofs using the source-observed v18 guard."""
from contextlib import contextmanager
from unittest.mock import patch
from scripts import p106b_hold_resolution_refinement_v5 as previous
from scripts import p106b_hold_resolution_policy_v18 as policy


@contextmanager
def refinement(base, baseline_name, new_policy, code_files):
    with patch.object(previous, "policy", policy):
        with previous.refinement(base, baseline_name, new_policy, code_files) as selector:
            yield selector
