"""CPU-only historical metadata, source transitions, and full-budget contracts."""
from __future__ import annotations

import copy
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tinylm
from scripts import p078_body_bridge as bridge
from scripts import diag_p078_prefix_router as driver
from scripts import diag_p078_route_training as base


def sources():
    old = {f'file{i}.py': 'A'*64 for i in range(42)}
    old.update({p: 'A'*64 for p in bridge.ALLOWED})
    new = dict(old)
    for path in bridge.ALLOWED:
        new[path] = 'B'*64
    changes = {p: dict(historical=old[p], current=new[p]) for p in bridge.ALLOWED}
    return dict(source_sha256=old, corpus='unchanged'), dict(source_sha256=new, corpus='unchanged'), changes


def receipt(info):
    now = datetime.now(timezone.utc)
    expires = (now+timedelta(hours=1)).isoformat()
    auth = dict(schema='P078_TRAIN_EXECUTION_AUTHORIZATION_V1', allow_gpu_training=True,
        tag='fixed', input_signature_sha256=base.route.sha(info), max_family_seconds=144000,
        max_worker_seconds=60, expires_at=expires)
    value = dict(input=info, authorization=auth, authorization_sha256='D'*64)
    activity = dict(input=info, complete=True, returncode=0, report_sha256='C'*64,
        seconds=1., started_at=now.isoformat(), ended_at=(now+timedelta(seconds=1)).isoformat(),
        pid=15, pgid=15, max_wall_sec=60, admission_remaining=1000., authority_expires_at=expires,
        authorization=auth, authorization_canonical_sha256=base.route.sha(auth), authorization_sha256='D'*64)
    return value, activity


def validate(value, activity, info):
    return base.validate_closed_receipt(value, activity, info, report_sha256='C'*64, expected_tag='fixed')


class BridgeTests(unittest.TestCase):
    def test_exact_source_transition_and_same_non_source_contract(self):
        old, new, transitions = sources()
        self.assertEqual(bridge.compare_sources(old, new, transitions), transitions)

    def test_third_changed_source_is_not_an_allowlisted_path(self):
        old, new, transitions = sources()
        new['source_sha256']['file0.py'] = 'F'*64
        transitions['file0.py'] = dict(historical='A'*64, current='F'*64)
        with self.assertRaises(ValueError):
            bridge.compare_sources(old, new, transitions)

    def test_declared_path_without_exact_sha_pair_is_refused(self):
        old, new, transitions = sources()
        transitions['tinylm/train/mtp_sft.py']['current'] = 'F'*64
        with self.assertRaises(ValueError):
            bridge.compare_sources(old, new, transitions)

    def test_added_or_missing_source_and_changed_recipe_are_refused(self):
        for case in ('missing', 'added', 'recipe'):
            old, new, transitions = sources()
            if case == 'missing':
                del new['source_sha256']['file0.py']
            elif case == 'added':
                new['source_sha256']['extra.py'] = 'A'*64
            else:
                new['corpus'] = 'another'
            with self.subTest(case=case), self.assertRaises(ValueError):
                bridge.compare_sources(old, new, transitions)

    def test_profile_and_sha_are_paired_and_r1_is_refused(self):
        self.assertFalse(bridge.selected(SimpleNamespace()))
        for args in (SimpleNamespace(profile='x'), SimpleNamespace(profile_sha256='A'*64),
                SimpleNamespace(profile='x', profile_sha256='A'*64, resource_only_r1=True)):
            with self.assertRaises(ValueError):
                bridge.selected(args)

    def test_historical_receipt_guard_accepts_exact_metadata_only(self):
        info = dict(test='historical'); value, activity = receipt(info)
        self.assertIs(validate(value, activity, info), value)
        with self.assertRaises(ValueError):
            validate(value, activity, dict(test='current'))

    def test_historical_receipt_mutations_keep_all_old_guards(self):
        info = dict(test='historical')
        mutations = [dict(complete=False), dict(returncode=8), dict(report_sha256='F'*64),
            dict(seconds=-1), dict(seconds=float('nan')), dict(seconds=91), dict(max_wall_sec=1),
            dict(admission_remaining=59), dict(pid=0), dict(pgid=16),
            dict(started_at='2026-10-27T00:00:00'), dict(authorization_canonical_sha256='F'*64),
            dict(authorization_sha256='F'*64), dict(input={'test':'another'})]
        for mutation in mutations:
            value, activity = receipt(info); activity.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, TypeError)):
                validate(value, activity, info)

    def test_default_closed_still_uses_current_signature(self):
        old = dict(source='old'); value, activity = receipt(old)
        with patch.object(base, 'signature', return_value=dict(source='new')), \
                patch.object(base, 'read', side_effect=[value, activity]), \
                patch.object(base, 'digest', return_value='C'*64), \
                patch.object(base, 'namespace', return_value='fixed'):
            with self.assertRaises(ValueError):
                base.closed(SimpleNamespace(corpus=base.CLEAN_CORPUS), 'train', 'balanced_count')

    def test_original_student_header_uses_historical_source_explicitly(self):
        old = dict(source='old')
        state = dict(step=704, tokenizer_sha256='A'*64, tokenizer_lineage='chat32',
            p078=dict(arm='balanced_count', source=old, dedicated_route_loader_required=True))
        base.validate_student_header(state, updates=704, tokenizer_sha256='A'*64,
            arm='balanced_count', expected_input=old)
        for mutation in (dict(step=703), dict(tokenizer_sha256='B'*64), dict(tokenizer_lineage='other'),
                dict(p078=dict(arm='balanced_count', source=old, dedicated_route_loader_required=False))):
            bad = copy.deepcopy(state); bad.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                base.validate_student_header(bad, updates=704, tokenizer_sha256='A'*64,
                    arm='balanced_count', expected_input=old)
        with self.assertRaises(ValueError):
            base.validate_student_header(state, updates=704, tokenizer_sha256='A'*64,
                arm='balanced_count', expected_input=dict(source='new'))

    def test_bridge_does_not_open_unknown_profile_or_bad_digest(self):
        args = SimpleNamespace(profile='somewhere.json', profile_sha256='A'*64)
        with self.assertRaises(ValueError):
            bridge.contract(args)
        args.profile = 'handoff/audit/known.json'
        with patch.object(base, 'digest', return_value='B'*64), self.assertRaises(ValueError):
            bridge.contract(args)

    def test_default_holdout_reader_keeps_current_producer_source_guard(self):
        from scripts import p078_router_holdout_data as holdout
        with patch.object(base,'digest',return_value='A'*64), \
                patch.object(holdout,'read_prepared_contract',return_value=('report','rows')) as reader:
            result=holdout.read_prepared('B'*64,'C'*64)
        self.assertEqual(result,('report','rows'))
        self.assertEqual(reader.call_args.kwargs['expected_source_sha256'],{p:'A'*64 for p in holdout.CODE})
        self.assertEqual(len(reader.call_args.kwargs['expected_source_sha256']),47)

    def test_alias_storage_not_double_counted_in_python_size_estimate(self):
        shared = [1.5, 2.5, 3.5]
        aliased = driver.deep_size([shared, shared])
        separate = driver.deep_size([shared, list(shared)])
        self.assertGreater(separate, aliased)

    def test_actual64_label_io_uses_original_shards_and_row_verifier(self):
        from scripts.test_p078_prefix_router import toy_model, toy_record, fixture_rows, body
        model=toy_model(); evidence=body(model); source=fixture_rows(64)
        records=[toy_record() for _ in source]
        losses, relative, routes=driver.router.trial_labels(model,records[:8],split='train',pad_id=0,width=32,device='cpu')
        events=[]
        for i,record in enumerate(records):
            prefix,feature,fingerprint=driver.prefix_features(model,record,evidence)
            events.append(driver.label_event(i,source[i],record,prefix,feature,fingerprint,
                losses[i%8],relative[i%8],routes))
        with tempfile.TemporaryDirectory() as directory, patch.object(base,'ROOT',Path(directory)):
            result=driver.label_io_probe(SimpleNamespace(resource_only_r1=False),events,evidence)
        self.assertEqual(result['rows'],64)
        self.assertGreater(result['serialized_bytes'],0)
        self.assertGreater(result['parsed_python_bytes'],0)
        self.assertEqual(result['manifest']['lineage']['split'],'TRAIN64_TIMING_ONLY_NOT_FULL_LABEL_ARTIFACT')

    def test_force_length_uses_original_sampler_and_disables_both_stops(self):
        import torch
        from scripts import interactive_research_infer as ui
        class Tokenizer:
            def decode(self, ids, **kwargs): return 'fixed-prefix'
        class Capture:
            def __init__(self, tok): self.decoded_ids = []
        def sample(model, cfg, capture, prompt, **kwargs):
            self.assertEqual(capture.encode(prompt).ids, [8]*896)
            self.assertIs(kwargs['stop_at_eos'], False)
            self.assertEqual(kwargs['stop_token_sequences'], [])
            self.assertIs(kwargs['use_cache'], False)
            capture.decoded_ids=[8]*896+[2]*128
            return '', dict(generated_tokens=128,max_new=128,finish_reason='MAX_NEW_EOS_DISABLED',
                stop_at_eos_requested=False,stop_at_eos_effective=False)
        cfg = SimpleNamespace(max_seq_len=1024)
        prefix = driver.router.route.QuestionPrefix(tuple([8]*896))
        with patch.object(ui, 'generation_tools', return_value=(sample, Capture, lambda m,p:m)), \
                patch.object(driver.router, 'action_scope', return_value=nullcontext(dict(actual_repeats=3))), \
                patch.object(torch.cuda, 'synchronize', side_effect=AssertionError('patched below')):
            # The synchronization below is CPU-only mocked; no CUDA initialization.
            with patch.object(torch.cuda, 'synchronize', return_value=None):
                result = driver.generate(torch, object(), cfg, Tokenizer(), prefix, 3, force_length=True)
        self.assertIsNone(result['actual_answer'])
        self.assertTrue(result['forced_cost_only'])

    def test_actual_cpu_product_sampler_eos_disabled_metadata_and128_ids(self):
        import torch
        from tinylm.infer.generate import sample
        class Capture:
            decoded_ids=[]
            def encode(self,text):return SimpleNamespace(ids=[3,8,4])
            def token_to_id(self,token):return 2
            def decode(self,ids,**kwargs):self.decoded_ids=list(ids);return ''
        class AlwaysEOS(torch.nn.Module):
            def forward(self,x,**kwargs):
                logits=torch.zeros(1,x.shape[1],5)
                logits[...,2]=1
                return logits
        capture=Capture()
        _,raw=sample(AlwaysEOS(),SimpleNamespace(max_seq_len=1024),capture,'prefix',max_new=128,
            temperature=0.,top_k=1,device='cpu',use_cache=False,stop_at_eos=False,
            return_metadata=True,stop_token_sequences=[])
        self.assertEqual(raw['finish_reason'],'MAX_NEW_EOS_DISABLED')
        self.assertNotIn('prompt_tokens',raw)
        normalized=driver.forced_cost_metadata([3,8,4],capture.decoded_ids,raw)
        self.assertEqual(normalized['prompt_tokens'],3)
        self.assertEqual(normalized['generated_token_ids'],[2]*128)
        bad=dict(raw,finish_reason='MAX_NEW')
        with self.assertRaises(ValueError):driver.forced_cost_metadata([3,8,4],capture.decoded_ids,bad)

    def test_new_namespace_and_profile_pair_leave_default_name_intact(self):
        args = SimpleNamespace(resource_only_r1=False)
        self.assertEqual(driver.namespace(args), driver.TAG)
        args.profile='handoff/audit/profile.json'; args.profile_sha256='A'*64
        self.assertEqual(driver.namespace(args), driver.TAG+'_bridge20261027')

    def test_body_exit_failure_still_attempts_every_owned_cleanup_and_keeps_primary(self):
        from types import SimpleNamespace
        import gc
        calls=[]
        model=SimpleNamespace(clear_quant=lambda:calls.append('clear'))
        torch=SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda:calls.append('empty')))
        original=ValueError('original forward error')
        with patch.object(base,'digest',side_effect=OSError('cannot hash')),patch.object(gc,'collect',side_effect=lambda:calls.append('gc')):
            bridge.close_owned_body(model,torch,lambda model:'changed','expected',Path('owned'),'A'*64,True,original)
        self.assertEqual(calls,['clear','gc','empty'])
        self.assertEqual(original.p078_body_exit_details['primary_error']['message'],'original forward error')
        self.assertEqual([v['stage'] for v in original.p078_body_exit_details['exit_errors']],['final_core','checkpoint_bytes'])

    def test_body_exit_without_primary_raises_after_cleanup(self):
        calls=[]
        model=SimpleNamespace(clear_quant=lambda:calls.append('clear'))
        torch=SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda:calls.append('empty')))
        with patch.object(base,'digest',return_value='B'*64),self.assertRaises(RuntimeError) as caught:
            bridge.close_owned_body(model,torch,lambda model:'same','same',Path('owned'),'A'*64,True)
        self.assertEqual(calls,['clear','empty'])
        self.assertIsNone(caught.exception.p078_body_exit_details['primary_error'])

    def test_actual_worker_cap_and_full_phase_forecast_must_fit(self):
        args=SimpleNamespace(mode='labels',max_wall_sec=1800)
        with patch.object(bridge,'selected',return_value=True),patch.object(bridge,'contract',return_value=({'phase_caps_seconds':{'labels':7200}},None,None)):
            with self.assertRaises(base.Hold):driver.actual_phase_admission(args)
            args.max_wall_sec=7200
            with patch.object(driver,'require_budget',return_value={'forecasts_seconds':{'labels':7201}}):
                with self.assertRaises(base.Hold):driver.actual_phase_admission(args)
            with patch.object(driver,'require_budget',return_value={'forecasts_seconds':{'labels':7200}}):
                self.assertEqual(driver.actual_phase_admission(args)['forecasts_seconds']['labels'],7200)

    def test_cpu_contract_never_initialized_cuda(self):
        import torch
        self.assertFalse(torch.cuda.is_initialized())


if __name__ == '__main__':
    unittest.main()
