"""Compare precomputed frozen teacher features with the P109 online KL run."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
from time import perf_counter
from unittest.mock import patch

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109_qwen35_248k_warm_kl as online


ce = online.ce
TAG = "p109_qwen35_248k_cached_kl_v2_20261119"
OUT = ce.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
EXPORT = OUT / "trained_5trit.pt"
REFERENCE = online.OUT / "report.json"
CACHE_BATCH = 16


def verify(profile):
    assert all(ce.qwen.digest(ce.ROOT / p) == sha for p, sha in profile["pins"].items())
    ref = ce.qwen.load(REFERENCE)
    assert ref["source_preserved"] and ref["profile_sha256"] == ce.qwen.digest(online.PROFILE)
    assert len(ref["history"]) == ce.UPDATES
    baseline = online.verify(ce.qwen.load(online.PROFILE))
    return ref, baseline


def prepare():
    prior = ce.qwen.load(online.PROFILE)
    cfg = ce.qwen.load(ce.ROOT / prior["teacher"] / "config.json")
    assert cfg["text_config"]["hidden_size"] == 1024
    files = [Path(__file__), Path(online.__file__), online.PROFILE, REFERENCE]
    with np.load(ce.DATA, allow_pickle=False) as data:
        draws = data["draws"]
        shifted = data["y"][draws.ravel()]
    active = shifted >= 0
    lengths = active.sum(axis=1)
    assert np.array_equal(active, np.arange(ce.WIDTH)[None, :] < lengths[:, None])
    assert len(np.unique(draws)) == ce.UPDATES*ce.BATCH and active.sum() == prior["targets"]
    profile = dict(tag=TAG, approval="WIP176", teacher=prior["teacher"], targets=prior["targets"],
                   teacher_batch=CACHE_BATCH, teacher_hidden=1024, max_width=ce.WIDTH,
                   pins={str(p.relative_to(ce.ROOT)): ce.qwen.digest(p) for p in files})
    verify(profile)
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    ce.qwen.write(PROFILE, profile)
    print("P109_CACHE_CPU", len(lengths), int(lengths.sum()), profile["teacher_hidden"], flush=True)


@dataclass
class TeacherCache:
    head: torch.nn.Module
    inputs: torch.Tensor
    masks: torch.Tensor
    features: tuple[torch.Tensor, ...]
    step: int = 0

    @torch.no_grad()
    def logits(self, x, mask, inspect_padding=False):
        assert self.step < len(self.features)
        assert torch.equal(x, self.inputs[self.step]) and torch.equal(mask, self.masks[self.step])
        full = self.head(self.features[self.step])
        self.step += 1
        assigned = full[:, :ce.ASSIGNED].contiguous()
        assert assigned.dtype == torch.bfloat16 and torch.isfinite(assigned).all()
        coverage = None
        if inspect_padding:
            total = full.float() / online.TEMPERATURE
            excluded = (total[:, ce.ASSIGNED:].logsumexp(1) - total.logsumexp(1)).exp()
            coverage = dict(excluded_mass_max=float(excluded.max()), excluded_mass_mean=float(excluded.mean()),
                            first_targets=len(assigned))
        return assigned, coverage


@torch.no_grad()
def build_cache(profile):
    teacher = online.load_teacher(ce.ROOT / profile["teacher"])
    with np.load(ce.DATA, allow_pickle=False) as bundle:
        draw = bundle["draws"]
        x = torch.from_numpy(bundle["x"][draw]).cuda()
        active_np = bundle["y"][draw] >= 0
    mask = torch.from_numpy(active_np).cuda()
    counts = active_np.sum(axis=(1, 2)).tolist()
    flat_x, flat_mask = x.flatten(0,1), mask.flatten(0,1)

    def collect(batch):
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        start = perf_counter()
        retained = torch.empty((profile["targets"],teacher.lm_head.in_features), dtype=torch.bfloat16, device=x.device)
        written = 0
        for offset in range(0,len(flat_x),batch):
            free, total = torch.cuda.mem_get_info()
            if total-free > online.DEVICE_BUDGET or (OUT/"STOP").exists():
                raise RuntimeError("device budget or owned STOP before teacher cache group")
            block = slice(offset,offset+batch)
            h = teacher.model.language_model(input_ids=flat_x[block],use_cache=False).last_hidden_state
            valid = h[flat_mask[block]]
            retained[written:written+len(valid)].copy_(valid)
            written += len(valid)
            del h, valid
        assert written == len(retained)
        torch.cuda.synchronize()
        return retained,dict(batch=batch,width=ce.WIDTH,seconds=perf_counter()-start,
                             peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved())

    candidate, larger = collect(CACHE_BATCH)
    reference, exact = collect(ce.BATCH)
    checked = perf_counter()
    delta = candidate.float()-reference.float()
    relative = float(torch.linalg.vector_norm(delta)/torch.linalg.vector_norm(reference.float()))
    positions = int(candidate.eq(reference).all(1).sum())
    whole = teacher.lm_head(reference[:counts[0]])[:, :ce.ASSIGNED]
    proposed = teacher.lm_head(candidate[:counts[0]])[:, :ce.ASSIGNED]
    first = dict(max_abs=float((whole.float()-proposed.float()).abs().max()),
                 same_top1=int(whole.argmax(1).eq(proposed.argmax(1)).sum()),targets=counts[0])
    larger.update(features_relative_l2=relative,exact_positions=positions,feature_max_abs=float(delta.abs().max()),
                  first_logits=first)
    use_larger = relative<=.01 and larger["seconds"]<exact["seconds"]
    retained, chosen, other = (candidate,larger,exact) if use_larger else (reference,exact,larger)
    audit = dict(**chosen, audit_seconds=other["seconds"]+perf_counter()-checked,
                 bytes=retained.numel()*retained.element_size(), teacher_head_bytes=teacher.lm_head.weight.numel()*2,
                 attended_positions=x.numel(), original_positions=x.numel(), compared_positions=len(retained),
                 selected="batch16_width96" if use_larger else "batch4_width96_exact",
                 candidate_batch16=larger, reference_batch4=exact)
    ce.qwen.write(OUT / "feature_audit.json", audit)
    print("P109_CACHE_FEATURES", audit, flush=True)
    return TeacherCache(teacher.lm_head,x,mask,retained.split(counts,dim=0)), audit


def export_eval(model, profile_sha):
    started = perf_counter()
    model = model.cpu().eval()
    torch.cuda.empty_cache()
    model.freeze_quant()
    payload = ce.export_payload(model, provenance=dict(tag=TAG, profile_sha256=profile_sha,
        training_updates=ce.UPDATES, assigned_rows=ce.ASSIGNED), tile_rows=1024,
        embedding_format="ternary5_existing_twn", head_rows=2048)
    assert len(payload["matrices"])==69 and payload["embedding"]["out_features"]==ce.VOCAB
    storage = ce.payload_storage(payload)
    with EXPORT.open("xb") as stream:
        torch.save(payload,stream)
    frozen = ce.load_payload(payload, device="cuda", tile_rows=4096)
    with np.load(ce.DATA,allow_pickle=False) as bundle:
        x,y,held = [torch.from_numpy(bundle[k]).cuda() for k in ("x","y","held")]
    metrics = ce.evaluate(frozen,x,y,held)
    return dict(packed_held=metrics, packed_payload_storage=storage, packed_bytes=EXPORT.stat().st_size,
                packed_sha256=ce.qwen.digest(EXPORT), packed_seconds=perf_counter()-started)


def run():
    assert ce.idle() and torch.cuda.device_count()==1
    assert torch.cuda.mem_get_info()[0] >= 13_000*2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.set_float32_matmul_precision("highest")
    profile=ce.qwen.load(PROFILE)
    reference, baseline = verify(profile)
    device = OUT / "device_100ms.csv"
    ce.qwen.write(OUT/"active.json",dict(tag=TAG,pid=os.getpid()))
    with device.open("xb") as stream:
        monitor=subprocess.Popen((*ce.DEVICE,f"--loop-ms={ce.INTERVAL_MS}"),stdout=stream)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                cache, audit = build_cache(profile)
                torch.cuda.empty_cache()
                original_initialize = ce.initialize
                student = None

                def capture_student():
                    nonlocal student
                    student = original_initialize()
                    return student

                with (
                    patch.object(online,"OUT",OUT),
                    patch.object(online,"load_teacher",lambda _:cache),
                    patch.object(online,"teacher_logits",TeacherCache.logits),
                    patch.object(ce,"initialize",capture_student),
                ):
                    result=online.train(profile,baseline)
                assert cache.step==ce.UPDATES and student is not None
                del cache
                result.update(export_eval(student,ce.qwen.digest(PROFILE)))
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    verify(profile)
    old = reference["held_by_update"][str(ce.UPDATES)]
    new = result["held_by_update"][str(ce.UPDATES)]
    delta = {lang:new[lang]["nll"]-old[lang]["nll"] for lang in new}
    top = sum(new[lang]["correct"]-old[lang]["correct"] for lang in new)
    old_seconds = sum(v["seconds"] for v in reference["history"])
    student_seconds = sum(v["seconds"] for v in result["history"])
    new_seconds = student_seconds+audit["seconds"]
    packed_delta = {lang:result["packed_held"][lang]["nll"]-baseline["packed_held"][lang]["nll"] for lang in new}
    samples=ce.read_samples(device)
    assert samples
    result.update(cache=audit, nll_vs_online=delta, top1_vs_online=top, packed_nll_vs_ce=packed_delta,
                  quality_kept=max(delta.values())<=.015 and top>=-2,
                  speed_candidate=new_seconds<=old_seconds*.9, online_seconds=old_seconds,
                  cached_compute_seconds=new_seconds, cached_updates_seconds=student_seconds,
                  device_peak=max(samples,key=lambda row:row["occupied_mib"]), device_samples=len(samples),
                  source_preserved=True, profile_sha256=ce.qwen.digest(PROFILE))
    ce.qwen.write(OUT/"report.json",result)
    print("P109_CACHE_RESULT", delta, top, packed_delta, new_seconds, old_seconds, result["device_peak"], flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","run"))
    phase=parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES")==("" if phase=="prepare" else "0")
    assert datetime.now(ce.parent.CUTOFF.tzinfo)+timedelta(seconds=400)<ce.parent.CUTOFF
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    (prepare if phase=="prepare" else run)()
