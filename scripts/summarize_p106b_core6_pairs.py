#!/usr/bin/env python3
"""Read-only paired Core6 recount v2; optional exclusive small summary output.

No model/backend is instantiated. Pinned official tasks own document processing,
requests and metrics; the existing independent recount and shard verifier are
reused. The statistic is unchanged from the archived v1: a fixed-task,
case-paired mean bootstrap. V2 applies the existing TinyLM cache import policy.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import sysconfig
import tarfile
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import tinylm  # noqa: F401 -- apply the existing process-local HF cache policy first.
from scripts import diag_p106b_official_core6 as official
from scripts import prepare_p106b_official_eval as assets
from scripts.p106b_shards import verify as verify_shards

SCRIPT = 'scripts/summarize_p106b_core6_pairs.py'
TEST = 'scripts/test_summarize_p106b_core6_pairs.py'
TAG = 'p106b_core6_pairs_v2_s1337'
SCHEMA = 'P106B_OFFICIAL_CORE6_PAIRED_RECOUNT_V2'
MAX_BYTES = 20_000_000
RESAMPLES, SEED = 100000, 20261024
PRIMARY = dict(piqa='acc', arc_easy='acc_norm', arc_challenge='acc_norm',
               hellaswag='acc_norm', winogrande='acc', boolq='acc')
COUNTS = dict(official.TASK_COUNTS)
INTERNAL = tuple(official.MODELS)
EXTERNAL = ('gemma270', 'qwen06', 'gemma1b')
MODELS = INTERNAL + EXTERNAL
SOURCES = (SCRIPT, TEST, 'scripts/diag_p106b_official_core6.py',
           'scripts/p106b_official_tasks.py', 'scripts/prepare_p106b_official_eval.py',
           'scripts/p106b_official_lm_adapter.py', 'scripts/p106b_shards.py',
           'tinylm/__init__.py', 'tinylm/paths.py')
SCOPE = ('Fixed completed models and the fixed six tasks; case-paired uncertainty '
         'within each task only. Not training-seed or task-population uncertainty. '
         'Exploratory percentile95 intervals, multiple comparisons uncorrected. '
         'No model adoption, intelligence improvement, dialogue or Korean-quality claim.')


class IncompleteFull(ValueError):
    """Missing/incomplete evaluation is not a zero score."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest().upper()


def regular(path):
    path = Path(path).absolute()
    if ('..' in path.parts or any(p.is_symlink() for p in (path, *path.parents))
            or not path.is_file()):
        raise ValueError('explicit nonsymlink regular file required: ' + str(path))
    return path


def digest(path):
    value = hashlib.sha256()
    with regular(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            value.update(block)
    return value.hexdigest().upper()


def unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('nonfinite JSON constant: ' + value)


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)


def read_json(path):
    path = regular(path)
    if path.stat().st_size >= MAX_BYTES:
        raise ValueError('JSON evidence must be below20MB')
    return decode(path.read_bytes())


def source_identity(root=ROOT):
    files = {name: digest(Path(root) / name) for name in SOURCES}
    return dict(files=files, sha256=digest_bytes(canonical(files)))


def report_path(model, root=ROOT):
    if model not in MODELS:
        raise ValueError('unregistered model; native successor schema is not admitted')
    namespace = 'p106b_official_core6_v2' if model in INTERNAL else 'p106b_external_core6_v3_s1337'
    return Path(root) / 'test_result/evidence' / namespace / model / 'full/report.json'


def output_path(stamp, root=ROOT):
    if not isinstance(stamp, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_\-]{0,79}', stamp):
        raise ValueError('explicit safe ASCII output stamp required')
    target = Path(root).absolute() / 'test_result/evidence' / TAG / stamp
    if any(p.is_symlink() for p in (target, *target.parents)) or target.exists():
        raise FileExistsError('existing/linked paired summary is preserved')
    return target


def sha_string(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def admit_report(model, report):
    schema, status = (('P106B_OFFICIAL_CORE6_V1', 'OFFICIAL_CORE6_FULL_COMPLETE')
                      if model in INTERNAL else
                      ('P106B_EXTERNAL_HF_CORE6_V3', 'EXTERNAL_OFFICIAL_CORE6_FULL_COMPLETE'))
    if (model not in MODELS or report.get('model') != model or report.get('schema') != schema
            or report.get('status') != status or report.get('mode') != 'full'
            or type(report.get('returncode')) is not int or report['returncode'] != 0
            or report.get('sources_unchanged') is not True
            or report.get('training') is not False or report.get('optimizer_updates') != 0
            or report.get('checkpoint_writes') != 0
            or report.get('actual_counts') != COUNTS
            or (model in INTERNAL and report.get('expected_counts') != COUNTS)
            or ('expected_counts' in report and report['expected_counts'] != COUNTS)
            or report.get('framework_commit') != assets.COMMIT
            or report.get('data_manifest_sha256') != assets.MANIFEST_SHA
            or not report.get('started_at') or not report.get('ended_at')):
        raise IncompleteFull('closed exact19965 full report required: ' + model)
    for key in ('sample_manifests', 'independent_audits', 'official_results'):
        if set(report.get(key, {})) != set(COUNTS):
            raise IncompleteFull('all six closed task artifacts required: ' + model)
    if report.get('token_lengths_summary', {}).get('requests') != 67106:
        raise IncompleteFull('exact67106 complete choice requests required')
    if model in EXTERNAL and (report.get('tag') != 'p106b_external_core6_v3_s1337'
            or report.get('raw_independent_recount') is not True or report.get('choice_likelihoods') != 67106):
        raise IncompleteFull('closed v3 external raw recount required')
    if not isinstance(report.get('model_proof'), dict) or not report['model_proof']:
        raise IncompleteFull('closed model provenance required, never load a replacement')
    signature = report.get('source_identity', {})
    files = signature.get('files')
    if (not isinstance(files, dict) or not files
            or any(not isinstance(p, str) or Path(p).is_absolute() or '..' in Path(p).parts
                   or not re.fullmatch(r'[0-9A-F]{64}', str(s)) for p, s in files.items())
            or signature.get('sha256') != digest_bytes(json.dumps(files, sort_keys=True).encode())):
        raise ValueError('historical evaluator source receipt is not self-consistent')
    policy = report.get('policy', {})
    common = dict(num_fewshot=0, chat_template=False, max_length=1024, seed=1337,
                  continuation='COMPLETE_SUM_LOGLIKELIHOOD; TASK_OWNS_ACC_NORM',
                  bos='NO_EXTRA_BOS_FOR_NONEMPTY_CONTEXT; NATIVE_PREFIX_FOR_EMPTY_CONTEXT',
                  bootstrap_iters=100000,
                  use_cache=False, request_cache=False, sqlite_cache=False,
                  logits_cache=False, softmax_dtype='float32', mixed_precision=False)
    if any(policy.get(key) != value for key, value in common.items()):
        raise ValueError('official fixed-task inference policy differs')
    precision = ('FP32; SDPA_MATH_OR_MODEL_EAGER; TF32_OFF' if model in INTERNAL else
                 'FP32; MODEL_EAGER_AND_SDPA_MATH; TF32_OFF')
    if policy.get('precision') != precision or policy.get('batch_size') != (8 if model in INTERNAL else 1):
        raise ValueError('recorded model-specific fixed FP32/batch policy differs')
    timestamps = [datetime.fromisoformat(report[key]) for key in ('started_at', 'ended_at')]
    for timestamp in timestamps:
        if timestamp.tzinfo is None:
            raise ValueError('aware closed report timestamps required')
    if timestamps[1] < timestamps[0]:
        raise ValueError('closed report cannot finish before its start')


class Inputs:
    """Only explicitly consumed files, rehashed at close; no tree scans."""
    def __init__(self):
        self.files = {}

    def add(self, path, expected=None):
        path = regular(path)
        value = dict(bytes=path.stat().st_size, sha256=digest(path))
        if expected is not None and value['sha256'] != str(expected).upper():
            raise ValueError('input SHA mismatch: ' + str(path))
        if str(path) in self.files and self.files[str(path)] != value:
            raise ValueError('input changed between reads: ' + str(path))
        self.files[str(path)] = value
        return value

    def unchanged(self):
        for path, expected in self.files.items():
            if Path(path).stat().st_size != expected['bytes'] or digest(path) != expected['sha256']:
                raise ValueError('read-only input changed during recount: ' + path)
        return True


def verify_pinned_task_code(inputs, provenance, specs, runtime):
    """Verify used task/YAML bodies against the already pinned archive, no extract."""
    source = Path(provenance['source_root'])
    archive = read_json(Path(provenance['manifest_path']))['archive_path']
    needed = {'lm_eval/api/task.py', 'lm_eval/tasks/_yaml_loader.py',
              'lm_eval/tasks/hellaswag/utils.py',
              'lm_eval/tasks/winogrande/preprocess_winogrande.py'}
    needed.update(str(Path(spec['official_yaml']).relative_to(source)) for spec in specs)
    expected = {}
    with tarfile.open(archive, 'r:gz') as stream:
        for member in stream:
            parts = Path(member.name).parts
            relative = '/'.join(parts[1:])
            if relative not in needed:
                continue
            if not member.isfile() or member.size >= MAX_BYTES or relative in expected:
                raise ValueError('pinned task source archive member differs')
            body = stream.extractfile(member)
            if body is None:
                raise ValueError('missing pinned task source bytes')
            with body:
                expected[relative] = digest_bytes(body.read())
    if set(expected) != needed:
        raise ValueError('pinned official task source closure is incomplete')
    for name, sha in expected.items():
        inputs.add(source / name, sha)
        if name in {'lm_eval/api/task.py', 'lm_eval/tasks/_yaml_loader.py'}:
            inputs.add(Path(runtime) / name, sha)
    inputs.add(archive, provenance['framework_archive_sha256'])
    inputs.add(provenance['manifest_path'], provenance['manifest_sha256'])
    return expected


def memory_task(task_class, task_yaml, dataset):
    """Change storage admission only; all official scientific methods inherited."""
    class ReadOnlyMemoryTask(task_class):
        def download(self, dataset_kwargs=None, **kwargs):
            self.dataset = dataset
    task = ReadOnlyMemoryTask(config=task_yaml)
    if task.dataset is not dataset:
        raise ValueError('in-memory-only official task storage changed')
    return task


def load_readonly_tasks(inputs):
    """Use the existing eval venv. Never call datasets.load_dataset or model code."""
    assets.configure_hf_cache()
    for key, value in official.OFFLINE.items():
        os.environ[key] = value
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    from scripts.p106b_official_lm_adapter import prepare_harness
    _, provenance = prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
    inputs.add(assets.ASSETS / 'manifest.json', assets.MANIFEST_SHA)
    specs = assets.task_specs(read_json(assets.ASSETS / 'manifest.json'))
    code = verify_pinned_task_code(inputs, provenance, specs, sysconfig.get_paths()['purelib'])
    from lm_eval.tasks._yaml_loader import load_yaml
    from lm_eval.api.task import ConfigurableTask
    import pyarrow.parquet as parquet
    from datasets import Dataset
    tasks = {}
    for spec in specs:
        inputs.add(spec['data_file'], spec['data_sha256'])
        task_yaml = load_yaml(spec['official_yaml'], resolve_func=True, recursive=True)
        before = {key: task_yaml.get(key) for key in
                  ('doc_to_text', 'doc_to_choice', 'doc_to_target', 'process_docs', 'metric_list', 'target_delimiter')}
        task_yaml.update(copy.deepcopy(spec['overrides']))
        split = next(iter(spec['overrides']['dataset_kwargs']['data_files']))
        table = parquet.read_table(spec['data_file'])
        task = memory_task(ConfigurableTask, task_yaml, {split: Dataset(table)})
        if len(task.task_docs) != COUNTS[spec['task']] or task.dataset[split].cache_files:
            raise ValueError('exact in-memory task denominator/no-cache contract differs')
        for key, value in before.items():
            if value is not None and getattr(task.config, key) != value:
                raise ValueError('official task science field changed: ' + key)
        tasks[spec['task']] = task
    return tasks, dict(specs=specs, framework=provenance, task_source_sha256=code,
        storage='PINNED_PARQUET_TO_IN_MEMORY_DATASET; ONLY_DOWNLOAD_STORAGE_METHOD_OVERRIDDEN',
        dataset_loader_calls=0, model_instances=0)


def read_samples(directory, task_name, manifest, model, inputs):
    if (manifest.get('schema') != 'P106B_WRITE_ONCE_SHARDS_V1'
            or type(manifest.get('limit_bytes')) is not int
            or not 0 < manifest['limit_bytes'] <= MAX_BYTES
            or manifest.get('rows') != COUNTS[task_name]):
        raise ValueError('full sample manifest contract differs')
    lineage = manifest.get('lineage', {})
    if (lineage.get('model') != model or lineage.get('task') != task_name
            or lineage.get('mode') != 'full'):
        raise ValueError('sample model/task/full lineage differs')
    disk = directory / (task_name + '_samples_shards_manifest.json')
    inputs.add(disk)
    if read_json(disk) != manifest:
        raise ValueError('embedded and closed disk sample manifests differ')
    for shard in manifest['shards']:
        name = shard.get('path', '')
        if Path(name).name != name or not name.startswith(task_name + '_samples_'):
            raise ValueError('sample shard must remain in its original task directory')
        inputs.add(directory / name, shard['sha256'])
    verify_shards(directory, manifest)
    rows = []
    for shard in manifest['shards']:
        with regular(directory / shard['path']).open('rb') as stream:
            rows.extend(decode(line) for line in stream)
    return rows


class CaseContracts:
    """Memoize official case/request results, never replace a scientific method.

    All admitted models use these same frozen six tasks. Jinja compilation in
    official task_requests is repeated even for unchanged strings; computing it
    once per case avoids N-model repeated evaluation of an identical prompt.
    """
    def __init__(self, task, expected, request_builder):
        if len(task.task_docs) != expected:
            raise ValueError('exact official task documents required')
        self.rows, self.by_identity = [], {}
        for index, doc in enumerate(task.task_docs):
            _, choices, requests = request_builder(task, doc, index)
            arguments = [list(request.args) for request in requests]
            target = task.doc_to_target(doc)
            gold = task.doc_to_text(doc) if task.multiple_input else target
            value = dict(doc=doc, choices=choices, arguments=arguments, target=target, gold=gold,
                doc_bytes=canonical(doc), hashes=dict(
                    doc_hash=sha_string(json.dumps(doc, indent=2, ensure_ascii=False)),
                    prompt_hash=sha_string(arguments[0][0]), target_hash=sha_string(str(target))))
            identities = dict(docs=doc, arguments=arguments, gold_choices=[gold, target, choices])
            identities['cases'] = dict(doc_id=index, **identities)
            value['identity_bytes'] = {key: canonical(identity) + b'\n' for key, identity in identities.items()}
            self.rows.append(value)
            self.by_identity[id(doc)] = value
        # The existing independent baseline audit sees exactly these original
        # official method results, without recompiling Jinja a second time.
        self.audit_view = SimpleNamespace(eval_docs=[value['doc'] for value in self.rows],
            multiple_input=task.multiple_input,
            doc_to_choice=lambda doc: self.by_identity[id(doc)]['choices'],
            doc_to_text=lambda doc: self.by_identity[id(doc)]['gold'],
            doc_to_target=lambda doc: self.by_identity[id(doc)]['target'])


def recount_task(task_name, task, rows, *, expected, request_builder, contracts=None):
    """Official request/metric methods plus existing independent baseline audit."""
    if len(rows) != expected:
        raise ValueError('exact task rows and official documents required')
    contracts = contracts or CaseContracts(task, expected, request_builder)
    if len(contracts.rows) != expected:
        raise ValueError('exact memoized official case denominator required')
    hashes = {key: hashlib.sha256() for key in ('cases', 'docs', 'arguments', 'gold_choices')}
    primary = []
    choices_total = 0
    for index, row in enumerate(rows):
        if type(row.get('doc_id')) is not int or row['doc_id'] != index or row.get('filter') != 'none':
            raise ValueError('exact ordered doc_id and official none filter required')
        contract = contracts.rows[index]
        doc, choices, gold = contract['doc'], contract['choices'], contract['gold']
        arguments, target = contract['arguments'], contract['target']
        if (canonical(row.get('doc')) != contract['doc_bytes'] or row.get('arguments') != arguments
                or row.get('target') != target):
            raise ValueError('official doc/prompt/choice/target differs at ' + task_name + ':' + str(index))
        # Original evaluator hashes the original insertion order before the shard writer sorts JSON keys.
        if any(row.get(key) != value for key, value in contract['hashes'].items()):
            raise ValueError('official original document/prompt/target hash differs')
        filtered, raw = row.get('filtered_resps'), row.get('resps')
        if (not isinstance(filtered, list) or not isinstance(raw, list)
                or len(filtered) != len(choices) or len(raw) != len(choices)
                or any(not isinstance(value, list) or len(value) != 2 or type(value[1]) is not bool
                       for value in filtered)
                or any(not isinstance(value, list) or len(value) != 1 or value[0] != filtered[i]
                       for i, value in enumerate(raw))):
            raise ValueError('complete unchanged one-response-per-choice raw/filtered scores required')
        independent = official.independent_row(choices, gold, [value[0] for value in filtered])
        metrics = task.process_results(doc, filtered)
        if set(row.get('metrics', [])) != set(metrics):
            raise ValueError('official per-row metric set differs')
        for metric, value in metrics.items():
            if (metric not in {'acc', 'acc_norm'} or type(row.get(metric)) not in (int, float)
                    or row[metric] not in (0, 1) or row[metric] != value or row[metric] != independent[metric]):
                raise ValueError('official per-row metric recount differs')
        primary.append(int(row[PRIMARY[task_name]]))
        for key, value in contract['identity_bytes'].items():
            hashes[key].update(value)
        choices_total += len(choices)
    audit = official.audit_samples(contracts.audit_view, rows, expected)
    return dict(values=primary, audit=audit, choice_likelihoods=choices_total,
        correspondence={key + '_ordered_sha256': value.hexdigest().upper() for key, value in hashes.items()})


def verify_audit(recount, reported):
    for key, value in recount.items():
        other = reported.get(key)
        if key == 'posthoc_label_counts':
            other = {int(k): v for k, v in other.items()} if isinstance(other, dict) else None
        if isinstance(value, float):
            if (not isinstance(other, (int, float)) or isinstance(other, bool)
                    or not math.isfinite(other) or not math.isclose(value, other, rel_tol=1e-12, abs_tol=1e-12)):
                raise ValueError('original aggregate audit differs: ' + key)
        elif value != other:
            raise ValueError('original aggregate audit differs: ' + key)


def recount_model(model, path, report, tasks, inputs, request_builder, contracts):
    totals, values, per_task, correspondence = 0, {}, {}, {}
    for name in PRIMARY:
        began = time.perf_counter()
        rows = read_samples(path.parent, name, report['sample_manifests'][name], model, inputs)
        counted = recount_task(name, tasks[name], rows, expected=COUNTS[name], request_builder=request_builder,
                               contracts=contracts[name])
        verify_audit(counted['audit'], report['independent_audits'][name])
        official_metrics = report['official_results'][name]['results'][name]
        for metric, field in (('acc', 'correct'), ('acc_norm', 'correct_norm')):
            if metric + ',none' in official_metrics:
                if not math.isclose(official_metrics[metric + ',none'], counted['audit'][field] / COUNTS[name],
                                    rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError('original official task aggregate differs')
        if PRIMARY[name] + ',none' not in official_metrics:
            raise ValueError('registered primary official metric absent')
        if 'choice_likelihoods' in report['independent_audits'][name]:
            if counted['choice_likelihoods'] != report['independent_audits'][name]['choice_likelihoods']:
                raise ValueError('original per-task choice count differs')
        audit = counted['audit']
        values[name] = counted['values']
        correspondence[name] = counted['correspondence']
        per_task[name] = dict(rows=COUNTS[name], primary_metric=PRIMARY[name],
            primary_correct=sum(values[name]), primary_score=sum(values[name]) / COUNTS[name],
            acc=audit['correct'] / COUNTS[name], acc_norm=audit['correct_norm'] / COUNTS[name],
            baseline=dict(random_expectation=audit['random_expected_correct'] / COUNTS[name],
                random_expected_correct=audit['random_expected_correct'],
                random_independent_sd=audit['random_independent_sd'],
                posthoc_label_majority=audit['posthoc_majority_correct'] / COUNTS[name],
                posthoc_label_counts={str(k): v for k, v in audit['posthoc_label_counts'].items()},
                shortest=audit['shortest_correct'] / COUNTS[name], longest=audit['longest_correct'] / COUNTS[name],
                baseline_policy=audit['baseline_policy'], length_ties='FIRST_ORIGINAL_CHOICE_INDEX'),
            raw_concat_sha256=report['sample_manifests'][name]['concat_sha256'],
            choice_likelihoods=counted['choice_likelihoods'], correspondence=counted['correspondence'],
            recount_seconds=time.perf_counter() - began)
        print('[CPU recount] ' + model + '/' + name + ': ' + str(COUNTS[name]) + ' exact rows', file=sys.stderr)
        totals += counted['choice_likelihoods']
        del rows
    if sum(len(v) for v in values.values()) != 19965 or totals != 67106:
        raise ValueError('recount must contain exact19965 documents and67106 likelihoods')
    return dict(model=model, report_path=str(path), report_sha256=inputs.files[str(path)]['sha256'],
        historical_evaluator_source_identity=report['source_identity'], policy=report['policy'],
        model_proof=report['model_proof'], framework_commit=report['framework_commit'],
        data_manifest_sha256=report['data_manifest_sha256'], rows=19965, choice_likelihoods=totals,
        per_task=per_task, mean6=sum(row['primary_score'] for row in per_task.values()) / 6,
        correspondence=correspondence, values=values)


def category_mean_samples(np, deltas, rng, draws):
    values = np.asarray(deltas)
    if (values.ndim != 1 or not values.size or not np.isin(values, (-1, 0, 1)).all()
            or type(draws) is not int or draws < 1):
        raise ValueError('nonempty paired {-1,0,+1} differences and positive draws required')
    counts = np.bincount(values.astype(np.int8) + 1, minlength=3)
    sampled = rng.multinomial(values.size, counts / values.size, size=draws)
    means = (sampled[:, 2] - sampled[:, 0]) / values.size
    return means, counts


def paired_intervals(left, right, *, draws=RESAMPLES, seed=SEED):
    import numpy as np
    if (set(left) != set(PRIMARY) or set(right) != set(PRIMARY) or type(seed) is not int
            or seed < 0 or type(draws) is not int or draws < 1):
        raise ValueError('the same exact six task strata and integer seed required')
    rng = np.random.default_rng(seed)
    macro = np.zeros(draws, dtype=np.float64)
    result = {}
    for name in PRIMARY:
        a, b = np.asarray(left[name]), np.asarray(right[name])
        if a.ndim != 1 or a.shape != b.shape or not np.isin(a, (0, 1)).all() or not np.isin(b, (0, 1)).all():
            raise ValueError('same nonempty paired binary primary outcomes required')
        delta = b.astype(np.int8) - a.astype(np.int8)
        means, counts = category_mean_samples(np, delta, rng, draws)
        macro += means / 6
        result[name] = dict(n=int(a.size), primary_metric=PRIMARY[name],
            left=float(a.mean()), right=float(b.mean()), right_minus_left=float(delta.mean()),
            discordant_right_worse=int(counts[0]), same_correctness=int(counts[1]),
            discordant_right_better=int(counts[2]),
            ci95=np.quantile(means, [.025, .975], method='linear').tolist())
    return dict(per_task=result, mean6=dict(left=sum(row['left'] for row in result.values()) / 6,
        right=sum(row['right'] for row in result.values()) / 6,
        right_minus_left=sum(row['right_minus_left'] for row in result.values()) / 6,
        ci95=np.quantile(macro, [.025, .975], method='linear').tolist()),
        resamples=draws, seed=seed, numpy_version=np.__version__, percentile_method='linear',
        sampling='Independent case-pair resampling within each fixed task; mean of six task means',
        optimization='Empirical {-1,0,+1} count multinomial; equivalent for the mean statistic only',
        rng='PCG64 default_rng reset to the fixed seed for every ordered model pair; fixed task order',
        multiple_comparisons_corrected=False, interpretation=SCOPE)


@contextmanager
def cpu_wall_limit(seconds):
    if type(seconds) is not int or not 1 <= seconds <= 120:
        raise ValueError('CPU wall reservation must be1..120 seconds')
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise ValueError('do not replace another active process alarm')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*_):
        raise TimeoutError('bounded CPU paired recount exceeded its wall reservation')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def collect(models, *, root=ROOT, max_wall_sec=120):
    if len(models) < 2 or len(set(models)) != len(models) or any(model not in MODELS for model in models):
        raise ValueError('at least two distinct registered completed models required')
    selected = tuple(model for model in MODELS if model in models)
    began = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    source = source_identity()
    inputs = Inputs()
    reports = {}
    # Refuse any missing/cost/partial/HOLD report before official task imports.
    for model in selected:
        path = report_path(model, root).absolute()
        if not path.is_file():
            raise IncompleteFull('full report is not closed: ' + str(path))
        inputs.add(path)
        report = read_json(path)
        admit_report(model, report)
        reports[model] = (path, report)
    with cpu_wall_limit(max_wall_sec):
        tasks, task_proof = load_readonly_tasks(inputs)
        from scripts.p106b_official_tasks import task_requests
        contract_began = time.perf_counter()
        contracts = {name: CaseContracts(tasks[name], COUNTS[name], task_requests) for name in PRIMARY}
        task_proof['official_case_contracts_generated'] = sum(len(value.rows) for value in contracts.values())
        task_proof['contract_generation_seconds'] = time.perf_counter() - contract_began
        task_proof['reuse'] = 'MEMOIZED_ORIGINAL_DOC_REQUEST_TARGET_RESULTS; ORIGINAL_PROCESS_RESULTS_PER_MODEL_CASE'
        models_data = {}
        reference_correspondence = None
        for model, (path, report) in reports.items():
            counted = recount_model(model, path, report, tasks, inputs, task_requests, contracts)
            if reference_correspondence is None:
                reference_correspondence = counted['correspondence']
            elif counted['correspondence'] != reference_correspondence:
                raise ValueError('models do not have exact paired document/prompt/gold/choice correspondence')
            models_data[model] = counted
        comparisons = {}
        for left, right in itertools.combinations(selected, 2):
            comparisons[left + '__' + right] = dict(left_model=left, right_model=right,
                **paired_intervals(models_data[left]['values'], models_data[right]['values']))
        for value in models_data.values():
            del value['values']
        if source_identity() != source:
            raise ValueError('paired recount source changed during CPU execution')
        inputs.unchanged()
    return dict(schema=SCHEMA, tag=TAG, status='CLOSED_FULLS_PAIRED_CPU_RECOUNT_COMPLETE',
        returncode=0, models=models_data, pairs=comparisons,
        primary_metrics=PRIMARY, task_counts=COUNTS, paired_correspondence_verified=True,
        task_proof=task_proof, source_identity=source, input_files=inputs.files,
        source_unchanged=True, inputs_unchanged=True,
        unselected_models={model: 'NOT_SELECTED_NOT_SCORED' for model in MODELS if model not in selected},
        unsupported_extensions={'native_successor': 'SCHEMA_NOT_ADMITTED_NOT_SCORED'},
        interpretation=SCOPE, models_loaded=0, gpu_calls=0, optimizer_updates=0,
        raw_modified=False, quality_claim=False, adoption_decision=False,
        started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=time.perf_counter() - began,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        rss_scope='WHOLE_CPU_PROCESS_LINUX_PEAK; INCLUDES_OFFICIAL_TASK_IMPORTS_AND_ARRAYS')


def write_summary(target, report):
    """Only small statistics and hashes; never copy original raw examples."""
    body = canonical(report) + b'\n'
    if len(body) >= MAX_BYTES:
        raise ValueError('small paired report must be below20MB')
    if target.exists() or any(p.is_symlink() for p in (target, *target.parents)):
        raise FileExistsError('prior paired output preserved')
    target.mkdir(parents=True, exist_ok=False)
    path = target / 'report.json'
    with path.open('xb') as stream:
        stream.write(body)
    receipt = dict(schema='P106B_CORE6_PAIRS_OUTPUT_RECEIPT_V2',
        outputs={'report.json': dict(bytes=len(body), sha256=digest_bytes(body))},
        source_sha256=report['source_identity']['sha256'],
        input_files_sha256=digest_bytes(canonical(report['input_files'])),
        raw_examples_copied=0, write_once=True)
    receipt_body = canonical(receipt) + b'\n'
    if len(receipt_body) >= MAX_BYTES:
        raise ValueError('output hash receipt must be below20MB')
    with (target / 'outputs.json').open('xb') as stream:
        stream.write(receipt_body)
    return dict(directory=str(target), report_sha256=digest_bytes(body),
        outputs_receipt_sha256=digest_bytes(receipt_body), report_bytes=len(body))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-only', action='store_true')
    modes.add_argument('--read-only', action='store_true')
    modes.add_argument('--execute', action='store_true')
    parser.add_argument('--models', nargs='+', choices=MODELS, default=list(INTERNAL))
    parser.add_argument('--output-stamp')
    parser.add_argument('--source-sha256')
    parser.add_argument('--max-wall-sec', type=int, default=120)
    args = parser.parse_args(argv)
    source = source_identity()
    if args.check_only:
        print(json.dumps(dict(schema=SCHEMA, status='SOURCE_ONLY', source_identity=source,
            registered_models=list(MODELS), native_extension='SCHEMA_NOT_ADMITTED',
            resamples=RESAMPLES, seed=SEED, models_loaded=0, raw_reads=0, evidence_writes=0,
            cache_policy_imported=True,
            cache_directory_side_effects='EXISTING_TINYLM_PATHS_MKDIR_EXIST_OK; NO_HEAVY_IMPORT')))
        return 0
    if args.source_sha256 is not None and args.source_sha256 != source['sha256']:
        parser.error('source-only receipt changed')
    if args.execute and args.source_sha256 is None:
        parser.error('exclusive output requires --source-sha256')
    if args.read_only and args.output_stamp:
        parser.error('read-only mode cannot name an output')
    target = output_path(args.output_stamp) if args.execute else None
    report = collect(args.models, max_wall_sec=args.max_wall_sec)
    output = write_summary(target, report) if target is not None else None
    print(json.dumps(dict(status=report['status'], models=list(report['models']),
        pairs=len(report['pairs']), elapsed_seconds=report['elapsed_seconds'],
        peak_rss_bytes=report['peak_rss_bytes'], source_sha256=source['sha256'],
        model_mean6={name: value['mean6'] for name, value in report['models'].items()},
        pair_mean6={name: value['mean6'] for name, value in report['pairs'].items()},
        report_sha256=digest_bytes(canonical(report) + b'\n'), output=output,
        models_loaded=0, gpu_calls=0, quality_claim=False), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
