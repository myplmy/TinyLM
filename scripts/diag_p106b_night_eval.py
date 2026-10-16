#!/usr/bin/env python3
"""Write-once natural QA, counterfactual, retention and public evaluation.

No weights are changed. Raw answers stay in ignored <=20MB private shards;
small metrics, hashes and independent paired recounts remain reviewable.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter, defaultdict
import copy
from datetime import datetime, timezone
import gc
import json
import random
import time
from scripts import p106b_night_course as c
from scripts import diag_p106b_night_train as train
from scripts import p106b_night_learning as metrics
from scripts.p106b_shards import ShardWriter, verify

FROZEN = c.CORPUS.parent / 'evaluation'
EVIDENCE = c.EVIDENCE / 'evaluate'
LOCAL = ROOT / 'test_result/evidence/local' / c.TAG / 'evaluate'
ENDPOINTS = ('parent', *c.ARMS)
OUTPUTS = frozenset(('natural', 'cube', 'role', 'recovery', 'code', 'public', 'native32', 'native256'))
CODE = ('scripts/diag_p106b_night_eval.py', 'scripts/p106b_night_evaluation.py',
        'scripts/test_p106b_night_evaluation.py', 'scripts/test_p106b_night_eval.py',
        'tinylm/infer/generate.py', 'scripts/diag_p101a_mtp_parity.py',
        'scripts/p106b_original_qa3_evaluation.py', 'scripts/eval_bench_suite.py')


def info():
    return dict(schema='P106B_NIGHT_ACTUAL_EVALUATION_V1', tag=c.TAG,
        code_sha256={p: c.data.digest(ROOT / p) for p in CODE},
        endpoints=list(ENDPOINTS), precision='FP32_MATH', temperature=0., top_k=1,
        max_new_natural=128, max_new_retention=64, use_cache=True, mtp=False,
        training_seeds=1, test_checkpoint_selection=False,
        primary='article-disjoint natural TEST both seen wrappers and unseen wrapper2',
        local_metric='NFKC lower/punctuation except numeric signs/decimals; KO char-F1/EN word-F1',
        official_scorer_equivalence=False, teacher_calls=0, model_training=False,
        semantic_truth='source annotation/code facts; not a global intelligence certificate',
        public_contamination='NOT_AUDITED_AGAINST_ALL_PRETRAINING',
        deadline_utc=c.DEADLINE.isoformat())


def safe_namespace():
    for target in (FROZEN, EVIDENCE, LOCAL):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('linked evaluation namespace')
            if parent == ROOT: break


def stream(directory, manifest):
    verify(directory, manifest)
    for shard in manifest['shards']:
        for line in (directory / shard['path']).read_text(encoding='utf-8').splitlines():
            yield json.loads(line)


def store(stem, values):
    writer = ShardWriter(FROZEN, stem)
    for value in values: writer.append(value)
    return writer.close(lineage=dict(tag=c.TAG, source='fixed before child answers'))


def root_subset(rows, count):
    key = lambda r: r['meta'].get('neutral_root', r['meta']['semantic_root_id'])
    roots = sorted({key(r) for r in rows}, key=lambda value: c.data.sha([20261016, value]))[:count]
    if len(roots) != count: raise ValueError('complete retention root supply required')
    return [r for r in rows if key(r) in set(roots)]


def mc_skip_reason(item, tok, context=1024):
    if type(item.get('gold')) is not int: raise ValueError('explicit MC gold index required')
    if item['gold'] < 0: return 'gold_missing'
    pairs = item.get('pairs') or [(item['ctx'], text) for text in item['choices']]
    if item['gold'] >= len(pairs): raise ValueError('MC gold index exceeds choices')
    for prompt, answer in pairs:
        prefix = tok.encode(prompt).ids if prompt else [tok.encode('\n').ids[0]]
        continuation = tok.encode(answer).ids
        if not continuation or len(prefix) + len(continuation) > context:
            return 'seq_max_exceeded'
    return None


def prepare():
    import numpy as np
    import torch
    from scripts import diag_p106b_evidence_recovery_course as old
    from scripts import diag_p106b_authorized_benchmark as public
    from scripts import p106b_night_evaluation as method
    from tokenizers import Tokenizer
    safe_namespace()
    if FROZEN.exists() or (EVIDENCE / 'inputs.json').exists():
        raise FileExistsError('frozen evaluation preserved')
    r, rows = c.read_night_course(); original, retained, _ = old.read_course()
    role = root_subset(retained['test_role_style0'] + retained['test_role_style2'], 16)
    recovery = root_subset(retained['test_evidence'], 8)
    code = c.stratified(retained['dev_code'], 96, ('language', 'kind'))
    previous = c.required(public.FROZEN / 'report.json')
    if c.data.digest(public.FROZEN / 'report.json') != 'A2D57C8E2A8F767EBA4D679A1660AB2A85A0B756A713FB0196D013DFB2E3A926':
        raise ValueError('original public inputs changed')
    for descriptor in previous['sources'].values():
        if c.data.digest(ROOT / descriptor['path']) != descriptor['sha256']:
            raise ValueError('original public source changed')
    benchmark = list(stream(public.FROZEN, previous['manifest']))
    tok = Tokenizer.from_file(str(c.data.TOKENIZER))
    for case in benchmark:
        if case['kind'] == 'mc': case['expected_skip'] = mc_skip_reason(case['item'], tok)
    tokens = np.memmap(c.NATIVE / 'val.bin', dtype=np.uint16, mode='r')
    offsets = list(range(32 * 1024, len(tokens) - 1024, 1024))
    random.Random(20261016).shuffle(offsets); offsets = offsets[:256]
    if len(offsets) != 256: raise ValueError('256 additional native val crops required')
    FROZEN.mkdir(parents=True, exist_ok=False)
    datasets = dict(natural=rows['test'], cube=method.cube_rows(), role=role,
                    recovery=recovery, code=code, public=benchmark)
    manifests = {name: store(name, values) for name, values in datasets.items()}
    if torch.cuda.is_initialized(): raise ValueError('CPU evaluation preparation initialized CUDA')
    result = dict(info(), status='EVAL_INPUTS_FROZEN', manifests=manifests,
        corpus_sha256=c.data.digest(c.CORPUS / 'report.json'),
        counts={k: len(v) for k, v in datasets.items()}, native256_val_offsets=offsets,
        native_val_sha256=r['native_val_sha256'],
        old_retention_sha256=c.data.digest(old.CORPUS / 'report.json'),
        old_public_report_sha256=c.data.digest(public.FROZEN / 'report.json'),
        public_mc_expected_skips=dict(Counter(x['expected_skip'] for x in benchmark
            if x['kind'] == 'mc' and x['expected_skip'] is not None)),
        natural_qa_original_questions=True, train_dev_test_article_disjoint=True,
        old_evaluation_is_development=True, new_test_not_used_for_training_or_selection=True)
    c.write(FROZEN / 'report.json', result); c.write(EVIDENCE / 'inputs.json', result)
    print('[NIGHT_EVAL_INPUTS] ' + json.dumps(result['counts']), flush=True)
    return 0


def read_inputs():
    safe_namespace()
    r = c.required(FROZEN / 'report.json')
    if (r['status'] != 'EVAL_INPUTS_FROZEN' or r['code_sha256'] != info()['code_sha256']
            or r['corpus_sha256'] != c.data.digest(c.CORPUS / 'report.json')
            or r['native_val_sha256'] != c.data.digest(c.NATIVE / 'val.bin')):
        raise ValueError('frozen evaluation code/data identity differs')
    return r, {name: list(stream(FROZEN, manifest)) for name, manifest in r['manifests'].items()}


def emit_function(base, cfg, tok, max_new=128):
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    wrapped = PrecisionForward(base, 'fp32_math')
    def emit(messages):
        train.deadline()
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


def dialogue(row, emit):
    """Actual model history, with separate gold-history diagnostics after turn1."""
    messages = row['messages']; meta = row['meta']
    if len(messages) % 2 or [m['role'] for m in messages] != ['user', 'assistant'] * (len(messages) // 2):
        raise ValueError('complete code-owned alternating turns required')
    result = []; history = []
    for turn in range(1, len(messages) // 2 + 1):
        history.append(copy.deepcopy(messages[2 * turn - 2]))
        prefixes = [('ACTUAL_MODEL', copy.deepcopy(history))]
        if turn > 1: prefixes.append(('GOLD_REFERENCE', copy.deepcopy(messages[:2 * turn - 1])))
        actual = None
        for kind, prefix in prefixes:
            answer, generation = emit(prefix)
            gold = c.data.text(messages[2 * turn - 1])
            event = dict(root=meta['semantic_root_id'], neutral_root=meta.get('neutral_root'),
                language=meta['language'], turn=turn, history=kind, messages=prefix,
                answer=answer, gold=gold, generation=generation,
                kind=meta['kind'], condition=meta.get('condition'), family=meta.get('family'),
                first_response_intent=meta.get('first_response_intent'), query_sufficient=meta.get('query_sufficient'),
                view=meta.get('view'), question_style=meta.get('question_style'),
                literal=int(answer.strip() == gold.strip()),
                clarification_semantics='NOT_AUTOMATICALLY_ADJUDICATED')
            result.append(event)
            if kind == 'ACTUAL_MODEL': actual = answer
        history.append(dict(role='assistant', content=actual))
    return result


def summarize_dialogue(events):
    totals = defaultdict(Counter); seen = set()
    for event in events:
        key = (event['root'], event['turn'], event['history'])
        if key in seen: raise ValueError('duplicate retention event')
        seen.add(key)
        if event['literal'] != int(event['answer'].strip() == event['gold'].strip()):
            raise ValueError('retention raw score mismatch')
        lanes = [event['history'] + '/all', event['history'] + '/' + event['language'],
                 event['history'] + '/turn' + str(event['turn'])]
        if event['condition'] is not None:
            lanes.append(event['history'] + '/condition' + str(event['condition']))
        for lane in lanes:
            totals[lane].update(n=1, literal=event['literal'], empty=int(not event['answer']))
    return dict(totals)


def verify_dialogue_rows(events, originals):
    """Rebuild every actual and gold prefix from frozen source + raw outputs."""
    cursor = 0; rebuilt = []
    def replay(prefix):
        nonlocal cursor
        if cursor >= len(events): raise ValueError('missing retention event')
        observed = events[cursor]; cursor += 1
        if prefix != observed['messages']: raise ValueError('retention actual/gold prompt changed')
        return observed['answer'], observed['generation']
    for original in originals: rebuilt.extend(dialogue(original, replay))
    if cursor != len(events) or rebuilt != events:
        raise ValueError('retention source/gold/case/order differs')
    return summarize_dialogue(events)


def public_recount(events, original_cases):
    """ID/gold/argmin and generation scoring are independent of saved totals."""
    import math
    from scripts import diag_p106b_authorized_benchmark as public
    expected = {(r['task'], r['item']['_iid'] if r['kind'] == 'mc' else r['id']): r for r in original_cases}
    indexed = {}
    for event in events:
        key = (event['task'], event['id'])
        if key in indexed or key not in expected: raise ValueError('duplicate/unknown public case')
        original = expected[key]
        if event['kind'] != original['kind']: raise ValueError('public original task kind differs')
        if event['kind'] == 'mc':
            if event.get('skipped'):
                if (original.get('expected_skip') not in ('gold_missing', 'seq_max_exceeded')
                        or event.get('reason') != original['expected_skip']):
                    raise ValueError('public MC skip differs from actual frozen eligibility')
            else:
                if original.get('expected_skip') is not None:
                    raise ValueError('ineligible frozen MC case was unexpectedly scored')
                gold = original['item']['gold']; losses = event['sum_nll']
                n_choices = len(original['item'].get('pairs') or original['item']['choices'])
                if (event['gold'] != gold or len(losses) != n_choices
                        or not all(type(v) in (int, float) and math.isfinite(v) for v in losses)
                        or event['pred_harness'] != min(range(n_choices), key=lambda i: losses[i])):
                    raise ValueError('public gold or summed-NLL argmin differs')
        elif not event.get('skipped'):
            if event['prompt'] != original['prompt'] or event['golds'] != original['golds']:
                raise ValueError('public original prompt/gold changed')
            score = public.answer_scores(event['answer'], event['golds'])
            if event['task'] == 'gsm8k_free':
                score['numeric_exact'] = int(public.numerical(event['answer']) is not None
                    and public.numerical(event['answer']) == public.numerical(event['golds'][0]))
            if score != event['scores']: raise ValueError('public raw generation score differs')
        elif original['prompt_tokens'] + 128 <= 1024:
            raise ValueError('unexpected complete-budget public generation skip')
        indexed[key] = event
    if set(indexed) != set(expected): raise ValueError('incomplete public original case set')
    result = {}
    for task in (*public.TASKS, 'korquad_free', 'gsm8k_free'):
        values = [e for e in events if e['task'] == task and not e.get('skipped')]
        skipped = sum(e['task'] == task and bool(e.get('skipped')) for e in events)
        if task in public.TASKS:
            result[task] = dict(n=len(values), skipped=skipped,
                correct=sum(e['pred_harness'] == e['gold'] for e in values),
                prediction_counts={str(k): v for k, v in Counter(e['pred_harness'] for e in values).items()})
        else:
            primary = 'numeric_exact' if task == 'gsm8k_free' else 'whitespace_nfkc_exact'
            result[task] = dict(n=len(values), skipped=skipped,
                correct=sum(e['scores'][primary] for e in values), primary=primary)
    return result


def endpoint_contract(report, endpoint, inputs):
    """Missing lanes and native denominators cannot become an errors=0 receipt."""
    import math
    if (report.get('status') != 'ACTUAL_EVALUATION_COMPLETE'
            or report.get('endpoint') != endpoint or set(report.get('outputs', {})) != OUTPUTS
            or report.get('checkpoints_written') != 0
            or report.get('directory') != str((LOCAL / endpoint).relative_to(ROOT))):
        raise ValueError('complete exact endpoint/lane/directory contract required')
    for name in OUTPUTS - {'native32', 'native256'}:
        spec = report['outputs'][name]
        if (not isinstance(spec, dict) or not isinstance(spec.get('counts'), dict) or not spec['counts']
                or not isinstance(spec.get('manifest'), dict)
                or spec['manifest'].get('schema') != 'P106B_WRITE_ONCE_SHARDS_V1'
                or not spec['manifest'].get('shards') or spec['manifest'].get('rows', 0) <= 0):
            raise ValueError('every raw-answer lane requires nonempty manifest and counts: ' + name)
    for name in ('native32', 'native256'):
        native = report['outputs'][name]
        if (type(native.get('ce')) not in (int, float) or not math.isfinite(native['ce'])
                or native['ce'] < 0 or native.get('val_sha256') != inputs['native_val_sha256']):
            raise ValueError('native finite CE/source contract differs')
        if name == 'native32':
            if native.get('crops') != 32 or native.get('targets') != 32768:
                raise ValueError('native32 actual denominator differs')
        elif (native.get('windows') != 256 or native.get('targets') != 262144
                or native.get('precision') != 'FP32_MATH'
                or native.get('offsets_sha256') != c.data.sha(inputs['native256_val_offsets'])):
            raise ValueError('native256 actual denominator/precision/offsets differs')


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
            train.deadline()
            v = values[start:start + 1025].astype('int64').tolist()
            x = torch.tensor([v[:-1]], device='cuda'); y = torch.tensor([v[1:]], device='cuda')
            hidden = wrapped(x, return_hidden=True)
            sums, n = core.components(base, hidden, y, torch.ones_like(y), horizons=(), checkpoint_heads=False)
            total += float(sums[1]); count += n[1]
    return dict(ce=total / count, targets=count, windows=256, precision='FP32_MATH',
        val_sha256=inputs['native_val_sha256'], offsets_sha256=c.data.sha(inputs['native256_val_offsets']),
        scope='additional fixed val windows, not whole validation or new unseen text')


def checkpoint_spec(endpoint):
    if endpoint == 'parent': return c.PARENT, c.PARENT_SHA
    report = c.required(c.EVIDENCE / endpoint / 'report.json')
    if (report['status'] != 'TRAIN_COMPLETE_EVALUATION_PENDING' or report['updates'] != 640
            or report['code_sha256'] != c.info()['code_sha256']):
        raise ValueError('complete fixed640 training endpoint required')
    return ROOT / report['checkpoint'], report['checkpoint_sha256']


def evaluate(endpoint, max_wall_sec):
    import torch
    import torch.nn.functional as F
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from scripts import p106b_night_evaluation as method
    from scripts import diag_p106b_authorized_benchmark as public
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    inputs, cases = read_inputs()
    target = EVIDENCE / (endpoint + '_report.json'); directory = LOCAL / endpoint
    if target.exists() or directory.exists(): raise FileExistsError('old endpoint answers preserved')
    cp, identity = checkpoint_spec(endpoint)
    if c.data.digest(cp) != identity: raise ValueError('endpoint checkpoint changed')
    idle_before_gpu(); directory.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter(); outputs = {}
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    with wall_limit(max_wall_sec):
        model, cfg, device = load_model(arch='dense', ckpt_path=str(cp), device='cuda')
        tok = Tokenizer.from_file(str(c.data.TOKENIZER)); initial = train.runtime.state_fingerprint(model)
        torch.cuda.reset_peak_memory_stats(); emit = emit_function(model, cfg, tok)
        with torch.no_grad():
            natural = []; writer = ShardWriter(directory, 'natural')
            for i, pair in enumerate(cases['natural']):
                for view in (0, 1, 2):
                    row = pair['views'][str(view)]; answer, generation = emit(row['messages'][:1])
                    event = dict(root=pair['root'], article_id=pair['article_id'], language=pair['language'], view=view,
                        source_sha256=pair['source_sha256'], question=pair['question'], context=pair['context'],
                        messages=row['messages'][:1],
                        answer=answer, aliases=pair['aliases'], generation=generation,
                        scores=metrics.qa_scores(answer, pair['aliases'], pair['language']))
                    writer.append(event); natural.append(event)
                if (i + 1) % 32 == 0:
                    print('[NIGHT_NATURAL_PROGRESS] ' + json.dumps(dict(endpoint=endpoint, pairs=i + 1, total=len(cases['natural']))), flush=True)
            outputs['natural'] = dict(manifest=writer.close(lineage=info()), counts=method.summarize_natural(natural))
            cube = []; writer = ShardWriter(directory, 'cube')
            for row in cases['cube']:
                answer, generation = emit(row['messages'])
                event = dict(row, answer=answer, generation=generation); writer.append(event); cube.append(event)
            outputs['cube'] = dict(manifest=writer.close(lineage=info()), counts=method.summarize_cube(cube))
            short_emit = emit_function(model, cfg, tok, 64)
            for lane in ('role', 'recovery', 'code'):
                events = []; writer = ShardWriter(directory, lane)
                for row in cases[lane]:
                    for event in dialogue(row, short_emit): writer.append(event); events.append(event)
                outputs[lane] = dict(manifest=writer.close(lineage=info()), counts=summarize_dialogue(events))
                print('[NIGHT_RETENTION] ' + json.dumps(dict(endpoint=endpoint, lane=lane, counts=outputs[lane]['counts'])), flush=True)
            writer = ShardWriter(directory, 'public'); summaries = {}; wrapped = PrecisionForward(model, 'fp32_math')
            for task in (*public.TASKS, 'korquad_free', 'gsm8k_free'):
                rows = [r for r in cases['public'] if r['task'] == task]; scored = []; skips = []
                if task in public.TASKS:
                    for start in range(0, len(rows), 16):
                        train.deadline()
                        block = rows[start:start + 16]
                        res = public.suite.run_mc(task, [r['item'] for r in block], wrapped, tok,
                            device, 1024, torch, F, False)
                        for event in res['rows']:
                            writer.append(dict(event, task=task, kind='mc', skipped=False)); scored.append(event)
                        for event in res['skip_rows']:
                            writer.append(dict(event, task=task, kind='mc', skipped=True)); skips.append(event)
                    summaries[task] = dict(n=len(scored), skipped=len(skips),
                        correct=sum(e['pred_harness'] == e['gold'] for e in scored),
                        prediction_counts=dict(Counter(e['pred_harness'] for e in scored)))
                else:
                    for row in rows:
                        if row['prompt_tokens'] + 128 > 1024:
                            event = dict(task=task, id=row['id'], kind='gen', skipped=True, reason='complete_prompt_budget')
                            skips.append(event); writer.append(event); continue
                        from tinylm.infer.generate import sample
                        output, generation = sample(wrapped, cfg, tok, row['prompt'], max_new=128,
                            temperature=0., top_k=1, device='cuda', use_cache=True, logits_last_only=True,
                            return_metadata=True, stop_token_sequences=[tok.encode('<|im_end|>').ids])
                        prefix = tok.decode(tok.encode(row['prompt']).ids)
                        if not output.startswith(prefix): raise ValueError('public prompt extraction differs')
                        raw_answer = output[len(prefix):].split('<|im_end|>', 1)[0]
                        answer = raw_answer.strip()
                        score = public.answer_scores(answer, row['golds'])
                        if task == 'gsm8k_free': score['numeric_exact'] = int(public.numerical(answer) is not None and public.numerical(answer) == public.numerical(row['golds'][0]))
                        event = dict(task=task, id=row['id'], kind='gen', skipped=False, answer=answer,
                            raw_answer=raw_answer, prompt=row['prompt'], golds=row['golds'], generation=generation, scores=score)
                        writer.append(event); scored.append(event)
                    primary = 'numeric_exact' if task == 'gsm8k_free' else 'whitespace_nfkc_exact'
                    summaries[task] = dict(n=len(scored), skipped=len(skips), correct=sum(e['scores'][primary] for e in scored), primary=primary)
                print('[NIGHT_PUBLIC_TASK] ' + json.dumps(dict(endpoint=endpoint, task=task, **summaries[task])), flush=True)
            outputs['public'] = dict(manifest=writer.close(lineage=info()), counts=summaries)
            outputs['native32'] = train.runtime.native_ce(model, c.NATIVE)
            model.eval(); model.freeze_quant()
            outputs['native256'] = native256(model, inputs, tok)
        if train.runtime.state_fingerprint(model) != initial: raise ValueError('evaluation changed body weights')
        result = dict(info(), status='ACTUAL_EVALUATION_COMPLETE', endpoint=endpoint,
            checkpoint=str(cp.relative_to(ROOT)), checkpoint_sha256=identity, initial_core_sha256=initial,
            body_unchanged=True, checkpoints_written=0, directory=str(directory.relative_to(ROOT)), outputs=outputs,
            input_report_sha256=c.data.digest(FROZEN / 'report.json'),
            whole_seconds=time.perf_counter() - began,
            peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20)
        endpoint_contract(result, endpoint, inputs)
        c.write(target, result)
        print('[NIGHT_ENDPOINT] ' + json.dumps(dict(endpoint=endpoint, whole_seconds=result['whole_seconds'],
            natural=outputs['natural']['counts'], cube=outputs['cube']['counts']), ensure_ascii=False), flush=True)
    del model; gc.collect(); torch.cuda.empty_cache()
    return 0


def readback():
    from scripts import p106b_night_evaluation as method
    from scripts import diag_p106b_authorized_benchmark as public
    inputs, cases = read_inputs(); reports = {}; natural = {}; reconstructed = {}
    for endpoint in ENDPOINTS:
        r = c.required(EVIDENCE / (endpoint + '_report.json'))
        endpoint_contract(r, endpoint, inputs)
        if (r['code_sha256'] != info()['code_sha256'] or not r['body_unchanged']
                or r['input_report_sha256'] != c.data.digest(FROZEN / 'report.json')):
            raise ValueError('same-code, complete immutable endpoint proof required')
        cp, expected = checkpoint_spec(endpoint)
        if r['checkpoint_sha256'] != expected or c.data.digest(cp) != expected:
            raise ValueError('post-evaluation checkpoint identity changed')
        recount = {}; directory = ROOT / r['directory']
        for lane, spec in r['outputs'].items():
            if lane in ('native32', 'native256'): continue
            if 'manifest' not in spec: raise ValueError('missing raw lane manifest')
            events = list(stream(directory, spec['manifest']))
            if lane == 'natural':
                expected_cases = {(p['root'], v): p for p in cases['natural'] for v in (0, 1, 2)}
                if {(e['root'], e['view']) for e in events} != set(expected_cases): raise ValueError('natural case IDs incomplete')
                for e in events:
                    original = expected_cases[(e['root'], e['view'])]
                    if any(e[k] != original[k] for k in ('article_id', 'language', 'aliases', 'source_sha256', 'question', 'context')):
                        raise ValueError('natural original/gold changed')
                    from tinylm.chat.serialize import serialize
                    messages = original['views'][str(e['view'])]['messages'][:1]
                    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
                    if (e['messages'] != messages or e['generation']['actual_prompt_sha256'] != c.data.sha(prompt)
                            or e['generation']['raw_answer_sha256'] != c.data.sha(e['answer'])):
                        raise ValueError('natural actual prompt/output identity differs')
                actual = method.summarize_natural(events); natural[endpoint] = events
            elif lane == 'cube': actual = method.summarize_cube(events)
            elif lane in ('role', 'recovery', 'code'): actual = verify_dialogue_rows(events, cases[lane])
            else: actual = public_recount(events, cases['public'])
            if actual != spec['counts']: raise ValueError('raw recount differs: ' + endpoint + '/' + lane)
            recount[lane] = actual
        reports[endpoint] = c.data.digest(EVIDENCE / (endpoint + '_report.json')); reconstructed[endpoint] = recount
    pairs = {a + '__' + b: method.paired_natural(natural[a], natural[b])
             for a, b in (('parent', 'ce'), ('parent', 'consistent'), ('ce', 'consistent'))}
    c.write(EVIDENCE / 'paired_readback.json', dict(info(), status='RAW_RECOUNTED', errors=0,
        endpoint_reports_sha256=reports, reconstructed=reconstructed, paired= pairs,
        scope='fixed articles and one learning seed; no family-wide adoption or multiplicity adjustment'))
    print('[NIGHT_READBACK] ' + json.dumps(pairs, ensure_ascii=False), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('freeze', 'evaluate', 'readback'), required=True)
    p.add_argument('--endpoint', choices=ENDPOINTS)
    p.add_argument('--max-wall-sec', type=int, default=7200)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute', action='store_true'); g.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    if a.check_only: print('[NIGHT_EVAL_CHECK] ' + json.dumps(info())); return 0
    if a.mode == 'evaluate' and a.endpoint is None: p.error('explicit endpoint required')
    try:
        train.deadline()
        if a.mode == 'freeze': return prepare()
        if a.mode == 'readback': return readback()
        remaining = int((c.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds())
        if remaining < 60: raise RuntimeError('final documentation hour reserved')
        return evaluate(a.endpoint, min(a.max_wall_sec, remaining))
    except KeyboardInterrupt:
        print('[NIGHT_EVAL_INTERRUPTED] partial raw preserved'); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[NIGHT_EVAL_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
