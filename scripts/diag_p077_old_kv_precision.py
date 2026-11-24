"""Measure actual packed bytes and synthetic attention for a mixed KV prefix."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


LENGTH, OLD, GROUP, KV_HEADS, HEAD, SLOTS = 2048, 1024, 32, 3, 64, 14
TARGETS = np.array([17, 191, 511, 960, 1079, 1230, 1792, 2005])
LOWEST_FP16_SCALE = np.finfo(np.float16).tiny


def quantize(value, kind, bits):
    values = value.astype(np.float32)
    if kind == "key":
        values = values.reshape(-1, GROUP, KV_HEADS, HEAD)
    axis = 1 if kind == "key" else -1
    limit = (1 << (bits - 1)) - 1
    scales = np.maximum(np.abs(values).max(axis=axis, keepdims=True) / limit,
                        LOWEST_FP16_SCALE).astype(np.float16)
    codes = np.clip(np.rint(values / scales.astype(np.float32)), -limit, limit).astype(np.int8)
    if bits == 4:
        nibbles = codes.reshape(-1).astype(np.uint8) & 15
        packed = nibbles[::2] | (nibbles[1::2] << 4)
        read = np.empty(len(nibbles), dtype=np.int8)
        read[::2] = packed & 15
        read[1::2] = packed >> 4
        restored = ((read ^ 8) - 8).reshape(codes.shape)
        if not np.array_equal(codes, restored):
            raise AssertionError("the packed nibble round trip changed a code")
        codes = restored
    else:
        packed = codes
    decoded = (codes.astype(np.float32) * scales.astype(np.float32)).astype(np.float16).reshape(value.shape)
    return decoded, packed.nbytes + scales.nbytes


def cache(key, value, key_bits, value_bits):
    decoded = []
    tail_bytes = (GROUP - 1) * KV_HEADS * HEAD * 2 * np.dtype(np.float16).itemsize
    bytes_per_slot = tail_bytes
    for kind, states, bits in (("key", key, key_bits), ("value", value, value_bits)):
        prefix, prefix_bytes = quantize(states[:OLD], kind, bits)
        recent, recent_bytes = quantize(states[OLD:], kind, 8)
        decoded.append(np.concatenate((prefix, recent)))
        bytes_per_slot += prefix_bytes + recent_bytes
    return (*decoded, bytes_per_slot * SLOTS)


def attention(query, key, value):
    owners = np.repeat(np.arange(KV_HEADS), 4)
    scores = np.einsum("qhd,thd->qht", query, key[:, owners].astype(np.float32)) * np.float32(0.125)
    exp = np.exp(scores - scores.max(axis=-1, keepdims=True))
    weights = exp / exp.sum(axis=-1, keepdims=True)
    output = np.einsum("qht,thd->qhd", weights, value[:, owners].astype(np.float32))
    return scores.argmax(axis=-1), output


def rmse(left, right):
    difference = left.astype(np.float32) - right.astype(np.float32)
    return float(np.sqrt(np.mean(difference ** 2)))


def compare(kind, seed):
    rng = np.random.default_rng(seed)
    shape = (LENGTH, KV_HEADS, HEAD)
    key = rng.normal(0, 0.25, shape)
    value = rng.normal(0, 0.4, shape)
    if kind == "channel_scales":
        key *= rng.lognormal(0, 0.7, (1, KV_HEADS, HEAD))
    if kind == "token_scales":
        value *= rng.lognormal(0, 0.7, (LENGTH, KV_HEADS, 1))
    key, value = key.astype(np.float16), value.astype(np.float16)
    query = rng.normal(0, 0.5, (12, KV_HEADS * 4, HEAD)).astype(np.float32)
    selected = np.repeat(key[TARGETS].astype(np.float32), 4, axis=1)
    selected = selected / np.maximum(np.linalg.norm(selected, axis=-1, keepdims=True), 1e-5) * 8
    query = np.concatenate((query, selected))
    fp16_rank, fp16_out = attention(query, key, value)
    int8_key, int8_value, int8_bytes = cache(key, value, 8, 8)
    int8_rank, int8_out = attention(query, int8_key, int8_value)
    focus = int8_rank[12:] == TARGETS[:, None]
    variants = {}
    for key_bits, value_bits in ((8, 8), (4, 8), (8, 4), (4, 4)):
        candidate_key, candidate_value, size = cache(key, value, key_bits, value_bits)
        if (not np.array_equal(candidate_key[OLD:], int8_key[OLD:])
                or not np.array_equal(candidate_value[OLD:], int8_value[OLD:])):
            raise AssertionError("recent key/value changed under old-prefix precision")
        rank, output = attention(query, candidate_key, candidate_value)
        hits = rank[12:] == TARGETS[:, None]
        variants[f"k{key_bits}v{value_bits}"] = dict(cache_bytes=size, saved_bytes=int8_bytes - size,
            key_rmse_to_fp16=rmse(candidate_key, key), value_rmse_to_fp16=rmse(candidate_value, value),
            output_rmse_to_fp16=rmse(output, fp16_out), output_rmse_to_int8=rmse(output, int8_out),
            output_top_position_same_as_fp16=int((rank == fp16_rank).sum()),
            output_top_position_same_as_int8=int((rank == int8_rank).sum()), top_positions=rank.size,
            old_focus_conditioned=[int((hits[:4] & focus[:4]).sum()), int(focus[:4].sum())],
            recent_focus_conditioned=[int((hits[4:] & focus[4:]).sum()), int(focus[4:].sum())])
    return variants


def main(path):
    profiles = {name: compare(name, seed) for name, seed in (("ordinary", 1701),
                ("channel_scales", 1702), ("token_scales", 1703))}
    value = dict(synthetic=True, length=LENGTH, prefix_low_precision=OLD, profiles=profiles,
                 sources={Path(__file__).name: hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()})
    path.mkdir(exist_ok=False)
    with (path / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write(chr(10))
    for name, variants in profiles.items():
        print(name, {variant: (row["cache_bytes"], row["output_rmse_to_fp16"], row["old_focus_conditioned"])
                     for variant, row in variants.items()})


if __name__ == "__main__":
    main(Path(sys.argv[1]))
