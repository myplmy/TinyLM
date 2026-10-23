"""BabyLM 실행기의 합성 경계 시험. 실제 자료·체크포인트·CUDA는 사용하지 않는다."""
from __future__ import annotations

import ast
import copy
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import diag_p106b_babylm_causal as m


class DriverTests(unittest.TestCase):
    def cost(self):
        return dict(status="BABYLM_CAUSAL_COST_COMPLETE",returncode=0,model="native595-f",
            source_identity={"synthetic":True},policy=m.policy(),sources_unchanged=True,inputs_unchanged=True,
            wall_seconds=20.,evaluation_seconds=dict(main=2.,supplement=1.),
            group_audits=dict(main=dict(rows=536),supplement=dict(rows=40)))

    def test_import_is_stdlib_only_and_has_no_model_action(self):
        tree=ast.parse(Path(m.__file__).read_text())
        imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any((getattr(n,"module","") or "").startswith(("torch","transformers","tinylm")) for n in imports))
        calls=[n for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)]
        self.assertEqual(calls,[])

    def test_cost_rows_are_eight_per_file_not_first_global_eight(self):
        values=[dict(file=name,line=i) for name in ("a","b") for i in range(10)]
        chosen=m.selected_rows(values,"cost")
        self.assertEqual(len(chosen),16)
        self.assertEqual([r["line"] for r in chosen],[*range(8),*range(8)])
        self.assertIs(m.selected_rows(values,"full"),values)
        with self.assertRaises(ValueError):m.selected_rows(values,"other")

    def test_closed_full_admission_uses_each_group_rate_and_overhead(self):
        now=m.DEADLINE-7200
        value=m.full_admission(self.cost(),{"synthetic":True},"native595-f",now)
        expected=(59875*2/536+5218*1/40)*1.5+17+120
        self.assertAlmostEqual(value["forecast_seconds"],expected)
        self.assertEqual(value["observed_non_eval_overhead_seconds"],17)

    def test_partial_or_changed_cost_never_opens_full(self):
        for key,value in (("status","PARTIAL"),("returncode",9),("model","native595-q"),
            ("source_identity",{}),("policy",{}),("sources_unchanged",False),("inputs_unchanged",False),
            ("group_audits",dict(main=dict(rows=535),supplement=dict(rows=40)))):
            cost=self.cost();cost[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                m.full_admission(cost,{"synthetic":True},"native595-f",m.DEADLINE-7200)

    def test_budget_never_extends_deadline(self):
        with self.assertRaises(ValueError):m.full_admission(self.cost(),{"synthetic":True},"native595-f",m.DEADLINE-60)
        cost=self.cost();cost["evaluation_seconds"]["main"]=200.
        with self.assertRaises(ValueError):m.full_admission(cost,{"synthetic":True},"native595-f",m.DEADLINE-7200)

    def test_bad_timing_not_used_as_speed_claim(self):
        cost=self.cost();cost["evaluation_seconds"]["main"]=float("nan")
        with self.assertRaises(ValueError):m.full_admission(cost,{"synthetic":True},"native595-f",m.DEADLINE-7200)

    def test_write_once_and_twenty_mb_guard(self):
        with tempfile.TemporaryDirectory() as name:
            target=Path(name)/"result.json"
            m.write(target,{"a":1});before=target.read_bytes()
            with self.assertRaises(FileExistsError):m.write(target,{"a":2})
            self.assertEqual(target.read_bytes(),before)
            with patch.object(m,"LIMIT",10),self.assertRaises(ValueError):m.write(Path(name)/"too_large.json",{"a":"x"*20})
            self.assertFalse((Path(name)/"too_large.json").exists())

    def test_manifest_symlink_is_not_opened(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);target=root/"real.txt";target.write_text("fixture")
            linked=root/"alias.txt";linked.symlink_to(target)
            with self.assertRaises(ValueError):m.digest(linked)

    def test_policy_separates_official_function_from_cli_and_training(self):
        value=m.policy()
        self.assertFalse(value["official_cli"]);self.assertFalse(value["training"])
        self.assertEqual(value["batch_size"],8);self.assertEqual(value["temperature"],1.)
        self.assertFalse(value["cache"]);self.assertEqual(value["max_context"],1024)
        self.assertIn("UNMODIFIED",value["implementation"])

    def test_model_flags_cannot_trigger_implicit_execute(self):
        for args in (("--model","native595-f"),("--mode","full"),("--prepare","--model","native595-f")):
            with self.subTest(args=args),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):m.main(args)

    def mock_admission_execute(self,*,model='falcon90m',foreign_pid=False,delay=None,expired_before_idle=False):
        """execute의 실제 입장 순서만 사용한다. Torch/자료/모델은 전부 합성 주입이다."""
        from scripts import diag_p106b_official_core6 as core6
        from scripts import interactive_research_infer as ui
        from scripts import p106b_babylm_causal as helper
        strict_idle=ui.require_idle_gpu
        clock=dict(elapsed=0.,wall=m.DEADLINE-7200);trace=[]
        signature=dict(files={},sha256='SYNTHETIC_SOURCE')
        prepared=dict(status='BABYLM_CAUSAL_DATA_PREPARED',source_identity=signature,input_pins={},actual_counts={})
        gpu='GPU-0011-2233'

        def run(command,**kwargs):
            trace.append('nvml')
            if '--query-gpu=uuid' in command:output=gpu+'\n'
            elif '--query-compute-apps=pid,gpu_uuid' in command:
                output='4242, '+gpu+'\n' if foreign_pid else ''
            else:raise AssertionError('예상하지 않은 합성 NVML 요청')
            return SimpleNamespace(returncode=0,stderr='',stdout=output)

        run_mock=Mock(side_effect=run)
        def idle():
            receipt=strict_idle(run=run_mock,pid=123)
            if delay=='wall':clock['elapsed']=581.
            elif delay=='deadline':clock['wall']=m.DEADLINE-19
            return receipt

        def source_loader(*args,**kwargs):
            if expired_before_idle:clock['elapsed']=581.
            return {},{}

        @contextmanager
        def stop_runtime(*args):
            trace.append('model_runtime')
            raise RuntimeError('합성 모델 입장 경계에서 중단; 실제 모델 없음')
            yield  # contextmanager의 enter만 관찰한다.

        runtime=Mock(side_effect=stop_runtime)
        fake_torch=ModuleType('torch');fake_nn=ModuleType('torch.nn');fake_attention=ModuleType('torch.nn.attention')
        fake_torch.nn=fake_nn;fake_nn.attention=fake_attention
        fake_torch.set_num_threads=lambda count:None
        fake_torch.manual_seed=lambda seed:None
        fake_torch.no_grad=nullcontext
        fake_torch.backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=False)),
            cudnn=SimpleNamespace(allow_tf32=False))
        fake_attention.SDPBackend=SimpleNamespace(MATH='SYNTHETIC_MATH')
        fake_attention.sdpa_kernel=lambda backend:nullcontext()
        fake_gate=ModuleType('scripts.p106b_gate_runtime');fake_gate.wall_limit=lambda seconds:nullcontext()
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder);output=root/'test_result/evidence'/m.OUTPUT.name
            for context in (
                patch.object(m,'ROOT',root),patch.object(m,'OUTPUT',output),
                patch.object(m,'identity',return_value=signature),patch.object(m,'read',return_value=prepared),
                patch.object(m,'pins_and_rows',return_value=({},{},{})),patch.object(m,'digest',return_value='A'*64),
                patch.object(m.time,'perf_counter',side_effect=lambda:clock['elapsed']),
                patch.object(m.time,'time',side_effect=lambda:clock['wall']),
                patch.object(core6,'prerequisites',return_value={}),patch.object(core6,'model_runtime',runtime),
                patch.object(core6,'OFFLINE',{}),patch.object(helper,'load_official',side_effect=source_loader),
                patch.object(ui,'require_idle_gpu',side_effect=idle),
                patch.dict(m.sys.modules,{'torch':fake_torch,'torch.nn':fake_nn,'torch.nn.attention':fake_attention,
                    'scripts.p106b_gate_runtime':fake_gate}),redirect_stdout(io.StringIO())):
                stack.enter_context(context)
            result=m.execute(model,'cost',signature['sha256'])
            report=json.loads((output/model/'cost/report.json').read_text(encoding='utf-8'))
        return result,report,runtime,run_mock,trace

    def test_foreign_gpu_pid_prevents_all_model_runtime_entries(self):
        for model in m.MODELS:
            with self.subTest(model=model):
                result,report,runtime,run,trace=self.mock_admission_execute(model=model,foreign_pid=True)
                runtime.assert_not_called();self.assertNotIn('model_runtime',trace)
                self.assertEqual(run.call_count,2)
                self.assertEqual(result['returncode'],9);self.assertEqual(report['status'],'BABYLM_CAUSAL_PARTIAL')
                self.assertEqual(report['error_type'],'RuntimeError');self.assertIn('4242',report['error'])
                self.assertNotIn('gpu_point_query',report)

    def test_delayed_idle_query_fails_wall_or_absolute_guard_before_model_runtime(self):
        for delay in ('wall','deadline'):
            with self.subTest(delay=delay):
                result,report,runtime,run,trace=self.mock_admission_execute(delay=delay)
                runtime.assert_not_called();self.assertEqual(run.call_count,2)
                self.assertEqual(result['returncode'],9);self.assertEqual(report['error_type'],'TimeoutError')
                self.assertEqual(report['gpu_point_query']['competing_compute_pids'],[])
                self.assertNotIn('model_runtime',trace)

    def test_expired_pre_query_guard_never_queries_or_enters_model_runtime(self):
        result,report,runtime,run,trace=self.mock_admission_execute(expired_before_idle=True)
        runtime.assert_not_called();run.assert_not_called();self.assertEqual(trace,[])
        self.assertEqual(result['returncode'],9);self.assertEqual(report['error_type'],'TimeoutError')

    def test_idle_receipt_is_saved_before_exactly_one_mock_model_runtime_entry(self):
        result,report,runtime,run,trace=self.mock_admission_execute()
        runtime.assert_called_once();self.assertEqual(run.call_count,2)
        self.assertEqual(trace,['nvml','nvml','model_runtime'])
        self.assertEqual(report['gpu_point_query']['gpu_uuid'],'GPU-0011-2233')
        self.assertEqual(report['gpu_point_query']['competing_compute_pids'],[])
        self.assertIn('POINT_QUERY_ONLY',report['gpu_point_query']['scope'])
        self.assertEqual(result['returncode'],9)  # 합성 runtime의 의도한 중단이며 평가 PASS가 아니다.

    def test_v1_snapshots_are_exact_readonly_and_scoring_nodes_unchanged_in_v2(self):
        root=Path(m.__file__).resolve().parents[1]
        pairs=(('20261023_babylm_driver_v1.py.txt','C25DC08AEDF02152A412E0CA55D83A83BF0484B1C7E28DE13A68DF1B186D2DDF'),
               ('20261023_babylm_driver_v1_test.py.txt','E3F1A80F695A69FF4B490D7F3448DA3AC2C282BAFD6408CD5E7EB93D06A514B6'))
        for name,expected in pairs:
            path=root/'handoff/audit/source_snapshots'/name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(),expected)
            self.assertEqual(path.stat().st_mode & 0o222,0)
        before=ast.parse((root/'handoff/audit/source_snapshots'/pairs[0][0]).read_text(encoding='utf-8'))
        after=ast.parse(Path(m.__file__).read_text(encoding='utf-8'))
        actual={node.name:node for node in after.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
        for node in before.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name!='execute':
                self.assertEqual(ast.dump(node,include_attributes=False),ast.dump(actual[node.name],include_attributes=False))
        self.assertEqual(m.OUTPUT.name,'p106b_babylm_causal_v3_s1337')


if __name__=="__main__":unittest.main()
