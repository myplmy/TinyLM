#!/usr/bin/env python3
"""User Stage6dWb: same16 off/on requests with opt-in start labels, no student."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_teacher_gate as gate
from scripts import p106b_gemma_labels as labels
from scripts.p106b_mixed_scale import digest,safe_repo_path

OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_teacher_v2_labels'
ASSET_SHA='952C13D1CAA933BD3D4D68CB1AB87FC144DEE2CCF69AA756D741BDB0069328BB'


def check():
    asset=safe_repo_path(gate.ASSET_FILE)
    if digest(asset)!=ASSET_SHA:raise ValueError('completed Gemma asset report changed')
    with patch.object(gate,'OUTPUT',OUTPUT),patch.object(gate,'profile',labels):
        info=gate.check('role')
    return dict(info,recovery_stage='Stage6dWb',wire_contract=labels.CONTRACT,
        previous_role_policy='v1 raw/report/negative unchanged; no retrospective PASS',
        asset_report_sha256=ASSET_SHA)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute',action='store_true')
    action.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    try:
        info=check()
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
        with patch.object(gate,'OUTPUT',OUTPUT),patch.object(gate,'profile',labels),\
             patch.object(gate,'COMPLETE_STATUS',labels.COMPLETE),\
             patch.object(gate,'ROLE_SCHEMA','P106B_GEMMA4_ROLE_LABELS_V1'),\
             patch.object(gate,'REQUIRE_TECHNICAL_WIRE',True):
            return gate.role(info)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
