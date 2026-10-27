"""Explicit historical704-body lineage, distinct from a current execution.

No import-time model/data reads. A root-pinned profile binds both source maps,
the unchanged historical receipts, CPU equivalence, and dedicated CP header.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import tinylm

from scripts import diag_p078_route_training as base

SCHEMA = 'P078_HISTORICAL_BODY_BRIDGE_V1'
ALLOWED = {'tinylm/train/mtp_sft.py', 'scripts/diag_p078_route_training.py'}


def selected(args):
    path = getattr(args, 'profile', None)
    digest = getattr(args, 'profile_sha256', None)
    if bool(path) != bool(digest):
        raise ValueError('body bridge requires both explicit profile and SHA')
    if path and getattr(args, 'resource_only_r1', False):
        raise ValueError('historical704 bridge cannot use resource-only R1')
    return bool(path)


def pinned(spec):
    if not isinstance(spec, dict) or set(spec) != {'path', 'sha256'}:
        raise ValueError('exact path/SHA bridge input required')
    path = base.path(spec['path'])
    if base.digest(path) != spec['sha256']:
        raise ValueError('bridge input bytes changed: ' + spec['path'])
    return base.read(spec['path'])


def compare_sources(historical, current, declared):
    old = historical['source_sha256']; new = current['source_sha256']
    if set(old) != set(new) or len(old) != 44:
        raise ValueError('historical/current exact44-source set differs')
    if {k: v for k, v in historical.items() if k != 'source_sha256'} != {
            k: v for k, v in current.items() if k != 'source_sha256'}:
        raise ValueError('historical corpus/tokenizer/recipe/body contract differs')
    changed = {p: dict(historical=old[p], current=new[p]) for p in old if old[p] != new[p]}
    if set(changed) != ALLOWED or changed != declared:
        raise ValueError('undeclared historical/current source transition')
    return changed


def contract(args):
    if not selected(args) or not str(args.profile).startswith('handoff/audit/'):
        raise ValueError('explicit root audit body bridge required')
    if base.digest(base.path(args.profile)) != args.profile_sha256:
        raise ValueError('root bridge profile SHA differs')
    profile = base.read(args.profile)
    if (profile.get('schema') != SCHEMA or profile.get('root_approved') is not True
            or profile.get('authority_directive') != 96 or profile.get('arm') != 'balanced_count'
            or profile.get('body_training_here') is not False):
        raise ValueError('root historical704 bridge contract differs')
    report = pinned(profile['historical_report'])
    activity = pinned(profile['historical_activity'])
    historical = report['input']; current = base.signature(args)
    changes = compare_sources(historical, current, profile['source_transitions'])
    if current['source_sha256'] != profile['current_body_source_sha256']:
        raise ValueError('root-approved current body sources differ')
    base.validate_closed_receipt(report, activity, historical,
        report_sha256=profile['historical_report']['sha256'], expected_tag=base.namespace(args))
    proof = pinned(profile['compatibility_proof'])
    if (proof.get('schema') != 'P078_BODY_COMPATIBILITY_V1'
            or proof.get('reference_cpu_cases') != 24
            or proof.get('reference_module_ast_equal') is not True
            or proof.get('validator_guard_ast_equal') is not True
            or proof.get('header_guard_ast_equal') is not True
            or proof.get('remaining_driver_ast_equal') is not True
            or proof.get('holdout_reader_ast_equal') is not True
            or proof.get('old_source_sha256') != historical['source_sha256']
            or proof.get('current_source_sha256') != current['source_sha256']):
        raise ValueError('exact CPU/reference/validator compatibility proof absent')
    for spec in proof['proof_inputs']:
        if base.digest(base.path(spec['path'])) != spec['sha256']:
            raise ValueError('compatibility proof source/CPU evidence changed')
    checkpoint = base.cp_name('balanced_count', args)
    if (report.get('status') != 'ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED'
            or report.get('updates') != 704 or report.get('checkpoint_writes') != 1
            or report.get('arm') != 'balanced_count' or report.get('checkpoint') != checkpoint
            or report.get('checkpoint_sha256') != profile['checkpoint_sha256']
            or report.get('final_core_sha256') != profile['core_sha256']
            or not base.path(checkpoint).is_file()):
        raise ValueError('original full704 checkpoint lineage differs')
    binding = dict(schema=SCHEMA, profile=args.profile, profile_sha256=args.profile_sha256,
        historical_report=profile['historical_report'], historical_activity=profile['historical_activity'],
        compatibility_proof=profile['compatibility_proof'], source_transitions=changes,
        historical_input_sha256=base.route.sha(historical), current_input_sha256=base.route.sha(current),
        historical_training_is_not_current_reproduction=True)
    return profile, report, binding


def read_holdout(args):
    profile, _, _ = contract(args)
    from scripts import p078_router_holdout_data as holdout
    report = pinned(profile['historical_holdout_report'])
    pinned(profile['historical_holdout_activity'])
    if profile['historical_holdout_report']['sha256'] != args.holdout_sha256:
        raise ValueError('current router holdout SHA is not the original512 report')
    old = report['source_sha256']
    current = {p:base.digest(base.path(p)) for p in holdout.CODE}
    if set(old) != set(current) or len(old) != 47:
        raise ValueError('exact historical/current47 holdout producer sources required')
    changes = {p:dict(historical=old[p],current=current[p]) for p in old if old[p]!=current[p]}
    if (set(changes) != ALLOWED|{'scripts/p078_router_holdout_data.py'}
            or changes != profile['holdout_source_transitions']):
        raise ValueError('undeclared historical holdout reader/source transition')
    return holdout.read_prepared_contract(args.holdout_sha256,args.corpus_sha256,expected_source_sha256=old)


def close_owned_body(model, torch, fingerprint, core, checkpoint, checkpoint_sha256, cuda, primary_error=None):
    """Attempt every check/release; never replace an existing body exception."""
    import gc
    errors=[]; attempted=[]
    def verify_core():
        if fingerprint(model)!=core:raise ValueError('original frozen body core changed')
    def verify_checkpoint():
        if base.digest(checkpoint)!=checkpoint_sha256:raise ValueError('original body CP bytes changed')
    actions=[('final_core',verify_core),('checkpoint_bytes',verify_checkpoint),
        ('clear_quant',model.clear_quant),('gc',gc.collect)]
    if cuda:actions.append(('empty_cache',torch.cuda.empty_cache))
    for name,action in actions:
        attempted.append(name)
        try:action()
        except BaseException as exc:
            errors.append(dict(stage=name,type=type(exc).__name__,message=str(exc)[:1000]))
    if errors:
        details=dict(primary_error=None if primary_error is None else
            dict(type=type(primary_error).__name__,message=str(primary_error)[:1000]),
            exit_errors=errors,attempted=attempted,process_exit_releases_body_parameters=True)
        import json
        print('[P078_BODY_EXIT] '+json.dumps(details),flush=True)
        error=primary_error if primary_error is not None else RuntimeError('body exit verification/cleanup failed')
        error.p078_body_exit_details=details
        if primary_error is None:raise error


def body_evidence(args):
    profile, report, binding = contract(args)
    return dict(checkpoint=report['checkpoint'], checkpoint_sha256=profile['checkpoint_sha256'],
        core_sha256=profile['core_sha256'], closed_report_sha256=profile['historical_report']['sha256'],
        closed_activity_sha256=profile['historical_activity']['sha256'], scientific_body=True,
        historical_lineage_bridge=binding)


@contextmanager
def loaded(args):
    """Same route factory/geometry; exact old header and actual current core."""
    profile, report, _ = contract(args)
    base.route.import_guard()
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.infer.generate import _strip
    from scripts import diag_p101a_sft_mtp as reference

    raw = base.path(base.TOKENIZER).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != base.TOK_SHA:
        raise ValueError('original body tokenizer changed')
    tokenizer = Tokenizer.from_str(raw.decode())
    if (tokenizer.get_vocab_size() != 32768 or
            tuple(tokenizer.token_to_id(t) for t in ('<|im_start|>', '<|im_end|>', '<eos>')) != (3, 4, 2)):
        raise ValueError('original chat32 vocabulary required')
    checkpoint = base.path(report['checkpoint'])
    with checkpoint.open('rb') as stream:
        before = os.fstat(stream.fileno()); digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
        if digest.hexdigest().upper() != profile['checkpoint_sha256']:
            raise ValueError('original full704 CP bytes changed')
        stream.seek(0)
        state = torch.load(stream, map_location='cpu', weights_only=True)
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('full704 CP changed during read')
    base.validate_student_header(state, updates=704, tokenizer_sha256=base.TOK_SHA,
        arm='balanced_count', expected_input=report['input'])
    if base.route.sha(state['cfg']) != base.route.sha(report['student_cfg']):
        raise ValueError('full704 actual configuration differs from original report')
    policy = base.route.Policy('balanced_count')
    config = dict(state['cfg'], grad_checkpoint=True, mtp_aux=False, train_repeat=float(policy.cap),
        infer_repeat=1., repeat_mode='uniform')
    cfg = TMTConfig(**config)
    if cfg.n_layers != 14 or cfg.dim != 768 or cfg.tie_mlp or cfg.max_seq_len != 1024:
        raise ValueError('exact original dense14 geometry required')
    torch.manual_seed(1337)
    model = base.route.build_model(cfg, policy)
    model.load_state_dict(_strip(state['model']), strict=True)
    del state
    core = reference.state_fingerprint(model)
    if core != profile['core_sha256']:
        raise ValueError('current frozen loader changed actual closed body core')
    cuda = False; primary_error = None
    try:
        base.idle()
        if not torch.cuda.is_available():
            raise base.Hold('current scientific bridge requires CUDA, no CPU quality fallback')
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        model = model.cuda(); cuda = True
        yield torch, model, cfg, tokenizer, core, reference
    except BaseException as exc:
        primary_error=exc
        raise
    finally:
        try:
            close_owned_body(model,torch,reference.state_fingerprint,core,checkpoint,profile['checkpoint_sha256'],cuda,primary_error)
        finally:
            model=None
