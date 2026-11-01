#!/usr/bin/env python3
"""Full source-pinned v21 proposals based on independently verified v20."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_revision_v20 as previous
from scripts import p106b_hold_resolution_refinement_v9 as replay
from scripts import p106b_hold_resolution_policy_v21 as policy
from scripts import p106b_hold_resolution_proposals as engine

CODE = previous.CODE + ["scripts/p106b_hold_resolution_preservation_v1.py", "scripts/p106b_hold_resolution_source_calls_v1.py",
                       "scripts/p106b_hold_resolution_structure_v1.py", "scripts/p106b_hold_resolution_policy_v21.py",
                       "scripts/p106b_hold_resolution_refinement_v9.py", "scripts/p106b_hold_resolution_revision_v21.py"]


def main():
    os.environ.update(CUDA_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false", RAYON_NUM_THREADS="1",
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=engine.BASE)
    parser.add_argument("--output-name", default="draft_proposals_v21")
    parser.add_argument("--each", type=int, default=2)
    args = parser.parse_args()
    engine.inventory.require(1 <= args.each <= 5, "packet stratum request out of bounds")
    with replay.refinement(args.base, "draft_proposals_v20", policy, CODE):
        return engine.full(args.base, args.output_name, args.each)


if __name__ == "__main__":
    main()
