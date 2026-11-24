"""Time the full v3 course objective on real batches spread through a v1.1 pilot."""

from contextlib import nullcontext
from hashlib import sha256
import json
import math
from time import perf_counter
from unittest.mock import patch


def mixed_worker(args, arm, cache, publish, tokens_per_step, width, seed, card_limit_mib):
    import numpy as np
    import torch
    from torch.nn import functional as F
    from torch.nn.attention import SDPBackend, sdpa_kernel

    from scripts import p109c_native_curriculum as curriculum
    from scripts.run_p109c_integrated_scratch import prepare
    from scripts.p109_training_elementwise import fused_operations
    from scripts.p109_training_head import target_nll as row_target_nll
    from tinylm.config import build_config
    from tinylm.model import modules, transformer
    from tinylm.train.anneal_schedule import lr_factor, quant_anneal_factor, resolve_quant_start
    from tinylm.train.muon import Muon, split_params
    from tinylm.train.recomputed_ce import target_nll

    torch.set_num_threads(1)
    torch.manual_seed(seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.cuda.set_per_process_memory_fraction(args.fraction, 0)
    torch.cuda.reset_peak_memory_stats()
    started = perf_counter()
    profile, bundle, slots, policy = prepare("original", "capped", "proportional", 0., True)
    supervised = curriculum.supervised
    prep = curriculum.prep
    if (prep.BATCH, prep.WIDTH, prep.ACCUM) != (4, width, tokens_per_step//(4*width)):
        raise ValueError("the pilot must retain the sealed course microbatch shape")
    if arm.batch * arm.seq != prep.BATCH * prep.WIDTH:
        raise ValueError("the raw shape must consume one matching reserved slot")

    class Model(supervised.SupervisedG4):
        def refresh_quant(self):
            # Both pilots share the single VJP after an optimizer update.
            transformer.TiedMLPTransformer.refresh_quant(self)

    cfg = build_config("m100s12_g4", "tied", width, ckpt=True)
    cfg.vocab_size = bundle.meta["vocab"]
    cfg.train_repeat = 2.0
    cfg.sdpa_gqa = True
    cfg.wq_dtype = "bf16" if arm.bf16_weights else "fp32"
    model = Model(cfg).cuda()
    model.set_anneal(1.0)
    r2 = tuple(model.visit_schedule())
    r1 = tuple(range(cfg.n_layers))
    if (len(r1), len(r2)) != (16, 28):
        raise ValueError("the v3 route no longer has the expected layer geometry")
    matrices, _ = split_params(model)
    auxiliary = {id(model.decimal_head.weight), *(id(p) for p in model.value_link.parameters())}
    matrices = [p for p in matrices if id(p) not in auxiliary]
    matrix_ids = {id(p) for p in matrices}
    groups = []
    for group in model.param_groups(0.001):
        params = [param for param in group["params"] if id(param) not in matrix_ids]
        if params:
            groups.append(dict(group, params=params))
    adamw = torch.optim.AdamW(groups, betas=(.9, .95), eps=1e-8)
    muon = Muon(matrices, lr=.004, scale_mode="rms", weight_decay=0.)
    groups = adamw.param_groups + muon.param_groups
    base_lrs = [g["lr"] for g in groups]

    # Keep each source update's paired, relational and decimal examples atomic.
    mixed_updates = max(4, round(args.steps * 2842 / 9546))
    source_pool = np.flatnonzero((bundle.schedule[:, :, 0] >= 0).any(axis=1))
    picks = source_pool[np.linspace(0, len(source_pool)-1, mixed_updates, dtype=int)]
    warmup = math.ceil(.034 * args.steps)
    anneal_start = resolve_quant_start(warmup, args.steps, None)
    addresses = np.linspace(warmup, args.steps-1, mixed_updates, dtype=int)
    course_at = dict(zip(addresses.tolist(), picks.tolist(), strict=True))
    if len(course_at) != mixed_updates or len(set(picks.tolist())) != mixed_updates:
        raise ValueError("the short pilot repeated or collided course addresses")
    raw = np.memmap(cache / "train.bin", mode="r", dtype="<u2")
    val = np.memmap(cache / "val.bin", mode="r", dtype="<u2")
    raw_windows = (len(raw)-1) // (prep.BATCH * width)
    raw_order = np.random.default_rng(seed).permutation(raw_windows)
    val_starts = np.random.default_rng(seed+1).integers(0, len(val)-width, size=32 if args.steps >= 48 else 8)
    native_checkpoint = transformer.checkpoint
    active_route, checkpoint_visits, visit, course_path = r2, 21, 0, False
    raw_cursor = 0

    def some_checkpoints(function, activation, **kwargs):
        nonlocal visit
        within = visit % len(active_route)
        visit += 1
        if ((within+1)*checkpoint_visits//len(active_route)
                == within*checkpoint_visits//len(active_route)):
            return function(activation)
        if not course_path:
            return native_checkpoint(function, activation, **kwargs)
        # The native varlen SDPA binding is scoped to forward. Replay that same
        # binding during backward checkpoint recomputation on the captured mask.
        attn, gqa, rope = F.scaled_dot_product_attention, cfg.sdpa_gqa, modules.apply_rope

        def replay(x):
            with (patch.object(F, "scaled_dot_product_attention", attn), patch.object(cfg, "sdpa_gqa", gqa),
                  patch.object(modules, "apply_rope", rope)):
                return function(x)

        return native_checkpoint(replay, activation, **kwargs)

    def cuda_batch(x, y):
        return tuple(torch.from_numpy(np.array(a, dtype=np.int64, copy=True)).pin_memory().to("cuda", non_blocking=True)
                     for a in (x, y))

    def original_windows(corpus, starts, seq):
        blocks = np.stack([corpus[start:start+width+1] for start in starts])
        x, y = cuda_batch(blocks[:, :-1], blocks[:, 1:])
        return x.reshape(-1, seq), y.reshape(-1, seq)

    @torch.no_grad()
    def validate(anneal):
        model.eval()
        model.set_anneal(1.)
        try:
            x, y = original_windows(val, val_starts, width)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                parts = [target_nll(model, model(a, return_hidden=True), b, rows=1024)[0].mean()
                         for a, b in zip(x.split(1), y.split(1), strict=True)]
            losses = torch.stack(parts)
            return losses.mean().item(), losses.tolist()
        finally:
            model.set_anneal(anneal)
            model.train()

    prepared = perf_counter()-started
    publish(args.record / "mix_binding.json", dict(manifest=profile["signature"],
            actual_course_source_addresses=course_at, packed_policy="intact v3 groups, raw before course in each update",
            paired_validation="fixed v1.1 VAL windows and fully ternary uniform R2", startup_seconds=prepared,
            val_targets=len(val_starts)*width, val_starts_sha256=sha256(val_starts.astype("<i8").tobytes()).hexdigest(),
            planned_quant_start=anneal_start, schedule="wsd", warmup=warmup, quant_end=.6, decay_fraction=.2))
    run = []
    kernel_context = fused_operations() if arm.fused else nullcontext()
    with (sdpa_kernel(SDPBackend.FLASH_ATTENTION), kernel_context,
          patch.object(transformer, "checkpoint", some_checkpoints),
          (args.record / "steps.jsonl").open("x", encoding="utf-8", buffering=1) as stream,
          (args.record / "validation.jsonl").open("x", encoding="utf-8", buffering=1) as val_stream):
        first_val, first_windows = validate(1.)
        print(json.dumps(dict(step=0, validation_nll_r2=first_val, window_nll=first_windows)), file=val_stream)
        check_steps = {args.steps//4, round(args.steps*.60), round(args.steps*.70), args.steps}
        validations = []
        for step in range(args.steps):
            start = perf_counter()
            anneal = quant_anneal_factor(step, args.steps, "wsd", "linear", anneal_start, .6)
            model.set_anneal(anneal)
            factor = lr_factor(step, warmup, args.steps, "wsd", .2)
            for group, base_lr in zip(groups, base_lrs, strict=True):
                group["lr"] = factor*base_lr
            source = course_at.get(step)
            course = []
            if source is not None:
                for lane, index in bundle.schedule[source]:
                    if lane >= 0:
                        x, y, labels = supervised.course_microbatch(bundle, slots, source, int(lane), int(index))
                        course.append((*cuda_batch(x, y), labels))
            raw_slots = prep.ACCUM - len(course)
            raw_targets = raw_slots*prep.BATCH*width
            count = dict(answers=(0, 0, 0), context=0, locations=0, pairs=0, relations=0, decimals=0, course_inputs=0)
            if source is not None:
                count = curriculum.read_targets(bundle, slots, source)
            count["raw"] = raw_targets
            stats = policy.weights(0 if source is None else source, count)
            stats.update(context_targets=count["context"], location_targets=count["locations"],
                         relation_questions=count["relations"], decimal_targets=count["decimals"], decimal_correct=0)
            indices = raw_order[raw_cursor:raw_cursor+raw_slots]
            raw_cursor += raw_slots
            starts = (indices[:, None]*prep.BATCH + np.arange(prep.BATCH)) * width
            x, y = original_windows(raw, starts.ravel(), arm.seq)
            adamw.zero_grad(set_to_none=True)
            muon.zero_grad(set_to_none=True)
            torch.cuda.synchronize()
            staged = perf_counter()
            raw_repeat = 2 if arm.r2_from and step >= round(args.steps*arm.r2_from) else arm.repeat
            active_route = r1 if raw_repeat == 1 else r2
            checkpoint_visits = arm.checkpoint_visits if raw_repeat == arm.repeat else arm.r2_ckpt
            model.training_route = active_route
            model.training_forwards = 0
            if arm.ste_update:
                model.begin_quant_update_cache()
            visit, course_path = 0, False
            primary = torch.zeros((), device="cuda")
            try:
                for a, b in zip(x.split(arm.batch), y.split(arm.batch), strict=True):
                    with torch.autocast("cuda", dtype=torch.bfloat16):
                        hidden = model(a, return_hidden=True)
                        values = (row_target_nll(model, hidden, b) if arm.row_head
                                  else target_nll(model, hidden, b, rows=1024))[0]
                        loss = values.sum()
                    (stats["raw_context_weight"] * loss).backward()
                    primary.add_(loss.detach())
                if visit != len(active_route)*raw_slots:
                    raise ValueError("raw visit accounting diverged")
                torch.cuda.synchronize()
                raw_end = perf_counter()
                model.training_route = active_route = r2
                visit, checkpoint_visits, course_path = 0, arm.course_ckpt, True
                with patch.object(supervised, "VALUE_WEIGHT", stats["value_weight"]):
                    for a, b, labels in course:
                        with torch.autocast("cuda", dtype=torch.bfloat16):
                            _, loss = supervised.course_objective(model, bundle, a, b, 1024, labels, stats)
                        loss.backward()
                if (visit != 28*len(course) or stats.get("bilingual_pairs", 0) != count["pairs"]
                        or model.training_forwards != prep.ACCUM):
                    raise ValueError("course visit, R2, or supervision accounting diverged")
                torch.cuda.synchronize()
                course_end = perf_counter()
                if arm.ste_update:
                    model.finish_quant_update_cache()
            finally:
                model.abort_quant_update_cache()
                model.training_route = None
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            adamw.step()
            muon.step()
            torch.cuda.synchronize()
            free, total = torch.cuda.mem_get_info()
            cuda_global_used = (total-free)/2**20
            if not (0 <= cuda_global_used < card_limit_mib-64):
                raise RuntimeError(f"CUDA reported {cuda_global_used:.2f} MiB used at the update boundary")
            row = dict(step=step, sec=perf_counter()-start, input_sec=staged-start, raw_sec=raw_end-staged,
                       course_sec=course_end-raw_end, optimizer_sec=perf_counter()-course_end,
                       train_nll=primary.item()/raw_targets, grad_norm=norm.item(), raw_repeat=raw_repeat,
                       anneal=anneal, lr_factor=factor,
                       raw_targets=raw_targets, course_batches=len(course), course_source=source,
                       course_tokens=count["course_inputs"], course_answers=list(count["answers"]),
                       relations=count["relations"], decimals=count["decimals"], bilingual_pairs=count["pairs"],
                       targets=raw_targets+count["course_inputs"], cuda_global_used_mib=cuda_global_used,
                       allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                       reserved_mib=torch.cuda.max_memory_reserved()/2**20)
            if not math.isfinite(row["grad_norm"]) or not math.isfinite(row["train_nll"]):
                raise ValueError("nonfinite mixed update")
            print(json.dumps(row), file=stream)
            run.append(row)
            if step+1 in check_steps:
                before_validation = perf_counter()
                value, window_values = validate(anneal)
                validation = dict(step=step+1, validation_nll_r2=value, window_nll=window_values,
                                  seconds=perf_counter()-before_validation)
                print(json.dumps(validation), file=val_stream)
                validations.append(validation)
    bundle.unchanged()
    steady = run[1:]
    phases = []
    for repeat in sorted({row["raw_repeat"] for row in steady}):
        rows = [row for row in steady if row["raw_repeat"] == repeat]
        phases.append(dict(repeat=repeat, raw_tokens=sum(row["raw_targets"] for row in rows),
                           raw_seconds=sum(row["raw_sec"] for row in rows), updates=len(rows)))
    publish(args.record / "worker.json", dict(torch=torch.__version__, updates=len(run), phases=phases,
            initial_val_r2=first_val, initial_val_windows=first_windows,
            final_val_r2=validations[-1]["validation_nll_r2"], val_curve=validations,
            seen_raw=sum(row["raw_targets"] for row in run),
            seen_course=sum(row["course_tokens"] for row in run), course_batches=sum(row["course_batches"] for row in run),
            course_sec=sum(row["course_sec"] for row in steady), update_seconds=sum(row["sec"] for row in run),
            tokens_per_s=sum(row["targets"] for row in steady)/sum(row["sec"] for row in steady),
            raw_window_order_sha256=sha256(raw_order[:raw_cursor].astype("<i8").tobytes()).hexdigest()))
