#!/usr/bin/env python3
"""CPU route/precondition contracts; never touch real corpus/model/GPU."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import diag_p101a_sft_mtp as driver


class Contracts(unittest.TestCase):
    def test_real_check_only_entry(self):
        proc=subprocess.run([sys.executable,'-B','-X','utf8','scripts/diag_p101a_sft_mtp.py',
            '--mode','train','--arm','scratch_mtp','--check-only'],cwd=ROOT,
            capture_output=True,text=True,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        info=json.loads(proc.stdout.split('[CHECK_ONLY] ')[1])
        self.assertEqual(info['model_loading'],'NOT_RUN')
        self.assertEqual(info['micro_bs']*info['accum'],128)
        self.assertEqual(info['initializers'],['scratch','parent'])

    def test_tags_and_collision(self):
        for tag in ('../bad','p101a_sft_mtp_x/../../','p101a_sft_mtp_A'):
            with self.assertRaises(ValueError):driver.paths(tag)

    def test_arm_is_explicit(self):
        self.assertEqual(driver.ARMS,('scratch_ntp','scratch_mtp','parent_ntp','parent_mtp'))
        names=[driver.checkpoint('p101a_sft_mtp_fixture',a).name for a in driver.ARMS]
        self.assertEqual(len(set(names)),4)

    def test_train_route_rejects_absent_corpus_before_model(self):
        from unittest.mock import patch
        args=type('Args',(),{'arm':'scratch_mtp'})()
        with patch.object(driver,'corpus_report',side_effect=FileNotFoundError('fixture absent')):
            with patch.object(driver,'load_runtime',side_effect=AssertionError('model forbidden')):
                with self.assertRaises(FileNotFoundError):
                    driver.train_arm(args,ROOT/'HF/sft_ready/p101a_fixture_absent',ROOT/'test_result/evidence',{})

    def test_every_new_shell_uses_the_real_configuration_route(self):
        import shlex
        expected=[('Stage3aW_sft_mtp_cpu_contract','contract','scratch_ntp'),
                  ('Stage3bW_sft_mtp_frozen8m_corpus','prepare','scratch_ntp'),
                  ('Stage3eW_sft_mtp_four_arm_readback','compare','scratch_ntp'),
                  ('Stage4aWa_scratch_mtp_verified_infer','infer','scratch_mtp'),
                  ('Stage4aWb_parent_mtp_verified_infer','infer','parent_mtp')]
        for index,arm in enumerate(driver.ARMS):
            letter='abcd'[index]
            expected.extend([(f'Stage3cW{letter}_{arm}_cost','calibrate',arm),
                             (f'Stage3dW{letter}_{arm}_frozen8m','train',arm)])
        for stem,mode,arm in expected:
            path=ROOT/('run_P101A_'+stem+'.sh')
            if not path.is_file():path=ROOT/('run_P101A_'+stem+'-done.sh')
            commands=[shlex.split(line) for line in path.read_text().splitlines()
                if 'scripts/diag_p101a_sft_mtp.py --' in line]
            self.assertEqual(len(commands),1,stem)
            command=commands[0];args=command[command.index('scripts/diag_p101a_sft_mtp.py')+1:]
            self.assertIn('--execute',args,stem)
            args[args.index('--execute')]='--check-only'
            proc=subprocess.run([sys.executable,'-B','-X','utf8','scripts/diag_p101a_sft_mtp.py',*args],
                cwd=ROOT,capture_output=True,text=True,timeout=15)
            self.assertEqual(proc.returncode,0,(stem,proc.stderr))
            info=json.loads(proc.stdout.split('[CHECK_ONLY] ')[1])
            self.assertEqual((info['mode'],info['arm']),(mode,arm),stem)
            self.assertEqual(info['tag'],'p101a_sft_mtp_v1_s1337',stem)
            self.assertEqual(info['model_loading'],'NOT_RUN',stem)


if __name__=='__main__':unittest.main()
