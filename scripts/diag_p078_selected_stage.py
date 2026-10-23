#!/usr/bin/env python3
"""Explicit two-of-four P078 admission; original training and ledgers unchanged.

The orchestrator chooses uniform_r2 + balanced_count before their main results.
All four cost receipts and all historical family activity remain accounted for.
Only the pending admission set changes, publicly and with a pinned descriptor.
This adapter never executes a router or claims the original four-arm readback.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import types
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p078_route_protocol as protocol

SCRIPT = 'scripts/diag_p078_selected_stage.py'
TEST = 'scripts/test_p078_selected_stage.py'
TAG = 'p078_selected_stage_v1_s1337'
SCHEMA = 'P078_SELECTED_STAGE_ADMISSION_V1'
SELECTED = ('uniform_r2', 'balanced_count')
DEFERRED = ('fixed_shuffle_r2', 'update_shuffle_r2')
ORIGINAL_ARMS = ('uniform_r2', 'fixed_shuffle_r2', 'update_shuffle_r2', 'balanced_count')
FAMILY_CAP = 144000
HARD_STOP = datetime(2026, 10, 22, 8, tzinfo=timezone.utc)  # 17:00 KST.


def utc_now():
    return datetime.now(timezone.utc)


def source_identity():
    result = protocol.source_identity()
    result.update({name: protocol.identity(name) for name in (SCRIPT, TEST)})
    return result


def source_hashes(sources):
    return {name: value['sha256'] for name, value in sources.items()}


def sha_string(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789ABCDEF' for c in value)


def aware(value):
    if not isinstance(value, str):
        raise ValueError('explicit timezone-aware timestamp required')
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('naive execution timestamp refused')
    return result


def descriptor_bytes(args):
    if (not isinstance(args.selection, str) or not args.selection.startswith('handoff/audit/')
            or not sha_string(args.selection_sha256)):
        raise ValueError('root-owned selection descriptor and uppercase SHA256 required')
    identity = protocol.identity(args.selection)
    raw = protocol.safe(args.selection).read_bytes()
    if identity['sha256'] != args.selection_sha256 or hashlib.sha256(raw).hexdigest().upper() != identity['sha256']:
        raise ValueError('selection descriptor bytes changed')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('selection descriptor must be a JSON object')
    return value


def validate_descriptor(value, args, driver, sources, now=None):
    now = utc_now() if now is None else now
    info = driver.signature(args)
    if (tuple(driver.route.ARMS) != ORIGINAL_ARMS or args.corpus != driver.CLEAN_CORPUS
            or not sha_string(args.corpus_sha256)
            or value.get('schema') != SCHEMA or value.get('tag') != TAG
            or value.get('decision_owner') != 'ROOT_EXECUTION_PRIORITIZATION'
            or value.get('selected_arms') != list(SELECTED) or value.get('deferred_arms') != list(DEFERRED)
            or value.get('original_input_signature_sha256') != driver.route.sha(info)
            or value.get('adapter_source_sha256') != source_hashes(sources)
            or value.get('corpus_sha256') != args.corpus_sha256
            or value.get('max_family_seconds') != FAMILY_CAP
            or type(value.get('reserve_seconds')) is not int or value['reserve_seconds'] < 1800
            or value.get('router_execution') is not False
            or not isinstance(value.get('reason'), str) or not value['reason'].strip()):
        raise ValueError('exact original-family/two-stage/source/corpus admission contract required')
    created, expires = aware(value.get('created_at')), aware(value.get('expires_at'))
    if not created <= now < expires <= HARD_STOP:
        raise driver.Hold('selection must be issued before execution and expire by today17:00 KST')
    remaining = driver.authority(args, info)
    auth = driver.read(args.authorization)
    if (auth.get('selected_stage_descriptor') != args.selection
            or auth.get('selected_stage_sha256') != args.selection_sha256
            or auth.get('selected_stage_adapter_sha256') != sources[SCRIPT]['sha256']
            or aware(auth.get('expires_at')) > expires):
        raise ValueError('fresh original authority must explicitly bind this selection and adapter')
    return value, info, remaining


def load_selection(args, driver):
    sources = source_identity()
    value, info, remaining = validate_descriptor(descriptor_bytes(args), args, driver, sources)
    return value, sources, info, remaining


def worker_cap_preflight(args, driver):
    """Reject a known-bad cap before the original worker creates activity.

    The original worker repeats its own authority/family/PGID checks. This
    early check neither replaces those checks nor increases their limits.
    """
    _, _, info, remaining = load_selection(args, driver)
    spent = driver.actual_spent(args, info)
    if (any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in (remaining, spent))
            or args.max_wall_sec > remaining or spent + args.max_wall_sec > FAMILY_CAP):
        raise driver.Hold('original whole worker cap/current deadline/family40h cannot be weakened')


def selected_budget(args, driver, original_budget):
    selection, sources, info, remaining = load_selection(args, driver)
    # A false all-pending forecast is retained. Exceptions (bad cost/resource,
    # failed activity, expired authority or changed source) are NEVER waived.
    full = original_budget(args)
    report = driver.inputs(args)
    if driver.update_count(report) != 704 or report['manifests']['train']['rows'] != 22528:
        raise ValueError('selected study requires the complete22528x4/704 course')
    spent = driver.actual_spent(args, info)
    if spent != full['actual_spent_seconds']:
        raise ValueError('all original family activity must remain in the same time ledger')
    completed = []
    for arm in ORIGINAL_ARMS:
        result = driver.path(driver.report_name('train', arm, args))
        activity = driver.path(driver.activity_name('train', arm, args))
        if result.exists() or activity.exists():
            value = driver.closed(args, 'train', arm)
            if arm in DEFERRED:
                raise driver.Hold('a deferred main stage already exists; do not retrospectively select a two-arm study')
            auth = value.get('authorization', {})
            if (auth.get('selected_stage_descriptor') != args.selection
                    or auth.get('selected_stage_sha256') != args.selection_sha256):
                raise ValueError('completed selected training belongs to another admission')
            completed.append(arm)
    train = {arm: full['train_forecast_seconds'][arm] for arm in SELECTED}
    evaluation = {arm: full['evaluation_forecast_seconds'][arm] for arm in SELECTED}
    pending = sum(train.values()) + sum(evaluation.values()) + selection['reserve_seconds']
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
           for v in (spent, pending, remaining, *train.values(), *evaluation.values())):
        raise ValueError('finite nonnegative original cost/time forecasts required')
    fits = spent + pending <= FAMILY_CAP and pending <= remaining
    cost_sources = {arm: dict(report_sha256=driver.digest(driver.path(driver.report_name('cost', arm, args))),
        activity_sha256=driver.digest(driver.path(driver.activity_name('cost', arm, args)))) for arm in ORIGINAL_ARMS}
    return dict(status='SELECTED_STAGE_BUDGET_READY' if fits else 'HOLD_SELECTED_STAGE_BUDGET', fits=fits,
        selection_descriptor=args.selection, selection_sha256=args.selection_sha256,
        adapter_source_sha256=source_hashes(sources), original_input_signature_sha256=driver.route.sha(info),
        original_all_pending_forecast=full, selected_arms=list(SELECTED), deferred_arms=list(DEFERRED),
        selected_completed=completed, completed_original_arms=len(completed), original_arms=4,
        original_four_arm_study_complete=False, actual_spent_seconds=spent, family_cap_seconds=FAMILY_CAP,
        train_forecast_seconds=train, evaluation_forecast_seconds=evaluation,
        deferred_forecast_seconds={arm: dict(train=full['train_forecast_seconds'][arm],
            evaluation=full['evaluation_forecast_seconds'][arm]) for arm in DEFERRED},
        reserve_seconds=selection['reserve_seconds'], total_pending_seconds=pending,
        remaining_authority_seconds=remaining, all_four_cost_receipts=cost_sources, router_execution=False,
        scope='EXPLICIT_ORCHESTRATOR_SELECTION; forecasts not runtime/quality guarantees')


def single_arm_verifier(driver):
    """Project the pinned original reader's per-arm body, never shrink ARMS.

    Prefix setup and the exact body of `for arm in route.ARMS` are reused.
    The original all-four final result and its completion status are excluded.
    No training/model function is extracted or rewritten.
    """
    tree = ast.parse(protocol.safe('scripts/diag_p078_route_training.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'readback')
    loops = [(i, n) for i, n in enumerate(node.body) if isinstance(n, ast.For)]
    if len(loops) != 1 or ast.unparse(loops[0][1].iter) != 'route.ARMS' or ast.unparse(loops[0][1].target) != 'arm':
        raise ValueError('pinned original per-arm reader structure changed')
    index, loop = loops[0]
    projected = copy.deepcopy(node)
    projected.name = '_verify_selected_original_arm'
    projected.args.args.append(ast.arg(arg='arm'))
    projected.body = copy.deepcopy(node.body[:index] + loop.body)
    projected.body.append(ast.Return(value=ast.Subscript(value=ast.Name(id='results', ctx=ast.Load()),
        slice=ast.Name(id='arm', ctx=ast.Load()), ctx=ast.Load())))
    module = ast.fix_missing_locations(ast.Module(body=[projected], type_ignores=[]))
    namespace = dict(vars(driver))
    exec(compile(module, 'PINNED_P078_PER_ARM_READER', 'exec'), namespace)
    return namespace[projected.name]


def partial_readback(args, driver, original_budget):
    admission = selected_budget(args, driver, original_budget)
    if not admission['fits']:
        raise driver.Hold('selected closure/reserve no longer fits current authority')
    if admission['selected_completed'] != [a for a in ORIGINAL_ARMS if a in SELECTED]:
        raise driver.Hold('both selected complete training stages are required')
    verifier = single_arm_verifier(driver)
    results = {}
    for arm in SELECTED:
        closed = driver.closed(args, 'train', arm)
        if (closed.get('status') != 'ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED'
                or closed.get('updates') != 704 or closed.get('checkpoint_writes') != 1
                or closed.get('checkpoint') != driver.cp_name(arm, args)):
            raise ValueError('complete original704/report/activity/checkpoint required')
        with protocol.normalized_plans(driver.route):
            results[arm] = verifier(args, arm)
    for key in ('initial_core_sha256', 'actual_x_tokens', 'assistant_targets'):
        if len({r[key] for r in results.values()}) != 1:
            raise ValueError('selected pair parent/data/target exposure differs')
    return dict(status='SELECTED_TWO_OF_FOUR_RAW_RECOUNTED_NO_ADOPTION', results=results,
        admission=admission, selected_complete=2, original_total=4, deferred_arms=list(DEFERRED),
        original_four_arm_readback='NOT_RUN; original reader still requires all four',
        original_four_arm_study_complete=False, router_execution=False, model_loads=0,
        checkpoint_tensor_loads=0, semantic_quality='RAW_ANSWERS_STILL_REQUIRE_CONTENT_REVIEW')


@contextmanager
def admission_scope(driver, args):
    if tuple(driver.route.ARMS) != ORIGINAL_ARMS:
        raise ValueError('original four arms must not change')
    # Keep the existing JSON-only verification adapter. Actual train/forward
    # always uses the original tuple-based route.plan implementation.
    with protocol.verification_scope(driver):
        full_budget = driver.budget
        def budget(actual_args): return selected_budget(actual_args, driver, full_budget)
        with patch.object(driver, 'budget', budget):
            if args.mode == 'readback':
                with patch.object(driver, 'readback', lambda actual_args: partial_readback(actual_args, driver, full_budget)):
                    yield
            else:
                yield


def metadata(driver, args):
    result = protocol.original_metadata(driver, args)
    for arm in SELECTED:
        for name in (driver.report_name('selected_readback', arm, args),
                     driver.activity_name('selected_readback', arm, args)):
            if protocol.safe(name).exists(): result[name] = protocol.identity(name)
    return result


def write_receipt(value):
    stamp = utc_now().strftime('%Y%m%dT%H%M%S%fZ')
    relative = 'test_result/evidence/' + TAG + '/' + stamp + '_' + uuid.uuid4().hex + '.json'
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(raw) >= protocol.MAX_METADATA:
        raise ValueError('selected admission receipt must stay below20MB')
    target = protocol.safe(relative); target.parent.mkdir(parents=True, exist_ok=True)
    with protocol.safe(relative).open('xb') as stream: stream.write(raw)
    print('[P078_SELECTED_RECEIPT] ' + relative, flush=True)
    return relative


def recorded(driver, args, argv, action, role, details=None):
    sources = source_identity(); before = metadata(driver, args)
    details = {} if details is None else details
    code = 9; error = None
    try:
        code, result_details = action()
        details.update(result_details)
        if type(code) is not int:
            raise ValueError('explicit integer worker returncode required')
    except driver.Hold as exc:
        code, error = 8, str(exc)
    except KeyboardInterrupt:
        code, error = 130, 'KeyboardInterrupt'
    except Exception as exc:
        code, error = 9, type(exc).__name__ + ': ' + str(exc)
    finally:
        after = {}
        try:
            after = metadata(driver, args); protocol.unchanged(before, after)
            if source_identity() != sources:
                raise ValueError('original/protocol/selected adapter source changed during stage')
        except Exception as exc:
            code, error = 9, type(exc).__name__ + ': ' + str(exc)
        write_receipt(dict(schema=SCHEMA, tag=TAG, role=role, argv=list(argv),
            selection_descriptor=args.selection, selection_sha256=args.selection_sha256,
            adapter_source_sha256=source_hashes(sources), original_metadata_before=before,
            original_metadata_after=after, original_existing_metadata_unchanged=all(after.get(k) == v for k, v in before.items()),
            original_arms=list(ORIGINAL_ARMS), selected_arms=list(SELECTED), deferred_arms=list(DEFERRED),
            admission_policy_changed=True, original_training_changed=False, original_authority_override=False,
            original_four_arm_readback_invoked=False, router_execution=False, returncode=code, error=error, details=details))
    if error: print('[P078_SELECTED_ERROR] ' + error, flush=True)
    return code


def launch(argv, seconds):
    # Reuse the exact original protocol PGID/DEVNULL/timeout/TERM/KILL function
    # body with only its entry script global changed. Child re-enters THIS file
    # and reinstalls admission_scope; process-local patches are not assumed to
    # survive exec. No original module global/source/PINS is modified.
    namespace = dict(protocol.launch.__globals__, SCRIPT=SCRIPT)
    original_launch = types.FunctionType(protocol.launch.__code__, namespace,
        protocol.launch.__name__, protocol.launch.__defaults__, protocol.launch.__closure__)
    return original_launch(argv, seconds)


def parser_for(driver):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('budget-preview', 'train', 'readback'), required=True)
    parser.add_argument('--arm', choices=SELECTED, default=SELECTED[0])
    parser.add_argument('--selection'); parser.add_argument('--selection-sha256')
    parser.add_argument('--corpus', choices=(driver.CLEAN_CORPUS,), default=driver.CLEAN_CORPUS)
    parser.add_argument('--corpus-sha256')
    parser.add_argument('--adam-lr', type=float, default=5e-5); parser.add_argument('--muon-lr', type=float, default=2e-4)
    parser.add_argument('--authorization'); parser.add_argument('--authorization-sha256')
    parser.add_argument('--max-wall-sec', type=int, default=1800); parser.add_argument('--worker', action='store_true')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true'); action.add_argument('--execute', action='store_true')
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        driver = protocol.load_driver(); args = parser_for(driver).parse_args(argv)
        if args.check_only:
            print('[STATIC_ONLY_SELECTED] ' + json.dumps(dict(schema=SCHEMA, tag=TAG,
                adapter_source_sha256=source_hashes(source_identity()),
                original_input_signature_sha256=driver.route.sha(driver.signature(args)),
                selected_arms=list(SELECTED), deferred_arms=list(DEFERRED), original_arms=list(driver.route.ARMS),
                hard_stop_utc=HARD_STOP.isoformat(), family_cap_seconds=FAMILY_CAP,
                model_loads=0, corpus_reads=0, router_execution=False)), flush=True)
            return 0
        if (not driver.READY or not 60 <= args.max_wall_sec <= FAMILY_CAP
                or any(not math.isfinite(v) or v <= 0 for v in (args.adam_lr, args.muon_lr))):
            raise driver.Hold('original readiness/LR/whole worker cap conditions remain required')
        load_selection(args, driver)
        if args.mode == 'budget-preview':
            def preview():
                with admission_scope(driver, args): result = driver.budget(args)
                print('[SELECTED_BUDGET_PREVIEW] ' + json.dumps(result, ensure_ascii=False), flush=True)
                return (0 if result['fits'] else 8), result
            return recorded(driver, args, argv, preview, 'READ_ONLY_SELECTED_ADMISSION_PREVIEW')
        if args.worker:
            details = {}
            def work():
                worker_cap_preflight(args, driver)
                worker_args = copy.copy(args)
                if args.mode == 'readback': worker_args.mode = 'selected_readback'
                with admission_scope(driver, args):
                    details['pre_execution_admission'] = driver.budget(args)
                    if not details['pre_execution_admission']['fits']:
                        raise driver.Hold('selected pending work does not fit; original worker not started')
                    code = driver.worker(worker_args)
                return code, dict(original_worker=True, effective_mode=worker_args.mode,
                    selected_arms=list(SELECTED), completion_scope='TWO_OF_ORIGINAL_FOUR')
            return recorded(driver, args, argv, work, 'OWNED_SELECTED_WORKER', details)
        details = {}
        def parent():
            worker_cap_preflight(args, driver)
            with admission_scope(driver, args): details['pre_execution_admission'] = driver.budget(args)
            if not details['pre_execution_admission']['fits']:
                raise driver.Hold('selected pending work does not fit; child not started')
            return launch(argv, args.max_wall_sec), dict(child_entry=SCRIPT, child_reinstalls_admission=True)
        return recorded(driver, args, argv, parent, 'SELECTED_PARENT_LAUNCH', details)
    except Exception as exc:
        code = 8 if 'driver' in locals() and isinstance(exc, driver.Hold) else 9
        print('[P078_SELECTED_ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
