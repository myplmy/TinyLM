#!/usr/bin/env python3
"""Process-local v2 metadata recovery; the preserved v1 owns all computation.

No source/checkpoint is copied by this adapter. An explicitly executed prepare
regenerates the complete course through v1, then independently compares the
new payload with the pinned, failed v1 preparation. That preparation remains
failed. Subsequent workers require the separate recovery receipt before any
model/GPU path. The scope is deliberately single-process, not thread-safe.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_broad_curriculum as legacy

ORIGINAL_TAG = 'p106b_broad_curriculum_v1_s1337'
TAG = 'p106b_broad_curriculum_v2_s1337'
RECOVERY_SCHEMA = 'P106B_BROAD_METADATA_RECOVERY_V1'
CACHE, RAW, EVIDENCE = (ROOT / 'data_cache' / TAG, ROOT / 'runs/eval' / TAG,
                        ROOT / 'test_result/evidence' / TAG)
ORIGINAL_CACHE = ROOT / 'data_cache' / ORIGINAL_TAG
ORIGINAL_EVIDENCE = ROOT / 'test_result/evidence' / ORIGINAL_TAG
OLD_SCRIPT = 'scripts/diag_p106b_broad_curriculum.py'
SCRIPT = 'scripts/diag_p106b_broad_recovery.py'
TEST = 'scripts.test_p106b_broad_recovery'
OWN_CODE = (SCRIPT, 'scripts/test_p106b_broad_recovery.py')
ACTIVITY_SCOPE = 'additional independent recovery audit; old/core prepare activity unchanged'
REFERENCE_PINS = {
    'data_cache/p106b_broad_curriculum_v1_s1337/frozen.json':
        'CE10EF37C5328E140A7EF9FFE466C3F4C834FAB3A47D16C6FEA92AFBAB4FABB7',
    'data_cache/p106b_broad_curriculum_v1_s1337/course.json':
        '107746B68C7AE0A2945A97700BBAA883E118CE245F003FEAE95E72661B215957',
    'test_result/evidence/p106b_broad_curriculum_v1_s1337/activity_prepare.json':
        '631A71AE13664430118B8697C994D72CEA74F1D2B66E2C015E32D46B6A8150A5',
    'test_result/101_log_20261019_P106B_Stage4eyW0_broad_course_cpu_214618.txt':
        'FF5B83250B04A5F61B29AE75DFFA2B880EAE7F967BFEF69AF7EF6F35AE55B458',
}
_INFO, _PHASES = legacy.info, legacy.phase_commands
_DIALOGUES, _DISPLAY = legacy.select_dialogues, legacy.monitor_display_ids


@contextmanager
def _attributes(**values):
    before = {key: getattr(legacy, key) for key in values}
    try:
        for key, value in values.items():
            setattr(legacy, key, value)
        yield
    finally:
        for key, value in before.items():
            setattr(legacy, key, value)


def info():
    value = _INFO()
    policy = value.pop('source_admission')
    if policy != 'CPU_PREPARE_ONLY':
        raise ValueError('preserved v1 source-admission policy changed')
    pins = dict(value['code_sha256'])
    for path in OWN_CODE:
        target = ROOT / path
        pins[path] = legacy.digest(legacy.safe(target)) if target.is_file() else 'NOT_CREATED'
    value.update(tag=TAG, code_sha256=pins, code_complete='NOT_CREATED' not in pins.values(),
        source_admission_policy=policy, recovery_schema=RECOVERY_SCHEMA,
        recovery_of_tag=ORIGINAL_TAG, selection_tag=ORIGINAL_TAG,
        recovery_change='METADATA_KEY_AND_OUTPUT_NAMESPACE_ONLY')
    return value


def select_dialogues(*args, **kwargs):
    with _attributes(TAG=ORIGINAL_TAG):
        return _DIALOGUES(*args, **kwargs)


def monitor_display_ids(*args, **kwargs):
    with _attributes(TAG=ORIGINAL_TAG):
        return _DISPLAY(*args, **kwargs)


def phase_commands(mode, arm, max_wall_sec):
    phases = _PHASES(mode, arm, max_wall_sec)
    result = []
    for name, original in phases:
        command = [SCRIPT if part == OLD_SCRIPT else part for part in original]
        if name == 'REGRESSION':
            if TEST not in command:
                command.insert(command.index('-v'), TEST)
        elif command.count(SCRIPT) != 1 or OLD_SCRIPT in command:
            raise ValueError('every non-regression child must use the recovery wrapper')
        result.append((name, command))
    return result


@contextmanager
def runtime_scope():
    # Only these six routing/metadata names and the two pure hash selectors move.
    # Neither prepare/train_updates/evaluate nor builder constants are replaced.
    with _attributes(TAG=TAG, CACHE=CACHE, RAW=RAW, EVIDENCE=EVIDENCE,
                     info=info, phase_commands=phase_commands,
                     select_dialogues=select_dialogues, monitor_display_ids=monitor_display_ids):
        yield


def compare_frozen(reference, current, *, reference_info, current_info):
    """Pure, strict comparison: only v2 info and manifest lineage may differ."""
    differences = {key for key, value in reference_info.items() if reference.get(key) != value}
    if (differences != {'source_admission'} or reference_info.get('source_admission') != 'CPU_PREPARE_ONLY'
            or not isinstance(reference.get('source_admission'), dict)
            or reference['source_admission'].get('status') != 'ADMISSIBLE'
            or reference.get('status') != 'BROAD_CPU_FROZEN' or reference.get('tag') != ORIGINAL_TAG
            or reference.get('model_loaded') is not False or reference.get('optimizer_updates') != 0
            or reference.get('checkpoints_written') != 0):
        raise ValueError('reference must be exactly the preserved metadata-key failure, not a completed experiment')
    if set(reference.get('manifests', {})) != {'train', 'dev', 'monitor', 'dialogues'}:
        raise ValueError('all four original wire populations required')
    expected = copy.deepcopy(reference)
    expected.update(current_info)
    for stem, manifest in expected['manifests'].items():
        if manifest.get('lineage') != dict(tag=ORIGINAL_TAG, stem=stem):
            raise ValueError('exact original v1 manifest lineage required')
        manifest['lineage'] = dict(tag=TAG, stem=stem)
    if legacy.sha(expected) != legacy.sha(current):
        raise ValueError('v2 changed source selection, course/count/target/order or non-lineage metadata')
    return {stem: dict(rows=manifest['rows'], bytes=manifest['bytes'],
                concat_sha256=manifest['concat_sha256'], shards_sha256=legacy.sha(manifest['shards']),
                reference_lineage=reference['manifests'][stem]['lineage'], new_lineage=manifest['lineage'])
            for stem, manifest in current['manifests'].items()}


def _equivalence_metadata():
    for relative, expected in REFERENCE_PINS.items():
        if legacy.digest(legacy.safe(ROOT / relative)) != expected:
            raise ValueError('preserved v1 partial/log/activity changed')
    reference = legacy.required(ORIGINAL_CACHE / 'frozen.json')
    current = legacy.required(CACHE / 'frozen.json')
    activity = legacy.required(ORIGINAL_EVIDENCE / 'activity_prepare.json')
    if activity.get('complete') is not False or activity.get('returncode') == 0:
        raise ValueError('v1 failure must remain a failure')
    with _attributes(TAG=ORIGINAL_TAG):
        reference_info = _INFO()
    payloads = compare_frozen(reference, current, reference_info=reference_info, current_info=info())
    old_course_sha = legacy.digest(legacy.safe(ORIGINAL_CACHE / 'course.json'))
    new_course_sha = legacy.digest(legacy.safe(CACHE / 'course.json'))
    if old_course_sha != reference['course_report_sha256'] or new_course_sha != old_course_sha:
        raise ValueError('byte-identical original course/group/schedule report required')
    course = legacy.required(CACHE / 'course.json')
    if (course['schema'] != legacy.builder.VERSION or course['selection_key'] != legacy.builder.SELECTION_KEY
            or course['groups_per_pass'] != 176 or course['updates'] != 352):
        raise ValueError('unchanged v1 selection and352-update geometry required')
    legacy.completed_activity('prepare')
    for stem in payloads:
        for directory, frozen in ((ORIGINAL_CACHE, reference), (CACHE, current)):
            actual = legacy.required(directory / 'wire' / (stem + '_shards_manifest.json'))
            if legacy.sha(actual) != legacy.sha(frozen['manifests'][stem]):
                raise ValueError('complete standalone wire manifest differs')
    return reference, current, course, payloads


def _expected_counts(current, course):
    return dict(train=dict(course['per_pass']['totals']),
                dev=dict(rows=current['dev_rows'], assistant_targets=current['dev_targets']),
                monitor=dict(rows=current['manifests']['monitor']['rows']),
                dialogues=dict(rows=current['manifests']['dialogues']['rows'],
                               source_turns=current['dialogue_source_turns']))


def _encoded_totals(directory, manifest):
    totals = Counter()
    for spec in manifest['shards']:
        with legacy.safe(directory / spec['path']).open(encoding='utf-8') as stream:
            for line in stream:
                record, metadata = legacy._unwire(json.loads(line))
                totals.update(rows=1, x_tokens=record.x_tokens, assistant_targets=record.targets,
                    assistant_turns=metadata['assistant_turns'],
                    content_targets=metadata['content_targets'], eot_targets=metadata['eot_targets'],
                    supervised_turns=metadata['supervised_turns'],
                    masked_positive_owner_tokens=metadata['masked_positive_owner_tokens'])
    return dict(totals)


def _equivalence_report(current, course, payloads):
    return dict(info(), status='BROAD_V1_PAYLOAD_EQUIVALENT', reference_pins=REFERENCE_PINS,
        frozen_sha256=legacy.digest(CACHE / 'frozen.json'),
        course_report_sha256=current['course_report_sha256'], payloads=payloads,
        verified_counts=_expected_counts(current, course),
        ordered_record_hashes_sha256=course['ordered_record_hashes_sha256'],
        schedules_sha256=course['schedules_sha256'],
        general_selection_sha256=legacy.sha(current['source_admission']['selected_source_indices']),
        dialogue_selection=current['dialogue_selection'],
        monitor_display_selection_sha256=current['monitor_display_selection_sha256'],
        original_prepare_complete=False, original_stage_returncode=9,
        scope='v1/v2 source selection, byte-identical wire lines/course; only manifest lineage and info differ',
        original_activity_scope='unchanged failed v1; v2 core activity and this adapter receipt are separate',
        model_loaded=False, optimizer_updates=0, checkpoints_written=0, model_quality='NOT_RUN')


def audit_equivalence():
    """Read-only full-byte/consumer audit, called only after root executes prepare."""
    reference, current, course, payloads = _equivalence_metadata()
    for stem in payloads:
        for directory, frozen in ((ORIGINAL_CACHE, reference), (CACHE, current)):
            legacy.verify(legacy.safe(directory / 'wire'), frozen['manifests'][stem])
    expected = _expected_counts(current, course)
    for stem in ('train', 'dev'):
        observed = _encoded_totals(CACHE / 'wire', current['manifests'][stem])
        if any(observed.get(key) != value for key, value in expected[stem].items()):
            raise ValueError('actual decoded x/assistant/content/EOT/mask consumer differs')
    dialogues = legacy._read('dialogues', current['manifests']['dialogues'])
    if sum(row['expected_source_turns'] for row in dialogues) != current['dialogue_source_turns']:
        raise ValueError('actual original dialogue turn population changed')
    return _equivalence_report(current, course, payloads)


def equivalence_path():
    return EVIDENCE / 'v1_payload_equivalence.json'


def equivalence_activity_path():
    return EVIDENCE / 'activity_recovery_equivalence.json'


def finish_prepare_equivalence(max_wall_sec, worker_began):
    """Record extra audit wall separately; legacy spent_seconds includes it."""
    if equivalence_path().exists() or equivalence_activity_path().exists():
        raise FileExistsError('preserve previous complete/partial recovery receipt')
    from scripts.p106b_gate_runtime import wall_limit
    began, code = time.perf_counter(), None
    try:
        available = min(max_wall_sec - (began - worker_began), legacy.authority(training=True),
            legacy.ACTIVE_LIMIT - legacy.spent_seconds() - legacy.EVAL_RESERVE - legacy.RECORD_RESERVE)
        if available < 60:
            raise legacy.Pending('full recovery audit plus unchanged stage/deadline reserves does not fit')
        with wall_limit(int(available)):
            report = audit_equivalence()
            legacy.write(equivalence_path(), report)
            code = 0
        print('[BROAD_RECOVERY_EQUIVALENT] full v1 payload/selection preserved; model/GPU NOT_RUN', flush=True)
    finally:
        path = equivalence_path()
        legacy.write(equivalence_activity_path(), dict(schema=RECOVERY_SCHEMA, tag=TAG,
            key='recovery_equivalence', complete=code == 0, returncode=code,
            code_sha256=info()['code_sha256'], seconds=time.perf_counter() - began,
            max_wall_sec=max_wall_sec, report_path=str(path.relative_to(ROOT)) if path.is_file() else None,
            report_sha256=legacy.digest(path) if path.is_file() else None,
            recorded_at=datetime.now(timezone.utc).isoformat(), scope=ACTIVITY_SCOPE))


def validate_equivalence():
    """Fail closed before model/GPU; v1 prepared() still rechecks all new bytes."""
    saved = legacy.required(equivalence_path())
    _, current, course, payloads = _equivalence_metadata()
    if legacy.sha(saved) != legacy.sha(_equivalence_report(current, course, payloads)):
        raise ValueError('same-code, exact-frozen recovery equivalence receipt required')
    activity = legacy.required(equivalence_activity_path())
    if (activity.get('schema') != RECOVERY_SCHEMA or activity.get('tag') != TAG
            or activity.get('key') != 'recovery_equivalence' or activity.get('scope') != ACTIVITY_SCOPE
            or activity.get('complete') is not True or type(activity.get('returncode')) is not int
            or activity['returncode'] != 0 or activity.get('code_sha256') != info()['code_sha256']
            or type(activity.get('seconds')) not in (int, float)
            or not math.isfinite(activity['seconds']) or activity['seconds'] < 0
            or type(activity.get('max_wall_sec')) is not int or not 60 <= activity['max_wall_sec'] <= 7200
            or activity.get('report_path') != str(equivalence_path().relative_to(ROOT))
            or activity.get('report_sha256') != legacy.digest(equivalence_path())):
        raise ValueError('completed exact-code/report recovery audit activity required')
    if datetime.fromisoformat(activity['recorded_at']).tzinfo is None:
        raise ValueError('aware recovery audit completion time required')
    return saved


def _route(argv):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mode'); parser.add_argument('--arm')
    parser.add_argument('--max-wall-sec', type=int, default=3600)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--check-only', action='store_true')
    args, unknown = parser.parse_known_args(argv)
    # Let the unchanged CLI own unknown/missing/conflicting-argument diagnostics.
    if (unknown or args.mode not in legacy.MODES or args.execute == args.check_only
            or args.arm is not None and args.arm not in legacy.ARMS):
        return None
    phase_commands(args.mode, args.arm, args.max_wall_sec)
    return args


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        with runtime_scope():
            args = _route(argv)
            if (args is not None and args.worker and args.execute
                    and args.mode not in ('source', 'prepare')):
                validate_equivalence()
            began = time.perf_counter()
            code = legacy.main(argv)
            if code == 0 and args is not None and args.worker and args.execute and args.mode == 'prepare':
                finish_prepare_equivalence(args.max_wall_sec, began)
            return code
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        status, code = legacy.monitor.base.failure_status(exc)
        if code == 9:
            import traceback
            traceback.print_exc()
        print('[BROAD_RECOVERY_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
