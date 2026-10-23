#!/usr/bin/env python3
"""Fixed new public MC768; orchestration only, not official BabyLM.

prepare reads pinned local public sources and writes a NEW source-only packet.
check-only reads code/arguments, never datasets/tokenizers/weights/torch.
evaluate requires --execute and a current aware deadline. Only that mode enters
the unchanged strict UI loader and existing literal adapters/NLL scorer.
Different questions with unchanged weights are NOT a training improvement;
cached Falcon scores on the old questions are not a direct comparison.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import copy
from datetime import datetime, timezone
import importlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p106b_minimal_pair_benchmark as common
from scripts.p106b_shards import ShardWriter, verify

SCHEMA = 'P106B_PUBLIC_MC_EXTENSION_V1'
MODELS = ('native595-f', 'native595-q', 'new595-broad-f')
TASKS = ('piqa', 'hellaswag', 'arc_easy')
SEED, COUNT, CONTEXT, CHUNK, LIMIT = 20261022, 256, 1024, 32, 19_999_999
AUTHORIZED_END = datetime(2026, 10, 22, 8, tzinfo=timezone.utc)
OLD_REPORT = 'HF/sft_ready/p106b_authorized_validation_v1_s1337/public_benchmark/report.json'
OLD_REPORT_SHA = 'A2D57C8E2A8F767EBA4D679A1660AB2A85A0B756A713FB0196D013DFB2E3A926'
SOURCE_PINS = {
    'piqa': (1838, '61533005E22F175534909B1EC8EACB6DA03C233933558D1BAFB15787453B1F55'),
    'hellaswag': (10042, 'D5C08C3E5771307E73886DC9D2744DF8CA5F372A7857F32FE77DF8C58942F950'),
    'arc_easy': (2376, '874354CF372667530BD6CBD2D78DCA2D657C5E2E746F53CF01D1E9D3A90CBC3D'),
}
IDS_SHA = 'B53F6B3430BB376E91AA3859F9266888C72320DB5F85ABA5256AABF29C9AF5D5'
PACKET_SHA = '660CD423BE22905F325405FBBEE471F0DFF9C06424DE5B2DFFCDD98BF5DB2AB2'
SELECTION_SHA = 'E127C90A0DDA31CA6EC608C50A93B65ACA8C344A89D99CC9E404382A5BB9D763'
KNOWN_BASELINES = dict(old_label_majority_correct=266, shortest_character_correct=272,
    longest_character_correct=245, new_label_majority_oracle_correct=283, candidate_forwards=2559)
CODE = ('scripts/p106b_public_mc_extension.py', 'scripts/test_p106b_public_mc_extension.py',
    'scripts/p106b_minimal_pair_benchmark.py', 'scripts/p106b_shards.py',
    'scripts/interactive_research_infer.py', 'scripts/diag_p106b_current_benchmark.py',
    'scripts/diag_p101a_mtp_parity.py', 'scripts/eval_bench_suite.py', 'scripts/p106b_gate_runtime.py')


def body(task, row):
    text = (row['goal'] if task == 'piqa' else row['question'] if task == 'arc_easy'
        else row['ctx_a'] + ' ' + row['ctx_b'].capitalize() if row.get('ctx_b') else row['ctx'])
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).strip().casefold()


def case_id(row): return row['task'] + '#' + str(row['index'])


def select_packet(sources, old_sources, count=COUNT, seed=SEED):
    """Source-only selection; no golds, tokenizer, predictions or models used."""
    blocked = {body(t, sources[t][i]) for t in TASKS for i in old_sources[t]['indices']}
    seen = set(blocked); packet = []; exclusions = {}
    for task in TASKS:
        old = set(old_sources[task]['indices'])
        complement = [i for i in range(len(sources[task])) if i not in old]
        eligible = [i for i in complement if body(task, sources[task][i]) not in blocked]
        order = eligible[:]; random.Random(seed).shuffle(order); chosen = []
        for index in order:
            key = body(task, sources[task][index])
            if key in seen: continue
            chosen.append(index); seen.add(key)
            if len(chosen) == count: break
        if len(chosen) != count: raise ValueError('insufficient unique new question/context bodies')
        packet.extend(dict(task=task, index=i, source_row=copy.deepcopy(sources[task][i])) for i in sorted(chosen))
        exclusions[task] = dict(old_index_excluded=len(old), old_body_extra_excluded=len(complement) - len(eligible),
            remaining_rows=len(eligible), remaining_unique_bodies=len({body(task, sources[task][i]) for i in eligible}))
    if len({case_id(r) for r in packet}) != len(packet): raise ValueError('duplicate selected ID')
    selected_bodies = [body(r['task'], r['source_row']) for r in packet]
    if len(set(selected_bodies)) != len(packet) or set(selected_bodies) & blocked:
        raise ValueError('old/new normalized-context overlap')
    return packet, exclusions


def receipts(paths, root=ROOT):
    return {p: dict(bytes=common.safe_path(p, root).stat().st_size,
        sha256=common.file_sha(common.safe_path(p, root))) for p in paths}


def unchanged(expected, root=ROOT):
    if receipts(expected, root) != expected: raise ValueError('pinned source/code/prepared bytes changed')


def read_jsonl(path):
    rows = []
    with Path(path).open('rb') as stream:
        while True:
            line = stream.readline(LIMIT + 1)
            if not line: break
            if not line.strip() or len(line) > LIMIT: raise ValueError('blank/oversized JSONL record')
            rows.append(json.loads(line.decode('utf-8'), object_pairs_hook=common._unique_object))
    return rows


def source_material(root=ROOT):
    paths = [OLD_REPORT, *('datasets/bench/' + t + '.jsonl' for t in TASKS)]
    before = receipts(paths, root)
    if before[OLD_REPORT]['sha256'] != OLD_REPORT_SHA: raise ValueError('old selection report bytes differ')
    old = json.loads(common.safe_path(OLD_REPORT, root).read_text(encoding='utf-8'), object_pairs_hook=common._unique_object)
    sources = {}
    for task in TASKS:
        path = 'datasets/bench/' + task + '.jsonl'; expected_n, expected_sha = SOURCE_PINS[task]
        if before[path]['sha256'] != expected_sha: raise ValueError('public source bytes differ: ' + task)
        sources[task] = read_jsonl(common.safe_path(path, root)); spec = old['sources'][task]
        if (len(sources[task]) != expected_n or spec['path'] != path or spec['rows'] != expected_n
                or spec['sha256'].upper() != expected_sha or len(spec['indices']) != COUNT
                or len(set(spec['indices'])) != COUNT
                or any(type(i) is not int or not 0 <= i < expected_n for i in spec['indices'])):
            raise ValueError('old source/index lineage differs')
    packet, exclusions = select_packet(sources, old['sources'], COUNT, SEED)
    ids = [case_id(r) for r in packet]
    selection = dict(schema='P106B_PUBLIC_NEW768_SELECTION_AUDIT_V1', seed=SEED, task_order=list(TASKS),
        source_sha256={t: SOURCE_PINS[t][1].lower() for t in TASKS},
        indices={t: [r['index'] for r in packet if r['task'] == t] for t in TASKS})
    if (len(packet) != COUNT * len(TASKS) or common.sha(ids) != IDS_SHA
            or common.sha(packet) != PACKET_SHA or common.sha(selection) != SELECTION_SHA):
        raise ValueError('audit-fixed new768 selection/object hashes differ')
    unchanged(before, root)
    return packet, sources, old, dict(source_receipts=before, ordered_ids_sha256=IDS_SHA,
        logical_source_packet_sha256=PACKET_SHA, logical_selection_sha256=SELECTION_SHA,
        exclusions=exclusions, old_id_overlap=0, old_normalized_context_overlap=0, new_context_duplicates=0)


def output_path(value, root=ROOT):
    path = common.safe_path(value, root); relative = path.relative_to(Path(root).absolute())
    if relative.parts[:2] != ('test_result', 'evidence') and relative.parts[0] != 'data_cache':
        raise ValueError('new artifacts belong in test_result/evidence or data_cache only')
    if path.exists(): raise FileExistsError('existing prepared/evaluation output preserved')
    return path


def prepare(output, root=ROOT):
    output = output_path(output, root); pins = receipts(CODE, root)
    packet, _, _, proof = source_material(root)
    output.mkdir(parents=True, exist_ok=False); writer = ShardWriter(output, 'cases', limit=LIMIT)
    for row in packet: writer.append(row)
    manifest = writer.close(lineage=proof); verify(output, manifest)
    unchanged(proof['source_receipts'], root); unchanged(pins, root)
    report = dict(schema=SCHEMA, status='PUBLIC_MC_NEW768_PREPARED_CPU_SOURCE_ONLY',
        proof=proof, code_receipts=pins, raw_manifest=manifest, requested=len(packet),
        actual_jsonl_concat_sha256=manifest['concat_sha256'],
        actual_manifest_file_sha256=common.file_sha(output / 'cases_shards_manifest.json'),
        tokenizer_eligibility='NOT_RUN', model_loads=0, checkpoint_tensor_loads=0,
        official_babylm=False, training_improvement_claim=False)
    common.atomic_json(output / 'report.json', report)
    return report


def load_prepared(directory, expected_packet, expected_proof, root=ROOT):
    directory = common.safe_path(directory, root)
    report_path = common.safe_path(directory / 'report.json', root)
    report = json.loads(report_path.read_text(encoding='utf-8'), object_pairs_hook=common._unique_object)
    manifest_path = common.safe_path(directory / 'cases_shards_manifest.json', root)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (report.get('schema') != SCHEMA or report.get('status') != 'PUBLIC_MC_NEW768_PREPARED_CPU_SOURCE_ONLY'
            or report.get('proof') != expected_proof or report.get('raw_manifest') != manifest
            or report.get('code_receipts') != receipts(CODE, root)
            or manifest.get('lineage') != expected_proof
            or report.get('actual_jsonl_concat_sha256') != manifest.get('concat_sha256')
            or report.get('actual_manifest_file_sha256') != common.file_sha(manifest_path)):
        raise ValueError('prepared source/manifest lineage differs')
    verify(directory, manifest); actual = []
    for spec in manifest['shards']:
        actual.extend(read_jsonl(common.safe_path(directory / spec['path'], root)))
    if actual != expected_packet or common.sha(actual) != PACKET_SHA: raise ValueError('prepared source packet differs')
    paths = [report_path, manifest_path, *(directory / s['path'] for s in manifest['shards'])]
    return receipts([str(p.relative_to(Path(root).absolute())) for p in paths], root)


def adapt_plans(packet, sources, old, adapters, tokenizer):
    majorities = {}
    for task in TASKS:
        counts = Counter(adapters[task](sources[task][i])['gold'] for i in old['sources'][task]['indices'])
        majorities[task] = min(counts, key=lambda k: (-counts[k], k))
    plans = []
    for row in packet:
        item = adapters[row['task']](copy.deepcopy(row['source_row'])); item['_iid'] = case_id(row)
        if (set(item) != {'ctx', 'choices', 'gold', '_iid'} or not isinstance(item['ctx'], str)
                or not isinstance(item['choices'], list) or len(item['choices']) < 2
                or any(not isinstance(c, str) for c in item['choices'])
                or type(item['gold']) is not int or not 0 <= item['gold'] < len(item['choices'])):
            raise ValueError('literal MC adapter shape/gold differs')
        prefix = tokenizer.encode(item['ctx']).ids if item['ctx'] else tokenizer.encode('\n').ids[:1]
        continuations = [list(tokenizer.encode(c).ids) for c in item['choices']]
        if not prefix: raise ValueError('empty prompt/fallback encoding')
        reason = ('empty_continuation' if any(not c.strip() for c in item['choices']) or any(not ids for ids in continuations)
            else 'seq_max_exceeded' if any(len(prefix) + len(ids) > CONTEXT for ids in continuations) else None)
        lengths = [len(c) for c in item['choices']]; gold = item['gold']
        shortest = min(range(len(lengths)), key=lambda k: lengths[k])
        longest = max(range(len(lengths)), key=lambda k: lengths[k])
        base = dict(random_expected_correct=1 / len(lengths), old_label_majority_prediction=majorities[row['task']],
            old_label_majority_correct=int(majorities[row['task']] == gold),
            shortest_character_prediction=shortest, shortest_character_correct=int(shortest == gold),
            longest_character_prediction=longest, longest_character_correct=int(longest == gold),
            shortest_character_tie=sum(n == min(lengths) for n in lengths) > 1,
            longest_character_tie=sum(n == max(lengths) for n in lengths) > 1)
        plans.append(dict(id=case_id(row), source=copy.deepcopy(row), item=item,
            encoding=dict(prefix_ids=list(prefix), continuation_ids=continuations), reason=reason, baseline=base))
    return plans


def score_diagnostics(scores, plan):
    item = plan['item']; counts = [len(x) for x in plan['encoding']['continuation_ids']]
    chars = [max(1, len(c)) for c in item['choices']]; n = len(counts)
    if (scores.get('id') != plan['id'] or scores.get('gold') != item['gold']
            or scores.get('n_tokens') != counts or scores.get('n_chars') != chars):
        raise ValueError('literal score identity/token/character counts differ')
    for field in ('sum_nll', 'mean_nll', 'score'):
        values = scores.get(field)
        if (not isinstance(values, list) or len(values) != n
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
            raise ValueError('missing/nonfinite candidate scores')
    primary = min(range(n), key=lambda k: scores['sum_nll'][k])
    mean = min(range(n), key=lambda k: scores['mean_nll'][k])
    char = min(range(n), key=lambda k: scores['sum_nll'][k] / chars[k])
    if (scores.get('pred_harness') != primary or scores.get('pred_harness_norm') != char
            or scores.get('pred_internal') != mean or scores.get('score') != scores['mean_nll']):
        raise ValueError('SUM_NLL primary/mean/character or no-PMI contract differs')
    return dict(primary_correct=int(primary == item['gold']), mean_correct=int(mean == item['gold']),
        character_normalized_correct=int(char == item['gold']),
        sum_nll_tie=sum(v == min(scores['sum_nll']) for v in scores['sum_nll']) > 1,
        ties='literal first index; ties reported, primary not redefined')


def summarize(events, plans):
    if [e['id'] for e in events] != [p['id'] for p in plans]: raise ValueError('missing/duplicate/reordered cases')
    tasks = {}; asked_baselines = Counter(); eligible_baselines = Counter()
    for event, plan in zip(events, plans):
        if (event['source'] != plan['source'] or event['item'] != plan['item']
                or event['encoding'] != plan['encoding'] or event['baseline'] != plan['baseline']
                or event['reason'] != plan['reason']): raise ValueError('raw case/source/encoding mutation')
        for key, value in plan['baseline'].items():
            if key.endswith('_correct') or key.endswith('_tie'): asked_baselines[key] += value
        cell = tasks.setdefault(plan['source']['task'], dict(asked=0, scored=0, correct=0,
            mean_correct=0, character_normalized_correct=0, sum_nll_ties=0, skip_reasons=Counter()))
        cell['asked'] += 1
        if plan['reason'] is not None:
            if event['scores'] is not None or event['diagnostics'] is not None: raise ValueError('ineligible case received scores')
            cell['skip_reasons'][plan['reason']] += 1; continue
        diagnostic = score_diagnostics(event['scores'], plan)
        if event['diagnostics'] != diagnostic: raise ValueError('diagnostic does not recount')
        for key, value in plan['baseline'].items():
            if key.endswith('_correct') or key.endswith('_tie'): eligible_baselines[key] += value
        cell['scored'] += 1; cell['correct'] += diagnostic['primary_correct']
        cell['mean_correct'] += diagnostic['mean_correct']; cell['character_normalized_correct'] += diagnostic['character_normalized_correct']
        cell['sum_nll_ties'] += diagnostic['sum_nll_tie']
    oracle = sum(max(Counter(p['item']['gold'] for p in plans if p['source']['task'] == t).values()) for t in tasks)
    asked_baselines['new_label_majority_oracle_correct'] = oracle
    asked_baselines['candidate_forwards'] = sum(len(p['item']['choices']) for p in plans)
    for cell in tasks.values():
        cell['accuracy'] = cell['correct'] / cell['scored'] if cell['scored'] else None
        cell['skip_reasons'] = dict(cell['skip_reasons'])
    scored = sum(c['scored'] for c in tasks.values()); correct = sum(c['correct'] for c in tasks.values())
    return dict(asked=len(plans), scored=scored, excluded=len(plans) - scored, correct=correct,
        accuracy=correct / scored if scored else None, by_task=tasks,
        asked_baselines=dict(asked_baselines), eligible_baselines=dict(eligible_baselines),
        oracle_scope='new gold-label majority diagnostic only; not an acceptance criterion or fixed predictor',
        length_scope='adapter continuation characters; first-index ties; token-length not substituted',
        official_babylm=False, training_improvement_claim=False, direct_cached_falcon_comparison=False)


class Budget:
    def __init__(self, seconds, deadline, *, now=None, clock=None):
        self.now = now or (lambda: datetime.now(timezone.utc)); self.clock = clock or time.perf_counter
        self.seconds, self.deadline, self.started = seconds, deadline, self.clock()
        self.check()

    def check(self):
        if self.now() >= self.deadline or self.clock() - self.started >= self.seconds:
            raise TimeoutError('current aware deadline/model-batch wall cap reached')

    def elapsed(self): return self.clock() - self.started


class ForwardCounter:
    """Count actual literal-scorer forward attempts/completions, not estimates."""
    def __init__(self, model, route, budget):
        self.model, self.route, self.budget = model, route, budget
        self.attempted = self.completed = 0

    def __call__(self, x, *args, **kwargs):
        self.budget.check(); self.route.assert_active()
        if tuple(x.shape)[0] != 1: raise ValueError('literal scorer must forward exactly one candidate at a time')
        self.attempted += 1
        value = self.model(x, *args, **kwargs); self.completed += 1
        self.budget.check(); return value


def collect(output, plans, lineage, score_one, counter, budget, chunk=CHUNK):
    if lineage.get('plans_sha256') != common.sha(plans): raise ValueError('plans were not frozen before scoring')
    plan_hashes = [common.sha(p) for p in plans]
    writer = ShardWriter(output, 'answers', limit=LIMIT); events = []; progress = []; chunk_start = budget.elapsed()
    try:
        for index, plan in enumerate(plans):
            budget.check(); start = counter.completed; tick = budget.elapsed()
            scores = None if plan['reason'] else score_one(plan)
            if common.sha(plan) != plan_hashes[index]: raise ValueError('scorer mutated source/adapter/encoding plan')
            expected = 0 if plan['reason'] else len(plan['item']['choices'])
            if counter.completed - start != expected: raise ValueError('actual candidate forward count differs')
            event = dict(copy.deepcopy(plan), scores=scores, diagnostics=None if plan['reason'] else score_diagnostics(scores, plan),
                lineage_sha256=common.sha(lineage), forward_start=start, forward_end=counter.completed,
                score_seconds=budget.elapsed() - tick)
            writer.append(event); events.append(event)
            if (index + 1) % chunk == 0 or index + 1 == len(plans):
                moment = budget.elapsed()
                receipt = dict(cases=len(events), requested=len(plans), whole_seconds=moment,
                    chunk_seconds=moment - chunk_start,
                    forward_attempted=counter.attempted, forward_completed=counter.completed)
                progress.append(receipt); chunk_start = moment
                # Existing writer owns formatting/sharding. Flush its current
                # shard before exposing the prefix as measured/admitted.
                if writer._file is not None:
                    writer._file.flush(); os.fsync(writer._file.fileno())
                print('[PUBLIC_MC_CHUNK] ' + json.dumps(receipt), flush=True)
        manifest = writer.close(lineage=dict(signature=common.sha(lineage), status='RAW_COMPLETE_STRICT_EXIT_PENDING'))
        verify(output, manifest); summary = summarize(events, plans)
        if not summary['scored']: raise ValueError('no eligible cases; undefined denominator, not zero accuracy')
        if any(summary['asked_baselines'].get(k) != v for k, v in KNOWN_BASELINES.items()):
            raise ValueError('audit-fixed candidate budget/baselines differ')
        if counter.completed != sum(len(p['item']['choices']) for p in plans if p['reason'] is None):
            raise ValueError('whole-batch actual forward count differs')
        return dict(schema=SCHEMA, status='RAW_COMPLETE_STRICT_EXIT_PENDING', lineage=lineage,
            signature=common.sha(lineage), raw_manifest=manifest, summary=summary, progress=progress,
            forward_attempted=counter.attempted, forward_completed=counter.completed), events
    except BaseException:
        if writer._total_rows and not writer.manifest_path.exists():
            writer.close(lineage=dict(signature=common.sha(lineage), status='INCOMPLETE'))
        raise


def dependencies(root=ROOT):
    ui = importlib.import_module('scripts.interactive_research_infer')
    numerical = importlib.import_module('scripts.diag_p106b_current_benchmark')
    suite = importlib.import_module('scripts.eval_bench_suite')
    for module, path in ((ui, 'scripts/interactive_research_infer.py'),
            (numerical, 'scripts/diag_p106b_current_benchmark.py'), (suite, 'scripts/eval_bench_suite.py')):
        if Path(module.__file__).absolute() != common.safe_path(path, root): raise ValueError('import source-root differs')
    from scripts.p106b_gate_runtime import wall_limit
    import torch.nn.functional as F
    return ui, suite, numerical.FP32Forward, F, wall_limit


def parse_deadline(value, now=None):
    try: deadline = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, ValueError): raise ValueError('explicit ISO aware --deadline required')
    if deadline.tzinfo is None or deadline.utcoffset() is None: raise ValueError('naive deadline refused')
    now = now or datetime.now(timezone.utc)
    if not now < deadline <= AUTHORIZED_END: raise ValueError('expired/out-of-current-authorization deadline')
    return deadline


def evaluate(args, root=ROOT):
    if (not getattr(args, 'execute', False) or args.model not in MODELS
            or type(args.max_wall_sec) is not int or not 60 <= args.max_wall_sec <= 21600):
        raise ValueError('explicit execute, fixed model and bounded wall cap required')
    deadline = parse_deadline(args.deadline); budget = Budget(args.max_wall_sec, deadline)
    output = output_path(args.output, root); result = events = counter = None; strict_exit = False
    packet, sources, old, proof = source_material(root)
    prepared = load_prepared(args.input, packet, proof, root); pins = receipts(CODE, root)
    ui, suite, forward, F, wall_limit = dependencies(root)
    timeout = min(args.max_wall_sec, int((deadline - datetime.now(timezone.utc)).total_seconds()))
    if timeout < 60: raise TimeoutError('less than60 seconds admission reserve; model not opened')
    output.mkdir(parents=True, exist_ok=False)
    try:
        with wall_limit(timeout):
            budget.check()
            with ui.selected_runtime(ui.resolve_model(args.model), root=root) as active:
                budget.check()
                if (active['name'] != args.model or active['precision'] != 'FP32_MATH'
                        or active['tokenizer_sha256'] != ui.TOKENIZER_SHA or active['cfg'].max_seq_len != CONTEXT
                        or active['quantization_route']['mode'] != ('ternary' if args.model.endswith('-q') else 'float')):
                    raise ValueError('actual endpoint/tokenizer/precision/context/QF route differs')
                plans = adapt_plans(packet, sources, old, suite.ADAPTERS, active['tokenizer'])
                lineage = dict(schema=SCHEMA, model=args.model, checkpoint=active['checkpoint'],
                    checkpoint_sha256=active['checkpoint_sha256'], core_sha256=active['core_sha256'],
                    tokenizer_sha256=active['tokenizer_sha256'], model_report_sha256=active['report_sha256'],
                    model_manifest_sha256=active['manifest_sha256'], quantization_route=copy.deepcopy(active['quantization_route']),
                    source_proof=proof, prepared_receipts=prepared, code_receipts=pins,
                    plans_sha256=common.sha(plans), precision='FP32_MATH_TF32_OFF', context=CONTEXT,
                    primary='SUM_NLL pred_harness; no PMI; first-index ties', max_wall_sec=args.max_wall_sec,
                    deadline=deadline.isoformat(), source_root=str(Path(root).absolute()),
                    model_training=False, checkpoint_writes=0, official_babylm=False)
                counter = ForwardCounter(forward(active['model']), active['route'], budget)
                def score_one(plan):
                    value = suite.run_mc(plan['source']['task'], [plan['item']], counter,
                        active['tokenizer'], 'cuda', CONTEXT, active['torch'], F, True)
                    if (value.get('skip_rows') or len(value.get('rows', [])) != 1
                            or value.get('h_ok') != [int(value['rows'][0]['pred_harness'] == plan['item']['gold'])]):
                        raise ValueError('literal MC row/h_ok/eligibility differs')
                    return value['rows'][0]
                result, events = collect(output, plans, lineage, score_one, counter, budget)
            strict_exit = True; budget.check()
            unchanged(proof['source_receipts'], root); unchanged(prepared, root); unchanged(pins, root)
            actual_manifest = json.loads((output / 'answers_shards_manifest.json').read_text(encoding='utf-8'))
            if actual_manifest != result['raw_manifest']: raise ValueError('raw manifest changed before publication')
            verify(output, actual_manifest); stored = []
            for spec in actual_manifest['shards']: stored.extend(read_jsonl(output / spec['path']))
            if stored != events or summarize(stored, plans) != result['summary']: raise ValueError('stored raw recount differs')
            budget.check()
            result.update(status='PUBLIC_MC_NEW768_COMPLETE', strict_context_exit_verified=True,
                whole_seconds=budget.elapsed(), model_training=False, optimizer_updates=0,
                checkpoint_writes=0, official_babylm=False, training_improvement_claim=False,
                direct_cached_falcon_comparison=False)
            common.atomic_json(output / 'report.json', result)
    except BaseException as exc:
        if not (output / 'error.json').exists():
            common.atomic_json(output / 'error.json', dict(schema=SCHEMA, status='INCOMPLETE',
                error_type=type(exc).__name__, message=str(exc), strict_context_exit_verified=strict_exit,
                forward_attempted=counter.attempted if counter else 0, forward_completed=counter.completed if counter else 0,
                whole_seconds=budget.elapsed(),
                partial_raw='completed-row shards preserved if any; failing row may not have returned scores',
                successful_completion_report=False))
        raise
    print('[PUBLIC_MC_NEW768] ' + json.dumps(result['summary'], ensure_ascii=False), flush=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'check-only', 'evaluate'))
    parser.add_argument('--source-root', default=str(ROOT)); parser.add_argument('--input')
    parser.add_argument('--output'); parser.add_argument('--model', choices=MODELS)
    parser.add_argument('--max-wall-sec', type=int); parser.add_argument('--deadline')
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args(argv)
    if Path(args.source_root).absolute() != ROOT or Path(args.source_root).is_symlink(): parser.error('source-root must be this literal repository root')
    if args.mode == 'evaluate':
        if not all((args.execute, args.input, args.output, args.model, args.max_wall_sec, args.deadline)):
            parser.error('evaluate requires --execute/--input/--output/--model/--max-wall-sec/aware --deadline')
    elif args.execute: parser.error('--execute is exclusive to evaluate')
    if args.max_wall_sec is not None and not 60 <= args.max_wall_sec <= 21600: parser.error('wall cap60..21600 required')
    if args.mode == 'prepare' and (not args.output or args.input or args.model or args.deadline or args.max_wall_sec):
        parser.error('prepare requires only a new --output and optional literal --source-root')
    try:
        if args.deadline: parse_deadline(args.deadline)
        if args.mode == 'check-only':
            for path in CODE: ast.parse(common.safe_path(path).read_text(encoding='utf-8'), filename=path)
            for value in (args.input, args.output):
                if value: common.safe_path(value)
            print('[PUBLIC_MC_CODE_ONLY] ' + json.dumps(dict(schema=SCHEMA, code_receipts=receipts(CODE),
                source_validation='NOT_RUN', asset_opens=0, model_loads=0, torch_imports=0, gpu_calls=0, writes=0)))
        elif args.mode == 'prepare': print('[PUBLIC_MC_PREPARED] ' + json.dumps(prepare(args.output), ensure_ascii=False))
        else: evaluate(args)
        return 0
    except KeyboardInterrupt: return 130
    except Exception as exc:
        print('[PUBLIC_MC_ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
