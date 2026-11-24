"""Frozen TRAIN128-selected Qwen0.6 PTS/HPA versus native causal hidden states."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback
import unittest

import tinylm
from scripts import diag_p106b_dvlm_pts as admission
from scripts import p106b_dvlm_native as native

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'test_result/evidence/p106b_dvlm_native_v1_20261117'
PROFILE = BASE / 'profile.json'
CPU_CLOSURE = ROOT / 'handoff/audit/research_20261117_01a1e647/CPU1_CONTROLLER_CLOSED_v2.json'
ATOL, RTOL = 1e-5, 1e-4
SOURCES = admission.SOURCES + (
    'scripts/p106b_dvlm_native.py', 'scripts/test_p106b_dvlm_native.py',
    'scripts/diag_p106b_dvlm_native.py', 'scripts/diag_p106b_external_core6.py',
    'scripts/diag_p106b_official_core6.py', 'scripts/prepare_p106b_official_eval.py',
    'scripts/interactive_research_infer.py', 'tinylm/__init__.py', 'tinylm/paths.py')
SCHEMA = 'P106B_DVLM_NATIVE_HPA_V1'


class NumericalNegative(ValueError):
    pass


@contextmanager
def wall_limit(seconds):
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*_):
        raise TimeoutError('owned native HPA wall cap reached; partial evidence retained')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def guard(start=None):
    admission.guard()
    if (BASE / 'STOP').exists():
        raise TimeoutError('owned native HPA STOP present')
    if start is not None and time.monotonic()-start >= 1080:
        raise TimeoutError('native HPA compute cap1080sec; cleanup reserve120sec')


def runtime_identity():
    import torch
    import transformers
    import transformers.masking_utils as masking
    import transformers.modeling_rope_utils as rope
    import transformers.models.qwen3.modeling_qwen3 as qwen
    import numpy
    return dict(python=sys.version, executable=sys.executable, torch=torch.__version__,
        torch_cuda=torch.version.cuda, transformers=transformers.__version__, numpy=numpy.__version__,
        files={str(Path(module.__file__).resolve()): admission.digest(module.__file__)
               for module in (masking, rope, qwen)})


def prerequisite_cases():
    p = admission.verify()
    path = admission.BASE / 'cpu/report.json'
    report = admission.read(path)
    if (report['status'] != 'PTS_CPU_ADMISSION_COMPLETE_NOT_MODEL_OR_QUALITY'
            or report['returncode'] != 0 or report['profile_sha256'] != admission.digest(admission.PROFILE)
            or report['original_rows'] != 128 or report['original_x_tokens'] != 32216
            or report['original_ce_targets'] != 772 or report['corpus_admitted'] is not False):
        raise ValueError('closed exact original TRAIN128 admission required')
    manifest = report['manifests']['layouts']
    if manifest is None:
        raise ValueError('no admitted complete PTS layout; no native model load')
    admission.verify_shards(admission.BASE / 'cpu', manifest)
    selected = report['selected_native_cases']
    if not selected or len(selected) > p['native_expected_max_cases']:
        raise ValueError('preselected complete native cases required')
    cases = {}
    for shard in manifest['shards']:
        for line in (admission.BASE / 'cpu' / shard['path']).read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if any(case['row_id'] == row['row_id'] for case in selected):
                cases[row['row_id']] = row
    if set(cases) != {row['row_id'] for row in selected}:
        raise ValueError('complete original-order native case membership differs')
    return p, report, [cases[item['row_id']] for item in selected]


def cpu_has_closed():
    record = admission.read(CPU_CLOSURE)
    if record.get('status') != 'PROCESS_CLOSED' or type(record.get('actual_exit_code')) is not int:
        raise ValueError('CPU1 timing controller must be terminal before native work')
    return dict(path=str(CPU_CLOSURE.relative_to(ROOT)), sha256=admission.digest(CPU_CLOSURE),
        actual_exit_code=record['actual_exit_code'], policy='TIMING_TERMINAL_GATE;NOT_A_NUMERICAL_PASS_REQUIREMENT')


def prepare():
    guard()
    if BASE.exists():
        raise FileExistsError('preserve native HPA namespace')
    closed = cpu_has_closed()
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    cache_policy = configure_hf_cache()
    cpu_profile, admitted, cases = prerequisite_cases()
    if cpu_profile['CPU_contracts'] != 21:
        raise ValueError('exact prior21 admission contracts required without redundant rerun')
    runtime = runtime_identity()
    suite = unittest.defaultTestLoader.loadTestsFromName('scripts.test_p106b_dvlm_native')
    checked = unittest.TextTestRunner(verbosity=2).run(suite)
    if not checked.wasSuccessful() or checked.testsRun != 6:
        raise RuntimeError('all6 new native contracts required in addition to frozen prior21')
    import torch
    if torch.cuda.is_initialized():
        raise ValueError('CPU native contracts unexpectedly initialized CUDA')
    from scripts.diag_p106b_external_core6 import asset_identity
    assets = asset_identity('qwen06')
    if (admission.digest(ROOT / admission.TEACHER_TOKENIZER)
            != assets['files']['tokenizer.json']['sha256']):
        raise ValueError('admission/native teacher tokenizer differs')
    guard()
    if datetime.now(timezone.utc).timestamp()+1200 >= admission.CUTOFF.timestamp():
        raise TimeoutError('complete native1200sec does not fit new-compute cutoff')
    BASE.mkdir()
    with (BASE / 'initial_plan.md').open('xb') as stream:
        stream.write(admission.PLAN.read_bytes())
    profile = dict(schema=SCHEMA, authority_directive=158, authority_end=admission.DEADLINE.isoformat(),
        cutoff=admission.CUTOFF.isoformat(), CPU1_closed=closed,
        sources={name:admission.digest(ROOT/name) for name in dict.fromkeys(SOURCES)},
        runtime=runtime, cache_policy=cache_policy, assets=assets,
        admission_profile_sha256=admission.digest(admission.PROFILE),
        admission_report_sha256=admission.digest(admission.BASE/'cpu/report.json'),
        initial_plan_sha256=admission.digest(BASE/'initial_plan.md'),
        selected_native_cases=admitted['selected_native_cases'], expected_cases=len(cases),
        original_train_rows=128, original_train_ce=772, selection_before_model_or_output=True,
        atol=ATOL, rtol=RTOL, dtype='FP32', attention='EAGER', KV_cache=False,
        max_compute_seconds=1080, max_phase_seconds=1200, max_output_bytes=180_000_000,
        minimum_free_vram_bytes=8*1024**3, cublas_workspace_config=':4096:8',
        max_case_packet_bytes=20_000_000, first_case_forecast_safety=1.5,
        forecast_policy='MEASURED_FIRST_COMPLETE_CASE_X_REMAINING_X1.5_PLUS60;FAIL_CLOSED_NO_CASE_SHRINK',
        numerical_policy='STOP_ON_FIRST_NEGATIVE;REMAINING_CASES_NOT_RUN;ORIGINAL_TOLERANCE_UNCHANGED',
        contracts=dict(inherited_frozen_admission=21,new_native=checked.testsRun,total=27),
        pretrained_model_loads=0, synthetic_CPU_model_constructions=1,
        CUDA_initializations=0, corpus_admitted=False, training=False, quality_claim=False)
    admission.write_new(PROFILE, profile)
    print('[DVLM_NATIVE_PREPARED]27 contracts;fixed cases;FP32/eager/strict original tolerance',flush=True)


def verify():
    guard()
    p = admission.read(PROFILE)
    if (p['schema'] != SCHEMA or p['authority_directive'] != 158 or p['authority_end'] != admission.DEADLINE.isoformat()
            or p['cutoff'] != admission.CUTOFF.isoformat() or p['atol'] != ATOL or p['rtol'] != RTOL
            or p['initial_plan_sha256'] != admission.digest(BASE/'initial_plan.md')
            or cpu_has_closed() != p['CPU1_closed']):
        raise ValueError('exact native authority/tolerance/plan/terminal CPU receipt differs')
    for name, expected in p['sources'].items():
        if admission.digest(ROOT/name) != expected:
            raise ValueError('frozen native source changed: '+name)
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    if configure_hf_cache() != p['cache_policy'] or runtime_identity() != p['runtime']:
        raise ValueError('frozen native runtime/cache policy differs')
    from scripts.diag_p106b_external_core6 import asset_identity
    if asset_identity('qwen06') != p['assets']:
        raise ValueError('frozen teacher asset identity differs')
    _, report, cases = prerequisite_cases()
    if (admission.digest(admission.PROFILE) != p['admission_profile_sha256']
            or admission.digest(admission.BASE/'cpu/report.json') != p['admission_report_sha256']
            or report['selected_native_cases'] != p['selected_native_cases'] or len(cases) != p['expected_cases']):
        raise ValueError('exact original preselected cases differ')
    return p, cases


def save_packet(path, packet):
    import numpy as np
    with path.open('xb') as stream:
        np.savez_compressed(stream, **{name:value.numpy() if hasattr(value,'numpy') else np.asarray(value)
                                    for name,value in packet.items()})
    if path.stat().st_size >= 20_000_000:
        raise OSError('owned case packet exceeds20MB; preserve it and HOLD')
    return dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=admission.digest(path))


def actual():
    guard()
    start = time.monotonic()
    out = BASE / 'actual'
    out.mkdir()
    model = torch = hook = None
    before = None
    head_calls = []
    report = dict(schema=SCHEMA, authority_directive=158, started_at=datetime.now(timezone.utc).isoformat(),
        status='NATIVE_HPA_INCOMPLETE', returncode=9, cases=[], expected_cases=None,
        corpus_admitted=False, training=False, optimizer_updates=0, checkpoint_writes=0, quality_claim=False,
        model_load_attempted=False, model_loaded=False, original_head_calls=None, closure_errors=[])
    try:
        with wall_limit(1080):
            p,cases = verify()
            report.update(profile_sha256=admission.digest(PROFILE), expected_cases=len(cases))
            if datetime.now(timezone.utc).timestamp()+1200 >= admission.CUTOFF.timestamp():
                raise TimeoutError('complete native phase no longer fits cutoff')
            from scripts.interactive_research_infer import require_idle_gpu, state_fingerprint
            report['GPU_idle_point'] = require_idle_gpu()
            if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != p['cublas_workspace_config']:
                raise ValueError('explicit deterministic CUBLAS workspace required before Torch import')
            import torch
            from transformers import AutoModelForCausalLM
            torch.set_num_threads(4)
            torch.set_num_interop_threads(1)
            torch.manual_seed(1337)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            torch.set_float32_matmul_precision('highest')
            torch.use_deterministic_algorithms(True)
            if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
                raise RuntimeError('exact one admitted CUDA GPU required')
            free_vram,total_vram=torch.cuda.mem_get_info()
            report['CUDA_free_point']=dict(free_bytes=free_vram,total_bytes=total_vram,
                required_free_bytes=p['minimum_free_vram_bytes'],scope='POINT_QUERY_ONLY_NOT_OOM_GUARANTEE')
            if free_vram < p['minimum_free_vram_bytes']:
                raise RuntimeError('native HPA free-VRAM admission failed before pretrained model load')
            report['model_load_attempted'] = True
            model,loading = AutoModelForCausalLM.from_pretrained(p['assets']['declared_directory'],
                local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32,
                attn_implementation='eager',use_cache=False,output_loading_info=True)
            report.update(model_loaded=True,loading_info=loading)
            if any(loading.get(name) for name in ('missing_keys','unexpected_keys','mismatched_keys','error_msgs')):
                raise ValueError('strict pretrained loading reported missing/extra/mismatched/error keys')
            if (model.config.model_type != 'qwen3' or model.config._attn_implementation != 'eager'
                    or model.config.use_cache or any(value.dtype != torch.float32 for value in model.parameters())):
                raise ValueError('strict Qwen3 FP32/eager/no-KV contract differs')
            model.eval()
            before = state_fingerprint(model)
            output_weight = model.get_output_embeddings().weight.detach().cpu().contiguous()
            output_sha = hashlib.sha256(output_weight.view(-1).view(torch.uint8).numpy().tobytes()).hexdigest().upper()
            tied_output = model.get_output_embeddings().weight.data_ptr() == model.get_input_embeddings().weight.data_ptr()
            report.update(initial_state_sha256=before, parameters=sum(value.numel() for value in model.parameters()),
                hidden_size=model.config.hidden_size,vocab_size=model.config.vocab_size,
                output_head_weight_sha256=output_sha,output_head_shape=list(output_weight.shape),
                output_head_dtype=str(output_weight.dtype),output_head_tied_to_input=tied_output,
                exact_head_source_tensor='model.embed_tokens.weight' if tied_output else 'lm_head.weight')
            del output_weight
            model.to('cuda')
            torch.cuda.reset_peak_memory_stats()
            hook = model.lm_head.register_forward_hook(lambda *_:head_calls.append(1))
            report['pre_case_seconds'] = time.monotonic()-start
            for index,row in enumerate(cases):
                guard(start)
                if sum(item['packet']['bytes'] for item in report['cases']) >= p['max_output_bytes']:
                    raise OSError('native owned packet byte cap reached')
                began = time.monotonic()
                layout = native.restore_layout(row['layout'])
                with torch.inference_mode():
                    check,packet = native.native_case(torch,model,layout,atol=p['atol'],rtol=p['rtol'],
                        guard=lambda:guard(start))
                torch.cuda.synchronize()
                saved = save_packet(out/f'case{index:03d}_hidden.npz',packet)
                receipt = dict(ordinal=index,row_id=row['row_id'],language=row['language'],
                    original_ce_targets=row['original_ce_targets'],physical_PTS_tokens=len(layout.input_ids),
                    alignment_groups=len(layout.groups),report=check,packet=saved,wall_seconds=time.monotonic()-began)
                report['cases'].append(receipt)
                admission.write_new(out/f'case{index:03d}_report.json',receipt)
                print('[DVLM_NATIVE_CASE]'+json.dumps(dict(ordinal=index,row_id=row['row_id'],passed=check['passed'],
                    groups=len(layout.groups),wall_seconds=receipt['wall_seconds'])),flush=True)
                del packet
                if head_calls:
                    raise ValueError('original LM head was called during hidden-only PTS oracle')
                if not check['passed']:
                    raise NumericalNegative('complete case violates original hidden tolerance or invariance')
                if index == 0 and len(cases) > 1:
                    forecast = receipt['wall_seconds']*(len(cases)-1)*p['first_case_forecast_safety']+60
                    report['first_case_forecast_remaining_seconds'] = forecast
                    if time.monotonic()-start+forecast >= p['max_compute_seconds']:
                        raise TimeoutError('measured complete remaining-case forecast exceeds fixed budget')
            report.update(status='NATIVE_HPA_HIDDEN_COMPLETE_NOT_TRAINING_OR_QUALITY',returncode=0)
    except BaseException as error:
        report.update(returncode=2 if isinstance(error,NumericalNegative) else 8 if isinstance(error,TimeoutError) else 9,
            status='NATIVE_HPA_NUMERICAL_NEGATIVE' if isinstance(error,NumericalNegative) else 'NATIVE_HPA_INCOMPLETE',
            error=dict(type=type(error).__name__,message=str(error)),traceback=traceback.format_exc())
    finally:
        if hook is not None:
            hook.remove()
        report['original_head_calls'] = len(head_calls)
        if model is not None and before is not None:
            try:
                from scripts.interactive_research_infer import state_fingerprint
                report['final_state_sha256'] = state_fingerprint(model)
                report['state_unchanged'] = report['final_state_sha256'] == before
                if not report['state_unchanged']:
                    raise ValueError('original teacher state changed')
            except BaseException as error:
                report['closure_errors'].append('state: '+str(error))
        if torch is not None and torch.cuda.is_initialized():
            report['torch_peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
            report['torch_peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        try:
            if model is not None:
                model.to('cpu')
        except BaseException as error:
            report['closure_errors'].append('model cleanup: '+str(error))
        model = None
        gc.collect()
        if torch is not None and torch.cuda.is_initialized():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            report['CUDA_exit_allocated_bytes'] = torch.cuda.memory_allocated()
            report['CUDA_exit_reserved_bytes'] = torch.cuda.memory_reserved()
            if report['CUDA_exit_allocated_bytes'] != 0 or report['CUDA_exit_reserved_bytes'] != 0:
                report['closure_errors'].append('CUDA resident memory remains')
        try:
            verify()
            report['sources_assets_inputs_unchanged'] = True
        except BaseException as error:
            report['closure_errors'].append('final source/assets/input verification: '+str(error))
        if report['closure_errors']:
            report.update(returncode=9,status='NATIVE_HPA_CLOSURE_ERROR')
        report.update(ended_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,
            model_released=True,remaining_cases_NOT_RUN=(report['expected_cases'] or 0)-len(report['cases']))
        admission.write_new(out/'report.json',report)
    print('[DVLM_NATIVE_CLOSED]'+json.dumps(dict(status=report['status'],returncode=report['returncode'],
        completed=len(report['cases']),remaining=report['remaining_cases_NOT_RUN'])),flush=True)
    return report['returncode']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','check','actual'))
    args=parser.parse_args()
    if args.action=='prepare':
        with wall_limit(600):prepare()
    elif args.action=='check':verify();print('[DVLM_NATIVE_CHECK]frozen native profile matched;no model load')
    else:return actual()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
