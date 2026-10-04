#!/usr/bin/env python3
"""P106B stage/UI contracts, safe CPU fixtures only."""
from __future__ import annotations
import contextlib
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_stage_receipt as runner
from scripts import diag_p106b_mtp_teacher as driver
from scripts.p106b_shards import ShardWriter
from scripts.p106b_mtp_teacher import text_sha


class ReceiptTests(unittest.TestCase):
    def simulate(self,values):
        calls=[];notes=[];iterator=iter(values)
        def launch(command):calls.append(command);return next(iterator)
        result=runner.pipeline(runner.phase_commands('contract'),launch,notes.append,experiment='FIXTURE')
        return result,calls,notes
    def test_pass_has_one_final_receipt_after_all_three(self):
        r,c,n=self.simulate([0,0,0])
        self.assertEqual(r['status'],'COMPLETE');self.assertEqual(len(c),3)
        self.assertEqual(sum(x.startswith('[EXPERIMENT_FINAL]') for x in n),1)
    def test_preflight_hold_never_runs_main(self):
        r,c,n=self.simulate([0,8])
        self.assertEqual(r['status'],'HOLD');self.assertEqual(r['returncode'],8)
        self.assertEqual(len(c),2);self.assertEqual(r['phases'][2]['status'],'NOT_RUN')
        self.assertFalse(r['main_experiment_invoked'])
    def test_regression_failure_is_error_even_if_rc8(self):
        r,c,n=self.simulate([8]);self.assertEqual(r['status'],'ERROR');self.assertEqual(len(c),1)
        self.assertEqual(r['returncode'],9);self.assertEqual(r['phases'][0]['returncode'],8)
    def test_backend_error_does_not_become_hold(self):
        r,c,n=self.simulate([0,0,9]);self.assertEqual(r['status'],'ERROR');self.assertEqual(r['returncode'],9)
    def test_interrupted_main_is_recorded_as_invoked_not_skipped(self):
        values=iter([0,0]);calls=[]
        def launch(command):
            calls.append(command)
            if len(calls)==3:raise KeyboardInterrupt()
            return next(values)
        r=runner.pipeline(runner.phase_commands('contract'),launch,lambda _:None,experiment='FIXTURE')
        self.assertEqual(r['status'],'INTERRUPTED');self.assertTrue(r['main_experiment_invoked'])
        self.assertEqual(r['phases'][2]['status'],'INTERRUPTED')
    def test_empty_or_reordered_pipeline_rejected(self):
        for phases in ([],list(reversed(runner.phase_commands('contract')))):
            with self.assertRaises(ValueError):runner.pipeline(phases,None,None,experiment='FIXTURE')
    def test_logging_failure_is_not_success(self):
        def note(_):raise OSError('fixture')
        with contextlib.redirect_stderr(io.StringIO()),contextlib.redirect_stdout(io.StringIO()):
            r=runner.pipeline(runner.phase_commands('contract'),lambda _:0,note,experiment='FIXTURE')
        self.assertEqual(r['status'],'LOG_ERROR');self.assertEqual(r['returncode'],9)
    def test_native_runlog_accumulates_all_phases_and_final_hold(self):
        from scripts import runlog
        with tempfile.TemporaryDirectory(prefix='p106b_receipt_tee_fixture_') as directory:
            fixture_root=Path(directory);output=fixture_root/'logs';capture=io.StringIO()
            common=['runlog','--name','P106B_Stage5eW_receipt_fixture','--num','101']
            phases=[('REGRESSION',[sys.executable,'-c','print("fixture regression passed")']),
                    ('PREFLIGHT',[sys.executable,'-c','import sys; print("fixture prerequisite missing"); sys.exit(8)']),
                    ('EXECUTE',[sys.executable,'-c','print("MAIN_SHOULD_NOT_RUN")'])]
            program=('import sys,subprocess;sys.path.insert(0,'+repr(str(ROOT))+');'
                     'from scripts.p106b_stage_receipt import pipeline;'
                     'r=pipeline('+repr(phases)+',lambda c:subprocess.run(c).returncode,'
                     'lambda s:print(s,flush=True),experiment="CPU_TEE_FIXTURE");'
                     'raise SystemExit(r["returncode"])')
            processes=[];native_popen=subprocess.Popen
            def tracked_popen(*args,**kwargs):
                proc=native_popen(*args,**kwargs);processes.append(proc);return proc
            with (patch.object(runlog,'ROOT',fixture_root),patch.object(runlog,'OUT',output),
                  patch.object(runlog,'_git_state',return_value=('fixture',(0,0))),
                  patch.object(runlog,'_register'),patch.object(runlog,'_post_run_wandb'),
                  patch.object(runlog.subprocess,'Popen',side_effect=tracked_popen),
                  patch.object(sys,'argv',common+['--',sys.executable,'-B','-X','utf8','-c',program]),
                  patch.dict('os.environ',{'TL_OUTDIR':''}),contextlib.redirect_stdout(capture)):
                try:rc=runlog.main()
                finally:
                    # This fixture calls a normally one-shot CLI in-process.
                    # Close only its completed child pipe, as process exit would.
                    for proc in processes:
                        if proc.stdout is not None:proc.stdout.close()
            files=list(output.glob('*.txt'));self.assertEqual(len(files),1)
            body=files[0].read_text();console=capture.getvalue()
            self.assertEqual(rc,8)
            self.assertIn('fixture regression passed',body);self.assertIn('fixture prerequisite missing',body)
            self.assertNotIn('\nMAIN_SHOULD_NOT_RUN\n',body)
            final=next(x for x in body.splitlines() if x.startswith('[EXPERIMENT_FINAL]'))
            self.assertIn(final,console);self.assertEqual(body.count('[EXPERIMENT_FINAL]'),1)
            self.assertEqual(json.loads(final.split(' ',1)[1])['status'],'HOLD')
            self.assertEqual(json.loads(final.split(' ',1)[1])['phases'][2]['status'],'NOT_RUN')
    def test_exact_new_names_and_original_training_configuration(self):
        with self.assertRaises(ValueError):runner.run('P106B_Stage5dW_lora_refusal_postreview','review')
        self.assertIn('new-balanced',runner.phase_commands('balanced')[1][1])
        for mode in ('lora','review','balanced'):
            self.assertIn('--check-only',runner.phase_commands(mode)[1][1])
            self.assertIn('--execute',runner.phase_commands(mode)[2][1])
    def test_lora_check_only_now_checks_c_before_metadata(self):
        with (patch.object(driver,'lora_refusal_gate',side_effect=FileNotFoundError('fixture missing')),
              patch.object(driver,'metadata_preflight') as metadata):
            with self.assertRaises(driver.PrerequisiteHold):driver.preflight('lora',False)
            metadata.assert_not_called()
    def test_review_missing_upstream_is_hold_not_pass(self):
        with tempfile.TemporaryDirectory(prefix='p106b_review_fixture_') as directory,patch.object(driver,'OUTPUT',Path(directory)):
            with self.assertRaises(driver.PrerequisiteHold):driver.review_preflight()
    def test_complete_review_checks_exact_raw_and_labels_without_writes(self):
        with tempfile.TemporaryDirectory(prefix='p106b_review_fixture_') as directory,patch.object(driver,'OUTPUT',Path(directory)):
            target=Path(directory)/'lora';target.mkdir()
            writer=ShardWriter(target,'raw');labels=[]
            for i in range(32):
                text='safe fixture '+str(i);row={'kind':'response','id':str(i),'condition':'base','metrics':{'final_text':text}}
                writer.append(row);labels.append({'id':str(i),'final_sha256':text_sha(text),'label':'ANSWER','reviewer':'fixture','reason':'fixture context'})
            manifest=writer.close(lineage={'fixture':True})
            (target/'report.json').write_text(json.dumps({'status':'TEACHER_BENCH_COMPARISON_COMPLETE','observed_requests':32,'raw_concat_sha256':manifest['concat_sha256']}))
            (target/'review_labels.jsonl').write_text('\n'.join(json.dumps(x) for x in labels)+'\n')
            driver.review_preflight();self.assertFalse((target/'review_summary.json').exists())
            labels[0]['final_sha256']='F'*64
            (target/'review_labels.jsonl').write_text('\n'.join(json.dumps(x) for x in labels)+'\n')
            with self.assertRaises(ValueError):driver.review_preflight()


if __name__=='__main__':unittest.main()
