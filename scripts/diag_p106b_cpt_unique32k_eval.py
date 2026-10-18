#!/usr/bin/env python3
"""같은 동결 원형과 두 고유32k 대표를 새 예산 범위에서만 평가한다.

학습·정답·생성 조건은 원본과 같고 별도 경로의 원답과 영수증만 쓴다.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import ast
import hashlib
import copy
from datetime import datetime, timezone
import gc
import json
import time
from scripts import diag_p106b_cpt_unique32k as training
from scripts import diag_p106b_night_diversity_scope_eval_v2 as original_eval
from scripts import diag_p106b_night_eval_recovery as evaluation
from scripts.p106b_shards import ShardWriter

qa, previous = training.qa, training.previous
c, metrics, retention = qa, evaluation.metrics, evaluation.retention
FROZEN = training.CORPUS.parent / 'evaluation'
EVIDENCE = training.EVIDENCE / 'evaluate'
LOCAL = ROOT / 'test_result/evidence/local' / training.TAG / 'evaluate'
ENDPOINTS = ('cpt_unique32k', 'cpt_unique32k_best')
CODE = ('scripts/diag_p106b_cpt_unique32k_eval.py',
        'scripts/test_p106b_cpt_unique32k_eval.py',
        *training.CODE, *original_eval.CODE, *evaluation.CODE)


def evaluation_core_equivalence():
    """Exact scientific functions, with explicit deadline-only helper routing."""
    new = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    class NormalizeAuthority(ast.NodeTransformer):
        def visit_Call(self, node):
            node = self.generic_visit(node)
            if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in ('previous', 'train') and node.func.attr == 'deadline'
                    and not node.args and not node.keywords):
                return ast.Call(func=ast.Attribute(value=ast.Name(id='training', ctx=ast.Load()),
                    attr='authority', ctx=ast.Load()), args=[], keywords=[])
            return node
        def visit_Attribute(self, node):
            node = self.generic_visit(node)
            exact = ast.unparse(node)
            replacements = {'evaluation.lane_events': 'lane_events',
                'evaluation.old.native256': 'native256', 'old.emit_function': 'emit_function'}
            if exact in replacements:
                return ast.Name(id=replacements[exact], ctx=ast.Load())
            return node
        def visit_Expr(self, node):
            node = self.generic_visit(node)
            if (isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == 'idle_before_gpu' and not node.value.args and not node.value.keywords):
                guard = ast.parse('max_wall_sec = evaluation_admission(max_wall_sec)').body[0]
                return [copy.deepcopy(guard), node, guard]
            return node
    proof = {}
    for name, owner in (('evaluate', 'scripts/diag_p106b_night_diversity_scope_eval_v2.py'),
                        ('emit_function', 'scripts/diag_p106b_night_eval.py'),
                        ('native256', 'scripts/diag_p106b_night_eval.py'),
                        ('public_events', 'scripts/diag_p106b_night_eval_recovery.py'),
                        ('lane_events', 'scripts/diag_p106b_night_eval_recovery.py')):
        old = ast.parse((ROOT / owner).read_text(encoding='utf-8'))
        left = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == name)
        right = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == name)
        normalized = ast.dump(NormalizeAuthority().visit(left), include_attributes=False)
        if normalized != ast.dump(right, include_attributes=False):
            raise ValueError('scientific evaluation differs beyond exact authority routing: ' + name)
        proof[name] = dict(source=owner, normalized_ast_sha256=hashlib.sha256(normalized.encode()).hexdigest().upper())
    return dict(ast_equal_after_authority_substitution=True, functions=proof,
        allowed_changes=['previous.deadline()/train.deadline() -> training.authority()',
            'evaluation.lane_events/old.emit_function/evaluation.old.native256 -> exact local authority-only clones',
            'current wall/reserve admission immediately before and after GPU-idle guard'],
        immutable_module_aliases=['c=training.qa', 'metrics=evaluation.metrics', 'retention=evaluation.retention'])


def info():
    result = original_eval.info()
    result.update(schema='P106B_CPT_UNIQUE32K_EVAL_V1', tag=training.TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        endpoints=list(ENDPOINTS),
        training_cpu_sha256=qa.data.digest(training.CORPUS / 'report.json'),
        recovery_input_sha256=qa.data.digest(evaluation.FROZEN / 'report.json'),
        original_diversity_input_sha256=qa.data.digest(original_eval.FROZEN / 'report.json'),
        initializer=training.info()['initializer'],
        initializer_sha256=training.info()['initializer_sha256'],
        authority_end_utc=training.AUTHORITY_END.isoformat(),
        evaluation_core_equivalence=evaluation_core_equivalence())
    return result


def namespace():
    for target in (FROZEN, EVIDENCE, LOCAL):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('linked unique32k evaluation namespace')
            if parent == ROOT: break


def prepare():
    import torch
    namespace(); _, inputs, cases = evaluation.read_inputs()
    cpu = training.required(training.CORPUS / 'report.json')
    if cpu['status'] != 'DIVERSITY_CPU_FROZEN' or cpu['code_sha256'] != training.info()['code_sha256']:
        raise ValueError('same-code real unique32k training CPU required')
    old_inputs, old_cases = original_eval.read_inputs()
    if inputs != old_inputs or cases != old_cases:
        raise ValueError('same exact full evaluation case sets required for the fourth cell')
    if FROZEN.exists() or EVIDENCE.exists(): raise FileExistsError('old evaluation source preserved')
    if torch.cuda.is_initialized(): raise ValueError('CPU evaluation binding initialized CUDA')
    FROZEN.mkdir(parents=True, exist_ok=False)
    result = dict(info(), status='DIVERSITY_EVAL_INPUTS_FROZEN', original_counts=inputs['counts'],
        actual_case_sets_sha256={lane: qa.data.sha(rows) for lane, rows in cases.items()},
        cuda_initialized=False, model_loaded=False, optimizer_updates=0)
    qa.write(FROZEN / 'report.json', result); qa.write(EVIDENCE / 'inputs.json', result)
    print('[DIVERSITY_EVAL_CPU] ' + json.dumps(dict(status=result['status'], counts=inputs['counts'])), flush=True)
    return 0


def read_inputs():
    namespace(); frozen = training.required(FROZEN / 'report.json'); _, inputs, cases = evaluation.read_inputs()
    if (frozen['status'] != 'DIVERSITY_EVAL_INPUTS_FROZEN' or frozen['code_sha256'] != info()['code_sha256']
            or frozen['recovery_input_sha256'] != info()['recovery_input_sha256']
            or frozen['original_diversity_input_sha256'] != info()['original_diversity_input_sha256']
            or frozen['training_cpu_sha256'] != info()['training_cpu_sha256']
            or qa.required(EVIDENCE / 'inputs.json') != frozen
            or frozen['actual_case_sets_sha256'] != {lane: qa.data.sha(rows) for lane, rows in cases.items()}):
        raise ValueError('complete same-code/input bound evaluation required')
    return inputs, cases


def checkpoint_spec(endpoint):
    if endpoint not in ENDPOINTS: raise ValueError('registered unique32k endpoint required')
    best = endpoint.endswith('_best')
    proof = training.required(training.CORPUS / 'report.json')
    if not training.completed(proof): raise training.PrerequisitePending('full same-source640 unique32k training not yet complete')
    report = qa.required(training.EVIDENCE / 'unique32k/report.json')
    history = report['history']; quarter = report['best_dev_quarter']
    if (len(history) != 4 or type(quarter) is not int or not 1 <= quarter <= 4
            or quarter != 1 + min(range(4), key=lambda i: history[i]['dev']['ce'])
            or report['best_dev_ce'] != history[quarter - 1]['dev']['ce']):
        raise ValueError('exact DEV-only quarter selection required')
    path = report['best_dev_checkpoint'] if best else report['checkpoint']
    identity = report['best_dev_checkpoint_sha256'] if best else report['checkpoint_sha256']
    core = report['best_dev_core_sha256'] if best else report['final_core_sha256']
    if path != str(training.checkpoint(best and quarter != 4).relative_to(ROOT)):
        raise ValueError('exact final/DEV unique32k checkpoint path required')
    cp = ROOT / path
    if qa.data.digest(cp) != identity: raise ValueError('saved selected unique32k body changed')
    return cp, identity, core


def receipt_path(endpoint, lane):
    return EVIDENCE / endpoint / (lane + '_receipt.json')


def endpoint_contract(report, endpoint, inputs):
    if (report.get('status') != 'ACTUAL_EVALUATION_COMPLETE' or report.get('endpoint') != endpoint
            or report.get('updates') != 0 or report.get('checkpoints_written') != 0
            or report.get('body_unchanged') is not True
            or report.get('directory') != str((LOCAL / endpoint).relative_to(ROOT))
            or set(report.get('outputs', {})) != evaluation.OUTPUTS
            or set(report.get('receipt_sha256', {})) != evaluation.OUTPUTS):
        raise ValueError('complete two-endpoint endpoint/lane contract required')
    for lane, spec in report['outputs'].items():
        if lane in ('native32', 'native256'): evaluation.native_contract(lane, spec, inputs)
        elif (not isinstance(spec.get('counts'), dict) or not spec['counts']
                or not spec.get('manifest', {}).get('shards') or spec['manifest'].get('rows', 0) <= 0):
            raise ValueError('nonempty complete actual-answer lane required')


def read_receipt(endpoint, lane, cases, inputs):
    r = qa.required(receipt_path(endpoint, lane)); cp, identity, core = checkpoint_spec(endpoint)
    if (r.get('status') != 'LANE_COMPLETE' or r.get('endpoint') != endpoint or r.get('lane') != lane
            or r.get('code_sha256') != info()['code_sha256']
            or r.get('checkpoint_sha256') != identity or r.get('initial_core_sha256') != core
            or r.get('body_proof') != evaluation.body_proof(dict(kind='NEW_MODEL_INFERENCE'), core, core)
            or r.get('input_report_sha256') != qa.data.digest(FROZEN / 'report.json')):
        raise ValueError('complete same-code/strict-body/source lane proof required')
    output = r['output']
    if lane in ('native32', 'native256'): evaluation.native_contract(lane, output, inputs)
    else:
        events = list(evaluation.old.stream(LOCAL / endpoint, output['manifest']))
        if evaluation.recount(lane, events, cases) != output['counts']:
            raise ValueError('unique32k endpoint raw/original/gold/history recount differs')
    return r


def emit_function(base, cfg, tok, max_new=128):
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    wrapped = PrecisionForward(base, 'fp32_math')
    def emit(messages):
        training.authority()
        prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
        ids = tok.encode(prompt).ids
        if len(ids) + max_new > cfg.max_seq_len:
            return '', dict(finish_reason='CONTEXT_BUDGET_EXHAUSTED', prompt_tokens=len(ids), requested_max_new=max_new,
                            actual_prompt_sha256=c.data.sha(prompt), raw_answer_sha256=c.data.sha(''))
        output, meta = sample(wrapped, cfg, tok, prompt, max_new=max_new,
            temperature=0., top_k=1, device='cuda', use_cache=True, logits_last_only=True,
            return_metadata=True, stop_token_sequences=[tok.encode('<|im_end|>').ids])
        prefix = tok.decode(ids)
        if not output.startswith(prefix): raise ValueError('decoded complete prompt extraction differs')
        answer = output[len(prefix):].split('<|im_end|>', 1)[0]
        return answer, dict(meta, prompt_tokens=len(ids), requested_max_new=max_new,
                            actual_prompt_sha256=c.data.sha(prompt), raw_answer_sha256=c.data.sha(answer))
    return emit


def native256(base, inputs, tok):
    import numpy as np
    import torch
    from tinylm.train import mtp_sft as core
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    wrapped = PrecisionForward(base, 'fp32_math')
    values = np.memmap(c.NATIVE / 'val.bin', dtype=np.uint16, mode='r')
    total = 0.; count = 0
    with torch.no_grad():
        for start in inputs['native256_val_offsets']:
            training.authority()
            v = values[start:start + 1025].astype('int64').tolist()
            x = torch.tensor([v[:-1]], device='cuda'); y = torch.tensor([v[1:]], device='cuda')
            hidden = wrapped(x, return_hidden=True)
            sums, n = core.components(base, hidden, y, torch.ones_like(y), horizons=(), checkpoint_heads=False)
            total += float(sums[1]); count += n[1]
    return dict(ce=total / count, targets=count, windows=256, precision='FP32_MATH',
        val_sha256=inputs['native_val_sha256'], offsets_sha256=c.data.sha(inputs['native256_val_offsets']),
        scope='additional fixed val windows, not whole validation or new unseen text')


def public_events(model, cfg, tok, device, cases):
    import torch
    import torch.nn.functional as F
    from scripts import diag_p106b_authorized_benchmark as public
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.infer.generate import sample
    wrapped = PrecisionForward(model, 'fp32_math')
    for task in (*public.TASKS, 'korquad_free', 'gsm8k_free'):
        rows = [r for r in cases if r['task'] == task]
        if task in public.TASKS:
            for start in range(0, len(rows), 16):
                training.authority()
                res = public.suite.run_mc(task, [r['item'] for r in rows[start:start + 16]],
                    wrapped, tok, device, 1024, torch, F, False)
                for e in res['rows']: yield dict(e, task=task, kind='mc', skipped=False)
                for e in res['skip_rows']: yield dict(e, task=task, kind='mc', skipped=True)
        else:
            for row in rows:
                training.authority()
                if row['prompt_tokens'] + 128 > 1024:
                    yield dict(task=task, id=row['id'], kind='gen', skipped=True, reason='complete_prompt_budget')
                    continue
                output, generation = sample(wrapped, cfg, tok, row['prompt'], max_new=128,
                    temperature=0., top_k=1, device='cuda', use_cache=True, logits_last_only=True,
                    return_metadata=True, stop_token_sequences=[tok.encode('<|im_end|>').ids])
                prefix = tok.decode(tok.encode(row['prompt']).ids)
                if not output.startswith(prefix): raise ValueError('public prompt extraction differs')
                raw = output[len(prefix):].split('<|im_end|>', 1)[0]; answer = raw.strip()
                scores = public.answer_scores(answer, row['golds'])
                if task == 'gsm8k_free':
                    scores['numeric_exact'] = int(public.numerical(answer) is not None and public.numerical(answer) == public.numerical(row['golds'][0]))
                yield dict(task=task, id=row['id'], kind='gen', skipped=False, answer=answer,
                    raw_answer=raw, prompt=row['prompt'], golds=row['golds'], generation=generation, scores=scores)
        print('[NIGHT_RECOVERY_PUBLIC] ' + json.dumps(dict(task=task)), flush=True)


def lane_events(lane, model, cfg, tok, device, cases):
    emit = emit_function(model, cfg, tok)
    if lane == 'natural':
        for index, pair in enumerate(cases[lane]):
            for view in (0, 1, 2):
                messages = pair['views'][str(view)]['messages'][:1]; answer, generation = emit(messages)
                yield dict(root=pair['root'], article_id=pair['article_id'], language=pair['language'], view=view,
                    source_sha256=pair['source_sha256'], question=pair['question'], context=pair['context'],
                    messages=messages, answer=answer, aliases=pair['aliases'], generation=generation,
                    scores=metrics.qa_scores(answer, pair['aliases'], pair['language']))
            if (index + 1) % 64 == 0: print('[NIGHT_RECOVERY_QA] ' + str(index + 1), flush=True)
    elif lane == 'cube':
        for row in cases[lane]:
            answer, generation = emit(row['messages']); yield dict(row, answer=answer, generation=generation)
    elif lane in ('role', 'recovery', 'code'):
        short = emit_function(model, cfg, tok, 64)
        for index, row in enumerate(cases[lane]):
            yield from retention.collect(row, short, lane=lane, row_index=index)
    elif lane == 'public': yield from public_events(model, cfg, tok, device, cases[lane])
    else: raise ValueError('raw-answer lane required')


def evaluation_admission(requested):
    if type(requested) is not int or not 60 <= requested <= 21600:
        raise ValueError('bounded actual evaluation wall required')
    seconds = min(requested, int(training.authority()) - 3600)
    if seconds < 60:
        raise training.PrerequisitePending('actual evaluation admission no longer fits documentation reserve')
    return seconds


def evaluate(endpoint, max_wall_sec):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    inputs, cases = read_inputs(); cp, identity, expected_core = checkpoint_spec(endpoint)
    target = EVIDENCE / (endpoint + '_report.json'); directory = LOCAL / endpoint
    if target.exists() or directory.exists(): raise FileExistsError('old complete/partial unique32k answers preserved')
    max_wall_sec = evaluation_admission(max_wall_sec)
    idle_before_gpu()
    max_wall_sec = evaluation_admission(max_wall_sec)
    directory.mkdir(parents=True, exist_ok=False); began = time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with wall_limit(max_wall_sec):
        model, cfg, device = load_model(arch='dense', ckpt_path=str(cp), device='cuda')
        initial = training.foundation.runtime.state_fingerprint(model)
        if initial != expected_core: raise ValueError('strict loaded unique32k body differs from selected checkpoint')
        tok = Tokenizer.from_file(str(qa.data.TOKENIZER)); torch.cuda.reset_peak_memory_stats(); outputs = {}
        with torch.no_grad():
            for lane in ('natural', 'cube', 'role', 'recovery', 'code', 'public', 'native32', 'native256'):
                training.authority()
                if lane in ('native32', 'native256'):
                    output = training.foundation.runtime.native_ce(model, qa.NATIVE) if lane == 'native32' else native256(model, inputs, tok)
                    model.eval(); model.freeze_quant(); evaluation.native_contract(lane, output, inputs)
                else:
                    writer = ShardWriter(directory, lane); values = []
                    for event in lane_events(lane, model, cfg, tok, device, cases):
                        writer.append(event); values.append(event)
                    output = dict(manifest=writer.close(lineage=info()), counts=evaluation.recount(lane, values, cases))
                final_core = training.foundation.runtime.state_fingerprint(model)
                proof = evaluation.body_proof(dict(kind='NEW_MODEL_INFERENCE'), initial, final_core)
                if qa.data.digest(cp) != identity: raise ValueError('read-only evaluation changed checkpoint file')
                receipt = dict(info(), status='LANE_COMPLETE', endpoint=endpoint, lane=lane,
                    checkpoint_sha256=identity, initial_core_sha256=initial, body_proof=proof,
                    input_report_sha256=qa.data.digest(FROZEN / 'report.json'), output=output)
                qa.write(receipt_path(endpoint, lane), receipt); outputs[lane] = output
                print('[DIVERSITY_EVAL_LANE] ' + json.dumps(dict(endpoint=endpoint, lane=lane)), flush=True)
        result = dict(info(), status='ACTUAL_EVALUATION_COMPLETE', endpoint=endpoint,
            checkpoint=str(cp.relative_to(ROOT)), checkpoint_sha256=identity, initial_core_sha256=initial,
            directory=str(directory.relative_to(ROOT)), body_unchanged=True,
            input_report_sha256=qa.data.digest(FROZEN / 'report.json'), outputs=outputs,
            receipt_sha256={lane: qa.data.digest(receipt_path(endpoint, lane)) for lane in evaluation.OUTPUTS},
            whole_seconds=time.perf_counter() - began, peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
        endpoint_contract(result, endpoint, inputs)
        for lane in evaluation.OUTPUTS: read_receipt(endpoint, lane, cases, inputs)
        qa.write(target, result)
        print('[DIVERSITY_EVAL_COMPLETE] ' + json.dumps(dict(endpoint=endpoint, whole_seconds=result['whole_seconds'])), flush=True)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def verified_endpoint(provider, endpoint, inputs, cases):
    path = provider.EVIDENCE / (endpoint + '_report.json')
    report = training.required(path)
    provider.endpoint_contract(report, endpoint, inputs)
    selected = provider.checkpoint_spec(endpoint)
    if provider is evaluation:
        if len(selected) != 2:
            raise ValueError('historical recovery uses its exact two-field checkpoint API')
        cp, identity = selected
        core = report.get('initial_core_sha256')
        if not isinstance(core, str) or len(core) != 64:
            raise ValueError('complete historical actual inference body fingerprint required')
    else:
        cp, identity, core = selected
    if (report.get('code_sha256') != provider.info()['code_sha256']
            or report.get('input_report_sha256') != qa.data.digest(provider.FROZEN / 'report.json')
            or report.get('checkpoint') != str(cp.relative_to(ROOT))
            or report.get('checkpoint_sha256') != identity
            or report.get('initial_core_sha256') != core):
        raise ValueError('fourth-cell comparison endpoint source/checkpoint/body mismatch')
    for lane in evaluation.OUTPUTS:
        if provider is evaluation:
            receipt = provider.read_receipt(endpoint, lane, cases)
        else:
            receipt = provider.read_receipt(endpoint, lane, cases, inputs)
        if (receipt['output'] != report['outputs'][lane]
                or qa.data.digest(provider.receipt_path(endpoint, lane)) != report['receipt_sha256'][lane]):
            raise ValueError('complete same-source lane/raw/body receipt required')
        if provider is evaluation and receipt.get('origin', {}).get('kind') == 'NEW_MODEL_INFERENCE':
            body = receipt.get('body_proof', {})
            if body.get('initial_core_sha256') != core or body.get('final_core_sha256') != core:
                raise ValueError('historical lane body differs from its fixed endpoint body')
    rows = list(evaluation.old.stream(provider.LOCAL / endpoint, report['outputs']['natural']['manifest']))
    return dict(report_sha256=qa.data.digest(path), checkpoint_sha256=identity,
        initial_core_sha256=core, outputs=report['outputs']), rows


def readback():
    inputs, cases = read_inputs()
    original_inputs, original_cases = original_eval.read_inputs()
    if inputs != original_inputs or cases != original_cases:
        raise ValueError('old diversity full evaluation cases changed')
    result_path = EVIDENCE / 'paired_readback.json'
    if result_path.exists():
        raise FileExistsError('old complete/partial fourth-cell readback preserved')
    summaries, natural = {}, {}
    providers = [(evaluation, e) for e in ('base_qa', 'base_qa_best', 'cpt_qa', 'cpt_qa_best')]
    providers += [(original_eval, e) for e in ('unique32k', 'unique32k_best')]
    providers += [(sys.modules[__name__], e) for e in ENDPOINTS]
    for provider, endpoint in providers:
        summaries[endpoint], natural[endpoint] = verified_endpoint(provider, endpoint, inputs, cases)
    pairs = [('base_qa', 'unique32k'), ('cpt_qa', 'cpt_unique32k'),
             ('base_qa', 'cpt_qa'), ('unique32k', 'cpt_unique32k'),
             ('base_qa_best', 'unique32k_best'), ('cpt_qa_best', 'cpt_unique32k_best'),
             ('base_qa_best', 'cpt_qa_best'), ('unique32k_best', 'cpt_unique32k_best'),
             ('cpt_unique32k', 'cpt_unique32k_best')]
    comparisons = {a + '__' + b: evaluation.method.paired_natural(natural[a], natural[b]) for a, b in pairs}
    result = dict(info(), status='RAW_RECOUNTED', errors=0,
        endpoints=summaries, paired=comparisons,
        primary_endpoints=['base_qa', 'cpt_qa', 'unique32k', 'cpt_unique32k'],
        interpretation='exploratory recipe interaction; source/exposure/repetition differ between 8k and32k',
        best_comparison_is_dev_selection_package=True, learning_seed_variance_measured=False,
        automatic_adoption=False, student_general_intelligence='NOT_ESTABLISHED')
    qa.write(result_path, result)
    print('[CPT_UNIQUE32K_READBACK] ' + json.dumps(comparisons, ensure_ascii=False), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('freeze', 'evaluate', 'readback'), required=True)
    parser.add_argument('--endpoint', choices=ENDPOINTS)
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if not 60 <= args.max_wall_sec <= 21600: parser.error('bounded60..21600 wall seconds required')
    if args.check_only:
        print('[CPT_UNIQUE32K_EVAL_CHECK] ' + json.dumps(dict(mode=args.mode, endpoints=ENDPOINTS,
            model_loaded=False, optimizer_updates=0, checkpoints_written=0,
            core_equivalence=evaluation_core_equivalence()))); return 0
    if args.mode == 'evaluate' and args.endpoint is None: parser.error('explicit endpoint required')
    try:
        training.authority()
        if args.mode == 'freeze': return prepare()
        if args.mode == 'readback': return readback()
        remaining = int((training.AUTHORITY_END - datetime.now(timezone.utc)).total_seconds()) - 3600
        if remaining < 60: raise training.PrerequisitePending('explicit Oct20 authority and final documentation reserve')
        return evaluate(args.endpoint, min(args.max_wall_sec, remaining))
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        status, code = training.failure_status(exc)
        if code == 9:
            import traceback
            traceback.print_exc()
        print('[CPT_UNIQUE32K_EVAL_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__': raise SystemExit(main())
