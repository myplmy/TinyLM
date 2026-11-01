#!/usr/bin/env python3
"""Complete residual pass with source-bound frozen terminal draft reproduction."""
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_proposals as engine
from scripts import p106b_hold_resolution_revision_v6 as previous
from scripts import p106b_hold_resolution_policy_v7 as policy
from scripts import p106b_hold_resolution_refinement as adapter

CODE = previous.CODE + ["scripts/p106b_hold_resolution_refinement.py",
                        "scripts/p106b_hold_resolution_policy_v7.py",
                        "scripts/p106b_hold_resolution_revision_v7.py"]
ORIGINAL_FULL = engine.full


def full(base=engine.BASE, output_name="draft_proposals_v7", each=2):
    with adapter.refinement(base, "draft_proposals_v6", policy, CODE):
        return ORIGINAL_FULL(base, output_name, each)


def main():
    with patch.object(engine, "full", full):
        return engine.main()


if __name__ == "__main__":
    main()
