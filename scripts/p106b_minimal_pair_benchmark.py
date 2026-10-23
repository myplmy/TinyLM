#!/usr/bin/env python3
"""Experimental local minimal pairs; no downloads or official BabyLM claim.

Only --execute enters the existing strict CUDA research loader. Import/help
and --check-only never import torch, open weights or start a model. Inputs are
local UTF-8 JSONL with pair_id, phenomenon, sentence_good, sentence_bad, source,
split. This code does not establish the linguistic validity of those labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts.p106b_shards import ShardWriter, verify

SCHEMA = 'P106B_EXPERIMENTAL_MINIMAL_PAIR_V1'
MODELS = ('native595-f', 'native595-q', 'new595-broad-f')
FIELDS = ('pair_id', 'phenomenon', 'sentence_good', 'sentence_bad', 'source', 'split')
LIMIT = 19_999_999
CODE = ('scripts/p106b_minimal_pair_benchmark.py', 'scripts/test_p106b_minimal_pair_benchmark.py',
        'scripts/eval_bench_suite.py', 'scripts/diag_p106b_current_benchmark.py',
        'scripts/interactive_research_infer.py', 'scripts/p106b_shards.py')


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1 << 20), b''): digest.update(part)
    return digest.hexdigest().upper()


def safe_path(path, root=ROOT):
    root = Path(root).absolute(); path = Path(path)
    path = path if path.is_absolute() else root / path
    if '..' in path.parts: raise ValueError('unresolved parent traversal')
    try: relative = path.relative_to(root)
    except ValueError: raise ValueError('explicit local repository paths required')
    if (not relative.parts or any(p in ('.claude', '.codex', '.agents', '.aws', '.git') for p in relative.parts)
            or relative.parts[:2] == ('datasets', 'TinyDataset')):
        raise ValueError('protected/environment paths are outside this benchmark')
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise ValueError('linked input/output ancestor refused')
        if parent == root: break
    return path


def _unique_object(items):
    result = {}
    for key, value in items:
        if key in result: raise ValueError('duplicate JSON object field: ' + key)
        result[key] = value
    return result


def validate_pairs(rows):
    if not isinstance(rows, list) or not rows: raise ValueError('nonempty local pair dataset required')
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != set(FIELDS)
                or any(not isinstance(row[k], str) or not row[k].strip() for k in FIELDS)):
            raise ValueError('exact six nonempty string fields required')
        if row['pair_id'] in seen: raise ValueError('duplicate pair_id')
        if row['sentence_good'] == row['sentence_bad']: raise ValueError('identical candidates are not a pair')
        seen.add(row['pair_id'])
    return True


def read_dataset(path, root=ROOT):
    path = safe_path(path, root)
    rows = []; digest = hashlib.sha256()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        while True:
            line = stream.readline(LIMIT + 1)
            if not line: break
            if len(line) > LIMIT or not line.strip(): raise ValueError('blank or oversized JSONL row')
            digest.update(line)
            rows.append(json.loads(line.decode('utf-8'), object_pairs_hook=_unique_object))
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if stamp(before) != stamp(after) or stamp(after) != stamp(path.stat()):
        raise ValueError('source changed while reading')
    validate_pairs(rows)
    return rows, dict(path=str(path.relative_to(Path(root).absolute())), bytes=after.st_size,
        sha256=digest.hexdigest().upper(), ordered_pairs_sha256=sha(rows), pairs=len(rows),
        label_validity='CALLER_SUPPLIED_EXPERIMENTAL_NOT_LINGUISTICALLY_CERTIFIED')


def _ids(values, vocab):
    if (not isinstance(values, (list, tuple)) or not values
            or any(type(v) is not int or not 0 <= v < vocab for v in values)):
        raise ValueError('nonempty in-vocabulary integer token sequence required')
    return list(values)


def protocol(tokenizer, bos_policy='newline', bos_token='<bos>', seq_max=1024):
    vocab = tokenizer.get_vocab_size()
    if type(vocab) is not int or vocab < 2 or type(seq_max) is not int or seq_max < 2:
        raise ValueError('actual vocabulary and context sizes required')
    if bos_policy == 'newline':
        prefix = _ids(tokenizer.encode('\n').ids, vocab)[:1]
    elif bos_policy == 'tokenizer_bos':
        token = tokenizer.token_to_id(bos_token)
        if type(token) is not int: raise ValueError('MISSING_BOS: no fallback or vocabulary extension allowed')
        prefix = _ids([token], vocab)
    else: raise ValueError('explicit newline or tokenizer_bos policy required')
    return dict(schema=SCHEMA, bos_policy=bos_policy, bos_token=bos_token if bos_policy == 'tokenizer_bos' else None,
        prefix_ids=prefix, vocab_size=vocab, seq_max=seq_max, eos_scored=False, chatml=False,
        tokenization='explicit prefix IDs + separately encoded complete sentence; no truncation',
        primary='strict good_logp_sum > bad_logp_sum; exact ties counted separately and not correct',
        secondary='mean token CE only; never substitute for primary', precision='FP32_MATH_TF32_OFF',
        official_babylm_equivalence=False, semantics='EXPERIMENTAL_PENDING_SOURCE_AND_ROOT_REVIEW')


def prepare_pairs(rows, tokenizer, metric):
    validate_pairs(rows); plans = []
    for row in rows:
        good = _ids(tokenizer.encode(row['sentence_good']).ids, metric['vocab_size'])
        bad = _ids(tokenizer.encode(row['sentence_bad']).ids, metric['vocab_size'])
        if good == bad: raise ValueError('distinct strings collapsed to identical candidate token IDs')
        length = max(len(good), len(bad)) + len(metric['prefix_ids'])
        plans.append(dict(pair=copy.deepcopy(row), pair_sha256=sha(row),
            prefix_ids=list(metric['prefix_ids']), good_ids=good, bad_ids=bad,
            skipped=length > metric['seq_max'],
            reason='complete_sentence_exceeds_context' if length > metric['seq_max'] else None))
    if all(p['skipped'] for p in plans): raise ValueError('zero scoreable pairs; not a successful benchmark')
    return plans


def _decision(good, bad):
    return dict(correct=int(good > bad), ties=int(good == bad), incorrect=int(good < bad))


def baseline_bundle(plans, source, tokenizer_sha, metric):
    counts = Counter(v for p in plans for key in ('good_ids', 'bad_ids') for v in p[key])
    total = sum(counts.values()); denominator = total + metric['vocab_size']
    specification = dict(schema=SCHEMA, source=source, tokenizer_sha256=tokenizer_sha,
        protocol=metric, encoded_pairs_sha256=sha(plans),
        unigram='add-one token counts from BOTH evaluation candidates, symmetrically; transductive non-LM reference',
        unigram_total_tokens=total, unigram_vocabulary=metric['vocab_size'],
        length='shorter token sequence / shorter Unicode string; ties separate', code_version=SCHEMA)
    records = []
    for plan in plans:
        row = plan['pair']
        logp = [math.fsum(n * math.log((counts[v] + 1) / denominator)
                         for v, n in sorted(Counter(plan[key]).items())) for key in ('good_ids', 'bad_ids')]
        records.append(dict(pair_id=row['pair_id'], pair_sha256=plan['pair_sha256'],
            unigram_good_logp=logp[0], unigram_bad_logp=logp[1], unigram=_decision(*logp),
            token_length=_decision(-len(plan['good_ids']), -len(plan['bad_ids'])),
            character_length=_decision(-len(row['sentence_good']), -len(row['sentence_bad']))))
    return dict(signature=sha(specification), specification=specification, records=records,
        records_sha256=sha(records))


class PrefixTokenizer:
    """Override only an object-identity sentinel, never a possible sentence string."""
    def __init__(self, tokenizer, prefix):
        self.tokenizer, self.prefix, self.marker = tokenizer, list(prefix), object()
    def encode(self, value):
        return SimpleNamespace(ids=list(self.prefix)) if value is self.marker else self.tokenizer.encode(value)


def make_scorer(active, metric):
    """Only the explicit GPU execute path calls this existing numerical stack."""
    from scripts.eval_bench_suite import seq_ce
    from scripts.diag_p106b_current_benchmark import FP32Forward
    import torch.nn.functional as F
    if active['precision'] != 'FP32_MATH' or active['cfg'].max_seq_len != metric['seq_max']:
        raise ValueError('actual strict FP32/1024 runtime required')
    proxy = PrefixTokenizer(active['tokenizer'], metric['prefix_ids']); model = FP32Forward(active['model'])
    def score(sentence):
        active['route'].assert_active()
        return seq_ce(model, proxy, 'cuda', proxy.marker, sentence, metric['seq_max'], active['torch'], F)
    return score


def _score(value, count):
    if (not isinstance(value, (list, tuple)) or len(value) != 3 or type(value[2]) is not int
            or value[2] != count or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in value[:2])
            or not math.isclose(value[0] * count, value[1], rel_tol=2e-5, abs_tol=2e-5)):
        raise ValueError('finite complete mean/sum/token accounting from scorer required')
    return dict(mean_nll=value[0], sum_nll=value[1], tokens=count, logp_sum=-value[1])


def score_pair(plan, score):
    event = dict(pair_id=plan['pair']['pair_id'], plan=copy.deepcopy(plan))
    if plan['skipped']: return dict(event, skipped=True, reason=plan['reason'])
    good = _score(score(plan['pair']['sentence_good']), len(plan['good_ids']))
    bad = _score(score(plan['pair']['sentence_bad']), len(plan['bad_ids']))
    return dict(event, skipped=False, good=good, bad=bad, gap=bad['sum_nll'] - good['sum_nll'],
        decision=_decision(good['logp_sum'], bad['logp_sum']))


def summarize(events, plans, baseline):
    if len(events) != len(plans): raise ValueError('all asked pairs, including skips, must be preserved')
    baseline_index = {b['pair_id']: b for b in baseline['records']}; cells = defaultdict(Counter)
    seen = set(); skipped = Counter()
    asked_by_phenomenon = Counter(p['pair']['phenomenon'] for p in plans)
    for event, plan in zip(events, plans):
        ident = plan['pair']['pair_id']
        if event.get('pair_id') != ident or ident in seen or event.get('plan') != plan:
            raise ValueError('ordered unique source-bound pair records required')
        seen.add(ident)
        if plan['skipped']:
            if event.get('skipped') is not True or event.get('reason') != plan['reason']: raise ValueError('skip changed')
            skipped[plan['reason']] += 1; continue
        if event.get('skipped') is not False: raise ValueError('eligible pair cannot be silently dropped')
        for key in ('good', 'bad'):
            value = event[key]
            expected = _score((value['mean_nll'], value['sum_nll'], value['tokens']), len(plan[key + '_ids']))
            if value != expected: raise ValueError('stored sentence score differs')
        expected = _decision(event['good']['logp_sum'], event['bad']['logp_sum'])
        if event.get('decision') != expected or event.get('gap') != event['bad']['sum_nll'] - event['good']['sum_nll']:
            raise ValueError('stored strict comparison differs from raw scores')
        cell = cells[plan['pair']['phenomenon']]; cell.update(pairs=1, **expected)
        for name in ('unigram', 'token_length', 'character_length'):
            for key, value in baseline_index[ident][name].items(): cell[name + '_' + key] += value
    if not cells: raise ValueError('zero scored pairs')
    aggregate = Counter()
    by_phenomenon = {}
    for name, cell in sorted(cells.items()):
        aggregate.update(cell)
        by_phenomenon[name] = dict(cell, asked=asked_by_phenomenon[name],
            skipped=asked_by_phenomenon[name] - cell['pairs'], accuracy=cell['correct'] / cell['pairs'])
    return dict(asked=len(plans), scored=aggregate['pairs'], skipped=sum(skipped.values()), skip_reasons=dict(skipped),
        counts=dict(aggregate), micro_accuracy=aggregate['correct'] / aggregate['pairs'],
        macro_phenomenon_accuracy=sum(c['accuracy'] for c in by_phenomenon.values()) / len(by_phenomenon),
        phenomena=len(by_phenomenon), by_phenomenon=by_phenomenon,
        phenomena_asked=len(asked_by_phenomenon), all_skipped_phenomena=sorted(set(asked_by_phenomenon) - set(cells)),
        macro_scope='only phenomena with at least one eligible pair; all-skipped phenomena listed separately',
        baseline_accuracy={name: aggregate[name + '_correct'] / aggregate['pairs']
                           for name in ('unigram', 'token_length', 'character_length')},
        chance=.5, ties_are_correct=False, official_babylm_equivalence=False,
        baseline_scope=baseline['specification']['unigram'])


def atomic_json(path, value):
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(body) > LIMIT: raise ValueError('JSON output must remain below20MB')
    path = Path(path)
    if path.exists() or path.is_symlink(): raise FileExistsError('existing atomic result preserved')
    pending = path.with_name(path.name + '.pending_' + uuid.uuid4().hex)
    with pending.open('xb') as stream:
        stream.write(body); stream.flush(); os.fsync(stream.fileno())
    # Atomic publication without replacing an existing result. Only our exact
    # successfully linked temporary metadata file is removed after publication.
    os.link(pending, path)
    pending.unlink()


def reuse_baseline(directory, expected, root=ROOT):
    directory = safe_path(directory, root)
    manifest_path = safe_path(directory / 'baseline_shards_manifest.json', root)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('lineage') != dict(baseline_signature=expected['signature'], records_sha256=expected['records_sha256']):
        raise ValueError('baseline source/tokenizer/prefix/metric signature differs')
    verify(directory, manifest); records = []
    for shard in manifest['shards']:
        with (directory / shard['path']).open(encoding='utf-8') as stream:
            records.extend(json.loads(line) for line in stream)
    if records != expected['records']: raise ValueError('baseline raw records differ from frozen recomputation')
    return dict(signature=expected['signature'], records_sha256=expected['records_sha256'],
        reused_from=str(directory), manifest_sha256=file_sha(manifest_path))


def collect_run(output, plans, baseline, lineage, score, root=ROOT):
    output = safe_path(output, root); output.mkdir(parents=True, exist_ok=False)
    base_writer = ShardWriter(output, 'baseline', limit=LIMIT)
    for row in baseline['records']: base_writer.append(row)
    base_manifest = base_writer.close(lineage=dict(baseline_signature=baseline['signature'], records_sha256=baseline['records_sha256']))
    verify(output, base_manifest)
    writer = ShardWriter(output, 'scores', limit=LIMIT); events = []
    try:
        for plan in plans:
            tick = time.perf_counter(); event = score_pair(plan, score)
            event['score_wall_seconds'] = time.perf_counter() - tick
            writer.append(event); events.append(event)
        manifest = writer.close(lineage=dict(signature=sha(lineage), status='RAW_COMPLETE_SESSION_EXIT_PENDING'))
        verify(output, manifest)
        return dict(schema=SCHEMA, status='RAW_COMPLETE_SESSION_EXIT_PENDING', lineage=copy.deepcopy(lineage),
            signature=sha(lineage), baseline_signature=baseline['signature'], baseline_specification=baseline['specification'],
            baseline_manifest=base_manifest, score_manifest=manifest, summary=summarize(events, plans, baseline),
            score_wall_seconds=sum(e['score_wall_seconds'] for e in events),
            score_wall_scope='pair scoring callback and local comparison; excludes model load, raw writes and strict context exit')
    except BaseException as exc:
        partial = (writer.close(lineage=dict(signature=sha(lineage), status='INCOMPLETE'))
                   if writer._total_rows and not writer.manifest_path.exists() else None)
        atomic_json(output / 'error.json', dict(status='INCOMPLETE', error_type=type(exc).__name__,
            message=str(exc), complete_pairs=len(events), partial_manifest=partial, signature=sha(lineage)))
        raise


def publish_run(output, result, root=ROOT):
    output = safe_path(output, root)
    if (result['status'] != 'RAW_COMPLETE_SESSION_EXIT_PENDING'
            or result.get('strict_model_context_exit_verified') is not True
            or result.get('signature') != sha(result['lineage'])
            or result['score_manifest'].get('lineage') != dict(signature=result['signature'], status='RAW_COMPLETE_SESSION_EXIT_PENDING')
            or result['baseline_manifest'].get('lineage', {}).get('baseline_signature') != result['baseline_signature']):
        raise ValueError('unclosed strict context or changed score/baseline lineage')
    for name in ('scores', 'baseline'):
        actual = json.loads((output / (name + '_shards_manifest.json')).read_text(encoding='utf-8'))
        expected = result['score_manifest' if name == 'scores' else 'baseline_manifest']
        if actual != expected: raise ValueError('closed manifest differs from pending report')
    verify(output, result['score_manifest']); verify(output, result['baseline_manifest'])
    report = dict(result, status='EXPERIMENTAL_MINIMAL_PAIR_COMPLETE',
        model_training=False, optimizer_updates=0, checkpoint_writes=0, official_babylm_equivalence=False)
    atomic_json(output / 'report.json', report)
    return report


def execute(args):
    from scripts import interactive_research_infer as research
    from scripts.p106b_gate_runtime import wall_limit
    rows, source = read_dataset(args.data); output = safe_path(args.output)
    if output.exists(): raise FileExistsError('existing output is preserved')
    began = time.perf_counter()
    with wall_limit(args.max_wall_sec):
        spec = research.resolve_model(args.model); manifest = research.verify_manifest(ROOT)
        tokenizer = research.local_tokenizer(manifest, ROOT)
        metric = protocol(tokenizer, args.bos_policy, args.bos_token)
        plans = prepare_pairs(rows, tokenizer, metric)
        baseline = baseline_bundle(plans, source, research.TOKENIZER_SHA, metric)
        reused = reuse_baseline(args.baseline_from, baseline) if args.baseline_from else None
        with research.selected_runtime(spec, root=ROOT) as active:
            if (active['name'] != args.model or active['tokenizer_sha256'] != research.TOKENIZER_SHA
                    or protocol(active['tokenizer'], args.bos_policy, args.bos_token) != metric
                    or prepare_pairs(rows, active['tokenizer'], metric) != plans):
                raise ValueError('loaded model/tokenizer differs from CPU input proof')
            lineage = dict(schema=SCHEMA, model=args.model, checkpoint=active['checkpoint'],
                checkpoint_sha256=active['checkpoint_sha256'], core_sha256=active['core_sha256'],
                model_report_sha256=active['report_sha256'], model_manifest_sha256=active['manifest_sha256'],
                tokenizer_sha256=active['tokenizer_sha256'], quantization_route=copy.deepcopy(active['quantization_route']),
                source=source, encoded_pairs_sha256=sha(plans), protocol=metric,
                code_sha256={p: file_sha(ROOT / p) for p in CODE})
            result = collect_run(output, plans, baseline, lineage, make_scorer(active, metric))
        # The strict context's CPU/GPU core and manifest exit checks have now
        # succeeded. Do not publish success from inside that context.
        if read_dataset(args.data)[1] != source: raise ValueError('source changed during model evaluation')
        if {p: file_sha(ROOT / p) for p in CODE} != lineage['code_sha256']:
            raise ValueError('benchmark or numerical dependency source changed during evaluation')
        result.update(seconds=time.perf_counter() - began, reused_baseline=reused, strict_model_context_exit_verified=True)
        report = publish_run(output, result)
    print('[EXPERIMENTAL_MINIMAL_PAIR] ' + json.dumps(report['summary'], ensure_ascii=False), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, required=True)
    parser.add_argument('--data', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--max-wall-sec', type=int, default=1800)
    parser.add_argument('--bos-policy', choices=('newline', 'tokenizer_bos'), default='newline')
    parser.add_argument('--bos-token', default='<bos>'); parser.add_argument('--baseline-from')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    if not 60 <= args.max_wall_sec <= 21600: parser.error('bounded60..21600 wall seconds required')
    try:
        if args.check_only:
            _, source = read_dataset(args.data, root=ROOT); output = safe_path(args.output, root=ROOT)
            if output.exists(): raise FileExistsError('existing output preserved')
            print('[MINIMAL_PAIR_CHECK_ONLY] ' + json.dumps(dict(schema=SCHEMA, source=source, model=args.model,
                device='cuda_only_on_execute', bos_policy=args.bos_policy, tokenizer_bos_presence='NOT_CHECKED',
                model_loads=0, checkpoint_tensor_loads=0, gpu_calls=0, writes=0,
                semantics='EXPERIMENTAL_NOT_OFFICIAL_BABYLM'), ensure_ascii=False)); return 0
        return execute(args)
    except KeyboardInterrupt: return 130
    except Exception as exc:
        print('[MINIMAL_PAIR_ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
