"""A06: storage 중복을 제거한 회계와 실행 구간 RSS 표본 최고점."""
from __future__ import annotations
import hashlib
import threading
import time


def tensor_inventory(*roots):
    import torch
    seen_objects, storages = set(), {}
    def walk(value, name):
        if isinstance(value, torch.Tensor):
            if value.numel() == 0:
                return
            storage = value.untyped_storage()
            key = (str(value.device), storage.data_ptr(), storage.nbytes())
            if key not in storages:
                storages[key] = {"bytes": storage.nbytes(), "device": str(value.device),
                                 "aliases": [], "tensor": value}
            storages[key]["aliases"].append({"path": name, "shape": list(value.shape),
                                             "dtype": str(value.dtype)})
            return
        if id(value) in seen_objects:
            return
        seen_objects.add(id(value))
        if isinstance(value, torch.nn.Module):
            for key, child in vars(value).items():
                walk(child, name + "." + key)
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, name + "." + str(key))
        elif isinstance(value, (list, tuple)):
            for i, child in enumerate(value):
                walk(child, name + "." + str(i))
    for i, root in enumerate(roots):
        walk(root, f"root{i}")
    return storages


def inventory_summary(*roots):
    rows = tensor_inventory(*roots).values()
    return {"bytes": sum(r["bytes"] for r in rows),
            "storages": [{k: v for k, v in row.items() if k != "tensor"} for row in rows]}


def tensor_digest(model):
    """계측 시작 전 모델에 실제 존재하는 tensor 값의 해시. storage 주소는 넣지 않는다."""
    import torch
    from .audit_io import digest_json
    rows = []
    for record in tensor_inventory(model).values():
        t = record["tensor"].detach().contiguous().reshape(-1)
        digest = hashlib.sha256()
        for start in range(0, t.numel(), 262144):
            digest.update(t[start:start+262144].cpu().view(torch.uint8).numpy().tobytes())
        aliases = sorted(record["aliases"], key=lambda x: x["path"])
        rows.append({"aliases": aliases, "value_sha256": digest.hexdigest(),
                     "storage_bytes": record["bytes"]})
    return digest_json(sorted(rows, key=lambda r: r["aliases"][0]["path"])), rows


class RssSampler:
    def __init__(self, interval=0.01):
        import psutil
        if interval <= 0:
            raise ValueError("RSS interval은 양수")
        self.process, self.interval = psutil.Process(), interval
        self.stop_event = threading.Event()
        self.samples, self.peak = 0, 0

    def _sample(self):
        rss = self.process.memory_info().rss
        self.samples += 1
        self.peak = max(self.peak, rss)

    def _loop(self):
        while not self.stop_event.wait(self.interval):
            self._sample()

    def __enter__(self):
        self.start = self.process.memory_info().rss
        self._sample()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop_event.set()
        self.thread.join()
        self._sample()
        info = self.process.memory_info()
        self.result = {"rss_start": self.start, "rss_end": info.rss,
                       "rss_sampled_peak": self.peak, "samples": self.samples,
                       "sample_interval_seconds": self.interval,
                       "process_lifetime_peak_wset": getattr(info, "peak_wset", None),
                       "note": "RSS는 engine/allocator/계측 포함. 표본 사이 peak와 model workspace 분리는 미해결."}


class ForwardAudit:
    def __init__(self, model, *, phase, record_tokens=False):
        self.model, self.phase, self.record_tokens = model, phase, record_tokens
        self.rows, self.tokens = [], []
        self.start = None

    def __enter__(self):
        import torch
        self.device = next(self.model.parameters()).device
        def pre(module, args, kwargs):
            if self.device.type == "cuda":
                torch.cuda.synchronize(self.device)
            self.start = time.perf_counter()
        def post(module, args, kwargs, output):
            if self.device.type == "cuda":
                torch.cuda.synchronize(self.device)
            elapsed = time.perf_counter() - self.start
            logits = output[0] if isinstance(output, tuple) else output
            present = output[1] if isinstance(output, tuple) and len(output) > 1 else None
            before = kwargs.get("past_kv")
            resident = inventory_summary(module)["bytes"]
            live = inventory_summary(module, args, before, output)["bytes"]
            kv = inventory_summary(present)["bytes"] if present is not None else 0
            self.rows.append({"phase": self.phase, "input_tokens": args[0].shape[-1],
                              "forward_seconds": elapsed, "resident_model_bytes": resident,
                              "present_kv_bytes": kv, "boundary_live_tensor_bytes": live})
            if self.record_tokens:
                self.tokens.append(int(logits[0, -1].argmax()))
        self.pre_handle = self.model.register_forward_pre_hook(pre, with_kwargs=True)
        self.post_handle = self.model.register_forward_hook(post, with_kwargs=True)
        return self

    def __exit__(self, *exc):
        self.pre_handle.remove()
        self.post_handle.remove()


def cached_continuation_nll(model, tok, prompt, answer, *, device, seq_max, last_head=False):
    import torch
    import torch.nn.functional as F
    from .model_adapter import prefix_ids
    prefix = tok.encode(prompt, add_special_tokens=False).ids if prompt else prefix_ids(tok)[0]
    target = tok.encode(answer, add_special_tokens=False).ids
    if not prefix or not target or len(prefix) + len(target) - 1 > seq_max:
        return None, "empty_or_context_overflow"
    past, total = None, 0.0
    dev = torch.device(device).type
    with torch.inference_mode():
        for i, token in enumerate(target):
            x = prefix if i == 0 else [target[i-1]]
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=dev == "cuda"):
                options = {"logits_last_only": True} if last_head else {}
                logits, past = model(torch.tensor([x], device=device), past_kv=past,
                                     use_cache=True, **options)
            total += float(F.cross_entropy(logits[:, -1].float(),
                                           torch.tensor([token], device=device), reduction="sum"))
    import math
    if not math.isfinite(total):
        return None, "nonfinite_nll"
    return {"nll_sum": total, "nll_mean": total / len(target), "tokens": len(target)}, None
