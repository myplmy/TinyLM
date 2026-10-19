#!/usr/bin/env python3
"""메모리 원형과 작은 CPU fixture만 사용하는 교차 드라이버 회귀.

실제 tagged prepare, 원문, CP tensor, CUDA, 파일/디렉터리 생성은 없다.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import dataclass, asdict
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
from scripts import diag_p106b_route_cross_readout as d
from scripts import p106b_weight_route as route
from scripts.test_p106b_weight_route import Mini


def tiny_info():
    return dict(schema=d.SCHEMA, tag=d.TAG, code_sha256={'fixture.py': 'A' * 64},
                code_complete=True, optimizer_updates=0, checkpoint_writes=0, new_answers=8)


def core(model_or_state):
    state = model_or_state.state_dict() if hasattr(model_or_state, 'state_dict') else model_or_state
    h = hashlib.sha256()
    for name, value in sorted(state.items()):
        h.update(name.encode()); h.update(value.detach().cpu().numpy().tobytes())
    return h.hexdigest().upper()


@dataclass
class FixtureCfg:
    micro_group: int = 2
    twn_thr_ratio: float = .7
    ste_clip: float = 2.5
    n_modes: int = 1
    mode_rank: int = 0
    quant_anneal: float = 1.
    tie_mlp: bool = False
    wq_dtype: str = 'fp32'
    center_weights: bool = False
    sparse34: bool = False
    n_layers: int = 14
    dim: int = 768
    vocab_size: int = 32768
    max_seq_len: int = 1024
    grad_checkpoint: bool = True
    mtp_aux: bool = False


class FixtureModel(Mini):
    def __init__(self):
        super().__init__()
        self.cfg = FixtureCfg()
        for module in self._tlinear_cache:module.cfg = self.cfg
        self.cuda_calls = []

    def cuda(self):
        if getattr(self, '_p106b_weight_route', None) is not None:
            raise AssertionError('CUDA 이동 전 원 훈련 context가 종료되지 않았다')
        self.cuda_calls.append('CPU_ROUTE_CLOSED')
        return self


class Tokens:
    def encode(self, text):return SimpleNamespace(ids=list(range(100, 100 + len(text))))
    def token_to_id(self, name):return {'<eos>': 2, '<|im_end|>': 4}.get(name)
    def decode(self, ids, skip_special_tokens=False):return {777: '응답', 778: '다름'}.get(ids[0], '') if ids else ''


def cases():
    from tinylm.chat.serialize import serialize
    result = [dict(id='case_' + str(i), lane=lane, family='fixture', language=lang,
        messages=[dict(role='user', content='합성 질문 ' + str(i))], gold='절대 추론에 전달하지 않는 골드')
        for i, (lane, lang) in enumerate((('fixture', 'en'), ('user_seen', 'ko')))]
    for case in result:
        prompt=serialize(dict(messages=case['messages']),'chatml',add_generation_prompt=True)
        ids=Tokens().encode(prompt).ids
        case['encoding']=dict(prompt_sha256=d.sha(prompt),prompt_ids_sha256=d.sha(ids),prompt_tokens=len(ids))
    return result


def classify(case, answer):return dict(correct=None if case['lane'] == 'user_seen' else answer == '응답')


def emit(model, cfg, tokenizer, messages):
    from tinylm.chat.serialize import serialize
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
    if '골드' in prompt:raise AssertionError('추론 prefix에 골드가 유출되었다')
    assert model.training is False
    assert all(p.requires_grad for p in model.parameters())
    ids = [777, 4]; content = [777]; answer = '응답'
    g = dict(max_new=64, precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        eos_token_available=True, stop_at_eos_requested=True, stop_at_eos_effective=True,
        stop_token_sequences=[[4]], candidate_answers_supplied=False, terminal_only_removed=True,
        prompt_sha256=d.sha(prompt), prompt_ids_sha256=d.sha(tokenizer.encode(prompt).ids),
        prompt_tokens=len(tokenizer.encode(prompt).ids), generated_ids=ids, terminal_ids=[4], generated_tokens=2,
        finish_reason='STOP_SEQUENCE', matched_stop_sequence=[4], generated_ids_sha256=d.sha(ids),
        content_ids_sha256=d.sha(content), body_utf8_sha256=hashlib.sha256(answer.encode()).hexdigest().upper())
    return answer, g


class Memory:
    """실제 파일 I/O 없이 한 회귀의 원형 바이트만 메모리에 보존한다."""
    def __init__(self):self.files = {}
    def exists(self, path):return Path(path) in self.files or any(p.is_relative_to(path) for p in self.files)
    def raw(self, path):
        if Path(path) not in self.files:raise d.Pending('합성 선결 파일이 없다')
        return self.files[Path(path)]
    def digest(self, path):return hashlib.sha256(self.raw(path)).hexdigest().upper()
    def required(self, path):return json.loads(self.raw(path))
    def write(self, path, value):
        path = Path(path)
        if path in self.files:raise FileExistsError('합성 원형은 덮어쓰지 않는다')
        data = (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode()
        if len(data) >= 20_000_000:raise ValueError('합성 원형 크기 초과')
        self.files[path] = data

    def writer(self, directory, stem, limit):
        memory = self
        class Writer:
            def __init__(self):self.lines = [];self._file = None
            def append(self, value):
                self.lines.append((json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode())
                memory.files[Path(directory) / (stem + '_000000.jsonl')] = b''.join(self.lines)
            def close(self, *, lineage):
                data = b''.join(self.lines);checksum = hashlib.sha256(data).hexdigest().upper()
                manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', limit_bytes=limit, rows=len(self.lines),
                    bytes=len(data), concat_sha256=checksum, lineage=lineage,
                    shards=[dict(path=stem + '_000000.jsonl', bytes=len(data), rows=len(self.lines), sha256=checksum)])
                memory.write(Path(directory) / (stem + '_shards_manifest.json'), manifest)
                return manifest
        return Writer()


class ContractTests(unittest.TestCase):
    def test_full_production_info_prepare_roundtrip_without_minimal_info_mock(self):
        memory = Memory()
        production_info = d.info()
        digest_real = d.digest
        cc = [dict(id=f'full_case_{i:04d}', lane='user_seen' if i >= d.ANSWERS - d.USER_CASES else 'coded')
              for i in range(d.ANSWERS)]
        bound = dict(fixture='metadata only; no checkpoint tensor or real namespace')
        def checksum(path):
            return memory.digest(path) if Path(path) in memory.files else digest_real(path)
        with patch.object(d, 'authority', return_value=10000.), \
                patch.object(d, 'source_state', return_value=(cc, {}, bound, {}, None)), \
                patch.multiple(d, exists=memory.exists, write=memory.write,
                    required=memory.required, digest=checksum), patch.object(d, 'completed_activity'):
            self.assertEqual(d.prepare(), 0)
            frozen, observed_cases, *_ = d.prepared()
        self.assertEqual(observed_cases, cc)
        for key, value in production_info.items():
            self.assertEqual(frozen[key], value, key)
        self.assertEqual(frozen['models_loaded'], 0)
        self.assertEqual(frozen['checkpoint_tensor_loads'], 0)
        self.assertEqual(len(frozen['user_ids']), d.USER_CASES)
        self.assertEqual(set(memory.files), {
            d.CACHE / 'frozen_reference.json', d.EVIDENCE / 'cpu_contract.json', d.result_path('prepare')})

    def test_four_off_diagonals_only_and_no_ignored_selectors(self):
        keys = {d.phase_key('evaluate', trained, infer, endpoint) for endpoint in d.ENDPOINTS
                for trained, infer in (('ternary', 'float'), ('float', 'ternary'))}
        self.assertEqual(len(keys), 4)
        for args in (('evaluate', 'float', 'float', 'native'), ('evaluate', 'ternary', None, 'native'),
                     ('evaluate', 'float', 'ternary', None), ('prepare', 'float', None, None)):
            with self.assertRaises(ValueError):d.phase_key(*args)

    def test_absolute_authority_keeps_six_hundred_seconds(self):
        self.assertEqual(d.authority(d.END - timedelta(seconds=660)), 60.)
        for when in (d.END - timedelta(seconds=600), d.END, d.END.replace(tzinfo=None)):
            with self.assertRaises((ValueError, d.Pending)):d.authority(when)

    def test_path_scope_refuses_traversal_protected_and_external_paths(self):
        for path in (Path('/tmp/not_a_repo_input'), d.ROOT / '../bad', d.ROOT / 'datasets/TinyDataset/private', d.ROOT / '.claude/x'):
            with self.assertRaises(ValueError):d.safe(path)

    def test_phase_pipeline_uses_new_script_and_own_regression_only(self):
        phases = d.phase_commands('evaluate', 'float', 'ternary', 'sft', 900)
        self.assertEqual([v[0] for v in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('scripts.test_p106b_route_cross_readout', phases[0][1])
        for value in ('--trained-mode', 'float', '--inference-mode', 'ternary', '--endpoint', 'sft', '--worker'):
            self.assertIn(value, phases[-1][1])
        for value in (True, 59, d.MAX_WORKER + 1):
            with self.assertRaises(ValueError):d.phase_commands('prepare', None, None, None, value)

    def test_missing_original_sources_are_pending_before_gpu(self):
        with patch.object(d, 'authority', return_value=10000.), patch.object(d, 'prepared', side_effect=d.Pending('네 CP가 미완이다')), \
                patch('scripts.p106b_gate_runtime.idle_before_gpu') as idle, patch.object(d, 'cross_runtime') as load:
            with self.assertRaises(d.Pending):d.evaluate('ternary', 'float', 'native')
        idle.assert_not_called();load.assert_not_called()

    def test_paired_strata_keep_unscored_user_cases(self):
        cc = cases();left = [dict(id=c['id'], answer='다름', metrics=classify(c, '다름')) for c in cc]
        right = [dict(id=c['id'], answer='응답', metrics=classify(c, '응답')) for c in cc]
        rows = d.paired(left, right, cc)
        self.assertEqual(sum(v.get('scored', 0) for v in rows), 1)
        self.assertEqual(sum(v.get('right_only', 0) for v in rows), 1)
        with self.assertRaises(ValueError):d.paired(left[::-1], right, cc)

    def test_launcher_reuses_own_pgid_cleanup_and_never_kills_foreign_group(self):
        for owner in (123, 456):
            process=Mock(pid=123)
            process.poll.return_value=None
            process.wait.side_effect=[subprocess.TimeoutExpired('fixture',1),0]
            with patch.object(d.n.subprocess,'Popen',return_value=process) as popen, \
                    patch.object(d.n.os,'getpgid',return_value=owner),patch.object(d.n.os,'killpg') as kill:
                self.assertEqual(d.n.launch(['fixture'],1),124)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            if owner==123:kill.assert_called_once_with(123,signal.SIGTERM)
            else:kill.assert_not_called()

    def test_each_phase_uses_its_own_wall_limit_and_expiry_is_hold(self):
        with patch.object(d,'authority',return_value=10000.),patch.object(d.n,'launch',return_value=0) as launch:
            self.assertEqual(d.launch_phase(['fixture','--max-wall-sec','600'],60),0)
            launch.assert_called_once_with(['fixture','--max-wall-sec','600'],720)
        with patch.object(d,'authority',side_effect=d.Pending('기록 예비')),patch.object(d.n,'launch') as launch:
            self.assertEqual(d.launch_phase(['fixture'],60),8)
        launch.assert_not_called()


class ReadoutFixture(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack();self.memory = Memory();self.cc = cases();self.tok = Tokens();self.model = FixtureModel()
        self.source = SimpleNamespace(emit64=Mock(side_effect=emit), classify_case=classify,
            recount=lambda events, cc, tok: dict(actual_answers=len(events), exact=sum(e['metrics']['correct'] is True for e in events)))
        self.runtime = SimpleNamespace(state_fingerprint=core)
        self.stack.enter_context(patch.object(d, 'ANSWERS', 2));self.stack.enter_context(patch.object(d, 'USER_CASES', 1))
        self.stack.enter_context(patch.object(d, 'DISPLAY_COUNT', 1));self.stack.enter_context(patch.object(d, 'info', side_effect=tiny_info))
        self.stack.enter_context(patch.object(d, 'authority', return_value=10000.))
        self.stack.enter_context(patch.multiple(d, required=self.memory.required, raw_bytes=self.memory.raw,
            digest=self.memory.digest, write=self.memory.write, exists=self.memory.exists, ShardWriter=self.memory.writer))
        self.stack.enter_context(patch.object(d.n, 'modules', return_value=(self.runtime, self.source, route)))
        self.memory.write(d.CACHE / 'frozen_reference.json', {'fixture': True})
        self.training = {}
        self.links = {}
        self.diagonals = {}
        for endpoint in d.ENDPOINTS:
            for trained in d.ROUTES:
                cp = d.n.checkpoint(trained, endpoint);self.memory.files[cp] = ('합성 CPU CP 바이트 표식 ' + trained + endpoint).encode()
                key = d.slot(endpoint, trained)
                self.training[key] = dict(arm=trained, endpoint=endpoint, updates=d.n.UPDATES if endpoint == 'native' else d.n.SFT_UPDATES,
                    checkpoint_sha256=self.memory.digest(cp), final_core_sha256=core(self.model), scratch_core_sha256=core(self.model),
                    reference_sha256='A' * 64, parent_checkpoint_sha256=None, parent_core_sha256=None)
                self.links[key] = dict(diagonal_report_sha256='B' * 64, summary={'actual_answers': 2}, native32_fp32=self.native())
                ev = []
                for c in self.cc:
                    self.model.eval();answer,g = emit(self.model, self.model.cfg, self.tok, c['messages'])
                    ev.append(dict(id=c['id'], case_sha256=d.sha(c), answer=answer, generation=g, metrics=classify(c, answer),
                        arm=trained, endpoint=endpoint, checkpoint_sha256=self.training[key]['checkpoint_sha256'], quantization_route=route.route_metadata(trained)))
                self.diagonals[key] = ev
        self.reference = dict(binding=dict(endpoints=self.links), display_ids=['case_0'], user_ids=['case_1'])

    def tearDown(self):self.stack.close()

    def native(self):return dict(ce=1., targets=32768, windows=32, val_sha256=d.n.VAL_SHA, precision='FP32_MATH')

    @contextmanager
    def runtime_context(self, trained, infer, endpoint, training):
        cfg_hash = d.sha(asdict(self.model.cfg))
        receipt = dict(training_mode=trained, inference_mode=infer, training_quantization_route=route.route_metadata(trained),
            cpu_strict_keys_dtypes_aliases=True, loaded_core_sha256=core(self.model), cfg_sha256=cfg_hash,
            training_context_closed_before_cuda=True, inference_context_opened_after_load=True)
        facade = SimpleNamespace(no_grad=torch.no_grad)
        with route.weight_route(self.model, infer) as handle:
            yield facade, self.model, self.model.cfg, self.tok, handle, receipt

    def execute_one(self, trained='ternary', infer='float', endpoint='native'):
        with patch.object(d, 'prepared', return_value=(self.reference,self.cc,self.training,self.diagonals,self.tok)), \
                patch.object(d, 'cross_runtime', side_effect=self.runtime_context), \
                patch.object(d.n, 'native_probe', side_effect=lambda *_:self.native()), \
                patch('scripts.p106b_gate_runtime.idle_before_gpu'), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.evaluate(trained, infer, endpoint), 0)
        return self.memory.required(d.result_path(d.phase_key('evaluate', trained, infer, endpoint))), output.getvalue()

    def test_same_1694_protocol_fixture_emits_no_gold_and_all_user_samples(self):
        report, output = self.execute_one()
        self.assertEqual(report['actual_cases'], 2)
        self.assertEqual(self.source.emit64.call_count, 2)
        self.assertEqual(self.source.emit64.call_args_list[1].args[-1], self.cc[1]['messages'])
        samples = [json.loads(line.split('] ',1)[1]) for line in output.splitlines() if line.startswith('[ROUTE_CROSS_SAMPLE]')]
        self.assertEqual([v['id'] for v in samples], ['case_0','case_1'])
        self.assertTrue(all(v['finish_reason']=='STOP_SEQUENCE' for v in samples))
        self.assertTrue(all('골드' not in str(v['messages']) for v in samples))

    def test_report_recount_strictly_reuses_both_training_and_inference_metadata(self):
        report,_ = self.execute_one();training=self.training['native_ternary']
        events, summary=d.validate_cross_report(report,'ternary','float','native',training,self.cc,self.tok)
        self.assertEqual(summary['actual_answers'],2)
        for name,value in (('inference_mode','ternary'),('core_after','C'*64),('requires_grad_unchanged',False)):
            bad=deepcopy(report);bad[name]=value
            with self.assertRaises(ValueError):d.validate_cross_report(bad,'ternary','float','native',training,self.cc,self.tok)
        bad=deepcopy(report);bad['load_receipt']['training_context_closed_before_cuda']=False
        with self.assertRaises(ValueError):d.validate_cross_report(bad,'ternary','float','native',training,self.cc,self.tok)

    def test_event_route_terminal_body_or_case_tamper_is_rejected(self):
        report,_=self.execute_one();key=d.phase_key('evaluate','ternary','float','native')
        event=d.read_answers(d.RAW/key,report['raw_manifest'],2)[0]
        for field,value in (('trained_mode','float'),('inference_mode','ternary'),('case_sha256','D'*64),('answer','바뀜')):
            bad=deepcopy(event);bad[field]=value
            with self.assertRaises(ValueError):d.validate_event(bad,self.cc[0],self.tok,'ternary','float','native',report['checkpoint_sha256'])
        bad=deepcopy(event);bad['generation']['terminal_ids']=[]
        with self.assertRaises(ValueError):d.validate_event(bad,self.cc[0],self.tok,'ternary','float','native',report['checkpoint_sha256'])

    def test_frozen_prefix_corruption_is_before_any_answer(self):
        self.cc[0]['encoding']['prompt_ids_sha256']='C'*64
        with self.assertRaisesRegex(ValueError,'prefix'):self.execute_one()
        self.source.emit64.assert_not_called()

    def test_raw_manifest_paths_and_bytes_are_checked_before_recount(self):
        report,_=self.execute_one();key=d.phase_key('evaluate','ternary','float','native');manifest=report['raw_manifest']
        bad=deepcopy(manifest);bad['shards'][0]['path']='../answers_000000.jsonl'
        with self.assertRaises(ValueError):d.read_answers(d.RAW/key,bad,2)
        raw=d.RAW/key/'answers_000000.jsonl';self.memory.files[raw]+=b' '
        with self.assertRaises(ValueError):d.read_answers(d.RAW/key,manifest,2)

    def test_diagonal_reader_requires_original_route_report_and_ordered_raw(self):
        trained,endpoint='ternary','native';key=d.n.phase_key('evaluate',trained,endpoint)
        training=self.training['native_ternary'];events=self.diagonals['native_ternary']
        lineage=dict(tag=d.n.TAG,arm=trained,endpoint=endpoint,checkpoint_sha256=training['checkpoint_sha256'],
            core_sha256=training['final_core_sha256'],cases_sha256=d.sha(self.cc),quantization_route=route.route_metadata(trained))
        writer=self.memory.writer(d.n.RAW/key,'answers',19_999_999)
        for event in events:writer.append(event)
        manifest=writer.close(lineage=lineage)
        self.model.eval()
        with route.weight_route(self.model,trained) as handle:
            self.model.freeze_quant();receipt=d.n.route_receipt(self.model,handle)
        report=dict(status='ACTUAL_ANSWERS_COLLECTED',arm=trained,endpoint=endpoint,actual_cases=2,
            checkpoint_sha256=training['checkpoint_sha256'],core_before=training['final_core_sha256'],
            core_after=training['final_core_sha256'],cases_sha256=d.sha(self.cc),lineage=lineage,raw_manifest=manifest,
            quantization_route=route.route_metadata(trained),route=receipt,native32_fp32=self.native(),source_fixture=True)
        self.memory.write(d.n.result_path(key),report)
        with patch.object(d.n,'completed_activity'),patch.object(d.n,'required',side_effect=self.memory.required), \
                patch.object(d.n,'info',return_value={'source_fixture':True}):
            self.assertEqual(d.diagonal(trained,endpoint,training,self.cc,self.tok)[1],events)
            bad=deepcopy(report);bad['core_after']='C'*64
            self.memory.files[d.n.result_path(key)]=json.dumps(bad).encode()
            with self.assertRaises(ValueError):d.diagonal(trained,endpoint,training,self.cc,self.tok)

    def test_source_state_does_not_write_or_mutate_original_pins(self):
        reference=dict(binding=dict(source_cases_sha256=d.sha(self.cc)))
        original=(d.n.TAG,d.n.CACHE,d.n.RAW,d.n.TRAIN_SHA,d.n.PARENT_SHA)
        for endpoint in d.ENDPOINTS:
            for trained in d.ROUTES:
                mode='train' if endpoint=='native' else 'sft';key=d.n.phase_key('evaluate',trained,endpoint)
                self.memory.write(d.n.result_path(d.n.phase_key(mode,trained)),{'fixture':True})
                self.memory.write(d.n.EVIDENCE/('activity_'+d.n.phase_key(mode,trained)+'.json'),{'fixture':True})
                self.memory.write(d.n.result_path(key),{'fixture':True})
                self.memory.write(d.n.EVIDENCE/('activity_'+key+'.json'),{'fixture':True})
                self.memory.write(d.n.RAW/key/'answers_shards_manifest.json',{'fixture':True})
        self.memory.write(d.n.CACHE/'frozen_reference.json',{'fixture':True})
        self.memory.write(d.n.EVIDENCE/'cpu_contract.json',{'fixture':True})
        def training(mode,trained):return self.training[d.slot('native' if mode=='train' else 'sft',trained)]
        def diagonal(trained,endpoint,training,cc,tok):
            return dict(raw_manifest={'fixture':True},native32_fp32=self.native()),self.diagonals[d.slot(endpoint,trained)],{'actual_answers':2}
        before=deepcopy(self.memory.files)
        with patch.object(d.n,'prepared',return_value=(reference,{},self.cc,[])),patch.object(d.n,'train_report',side_effect=training), \
                patch.object(d,'diagonal',side_effect=diagonal),patch.object(d,'tokenizer',return_value=self.tok), \
                patch.object(d.n,'info',return_value={'code_sha256':{'fixture.py':'A'*64}}):
            result=d.source_state()
            self.assertEqual(result[0],self.cc)
            self.assertEqual(len(result[1]),4)
            self.training['sft_float']['scratch_core_sha256']='D'*64
            with self.assertRaises(ValueError):d.source_state()
        self.assertEqual(self.memory.files,before)
        self.assertEqual((d.n.TAG,d.n.CACHE,d.n.RAW,d.n.TRAIN_SHA,d.n.PARENT_SHA),original)

    def test_four_crosses_and_reused_diagonals_have_separate_denominators(self):
        for endpoint in d.ENDPOINTS:
            for trained,infer in (('ternary','float'),('float','ternary')):self.execute_one(trained,infer,endpoint)
        with patch.object(d,'prepared',return_value=(self.reference,self.cc,self.training,self.diagonals,self.tok)),patch.object(d,'completed_activity'):
            self.assertEqual(d.readback(),0)
        result=self.memory.required(d.result_path('readback'))
        self.assertEqual((result['fresh_off_diagonal_answers'],result['reused_diagonal_answers']),(8,8))
        self.assertEqual(len(result['summaries']),8);self.assertEqual(len(result['paired_contrasts']),8)
        self.assertEqual(sum(v['origin']=='REUSED_DIAGONAL' for v in result['summaries']),4)
        self.assertEqual(result['checkpoint_tensor_loads'],0)

    def test_inference_error_keeps_partial_raw_and_no_success_report(self):
        prior=emit
        def fail_on_second(model,cfg,tok,messages):
            if messages==self.cc[1]['messages']:raise RuntimeError('합성 원답 중간 실패')
            return prior(model,cfg,tok,messages)
        self.source.emit64.side_effect=fail_on_second
        with self.assertRaisesRegex(RuntimeError,'원답 중간'):self.execute_one()
        key=d.phase_key('evaluate','ternary','float','native')
        self.assertTrue(self.memory.exists(d.RAW/key/'answers_000000.jsonl'))
        self.assertFalse(self.memory.exists(d.RAW/key/'answers_shards_manifest.json'))
        self.assertFalse(self.memory.exists(d.result_path(key)))

    def test_prepare_and_reference_revalidation_use_only_new_write_namespace(self):
        self.memory.files.pop(d.CACHE/'frozen_reference.json')
        binding=dict(endpoints=self.links)
        state=(self.cc,self.training,binding,self.diagonals,self.tok)
        with patch.object(d,'source_state',return_value=state):
            self.assertEqual(d.prepare(),0)
            with patch.object(d,'completed_activity'):self.assertEqual(d.prepared()[1],self.cc)
            with self.assertRaises(FileExistsError):d.prepare()
            frozen=self.memory.required(d.CACHE/'frozen_reference.json');frozen['user_ids']=[]
            self.memory.files[d.CACHE/'frozen_reference.json']=json.dumps(frozen).encode()
            with self.assertRaises(ValueError):d.prepared()
        self.assertTrue(all(p.is_relative_to(d.CACHE) or p.is_relative_to(d.RAW) or p.is_relative_to(d.EVIDENCE)
                            or p in [d.n.checkpoint(a,e) for a in d.ROUTES for e in d.ENDPOINTS] for p in self.memory.files))

    def test_worker_error_activity_and_zero_without_report_cannot_pass(self):
        for cause in (d.Pending('원 선결 미완'),ValueError('합성 손상')):
            self.memory.files={p:v for p,v in self.memory.files.items() if not p.name.startswith('activity_')}
            with patch.object(d,'prepare',side_effect=cause),patch.object(d.os,'getpid',return_value=7), \
                    patch.object(d.os,'getpgid',return_value=7),patch('scripts.p106b_gate_runtime.wall_limit',return_value=nullcontext()):
                with self.assertRaises(type(cause)):d.worker('prepare',None,None,None,60)
            record=self.memory.required(d.EVIDENCE/'activity_prepare.json')
            self.assertFalse(record['complete']);self.assertEqual(record['returncode'],8 if isinstance(cause,d.Pending) else 9)
        self.memory.files={p:v for p,v in self.memory.files.items() if not p.name.startswith('activity_')}
        with patch.object(d,'prepare',return_value=0),patch.object(d.os,'getpid',return_value=7), \
                patch.object(d.os,'getpgid',return_value=7),patch('scripts.p106b_gate_runtime.wall_limit',return_value=nullcontext()):
            with self.assertRaises(ValueError):d.worker('prepare',None,None,None,60)
        self.assertEqual(self.memory.required(d.EVIDENCE/'activity_prepare.json')['returncode'],9)

    def test_foreign_pgid_and_expired_budget_block_all_work(self):
        with patch.object(d.os,'getpid',return_value=7),patch.object(d.os,'getpgid',return_value=8),patch.object(d,'prepare') as work:
            with self.assertRaises(ValueError):d.worker('prepare',None,None,None,60)
        work.assert_not_called()
        with patch.object(d,'authority',return_value=59.),patch.object(d,'source_state') as source:
            with self.assertRaises(d.Pending):d.worker('source',None,None,None,60)
        source.assert_not_called()

    def test_own_sigterm_writes_failure_activity_and_restores_handler(self):
        previous=signal.getsignal(signal.SIGTERM)
        def stop():signal.getsignal(signal.SIGTERM)(signal.SIGTERM,None)
        with patch.object(d,'prepare',side_effect=stop),patch.object(d.os,'getpid',return_value=7), \
                patch.object(d.os,'getpgid',return_value=7),patch('scripts.p106b_gate_runtime.wall_limit',return_value=nullcontext()):
            with self.assertRaises(KeyboardInterrupt):d.worker('prepare',None,None,None,60)
        value=self.memory.required(d.EVIDENCE/'activity_prepare.json')
        self.assertEqual(value['returncode'],130);self.assertFalse(value['complete'])
        self.assertIs(signal.getsignal(signal.SIGTERM),previous)

    def test_completed_activity_requires_exact_code_pgid_report_and_reference_hash(self):
        self.memory.write(d.result_path('prepare'),{'fixture':True})
        value=dict(schema=d.SCHEMA,tag=d.TAG,key='prepare',mode='prepare',trained_mode=None,inference_mode=None,endpoint=None,
            code_sha256=tiny_info()['code_sha256'],seconds=1.,max_wall_sec=60,returncode=0,complete=True,error_type=None,
            worker_pid=7,worker_pgid=7,started_at=(d.END-timedelta(hours=2)).isoformat(),
            ended_at=(d.END-timedelta(hours=2)+timedelta(seconds=1)).isoformat(),
            result_sha256=self.memory.digest(d.result_path('prepare')),reference_sha256=self.memory.digest(d.CACHE/'frozen_reference.json'))
        self.memory.write(d.EVIDENCE/'activity_prepare.json',value)
        self.assertEqual(d.completed_activity('prepare'),value)
        for field,changed in (('worker_pgid',8),('code_sha256',{}),('result_sha256','C'*64),('complete',False)):
            bad=deepcopy(value);bad[field]=changed
            self.memory.files[d.EVIDENCE/'activity_prepare.json']=json.dumps(bad).encode()
            with self.assertRaises((ValueError,d.Pending)):d.completed_activity('prepare')

    def test_internal_worker_error_has_traceback_and_final_message(self):
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(d,'worker',side_effect=ValueError('합성 도구 오류')),redirect_stdout(stdout),redirect_stderr(stderr):
            code=d.main(['--mode','prepare','--worker','--execute'])
        self.assertEqual(code,9);self.assertIn('Traceback',stderr.getvalue());self.assertIn('[ROUTE_CROSS_FINAL]',stdout.getvalue())


class RuntimeTests(unittest.TestCase):
    def fixture(self, trained, endpoint='native'):
        model=FixtureModel();scratch=core(model)
        state={k:v.detach().clone()+.07 for k,v in model.state_dict().items()}
        training=dict(arm=trained,endpoint=endpoint,updates=d.n.UPDATES if endpoint=='native' else d.n.SFT_UPDATES,
            checkpoint_sha256='B'*64,scratch_core_sha256=scratch,final_core_sha256=core(state),reference_sha256='A'*64,
            parent_checkpoint_sha256=None,parent_core_sha256=None)
        saved=dict(model=state,cfg=asdict(model.cfg),step=training['updates'],tokenizer_sha256=d.n.TOKENIZER_SHA,
            tokenizer_lineage='chat32',quantization_route=route.route_metadata(trained),experiment=d.n.cp_experiment(training))
        facade=SimpleNamespace(load=Mock(return_value=saved),Tensor=torch.Tensor,equal=torch.equal,
            backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=True)),cudnn=SimpleNamespace(allow_tf32=True)),
            cuda=SimpleNamespace(empty_cache=Mock()))
        runtime=SimpleNamespace(load_runtime=Mock(return_value=(facade,model,model.cfg,Tokens(),scratch)),state_fingerprint=core)
        return model,training,saved,facade,runtime

    def test_cpu_original_route_is_closed_before_cuda_and_other_route(self):
        for trained,infer in (('float','ternary'),('ternary','float')):
            model,training,saved,facade,runtime=self.fixture(trained)
            with patch.object(d.n,'modules',return_value=(runtime,None,route)),patch.object(d,'digest',return_value='B'*64):
                with d.cross_runtime(trained,infer,'native',training) as values:
                    self.assertIs(values[1],model);self.assertEqual(values[4].mode,infer)
                    self.assertEqual(core(model),training['final_core_sha256'])
                    self.assertEqual(model.cuda_calls,['CPU_ROUTE_CLOSED'])
                    self.assertTrue(values[5]['training_context_closed_before_cuda'])
                    self.assertEqual(saved['quantization_route'],route.route_metadata(trained))
            self.assertIsNone(getattr(model,'_p106b_weight_route',None))
            facade.load.assert_called_once_with(d.n.checkpoint(trained,'native'),map_location='cpu',weights_only=True)

    def test_bad_cpu_dtype_cfg_mode_or_core_is_before_cuda(self):
        for change in ('dtype','cfg','mode','core'):
            model,training,saved,facade,runtime=self.fixture('float')
            if change=='dtype':saved['model']['a.weight']=saved['model']['a.weight'].double()
            if change=='cfg':saved['cfg']['dim']=999
            if change=='mode':saved['quantization_route']=route.route_metadata('ternary')
            if change=='core':training['final_core_sha256']='C'*64;saved['experiment']=d.n.cp_experiment(training)
            with patch.object(d.n,'modules',return_value=(runtime,None,route)),patch.object(d,'digest',return_value='B'*64):
                with self.assertRaises(ValueError):
                    with d.cross_runtime('float','ternary','native',training):pass
            self.assertEqual(model.cuda_calls,[])

    def test_generic_float_guard_remains_strict_and_relabelled_payload_rejected(self):
        _,_,saved,_,_=self.fixture('float')
        with self.assertRaises(RuntimeError):route.generic_loader_guard(saved)
        self.assertEqual(d.n.TAG,'p106b_native_weight_route_v1_s1337')
        self.assertEqual(d.n.CACHE,d.n.ROOT/'data_cache'/d.n.TAG)

    def test_context_error_restores_methods_and_requires_grad(self):
        model,training,saved,facade,runtime=self.fixture('ternary')
        with patch.object(d.n,'modules',return_value=(runtime,None,route)),patch.object(d,'digest',return_value='B'*64):
            with self.assertRaisesRegex(RuntimeError,'합성'):
                with d.cross_runtime('ternary','float','native',training):raise RuntimeError('합성')
        self.assertNotIn('forward',model.a.__dict__)
        self.assertTrue(all(p.requires_grad for p in model.parameters()))


if __name__=='__main__':
    torch.set_num_threads(1)
    unittest.main()
