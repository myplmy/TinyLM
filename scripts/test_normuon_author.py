"""Independent synthetic CPU author-formula and optional Gloo2 contracts."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from datetime import timedelta
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import torch
from tinylm.train.normuon_author import (SingleDeviceNorMuonAuthor, NorMuonAuthor,
    SingleDeviceNorMuonWithAuxAdamAuthor, NorMuonWithAuxAdamAuthor)


def equal(a, b):
    return a.shape == b.shape and a.dtype == b.dtype and torch.equal(
        a.detach().contiguous().reshape(-1).view(torch.uint8),
        b.detach().contiguous().reshape(-1).view(torch.uint8))


def pattern(shape, step, index=0):
    count = math_product(shape)
    return torch.sin(torch.arange(count, dtype=torch.float32) * .73 + step * .91 + index).reshape(shape)


def math_product(shape):
    value = 1
    for size in shape:
        value *= size
    return value


def reference_matrix(weight, gradient, previous=None, *, beta=.8, beta2=.7, lr=.01, wd=.1):
    """Independent explicit equations; does not import production direction/NS."""
    present = gradient is not None
    gradient = gradient.clone() if present else torch.zeros_like(weight)
    old_m, old_v = previous if previous is not None else (torch.zeros_like(weight), torch.zeros_like(weight[..., :1]))
    moment = torch.lerp(old_m, gradient, 1 - beta)
    mixed = torch.lerp(gradient, moment, beta)
    shaped = mixed.reshape(weight.shape[0], -1) if weight.ndim == 4 else mixed
    x = shaped.to(torch.bfloat16)
    transposed = x.shape[-2] > x.shape[-1]
    if transposed:
        x = x.transpose(-2, -1)
    x = x / (torch.linalg.vector_norm(x, dim=(-2, -1), keepdim=True) + 1e-7)
    for _ in range(5):
        gram = torch.matmul(x, x.transpose(-2, -1))
        polynomial = -4.7750 * gram + torch.matmul(2.0315 * gram, gram)
        x = 3.4445 * x + torch.matmul(polynomial, x)
    if transposed:
        x = x.transpose(-2, -1)
    raw = x.to(torch.float32).reshape(weight.shape)
    old_norm = torch.linalg.vector_norm(raw, dim=(-2, -1), keepdim=True)
    variance = torch.lerp(old_v, (raw * raw).mean(-1, keepdim=True), 1 - beta2)
    update = raw * (1 / (variance.sqrt() + 1e-10))
    update = update * (old_norm / (torch.linalg.vector_norm(update, dim=(-2, -1), keepdim=True) + 1e-10))
    update = update * max(1, weight.shape[-2] / weight.shape[-1]) ** .5
    result = weight.clone()
    if present and wd:
        result.mul_(1 - lr * wd)
    result.add_(update, alpha=-lr)
    return result, (moment, variance), mixed


def reference_adam(weight, gradient, previous=None, *, betas=(.85, .92), eps=1e-9, lr=.003, wd=.04):
    present = gradient is not None
    gradient = gradient.clone() if present else torch.zeros_like(weight)
    first, second, count = previous if previous is not None else (torch.zeros_like(weight), torch.zeros_like(weight), 0)
    count += 1
    first = torch.lerp(first, gradient, 1 - betas[0])
    second = torch.lerp(second, gradient.square(), 1 - betas[1])
    update = (first / (1 - betas[0] ** count)) / ((second / (1 - betas[1] ** count)).sqrt() + eps)
    result = weight.clone()
    if present and wd:
        result.mul_(1 - lr * wd)
    result.add_(update, alpha=-lr)
    return result, (first, second, count), gradient


def groups(matrices, auxiliary):
    result = [dict(params=matrices, use_muon=True, lr=.01, momentum=.8, beta2=.7, weight_decay=.1)]
    if auxiliary:
        result.append(dict(params=auxiliary, use_muon=False, lr=.003, betas=(.85, .92), eps=1e-9, weight_decay=.04))
    return result


def frozen_state(value):
    buffer = io.BytesIO()
    torch.save(value, buffer)
    buffer.seek(0)
    return torch.load(buffer, map_location="cpu", weights_only=True)


def tensors_same(a, b):
    if isinstance(a, torch.Tensor):
        return isinstance(b, torch.Tensor) and equal(a, b)
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(tensors_same(a[k], b[k]) for k in a)
    if isinstance(a, (tuple, list)):
        return type(a) is type(b) and len(a) == len(b) and all(tensors_same(x, y) for x, y in zip(a, b))
    return a == b


class AuthorContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():
            raise ValueError("CPU parameter contracts must not initialize CUDA")

    @classmethod
    def tearDownClass(cls):
        if torch.cuda.is_initialized():
            raise ValueError("CPU author tests initialized CUDA")

    def test_byte_comparator_supports_scalar_Adam_steps_and_distinguishes_signed_zero(self):
        for dtype in (torch.float32, torch.bfloat16, torch.float64):
            self.assertTrue(equal(torch.tensor(1., dtype=dtype), torch.tensor(1., dtype=dtype)))
            self.assertFalse(equal(torch.tensor(0., dtype=dtype), torch.tensor(-0., dtype=dtype)))
        self.assertFalse(equal(torch.tensor(1.), torch.tensor([1.])))
        self.assertTrue(tensors_same({'step': torch.tensor(2.)}, {'step': torch.tensor(2.)}))

    def test_independent_author_weight_momentum_variance_and_gradient_bytes(self):
        for shape in ((3, 7), (7, 3), (4, 4)):
            p = torch.nn.Parameter(pattern(shape, 0) / 10)
            reference, previous = p.detach().clone(), None
            opt = SingleDeviceNorMuonAuthor([p], lr=.01, momentum=.8, beta2=.7, weight_decay=.1)
            for step in range(5):
                grad = pattern(shape, step)
                reference, previous, mixed = reference_matrix(reference, grad, previous)
                p.grad = grad.clone()
                opt.step()
                self.assertTrue(equal(p, reference))
                self.assertTrue(equal(p.grad, mixed))
                self.assertTrue(equal(opt.state[p]["momentum_buffer"], previous[0]))
                self.assertTrue(equal(opt.state[p]["second_momentum_buffer"], previous[1]))

    def test_first_EMA_momentum_has_normalized_coefficient(self):
        p = torch.nn.Parameter(torch.zeros(2, 3))
        p.grad = torch.full_like(p, 2.)
        opt = SingleDeviceNorMuonAuthor([p], momentum=.75)
        opt.step()
        self.assertTrue(equal(opt.state[p]["momentum_buffer"], torch.full_like(p, .5)))
        self.assertTrue(equal(p.grad, torch.full_like(p, .875)))

    def test_first_None_creates_zero_gradient_and_state_without_weight_decay(self):
        p = torch.nn.Parameter(torch.ones(2, 3))
        opt = SingleDeviceNorMuonAuthor([p], lr=.1, weight_decay=.5)
        opt.step()
        self.assertTrue(equal(p, torch.ones_like(p)))
        self.assertTrue(equal(p.grad, torch.zeros_like(p)))
        self.assertEqual(set(opt.state[p]), {"momentum_buffer", "second_momentum_buffer"})

    def test_None_after_history_applies_momentum_tail_but_skips_current_WD(self):
        p = torch.nn.Parameter(torch.ones(3, 5))
        opt = SingleDeviceNorMuonAuthor([p], lr=.01, momentum=.8, beta2=.7, weight_decay=.1)
        p.grad = pattern(p.shape, 0)
        opt.step()
        before = p.detach().clone()
        old = opt.state[p]
        expected, state, mixed = reference_matrix(before, None,
            (old["momentum_buffer"].clone(), old["second_momentum_buffer"].clone()))
        p.grad = None
        opt.step()
        self.assertTrue(equal(p, expected))
        self.assertFalse(equal(p, before))
        self.assertTrue(equal(p.grad, mixed))
        self.assertTrue(equal(opt.state[p]["momentum_buffer"], state[0]))

    def test_auxiliary_Adam_preserves_None_history_step_and_source_defaults(self):
        p = torch.nn.Parameter(torch.ones(3))
        opt = SingleDeviceNorMuonWithAuxAdamAuthor([dict(params=[p], use_muon=False)])
        settings = opt.param_groups[0]
        self.assertEqual((settings["lr"], settings["betas"], settings["eps"], settings["weight_decay"]),
            (.0003, (.9, .95), 1e-10, 0.))
        opt = SingleDeviceNorMuonWithAuxAdamAuthor(groups([], [p])[1:])
        previous, expected = None, p.detach().clone()
        for step in range(3):
            grad = pattern(p.shape, step) if step == 0 else None
            expected, previous, actual_grad = reference_adam(expected, grad, previous)
            p.grad = grad.clone() if grad is not None else None
            opt.step()
            self.assertTrue(equal(p, expected))
            self.assertTrue(equal(p.grad, actual_grad))
            self.assertEqual(opt.state[p]["step"], step + 1)

    def test_source_4D_axes_preserve_per_last_axis_variance_and_partial_norms(self):
        p = torch.nn.Parameter(pattern((2, 2, 3, 3), 0) / 100)
        expected, previous = p.detach().clone(), None
        opt = SingleDeviceNorMuonAuthor([p], lr=.01, momentum=.8, beta2=.7, weight_decay=.1)
        for step in range(3):
            grad = pattern(p.shape, step)
            expected, previous, _ = reference_matrix(expected, grad, previous)
            p.grad = grad.clone()
            opt.step()
            self.assertTrue(equal(p, expected))
            self.assertTrue(equal(opt.state[p]["second_momentum_buffer"], previous[1]))
        self.assertEqual(opt.state[p]["second_momentum_buffer"].shape, (2, 2, 3, 1))

    def test_actual_state_storage_counts_matrix_4D_and_auxiliary_separately(self):
        matrix = torch.nn.Parameter(torch.ones(3, 5))
        convolution = torch.nn.Parameter(torch.ones(2, 2, 3, 3))
        auxiliary = torch.nn.Parameter(torch.ones(4))
        opt = SingleDeviceNorMuonWithAuxAdamAuthor(groups([matrix, convolution], [auxiliary]))
        for p in (matrix, convolution, auxiliary):
            p.grad = torch.ones_like(p)
        opt.step()
        sizes = [sum(t.untyped_storage().nbytes() for t in opt.state[p].values() if isinstance(t, torch.Tensor))
            for p in (matrix, convolution, auxiliary)]
        self.assertEqual(sizes, [4 * (15 + 3), 4 * (36 + 12), 8 * 4])
        self.assertEqual(sum(sizes), 296)

    def test_serialized_matrix_and_aux_resume_all_following_weights_and_states(self):
        for auxiliary in (False, True):
            ps = [torch.nn.Parameter(pattern(s, 0) / 100) for s in ((3, 5), (4,))] if auxiliary else [torch.nn.Parameter(pattern((3, 5), 0))]
            opt = (SingleDeviceNorMuonWithAuxAdamAuthor(groups(ps[:1], ps[1:])) if auxiliary
                else SingleDeviceNorMuonAuthor(ps, lr=.01, momentum=.8, beta2=.7, weight_decay=.1))
            for step in range(2):
                for i, p in enumerate(ps): p.grad = pattern(p.shape, step, i)
                opt.step()
            saved = frozen_state(opt.state_dict())
            untouched = copy.deepcopy(saved)
            qs = [torch.nn.Parameter(p.detach().clone()) for p in ps]
            other = (SingleDeviceNorMuonWithAuxAdamAuthor(groups(qs[:1], qs[1:])) if auxiliary
                else SingleDeviceNorMuonAuthor(qs))
            other.load_state_dict(saved)
            for step in range(2, 5):
                for i, (p, q) in enumerate(zip(ps, qs)):
                    grad = pattern(p.shape, step, i) if step != 3 else None
                    p.grad = grad.clone() if grad is not None else None
                    q.grad = grad.clone() if grad is not None else None
                opt.step(); other.step()
                self.assertTrue(all(equal(p, q) for p, q in zip(ps, qs)))
                self.assertTrue(tensors_same(opt.state_dict(), other.state_dict()))
            self.assertTrue(tensors_same(saved, untouched))

    def test_nonfinite_preflight_precedes_all_weight_state_and_gradient_writes(self):
        ps = [torch.nn.Parameter(torch.ones(3, 5)), torch.nn.Parameter(torch.ones(4))]
        opt = SingleDeviceNorMuonWithAuxAdamAuthor(groups(ps[:1], ps[1:]))
        for p in ps: p.grad = torch.ones_like(p)
        opt.step()
        before, weights = copy.deepcopy(opt.state_dict()), [p.detach().clone() for p in ps]
        ps[0].grad = torch.ones_like(ps[0]); grad = ps[0].grad.clone()
        ps[1].grad[0] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite differs"): opt.step()
        self.assertTrue(tensors_same(before, opt.state_dict()))
        self.assertTrue(all(equal(p, w) for p, w in zip(ps, weights)))
        self.assertTrue(equal(ps[0].grad, grad))

    def test_wrong_method_rank_orphan_missing_state_and_precision_reject_before_load(self):
        p = torch.nn.Parameter(torch.ones(2, 3)); p.grad = torch.ones_like(p)
        opt = SingleDeviceNorMuonAuthor([p]); opt.step()
        original = copy.deepcopy(opt.state_dict())
        bad = []
        for key, value in (("variant", "AUX_SINGLE"), ("rank", 1), ("completed_steps", True)):
            row = copy.deepcopy(original); row["author_contract"][key] = value; bad.append(row)
        row = copy.deepcopy(original); row["state"][99] = copy.deepcopy(row["state"][0]); bad.append(row)
        row = copy.deepcopy(original); row["state"].clear(); bad.append(row)
        row = copy.deepcopy(original); row["state"][0]["second_momentum_buffer"] = torch.ones(2, 1, dtype=torch.bfloat16); bad.append(row)
        for value in bad:
            with self.assertRaises(ValueError): opt.load_state_dict(value)
            self.assertTrue(tensors_same(original, opt.state_dict()))

    def test_invalid_construction_and_dynamic_topology_are_rejected(self):
        p = torch.nn.Parameter(torch.ones(2, 3))
        for values in (dict(lr=float("inf")), dict(momentum=True), dict(beta2=1), dict(weight_decay=-1)):
            with self.assertRaises(ValueError): SingleDeviceNorMuonAuthor([p], **values)
        with self.assertRaises(ValueError): SingleDeviceNorMuonAuthor([p, p])
        with self.assertRaises(ValueError): SingleDeviceNorMuonAuthor([torch.nn.Parameter(torch.ones(2, 3, dtype=torch.bfloat16))])
        with self.assertRaises(ValueError): SingleDeviceNorMuonWithAuxAdamAuthor([dict(params=[p])])
        with self.assertRaises(ValueError): NorMuonAuthor([p], rank=0, world_size=2)
        opt = SingleDeviceNorMuonAuthor([p])
        with self.assertRaises(ValueError): opt.add_param_group(dict(params=[p]))
        opt.param_groups[0]["params"].append(torch.nn.Parameter(torch.ones(3, 2)))
        with self.assertRaisesRegex(ValueError, "topology changed"): opt.step()

    def test_zero_matrix_and_aux_gradients_are_finite_with_exact_zero_moments(self):
        ps = [torch.nn.Parameter(torch.ones(2, 3)), torch.nn.Parameter(torch.ones(4))]
        config = groups(ps[:1], ps[1:])
        for group in config: group["weight_decay"] = 0.
        opt = SingleDeviceNorMuonWithAuxAdamAuthor(config)
        for p in ps: p.grad = torch.zeros_like(p)
        opt.step()
        self.assertTrue(all(equal(p, torch.ones_like(p)) for p in ps))
        for value in opt.state.values():
            self.assertTrue(all(bool((t == 0).all()) for t in value.values() if isinstance(t, torch.Tensor)))

    def test_existing_TinyLM_variant_keeps_gradient_and_None_skip_distinct(self):
        from tinylm.train.normuon import NorMuon
        p = torch.nn.Parameter(torch.ones(3, 5)); q = torch.nn.Parameter(p.detach().clone())
        author = SingleDeviceNorMuonAuthor([p], lr=.01, momentum=.8, beta2=.7)
        adapted = NorMuon([q], lr=.01, momentum=.8, beta2=.7)
        grad = pattern(p.shape, 0); p.grad = grad.clone(); q.grad = grad.clone()
        author.step(); adapted.step()
        self.assertTrue(equal(q.grad, grad))
        self.assertFalse(equal(p.grad, grad))
        before = q.detach().clone(); state = copy.deepcopy(adapted.state_dict())
        p.grad = None; q.grad = None
        author.step(); adapted.step()
        self.assertTrue(equal(q, before)); self.assertIsNone(q.grad)
        self.assertTrue(tensors_same(state, adapted.state_dict()))
        self.assertIsNotNone(p.grad)

    def test_closure_result_and_no_global_parameter_group_mutation(self):
        p = torch.nn.Parameter(torch.ones(2, 3))
        original = groups([p], [])
        before = {k:v for k,v in original[0].items() if k != "params"}
        opt = SingleDeviceNorMuonWithAuxAdamAuthor(original)
        p.grad = torch.ones_like(p)
        returned = opt.step(lambda: p.square().sum())
        self.assertEqual(float(returned.detach()), 6.)
        self.assertEqual({k:v for k,v in original[0].items() if k != "params"}, before)


def gloo_worker(rank, directory):
    import torch.distributed as dist
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    out = Path(directory)
    report = dict(rank=rank, status="ERROR", CUDA_initialized=False, cases=[])
    try:
        dist.init_process_group("gloo", init_method="file://" + str(out / "rendezvous"),
            rank=rank, world_size=2, timeout=timedelta(seconds=20))
        for auxiliary in (False, True):
            shapes = [(3, 7), (7, 3), (4, 4), (2, 2, 3, 3)] + ([(5,), (8, 3)] if auxiliary else [])
            ps = [torch.nn.Parameter(pattern(shape, 0, i) / 100) for i, shape in enumerate(shapes)]
            reference = [p.detach().clone() for p in ps]
            moments = [None] * len(ps)
            def make(parameters):
                return (NorMuonWithAuxAdamAuthor(groups(parameters[:4], parameters[4:]), rank=rank, world_size=2)
                    if auxiliary else NorMuonAuthor(parameters, lr=.01, momentum=.8, beta2=.7,
                        weight_decay=.1, rank=rank, world_size=2))
            opt = make(ps)
            checks, restored = 0, False
            for step in range(4):
                for i, p in enumerate(ps):
                    grad = None if step == 2 and i in (0, 4) else pattern(p.shape, step, i)
                    p.grad = grad.clone() if grad is not None else None
                    fn = reference_matrix if i < 4 else reference_adam
                    reference[i], moments[i], _ = fn(reference[i], grad, moments[i])
                opt.step()
                for p, expected in zip(ps, reference):
                    if not equal(p, expected): raise ValueError("Gloo2 independent reference weight bytes differ")
                    checks += 1
                if step == 1:
                    saved = frozen_state(opt.state_dict())
                    ps = [torch.nn.Parameter(p.detach().clone()) for p in ps]
                    opt = make(ps); opt.load_state_dict(saved); restored = True
            before = copy.deepcopy(opt.state_dict()); weights = [p.detach().clone() for p in ps]
            for p in ps: p.grad = torch.ones_like(p)
            if rank == 0: ps[-1].grad.flatten()[0] = float("nan")
            try:
                opt.step()
            except ValueError as exc:
                if "finite differs" not in str(exc): raise
            else:
                raise ValueError("one-rank nonfinite gradient was accepted")
            if not tensors_same(before, opt.state_dict()) or not all(equal(p, w) for p,w in zip(ps, weights)):
                raise ValueError("collective preflight fault changed state or weights")
            digest = hashlib.sha256(b"".join(p.detach().numpy().tobytes() for p in ps)).hexdigest().upper()
            report["cases"].append(dict(auxiliary=auxiliary, independent_parameter_steps=checks,
                serialized_resume=restored, one_rank_nonfinite_rejected_before_writes=True,
                owned_states=len(opt.state), completed_steps=opt.state_dict()["author_contract"]["completed_steps"],
                state_tensor_bytes=sum(t.untyped_storage().nbytes() for value in opt.state.values()
                    for t in value.values() if isinstance(t, torch.Tensor)), weight_sha256=digest,
                transport="SEQUENTIAL_OWNER_BROADCAST;NOT_UPSTREAM_ALL_GATHER_OR_FSDP2"))
        if torch.cuda.is_initialized(): raise ValueError("CPU Gloo initialized CUDA")
        report["status"] = "PASS"
    except BaseException as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        with (out / ("rank" + str(rank) + ".json")).open("x", encoding="utf-8") as stream:
            json.dump(report, stream, sort_keys=True)
        if dist.is_initialized(): dist.destroy_process_group()


def run_gloo(directory):
    import torch.multiprocessing as mp
    out = Path(directory).absolute()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    processes = mp.spawn(gloo_worker, args=(str(out),), nprocs=2, join=False)
    try:
        while not processes.join(timeout=1):
            if time.monotonic() - started > 45: raise TimeoutError("owned CPU Gloo2 45s cap")
    finally:
        for process in processes.processes:
            if process.is_alive(): process.terminate()
        for process in processes.processes: process.join(timeout=5)
    reports = [json.loads((out / ("rank" + str(rank) + ".json")).read_text()) for rank in range(2)]
    if any(row["status"] != "PASS" for row in reports): raise ValueError("both CPU ranks must pass")
    for a, b in zip(reports[0]["cases"], reports[1]["cases"]):
        if a["weight_sha256"] != b["weight_sha256"]: raise ValueError("CPU rank final weight hashes differ")
    report = dict(schema="NORMUON_AUTHOR_CPU_GLOO2_V1", returncode=0, ranks=reports,
        wall_seconds=time.monotonic() - started, model_loads=0, natural_language_training_tokens=0,
        CUDA_initialized=False, quality_claim=False, original_library_executed=False)
    with (out / "report.json").open("x", encoding="utf-8") as stream: json.dump(report, stream, sort_keys=True)
    print(json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gloo":
        if len(sys.argv) != 3: raise SystemExit("--gloo requires one new output directory")
        run_gloo(sys.argv[2])
    else:
        unittest.main()
