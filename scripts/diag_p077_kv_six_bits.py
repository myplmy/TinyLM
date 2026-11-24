"""Compare packed prefix K/V splits on the P077 cache geometry."""

import json
from pathlib import Path
import sys

import numpy as np

from scripts import diag_p077_old_kv_precision as previous


OLD = 1920
RESIDENT_GAP = 3_280_896  # Result 065 §10.10, same native measurement phase.
TARGETS = np.array([17, 191, 511, 960, 1023, 1079, 1230, 1792, 1855, 1919, 1920, 1968, 2005, 2047])
PROFILES = (
    ("previous_k4v4", previous.OLD, 4, 4, False, False),
    ("k3v3", OLD, 3, 3, False, False),
    ("k2v4", OLD, 2, 4, True, False),
    ("k4v2", OLD, 4, 2, False, True),
)
OWNERS = np.repeat(np.arange(previous.KV_HEADS), 4)


def quantize(values, side, bits, affine):
    if bits >= 4:
        return previous.quantize(values, side, bits)
    values32 = values.astype(np.float32)
    if side == "key":
        values32 = values32.reshape(-1, previous.GROUP, previous.KV_HEADS, previous.HEAD)
    axis = 1 if side == "key" else -1
    if affine:
        offset = values32.min(axis=axis, keepdims=True).astype(np.float16)
        limit = (1 << bits) - 1
        width = values32.max(axis=axis, keepdims=True) - offset.astype(np.float32)
        bias = 0
    else:
        offset = None
        limit = (1 << (bits-1)) - 1
        width = np.abs(values32).max(axis=axis, keepdims=True)
        bias = limit
    scales = np.maximum(width/limit, previous.LOWEST_FP16_SCALE).astype(np.float16)
    scale32 = scales.astype(np.float32)
    minimum = 0.0 if offset is None else offset.astype(np.float32)
    indices = np.clip(np.rint((values32-minimum)/scale32)+bias, 0, limit+bias).astype(np.uint8)
    shifts = np.arange(bits, dtype=np.uint8)
    planes = (indices.reshape(-1, 1) >> shifts) & 1
    packed = np.packbits(planes.reshape(-1), bitorder="little")
    decoded_planes = np.unpackbits(packed, bitorder="little", count=indices.size*bits).reshape(-1, bits)
    recovered = (decoded_planes << shifts).sum(axis=1, dtype=np.uint8).reshape(indices.shape)
    if not np.array_equal(recovered, indices):
        raise AssertionError("packed code mismatch")
    restored = ((recovered.astype(np.float32)-bias)*scale32 + minimum).astype(np.float16).reshape(values.shape)
    return restored, packed.nbytes+scales.nbytes+(0 if offset is None else offset.nbytes)


def mixed(key, value, old, k, v, k_affine, v_affine):
    decoded, nbytes = [], (previous.GROUP-1)*previous.KV_HEADS*previous.HEAD*4
    for side, data, bits, affine in (("key", key, k, k_affine), ("value", value, v, v_affine)):
        early, old_bytes = quantize(data[:old], side, bits, affine)
        recent, recent_bytes = quantize(data[old:], side, 8, False)
        decoded.append(np.concatenate((early, recent)))
        nbytes += old_bytes+recent_bytes
    return *decoded, nbytes*previous.SLOTS


def attention_weights(query, key):
    scores = np.einsum("qhd,thd->qht", query, key[:, OWNERS].astype(np.float32)) * np.float32(0.125)
    weight = np.exp(scores - scores.max(axis=-1, keepdims=True))
    weight /= weight.sum(axis=-1, keepdims=True)
    return weight


def weighted_value(weights, value):
    return np.einsum("qht,thd->qhd", weights, value[:, OWNERS].astype(np.float32))


def compare(kind, seed):
    rng = np.random.default_rng(seed)
    shape = (previous.LENGTH, previous.KV_HEADS, previous.HEAD)
    key = rng.normal(0, .25, shape)
    value = rng.normal(0, .4, shape)
    if kind == "channel_scales":
        key *= rng.lognormal(0, .7, (1, previous.KV_HEADS, previous.HEAD))
    if kind == "token_scales":
        value *= rng.lognormal(0, .7, (previous.LENGTH, previous.KV_HEADS, 1))
    key, value = key.astype(np.float16), value.astype(np.float16)
    control_key, control_value, control_bytes = previous.cache(key, value, 8, 8)
    plain = rng.normal(0, .5, (12, previous.KV_HEADS*4, previous.HEAD)).astype(np.float32)
    focus = key[TARGETS][:, OWNERS].astype(np.float32)
    focus *= 8 / np.maximum(np.linalg.norm(focus, axis=-1, keepdims=True), 1e-5)
    q = np.concatenate((plain, focus))
    control_w = attention_weights(q, control_key)
    control_y = weighted_value(control_w, control_value)
    focus_ref = control_w[12:].argmax(-1) == TARGETS[:, None]
    old_rows = TARGETS < OLD
    rows = np.arange(TARGETS.size)+12
    reference_mass = control_w[rows, :, TARGETS]
    first = previous.cache(key, value, 4, 4)
    comparison = {}
    for name, old, bits_k, bits_v, affine_k, affine_v in PROFILES:
        cur_k, cur_v, size = mixed(key, value, old, bits_k, bits_v, affine_k, affine_v)
        if (not np.array_equal(cur_k[old:], control_key[old:]) or
                not np.array_equal(cur_v[old:], control_value[old:])):
            raise AssertionError("the recent INT8 rows changed")
        if name == "previous_k4v4" and (size != first[2] or not np.array_equal(cur_k, first[0])
                                       or not np.array_equal(cur_v, first[1])):
            raise AssertionError("the reference K4/V4 route changed")
        w = attention_weights(q, cur_k)
        old_focus = (w[12:].argmax(-1) == TARGETS[:, None]) & focus_ref
        lost_mass = (reference_mass-w[rows, :, TARGETS])[old_rows][focus_ref[old_rows]]
        saved = first[2]-size
        comparison[name] = dict(bytes=size, saved_from_previous=saved, projected_gap_bytes=RESIDENT_GAP-saved,
            k_rmse=previous.rmse(cur_k, control_key), v_rmse=previous.rmse(cur_v, control_value),
            k_only_output_rmse=previous.rmse(weighted_value(w, control_value), control_y),
            v_only_output_rmse=previous.rmse(weighted_value(control_w, cur_v), control_y),
            output_rmse=previous.rmse(weighted_value(w, cur_v), control_y),
            old_focus=[int(old_focus[old_rows].sum()), int(focus_ref[old_rows].sum())],
            recent_focus=[int(old_focus[~old_rows].sum()), int(focus_ref[~old_rows].sum())],
            old_target_mass_loss_mean=float(lost_mass.mean()), old_target_mass_abs_mean=float(np.abs(lost_mass).mean()))
    return dict(int8_bytes=control_bytes, profiles=comparison)


def main(output):
    results = {name: compare(name, seed) for name, seed in (("ordinary", 1701),
               ("channel_scales", 1702), ("token_scales", 1703))}
    output.mkdir(exist_ok=False)
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(synthetic=True, old_rows=OLD, recent_rows=previous.LENGTH-OLD,
                       observed_resident_gap_bytes=RESIDENT_GAP, profiles=results), stream, indent=2)
        stream.write(chr(10))
    for name, r in results.items():
        print(name, {key: [v["bytes"], v["old_focus"], round(v["output_rmse"], 5)]
                     for key, v in r["profiles"].items()})


if __name__ == "__main__":
    main(Path(sys.argv[1]))
