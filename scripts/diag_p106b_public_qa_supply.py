#!/usr/bin/env python3
"""Pinned public QA supply inventory only; no teacher/model/weights/GPU/training.

prepare runs exactly regression/preflight/collect phases. collect is the bounded
CPU action, check verifies saved ID/count shards, and check-only/help read code
only. Original source text and canonical conversations are never copied to output.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
import ast
from collections import Counter, defaultdict
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
import resource
import subprocess
import time
from scripts import p106b_night_qa_data as data
from scripts import p106b_night_diversity_data as baseline_data
from scripts import diag_p106b_night_diversity as baseline_driver
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline
from scripts.p106b_night_qa_data import (VERSION, SEED, CONTEXT, MAX_NEW,
    normalized, overlap_keys, article_split, sha, _paragraphs, _balanced_candidates, _encoded_pair)

TAG = 'p106b_public_qa_supply_v1_s1337'
LOCAL = ROOT / 'test_result/evidence/local' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
BASELINE = baseline_data.CORPUS
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
CODE = ('scripts/diag_p106b_public_qa_supply.py', 'scripts/test_p106b_public_qa_supply.py',
        'scripts/p106b_night_qa_data.py', 'scripts/p106b_night_diversity_data.py',
        'scripts/p106b_shards.py', 'scripts/p106b_stage_receipt.py',
        'tinylm/chat/canonical.py', 'tinylm/chat/serialize.py', 'tinylm/data/sft.py', *baseline_driver.CODE)


class PrerequisitePending(RuntimeError):
    """Missing inventory input/output is NOT_RUN, not an observed zero supply."""


def safe(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('unresolved inventory path')
    try: path.relative_to(ROOT)
    except ValueError as exc: raise ValueError('inventory paths stay inside repository') from exc
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise ValueError('linked inventory/source path')
        if parent == ROOT: break
    return path


def required(path):
    path = safe(path)
    if not path.exists() or (path.is_file() and not path.stat().st_size):
        raise PrerequisitePending('complete earlier inventory stage absent: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(body) >= 20_000_000: raise ValueError('inventory report must be below20MB')
    path = safe(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(body)


def info():
    return dict(schema='P106B_PUBLIC_QA_SUPPLY_V1', tag=TAG,
        code_sha256={p: data.digest(safe(ROOT / p)) for p in sorted(set(CODE))},
        sources=copy.deepcopy(data.SOURCES), tokenizer_sha256=data.TOK_SHA,
        baseline_tag=baseline_driver.TAG, reference_train_context_cap=2,
        hypothetical_train_context_cap=4, sealed_eval_context_cap=2,
        train_limit=None, eval_limit_per_language=256, min_eval_contexts=128,
        common_bpb_count=4000, split_percent=dict(train=90, dev=5, test=5),
        seed=SEED, context=1024, generation_budget=128, max_cpu_threads=2,
        teacher_calls=0, model_loaded=False, weights_loaded=False, gpu=False,
        training=False, training_policy_adopted=False, formal_train_ready=False,
        existing29m_overlap='NOT_MEASURED', new75m_quota_integration='NOT_MEASURED',
        no_additive75m_claim=True, source_immutable=True)


def core_equivalence(reference_source=None, candidate_source=None):
    if reference_source is None: reference_source = (ROOT / 'scripts/p106b_night_qa_data.py').read_text(encoding='utf-8')
    if candidate_source is None: candidate_source = Path(__file__).read_text(encoding='utf-8')
    def segment(source):
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'collect_documents')
        return ast.get_source_segment(source, node)
    before = segment(reference_source); expected = before; actual = segment(candidate_source)
    for old, new, _ in ALLOWED_COLLECTOR_EDITS:
        if expected.count(old) != 1: raise ValueError('collector allowed edit source occurrence differs')
        expected = expected.replace(old, new, 1)
    if expected != actual or ast.dump(ast.parse(expected), include_attributes=False) != ast.dump(ast.parse(actual), include_attributes=False):
        raise ValueError('collector changed beyond declared TRAIN-bound/cap/metadata edits')
    return dict(ast_equal_after_declared_edits=True, character_equal_after_declared_edits=True,
        original_character_sha256=hashlib.sha256(before.encode()).hexdigest().upper(),
        candidate_character_sha256=hashlib.sha256(actual.encode()).hexdigest().upper(),
        allowed_edits=[dict(original=a, candidate=b, reason=c) for a, b, c in ALLOWED_COLLECTOR_EDITS])


def read_shards(directory, manifest, stem, expected_count=None):
    directory = safe(directory)
    count = manifest.get('rows')
    if type(count) is not int or count < 0: raise ValueError('integer nonnegative row count required')
    if expected_count is not None and count < expected_count:
        raise PrerequisitePending('partial original manifest; missing rows are not zero supply')
    if expected_count is not None and count != expected_count: raise ValueError('unexpected original row count')
    path = directory / (stem + '_shards_manifest.json')
    if required(path) != manifest: raise ValueError('stored manifest/report differs')
    for index, spec in enumerate(manifest.get('shards', [])):
        if spec.get('path') != f'{stem}_{index:06d}.jsonl' or spec.get('bytes', 20_000_000) >= 20_000_000:
            raise ValueError('exact row-aligned shard names below20MB required')
        safe(directory / spec['path'])
    verify(directory, manifest)
    rows = []
    for spec in manifest['shards']:
        with (directory / spec['path']).open(encoding='utf-8') as stream:
            rows.extend(json.loads(line) for line in stream)
    if len(rows) != count: raise ValueError('manifest decoded row count differs')
    return rows


def load_baseline(*, expected_train=16384, expected_eval=256, expected_code=None, enforce_observed=True):
    report = required(BASELINE / 'report.json')
    code = baseline_driver.info()['code_sha256'] if expected_code is None else expected_code
    if report.get('status') != 'DIVERSITY_CPU_FROZEN' or report.get('code_sha256') != code:
        raise ValueError('same frozen32k source/code report required')
    index = {}; signature_rows = []; manifests = report.get('manifests', {})
    if set(manifests) != {'train', 'dev', 'test'}: raise PrerequisitePending('all original32k source manifests required')
    for split in ('train', 'dev', 'test'):
        manifest = manifests[split]
        if manifest.get('lineage', {}).get('tag') != baseline_driver.TAG or manifest['lineage'].get('code_sha256') != code:
            raise ValueError('original32k manifest lineage differs')
        values = read_shards(BASELINE, manifest, split, 2 * (expected_train if split == 'train' else expected_eval))
        seen = set(); language_roots = defaultdict(list)
        for pair in values:
            baseline_data._pair(pair, split, True)
            root = pair['root']
            if root in seen or root in index: raise ValueError('duplicate/overlapping original32k root')
            seen.add(root); language_roots[pair['language']].append(root)
            signature = data.sha(pair)
            item = dict(root=root, split=split, language=pair['language'], full_row_sha256=signature)
            index[root] = item; signature_rows.append(item)
        if {k: len(v) for k, v in language_roots.items()} != {l: expected_train if split == 'train' else expected_eval for l in ('ko', 'en')}:
            raise ValueError('original32k language quota differs')
        if enforce_observed:
            expected_roots = baseline_data.OBSERVED_EVAL_ROOTS.get(split)
            if split == 'train':
                if any(data.sha(sorted(language_roots[l])) != baseline_data.OBSERVED_TRAIN[l]['roots_sha256'] for l in ('ko', 'en')):
                    raise ValueError('actual original32k full root cohort differs')
            elif data.sha(sorted(seen)) != expected_roots:
                raise ValueError('actual original sealed evaluation root cohort differs')
    return dict(report_sha256=data.digest(safe(BASELINE / 'report.json')),
        manifests_sha256=data.sha(manifests), full_row_signatures_sha256=data.sha(sorted(signature_rows, key=lambda v: v['root'])),
        counts={s: sum(v['split'] == s for v in index.values()) for s in ('train', 'dev', 'test')}), index


def annotation_inventory(documents):
    result = {}
    for language in ('ko', 'en'):
        result[language] = {}
        for split in ('train', 'dev'):
            paragraphs = list(data._paragraphs(documents[language][split]['document']))
            values = [q for _, _, qas in paragraphs for q in qas]
            result[language][split] = dict(original_articles=len({data.normalized(t) for t, _, _ in paragraphs}),
                original_contexts=len({data.normalized(c) for _, c, _ in paragraphs}), original_questions=len(values),
                annotated_impossible=sum(q.get('is_impossible') is True for q in values),
                annotated_empty_answers=sum(not q['answers'] for q in values),
                annotated_unanswerable_union=sum(not q['answers'] or q.get('is_impossible') is True for q in values),
                requestions_generated=0, replacement_answers_generated=0)
    return result


def pair_detail(pair, tok, cap, baseline_index):
    baseline_data._pair(pair, pair['split'], True)
    metrics = {}
    for view, row in pair['views'].items():
        ids, labels, _ = data.encode_view(row, tok)
        supervised = [v for v in labels[1:] if v != -100]; old = pair['encoding'][view]
        eot = tok.token_to_id('<|im_end|>')
        from tinylm.chat.serialize import serialize
        prefix = tok.encode(serialize(dict(messages=row['messages'][:1]), 'chatml', add_generation_prompt=True)).ids
        observed = dict(x_tokens=len(ids) - 1, prompt_tokens=len(prefix), assistant_targets=len(supervised),
            eot_supervised=bool(supervised and supervised[-1] == eot), target_ids_sha256=data.sha(supervised))
        if observed != old or len(ids) - 1 > 1024 or len(prefix) + 128 > 1024:
            raise ValueError('actual original view encoding/complete1024+128 differs')
        first = next((i for i, value in enumerate(labels) if value != -100), None)
        if first != len(prefix) or any(v != -100 for v in labels[:len(prefix)]):
            raise ValueError('actual assistant-only mask/prefix differs')
        eots = sum(v == eot for v in supervised)
        metrics[view] = dict(x_tokens=observed['x_tokens'], assistant_targets=len(supervised),
            eot_targets=eots, content_targets=len(supervised) - eots,
            prompt_tokens=len(prefix), encoded_ids_sha256=data.sha(ids), labels_sha256=data.sha(labels))
    signature = data.sha(pair); previous = baseline_index.get(pair['root'])
    if previous and previous['full_row_sha256'] != signature:
        raise ValueError('same original32k root has changed question/context/annotation/view/encoding')
    return dict(root=pair['root'], language=pair['language'], split=pair['split'], cap=cap,
        article_id=pair['article_id'], context_id=pair['context_id'],
        exact_context_sha256=data.sha(pair['context']),
        normalized_question_sha256=data.sha([pair['language'], data.normalized(pair['question'])]),
        qa_id_sha256=data.sha(pair['qa_id']), original_annotation_sha256=data.sha(pair['answers']),
        full_row_sha256=signature, source32k_member=previous is not None, metrics=metrics)


def detail_summary(details):
    allowed = {'root', 'language', 'split', 'cap', 'article_id', 'context_id', 'exact_context_sha256',
        'normalized_question_sha256', 'qa_id_sha256', 'original_annotation_sha256',
        'full_row_sha256', 'source32k_member', 'metrics'}
    if len({r.get('cap') for r in details}) > 1:
        raise ValueError('one declared cap per inventory cohort required')
    for row in details:
        if set(row) != allowed or type(row.get('source32k_member')) is not bool:
            raise ValueError('ID/count-only private row schema required; source text/QA forbidden')
        if row.get('language') not in ('ko', 'en') or row.get('split') not in ('train', 'dev', 'test') or row.get('cap') not in (2, 4):
            raise ValueError('explicit inventory language/split/cap required')
        views = {'0', '1'} if row['split'] == 'train' else {'0', '1', '2'}
        if set(row.get('metrics', {})) != views:
            raise ValueError('original complete view inventory required')
        for metrics in row['metrics'].values():
            if (set(metrics) != {'x_tokens', 'assistant_targets', 'eot_targets', 'content_targets', 'prompt_tokens', 'encoded_ids_sha256', 'labels_sha256'}
                    or any(type(metrics.get(k)) is not int for k in ('x_tokens', 'assistant_targets', 'eot_targets', 'content_targets', 'prompt_tokens'))
                    or not 1 <= metrics['x_tokens'] <= 1024 or not 2 <= metrics['assistant_targets'] <= 128
                    or not 1 <= metrics['eot_targets'] <= metrics['assistant_targets']
                    or metrics['content_targets'] + metrics['eot_targets'] != metrics['assistant_targets']
                    or metrics['prompt_tokens'] < 1 or metrics['prompt_tokens'] + 128 > 1024
                    or metrics['prompt_tokens'] - 1 + metrics['assistant_targets'] > metrics['x_tokens']):
                raise ValueError('invalid actual input/assistant/EOT/content inventory')
        if len({(m['assistant_targets'], m['eot_targets'], m['content_targets']) for m in row['metrics'].values()}) != 1:
            raise ValueError('same annotation views must preserve identical supervision counts')
    for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test')):
        for field in ('root', 'article_id', 'context_id', 'normalized_question_sha256'):
            if {r[field] for r in details if r['split'] == a} & {r[field] for r in details if r['split'] == b}:
                raise ValueError('inventory split separation changed')
    result = {}
    for language in ('ko', 'en'):
        result[language] = {}
        for split in ('train', 'dev', 'test'):
            rows = [r for r in details if r['language'] == language and r['split'] == split]
            roots = [r['root'] for r in rows]
            if len(roots) != len(set(roots)): raise ValueError('duplicate inventory root')
            if len({r['normalized_question_sha256'] for r in rows}) != len(rows):
                raise ValueError('global normalized-question dedup contract changed')
            context_counts = Counter(r['context_id'] for r in rows)
            cap = rows[0]['cap'] if rows and split == 'train' else 2
            if any(count > cap for count in context_counts.values()):
                raise ValueError('declared context question cap exceeded')
            views = ('0', '1') if split == 'train' else ('0', '1', '2')
            by_view = {}
            for v in views:
                by_view[v] = {k: sum(r['metrics'][v][k] for r in rows)
                              for k in ('x_tokens', 'assistant_targets', 'eot_targets', 'content_targets')}
                by_view[v]['conversations'] = len(rows)
            two = {k: by_view['0'][k] + by_view['1'][k] for k in ('x_tokens', 'assistant_targets', 'eot_targets', 'content_targets', 'conversations')}
            result[language][split] = dict(unique_qa_roots=len(roots),
                unique_questions=len({r['normalized_question_sha256'] for r in rows}),
                contexts=len({r['context_id'] for r in rows}), articles=len({r['article_id'] for r in rows}),
                exact_contexts=len({r['exact_context_sha256'] for r in rows}),
                by_view=by_view, two_view_exposure=two,
                same_answer_views_are_not_independent_questions=True, roots_sha256=data.sha(sorted(roots)))
    return result


def membership(details, baseline_index, *, require_all=False):
    for row in details:
        previous = baseline_index.get(row['root'])
        if row.get('source32k_member') != (previous is not None):
            raise ValueError('original32k membership label differs')
        if previous and (row['full_row_sha256'] != previous['full_row_sha256']
                         or row['split'] != previous['split'] or row['language'] != previous['language']):
            raise ValueError('same original32k ID has changed full row/source owner')
    result = {}
    for language in ('ko', 'en'):
        source = {k for k, v in baseline_index.items() if v['split'] == 'train' and v['language'] == language}
        current = {r['root'] for r in details if r['split'] == 'train' and r['language'] == language}
        common, extra, missing = source & current, current - source, source - current
        if require_all and missing: raise ValueError('unlimited cap2 lost original32k prefix roots')
        result[language] = dict(source32k_questions=len(source), common=len(common), additional=len(extra), missing=len(missing),
            common_roots_sha256=data.sha(sorted(common)), additional_roots_sha256=data.sha(sorted(extra)), missing_roots_sha256=data.sha(sorted(missing)))
    return result


def compare_caps(left, right):
    result = {}
    for split in ('dev', 'test'):
        a = {r['root']: r['full_row_sha256'] for r in left if r['split'] == split}
        b = {r['root']: r['full_row_sha256'] for r in right if r['split'] == split}
        if a != b: raise ValueError('sealed DEV/TEST must stay exactly identical across TRAIN caps')
    for language in ('ko', 'en'):
        a = {r['root'] for r in left if r['split'] == 'train' and r['language'] == language}
        b = {r['root'] for r in right if r['split'] == 'train' and r['language'] == language}
        result[language] = dict(cap2=len(a), cap4=len(b), common=len(a & b), added_in_cap4=len(b - a),
            absent_in_cap4=len(a - b), cap2_subset_cap4=not (a - b),
            common_sha256=data.sha(sorted(a & b)), added_sha256=data.sha(sorted(b - a)), absent_sha256=data.sha(sorted(a - b)))
    return result


def load_documents():
    documents = {}
    for language, splits in data.SOURCES.items():
        documents[language] = {}
        for split, (relative, expected) in splits.items():
            path = safe(ROOT / relative)
            if data.digest(path) != expected: raise ValueError('pinned original public source changed')
            documents[language][split] = dict(path=relative, sha256=expected, document=required(path))
    return documents


def configure_cpu():
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS'):
        os.environ[name] = '2'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    torch.set_num_threads(2)
    if torch.get_num_interop_threads() != 2: torch.set_num_interop_threads(2)
    if torch.cuda.is_initialized(): raise ValueError('CPU inventory must not initialize CUDA')
    return dict(torch_threads=torch.get_num_threads(), torch_interop_threads=torch.get_num_interop_threads(),
                tokenizer_parallelism=False, max_cpu_threads=2)


def write_detail_shards(stem, rows):
    if not rows:
        raise ValueError('global details include sealed evaluations even when TRAIN is empty')
    writer = ShardWriter(safe(LOCAL), stem, limit=19_999_999)
    for row in rows: writer.append(row)
    return writer.close(lineage=dict(tag=TAG, purpose='IDS_AND_ENCODING_COUNTS_ONLY', code_sha256=info()['code_sha256']))


def collect_work(max_wall_sec=3600):
    from scripts.p106b_gate_runtime import wall_limit
    from tokenizers import Tokenizer
    if not 60 <= max_wall_sec <= 3600: raise ValueError('CPU bound must be60..3600 seconds')
    remaining = (END - datetime.now(timezone.utc)).total_seconds()
    if remaining <= max_wall_sec + 3600: raise PrerequisitePending('CPU bound and one-hour record reserve exceed current authority')
    for path in (LOCAL, EVIDENCE):
        safe(path)
        if path.exists(): raise FileExistsError('old complete/partial supply inventory preserved')
    began = time.perf_counter(); metadata = info(); equivalence = core_equivalence()
    LOCAL.mkdir(parents=True, exist_ok=False)
    write(LOCAL / 'start.json', dict(metadata, max_wall_sec=max_wall_sec))
    with wall_limit(max_wall_sec):
        threads = configure_cpu()
        if data.digest(safe(data.TOKENIZER)) != data.TOK_SHA: raise ValueError('pinned tokenizer changed')
        tok = Tokenizer.from_file(str(data.TOKENIZER))
        baseline, index = load_baseline()
        documents = load_documents(); annotations = annotation_inventory(documents)
        cohorts = {}; details_by_cap = {}
        for cap in (2, 4):
            rows, inventory = collect_documents(documents, tok, context_question_cap=cap)
            details = [pair_detail(pair, tok, cap, index) for split in ('train', 'dev', 'test') for pair in rows[split]]
            del rows
            summary = detail_summary(details)
            members = membership(details, index, require_all=cap == 2)
            for split in ('dev', 'test'):
                actual = {r['root']: r['full_row_sha256'] for r in details if r['split'] == split}
                wanted = {k: v['full_row_sha256'] for k, v in index.items() if v['split'] == split}
                if actual != wanted: raise ValueError('source32k sealed evaluation mapping changed')
            manifest = write_detail_shards('cap' + str(cap), details)
            cohorts[str(cap)] = dict(summary=summary, source32k_membership=members, collector_inventory=inventory,
                detail_manifest=manifest, detail_manifest_sha256=data.digest(LOCAL / ('cap' + str(cap) + '_shards_manifest.json')),
                policy='REFERENCE_CAP2' if cap == 2 else 'HYPOTHETICAL_NOT_ADOPTED')
            details_by_cap[cap] = details
        comparison = compare_caps(details_by_cap[2], details_by_cap[4])
        baseline_rows = sorted(index.values(), key=lambda v: v['root'])
        manifest = write_detail_shards('baseline', baseline_rows)
        result = dict(metadata, status='CPU_PUBLIC_QA_SUPPLY_COMPLETE_NO_TRAINING_CLAIM',
            threads=threads, baseline=baseline, baseline_manifest=manifest,
            baseline_manifest_sha256=data.digest(LOCAL / 'baseline_shards_manifest.json'),
            annotation_inventory=annotations, cohorts=cohorts, cap_comparison=comparison,
            collector_equivalence=equivalence, free_answer_quality='NOT_MEASURED',
            whole_seconds=time.perf_counter() - began, peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            peak_rss_scope='Linux process ru_maxrss KiB divided by1024; not model/GPU memory',
            cuda_initialized=False, source_text_or_qa_copied_to_output=False)
        write(EVIDENCE / 'report.json', result)
    print('[PUBLIC_QA_SUPPLY_COMPLETE] CPU inventory only; no training policy/quota/quality claim', flush=True)
    return 0


def check():
    report = required(EVIDENCE / 'report.json')
    if report.get('status') != 'CPU_PUBLIC_QA_SUPPLY_COMPLETE_NO_TRAINING_CLAIM':
        raise PrerequisitePending('complete public QA supply inventory required')
    if any(report.get(k) != v for k, v in info().items()): raise ValueError('inventory source/code/claim contract changed')
    if (report.get('cuda_initialized') is not False or report.get('source_text_or_qa_copied_to_output') is not False
            or report.get('free_answer_quality') != 'NOT_MEASURED'):
        raise ValueError('CPU-only inventory evidence boundary changed')
    for language, splits in data.SOURCES.items():
        for _, (relative, expected) in splits.items():
            if data.digest(safe(ROOT / relative)) != expected: raise ValueError('original source changed after inventory')
    baseline, index = load_baseline()
    if report.get('baseline') != baseline: raise ValueError('source32k report/manifests changed')
    stem = 'baseline'; manifest = report.get('baseline_manifest', {})
    expected_lineage = dict(tag=TAG, purpose='IDS_AND_ENCODING_COUNTS_ONLY', code_sha256=info()['code_sha256'])
    if manifest.get('lineage') != expected_lineage: raise ValueError('baseline manifest source/code lineage differs')
    if data.digest(safe(LOCAL / (stem + '_shards_manifest.json'))) != report.get('baseline_manifest_sha256'):
        raise ValueError('baseline ID manifest changed')
    if read_shards(LOCAL, manifest, stem) != sorted(index.values(), key=lambda v: v['root']):
        raise ValueError('full baseline ID/signature cohort differs')
    details = {}
    for cap in (2, 4):
        cohort = report['cohorts'][str(cap)]; stem = 'cap' + str(cap)
        if (cohort.get('policy') != ('REFERENCE_CAP2' if cap == 2 else 'HYPOTHETICAL_NOT_ADOPTED')
                or cohort.get('detail_manifest', {}).get('lineage') != expected_lineage):
            raise ValueError('cap policy or detail lineage changed')
        if data.digest(safe(LOCAL / (stem + '_shards_manifest.json'))) != cohort.get('detail_manifest_sha256'):
            raise ValueError('inventory detail manifest changed')
        rows = read_shards(LOCAL, cohort['detail_manifest'], stem)
        if any(r.get('cap') != cap for r in rows): raise ValueError('inventory cap label changed')
        if detail_summary(rows) != cohort.get('summary') or membership(rows, index, require_all=cap == 2) != cohort.get('source32k_membership'):
            raise ValueError('raw inventory denominator or source32k membership differs')
        details[cap] = rows
    if compare_caps(details[2], details[4]) != report.get('cap_comparison'):
        raise ValueError('raw cap common/additional/missing recount differs')
    print('[PUBLIC_QA_SUPPLY_CHECK] raw count/ID/source/code matched; no quality or75M claim', flush=True)
    return 0


def phase_commands(max_wall_sec=3600):
    if type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 3600: raise ValueError('bounded60..3600 CPU seconds required')
    py = [sys.executable, '-B', '-X', 'utf8']
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_public_qa_supply', '-v']),
            ('PREFLIGHT', py + ['scripts/diag_p106b_public_qa_supply.py', '--mode', 'prepare', '--max-wall-sec', str(max_wall_sec), '--check-only']),
            ('EXECUTE', py + ['scripts/diag_p106b_public_qa_supply.py', '--mode', 'collect', '--max-wall-sec', str(max_wall_sec), '--execute'])]


def prepare(max_wall_sec=3600, launch=None, note=None):
    phases = phase_commands(max_wall_sec); began = time.perf_counter()
    if launch is None:
        def launch(command):
            remaining = max_wall_sec - (time.perf_counter() - began)
            if remaining <= 0: return 124
            environment = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2',
                OPENBLAS_NUM_THREADS='2', RAYON_NUM_THREADS='2', TOKENIZERS_PARALLELISM='false')
            try: return subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, timeout=remaining, env=environment).returncode
            except subprocess.TimeoutExpired: return 124
    note = (lambda line: print(line, flush=True)) if note is None else note
    return pipeline(phases, launch, note, experiment='P106B_PUBLIC_QA_SUPPLY')['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'collect', 'check'), required=True)
    parser.add_argument('--max-wall-sec', type=int, default=3600)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    if not 60 <= args.max_wall_sec <= 3600: parser.error('CPU bound must be60..3600 seconds')
    if args.check_only:
        print('[PUBLIC_QA_SUPPLY_CHECK_ONLY] ' + json.dumps(dict(info(), phases=phase_commands(args.max_wall_sec)), ensure_ascii=False))
        return 0
    try:
        if args.mode == 'prepare': return prepare(args.max_wall_sec)
        if args.mode == 'collect': return collect_work(args.max_wall_sec)
        from scripts.p106b_gate_runtime import wall_limit
        with wall_limit(args.max_wall_sec): return check()
    except KeyboardInterrupt: return 130
    except PrerequisitePending as exc:
        print('[PUBLIC_QA_SUPPLY_NOT_RUN] ' + str(exc), flush=True); return 8
    except Exception as exc:
        print('[PUBLIC_QA_SUPPLY_TOOL_ERROR] ' + type(exc).__name__ + ': ' + str(exc), flush=True); return 9


ALLOWED_COLLECTOR_EDITS = [
    [
        "train_limit=4096",
        "train_limit=None",
        "unlimited TRAIN default only"
    ],
    [
        "or train_limit < 1 or eval_limit < 1",
        "or (train_limit is not None and train_limit < 1) or eval_limit < 1",
        "allow explicit unbounded TRAIN; other validation fixed"
    ],
    [
        "tag=TAG, seed=seed",
        "tag=data.TAG, seed=seed",
        "original collector metadata tag alias"
    ],
    [
        "used_contexts[pair['context_id']] >= context_question_cap",
        "used_contexts[pair['context_id']] >= (context_question_cap if split == 'train' else 2)",
        "hypothetical TRAIN cap4; sealed evaluation remains cap2"
    ],
    [
        "if len(selected) == limit:",
        "if limit is not None and len(selected) == limit:",
        "no TRAIN early stop without bound"
    ],
    [
        "if len(selected) != limit:",
        "if limit is not None and len(selected) != limit:",
        "no exhausted unbounded TRAIN quota exception; strict DEV/TEST preserved"
    ]
]


def collect_documents(documents, tokenizer, *, train_limit=None, eval_limit=256,
                      min_eval_contexts=128, context_question_cap=2,
                      common_bpb_count=4000, seed=SEED):
    """Pure in-memory fixture/collector core; documents carry source descriptors.

    documents[language][split] = {'document': parsed original JSON,
        'path': original source path, 'sha256': pinned original file digest}.
    Only original TRAIN QAs become new train/dev/test; official DEV is excluded.
    """
    if (set(documents) != {'ko', 'en'} or (train_limit is not None and train_limit < 1) or eval_limit < 1
            or context_question_cap < 1 or min_eval_contexts < 0
            or common_bpb_count < 0):
        raise ValueError('bounded bilingual collection configuration required')
    rows = {s: [] for s in ('train', 'dev', 'test')}
    report = dict(schema=VERSION, tag=data.TAG, seed=seed, tokenizer_sha256=None,
                  tokenizer_identity='CALLER_SUPPLIED_IN_MEMORY_CORE',
                  train_wrappers=[0, 1], heldout_wrapper=2, heldout_wrapper_train_rows=0,
                  context=CONTEXT, max_new=MAX_NEW, sources={}, languages={},
                  semantic_review='NOT_FULLY_REVIEWED', teacher_calls=0,
                  source_original_split='train', split_unit='original article',
                  split_hash_percent=dict(train=90, dev=5, test=5),
                  common_bpb_policy=f'sorted unique first{common_bpb_count} English TRAIN contexts excluded; old metric not redefined',
                  near_overlap=dict(en='NFKC casefold whitespace word24', ko='NFKC casefold nonspace char64'),
                  corpus_written=False, model_loaded=False, optimizer_updates=0)
    for language in ('ko', 'en'):
        if set(documents[language]) != {'train', 'dev'}:
            raise ValueError('exact original train/dev descriptors required')
        original = list(_paragraphs(documents[language]['train']['document']))
        reserved = list(_paragraphs(documents[language]['dev']['document']))
        report['sources'][language] = {s: {k: documents[language][s][k] for k in ('path', 'sha256')}
                                       for s in ('train', 'dev')}
        dev_titles = {normalized(t) for t, c, q in reserved}
        dev_contexts = {normalized(c) for t, c, q in reserved}
        dev_questions = {normalized(q['question']) for t, c, qs in reserved for q in qs}
        dev_grams = set()
        for context in dev_contexts:
            dev_grams.update(overlap_keys(context, language))
        common = set(sorted({c for t, c, q in original})[:common_bpb_count]) if language == 'en' else set()
        common_normalized = {normalized(c) for c in common}
        common_grams = set()
        for context in common_normalized:
            common_grams.update(overlap_keys(context, language))
        common_near_contexts = set()
        rejected = Counter()
        candidates = defaultdict(list)
        seen = set()
        for title, context, qas in original:
            context_grams = overlap_keys(context, language)
            common_near = (normalized(context) not in common_normalized
                           and bool(context_grams & common_grams))
            if common_near:
                common_near_contexts.add(sha([language, normalized(context)]))
            reason = ('official_dev_article' if normalized(title) in dev_titles else
                      'common_bpb_context' if normalized(context) in common_normalized else
                      'common_near_context' if common_near else
                      'official_dev_context' if normalized(context) in dev_contexts else
                      'official_dev_near_context' if context_grams & dev_grams else None)
            if reason:
                rejected[reason] += len(qas)
                continue
            split = article_split(language, title, seed)
            article_id = sha([language, normalized(title)])
            context_id = sha([language, normalized(context)])
            for qa in qas:
                question, answers = qa['question'], qa['answers']
                if not isinstance(question, str) or not question.strip():
                    rejected['empty_question'] += 1
                    continue
                if not answers or qa.get('is_impossible') is True:
                    rejected['unanswerable'] += 1
                    continue
                if normalized(question) in dev_questions:
                    rejected['official_dev_question'] += 1
                    continue
                if any(not isinstance(a.get('text'), str) or not a['text']
                       or type(a.get('answer_start')) is not int or a['answer_start'] < 0
                       or context[a['answer_start']:a['answer_start'] + len(a['text'])] != a['text']
                       for a in answers):
                    rejected['answer_span_mismatch'] += 1
                    continue
                key = (context_id, normalized(question))
                if key in seen:
                    rejected['duplicate_context_question'] += 1
                    continue
                seen.add(key)
                source = documents[language]['train']
                root = sha([VERSION, language, source['sha256'], title, context, question, answers])
                candidates[split].append(dict(root=root, language=language, split=split,
                    article_id=article_id, article_title=title, context_id=context_id,
                    qa_id=qa['id'], question=question, context=context,
                    answers=copy.deepcopy(answers), aliases=list(dict.fromkeys(a['text'] for a in answers)),
                    source_path=source['path'], source_sha256=source['sha256']))
        # Prefer sealed TEST, then DEV, when different articles share source text
        # or questions. The lower-priority split loses the colliding records.
        reserved_contexts, reserved_questions, reserved_grams = set(), set(), set()
        split_counts = {}
        for split in ('test', 'dev', 'train'):
            clean = []
            for pair in candidates[split]:
                if (pair['context_id'] in reserved_contexts
                        or normalized(pair['question']) in reserved_questions
                        or overlap_keys(pair['context'], language) & reserved_grams):
                    rejected['cross_split_context_question_or_near'] += 1
                else:
                    clean.append(pair)
            used_contexts, used_questions, selected = Counter(), set(), []
            limit = train_limit if split == 'train' else eval_limit
            for pair in _balanced_candidates(clean, seed):
                question_key = normalized(pair['question'])
                if used_contexts[pair['context_id']] >= (context_question_cap if split == 'train' else 2) or question_key in used_questions:
                    continue
                encoded, reason = _encoded_pair(pair, tokenizer)
                if reason:
                    rejected[reason] += 1
                    continue
                selected.append(encoded)
                used_contexts[pair['context_id']] += 1
                used_questions.add(question_key)
                if limit is not None and len(selected) == limit:
                    break
            if limit is not None and len(selected) != limit:
                raise ValueError(f'{language}/{split}: need {limit} complete pairs, found {len(selected)}')
            if split != 'train' and len(used_contexts) < min_eval_contexts:
                raise ValueError(f'{language}/{split}: fewer than {min_eval_contexts} original contexts')
            rows[split].extend(selected)
            # Reserve the whole clean split, including unselected QAs, so no
            # source article/context becomes training through quota subsampling.
            for pair in clean:
                reserved_contexts.add(pair['context_id'])
                reserved_questions.add(normalized(pair['question']))
            for context in {p['context'] for p in clean}:
                reserved_grams.update(overlap_keys(context, language))
            split_counts[split] = dict(pairs=len(selected), contexts=len(used_contexts),
                articles=len({p['article_id'] for p in selected}),
                unique_questions=len(used_questions), eligible_before_tokenizer=len(clean),
                x_tokens_by_view={str(v): sum(p['encoding'][str(v)]['x_tokens'] for p in selected)
                                  for v in ((0, 1) if split == 'train' else (0, 1, 2))},
                assistant_targets=sum(p['encoding']['0']['assistant_targets'] for p in selected),
                roots_sha256=sha(sorted(p['root'] for p in selected)))
        report['languages'][language] = dict(splits=split_counts, rejections=dict(rejected),
            original_train_articles=len({normalized(t) for t, c, q in original}),
            original_train_questions=sum(len(q) for t, c, q in original),
            common_bpb_unique_contexts=len(common), common_bpb_near_contexts=len(common_near_contexts),
            official_dev_contexts=len(dev_contexts),
            official_dev_exact_context_intersection=len({normalized(c) for t, c, q in original} & dev_contexts))
    for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test')):
        for field in ('root', 'article_id', 'context_id'):
            if {p[field] for p in rows[a]} & {p[field] for p in rows[b]}:
                raise ValueError('selected split overlap: ' + field)
        if {(p['language'], normalized(p['question'])) for p in rows[a]} & {
                (p['language'], normalized(p['question'])) for p in rows[b]}:
            raise ValueError('selected normalized question overlap')
    report['selected_roots_sha256'] = sha({s: sorted(p['root'] for p in r) for s, r in rows.items()})
    report['paired_targets_identical'] = True
    report['source_span_agreement_is_semantic_truth'] = False
    return rows, report


if __name__ == '__main__': raise SystemExit(main())
