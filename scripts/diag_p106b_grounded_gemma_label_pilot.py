#!/usr/bin/env python3
"""User Stage4iWb: same16 original groups after the new Gemma label role gate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_grounded_gemma_pilot as pilot
from scripts import diag_p106b_gemma_label_recovery as role_gate
from scripts import p106b_gemma_labels as labels
from scripts.p106b_mixed_scale import digest,safe_repo_path

OUTPUT=ROOT/'HF/sft_ready/p106b_gemma_grounded_pilot_v2_labels'
INVENTORY_SHA='1C40536A05F349303BE780AF0FE714D59587B4CE17FEA974CC115CCB67F0AE94'


def require_base_off(role):
    if (role.get('schema')!='P106B_GEMMA4_ROLE_LABELS_V1'
            or role.get('actual_requests')!=16
            or role.get('input',{}).get('wire_contract')!=labels.CONTRACT):
        raise ValueError('new complete16 label role collection required')
    off=[a for a in role.get('answers',[]) if a.get('mtp') is False]
    expected={c['id'] for c in labels.cases()}
    expected_pairs={(r,c) for r in (0,1) for c in expected}
    if (len(off)!=8 or {(a.get('round'),a.get('case_id')) for a in off}!=expected_pairs
            or any(a.get('format_status')!=labels.COMPLETE or
                   a.get('wire',{}).get('technical_ready') is not True for a in off)):
        raise FileNotFoundError('new base-off8/8 field/context/mask gate required; MTP benefit is not required')


def check():
    if digest(safe_repo_path(pilot.INVENTORY/'report.json'))!=INVENTORY_SHA:
        raise ValueError('pinned source inventory report changed')
    report_path=safe_repo_path(role_gate.OUTPUT/'role/report.json')
    role=json.loads(report_path.read_text(encoding='utf-8'))
    require_base_off(role)
    with patch.object(pilot,'OUTPUT',OUTPUT),patch.object(pilot,'TEACHER',role_gate.OUTPUT),\
         patch.object(pilot,'teacher',labels),patch.object(pilot,'COMPLETE_STATUS',labels.COMPLETE):
        jobs,info=pilot.check()
    return jobs,dict(info,recovery_stage='Stage4iWb',wire_contract=labels.CONTRACT,
        source_inventory_report_sha256=INVENTORY_SHA,role_report_sha256=digest(report_path),
        prior_output_policy='v1 HOLD/raw preserved; no source substitution or repeated filler')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute',action='store_true')
    action.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    try:
        jobs,info=check()
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
        with patch.object(pilot,'OUTPUT',OUTPUT),patch.object(pilot,'teacher',labels),\
             patch.object(pilot,'COMPLETE_STATUS',labels.COMPLETE):
            return pilot.execute(jobs,info)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
