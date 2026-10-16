#!/usr/bin/env python3
"""동일한 고유32k 학습을 독립 예산과 새 비용8로 실행하는 별도 범위.

동결된 원본의 수집·학습·평가 조건은 변경하지 않는다.
실물 준비와 GPU 실행은 명시적인 execute에서만 수행한다.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import ast
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import tempfile
import time
from scripts import diag_p106b_night_diversity as original_driver
from scripts import p106b_night_diversity_data as data
from scripts import diag_p106b_night_foundation as foundation
from scripts import diag_p106b_night_prompt as other
from scripts import p106b_night_course as qa
from scripts import p106b_night_learning as method
from scripts import diag_p106b_night_train as previous
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_native_windows import reader as native_reader

TAG = 'p106b_night_diversity_scope_v2_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
CODE = ('scripts/diag_p106b_night_diversity_scope_v2.py',
        'scripts/test_p106b_night_diversity_scope_v2.py', *original_driver.CODE)
TRAINED_ENDPOINTS = ('base_qa', 'base_qa_best', 'cpt_qa', 'cpt_qa_best')
ALWAYS_EVALUATE = ('prompt0', 'prompt0_best', 'prompt01', 'prompt01_best',
                   'unique32k', 'unique32k_best')
EVALUATION_SECONDS = 900
RESERVE_SECONDS = 600


def info():
    result = original_driver.info()
    result.update(schema='P106B_NIGHT_UNIQUE_QA_SCOPE_V2', tag=TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        original_driver_code_sha256=original_driver.info()['code_sha256'],
        scientific_conditions_changed=False, budget_only_revision=True,
        legacy_gate_credited=False,
        excluded_reservations=dict(falcon896='ALREADY_COMPLETED_OUTSIDE_THIS_SCOPE',
            bare_full512='HOLD_NOT_COMPLETE', input_order_training='HOLD_NOT_COMPLETE'))
    return result


def namespace():
    for target in (CORPUS, EVIDENCE, checkpoint(), checkpoint(True)):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('새 범위의 심볼릭 링크는 허용하지 않는다')
            if parent == ROOT: break


def _segment(source, name, gpu_core=False):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    if gpu_core:
        node = next(n for n in node.body if isinstance(n, ast.Try))
    text = ast.get_source_segment(source, node)
    return ast.dump(node, include_attributes=False), hashlib.sha256(text.encode('utf-8')).hexdigest().upper()


def core_equivalence(original_source=None, candidate_source=None):
    """훈련·저장·완료 판정의 AST 및 정확한 문자구간을 별도로 검산한다."""
    if original_source is None:
        original_source = (ROOT / 'scripts/diag_p106b_night_diversity.py').read_text(encoding='utf-8')
    if candidate_source is None:
        candidate_source = Path(__file__).read_text(encoding='utf-8')
    proof = {}
    for name in ('checkpoint', 'completed', 'save', 'run'):
        left = _segment(original_source, name, gpu_core=name == 'run')
        right = _segment(candidate_source, name, gpu_core=name == 'run')
        if left != right: raise ValueError('동결 원본의 핵심 구간과 다르다: ' + name)
        proof[name] = dict(ast_sha256=hashlib.sha256(left[0].encode('utf-8')).hexdigest().upper(),
            character_segment_sha256=left[1], ast_equal=True, character_equal=True)
    return proof


def _first8(courses):
    natural, replay = courses[0]
    groups = method.schedule(len(natural), len(replay), 0)
    if len(groups) != 160: raise ValueError('원본 첫 분기의 160개 업데이트가 필요하다')
    totals = Counter(); updates = []
    for index, group in enumerate(groups[:8], 1):
        words, content = previous.denominators(group, natural, replay)
        if words <= 0: raise ValueError('비어 있지 않은 원본 분모가 필요하다')
        records = [r for micro in group for r in previous.micro_records(micro, natural, replay)]
        if len(records) != 128: raise ValueError('원본 micro8과 accum16이 필요하다')
        totals.update(actual_x_tokens=sum(r.x_tokens for r in records),
            assistant_targets=words, native_x_tokens=8192, padded_slots=len(records) * 1024,
            pairs_seen=sum(len(m.indices) for m in group if m.kind == 'natural'),
            content_targets=content)
        updates.append(dict(updates=index, logical_quarter=1, natural_epoch=1,
            x=totals['actual_x_tokens'], assistant_targets=totals['assistant_targets'],
            native_x=totals['native_x_tokens']))
    if len(updates) != 8: raise ValueError('정확한 비용8 원형이 필요하다')
    return dict(totals), updates


def _source_binding(report, expanded, courses):
    if (report.get('status') != 'DIVERSITY_CPU_FROZEN'
            or report.get('code_sha256') != original_driver.info()['code_sha256']
            or report.get('actual_parent_loaded_cpu') is not True
            or report.get('cuda_initialized') is not False
            or report.get('padding') != [0, 4]
            or report.get('first160_actual_x_y_equal') is not True
            or report.get('checkpoints_written') != 0 or report.get('optimizer_updates') != 0
            or not isinstance(report.get('initial_core_sha256'), str)
            or len(report['initial_core_sha256']) != 64):
        raise ValueError('원본 CPU 원형과 실제 부모 검산 계약이 필요하다')
    cost8, updates = _first8(courses)
    return dict(original_cpu_sha256=qa.data.digest(original_driver.CORPUS / 'report.json'),
        original_cpu_evidence_sha256=qa.data.digest(original_driver.EVIDENCE / 'cpu_contract.json'),
        original_driver_code_sha256=original_driver.info()['code_sha256'],
        original_manifests=report['manifests'], source_contract=report['source_contract'],
        inventory=report['inventory'], actual_exposure=report['actual_exposure'],
        schedules=report['schedules'], initial_core_sha256=report['initial_core_sha256'],
        same_replay_sha256=report['same_replay_sha256'],
        actual_split_sha256={split: qa.data.sha(rows) for split, rows in expanded.items()},
        original_qa_report_sha256=qa.data.digest(ROOT / foundation.data.QA_REPORT),
        cost8_expected=cost8, cost8_updates=updates,
        core_equivalence=core_equivalence())


def prepare():
    from tinylm.train import mtp_sft as core
    namespace(); previous.deadline(training=True)
    if CORPUS.parent.exists() or EVIDENCE.exists() or checkpoint().exists() or checkpoint(True).exists():
        raise FileExistsError('기존 새 범위의 완결 또는 부분 산출물을 보존한다')
    original, expanded, tok, courses, _ = original_driver.read_source()
    binding = _source_binding(original, expanded, courses)
    torch, model, cfg, actual_tok, initial, cp, identity = foundation.load_foundation_parent('base_qa')
    if (initial != binding['initial_core_sha256'] or actual_tok.to_str() != tok.to_str()
            or cp != foundation.data.PARENT or identity != foundation.data.PARENT_SHA):
        raise ValueError('실제 원P090B 부모 본체와 토크나이저가 같아야 한다')
    pad, eot, _ = previous.special_ids(tok)
    sample = courses[0][0][0] + courses[0][1][:6]
    px, py, ps = core.pad_records(sample, pad, 'cpu', fixed_width=1024, batch_size=8)
    if (list(px.shape) != [8, 1024] or list(py.shape) != [8, 1024]
            or list(ps.shape) != [8, 1024] or pad != 0 or eot != 4):
        raise ValueError('실제 원본 padding과 EOT 구조가 필요하다')
    if torch.cuda.is_initialized(): raise ValueError('CPU 준비가 CUDA를 초기화했다')
    CORPUS.mkdir(parents=True, exist_ok=False)
    result = dict(info(), **binding, status='DIVERSITY_CPU_FROZEN',
        actual_parent_loaded_cpu=True, cuda_initialized=False, padding=[pad, eot],
        actual_padded_shape=list(px.shape), first160_actual_x_y_equal=True,
        initializer_sha256=identity, initializer=str(cp.relative_to(ROOT)),
        model_forward=False, checkpoints_written=0, optimizer_updates=0,
        source_corpus=str(original_driver.CORPUS.relative_to(ROOT)), source_rewritten=False)
    qa.write(CORPUS / 'report.json', result); qa.write(EVIDENCE / 'cpu_contract.json', result)
    print('[DIVERSITY_SCOPE_CPU] ' + json.dumps(dict(status=result['status'],
        actual=result['actual_exposure'], original_cpu_sha256=result['original_cpu_sha256'])), flush=True)
    return 0


def read_source():
    namespace()
    original, expanded, tok, courses, qa_original = original_driver.read_source()
    binding = _source_binding(original, expanded, courses)
    report = qa.required(CORPUS / 'report.json')
    if (report.get('status') != 'DIVERSITY_CPU_FROZEN'
            or report.get('code_sha256') != info()['code_sha256']
            or qa.required(EVIDENCE / 'cpu_contract.json') != report
            or any(report.get(key) != value for key, value in binding.items())
            or report.get('actual_parent_loaded_cpu') is not True
            or report.get('cuda_initialized') is not False or report.get('padding') != [0, 4]
            or report.get('actual_padded_shape') != [8, 1024]
            or report.get('initializer_sha256') != foundation.data.PARENT_SHA
            or report.get('initializer') != str(foundation.data.PARENT.relative_to(ROOT))
            or report.get('first160_actual_x_y_equal') is not True
            or report.get('source_corpus') != str(original_driver.CORPUS.relative_to(ROOT))
            or report.get('source_rewritten') is not False or report.get('model_forward') is not False
            or report.get('checkpoints_written') != 0 or report.get('optimizer_updates') != 0):
        raise ValueError('새 코드와 원본 실물 courses에 결합한 완전한 CPU 증거가 필요하다')
    return report, expanded, tok, courses, qa_original


def _cost_events(report):
    directory = EVIDENCE / 'cost8'
    verify(directory, report['event_manifest'])
    return [json.loads(line) for shard in report['event_manifest']['shards']
        for line in (directory / shard['path']).read_text(encoding='utf-8').splitlines()]


def cost_forecast(report, proof=None):
    if proof is None: proof = read_source()[0]
    times = report.get('step_seconds', [])
    expected = proof['cost8_expected']
    if (report.get('status') != 'DIVERSITY_COST_COMPLETE' or report.get('updates') != 8
            or report.get('tag') != TAG or report.get('code_sha256') != info()['code_sha256']
            or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
            or report.get('initializer_sha256') != foundation.data.PARENT_SHA
            or report.get('initial_core_sha256') != proof['initial_core_sha256']
            or report.get('actual_oom') is not False or report.get('checkpoint_written') is not False
            or any(report.get(k) != v for k, v in expected.items())
            or report.get('event_manifest', {}).get('rows') != 8
            or len(times) != 8
            or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in times)):
        raise ValueError('새 범위에서 실제 성공한 동일 원형 비용8이 필요하다')
    events = _cost_events(report)
    if len(events) != 8: raise ValueError('새 비용8의 전체 이벤트가 필요하다')
    for index, (event, expected_update) in enumerate(zip(events, proof['cost8_updates'])):
        if (any(event.get(k) != v for k, v in expected_update.items())
                or event.get('step_seconds') != times[index]
                or any(type(event.get(k)) not in (int, float) or not math.isfinite(event[k])
                       for k in ('ce', 'grad'))):
            raise ValueError('새 비용8의 원답 이벤트와 노출 및 시간 보고가 다르다')
    return max(times[1:]) * 640 + 600


def pending_prompt_training():
    proof, *_ = other.read_source()
    remaining = {}; completed_arms = []
    for arm in other.ARMS:
        if other.completed_prompt(arm, proof):
            completed_arms.append(arm); continue
        report = qa.required(other.EVIDENCE / ('cost_' + arm) / 'report.json')
        first = proof['update_exposure'][:8]
        if (report.get('status') != 'PROMPT_COST_COMPLETE' or report.get('arm') != arm
                or report.get('beta') != other.BETAS[arm]
                or report.get('cpu_contract_sha256') != qa.data.digest(other.CORPUS / 'report.json')
                or report.get('source_qa_sha256') != foundation.data.LOCKED_QA_SHA
                or report.get('initializer_sha256') != foundation.data.PARENT_SHA
                or report.get('initial_core_sha256') != proof['initial_core_sha256']
                or report.get('actual_x_tokens') != sum(e['x'] for e in first)
                or report.get('assistant_targets') != sum(e['assistant_targets'] for e in first)
                or report.get('prompt_targets') != sum(e['prompt_targets'] for e in first)
                or report.get('content_targets') != sum(e['content_targets'] for e in first)
                or report.get('native_x_tokens') != 65536 or report.get('padded_slots') != 1048576
                or report.get('event_manifest', {}).get('rows') != 8 or len(first) != 8):
            raise ValueError('미완료 본문보조 팔의 같은 원형 비용8이 필요하다')
        verify(other.EVIDENCE / ('cost_' + arm), report['event_manifest'])
        remaining[arm] = other.cost_estimate(report, other.info()['code_sha256'], 640)
    return remaining, completed_arms


def pending_trained_evaluations(evaluation=None):
    if evaluation is None:
        from scripts import diag_p106b_night_eval_recovery as evaluation
    # 평가 유무와 무관하게 네 학습이 끝나 있어야 이 예산 범위를 쓸 수 있다.
    # 체크포인트가 없거나 본체가 바뀌면 미완료 학습비용을 0으로 보지 않는다.
    checkpoints = {}
    for endpoint in TRAINED_ENDPOINTS:
        cp, identity = evaluation.checkpoint_spec(endpoint)
        if qa.data.digest(cp) != identity:
            raise ValueError('네 학습 endpoint의 완료 계약과 실제 체크포인트 SHA가 필요하다: ' + endpoint)
        checkpoints[endpoint] = cp, identity
    _, inputs, cases = evaluation.read_inputs()
    pending = []; completed_endpoints = []
    for endpoint in TRAINED_ENDPOINTS:
        path = evaluation.EVIDENCE / (endpoint + '_report.json')
        if not path.exists():
            pending.append(endpoint); continue
        report = qa.required(path); evaluation.endpoint_contract(report, endpoint, inputs)
        cp, identity = checkpoints[endpoint]
        if (report.get('code_sha256') != evaluation.info()['code_sha256']
                or report.get('input_report_sha256') != qa.data.digest(evaluation.FROZEN / 'report.json')
                or report.get('checkpoint') != str(cp.relative_to(ROOT))
                or report.get('checkpoint_sha256') != identity or qa.data.digest(cp) != identity):
            raise ValueError('학습후 평가의 같은 코드와 원형 및 본체 보고가 필요하다')
        for lane in evaluation.OUTPUTS:
            receipt = evaluation.read_receipt(endpoint, lane, cases)
            if (receipt['output'] != report['outputs'][lane]
                    or qa.data.digest(evaluation.receipt_path(endpoint, lane)) != report['receipt_sha256'][lane]):
                raise ValueError('학습후 평가의 원답 검산 및 영수증이 다르다')
        completed_endpoints.append(endpoint)
    return pending, completed_endpoints


def budget(proof=None, now=None):
    if proof is None: proof = read_source()[0]
    own = cost_forecast(qa.required(EVIDENCE / 'cost8/report.json'), proof)
    prompts, completed_prompts = pending_prompt_training()
    pending, completed_evals = pending_trained_evaluations()
    # 부모 소형 진단과 새 여섯 평가의 완료를 가정하지 않고 계속 예약한다.
    evaluations = len(ALWAYS_EVALUATE) * EVALUATION_SECONDS
    panels = 2 * EVALUATION_SECONDS
    trained = len(pending) * EVALUATION_SECONDS
    needed = own + sum(prompts.values()) + evaluations + panels + trained + RESERVE_SECONDS
    now = datetime.now(timezone.utc) if now is None else now
    remaining = (qa.TRAIN_STOP - now).total_seconds()
    result = dict(tag=TAG, own_training_seconds=own, pending_prompt_training_seconds=prompts,
        verified_completed_prompt_arms=completed_prompts,
        always_reserved_full_evaluations=list(ALWAYS_EVALUATE),
        full_evaluation_seconds=evaluations, bare64_panel_count=2, bare64_panel_seconds=panels,
        pending_trained_evaluations=pending, verified_completed_trained_evaluations=completed_evals,
        trained_evaluation_seconds=trained, reserve_seconds=RESERVE_SECONDS,
        excluded_reservations=dict(falcon896=dict(seconds=0, status='EXTERNAL_COMPLETE_NOT_LEGACY_GATE_CREDIT'),
            bare_full512=dict(seconds=0, status='HOLD_NOT_COMPLETE'),
            input_order_training=dict(seconds=0, status='HOLD_NOT_COMPLETE')),
        legacy_gate_credited=False, needed_seconds=needed, remaining_seconds=remaining)
    if (not math.isfinite(needed) or needed <= 0 or needed >= remaining):
        raise ValueError('새 범위의 실제 남은 예약이 09시 이전에 들어오지 않는다: ' + json.dumps(result))
    return result


def checkpoint(best=False):
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_night_' + TAG + ('_best' if best else '') + '.pt')


def completed(proof):
    def validate(report):
        expected = proof['actual_exposure']
        if (report.get('code_sha256') != info()['code_sha256'] or report.get('updates') != 640
                or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
                or report.get('initial_core_sha256') != proof['initial_core_sha256']
                or report.get('initializer_sha256') != foundation.data.PARENT_SHA
                or report.get('actual_x_tokens') != expected['x_tokens']
                or report.get('assistant_targets') != expected['assistant_targets']
                or report.get('native_x_tokens') != 5242880 or report.get('padded_slots') != 83886080
                or report.get('pairs_seen') != 32768 or report.get('natural_epoch') != 1
                or report.get('logical_quarters') != 4 or report.get('actual_oom') is not False
                or report.get('checkpoint_written') is not True
                or report.get('checkpoint') != str(checkpoint().relative_to(ROOT))
                or qa.data.digest(checkpoint()) != report.get('checkpoint_sha256')
                or report.get('event_manifest', {}).get('rows') != 640):
            raise ValueError('complete same-source unique32k640 exposure/body/checkpoint proof required')
        verify(EVIDENCE / 'unique32k', report['event_manifest'])
    return other.completion(EVIDENCE / 'unique32k/report.json', 'DIVERSITY_TRAIN_COMPLETE', validate)


def save(torch, path, state, cfg, steps, quarter, core):
    with path.open('xb') as output:
        torch.save(dict(model=state, cfg=asdict(cfg), step=steps, optimizer_saved=False,
            tokenizer_sha256=qa.data.TOK_SHA, tokenizer_lineage='chat32',
            night_diversity=dict(tag=TAG, logical_quarter=quarter, natural_epoch=1,
                initializer_sha256=foundation.data.PARENT_SHA, core_sha256=core)), output)
    return dict(path=str(path.relative_to(ROOT)), sha256=qa.data.digest(path))


def run(cost, max_wall_sec):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    proof, expanded, tok, courses, original = read_source(); target = EVIDENCE / ('cost8' if cost else 'unique32k')
    if target.exists() or (not cost and checkpoint().exists()): raise FileExistsError('old complete/partial diversity preserved')
    if not cost:
        from scripts import diag_p106b_night_eval_recovery as evaluation
        evaluation.checkpoint_spec('base_qa')
        reservation = budget(proof)
        print('[DIVERSITY_SCOPE_BUDGET] ' + json.dumps(reservation), flush=True)
    previous.deadline(training=True); idle_before_gpu(); target.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter(); events = ShardWriter(target, 'events')
    qa.write(target / 'start.json', dict(info(), cost=cost, cpu_contract_sha256=qa.data.digest(CORPUS / 'report.json')))
    try:
        with wall_limit(min(max_wall_sec, int((qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()))):
            torch, base, cfg, actual_tok, initial, cp, identity = foundation.load_foundation_parent('base_qa')
            if initial != proof['initial_core_sha256'] or actual_tok.to_str() != tok.to_str(): raise ValueError('same original body/tokenizer required')
            pad, eot, _ = previous.special_ids(tok); windows = native_reader(ROOT, original)
            base = base.cuda(); torch.cuda.reset_peak_memory_stats()
            before = None if cost else foundation.runtime.native_ce(base, qa.NATIVE)
            dev_before = None if cost else previous.dev_loss(base, expanded['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_diversity_')
            model = torch.compile(base, mode='default'); adam, muon = foundation.runtime.optimizers(base)
            for optimizer in (adam, muon):
                for group in optimizer.param_groups: group['lr'] *= .5
            steps = x_tokens = targets = native_x = slots = content_n = pairs_n = 0
            times = []; history = []; gmax = 0.; clips = 0; best_ce = math.inf; best_state = best_core = best_quarter = None
            for quarter, (natural, replay) in enumerate(courses):
                epoch_nll = 0.; epoch_words = 0
                for group in method.schedule(len(natural), len(replay), quarter):
                    previous.deadline(training=True); tick = time.perf_counter()
                    adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
                    denom = previous.denominators(group, natural, replay)[0]; nword = 0; step_nll = torch.zeros((), device='cuda')
                    for micro in group:
                        records = previous.micro_records(micro, natural, replay)
                        x, y, seg = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=8)
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            hidden = model(x, return_hidden=True)
                            if micro.kind == 'natural':
                                values, cn, pn = method.natural_sums(base, hidden, records, eot)
                                loss = values[0] / denom + values[1] * 0.; nll = values[0]
                                n = sum(r.targets for r in records); content_n += cn; pairs_n += pn
                            else:
                                sums, valid = core.components(base, hidden, y, seg, horizons=())
                                n, nll = valid[1], sums[1]; loss = nll / denom
                        if not bool(torch.isfinite(loss)): raise ValueError('nonfinite diversity assistant loss')
                        loss.backward(); nword += n; step_nll += nll.detach()
                        slots += x.numel(); x_tokens += sum(r.x_tokens for r in records)
                    if nword != denom: raise ValueError('actual complete-update denominator differs')
                    x, y, seg = foundation.native_batch(torch, windows, list(range(steps * 8, (steps + 1) * 8)))
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        hidden = model(x, return_hidden=True); sums, _ = core.components(base, hidden, y, seg, horizons=()); loss_native = sums[1] / 8192
                    if not bool(torch.isfinite(loss_native)): raise ValueError('nonfinite native replay')
                    loss_native.backward(); native_x += 8192
                    grad = torch.nn.utils.clip_grad_norm_(base.parameters(), 1.)
                    if not bool(torch.isfinite(grad)): raise ValueError('nonfinite diversity gradient')
                    gmax = max(gmax, float(grad)); clips += int(grad > 1.)
                    adam.step(); muon.step(); steps += 1; targets += nword
                    torch.cuda.synchronize(); times.append(time.perf_counter() - tick)
                    epoch_words += nword; epoch_nll += float(step_nll)
                    event = dict(updates=steps, logical_quarter=quarter + 1, natural_epoch=1,
                        x=x_tokens, assistant_targets=targets, native_x=native_x,
                        ce=float(step_nll) / nword, grad=float(grad), step_seconds=times[-1])
                    events.append(event)
                    if steps <= 8 or steps % 100 == 0: print('[DIVERSITY_UPDATE] ' + json.dumps(event), flush=True)
                    if cost and steps == 8: break
                if cost: break
                entry = dict(logical_quarter=quarter + 1, updates=steps, train_ce=epoch_nll / epoch_words,
                    dev=previous.dev_loss(base, expanded['dev'], tok, pad, eot), native=foundation.runtime.native_ce(base, qa.NATIVE))
                history.append(entry)
                if entry['dev']['ce'] < best_ce:
                    best_ce = entry['dev']['ce']; best_quarter = quarter + 1
                    best_state = {k:v.detach().cpu().clone() for k,v in base.state_dict().items()}
                    best_core = foundation.runtime.state_fingerprint(base)
                print('[DIVERSITY_QUARTER] ' + json.dumps(entry), flush=True)
            if not cost and (steps != 640 or dict(rows=81920, x_tokens=x_tokens, assistant_targets=targets) != proof['actual_exposure']
                    or native_x != 5242880 or slots != 83886080 or pairs_n != 32768
                    or content_n != sum(s['content_targets'] for s in proof['schedules'])):
                raise ValueError('full actual same-update exposure differs')
            result = dict(info(), status='DIVERSITY_COST_COMPLETE' if cost else 'DIVERSITY_TRAIN_COMPLETE',
                updates=steps, actual_x_tokens=x_tokens, assistant_targets=targets, native_x_tokens=native_x,
                padded_slots=slots, pairs_seen=pairs_n, content_targets=content_n, step_seconds=times,
                initial_core_sha256=initial, initializer_sha256=identity,
                cpu_contract_sha256=qa.data.digest(CORPUS / 'report.json'), native_before=before,
                dev_before=dev_before, history=history, grad_max=gmax, clip_events=clips, actual_oom=False,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                peak_scope='torch allocator only, not global WDDM peak', checkpoint_written=not cost)
            if not cost:
                final_core = foundation.runtime.state_fingerprint(base)
                saved = save(torch, checkpoint(), base.state_dict(), cfg, steps, 4, final_core)
                best = saved if best_quarter == 4 else save(torch, checkpoint(True), best_state, cfg, best_quarter * 160, best_quarter, best_core)
                result.update(checkpoint=saved['path'], checkpoint_sha256=saved['sha256'], final_core_sha256=final_core,
                    best_dev_checkpoint=best['path'], best_dev_checkpoint_sha256=best['sha256'],
                    best_dev_core_sha256=best_core, best_dev_quarter=best_quarter, best_dev_ce=best_ce)
            result['event_manifest'] = events.close(lineage=info()); result['whole_seconds'] = time.perf_counter() - began
            qa.write(target / 'report.json', result)
    except BaseException as exc:
        try: qa.write(target / 'error.json', dict(status='ERROR_OR_INTERRUPTED', message=str(exc), exception=type(exc).__name__))
        except Exception: pass
        raise
    print('[DIVERSITY_FINAL] ' + json.dumps(dict(status=result['status'], updates=steps, whole_seconds=result['whole_seconds'])), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('freeze', 'cost', 'train'), required=True)
    p.add_argument('--max-wall-sec', type=int, default=14400); p.add_argument('--execute', action='store_true'); a = p.parse_args()
    if not a.execute or not 60 <= a.max_wall_sec <= 14400: p.error('explicit execute and60..14400 bounded wall required')
    try: return prepare() if a.mode == 'freeze' else run(a.mode == 'cost', a.max_wall_sec)
    except KeyboardInterrupt:
        print('[DIVERSITY_INTERRUPTED] partial outputs preserved'); return 130
    except Exception as exc:
        print('[DIVERSITY_ERROR] ' + type(exc).__name__ + ': ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
