#!/usr/bin/env python3
"""User Stage4eWc: real serialized config, same endpoints, immutable v1/v2."""
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_epoch_retention_recovery as recovery

OUTPUT=ROOT/'HF/sft_ready/p106b_epoch_retention_v3_cfg_geometry'


def main():
    with patch.object(recovery,'OUTPUT',OUTPUT),\
         patch.object(recovery,'STAGE','Stage4eWc'),\
         patch.object(recovery,'FAILED_OUTPUT_POLICY','v1/v2 preserved; no checkpoint/schema changes'),\
         patch.object(recovery,'__doc__',__doc__):
        return recovery.main()


if __name__=='__main__':raise SystemExit(main())
