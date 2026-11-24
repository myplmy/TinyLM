"""Check one fixed-scale edit through the existing packed export on CPU."""

from contextlib import nullcontext
from datetime import datetime
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import sys

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import p014e_packed_g128 as packed
from scripts import p108_native_scale as native
from scripts.p108_shared_ternary_edit import apply_shared_down_packets, physical_down_owners
from scripts.p108_weight_space import tensor_sha
from tinylm.config import TMTConfig
from tinylm.infer.generate import _strip
from tinylm.model.transformer import TiedMLPTransformer


ROOT = Path(__file__).resolve().parents[1]
TAG = "p108_g4_shared_pack_transfer_v2_20261119"
PARENT = ROOT / "runs/ckpt/m100s12_ko-en_300M_d16_g4_r20.pt"
PARENT_SHA = "D576B9EB6DEF02DF5DCCAD91E484098AFB67A52553A7A735B21249DB2D9EC3D5"
CUTOFF = datetime.fromisoformat("2026-11-19T16:56:00+09:00")
OUT = ROOT / "test_result/evidence" / TAG / "report.json"
SOURCES = (
    "scripts/diag_p108_g4_shared_pack.py", "scripts/p014e_packed_g128.py",
    "scripts/p108_native_scale.py", "scripts/p108_shared_ternary_edit.py",
    "scripts/p108_weight_space.py", "tinylm/config.py", "tinylm/infer/generate.py",
    "tinylm/model/transformer.py", "tinylm/model/modules.py", "tinylm/model/ternary.py",
    "tinylm/model/lut.py",
)


def digest(path):
    result = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest().upper()


def load_model():
    checkpoint = torch.load(PARENT, map_location="cpu", weights_only=True, mmap=True)
    cfg = TMTConfig(**checkpoint["cfg"])
    packed.supported_config(cfg)
    assert (cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.cla_group) == (2, 12, 2, 4, 2)
    assert cfg.tie_mlp and cfg.micro_group == 128 and cfg.train_repeat == 2
    assert cfg.infer_repeat == 1 and cfg.repeat_mode == "uniform" and cfg.vocab_size == 32768
    model = TiedMLPTransformer(cfg).eval()
    model.load_state_dict(_strip(checkpoint["model"]), strict=True)
    model.freeze_quant()
    assert len(model.visit_schedule()) == 28
    return model, checkpoint["step"]


def edit_packet(weight, group):
    codes, _ = native.layout(weight, group)
    for row in range(codes.shape[0]):
        for group_index, trits in enumerate(codes[row]):
            nonzero = trits.ne(0).nonzero().flatten().tolist()
            zeros = trits.eq(0).nonzero().flatten().tolist()
            for sign in nonzero:
                new = next((zero for zero in zeros if zero // 5 != sign // 5), None)
                if new is not None:
                    modified = codes.clone()
                    modified[row, group_index, sign] = -trits[sign]
                    modified[row, group_index, new] = 1
                    target = native.from_codes(weight, modified, group)
                    return native.packet(weight, target, group), ((row, group_index, sign // 5),
                                                                 (row, group_index, new // 5))
    raise RuntimeError("no group supports the predeclared edit")


def probe(model, module, tokens):
    hits = []
    handle = module.register_forward_hook(lambda *_: hits.append(1))
    try:
        full = model(tokens, logits_last_only=True)
        full_visits = len(hits)
        _, before = model(tokens[:, :-1], use_cache=True, logits_last_only=True)
        prefill_visits = len(hits) - full_visits
        cached, after = model(tokens[:, -1:], past_kv=before, use_cache=True, logits_last_only=True)
    finally:
        handle.remove()
    visits = [full_visits, prefill_visits, len(hits) - full_visits - prefill_visits]
    assert visits == [8, 8, 8]
    assert len(before) == len(after) == 14 and set(before) == set(after)
    assert all(k.shape[2] == v.shape[2] == tokens.shape[1] for k, v in after.values())
    return full, cached, visits


def compare(reference, observed):
    assert reference.shape == observed.shape and bool(torch.isfinite(reference).all() & torch.isfinite(observed).all())
    return {"logits": reference.numel(), "max_abs": float((reference - observed).abs().max()),
            "outside_tolerance": int((~torch.isclose(observed, reference, atol=2e-6, rtol=2e-5)).sum()),
            "reference_greedy": reference.argmax(dim=-1).tolist(),
            "observed_greedy": observed.argmax(dim=-1).tolist()}


def fingerprint(payload):
    matrices = {tuple(row["paths"]): (tensor_sha(row["weight"]["codes"]), tensor_sha(row["weight"]["scales"]))
                for row in payload["matrices"]}
    rest = {(row["kind"], tuple(row["paths"])): tensor_sha(row["tensor"]) for row in payload["rest"]}
    return matrices, rest


def packed_probe(model, owner, tokens):
    full, cached, eager_visits = probe(model, owner.module, tokens)
    payload = packed.export_payload(model, provenance={"source_checkpoint_sha256": PARENT_SHA, "tag": TAG})
    with BytesIO() as stream:
        torch.save(payload, stream)
        archive_bytes = stream.tell()
        stream.seek(0)
        reloaded = torch.load(stream, map_location="cpu", weights_only=True)
    fingerprints = fingerprint(reloaded)
    assert fingerprints == fingerprint(payload)
    registered_paths = next(paths for paths in fingerprints[0] if model.get_submodule(paths[0]) is owner.module)
    loaded = packed.load_payload(reloaded)
    layer = loaded.get_submodule(registered_paths[0])
    assert all(loaded.get_submodule(path) is layer for path in registered_paths)
    logical_layers = tuple(i for i, block in enumerate(loaded.layers) if block.mlp[0].down_proj is layer)
    assert logical_layers == owner.layers
    assert type(layer) is packed.PackedGroupLinear and layer.group == model.cfg.micro_group
    for start in range(0, layer.out_f, layer.tile_rows):
        stop = min(start + layer.tile_rows, layer.out_f)
        assert torch.equal(layer.unpack_rows(start, stop), owner.module._wq[start:stop])
    packed_full, packed_cached, packed_visits = probe(loaded, layer, tokens)
    checks = {"full_eager_packed": compare(full, packed_full),
              "cached_eager_packed": compare(cached, packed_cached),
              "eager_full_cached": compare(full, cached),
              "packed_full_cached": compare(packed_full, packed_cached)}
    evidence = {"checks": checks, "archive_bytes": archive_bytes,
                "eager_owner_visits": eager_visits, "packed_owner_visits": packed_visits,
                "storage": packed.payload_storage(reloaded)}
    return evidence, full, packed_full, fingerprints, registered_paths, layer.packed_codes, layer.group_scales


@torch.no_grad()
def verify():
    model, step = load_model()
    owner = physical_down_owners(model)[2]
    assert owner.layers == (2, 3, 4, 5) and len(owner.visits) == 8
    cache = owner.module._wq
    master_sha = tensor_sha(owner.module.weight)
    cache_sha = tensor_sha(cache)
    packet, expected_bytes = edit_packet(cache, model.cfg.micro_group)
    tokens = torch.tensor([[1, 127, 1097, 3111, 3, 233], [2, 319, 5501, 28904, 61, 7]])
    outputs = {}
    with sdpa_kernel(SDPBackend.MATH):
        for name, selected in (("original", None), ("frozen_edit", packet)):
            context = nullcontext() if selected is None else apply_shared_down_packets(model, {2: selected}, realization="codes")
            with context as receipt:
                outputs[name] = packed_probe(model, owner, tokens)
                if receipt is not None:
                    assert receipt[0]["changed_trits"] == 2 and receipt[0]["changed_master"] == 0
                    assert tensor_sha(owner.module._wq) == packet["target_sha256"]
    assert tensor_sha(owner.module.weight) == master_sha
    assert owner.module._wq is cache and tensor_sha(cache) == cache_sha
    original, eager, original_pack, (base_weights, base_rest), paths, base_codes, old_scales = outputs["original"]
    edited, after_eager, edited_pack, (new_weights, new_rest), edit_paths, new_codes, new_scales = outputs["frozen_edit"]
    assert edit_paths == paths and base_rest == new_rest and base_weights.keys() == new_weights.keys()
    assert [path for path in base_weights if base_weights[path] != new_weights[path]] == [paths]
    assert tensor_sha(old_scales) == tensor_sha(new_scales)
    changed_bytes = [tuple(point) for point in base_codes.ne(new_codes).nonzero().tolist()]
    assert sorted(changed_bytes) == sorted(expected_bytes)
    model.freeze_quant()
    assert tensor_sha(owner.module._wq) == cache_sha
    status = all(not row["outside_tolerance"] and row["reference_greedy"] == row["observed_greedy"]
                 for arm in (original, edited) for row in arm["checks"].values())
    return dict(checkpoint_step=step, prompts=tokens.tolist(), owner_layers=owner.layers, visit_ordinals=owner.visits,
                packet=packet, changed_packed_bytes=changed_bytes, registered_paths=paths,
                original=original, frozen_edit=edited, master_unchanged=True, refreeze_restored=True,
                untouched_payload_equal=True, group_scales_equal=True, kv_entries=14,
                eager_edit_max_abs=float((after_eager - eager).abs().max()),
                packed_edit_max_abs=float((edited_pack - original_pack).abs().max()),
                full_logit_gate_pass=status)


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or datetime.now(CUTOFF.tzinfo) >= CUTOFF:
        raise RuntimeError("active CPU-only approval window required")
    if OUT.parent.exists() or PARENT.is_symlink() or digest(PARENT) != PARENT_SHA:
        raise RuntimeError("existing output or unapproved checkpoint")
    pins = {name: digest(ROOT / name) for name in SOURCES}
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    print("P108_G4_PACK_SOURCE", TAG, PARENT_SHA, json.dumps(pins, sort_keys=True), flush=True)
    report = verify()
    assert not torch.cuda.is_initialized()
    assert digest(PARENT) == PARENT_SHA and pins == {name: digest(ROOT / name) for name in SOURCES}
    report.update(tag=TAG, checkpoint=str(PARENT.relative_to(ROOT)), checkpoint_sha256=PARENT_SHA,
                  source_pins=pins, torch_version=str(torch.__version__), checkpoint_writes=0, training_updates=0)
    OUT.parent.mkdir()
    with OUT.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print("P108_G4_PACK_RESULT", json.dumps(report, ensure_ascii=False, allow_nan=False), flush=True)
    return 0 if report["full_logit_gate_pass"] else 8


if __name__ == "__main__":
    sys.exit(main())
