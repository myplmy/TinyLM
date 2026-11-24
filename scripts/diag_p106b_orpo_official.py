#!/usr/bin/env python3
"""Read-only ORPO176/64 and immediate-parent official Core6/KoBEST evaluation.

No model imports on import or --check-only. Reuse the pinned official tasks,
likelihood adapter, raw shard writer and independent per-item metric audit.
Legacy checkpoint routing is explicitly original ternary-at-anneal1, not the
separately trained Native595 float route. No training or checkpoint writes.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import sysconfig
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_official_core6 as official
from scripts import p106b_official_lm_adapter as adapter
from scripts import prepare_p106b_kobest_official_eval as kobest
from scripts.p106b_shards import ShardWriter, verify

TAG = 'p106b_orpo_official_v2_20261113'
OUTPUT = ROOT / 'test_result/evidence' / TAG
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
MODELS = {
    'parent176': ('runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt',
                  '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'),
    'orpo176': ('runs/ckpt/m100s10_ko-en_context_orpo_dense_chat32_p106b_context_orpo_v1_s1337_pair010.pt',
                'E86E5AA15D406EDBB4C22E3F5C7D7E59A510DB08B06E2E97454C47370B0045A1'),
    'parent64': ('runs/ckpt/m100s10_ko-en_evidencerecovery_dense_chat32_p106b_evidence_recovery_v1_s1337_evidence_recovery.pt',
                 'E9707AA2ABB55054DA226A6303A0EEAD8BA0B653029E24AFAD2A63D86E729E42'),
    'orpo64': ('runs/ckpt/m100s10_ko-en_evidencepref_dense_chat32_p106b_evidence_preference_v1_s1337_orpo010.pt',
               '0F8A387F8B2A0F4422B35C920330C162280A85E05BF3EBE4FBD72A88AB613D90'),
}
CODE = tuple(sorted(set((*official.SOURCES,
    'scripts/diag_p106b_official_adapter.py', 'scripts/diag_p106b_native_format_official.py',
    'scripts/prepare_p106b_kobest_official_eval.py', 'scripts/diag_p106b_orpo_official.py',
    'scripts/test_p106b_orpo_official.py',
    'tinylm/config.py', 'tinylm/model/transformer.py', 'tinylm/model/ternary.py',
    'tinylm/model/modules.py', 'scripts/diag_p101a_sft_mtp.py'))))


def write(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    if len(data) >= 20_000_000:
        raise ValueError('20MB report limit')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data + b'\n')


def identity():
    files = {name: official.digest(ROOT / name) for name in CODE}
    return dict(files=files, sha256=hashlib.sha256(adapter.canonical(files)).hexdigest().upper())


def metadata(name):
    path, expected = MODELS[name]
    checkpoint = ROOT / path
    if any(p.is_symlink() for p in (checkpoint, *checkpoint.parents)):
        raise ValueError('regular checkpoint required')
    if official.digest(checkpoint) != expected or official.digest(TOKENIZER) != TOKENIZER_SHA:
        raise ValueError('fixed checkpoint/tokenizer identity differs')
    return dict(name=name, checkpoint=path, checkpoint_sha256=expected,
                tokenizer_sha256=TOKENIZER_SHA, bytes=checkpoint.stat().st_size)


def load_tasks():
    from scripts.p106b_official_tasks import load_tasks as core_tasks
    tasks, specs, provenance = core_tasks()
    manifest_path = kobest.ASSETS / 'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    if manifest['dataset_revision'] != kobest.REVISION or manifest['source_commit'] != adapter.COMMIT:
        raise ValueError('fixed KoBEST revision/framework required')
    original = json.loads(adapter.MANIFEST.read_bytes())
    kobest.task_sources(adapter.SOURCE, Path(original['archive_path']))
    from lm_eval.tasks._yaml_loader import load_yaml
    from lm_eval.api.task import ConfigurableTask
    import copy
    signatures = {}
    for row in manifest['tests']:
        path = ROOT / row['local_path']
        if official.digest(path) != row['sha256']:
            raise ValueError('KoBEST test bytes differ')
        observed = kobest.scan_test(path, row['family'])
        if observed['ordered_json_sha256'] != row['ordered_json_sha256']:
            raise ValueError('KoBEST test order/labels differ')
        yaml = adapter.SOURCE / 'lm_eval/tasks/kobest' / (row['task'] + '.yaml')
        task_fields = load_yaml(str(yaml), resolve_func=True, recursive=True)
        before = {k: task_fields.get(k) for k in row['semantic_fields_unchanged']}
        task_fields.update(copy.deepcopy(row['storage_overrides']))
        task = ConfigurableTask(config=task_fields)
        if len(task.eval_docs) != row['rows'] or set(task.dataset) != {'test'}:
            raise ValueError('KoBEST processed denominator or test-only split differs')
        for key, value in before.items():
            if value is not None and getattr(task.config, key) != value:
                raise ValueError('official KoBEST semantic field changed: ' + key)
        tasks[row['task']] = task
        signatures[row['task']] = dict(rows=row['rows'], sha256=row['sha256'],
                                       ordered_json_sha256=row['ordered_json_sha256'],
                                       yaml_sha256=official.digest(yaml))
    expected = dict(official.TASK_COUNTS, **{'kobest_' + k: v[0] for k, v in kobest.SPECS.items()})
    if {name: len(task.eval_docs) for name, task in tasks.items()} != expected:
        raise ValueError('all eleven official task denominators required')
    return tasks, dict(core6=specs, kobest=signatures,
                      kobest_manifest_sha256=official.digest(manifest_path)), provenance


def audit_task(task, rows, expected):
    """Use official string-target-to-choice-index semantics for KoBEST COPA.

    Official ConfigurableTask.process_results accepts a choice string as gold.
    The pre-existing Core6 audit accepts integer indices only. This read-only
    proxy changes the audit input representation, never the evaluated task,
    original gold label, generated request, raw result or official metric.
    """
    if not task.config.task.startswith('kobest_'):
        return official.audit_samples(task, rows, expected)
    from types import SimpleNamespace

    def index(doc):
        choices = task.doc_to_choice(doc)
        gold = task.doc_to_text(doc) if task.multiple_input else task.doc_to_target(doc)
        if isinstance(gold, str):
            if gold not in choices:
                raise ValueError('official string gold is not an exact choice')
            return choices.index(gold)
        if type(gold) is not int or not 0 <= gold < len(choices):
            raise ValueError('official scalar gold is not an integer choice index')
        return gold

    proxy = SimpleNamespace(eval_docs=task.eval_docs, multiple_input=False,
                            doc_to_choice=task.doc_to_choice, doc_to_target=index)
    return official.audit_samples(proxy, rows, expected)


@contextmanager
def model_runtime(name):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    from scripts.interactive_research_infer import state_fingerprint
    proof = metadata(name)
    model = payload = runtime = lm = before = None
    try:
        with (ROOT / proof['checkpoint']).open('rb') as stream:
            payload = torch.load(stream, map_location='cpu', weights_only=True)
        if payload.get('tokenizer_sha256') != TOKENIZER_SHA:
            raise ValueError('actual saved tokenizer lineage differs')
        cfg = TMTConfig(**payload['cfg'])
        if cfg.n_layers != 14 or cfg.dim != 768 or cfg.vocab_size != 32768 or cfg.max_seq_len != 1024 or cfg.tie_mlp or cfg.mtp_aux:
            raise ValueError('legacy dense14/chat32/1024/noMTP checkpoint required')
        with torch.device('cpu'):
            model = TiedMLPTransformer(cfg)
        model.load_state_dict(_strip(payload['model']), strict=True)
        payload = None
        model.eval()
        model.set_anneal(1.)
        before = state_fingerprint(model)
        if any(p.dtype != torch.float32 for p in model.parameters()):
            raise ValueError('full FP32 model required')
        if not torch.cuda.is_available() or torch.cuda.mem_get_info()[0] < 6 * 1024**3:
            raise RuntimeError('CUDA with at least6GiB free required; no CPU fallback')
        model = model.cuda()
        with torch.no_grad():
            model.freeze_quant()
        if state_fingerprint(model) != before:
            raise ValueError('CPU/GPU/freeze core fingerprint differs')
        tokenizer = Tokenizer.from_file(str(TOKENIZER))
        proof.update(initial_core_sha256=before, cfg=payload_cfg(cfg),
                     inference_route='ORIGINAL_LEGACY_TLINEAR_ANNEAL1_FROZEN_TERNARY_FP32_MATH',
                     parameters=sum(p.numel() for p in model.parameters()),
                     visits=list(model.visit_schedule()))
        runtime = dict(model=model, cfg=cfg, tokenizer=tokenizer, torch=torch, precision='FP32_MATH',
                       checkpoint=proof['checkpoint'], checkpoint_sha256=proof['checkpoint_sha256'],
                       tokenizer_sha256=TOKENIZER_SHA)
        lm = adapter.create_adapter(runtime, runtime_root=Path(sysconfig.get_paths()['purelib']), batch_size=8)
        yield lm, proof
    finally:
        try:
            if model is not None and before is not None:
                after = state_fingerprint(model)
                proof.update(final_core_sha256=after, checkpoint_unchanged=metadata(name) ==
                             {k: proof[k] for k in ('name', 'checkpoint', 'checkpoint_sha256', 'tokenizer_sha256', 'bytes')})
                if after != before or not proof['checkpoint_unchanged']:
                    raise ValueError('read-only model/checkpoint changed')
        finally:
            if lm is not None:
                lm.close()
            if runtime is not None:
                runtime.clear()
            if model is not None:
                model.clear_quant()
            lm = model = payload = runtime = None
            gc.collect()
            torch.cuda.empty_cache()


def payload_cfg(cfg):
    from dataclasses import asdict
    return asdict(cfg)


def evaluate(name, source_sha, cap):
    signature = identity()
    if signature['sha256'] != source_sha:
        raise ValueError('explicit source pin differs')
    target = OUTPUT / name
    if target.exists():
        raise FileExistsError('prior complete/partial evidence preserved')
    target.mkdir(parents=True)
    report = dict(schema='P106B_ORPO_OFFICIAL_V1', tag=TAG, model=name, status='STARTED',
                  source_identity=signature, policy=official.policy(), training=False,
                  optimizer_updates=0, checkpoint_writes=0, framework_commit=adapter.COMMIT,
                  max_wall_sec=cap, started_at=datetime.now(timezone.utc).isoformat(),
                  metrics_scope='COMPLETED_SMALL_POSTTRAINING_EXCEPTION_NOT300M_ORPO_ADOPTION',
                  independent_audits={}, official_results={}, sample_manifests={}, actual_counts={})
    began = time.monotonic()
    try:
        for key, value in official.OFFLINE.items():
            os.environ[key] = value
        os.environ['HF_EVALUATE_OFFLINE'] = '1'
        from scripts.p106b_gate_runtime import wall_limit
        with wall_limit(cap):
            tasks, specs, provenance = load_tasks()
            report.update(task_specs=specs, framework_provenance=provenance)
            import torch
            from torch.nn.attention import sdpa_kernel, SDPBackend
            from lm_eval.evaluator import simple_evaluate
            from lm_eval.tasks import TaskManager
            from scripts.diag_p106b_native_format_official import canary
            torch.set_num_threads(4)
            torch.manual_seed(1337)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            with sdpa_kernel(SDPBackend.MATH), torch.no_grad(), model_runtime(name) as (lm, proof):
                report['model_proof'] = proof
                torch.cuda.reset_peak_memory_stats()
                report['canary'] = canary(lm, torch)
                manager = TaskManager()
                length_writer = ShardWriter(target, 'token_lengths')
                with official.length_observer(lm, length_writer) as lengths:
                    # First32 cost is a resource gate, not a partial quality claim.
                    costs = {}
                    for taskname, task in tasks.items():
                        tick = time.monotonic()
                        result = simple_evaluate(model=lm, tasks=[task], num_fewshot=0,
                            task_manager=manager, batch_size=8, device='cuda', use_cache=None,
                            cache_requests=False, limit=32, bootstrap_iters=0, log_samples=True,
                            apply_chat_template=False, fewshot_as_multiturn=False, random_seed=1337,
                            numpy_random_seed=1337, torch_random_seed=1337, fewshot_random_seed=1337)
                        audit_task(task, result['samples'][taskname], 32)
                        torch.cuda.synchronize()
                        costs[taskname] = time.monotonic() - tick
                    forecast = sum(costs[k] * len(tasks[k].eval_docs) / 32 for k in tasks) * 1.3 + 60
                    report.update(cost_seconds=costs, forecast_seconds=forecast)
                    if forecast > cap - (time.monotonic() - began):
                        raise TimeoutError('full eleven-task forecast exceeds remaining cap')
                    print(json.dumps(dict(event='COST_GATE_COMPLETE', model=name, forecast_seconds=forecast)), flush=True)
                    for taskname, task in tasks.items():
                        tick = time.monotonic()
                        result = simple_evaluate(model=lm, tasks=[task], num_fewshot=0,
                            task_manager=manager, batch_size=8, device='cuda', use_cache=None,
                            cache_requests=False, limit=None,
                            bootstrap_iters=0 if taskname.startswith('kobest_') else 100000,
                            log_samples=True, apply_chat_template=False, fewshot_as_multiturn=False,
                            random_seed=1337, numpy_random_seed=1337, torch_random_seed=1337,
                            fewshot_random_seed=1337)
                        rows = result.pop('samples')[taskname]
                        audit = audit_task(task, rows, len(task.eval_docs))
                        for metric in ('acc', 'acc_norm'):
                            point = result['results'][taskname].get(metric + ',none')
                            count = audit['correct_norm' if metric == 'acc_norm' else 'correct']
                            if point is not None and not math.isclose(point, count / len(rows), abs_tol=1e-12):
                                raise ValueError('independent official metric recount differs')
                        if taskname.startswith('kobest_'):
                            for metric, aggregate in task.aggregation().items():
                                if metric == 'f1':
                                    independent = aggregate([row[metric] for row in rows])
                                    if not math.isclose(independent, result['results'][taskname]['f1,none'], abs_tol=1e-12):
                                        raise ValueError('official macro F1 recount differs')
                        writer = ShardWriter(target, taskname + '_samples')
                        for row in rows:
                            writer.append(official.plain(row))
                        manifest = writer.close(lineage=dict(model=name, task=taskname,
                            framework_commit=adapter.COMMIT, tag=TAG))
                        verify(target, manifest)
                        report['sample_manifests'][taskname] = manifest
                        report['independent_audits'][taskname] = audit
                        report['official_results'][taskname] = official.plain(result)
                        report['actual_counts'][taskname] = len(rows)
                        print(json.dumps(dict(event='OFFICIAL_TASK_CLOSED', model=name, task=taskname,
                            rows=len(rows), seconds=time.monotonic() - tick)), flush=True)
                    report['token_lengths_summary_with_cost'] = lengths
                report['lengths_manifest_with_cost'] = length_writer.close(
                    lineage=dict(model=name, tag=TAG, includes_cost32=True))
                verify(target, report['lengths_manifest_with_cost'])
                report['peak_allocated_mib'] = torch.cuda.max_memory_allocated() / 1024**2
                report['peak_reserved_mib'] = torch.cuda.max_memory_reserved() / 1024**2
            report.update(status='OFFICIAL_ELEVEN_TASKS_COMPLETE', returncode=0)
    except BaseException as error:
        report.update(status='OFFICIAL_EVALUATION_ERROR', returncode=9,
                      error_type=type(error).__name__, error=str(error)[:1600])
        raise
    finally:
        report.update(wall_seconds=time.monotonic() - began,
                      ended_at=datetime.now(timezone.utc).isoformat(),
                      sources_unchanged=identity() == signature)
        write(target / 'report.json', report)
    return dict(status=report['status'], model=name, actual_counts=report['actual_counts'],
                seconds=report['wall_seconds'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only', action='store_true')
    group.add_argument('--execute', action='store_true')
    parser.add_argument('--model', choices=MODELS)
    parser.add_argument('--source-sha256')
    parser.add_argument('--max-wall-sec', type=int, default=1800)
    args = parser.parse_args()
    if args.check_only:
        value = dict(status='SOURCE_AND_ASSETS_ONLY_NO_MODEL', source_identity=identity(),
                     models={name: metadata(name) for name in MODELS}, policy=official.policy())
    else:
        if args.model is None or not 300 <= args.max_wall_sec <= 3600:
            parser.error('explicit model and300~3600second cap required')
        value = evaluate(args.model, args.source_sha256, args.max_wall_sec)
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
