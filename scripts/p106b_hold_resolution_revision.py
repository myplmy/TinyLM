#!/usr/bin/env python3
"""Run the frozen full proposal engine with separately pinned v2 draft rules."""
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_proposals as engine
from scripts import p106b_hold_resolution_policy_v2 as policy

CODE = engine.CODE + ["scripts/p106b_hold_resolution_policy_v2.py", "scripts/p106b_hold_resolution_revision.py"]


def main():
    with patch.object(engine, "policy", policy), patch.object(engine, "CODE", CODE):
        return engine.main()


if __name__ == "__main__":
    main()
