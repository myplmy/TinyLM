#!/usr/bin/env python3
"""Completed native2281 -> unchanged unique32k640; independent write-once scope.

prepare may load the pinned native weights on CPU only under root authorization.
preflight/check-only/help never load a model. Cost and training require execute,
fresh optimizers, a new cost8 and the current absolute authority/budget.
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
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
import tempfile
import time
from scripts import diag_p106b_night_diversity_scope_v2 as original_driver
from scripts import diag_p106b_night_foundation as foundation
from scripts import diag_p106b_night_prompt as other
from scripts import p106b_night_course as qa
from scripts import p106b_night_learning as method
from scripts import diag_p106b_night_train as previous
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_native_windows import reader as native_reader

source_driver = original_driver.original_driver
TAG = 'p106b_cpt_unique32k_v1_s1337'
LOCAL = ROOT / 'test_result/evidence/local' / TAG
CORPUS = LOCAL / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
AUTHORITY_END = END
RESERVE_SECONDS = 3600
EVALUATION_SECONDS = 900
TRAIN_STOP = END - timedelta(seconds=RESERVE_SECONDS + 2 * EVALUATION_SECONDS)
COST_WALL_SECONDS = 900
INITIALIZER = foundation.checkpoint('native')
INITIALIZER_SHA = 'D6ECF7127A719A08ED396B39A51285DD9F20568880F21049DF56149E01A53A11'
INITIAL_CORE = '16CBDEC379D9DAB4193B22DF41241AC1746ADEE94C03F4491B2D5E3AC39CC640'
SOURCE_INITIAL_CORE = 'E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193'
CODE = ('scripts/diag_p106b_cpt_unique32k.py', 'scripts/test_p106b_cpt_unique32k.py',
        'scripts/p106b_cpt_unique32k_entry.py', 'scripts/test_p106b_cpt_unique32k_entry.py',
        'scripts/diag_p106b_cpt_unique32k_eval.py', 'scripts/test_p106b_cpt_unique32k_eval.py',
        'tinylm/train/muon.py', 'tinylm/train/optimizer_audit.py', *original_driver.CODE)


class PrerequisitePending(RuntimeError):
    """Absent/partial earlier work is NOT_RUN, not an observed quality failure."""


def safe(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('unresolved research path')
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError('research path must stay inside repository') from exc
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('linked research path')
        if parent == ROOT:
            break
    return path


def required(path):
    path = safe(path)
    if not path.exists() or (path.is_file() and path.stat().st_size == 0):
        raise PrerequisitePending('earlier complete stage not run: ' + str(path))
    return qa.required(path)


def namespace():
    for target in (CORPUS, EVIDENCE, checkpoint(), checkpoint(True)):
        safe(target)


def authority(training=False, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('timezone-aware current UTC time required')
    stop = TRAIN_STOP if training else END
    remaining = (stop - now).total_seconds()
    if not math.isfinite(remaining) or remaining <= 0:
        raise PrerequisitePending('current absolute authority/cutoff has ended')
    return remaining


def info():
    recipe = source_driver.info()
    keys = ('natural_epoch', 'logical_quarters', 'updates_planned', 'seed', 'micro_bs', 'accum', 'seq',
            'grad_checkpoint', 'compile', 'adam_lr', 'muon_lr', 'clip', 'anneal', 'scheduler',
            'fresh_moments', 'consistency_weight', 'prompt_loss_weight', 'mtp', 'binary_aux',
            'fact_aux', 'teacher_calls', 'final_primary', 'best_selection', 'protected_source')
    paths = sorted(set(CODE))
    code = {p: qa.data.digest(safe(ROOT / p)) if safe(ROOT / p).is_file() else 'NOT_CREATED' for p in paths}
    return dict({k: recipe[k] for k in keys}, schema='P106B_CPT_UNIQUE32K_V1', tag=TAG,
        code_sha256=code, code_complete=all(v != 'NOT_CREATED' for v in code.values()),
        original_driver_code_sha256=original_driver.info()['code_sha256'],
        source_initial_core_sha256=SOURCE_INITIAL_CORE, expected_initial_core_sha256=INITIAL_CORE,
        initializer=str(INITIALIZER.relative_to(ROOT)), initializer_sha256=INITIALIZER_SHA,
        source_original_parent_sha256=foundation.data.PARENT_SHA,
        matrix_weight_decay=0., embedding_weight_decay_policy='unchanged original optimizer default; actual group receipts',
        deadline_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
        gpu_stop_utc=TRAIN_STOP.isoformat(), authority_end_utc=END.isoformat(),
        evaluation_seconds_per_endpoint=EVALUATION_SECONDS, full_evaluation_endpoints=['final640', 'DEV_best'],
        reserve_seconds=RESERVE_SECONDS, cost_wall_seconds=COST_WALL_SECONDS,
        initializer_changed=True, source_rewritten=False, free_answer_quality='NOT_RUN',
        comparison='same unique32k640 recipe; initializer is completed native2281, not QA-completed cpt_qa',
        original_driver_info=dict(tag=original_driver.TAG,
            historical_gpu_stop_utc=recipe['gpu_stop_utc'], historical_authority_end_utc=recipe['authority_end_utc']))


def require_code():
    if not info()['code_complete']:
        raise PrerequisitePending('all six independent driver/entry/evaluation files must be frozen first')


def _segment(source, name, gpu_core=False):
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    if gpu_core:
        node = next(n for n in node.body if isinstance(n, ast.Try))
    return ast.get_source_segment(source, node)


def core_equivalence(reference_source=None, candidate_source=None):
    """AST and exact text after only the enumerated initialization/runtime edits."""
    if reference_source is None:
        reference_source = (ROOT / 'scripts/diag_p106b_night_diversity_scope_v2.py').read_text(encoding='utf-8')
    if candidate_source is None:
        candidate_source = Path(__file__).read_text(encoding='utf-8')
    proof = {}
    for name in ('checkpoint', 'completed', 'save', 'run'):
        before = _segment(reference_source, name, name == 'run')
        actual = _segment(candidate_source, name, name == 'run')
        expected = before
        substitutions = []
        for old, new, reason in ALLOWED_SUBSTITUTIONS[name]:
            if expected.count(old) != 1:
                raise ValueError('allowed source segment count differs: ' + name + ' / ' + reason)
            expected = expected.replace(old, new, 1)
            substitutions.append(dict(original=old, candidate=new, reason=reason, occurrences=1))
        # get_source_segment removes indentation only from the first try line.
        # Restore that one line inside a synthetic function before AST parsing.
        expected_ast_source = 'def _core():\n    ' + expected if name == 'run' else expected
        actual_ast_source = 'def _core():\n    ' + actual if name == 'run' else actual
        a = ast.dump(ast.parse(expected_ast_source), include_attributes=False)
        b = ast.dump(ast.parse(actual_ast_source), include_attributes=False)
        if a != b or expected != actual:
            raise ValueError('scientific core changed outside declared substitutions: ' + name)
        proof[name] = dict(ast_equal_after_declared_edits=True, character_equal_after_declared_edits=True,
            original_character_sha256=hashlib.sha256(before.encode()).hexdigest().upper(),
            candidate_character_sha256=hashlib.sha256(actual.encode()).hexdigest().upper(),
            normalized_ast_sha256=hashlib.sha256(a.encode()).hexdigest().upper(),
            allowed_substitutions=substitutions)
    return proof


def _read_events(directory, report, expected_rows):
    manifest = report.get('event_manifest', {})
    count = manifest.get('rows')
    if type(count) is not int:
        raise ValueError('integer event denominator required')
    if count < expected_rows:
        raise PrerequisitePending('empty/partial event cohort; no zero imputation')
    if count != expected_rows:
        raise ValueError('wrong event denominator')
    directory = safe(directory)
    manifest_path = directory / 'events_shards_manifest.json'
    if required(manifest_path) != manifest:
        raise ValueError('event manifest file/report differs')
    for i, shard in enumerate(manifest.get('shards', [])):
        if shard.get('path') != f'events_{i:06d}.jsonl' or shard.get('bytes', 20_000_000) >= 20_000_000:
            raise ValueError('exact ordered events shards below20MB required')
        safe(directory / shard['path'])
    verify(directory, manifest)
    events = [json.loads(line) for spec in manifest['shards']
              for line in (directory / spec['path']).read_text(encoding='utf-8').splitlines()]
    if len(events) != expected_rows:
        raise ValueError('raw event count differs')
    return events


def _finite(value, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)


def native_source():
    """Full2281-event, contract, native checkpoint SHA; never load model tensors."""
    path = foundation.data.EVIDENCE / 'native/report.json'
    report = required(path)
    contract_path = foundation.data.CORPUS / 'native_contract.json'
    contract = required(contract_path); foundation.data.validate_contract(contract)
    expected = dict(status='FOUNDATION_TRAIN_COMPLETE', tag=foundation.data.TAG, arm='native',
        code_sha256=foundation.info()['code_sha256'], updates=2281, actual_x_tokens=298975232,
        actual_targets=298975232, padded_slots=298975232, native_replay_x=0, natural_pairs=0,
        content_targets=0, actual_oom=False, checkpoint_written=True, optimizer_saved=False,
        original_assets_preserved=True, initial_core_sha256=SOURCE_INITIAL_CORE,
        initializer=str(foundation.data.PARENT.relative_to(ROOT)),
        initializer_sha256=foundation.data.PARENT_SHA, checkpoint=str(INITIALIZER.relative_to(ROOT)),
        checkpoint_sha256=INITIALIZER_SHA, final_core_sha256=INITIAL_CORE,
        contract_sha256=qa.data.digest(safe(contract_path)), source_qa_sha256=foundation.data.LOCKED_QA_SHA)
    if (any(report.get(k) != v for k, v in expected.items())
            or contract.get('steps') != 2281 or contract.get('actual_draw_tokens') != 298975232
            or qa.data.digest(safe(INITIALIZER)) != INITIALIZER_SHA):
        raise ValueError('complete exact native2281 initializer/contract/checkpoint required')
    events = _read_events(foundation.data.EVIDENCE / 'native', report, 2281)
    if report['event_manifest'].get('lineage') != dict(tag=foundation.data.TAG, arm='native', status='FOUNDATION_TRAIN_COMPLETE'):
        raise ValueError('native event lineage differs')
    times = report.get('step_seconds', [])
    if len(times) != 2281:
        raise PrerequisitePending('native update timing cohort incomplete')
    for i, event in enumerate(events, 1):
        fixed = dict(arm='native', updates=i, epoch=1, x=i * 131072, targets=i * 131072, native_replay_x=0)
        if (any(event.get(k) != v for k, v in fixed.items()) or event.get('step_seconds') != times[i - 1]
                or not _finite(times[i - 1], True) or not all(_finite(event.get(k)) for k in ('ce', 'grad'))):
            raise ValueError('native full raw timeline/exposure/timing differs')
    if (report.get('grad_max') != max(e['grad'] for e in events)
            or report.get('clip_events') != sum(e['grad'] > 1. for e in events)):
        raise ValueError('native gradient/clip recount differs')
    cpt8_path = foundation.data.EVIDENCE / 'cpt_qa/report.json'
    cpt8 = required(cpt8_path)
    reference = dict(status='FOUNDATION_TRAIN_COMPLETE', arm='cpt_qa', updates=640,
        code_sha256=foundation.info()['code_sha256'], initializer=str(INITIALIZER.relative_to(ROOT)),
        initializer_sha256=INITIALIZER_SHA, initial_core_sha256=INITIAL_CORE)
    if any(cpt8.get(k) != v for k, v in reference.items()):
        raise ValueError('CPT8 initializer reference differs; never initialize from its QA-completed checkpoint')
    return dict(native_report_sha256=qa.data.digest(safe(path)),
        native_manifest_sha256=qa.data.digest(safe(foundation.data.EVIDENCE / 'native/events_shards_manifest.json')),
        native_contract_sha256=qa.data.digest(safe(contract_path)),
        native_event_concat_sha256=report['event_manifest']['concat_sha256'],
        native_updates=2281, native_actual_targets=298975232,
        initializer=str(INITIALIZER.relative_to(ROOT)), initializer_sha256=INITIALIZER_SHA,
        initial_core_sha256=INITIAL_CORE, cpt8_initializer_reference_sha256=qa.data.digest(safe(cpt8_path)))


def course_plan(courses):
    if len(courses) != 4:
        raise ValueError('four unchanged logical quarters required')
    totals = Counter(); updates = []; schedules = []; h = hashlib.sha256()
    for quarter, (natural, replay) in enumerate(courses):
        if len(natural) != 8192 or len(replay) != 4096:
            raise ValueError('same8192 natural pairs and4096 replay/quarter required')
        for lane, values in (('natural', natural), ('replay', replay)):
            for i, records in enumerate(values):
                for j, rec in enumerate(records if lane == 'natural' else [records]):
                    h.update(qa.data.sha([quarter, lane, i, j, rec.x, rec.y, rec.segments]).encode('ascii'))
        groups = method.schedule(len(natural), len(replay), quarter)
        if len(groups) != 160:
            raise ValueError('exact160 updates/quarter required')
        seen = dict(natural=[], replay=[]); exposure = Counter(); content = 0; denominators = []
        for group in groups:
            if len(group) != 16:
                raise ValueError('unchanged accum16 required')
            words, parts = previous.denominators(group, natural, replay)
            rows = [r for micro in group for r in previous.micro_records(micro, natural, replay)]
            if words <= 0 or len(rows) != 128 or any(len(previous.micro_records(m, natural, replay)) != 8 for m in group):
                raise ValueError('whole-update positive targets and physical micro8 required')
            for micro in group: seen[micro.kind].extend(micro.indices)
            exposure.update(rows=len(rows), x_tokens=sum(r.x_tokens for r in rows), assistant_targets=words)
            totals.update(actual_x_tokens=sum(r.x_tokens for r in rows), assistant_targets=words,
                native_x_tokens=8192, padded_slots=131072, pairs_seen=sum(len(m.indices) for m in group if m.kind == 'natural'),
                content_targets=parts)
            denominators.append(words); content += parts
            updates.append(dict(updates=len(updates) + 1, logical_quarter=quarter + 1, natural_epoch=1,
                x=totals['actual_x_tokens'], assistant_targets=totals['assistant_targets'], native_x=totals['native_x_tokens']))
        if sorted(seen['natural']) != list(range(8192)) or sorted(seen['replay']) != list(range(4096)):
            raise ValueError('course source duplicated/omitted')
        schedules.append(dict(quarter=quarter + 1, updates=160, exposure=dict(exposure), content_targets=content,
            denominators=denominators, schedule_sha256=qa.data.sha([[asdict(m) for m in g] for g in groups])))
    return dict(encoded_courses_sha256=h.hexdigest().upper(), schedules=schedules, updates=updates, totals=dict(totals))


def source_snapshot():
    report, expanded, tok, courses, qa_original = original_driver.read_source()
    if (report.get('status') != 'DIVERSITY_CPU_FROZEN' or report.get('code_sha256') != original_driver.info()['code_sha256']
            or report.get('initial_core_sha256') != SOURCE_INITIAL_CORE or report.get('padding') != [0, 4]
            or report.get('source_rewritten') is not False):
        raise ValueError('original scope/source CPU provenance differs')
    plan = course_plan(courses)
    expected = dict(rows=81920, x_tokens=plan['totals']['actual_x_tokens'], assistant_targets=plan['totals']['assistant_targets'])
    if expected != report['actual_exposure'] or plan['schedules'] != report['schedules']:
        raise ValueError('same actual source courses/full schedules/exposure required')
    cost8_expected, cost8_updates = original_driver._first8(courses)
    binding = dict(source_scope_cpu_sha256=qa.data.digest(safe(original_driver.CORPUS / 'report.json')),
        source_scope_evidence_sha256=qa.data.digest(safe(original_driver.EVIDENCE / 'cpu_contract.json')),
        source_original_cpu_sha256=report['original_cpu_sha256'],
        source_initial_core_sha256=report['initial_core_sha256'],
        source_split_sha256={s: qa.data.sha(v) for s, v in expanded.items()},
        source_manifests=report['original_manifests'], source_inventory=report['inventory'],
        actual_exposure=report['actual_exposure'], schedules=report['schedules'],
        same_replay_sha256=report['same_replay_sha256'], course_plan=plan,
        native_source=native_source(), cost8_expected=cost8_expected, cost8_updates=cost8_updates,
        source_qa_report_sha256=qa.data.digest(safe(ROOT / foundation.data.QA_REPORT)),
        qa_native_offsets_sha256=qa.data.sha(qa_original.get('native_train_offsets', [])),
        core_equivalence=core_equivalence())
    if not qa_original.get('native_train_offsets'):
        raise ValueError('unchanged indexed QA-native window order required')
    return binding, expanded, tok, courses, qa_original


def verify_initializer(initial, cp, identity, proof):
    if (initial != INITIAL_CORE or proof.get('initial_core_sha256') != INITIAL_CORE
            or cp != INITIALIZER or identity != INITIALIZER_SHA):
        raise ValueError('actual completed native initializer differs from frozen CPU proof')


def prepare():
    from tinylm.train import mtp_sft as core
    namespace(); authority(training=True); require_code()
    if LOCAL.exists() or EVIDENCE.exists() or checkpoint().exists() or checkpoint(True).exists():
        raise FileExistsError('new namespace complete/partial artifacts preserved')
    binding, expanded, tok, courses, _ = source_snapshot()
    torch, model, cfg, actual_tok, initial, cp, identity = foundation.load_foundation_parent('cpt_qa')
    proof = dict(initial_core_sha256=INITIAL_CORE)
    verify_initializer(initial, cp, identity, proof)
    if actual_tok.to_str() != tok.to_str():
        raise ValueError('same actual tokenizer required')
    pad, eot, _ = previous.special_ids(tok)
    px, py, ps = core.pad_records(courses[0][0][0] + courses[0][1][:6], pad, 'cpu', fixed_width=1024, batch_size=8)
    if (list(px.shape) != [8, 1024] or list(py.shape) != [8, 1024] or list(ps.shape) != [8, 1024]
            or pad != 0 or eot != 4 or torch.cuda.is_initialized()):
        raise ValueError('CPU-only original padding/EOT required')
    result = dict(info(), **binding, status='DIVERSITY_CPU_FROZEN', initial_core_sha256=initial,
        actual_parent_loaded_cpu=True, cuda_initialized=False, padding=[pad, eot], actual_padded_shape=list(px.shape),
        initializer_sha256=identity, initializer=str(cp.relative_to(ROOT)), first160_actual_x_y_equal=True,
        model_forward=False, checkpoints_written=0, optimizer_updates=0,
        source_corpus=str(original_driver.CORPUS.relative_to(ROOT)), source_rewritten=False)
    CORPUS.mkdir(parents=True, exist_ok=False)
    qa.write(CORPUS / 'report.json', result); qa.write(EVIDENCE / 'cpu_contract.json', result)
    print('[CPT_UNIQUE32K_CPU] same source courses; actual native initializer CPU verified; GPU/free-answer NOT_RUN', flush=True)
    return 0


def read_source():
    namespace(); require_code()
    report = required(CORPUS / 'report.json')
    binding, expanded, tok, courses, qa_original = source_snapshot()
    expected = dict(status='DIVERSITY_CPU_FROZEN', initial_core_sha256=INITIAL_CORE,
        initializer_sha256=INITIALIZER_SHA, initializer=str(INITIALIZER.relative_to(ROOT)),
        actual_parent_loaded_cpu=True, cuda_initialized=False, padding=[0, 4], actual_padded_shape=[8, 1024],
        first160_actual_x_y_equal=True, model_forward=False, checkpoints_written=0, optimizer_updates=0,
        source_corpus=str(original_driver.CORPUS.relative_to(ROOT)), source_rewritten=False)
    if (any(report.get(k) != v for k, v in info().items()) or any(report.get(k) != v for k, v in binding.items())
            or any(report.get(k) != v for k, v in expected.items()) or required(EVIDENCE / 'cpu_contract.json') != report):
        raise ValueError('same new CPU proof/source/code/native initializer required')
    return report, expanded, tok, courses, qa_original


def optimizer_receipt(adam, muon):
    receipts = []
    for name, optimizer in (('adamw', adam), ('muon', muon)):
        if optimizer.state:
            raise ValueError('fresh optimizer moments required')
        for index, group in enumerate(optimizer.param_groups):
            if not _finite(group.get('lr'), True) or not _finite(group.get('weight_decay')) or group['weight_decay'] < 0:
                raise ValueError('finite actual optimizer LR/WD required')
            receipts.append(dict(optimizer=name, group=index, lr=group['lr'], weight_decay=group['weight_decay'],
                tensors=len(group['params']), parameters=sum(p.numel() for p in group['params']),
                state_entries_before_updates=len(optimizer.state)))
    if not receipts or any(r['tensors'] <= 0 or r['parameters'] <= 0 for r in receipts):
        raise ValueError('actual nonempty parameter groups required')
    return receipts


def verify_optimizer_receipt(receipts):
    if (not isinstance(receipts, list) or {r.get('optimizer') for r in receipts} != {'adamw', 'muon'}
            or any(r.get('state_entries_before_updates') != 0 or not _finite(r.get('lr'), True)
                   or not _finite(r.get('weight_decay')) or r['weight_decay'] < 0
                   or type(r.get('parameters')) is not int or r['parameters'] <= 0
                   or type(r.get('tensors')) is not int or r['tensors'] <= 0 for r in receipts)):
        raise ValueError('actual fresh optimizer group receipt missing/invalid')


def _cost_events(report):
    return _read_events(LOCAL / 'cost8', report, 8)


def cost_forecast(report, proof=None):
    if proof is None: proof = read_source()[0]
    expected = proof['cost8_expected']; times = report.get('step_seconds', [])
    if (report.get('status') != 'DIVERSITY_COST_COMPLETE' or report.get('updates') != 8
            or report.get('tag') != TAG or report.get('code_sha256') != info()['code_sha256']
            or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
            or report.get('initializer_sha256') != INITIALIZER_SHA
            or report.get('initial_core_sha256') != INITIAL_CORE
            or report.get('source_initial_core_sha256') != SOURCE_INITIAL_CORE
            or report.get('actual_oom') is not False or report.get('checkpoint_written') is not False
            or report.get('event_manifest', {}).get('lineage') != info()
            or any(report.get(k) != v for k, v in expected.items()) or len(times) != 8
            or any(not _finite(v, True) for v in times)
            or not _finite(report.get('whole_seconds'), True)
            or report['whole_seconds'] < sum(times)):
        raise ValueError('fresh same-native/source/code actual cost8 required')
    verify_optimizer_receipt(report.get('actual_optimizer_groups'))
    events = _cost_events(report)
    for i, (event, expected_event) in enumerate(zip(events, proof['cost8_updates'])):
        if (any(event.get(k) != v for k, v in expected_event.items()) or event.get('step_seconds') != times[i]
                or not all(_finite(event.get(k)) for k in ('ce', 'grad'))):
            raise ValueError('cost8 raw full exposure/timing/gradient differs')
    if len(events) != 8 or len(proof['cost8_updates']) != 8:
        raise PrerequisitePending('full eight-update source/event cohort required')
    if (report.get('grad_max') != max(e['grad'] for e in events)
            or report.get('clip_events') != sum(e['grad'] > 1. for e in events)):
        raise ValueError('cost8 gradient/clip report differs from raw events')
    return max(times[1:]) * 640 + 600


def budget(proof=None, now=None):
    if proof is None: proof = read_source()[0]
    cost = required(EVIDENCE / 'cost8/report.json')
    forecast = cost_forecast(cost, proof)
    now = datetime.now(timezone.utc) if now is None else now
    remaining = authority(now=now)
    needed = forecast + 2 * EVALUATION_SECONDS + RESERVE_SECONDS
    before_training_cutoff = authority(training=True, now=now)
    result = dict(tag=TAG, training_forecast_seconds=forecast, final_evaluation_seconds=EVALUATION_SECONDS,
        dev_representative_evaluation_seconds=EVALUATION_SECONDS, reserve_seconds=RESERVE_SECONDS,
        needed_seconds=needed, remaining_seconds=remaining, remaining_training_seconds=before_training_cutoff,
        deadline_utc=END.isoformat(), training_stop_utc=TRAIN_STOP.isoformat(),
        cost8_already_spent_seconds=cost['whole_seconds'], cost8_report_sha256=qa.data.digest(EVIDENCE / 'cost8/report.json'),
        scope='new actual cost8; forecast includes600s setup/internal probes/save; not an upper bound',
        fits=needed < remaining and forecast < before_training_cutoff)
    if not result['fits']:
        raise PrerequisitePending('new training/evaluation/record reservation does not fit: ' + json.dumps(result))
    return result


def cost_reservation(max_wall_sec, now=None):
    remaining = authority(now=now); training = authority(training=True, now=now)
    wall = min(max_wall_sec, COST_WALL_SECONDS)
    needed = wall + 2 * EVALUATION_SECONDS + RESERVE_SECONDS
    if wall >= training or needed >= remaining:
        raise PrerequisitePending('cost-only bounded run and evaluation/record reserve do not fit')
    return dict(cost_only=True, cost_wall_seconds=wall, remaining_seconds=remaining,
        final_evaluation_seconds=EVALUATION_SECONDS, dev_representative_evaluation_seconds=EVALUATION_SECONDS,
        reserve_seconds=RESERVE_SECONDS, training_forecast='NOT_MEASURED_UNTIL_COST8',
        full_training_admitted=False, deadline_utc=END.isoformat())


def write_run_report(path, result, proof, receipts, reservation, cost):
    verify_optimizer_receipt(receipts)
    if not cost and receipts != required(EVIDENCE / 'cost8/report.json')['actual_optimizer_groups']:
        raise ValueError('training optimizer groups differ from actual cost8 recipe')
    result.update(source_initial_core_sha256=proof['source_initial_core_sha256'],
        initializer=str(INITIALIZER.relative_to(ROOT)), actual_optimizer_groups=receipts,
        optimizer_saved=False, fresh_optimizer=True, source_immutable=True,
        reservation=reservation, free_answer_quality='NOT_RUN', semantic_adoption='NOT_DECIDED')
    if cost: cost_forecast(result, proof)
    else: verify_training_events(result, proof)
    qa.write(safe(path), result)
    qa.write(safe(EVIDENCE / ('cost8' if cost else 'unique32k') / 'report.json'), result)


def verify_training_events(report, proof):
    expected = proof['course_plan']['updates']
    totals = proof['course_plan']['totals']
    events = _read_events(LOCAL / 'unique32k', report, 640); times = report.get('step_seconds', [])
    if (len(expected) != 640 or len(times) != 640
            or report.get('event_manifest', {}).get('lineage') != info()
            or any(report.get(k) != totals[k] for k in ('actual_x_tokens', 'assistant_targets',
                'native_x_tokens', 'padded_slots', 'pairs_seen', 'content_targets'))
            or report.get('initializer') != str(INITIALIZER.relative_to(ROOT))
            or report.get('source_initial_core_sha256') != SOURCE_INITIAL_CORE
            or report.get('initial_core_sha256') != INITIAL_CORE or report.get('initializer_sha256') != INITIALIZER_SHA
            or report.get('optimizer_saved') is not False or report.get('source_immutable') is not True):
        raise ValueError('full same-native/source/recipe training proof required')
    verify_optimizer_receipt(report.get('actual_optimizer_groups'))
    for i, (event, source_event) in enumerate(zip(events, expected)):
        if (any(event.get(k) != v for k, v in source_event.items()) or event.get('step_seconds') != times[i]
                or not _finite(times[i], True) or not all(_finite(event.get(k)) for k in ('ce', 'grad'))):
            raise ValueError('full640 event exposure/timing/gradient differs')
    if report.get('grad_max') != max(e['grad'] for e in events) or report.get('clip_events') != sum(e['grad'] > 1. for e in events):
        raise ValueError('full640 gradient/clip report differs')
    history = report.get('history', [])
    if (len(history) != 4 or [v.get('logical_quarter') for v in history] != [1, 2, 3, 4]
            or [v.get('updates') for v in history] != [160, 320, 480, 640]
            or any(not _finite(v.get('dev', {}).get('ce')) for v in history)):
        raise ValueError('four complete DEV-only selection observations required')
    best = min(range(4), key=lambda i: history[i]['dev']['ce']) + 1
    if report.get('best_dev_quarter') != best or report.get('best_dev_ce') != history[best - 1]['dev']['ce']:
        raise ValueError('strict first minimum DEV CE selection differs')
    for key in ('final_core_sha256', 'best_dev_core_sha256'):
        if not isinstance(report.get(key), str) or len(report[key]) != 64:
            raise ValueError('trained core fingerprints required')
    if best == 4 and report['best_dev_core_sha256'] != report['final_core_sha256']:
        raise ValueError('final-quarter DEV representative must share the final body')
    cp = checkpoint() if best == 4 else checkpoint(True)
    if (report.get('best_dev_checkpoint') != str(cp.relative_to(ROOT))
            or qa.data.digest(safe(cp)) != report.get('best_dev_checkpoint_sha256')):
        raise ValueError('actual DEV representative checkpoint differs')
    return True


def checkpoint_spec(best=False):
    proof = read_source()[0]
    if not completed(proof):
        raise PrerequisitePending('completed exact native->unique32k640 required')
    report = required(EVIDENCE / 'unique32k/report.json')
    path = ROOT / report['best_dev_checkpoint'] if best else checkpoint()
    identity = report['best_dev_checkpoint_sha256'] if best else report['checkpoint_sha256']
    if qa.data.digest(safe(path)) != identity:
        raise ValueError('actual final/DEV checkpoint SHA differs')
    return path, identity

ALLOWED_SUBSTITUTIONS = {
    "checkpoint": (),
    "completed": [
        [
            "initializer_sha256') != foundation.data.PARENT_SHA",
            "initializer_sha256') != INITIALIZER_SHA",
            "native initializer SHA only"
        ],
        [
            "verify(EVIDENCE / 'unique32k', report['event_manifest'])",
            "verify_training_events(report, proof)",
            "stronger raw completion audit; no math change"
        ]
    ],
    "save": [
        [
            "initializer_sha256=foundation.data.PARENT_SHA",
            "initializer_sha256=INITIALIZER_SHA",
            "native initializer metadata only"
        ]
    ],
    "run": [
        [
            "qa.TRAIN_STOP",
            "TRAIN_STOP",
            "new bounded runtime cutoff only"
        ],
        [
            "foundation.load_foundation_parent('base_qa')",
            "foundation.load_foundation_parent('cpt_qa')",
            "native final weights instead of original base"
        ],
        [
            "            if initial != proof['initial_core_sha256']",
            "            verify_initializer(initial, cp, identity, proof)\n            if initial != proof['initial_core_sha256']",
            "actual native identity audit before GPU"
        ],
        [
            "previous.deadline(training=True)",
            "authority(training=True)",
            "new absolute authority only"
        ],
        [
            "tempfile.mkdtemp(prefix='p106b_diversity_')",
            "tempfile.mkdtemp(prefix='p106b_cpt_unique32k_')",
            "new compile-cache namespace only"
        ],
        [
            "                for group in optimizer.param_groups: group['lr'] *= .5",
            "                for group in optimizer.param_groups: group['lr'] *= .5\n            optimizer_receipts = optimizer_receipt(adam, muon)",
            "read-only audit of unchanged fresh optimizers after LR scaling"
        ],
        [
            "qa.write(target / 'report.json', result)",
            "write_run_report(target / 'report.json', result, proof, optimizer_receipts, reservation, cost)",
            "independent report/lineage/receipt output only"
        ]
    ]
}


def checkpoint(best=False):
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_night_' + TAG + ('_best' if best else '') + '.pt')


def completed(proof):
    def validate(report):
        expected = proof['actual_exposure']
        if (report.get('code_sha256') != info()['code_sha256'] or report.get('updates') != 640
                or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
                or report.get('initial_core_sha256') != proof['initial_core_sha256']
                or report.get('initializer_sha256') != INITIALIZER_SHA
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
        verify_training_events(report, proof)
    return other.completion(EVIDENCE / 'unique32k/report.json', 'DIVERSITY_TRAIN_COMPLETE', validate)


def save(torch, path, state, cfg, steps, quarter, core):
    with path.open('xb') as output:
        torch.save(dict(model=state, cfg=asdict(cfg), step=steps, optimizer_saved=False,
            tokenizer_sha256=qa.data.TOK_SHA, tokenizer_lineage='chat32',
            night_diversity=dict(tag=TAG, logical_quarter=quarter, natural_epoch=1,
                initializer_sha256=INITIALIZER_SHA, core_sha256=core)), output)
    return dict(path=str(path.relative_to(ROOT)), sha256=qa.data.digest(path))


def run(cost, max_wall_sec):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    proof, expanded, tok, courses, original = read_source()
    target = safe(LOCAL / ('cost8' if cost else 'unique32k'))
    public = safe(EVIDENCE / ('cost8' if cost else 'unique32k'))
    if target.exists() or public.exists() or (not cost and (checkpoint().exists() or checkpoint(True).exists())):
        raise FileExistsError('old complete/partial native->unique32k artifacts preserved')
    reservation = cost_reservation(max_wall_sec) if cost else budget(proof)
    print('[CPT_UNIQUE32K_BUDGET] ' + json.dumps(reservation), flush=True)
    if cost: max_wall_sec = min(max_wall_sec, reservation['cost_wall_seconds'])
    authority(training=True); idle_before_gpu(); target.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter(); events = ShardWriter(target, 'events')
    qa.write(target / 'start.json', dict(info(), cost=cost, cpu_contract_sha256=qa.data.digest(CORPUS / 'report.json')))
    try:
        with wall_limit(min(max_wall_sec, int((TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()))):
            torch, base, cfg, actual_tok, initial, cp, identity = foundation.load_foundation_parent('cpt_qa')
            verify_initializer(initial, cp, identity, proof)
            if initial != proof['initial_core_sha256'] or actual_tok.to_str() != tok.to_str(): raise ValueError('same original body/tokenizer required')
            pad, eot, _ = previous.special_ids(tok); windows = native_reader(ROOT, original)
            base = base.cuda(); torch.cuda.reset_peak_memory_stats()
            before = None if cost else foundation.runtime.native_ce(base, qa.NATIVE)
            dev_before = None if cost else previous.dev_loss(base, expanded['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_cpt_unique32k_')
            model = torch.compile(base, mode='default'); adam, muon = foundation.runtime.optimizers(base)
            for optimizer in (adam, muon):
                for group in optimizer.param_groups: group['lr'] *= .5
            optimizer_receipts = optimizer_receipt(adam, muon)
            steps = x_tokens = targets = native_x = slots = content_n = pairs_n = 0
            times = []; history = []; gmax = 0.; clips = 0; best_ce = math.inf; best_state = best_core = best_quarter = None
            for quarter, (natural, replay) in enumerate(courses):
                epoch_nll = 0.; epoch_words = 0
                for group in method.schedule(len(natural), len(replay), quarter):
                    authority(training=True); tick = time.perf_counter()
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
            write_run_report(target / 'report.json', result, proof, optimizer_receipts, reservation, cost)
    except BaseException as exc:
        try: qa.write(target / 'error.json', dict(status='ERROR_OR_INTERRUPTED', message=str(exc), exception=type(exc).__name__))
        except Exception: pass
        raise
    print('[DIVERSITY_FINAL] ' + json.dumps(dict(status=result['status'], updates=steps, whole_seconds=result['whole_seconds'])), flush=True)
    return 0


def failure_status(exc):
    if isinstance(exc, KeyboardInterrupt): return 'INTERRUPTED', 130
    if isinstance(exc, PrerequisitePending): return 'PREREQUISITE_NOT_RUN', 8
    from scripts.p106b_gate_runtime import PrerequisiteHold
    if isinstance(exc, PrerequisiteHold): return 'RESOURCE_PRECONDITION_NOT_RUN', 8
    if type(exc).__module__.startswith('torch') and type(exc).__name__ == 'OutOfMemoryError':
        return 'ACTUAL_RESOURCE_OOM', 8
    return 'TOOL_ERROR', 9


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'preflight', 'cost', 'train'), required=True)
    parser.add_argument('--max-wall-sec', type=int, default=14400)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    if not 60 <= args.max_wall_sec <= 21600: parser.error('bounded60..21600 wall seconds required')
    if args.check_only:
        print('[CPT_UNIQUE32K_CHECK] ' + json.dumps(info())); return 0
    try:
        authority(training=args.mode != 'preflight')
        if args.mode == 'prepare': return prepare()
        if args.mode == 'preflight':
            read_source(); print('[CPT_UNIQUE32K_PREFLIGHT] complete source/code/initializer proof; model/GPU not loaded')
            return 0
        return run(args.mode == 'cost', args.max_wall_sec)
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        status, code = failure_status(exc)
        if code == 9:
            import traceback
            traceback.print_exc()
        print('[CPT_UNIQUE32K_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__': raise SystemExit(main())
