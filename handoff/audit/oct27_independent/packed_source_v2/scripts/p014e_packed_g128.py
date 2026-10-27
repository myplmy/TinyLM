"""Inference-only, original-scale ternary payload; reuse the existing five-trit codec.

This is a storage/loader and tiled FP32 reference, not a fast packed GEMM.
It never changes product defaults and deliberately rejects unsupported states.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace

import torch
from torch import nn
from torch.nn import functional as F

from tinylm.config import TMTConfig
from tinylm.model.lut import pack_trits, unpack_trits
from tinylm.model.ternary import TLinear, _group_of, ternary_g
from tinylm.model.transformer import TiedMLPTransformer

SCHEMA = "P014E_ORIGINAL_SCALE_G128_PAYLOAD_V1"


def need(value, message):
    if not value:
        raise ValueError(message)


def json_copy(value):
    """No tensors, modules, nonfinite numbers or aliased mutable provenance."""
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("finite JSON metadata required, never tensor state") from exc
    need(len(raw.encode("utf-8")) <= 1_000_000, "metadata is not a weight container")
    return json.loads(raw)


def supported_config(cfg):
    need(cfg.quant_anneal == 1.0 and cfg.wq_dtype == "fp32" and cfg.n_modes == 1
         and not cfg.mtp_aux and not cfg.use_ternary_kernel and not cfg.sparse34,
         "only frozen FP32 non-MTP single-mode ternary route is supported")
    need(not cfg.x2_active_tiles and cfg.mlp_lora_rank == 0 and cfg.connectivity_mode == "none",
         "pruned MLP tiles, connectivity and LoRA require a separately validated route")


def strict_pack(trits):
    """Check before the historical codec's integer cast; do not round fractions."""
    need(isinstance(trits, torch.Tensor) and trits.numel() > 0, "nonempty trits required")
    need(trits.dtype in (torch.int8, torch.int16, torch.int32, torch.int64, torch.float32),
         "unsupported trit dtype")
    need(bool(torch.isfinite(trits).all())
         and bool(((trits == -1) | (trits == 0) | (trits == 1)).all()),
         "exact finite ternary values required before codec")
    return pack_trits(trits)


def validate_record(record):
    need(set(record) == {"in_features", "out_features", "group", "codes", "scales"},
         "unknown packed record fields")
    i, o, g = (record[k] for k in ("in_features", "out_features", "group"))
    need(all(type(v) is int and v > 0 for v in (i, o, g)) and i % g == 0,
         "positive divisible packed shape required")
    codes, scales = record["codes"], record["scales"]
    need(isinstance(codes, torch.Tensor) and codes.dtype == torch.uint8
         and tuple(codes.shape) == (o, i // g, (g + 4) // 5), "packed code shape/dtype differs")
    need(isinstance(scales, torch.Tensor) and scales.dtype == torch.float32
         and tuple(scales.shape) == (o, i // g), "original FP32 group scale shape differs")
    need(codes.device == scales.device and not codes.is_meta and codes.is_contiguous()
         and scales.is_contiguous(), "real contiguous colocated packed tensors required")
    need(bool((codes <= 242).all()), "reserved byte code refused")
    need(bool(torch.isfinite(scales).all()) and bool((scales >= 0).all()),
         "finite nonnegative scales required")
    # Validation is bounded by output rows too: no full decoded FP32 matrix.
    for start in range(0, o, 128):
        raw = unpack_trits(codes[start:start + 128], codes.shape[-1] * 5)
        need(bool((raw[..., g:] == 0).all()), "nonzero padding trits refused")
        need(bool((raw[..., :g][scales[start:start + 128] == 0] == 0).all()),
             "zero-scale group must use canonical zero trits")


@torch.no_grad()
def pack_weight(weight, group, tile_rows=128):
    need(isinstance(weight, torch.Tensor) and weight.dtype == torch.float32
         and weight.ndim == 2 and not weight.is_meta, "real FP32 weight matrix required")
    o, i = weight.shape
    need(type(group) is int and group > 0 and i % group == 0
         and type(tile_rows) is int and tile_rows > 0, "invalid group/tile")
    codes, scales = [], []
    for start in range(0, o, tile_rows):
        w = weight[start:start + tile_rows].detach().to("cpu").reshape(-1, i // group, group)
        need(bool(torch.isfinite(w).all()), "nonfinite source weight")
        scale = w.abs().amax(-1)
        trits = w.sign().to(torch.int8)
        # No ratio/clamp: scales smaller than 1e-12 must still round-trip.
        need(torch.equal(trits.to(torch.float32) * scale.unsqueeze(-1), w),
             "source is not exactly one ternary magnitude per group")
        code, n = strict_pack(trits)
        need(n == group, "codec original group length changed")
        codes.append(code)
        scales.append(scale)
    result = dict(in_features=i, out_features=o, group=group,
                  codes=torch.cat(codes).contiguous(), scales=torch.cat(scales).contiguous())
    validate_record(result)
    return result


class PackedGroupLinear(nn.Module):
    """Output-row tiles only; no master, optimizer, or full unpack cache."""

    def __init__(self, record, tile_rows=128, cfg=None):
        super().__init__()
        validate_record(record)
        need(type(tile_rows) is int and tile_rows > 0, "positive tile rows required")
        self.in_f, self.out_f = record["in_features"], record["out_features"]
        self.group, self.tile_rows = record["group"], tile_rows
        self.cfg = cfg if cfg is not None else SimpleNamespace(x2_active_tiles=())
        self.register_buffer("packed_codes", record["codes"])
        self.register_buffer("group_scales", record["scales"])

    def train(self, mode=True):
        if mode:
            raise RuntimeError("packed deployment is inference-only")
        return super().train(False)

    def unpack_rows(self, start, stop):
        need(0 <= start < stop <= self.out_f, "invalid output rows")
        raw = unpack_trits(self.packed_codes[start:stop], self.group)
        return (raw.to(torch.float32) * self.group_scales[start:stop].unsqueeze(-1)).reshape(stop - start, self.in_f)

    def forward(self, x, mode_p=None):
        need(not torch.is_grad_enabled(), "packed inference requires no_grad or inference_mode")
        need(x.dtype == torch.float32 and x.device == self.packed_codes.device
             and x.shape[-1] == self.in_f, "FP32 colocated activation shape required")
        need(not torch.is_autocast_enabled(x.device.type), "autocast is a separate untested route")
        need(mode_p is None, "mode delta is not serialized by this payload")
        outputs = []
        for start in range(0, self.out_f, self.tile_rows):
            weight = self.unpack_rows(start, min(start + self.tile_rows, self.out_f))
            outputs.append(F.linear(x, weight))
            del weight
        return torch.cat(outputs, dim=-1)


class PackedTransformer(TiedMLPTransformer):
    """Use the product forward/cache, disallow returning to latent training."""

    def train(self, mode=True):
        if mode:
            raise RuntimeError("packed deployment cannot train")
        return super().train(False)

    def clear_quant(self):
        raise RuntimeError("packed deployment has no latent quantization state to restore")

    def refresh_quant(self):
        raise RuntimeError("packed deployment must keep its frozen original scales")

    def _emb_rows(self, idx=None):
        if getattr(self, "packed_embedding", None) is not None:
            return self.packed_embedding.rows(idx)
        return super()._emb_rows(idx)

    def _emb_w(self):
        if getattr(self, "packed_embedding", None) is not None:
            raise RuntimeError("full unpacked vocabulary matrix is forbidden")
        return super()._emb_w()

    def _head_logits(self, x):
        table = getattr(self, "packed_embedding", None)
        if table is None:
            return super()._head_logits(x)
        if self.emb_up is not None:
            x = F.linear(x, self._emb_up_w().t())
        outputs = []
        for start in range(0, table.vocab_size, table.head_rows):
            weight = table.rows(slice(start, min(start + table.head_rows, table.vocab_size)))
            outputs.append(F.linear(x, weight))
            del weight
        return torch.cat(outputs, dim=-1)


class PackedTernaryTable(nn.Module):
    """Existing per-row ternary embedding, five-trit storage, bounded head rows."""

    def __init__(self, record, head_rows):
        super().__init__()
        validate_record(record)
        need(record["group"] == record["in_features"] and type(head_rows) is int
             and 0 < head_rows < record["out_features"], "per-row table and bounded head chunk required")
        self.vocab_size, self.emb_rank = record["out_features"], record["in_features"]
        self.head_rows = head_rows
        self.register_buffer("packed_codes", record["codes"])
        self.register_buffer("group_scales", record["scales"])

    def rows(self, idx):
        need(idx is not None, "full vocabulary unpack is forbidden")
        if isinstance(idx, slice):
            start, stop, step = idx.indices(self.vocab_size)
            need(step == 1 and 0 < stop - start <= self.head_rows, "bounded contiguous head rows required")
            code, scale = self.packed_codes[idx], self.group_scales[idx]
        else:
            need(isinstance(idx, torch.Tensor) and idx.dtype == torch.long and idx.ndim == 1
                 and idx.device == self.packed_codes.device and idx.numel() <= 1024,
                 "context-bounded lookup IDs required")
            code, scale = self.packed_codes[idx], self.group_scales[idx]
        raw = unpack_trits(code, self.emb_rank).reshape(-1, self.emb_rank)
        return raw.to(torch.float32) * scale.reshape(-1, 1)


def _plain_tensor_check(model, skip_ids):
    for name, module in model.named_modules():
        if id(module) in skip_ids:
            continue
        for key, value in vars(module).items():
            if key not in ("_parameters", "_buffers", "_modules"):
                need(not isinstance(value, torch.Tensor),
                     "unserialized plain tensor attribute: " + name + "." + key)


@torch.no_grad()
def export_payload(model, *, provenance, tile_rows=128, embedding_format="fp32_unchanged", head_rows=1024):
    need(type(model) is TiedMLPTransformer and not model.training and model._quant_frozen,
         "frozen unmodified product model required")
    cfg = model.cfg
    supported_config(cfg)
    need(model.embedding_quantized() is None and not model._int8_store
         and not model._lut_store and not model._unpack_cache,
         "preconverted embedding/cache routes require a separate payload")
    need(embedding_format in ("fp32_unchanged", "ternary5_existing_twn"), "unknown embedding format")
    embedding = None
    if embedding_format == "ternary5_existing_twn":
        need(0 < head_rows < cfg.vocab_size, "bounded vocabulary head chunk required")
        # Reuse the product TWN function, not a new quantizer. This changes FP32
        # embedding quality and must be compared separately from lossless body packing.
        weight = ternary_g(model.emb.weight.detach(), model.emb.weight.shape[-1], cfg)
        embedding = pack_weight(weight, weight.shape[-1], tile_rows)
        del weight
    records, owners, excluded = [], {}, set()
    for path, module in model.named_modules(remove_duplicate=False):
        if not isinstance(module, TLinear):
            continue
        need(not module.use_mode and module.connectivity_mask is None
             and module._wq is not None and module._i8 is None and module._lut_codes is None,
             "unsupported TLinear state")
        if id(module) not in owners:
            owners[id(module)] = len(records)
            records.append(dict(paths=[], weight=pack_weight(module._wq, _group_of(cfg, module.in_f), tile_rows)))
        records[owners[id(module)]]["paths"].append(path)
        excluded.add(path + ".weight")
    need(records, "no physical ternary matrices found")
    if embedding is not None:
        excluded.add("emb.weight")
    _plain_tensor_check(model, set(owners))
    rest, tensors = [], {}
    for kind, values in (("parameter", model.named_parameters(remove_duplicate=False)),
                         ("buffer", model.named_buffers(remove_duplicate=False))):
        for path, tensor in values:
            if path in excluded:
                continue
            need(not tensor.is_meta and tensor.dtype == torch.float32
                 and bool(torch.isfinite(tensor).all()), "only finite FP32 rest tensors supported")
            key = (kind, id(tensor))
            if key not in tensors:
                tensors[key] = len(rest)
                rest.append(dict(kind=kind, paths=[], tensor=tensor.detach().to("cpu").clone()))
            rest[tensors[key]]["paths"].append(path)
    need(type(provenance) is dict and all(type(k) is str for k in provenance), "explicit provenance required")
    return dict(schema=SCHEMA, cfg=asdict(cfg), provenance=json_copy(provenance), matrices=records,
                rest=rest, original_parameters=sum(p.numel() for p in model.parameters()),
                tile_rows=tile_rows, embedding_format=embedding_format, embedding=embedding,
                embedding_head_rows=head_rows if embedding is not None else None,
                arithmetic="FP32_ROW_TILE_LINEAR_REFERENCE_NOT_DIRECT_PACKED_KERNEL")


def _slot(model, path):
    need(type(path) is str and path and ".." not in path, "invalid module path")
    parent, sep, name = path.rpartition(".")
    return model.get_submodule(parent) if sep else model, name


def payload_storage(payload):
    seen, total = set(), 0
    values = [v for row in payload["matrices"] for v in (row["weight"]["codes"], row["weight"]["scales"])]
    values.extend(row["tensor"] for row in payload["rest"])
    if payload.get("embedding") is not None:
        values.extend((payload["embedding"]["codes"], payload["embedding"]["scales"]))
    for tensor in values:
        storage = tensor.untyped_storage()
        key = (str(tensor.device), storage.data_ptr(), storage.nbytes())
        if key not in seen:
            seen.add(key)
            total += storage.nbytes()
    return dict(unique_storage_bytes=total, unique_storages=len(seen),
                physical_matrices=len(payload["matrices"]),
                logical_parameters=payload["original_parameters"])


def save_new(payload, path):
    need(payload.get("schema") == SCHEMA, "packed payload schema differs")
    path = Path(path)
    need(not path.exists() and not any(p.is_symlink() for p in (path, *path.parents)),
         "new nonsymlink deployment path required")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        torch.save(payload, stream)
    return path.stat().st_size


def load_payload(payload, *, device="cpu", tile_rows=None):
    need(set(payload) == {"schema", "cfg", "provenance", "matrices", "rest", "original_parameters",
                          "tile_rows", "embedding_format", "embedding", "embedding_head_rows", "arithmetic"},
         "unknown payload fields may hide unneeded master state")
    need(payload.get("schema") == SCHEMA
         and payload.get("embedding_format") in ("fp32_unchanged", "ternary5_existing_twn"),
         "packed payload schema/embedding differs")
    json_copy(payload["provenance"])
    try:
        cfg = TMTConfig(**json_copy(payload["cfg"]))
    except (TypeError, AssertionError) as exc:
        raise ValueError("invalid deployment cfg") from exc
    supported_config(cfg)
    # All latent matrices and random initialization stay on meta, not host RAM.
    with torch.random.fork_rng(devices=[]), torch.device("meta"):
        model = PackedTransformer(cfg)
    expected_matrices = {}
    for path, module in model.named_modules(remove_duplicate=False):
        if isinstance(module, TLinear):
            expected_matrices.setdefault(id(module), set()).add(path)
    expected_aliases = {frozenset(paths) for paths in expected_matrices.values()}
    need(len(payload["matrices"]) == len(expected_aliases)
         and {frozenset(row["paths"]) for row in payload["matrices"]} == expected_aliases,
         "physical source matrix alias coverage differs")
    seen, packed_ids = set(), set()
    for row in payload["matrices"]:
        need(set(row) == {"paths", "weight"} and row["paths"], "invalid physical matrix record")
        packed = PackedGroupLinear(row["weight"], payload["tile_rows"] if tile_rows is None else tile_rows, cfg=cfg)
        for path in row["paths"]:
            need(path not in seen, "duplicate packed path")
            seen.add(path)
            parent, name = _slot(model, path)
            old = parent._modules.get(name)
            need(isinstance(old, (TLinear, PackedGroupLinear))
                 and (old.in_f, old.out_f) == (packed.in_f, packed.out_f), "packed structural path differs")
            need(packed.group == _group_of(cfg, packed.in_f), "group differs from the source cfg")
            parent._modules[name] = packed
        packed_ids.add(id(packed))
    # Plain runtime lists would retain meta TLinear objects, including masters.
    model._tlinear_cache = []
    model._armed_tlinears = []
    model._cacheable_mlps = []
    packed_buffer_paths = {path + "." + key for path in seen
                           for key in ("packed_codes", "group_scales")}
    if payload["embedding_format"] == "ternary5_existing_twn":
        embedding = payload["embedding"]
        need((embedding["out_features"], embedding["in_features"])
             == tuple(model.emb.weight.shape), "embedding table shape differs")
        model.packed_embedding = PackedTernaryTable(embedding, payload["embedding_head_rows"])
        model.emb.weight = nn.Parameter(torch.empty(0), requires_grad=False)
        model._emb_fmt = "packed_ternary5"
        packed_buffer_paths.update({"emb.weight", "packed_embedding.packed_codes", "packed_embedding.group_scales"})
    else:
        need(payload.get("embedding") is None and payload.get("embedding_head_rows") is None,
             "FP32 variant must not contain a second embedding table")
    expected_rest = {}
    for kind, values in (("parameter", model.named_parameters(remove_duplicate=False)),
                         ("buffer", model.named_buffers(remove_duplicate=False))):
        for path, tensor in values:
            if path not in packed_buffer_paths:
                expected_rest.setdefault((kind, id(tensor)), set()).add(path)
    need({(kind, frozenset(paths)) for (kind, _), paths in expected_rest.items()}
         == {(row["kind"], frozenset(row["paths"])) for row in payload["rest"]}
         and len(expected_rest) == len(payload["rest"]), "rest parameter/buffer alias coverage differs")
    assigned = set()
    for row in payload["rest"]:
        need(set(row) == {"kind", "paths", "tensor"} and row["paths"], "invalid rest record")
        kind, tensor = row["kind"], row["tensor"]
        need(kind in ("parameter", "buffer") and isinstance(tensor, torch.Tensor)
             and tensor.device.type == "cpu" and tensor.dtype == torch.float32
             and bool(torch.isfinite(tensor).all()), "invalid CPU rest tensor")
        value = nn.Parameter(tensor, requires_grad=False) if kind == "parameter" else tensor
        for path in row["paths"]:
            need(path not in assigned, "duplicate rest path")
            assigned.add(path)
            parent, name = _slot(model, path)
            table = parent._parameters if kind == "parameter" else parent._buffers
            old = table.get(name)
            need(old is not None and tuple(old.shape) == tuple(tensor.shape), "rest structural shape differs")
            table[name] = value
    need(not any(isinstance(m, TLinear) for m in model.modules()), "unreplaced latent TLinear")
    need(not any(t.is_meta for t in (*model.parameters(), *model.buffers())), "unserialized meta tensor remains")
    need(len(packed_ids) == len(payload["matrices"]), "physical matrix aliases differ")
    model._quant_frozen = True
    model._packed_g128_inference = True
    model.eval().to(device)
    return model


def load_file(path, *, device="cpu", tile_rows=None):
    with Path(path).open("rb") as stream:
        payload = torch.load(stream, map_location="cpu", weights_only=True)
    return load_payload(payload, device=device, tile_rows=tile_rows)
