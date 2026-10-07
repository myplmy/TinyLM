#!/usr/bin/env python3
"""User-only Stage4eWb: fixed row attribution, same endpoints and a new output.

Keep the failed v1 output immutable. No teacher, retraining or checkpoint writes.
The flags already exist in the global whitelist; no new model/CLI axis is added.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_epoch_retention as epoch

OUTPUT=ROOT/'HF/sft_ready/p106b_epoch_retention_v2_row_attribution'
STAGE='Stage4eWb'
FAILED_OUTPUT_POLICY='v1 preserved'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute',action='store_true')
    action.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    # Process-local namespace selection, never rewriting the old module/default.
    previous=epoch.OUTPUT
    try:
        epoch.OUTPUT=OUTPUT
        info=epoch.check()
        info=dict(info,recovery_stage=STAGE,failed_output_policy=FAILED_OUTPUT_POLICY,
                  output=str(OUTPUT.relative_to(ROOT)))
        if args.check_only:
            print('[CHECK_ONLY] '+json.dumps(info,ensure_ascii=False));return 0
        return epoch.execute(info)
    except (FileNotFoundError,FileExistsError) as exc:
        print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:
        print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9
    finally:
        epoch.OUTPUT=previous


if __name__=='__main__':raise SystemExit(main())
