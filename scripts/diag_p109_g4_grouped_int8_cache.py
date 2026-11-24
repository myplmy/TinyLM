"""Measure grouped INT8 KV storage and logits on the existing packed 16L G4."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from pathlib import Path
from time import perf_counter

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_g4_int8_kv1024 as prior


TAG = "p109_g4_grouped_int8_cache_v1_20261119"
OUT = prior.OUT.with_name(TAG)
read, write, sha = prior.embedding.READ, prior.embedding.WRITE, prior.embedding.SHA
GROUP, TOLERANCE = 32, 0.001


def quantize(value, axis):
    values = value.float()
    limit = torch.finfo(torch.float16).tiny
    scale = (values.abs().amax(dim=axis, keepdim=True) / 127).clamp_min(limit).half()
    codes = (values / scale.float()).round().clamp(-127, 127).to(torch.int8)
    return codes.contiguous(), scale.contiguous()


@dataclass
class CacheSlice:
    key_codes: torch.Tensor
    key_scale: torch.Tensor
    value_codes: torch.Tensor
    value_scale: torch.Tensor
    tail_key: torch.Tensor
    tail_value: torch.Tensor

    @classmethod
    def create(cls, key, value):
        width = key.shape[-1]
        blocks = key.shape[-2] // GROUP
        count = blocks * GROUP
        key_block = key[..., :count, :].reshape(*key.shape[:2], blocks, GROUP, width)
        return cls(*quantize(key_block, -2), *quantize(value[..., :count, :], -1),
                   key[..., count:, :].contiguous().clone(), value[..., count:, :].contiguous().clone())

    def append(self, key, value):
        self.tail_key = torch.cat((self.tail_key, key[..., -1:, :]), dim=-2)
        self.tail_value = torch.cat((self.tail_value, value[..., -1:, :]), dim=-2)
        if self.tail_key.shape[-2] == GROUP:
            block = self.create(self.tail_key, self.tail_value)
            self.key_codes = torch.cat((self.key_codes, block.key_codes), dim=2)
            self.key_scale = torch.cat((self.key_scale, block.key_scale), dim=2)
            self.value_codes = torch.cat((self.value_codes, block.value_codes), dim=2)
            self.value_scale = torch.cat((self.value_scale, block.value_scale), dim=2)
            self.tail_key, self.tail_value = block.tail_key, block.tail_value

    def decode(self):
        keys = (self.key_codes.float() * self.key_scale.float()).half().flatten(2, 3)
        values = (self.value_codes.float() * self.value_scale.float()).half()
        return torch.cat((keys, self.tail_key), dim=-2), torch.cat((values, self.tail_value), dim=-2)

    def size(self):
        return sum(t.untyped_storage().nbytes() for t in vars(self).values())


def measure(model, ids, expected_ids):
    started = perf_counter()
    scores, fp16_bank = model(torch.tensor([ids]), use_cache=True, logits_last_only=True)
    assert len(fp16_bank) == 14
    assert all(t.dtype == torch.float16 and t.shape == (1, 3, len(ids), 64)
               for pair in fp16_bank.values() for t in pair)
    packed = {slot: CacheSlice.create(*pair) for slot, pair in fp16_bank.items()}
    packed_scores = scores
    packed_ids, rows = [], []
    for index, expected in enumerate(expected_ids):
        next_id = int(scores.argmax(-1))
        candidate_id = int(packed_scores.argmax(-1))
        assert next_id == expected
        assert torch.isfinite(scores).all() and torch.isfinite(packed_scores).all()
        packed_ids.append(candidate_id)
        rows.append(dict(step=index + 1, context=len(ids) + index, reference_id=next_id,
            candidate_id=candidate_id, max_abs_logits=float((scores - packed_scores).abs().amax()),
            reference_cache=sum(t.numel() * t.element_size() for pair in fp16_bank.values() for t in pair),
            stored_cache=sum(item.size() for item in packed.values())))
        if index + 1 < len(expected_ids):
            token = torch.tensor([[next_id]])
            scores, fp16_bank = model(token, use_cache=True, logits_last_only=True, past_kv=fp16_bank)
            packed_scores, returned = model(token, use_cache=True, logits_last_only=True,
                past_kv={slot: item.decode() for slot, item in packed.items()})
            assert packed.keys() == returned.keys()
            for slot, pair in returned.items():
                packed[slot].append(*pair)
            del returned
    assert rows[-1]["context"] == 1024 and rows[-1]["stored_cache"] == 5_763_072
    maximum = max(row["max_abs_logits"] for row in rows)
    return dict(rows=rows, expected_ids=expected_ids, candidate_ids=packed_ids,
                same_choices=packed_ids == expected_ids, max_abs_logits=maximum,
                numerical_gate_passed=maximum <= TOLERANCE, diagnostic_seconds=perf_counter() - started)


@torch.inference_mode()
def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    cutoff = prior.ORIGIN.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=250) < cutoff
    profile_path, report_path = prior.OUT / "profile.json", prior.OUT / "report.json"
    before, previous = read(profile_path), read(report_path)
    assert previous["profile_sha256"] == sha(profile_path)
    contract = prior.contract()
    assert contract == {k: v for k, v in before.items() if k not in ("cases", "affinity")}
    os.sched_setaffinity(0, {before["affinity"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    self_sha = sha(Path(__file__))
    profile = dict(tag=TAG, source_sha256=self_sha, previous_profile_sha256=sha(profile_path),
        previous_report_sha256=sha(report_path), group_tokens=GROUP, key_scale="FP16_CHANNEL_PER_GROUP",
        value_scale="FP16_PER_TOKEN_PER_HEAD", residual="FP16", cutoff=cutoff.isoformat(),
        comparison="FORCED_COMMON_GREEDY_HISTORY", max_abs_tolerance=TOLERANCE)
    write(OUT / "profile.json", profile)
    model = prior.load_candidate(contract)
    model.eval()
    model.cfg.kv_dtype = "fp16"
    results = {}
    with prior.DEPLOY.native_unpack(model), sdpa_kernel(SDPBackend.MATH):
        for name, request in before["cases"].items():
            row = measure(model, request["ids"], previous["requests"][name]["fp16"]["ids"])
            write(OUT / f"{name}.json", row)
            results[name] = row
            print("P109_INT8_KV", name, row["same_choices"], row["max_abs_logits"],
                  row["rows"][-1]["stored_cache"], row["rows"][-1]["reference_cache"], flush=True)
    assert not torch.cuda.is_initialized() and prior.contract() == contract
    assert sha(Path(__file__)) == self_sha and sha(report_path) == profile["previous_report_sha256"]
    write(OUT / "report.json", dict(profile_sha256=sha(OUT / "profile.json"), cases=results,
        tool_restores_fp16_before_attention=True, benchmark_end_to_end=False, checkpoint_writes=0))


if __name__ == "__main__":
    main()
