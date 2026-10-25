#!/usr/bin/env python3
"""Opt-in actual-gradient/NS diagnostic. Never an intelligence or speed gate.

Source-only inspection imports no torch and opens no model/data assets. Execution
owns a new deadline/namespace; historical helpers, Muon and trainers are unchanged.
All tensor captures stay in bounded CPU RAM. Only statistics/hashes are written.
"""
from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timezone
import gc
import inspect
import json
from pathlib import Path
import sys
import time
import types
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p101a_padding_gpu as old
from scripts import diag_p102a_streaming_head as head

SCRIPT = 'scripts/diag_p102a_head_muon_trace.py'
TEST = 'scripts/test_p102a_head_muon_trace.py'
TAG = 'p102a_head_muon_trace_v1_s1337'
SCHEMA = 'P102A_HEAD_MUON_TRACE_V1'
HARD_STOP = datetime.fromisoformat('2026-10-24T08:40:00+09:00').astimezone(timezone.utc)
CPU_CAPTURE_LIMIT = 8 * 2**30
CPU_SCRATCH_RESERVE = 2**30
CPU_SYSTEM_RESERVE = 2 * 2**30
MAX_BYTES = 19_999_999
REPRESENTATIVES = ('emb_up.weight', 'layers.0.attn.k_proj.weight',
                   'coda_mlps.1.down_proj.weight')
MUON_KEYS = ('lr', 'momentum', 'nesterov', 'ns_steps', 'weight_decay', 'scale_mode')


def sources(root=ROOT):
    """Code only; do not import the execution engine or examine asset paths."""
    result = old.source_manifest(root)
    for name in (*head.NEW_SOURCES, 'scripts/diag_p102a_streaming_head.py', SCRIPT, TEST):
        path = old.safe_path(name, root)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('source exceeds the per-file bound: ' + name)
        result[name] = old.digest(path)
    return dict(sorted(result.items()))


def validate_execution(args, now=None):
    now = old.utc_now() if now is None else now
    deadline = old.aware(args.deadline)
    if not now < deadline <= HARD_STOP:
        raise ValueError('deadline must be current and no later than 2026-10-24 08:40 KST')
    if type(args.max_wall_sec) is not int or not 60 <= args.max_wall_sec <= 1200:
        raise ValueError('wall bound must be 60..1200 seconds')
    if (deadline - now).total_seconds() < args.max_wall_sec:
        raise ValueError('full wall reservation does not fit before the deadline')
    return deadline


def output_path(root=ROOT):
    target = old.safe_path('test_result/evidence/' + TAG, root)
    if target.exists() or target.is_symlink():
        raise FileExistsError('existing evidence namespace is preserved')
    return target


def check(guard, stage):
    if guard is not None:
        guard.check(stage)


def cpu_clone(value):
    return value.detach().cpu().clone()


def tensor_bytes(values):
    return sum(value.numel() * value.element_size() for value in values.values())


def memory_plan(model, muon):
    matrices, _ = muon.split_params(model)
    state_bytes = tensor_bytes(model.state_dict())
    all_bytes = sum(p.numel() * p.element_size() for p in model.parameters() if p.requires_grad)
    matrix_bytes = sum(p.numel() * p.element_size() for p in matrices)
    # Per arm: raw157 + clipped157 + NSinput/output/buffer/updated85.
    estimate = state_bytes + 2 * (2 * all_bytes + 4 * matrix_bytes) + CPU_SCRATCH_RESERVE
    if len(matrices) != 85 or estimate > CPU_CAPTURE_LIMIT:
        raise ValueError('expected85 matrices and CPU capture+scratch <=8GiB required')
    available = None
    meminfo = Path('/proc/meminfo')
    if meminfo.is_file():
        for line in meminfo.read_text(encoding='ascii').splitlines():
            if line.startswith('MemAvailable:'):
                available = int(line.split()[1]) * 1024
                break
    if available is not None and available < estimate + CPU_SYSTEM_RESERVE:
        raise MemoryError('insufficient available CPU RAM for complete captures and system reserve')
    return dict(initial_bytes=state_bytes, all_parameter_bytes=all_bytes,
        muon_parameter_bytes=matrix_bytes, estimated_capture_and_scratch_bytes=estimate,
        capture_limit_bytes=CPU_CAPTURE_LIMIT, scratch_reserve_bytes=CPU_SCRATCH_RESERVE,
        system_reserve_bytes=CPU_SYSTEM_RESERVE, available_bytes_at_preflight=available,
        policy='CPU_RAM_ONLY_NO_TENSOR_FILES; abort instead of dropping gradients')


class GlobalIdentity:
    """Observe original namespace and class-step identity, never patch them."""
    def __init__(self, muon):
        self.muon = muon
        self.namespace = dict(vars(muon))
        self.step = muon.Muon.step
        self.code = inspect.unwrap(self.step).__code__

    def check(self):
        now = vars(self.muon)
        if (set(now) != set(self.namespace)
                or any(now[name] is not value for name, value in self.namespace.items())
                or self.muon.Muon.step is not self.step
                or inspect.unwrap(self.muon.Muon.step).__code__ is not self.code):
            raise ValueError('original Muon globals/function/class step changed')


def private_muon_step(torch, optimizer, observer):
    """Same original step bytecode and profiling/hooks, private NS binding only."""
    original = inspect.unwrap(type(optimizer).step)
    if '_newton_schulz' not in original.__code__.co_names:
        raise ValueError('registered original Muon step body required')
    namespace = dict(original.__globals__)
    namespace['_newton_schulz'] = observer
    private = types.FunctionType(original.__code__, namespace, original.__name__,
                                 original.__defaults__, original.__closure__)
    private.__kwdefaults__ = copy.copy(original.__kwdefaults__)
    wrapped = torch.optim.Optimizer.profile_hook_step(torch.no_grad()(private))
    if inspect.unwrap(wrapped).__code__ is not original.__code__:
        raise ValueError('private step bytecode differs')
    def call(*args, **kwargs):
        return wrapped(optimizer, *args, **kwargs)
    return call


def validate_ns_interface(function):
    """Facade is safe only while the pinned original reads G.cast and G.dtype."""
    tree = ast.parse(inspect.getsource(inspect.unwrap(function)))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    attributes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == 'G' and isinstance(node.ctx, ast.Load):
            parent = parents.get(node)
            if not isinstance(parent, ast.Attribute) or parent.value is not node:
                raise ValueError('original NS uses G outside the audited facade interface')
            attributes.append(parent.attr)
    if sorted(attributes) != ['bfloat16', 'dtype']:
        raise ValueError('original NS input interface changed')


class FP32NSInput:
    """Diagnostic only: replace one cast; original NS owns all remaining math."""
    def __init__(self, gradient):
        self.gradient = gradient

    @property
    def dtype(self):
        return self.gradient.dtype

    def bfloat16(self):
        return self.gradient.float()


def ns_value(torch, original, value, *, fp32=False, steps=5):
    if value.dtype != torch.float32 or value.ndim != 2:
        raise ValueError('FP32 matrix NS input required')
    with torch.autocast(device_type=value.device.type, enabled=False):
        return original(FP32NSInput(value) if fp32 else value, steps=steps)


class NSObserver:
    def __init__(self, torch, original, order, *, guard=None, fp32=False):
        self.torch, self.original, self.order = torch, original, tuple(order)
        self.guard, self.fp32 = guard, fp32
        self.inputs, self.outputs, self.metadata = {}, {}, {}

    def __call__(self, value, *, steps=5):
        check(self.guard, 'before observed NS')
        index = len(self.inputs)
        if index >= len(self.order) or steps != 5:
            raise ValueError('unexpected NS call count or iteration count')
        name = self.order[index]
        if name in self.inputs or self.torch.is_autocast_enabled(value.device.type):
            raise ValueError('duplicate NS matrix or unexpected optimizer autocast')
        self.inputs[name] = cpu_clone(value)
        answer = ns_value(self.torch, self.original, value, fp32=self.fp32, steps=steps)
        self.outputs[name] = cpu_clone(answer)
        self.metadata[name] = dict(shape=list(value.shape), input_stride=list(value.stride()),
            output_stride=list(answer.stride()), input_dtype=str(value.dtype),
            internal_dtype='float32_DIAGNOSTIC_ONLY' if self.fp32 else 'original_bfloat16', steps=steps)
        check(self.guard, 'after observed NS')
        return answer

    def finish(self):
        if tuple(self.inputs) != self.order or tuple(self.outputs) != self.order:
            raise ValueError('not every actual Muon matrix reached NS')


class PostClipCapture:
    def __init__(self, parameters, expected=157):
        self.parameters, self.expected = dict(parameters), expected
        self.values = None

    def capture(self):
        if self.values is not None:
            return
        if (len(self.parameters) != self.expected
                or any(p.grad is None for p in self.parameters.values())):
            raise ValueError('complete non-None postclip gradient set required')
        self.values = {name: cpu_clone(p.grad) for name, p in self.parameters.items()}


class OptimizerProxy:
    def __init__(self, optimizer, capture, *, step=None):
        self.optimizer, self.capture, self.private_step = optimizer, capture, step

    @property
    def param_groups(self):
        return self.optimizer.param_groups

    @property
    def state(self):
        return self.optimizer.state

    def zero_grad(self, *args, **kwargs):
        return self.optimizer.zero_grad(*args, **kwargs)

    def step(self, *args, **kwargs):
        self.capture.capture()
        return (self.private_step or self.optimizer.step)(*args, **kwargs)


def comparison(torch, reference, candidate, tolerance):
    if any(v is None for v in (*reference.values(), *candidate.values())):
        raise ValueError('missing tensors cannot pass the diagnostic')
    table = old.tensor_table(torch, reference, candidate, tolerance)
    for row in table['per_parameter']:
        row['exact'] = row['finite'] and row['reference_sha256'] == row['candidate_sha256']
    table['exact'] = all(row['exact'] for row in table['per_parameter'])
    return table


def cpu_control(torch, muon):
    """Original/private step parity with pre/post hooks and nonzero real weights."""
    initial = torch.tensor([[.1, -.2], [.3, .4], [-.5, .6]], dtype=torch.float32)
    gradient = torch.tensor([[.2, -.1], [.05, .4], [-.3, .15]], dtype=torch.float32)
    parameters = [torch.nn.Parameter(initial.clone()) for _ in range(2)]
    optimizers = [muon.Muon([p], lr=2e-4, scale_mode='rms') for p in parameters]
    identity = GlobalIdentity(muon)
    rng = torch.get_rng_state().clone()
    cuda_before = torch.cuda.is_initialized()
    hooks, handles = [[], []], []
    try:
        for index, optimizer in enumerate(optimizers):
            def before(opt, args, kwargs, index=index):
                hooks[index].append(('pre', len(args), sorted(kwargs)))
            def after(opt, args, kwargs, index=index):
                hooks[index].append(('post', len(args), sorted(kwargs)))
            handles.extend((optimizer.register_step_pre_hook(before), optimizer.register_step_post_hook(after)))
            parameters[index].grad = gradient.clone()
        observer = NSObserver(torch, muon._newton_schulz, ('matrix',))
        optimizers[0].step()
        private_muon_step(torch, optimizers[1], observer)()
        observer.finish()
        if (not torch.equal(parameters[0], parameters[1])
                or not torch.equal(optimizers[0].state[parameters[0]]['buf'], optimizers[1].state[parameters[1]]['buf'])
                or hooks[0] != hooks[1] or len(hooks[0]) != 2
                or any(not torch.equal(p.grad, gradient) for p in parameters)
                or not torch.equal(rng, torch.get_rng_state())
                or torch.cuda.is_initialized() != cuda_before):
            raise ValueError('CPU original/private control or hooks/input/RNG isolation failed')
        validate_ns_interface(muon._newton_schulz)
        identity.check()
        return dict(exact=True, hooks_preserved=True, input_and_rng_unchanged=True,
                    model_calls=0, cuda_calls=0, scope='CPU_SYNTHETIC_PRECONDITION_ONLY')
    finally:
        for handle in handles:
            handle.remove()


def matrix_options(optimizer, names):
    result = {}
    for group in optimizer.param_groups:
        options = {key: group[key] for key in MUON_KEYS}
        if (options['lr'] != 2e-4 or options['momentum'] != .95
                or not options['nesterov'] or options['ns_steps'] != 5
                or options['weight_decay'] != 0 or options['scale_mode'] != 'rms'):
            raise ValueError('original fresh RMS4 optimizer contract changed')
        for p in group['params']:
            result[names[id(p)]] = dict(options)
    if len(result) != 85:
        raise ValueError('exact85 original Muon matrices required')
    return result


def run_arm(torch, engine, muon, cls, cfg, initial, initial_sha, pad, variant, groups, plan, guard, journal):
    model = opts = proxies = capture = observer = parameters = None
    try:
        check(guard, 'before fresh model')
        old.gpu_admission(torch)
        check(guard, 'after fresh GPU admission')
        torch.manual_seed(1337)
        model = cls(copy.deepcopy(cfg))
        model.load_state_dict(initial, strict=True)
        model.set_anneal(1.)
        if engine.state_fingerprint(model) != initial_sha:
            raise ValueError('fresh model differs from the pinned initial state')
        model._padding_pad_id = pad
        model.train()
        model = head.checked_cuda(model, guard)
        opts = head.fresh_optimizers(engine, model)
        parameters = dict(model.named_parameters())
        names = {id(p): name for name, p in parameters.items()}
        ids = [id(p) for opt in opts for group in opt.param_groups for p in group['params']]
        if (len(ids) != len(set(ids)) or set(ids) != {id(p) for p in parameters.values() if p.requires_grad}
                or any(opt.state for opt in opts)):
            raise ValueError('fresh optimizer coverage/state differs')
        options = matrix_options(opts[1], names)
        capture = PostClipCapture(parameters)
        observer = NSObserver(torch, muon._newton_schulz, tuple(options), guard=guard)
        proxies = (OptimizerProxy(opts[0], capture),
                   OptimizerProxy(opts[1], capture, step=private_muon_step(torch, opts[1], observer)))
        torch.manual_seed(1337)
        rng_before = old.rng_identity(torch)
        update, raw = old.one_update(torch, head.HeadCore(variant), model, proxies, groups, plan,
            'fixed1024', 'fp32_math', guard, journal, 0 if variant == 'reference' else 1,
            0, 'actual_gradient_trace', capture=True)
        observer.finish()
        if (update['all_parameter_count'] != 157 or update['non_none_gradient_count'] != 157
                or update['none_gradient_names'] or len(raw) != 157
                or any(g is None for g in raw.values()) or capture.values is None):
            raise ValueError('all157 raw and clipped gradients required')
        updated = {name: cpu_clone(parameters[name]) for name in options}
        # Capture actual buffers too: equal values need not have identical signed-zero bits.
        buffers, fresh_buffer_equal, fresh_buffer_bit_exact = {}, {}, {}
        for group in opts[1].param_groups:
            for p in group['params']:
                name = names[id(p)]
                buffers[name] = cpu_clone(opts[1].state[p]['buf'])
                fresh_buffer_equal[name] = torch.equal(buffers[name], capture.values[name])
                fresh_buffer_bit_exact[name] = torch.equal(buffers[name].contiguous().view(torch.uint8),
                    capture.values[name].contiguous().view(torch.uint8))
        if not all(fresh_buffer_equal.values()):
            raise ValueError('actual fresh Muon buffer differs from captured clipped gradient')
        return dict(raw=raw, clipped=capture.values, ns_input=observer.inputs,
            ns_output=observer.outputs, updated=updated, buffers=buffers, ns_metadata=observer.metadata,
            options=options, update=dict(update, head_policy=variant),
            fresh_buffer_equal_values=fresh_buffer_equal, fresh_buffer_bit_exact=fresh_buffer_bit_exact,
            initial_rng=rng_before,
            final_rng=old.rng_identity(torch),
            weak_model=weakref.ref(model), weak_parameters=[weakref.ref(p) for p in parameters.values()])
    finally:
        if model is not None:
            model.clear_quant()
        model = opts = proxies = capture = observer = parameters = None


def release_cuda(torch):
    gc.collect()
    torch.cuda.synchronize()
    old.clear_runtime_workspace(torch)
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    if torch.cuda.memory_allocated():
        raise ValueError('live CUDA tensor remains; no next admission')


def replay_one(torch, muon, initial, gradient, options, *, device, guard=None, fp32=False):
    """One actual matrix at a time, after global clipping; never reclip it."""
    check(guard, 'before matrix replay')
    if (initial.device.type != 'cpu' or gradient.device.type != 'cpu' or initial.shape != gradient.shape
            or initial.dtype != torch.float32 or gradient.dtype != torch.float32
            or initial.ndim != 2 or not initial.numel()
            or not bool(torch.isfinite(initial).all()) or not bool(torch.isfinite(gradient).all())):
        raise ValueError('matching actual CPU initial weight and clipped gradient required')
    parameter = torch.nn.Parameter(initial.to(device=device).clone())
    optimizer = muon.Muon([parameter], **options)
    parameter.grad = gradient.to(device=device).clone()
    observer = NSObserver(torch, muon._newton_schulz, ('matrix',), guard=guard, fp32=fp32)
    private_muon_step(torch, optimizer, observer)()
    observer.finish()
    answer = dict(weight=cpu_clone(parameter), buffer=cpu_clone(optimizer.state[parameter]['buf']),
                  ns_input=observer.inputs['matrix'], ns_output=observer.outputs['matrix'])
    check(guard, 'after matrix replay')
    return answer


def prefix_trace(torch, muon, left, right, actual_left, actual_right, tolerance, *, device, guard=None):
    report = {}
    for fp32 in (False, True):
        rows = {}
        for label, value in (('reference', left), ('streaming', right)):
            operand = value.to(device=device)
            stages = {'cast': cpu_clone(operand.float() if fp32 else operand.bfloat16().float())}
            for steps in range(6):
                check(guard, 'before NS prefix')
                stages[str(steps)] = cpu_clone(ns_value(torch, muon._newton_schulz,
                    operand, fp32=fp32, steps=steps))
            rows[label] = stages
            del operand
        exact_actual = None
        if not fp32:
            exact_actual = (torch.equal(rows['reference']['5'], actual_left)
                            and torch.equal(rows['streaming']['5'], actual_right))
            if not exact_actual:
                raise ValueError('original NS prefix5 does not exactly reproduce actual optimizer output')
        report['fp32_diagnostic' if fp32 else 'original_bf16'] = dict(
            stages=comparison(torch, rows['reference'], rows['streaming'], tolerance),
            actual_ns_output_exact=exact_actual,
            scope='PREFIX_REEXECUTION_WITH_ORIGINAL_FUNCTION_NOT_INTERCEPTED_ITERATES')
    return report


def replay_all(torch, muon, initial, a, b, tolerance, guard, journal, *, device='cuda'):
    report, prefix = {}, {}
    names = set(a['options'])
    if len(names) != 85 or names != set(b['options']):
        raise ValueError('same complete85 actual matrices required for replay')
    for capture in (a, b):
        if (not names <= set(initial) or not names <= set(capture['clipped'])
                or any(set(capture[key]) != names for key in ('ns_input', 'ns_output', 'updated', 'buffers'))):
            raise ValueError('missing actual NS/updated/buffer captures')
    for index, name in enumerate(a['options']):
        check(guard, 'before next actual matrix')
        if a['options'][name] != b['options'][name]:
            raise ValueError('paired actual optimizer groups differ')
        options = a['options'][name]
        runs = {}
        for label, gradient, fp32 in (
                ('reference_original', a['clipped'][name], False),
                ('identical_original', a['clipped'][name], False),
                ('streaming_original', b['clipped'][name], False),
                ('reference_fp32_ns', a['clipped'][name], True),
                ('streaming_fp32_ns', b['clipped'][name], True)):
            runs[label] = replay_one(torch, muon, initial[name], gradient, options,
                device=device, guard=guard, fp32=fp32)
        identical = comparison(torch, runs['reference_original'], runs['identical_original'], tolerance)
        actual = {}
        for label, capture in (('reference', a), ('streaming', b)):
            actual[label] = comparison(torch,
                dict(weight=capture['updated'][name], buffer=capture['buffers'][name],
                     ns_input=capture['ns_input'][name], ns_output=capture['ns_output'][name]),
                runs[label + '_original'], tolerance)
        if not identical['exact'] or any(not row['exact'] for row in actual.values()):
            raise ValueError('identical-gradient replay or exact actual-step reproduction failed: ' + name)
        report[name] = dict(identical_gradient_control=identical, actual_reproduction=actual,
            original_pair=comparison(torch, runs['reference_original'], runs['streaming_original'], tolerance),
            fp32_ns_pair=comparison(torch, runs['reference_fp32_ns'], runs['streaming_fp32_ns'], tolerance),
            initial_weight_source='ACTUAL_PINNED_PARENT_NOT_ZERO', clipping='ACTUAL_POSTCLIP_NO_RECLIP')
        if name in REPRESENTATIVES:
            prefix[name] = prefix_trace(torch, muon, a['ns_input'][name], b['ns_input'][name],
                a['ns_output'][name], b['ns_output'][name], tolerance, device=device, guard=guard)
        journal.append(dict(event='matrix_replay_complete', matrix=name, index=index,
            identical_exact=identical['exact'], actual_reproduction_exact=True,
            original_pair_close=report[name]['original_pair']['close'],
            fp32_ns_pair_close=report[name]['fp32_ns_pair']['close'], at=old.utc_now().isoformat()))
        del runs
    if set(prefix) != set(REPRESENTATIVES):
        raise ValueError('all three registered actual representative matrices required')
    return dict(matrices=report, prefixes=prefix, matrix_count=len(report),
        same_gradient_controls_exact=True, actual_updates_reproduced_exactly=True,
        tensor_storage='CPU_RAM_ONLY; JSON_STATISTICS_AND_HASHES_ONLY',
        fp32_ns_scope='DIAGNOSTIC_ONLY_BOTH_ARMS; NO_PRODUCT_OPTIMIZER_CHANGE',
        head_unique_cause_proven=False)


def run(args, source_map):
    deadline = validate_execution(args)
    if args.source_sha256 != old.identity(source_map):
        raise ValueError('source-only receipt changed')
    target = output_path()
    admission = old.gpu_admission()
    target.mkdir()
    journal = old.Journal(target / 'events.jsonl')
    began = time.perf_counter()
    guard = old.Guard(deadline, args.max_wall_sec)
    result = dict(schema=SCHEMA, tag=TAG, sources=source_map,
        source_sha256=old.identity(source_map), started_at=old.utc_now().isoformat(),
        deadline=deadline.isoformat(), hard_stop=HARD_STOP.isoformat(),
        max_wall_sec=args.max_wall_sec, checkpoint_writes=0, production_adopted=False,
        quality_claim=False, speed_adoption=False, precision='FP32_MATH_FORWARD_AND_BACKWARD',
        optimizer_precision='ORIGINAL_BF16_NS; SEPARATE_FP32_NS_DIAGNOSTIC',
        dataset_quality='KNOWN_V3_SUPERVISION_DEFECTS_NUMERICAL_CONTROL_ONLY_NOT_ADMITTED',
        timing_scope='INSTRUMENTED_FIRST_UPDATES_WITH_CPU_TRANSFERS; WARMUP_CONFOUNDED_NOT_SPEEDUP',
        tolerances=old.literal_tolerances(), gpu_admission=admission,
        status='STARTED', returncode=9, updates=[], assets_before=None)
    old.write_new(target / 'admission.json', result)
    assets = torch = template = initial = captures = identity = None
    try:
        with old.wall_limit(args.max_wall_sec):
            import tinylm  # path setup before external libraries
            import torch
            from tinylm.train import muon
            result['cpu_control'] = cpu_control(torch, muon)
            identity = GlobalIdentity(muon)
            from scripts import diag_p101a_sft_mtp as engine
            from scripts import diag_p101a_clean_bilingual as clean
            report = engine.corpus_report(old.safe_path(old.CORPUS))
            assets = old.asset_manifest(engine, report)
            result['assets_before'] = assets
            check(guard, 'before parent load')
            torch, template, cfg, tok, initial_sha = engine.load_runtime('parent_ntp')
            if (cfg.cla_group != 2 or not cfg.grad_checkpoint or cfg.mtp_aux or cfg.train_repeat != 1.
                    or any(isinstance(m, torch.nn.Dropout) and m.p for m in template.modules())):
                raise ValueError('original CLA2/checkpoint/R1/MTPoff/dropout0 required')
            result['cpu_memory_plan'] = memory_plan(template, muon)
            initial = old.cpu_copy(template.state_dict())
            records = clean.encoded(old.safe_path(old.CORPUS), report, tok)
            if len(records['train']) != 22528 or len(records['val']) != 512:
                raise ValueError('full frozen known-V3 row identity required')
            groups = next(iter(engine.batches(records['train'], 0)))
            plan = old.update_plan(groups)
            cls = type(template)
            pad = tok.token_to_id('<|pad|>')
            if pad is None:
                pad = tok.token_to_id('<pad>')
            if type(pad) is not int or not 0 <= pad < 32768:
                raise ValueError('original PAD id required')
            result.update(initial_core_sha256=initial_sha, parent_sha256=old.PARENT_SHA,
                tokenizer_sha256=old.TOKENIZER_SHA, plan=plan, seed=1337,
                optimizer=dict(factory='diag_p101a_sft_mtp.optimizers', adam_lr=5e-5,
                    muon_lr=2e-4, clip=1., fresh_each_arm=True, reclip_in_replay=False))
            template = None
            gc.collect()
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            captures = []
            for variant in ('reference', 'streaming'):
                capture = run_arm(torch, engine, muon, cls, cfg, initial, initial_sha,
                    pad, variant, groups, plan, guard, journal)
                if (capture.pop('weak_model')() is not None
                        or any(ref() is not None for ref in capture.pop('weak_parameters'))):
                    raise ValueError('prior model/parameters still referenced')
                release_cuda(torch)
                identity.check()
                result['updates'].append(capture['update'])
                result.setdefault('actual_ns_metadata', {})[variant] = capture['ns_metadata']
                result.setdefault('fresh_buffer_equals_clipped_values', {})[variant] = capture['fresh_buffer_equal_values']
                result.setdefault('fresh_buffer_bit_exact_to_clipped', {})[variant] = capture['fresh_buffer_bit_exact']
                captures.append(capture)
                del capture
            a, b = captures
            if a['initial_rng'] != b['initial_rng'] or a['final_rng'] != b['final_rng']:
                raise ValueError('paired initial/final RNG differs')
            result['rng'] = dict(initial=a['initial_rng'], final=a['final_rng'])
            tolerance = result['tolerances']['gradients_and_update']
            result['actual_pair'] = {
                key: comparison(torch, a[key], b[key], tolerance)
                for key in ('raw', 'clipped', 'ns_input', 'ns_output', 'updated', 'buffers')}
            for key in ('loss', 'preclip_norm'):
                result['actual_pair'][key] = old.scalar_difference(
                    a['update'][key], b['update'][key], result['tolerances']['loss_and_norm'])
            result['cpu_captured_tensor_bytes'] = tensor_bytes(initial) + sum(
                tensor_bytes(capture[key]) for capture in captures
                for key in ('raw', 'clipped', 'ns_input', 'ns_output', 'updated', 'buffers'))
            if result['cpu_captured_tensor_bytes'] + CPU_SCRATCH_RESERVE > CPU_CAPTURE_LIMIT:
                raise MemoryError('actual capture size exceeded reserved CPU budget')
            old.gpu_admission(torch)
            result['replay'] = replay_all(torch, muon, initial, a, b, tolerance, guard, journal)
            release_cuda(torch)
            identity.check()
            result['original_muon_globals_unchanged'] = True
            close = all(row['close'] for row in result['actual_pair'].values())
            result.update(status='VALID_TRACE_NUMERICAL_PASS_NOT_ADOPTED' if close
                else 'VALID_TRACE_NUMERICAL_NEGATIVE_NOT_ADOPTED', returncode=0 if close else 8)
    except Exception as error:
        result.update(status='ERROR_PARTIAL_EVIDENCE', returncode=9,
                      error_type=type(error).__name__, error=str(error))
    finally:
        errors = []
        template = initial = captures = None
        # a/b may otherwise keep CPU arrays alive until this function returns.
        a = b = None
        gc.collect()
        if torch is not None and torch.cuda.is_initialized():
            try:
                release_cuda(torch)
                result['final_allocated_bytes'] = torch.cuda.memory_allocated()
            except Exception as error:
                errors.append('CUDA cleanup: ' + repr(error))
        if identity is not None:
            try:
                identity.check()
                result['original_muon_globals_unchanged'] = True
            except Exception as error:
                errors.append('Muon identity: ' + repr(error))
        try:
            result['sources_unchanged'] = sources() == source_map
            if not result['sources_unchanged']:
                errors.append('source changed during execution')
        except Exception as error:
            errors.append('source audit: ' + repr(error))
        if assets is not None:
            try:
                result['assets_after'] = {p: old.digest(old.safe_path(p)) for p in assets}
                result['assets_unchanged'] = result['assets_after'] == assets
                if not result['assets_unchanged']:
                    errors.append('pinned assets changed during execution')
            except Exception as error:
                errors.append('asset audit: ' + repr(error))
        if errors:
            result.update(status='ERROR_CLEANUP_OR_FINAL_AUDIT', returncode=9, cleanup_errors=errors)
        result.update(finished_at=old.utc_now().isoformat(), wall_seconds=time.perf_counter() - began)
        journal.close()
        old.write_new(target / 'report.json', result)
    print(json.dumps({key: result[key] for key in ('schema', 'status', 'returncode',
        'wall_seconds', 'checkpoint_writes', 'quality_claim', 'speed_adoption')}, ensure_ascii=False))
    return result['returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--source-sha256')
    parser.add_argument('--deadline', default='2026-10-24T08:40:00+09:00')
    parser.add_argument('--max-wall-sec', type=int, default=600)
    args = parser.parse_args(argv)
    if not 60 <= args.max_wall_sec <= 1200:
        parser.error('wall bound must be 60..1200 seconds')
    source_map = sources()
    if args.check_only:
        print(json.dumps(dict(schema=SCHEMA, tag=TAG, source_sha256=old.identity(source_map),
            source_count=len(source_map), model_calls=0, cuda_calls=0, asset_reads=0,
            hard_stop=HARD_STOP.isoformat(), max_file_bytes=MAX_BYTES,
            cpu_capture_limit_bytes=CPU_CAPTURE_LIMIT, cpu_scratch_reserve_bytes=CPU_SCRATCH_RESERVE,
            cpu_system_reserve_bytes=CPU_SYSTEM_RESERVE)))
        return 0
    try:
        return run(args, source_map)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
