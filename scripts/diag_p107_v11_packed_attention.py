"""Check document offsets and grouped attention against the same dense visibility."""

import argparse
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import audit_p107_v11_attention_geometry as geometry
from tinylm.train.hybrid_mntp import document_visibility


def offsets_for(documents):
    if (documents.device.type != "cpu" or documents.ndim != 2 or documents.dtype != torch.long
            or min(documents.shape) < 1 or bool((documents < 0).any())
            or bool((documents[:, 1:] < documents[:, :-1]).any())):
        raise ValueError("packed attention requires ordered document IDs with no padding")
    starts = torch.ones_like(documents, dtype=torch.bool)
    starts[:, 1:] = documents[:, 1:] != documents[:, :-1]
    offsets = torch.cat((starts.flatten().nonzero().flatten(), torch.tensor([documents.numel()])))
    return offsets.to(torch.int32)


def attention(query, key, value, offsets, causal):
    batch, q_heads, length, depth = query.shape
    packed = tuple(t.transpose(1, 2).reshape(batch * length, t.shape[1], depth).contiguous()
                   for t in (query, key, value))
    if query.is_cuda:
        from torch.nn.attention.varlen import varlen_attn

        width = int(offsets.diff().max())
        positions = offsets.to(query.device)
        output = varlen_attn(*packed, positions, positions, width, width, is_causal=causal)
    else:
        output = torch.cat([
            F.scaled_dot_product_attention(*(t[first:last].transpose(0, 1).unsqueeze(0) for t in packed),
                                           is_causal=causal, enable_gqa=q_heads != key.shape[1])[0].transpose(0, 1)
            for first, last in zip(offsets[:-1].tolist(), offsets[1:].tolist(), strict=True)])
    return output.reshape(batch, length, q_heads, depth).transpose(1, 2)


def measure(documents, device, dtype, causal, seed):
    offsets = offsets_for(documents)
    lengths = offsets.diff().tolist()
    batch, length = documents.shape
    visible = document_visibility(documents, bidirectional=not causal).to(device)
    g = torch.Generator(device="cpu").manual_seed(seed)

    def tensor(heads):
        return torch.randn(batch, heads, length, 64, generator=g).to(device=device, dtype=dtype)

    qkv = tuple(tensor(heads).requires_grad_() for heads in (12, 3, 3))
    grad = tensor(12)
    with sdpa_kernel(SDPBackend.MATH):
        dense = F.scaled_dot_product_attention(*qkv, attn_mask=visible, enable_gqa=True)
        dense_grads = torch.autograd.grad(dense, qkv, grad_outputs=grad)
        packed = attention(*qkv, offsets, causal)
        packed_grads = torch.autograd.grad(packed, qkv, grad_outputs=grad)

    comparisons = {}
    for name, previous, candidate in zip(("output", "query_grad", "key_grad", "value_grad"),
                                         (dense, *dense_grads), (packed, *packed_grads), strict=True):
        delta = (previous.detach().float() - candidate.detach().float()).abs()
        if not bool(torch.isfinite(delta).all()):
            raise ValueError("nonfinite output or gradient")
        comparisons[name] = dict(max_abs=float(delta.max()), rms=float(delta.square().mean().sqrt()),
                                 exact_fraction=float((delta == 0).float().mean()))
    return dict(causal=causal, dtype=str(dtype), spans=lengths, comparisons=comparisons)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.device == "cpu" and os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("hide CUDA for the CPU diagnostic")
    started = perf_counter()
    torch.set_num_threads(2)
    pair = geometry.pair
    profile = json.loads(pair.supervisor.manifest_bytes(geometry.PROFILE, geometry.PROFILE_SHA))
    train = profile["splits"]["train"]
    path = geometry.INDEX_ROOT / "train_ends.npy"
    if pair.documents.pin(path) != train["index"]:
        raise ValueError("the adopted EOS index differs")
    ends = np.load(path, mmap_mode="r", allow_pickle=False)
    starts = geometry.scheduled_starts(train["tokens"], 1, pair.MICROS, pair.SEED)[0]
    docs = torch.from_numpy(np.searchsorted(ends, starts[..., None] + np.arange(pair.LENGTH), side="left"))
    choose = (0, pair.MICROS // 2)
    scopes = ((docs[choose[0]], True, "causal_v11"), (docs[choose[1]], False, "mntp_v11"),
              (torch.tensor([[9, 9, 10, 10, 10], [10, 10, 10, 11, 11]]), False, "batch_boundary"))
    dtypes = (torch.float32, torch.bfloat16) if args.device == "cpu" else (torch.bfloat16,)
    result = {name: [measure(rows, args.device, dtype, causal, pair.SEED) for dtype in dtypes]
              for rows, causal, name in scopes}
    report = dict(device=args.device, torch=torch.__version__, results=result, seconds=perf_counter() - started,
                  source_sha256=pair.evaluation.core6.digest(Path(__file__)), profile_sha256=geometry.PROFILE_SHA)
    if args.device == "cuda":
        report.update(device_name=torch.cuda.get_device_name(),
                      peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20)
    pair.supervisor.publish(args.output, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
