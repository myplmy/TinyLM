#!/usr/bin/env python3
"""CPU namespace/entry fixtures; no actual HF/teacher/checkpoint reads."""
from contextlib import redirect_stdout,redirect_stderr
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gemma_literal_recovery as run
from scripts import diag_p106b_gemma_output_recovery as previous
from scripts import diag_p106b_gemma_task_pilot as gate
from scripts import p106b_gemma_deficit as control
from scripts import p106b_gemma_task_contract_v3 as tasks


class RecoveryTests(unittest.TestCase):
    def report(self):
        return dict(schema='P106B_GEMMA_TASK_PILOT_V1',status='TASK_PILOT_COMPLETE',accepted_groups=4,
            input=dict(mode='structure4',wire_contract=run.complex_tasks.CONTRACT,
                role_report_sha256=previous.gate.ROLE_SHA,producer_code_sha256={'scripts/p106b_gemma_labels.py':'A'*64}),
            candidate_manifest=dict(rows=4,concat_sha256=run.STRUCTURE_CANON_SHA),raw_manifest=dict(rows=5))

    def test_nested_scopes_restore_v2_and_v1_namespace(self):
        before=(previous.tasks,previous.PILOTS,previous.PATHS,previous.TAG,previous.require_structure4,
                previous.pipeline,gate.tasks,gate.OUTPUTS,control.CORPUS,control.TAG)
        with self.assertRaises(RuntimeError),run.literal_scope(),previous.recovery_scope():
            self.assertIs(gate.tasks,tasks)
            self.assertEqual(control.CORPUS,run.PATHS['CORPUS'])
            self.assertEqual(control.TAG,run.TAG)
            self.assertEqual(gate.OUTPUTS['structure4'],run.STRUCTURE)
            raise RuntimeError('fixture')
        self.assertEqual(before,(previous.tasks,previous.PILOTS,previous.PATHS,previous.TAG,previous.require_structure4,
                              previous.pipeline,gate.tasks,gate.OUTPUTS,control.CORPUS,control.TAG))

    def test_check_only_routes_without_execute(self):
        captured=[]
        def child():
            captured.extend(sys.argv)
            return 0
        with patch.object(sys,'argv',['r','--mode','contract16','--check-only']),\
             patch.object(previous,'main',side_effect=child) as called,redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(),0)
            self.assertEqual(called.call_count,1)
        self.assertEqual(captured,['literal','--mode','contract16','--check-only'])

    def test_execute_forwards_explicit_wall_budget_to_producer(self):
        captured=[]
        def child():
            captured.extend(sys.argv)
            return 0
        with patch.object(sys,'argv',['r','--mode','produce','--execute','--max-wall-sec','17']),\
             patch.object(previous,'main',side_effect=child),redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(),0)
        self.assertEqual(captured,['literal','--mode','produce','--execute','--max-wall-sec','17'])

    def test_actual_entry_receipt_uses_v3_not_inherited_v2_label(self):
        # Mock the phase runner itself: no subprocess, real data, GPU or model.
        with patch.object(sys,'argv',['r','--mode','contract16','--execute']),\
             patch.object(previous,'pipeline',return_value={'returncode':0}) as phase,redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(),0)
        self.assertEqual(phase.call_args.kwargs['experiment'],'P106B_GEMMA_LITERAL_V3_contract16')

    def test_prior_complex_exact_report_runtime_and_shards_verified(self):
        report=self.report();path=SimpleNamespace(is_file=lambda:True,read_text=lambda **_:json.dumps(report),parent=run.STRUCTURE)
        with patch.object(run,'safe_repo_path',side_effect=lambda p:path if p.name=='report.json' else p),\
             patch.object(run,'digest',side_effect=[run.STRUCTURE_SHA,'A'*64]),patch.object(run,'verify') as checked:
            self.assertEqual(run.require_pinned_structure4(),run.STRUCTURE_SHA)
            self.assertEqual(checked.call_count,2)

    def test_changed_shared_runtime_or_report_not_silently_carried(self):
        for values in ([run.STRUCTURE_SHA,'wrong'],['wrong']):
            report=self.report();path=SimpleNamespace(is_file=lambda:True,read_text=lambda **_:json.dumps(report),parent=run.STRUCTURE)
            with patch.object(run,'safe_repo_path',side_effect=lambda p:path if p.name=='report.json' else p),\
                 patch.object(run,'digest',side_effect=values),patch.object(run,'verify',side_effect=AssertionError('must stop')):
                with self.assertRaises(ValueError):run.require_pinned_structure4()

    def test_prior_failed_or_wrong_mode_not_success_proof(self):
        for field in ('status','accepted_groups','mode','wire_contract'):
            r=self.report()
            if field in r:r[field]='bad'
            else:r['input'][field]='bad'
            p=SimpleNamespace(is_file=lambda:True,read_text=lambda **_:json.dumps(r),parent=run.STRUCTURE)
            with patch.object(run,'safe_repo_path',return_value=p),patch.object(run,'digest',return_value=run.STRUCTURE_SHA):
                with self.assertRaises(ValueError):run.require_pinned_structure4()

    def test_missing_prior_evidence_holds_without_digest_or_allocation(self):
        p=SimpleNamespace(is_file=lambda:False)
        with patch.object(run,'safe_repo_path',return_value=p),\
             patch.object(run,'digest',side_effect=AssertionError('must not hash')):
            with self.assertRaises(FileNotFoundError):run.require_pinned_structure4()

    def test_does_not_expose_overwriting_passed_structure_mode(self):
        with patch.object(sys,'argv',['r','--mode','structure4','--execute']),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):run.main()


if __name__=='__main__':unittest.main()
