"""User-run P093B calibration gates. --check-only never loads a checkpoint/GPU."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PARENT = ROOT / "runs/ckpt/m100s12_ko-en_300M_d16_cla2_norecur_rms4.pt"
POOL = ROOT / "data_cache/ko-en_600000000/train.bin"
MODES = ("contract", "calibrate_a", "calibrate_b", "readback", "factor")
SCHEMA = "P093B_NATIVE_FUNCTION_CAL_V1"
CODE = ("scripts/diag_p093b_native_repair.py", "scripts/p093b_native_repair.py",
        "scripts/test_p093b_native_repair.py", "tinylm/model/modules.py",
        "tinylm/model/ternary.py", "tinylm/infer/generate.py")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""): h.update(block)
    return h.hexdigest().upper()


def regular(path):
    return path.is_file() and not any(p.is_symlink() for p in (path, *path.parents))


def directory(tag, mode):
    if not re.fullmatch(r"[a-z0-9_]+", tag): raise ValueError("safe diagnostic tag required")
    path = ROOT / "test_result/evidence" / tag / mode
    if any(p.is_symlink() for p in (path, *path.parents)): raise ValueError("linked evidence path")
    return path


def write(path, report):
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
    if len(text.encode()) > 20_000_000: raise ValueError("report exceeds 20MB")
    with path.open("x", encoding="utf-8") as f: f.write(text)


def evidence_base(args):
    if args.ckpt.resolve() != PARENT.resolve() or args.data.resolve() != POOL.resolve():
        raise ValueError("P093B pins the prior P093 parent and source; use a new plan for replacement")
    if (args.arch != "dense" or args.samples != 512 or args.steps not in (20, 250)
            or not 1 <= args.max_wall_sec <= 3600):
        raise ValueError("preregistered dense geometry/samples/calibration steps differ")
    ranks = tuple(int(v) for v in args.ranks.split(","))
    if ranks != (8, 16): raise ValueError("preregistered rank pair is 8,16")
    return {"schema": SCHEMA, "mode": args.mode, "parent": str(PARENT.relative_to(ROOT)),
        "source": str(POOL.relative_to(ROOT)), "samples": args.samples,
        "steps": args.steps, "ranks": list(ranks), "seed": args.seed,
        "code_sha256": {p: digest(ROOT/p) for p in CODE}, "model_loading": "NOT_RUN",
        "full_training": "NOT_RUN", "model_quality": "NOT_ESTABLISHED",
        "max_wall_sec": args.max_wall_sec}


def input_windows(path, vocab, seed):
    import numpy as np
    if not regular(path) or path.stat().st_size % 2: raise FileNotFoundError("uint16 source absent/linked")
    pool = np.memmap(path, dtype="<u2", mode="r")
    count = len(pool)//128
    if count < 64: raise ValueError("source cannot supply disjoint windows")
    rng = np.random.default_rng(seed)
    starts = rng.choice(count, size=32, replace=False)*128
    windows = [np.array(pool[int(i):int(i)+128], dtype=np.int64, copy=True) for i in starts]
    if any(w.min()<0 or w.max()>=vocab for w in windows): raise ValueError("source/parent vocabulary mismatch")
    h = hashlib.sha256()
    for w in windows: h.update(w.astype("<u2").tobytes())
    return windows[:24], windows[24:], {"offsets": [int(i) for i in starts],
        "source_hash_scope": "selected32_disjoint_uint16_windows_only",
        "source_selected_sha256": h.hexdigest().upper(), "capture_seq": 128}


def capture(model, ids, windows, samples, device):
    import torch
    x, y = [[] for _ in ids], [[] for _ in ids]
    handles = []
    def hook(slot):
        def collect(_module, args, output):
            have = sum(t.shape[0] for t in x[slot]); take = max(0, samples-have)
            if take:
                x[slot].append(args[0].detach().reshape(-1, args[0].shape[-1])[:take].clone())
                y[slot].append(output.detach().reshape(-1, output.shape[-1])[:take].clone())
        return collect
    try:
        for slot, i in enumerate(ids): handles.append(model.layers[i].mlp[0].register_forward_hook(hook(slot)))
        with torch.no_grad():
            for window in windows:
                model(torch.tensor(window[None], dtype=torch.long, device=device), logits_last_only=True)
                if all(sum(t.shape[0] for t in lane)>=samples for lane in x): break
    finally:
        for handle in handles: handle.remove()
    if any(sum(t.shape[0] for t in lane)!=samples for lane in x): raise ValueError("empty/short actual activation capture")
    return [torch.cat(lane) for lane in x], [torch.cat(lane) for lane in y]


def tensor_sha(values):
    h = hashlib.sha256()
    for tensor in values: h.update(tensor.detach().float().cpu().contiguous().numpy().tobytes())
    return h.hexdigest().upper()


def ce_probe(model, windows, device):
    import torch
    import torch.nn.functional as F
    values = []
    with torch.no_grad():
        for window in windows:
            t = torch.tensor(window[None], dtype=torch.long, device=device)
            logits = model(t[:, :-1])
            if logits.ndim!=3 or logits.shape[:2]!=t[:,1:].shape:
                raise ValueError("native forward logits/target shape differs")
            values.append(float(F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), t[:, 1:].reshape(-1))))
    if not values or not all(math.isfinite(v) for v in values): raise ValueError("CE empty/nonfinite")
    return {"window_ce": values, "mean_ce": sum(values)/len(values), "prediction_tokens": len(values)*127,
            "truth_scope": "same source function probe, not unseen knowledge"}


def save_candidate(path, stem, shared, adapters, info):
    import torch
    from scripts.p093b_native_repair import PROJECTIONS, GSQProjection
    files = []
    for slot, name in enumerate(PROJECTIONS):
        projection = getattr(shared, name)
        q = projection.matrix().detach() if isinstance(projection, GSQProjection) else projection._wq.detach()
        packet = {"shared_master": projection.weight.detach().cpu() if hasattr(projection, "weight") else q.cpu(),
                  "shared_native": q.cpu(), "adapters": []}
        if adapters is not None:
            for layer in adapters:
                a = layer[slot]
                if hasattr(a, "native_export"): a = a.native_export()
                packet["adapters"].append({"D": a.D.detach().cpu(), "U": a.U.detach().cpu(), "bits": a.bits})
        # Both master/native copies are retained for audit. Split by projection.
        nbytes = sum(v.numel()*v.element_size() for v in packet.values() if torch.is_tensor(v))
        nbytes += sum(v.numel()*v.element_size() for row in packet["adapters"] for v in row.values() if torch.is_tensor(v))
        if nbytes > 18_000_000: raise ValueError("projection packet needs another split before serialization")
        target = path/f"{stem}_{name}.pt"
        with target.open("xb") as f: torch.save(packet, f)
        if target.stat().st_size > 20_000_000: raise ValueError("serialized projection exceeds20MB; preserve for inspection")
        files.append({"path": target.name, "bytes": target.stat().st_size, "sha256": digest(target)})
    manifest = {"schema": "P093B_DIAGNOSTIC_PATCH_SHARDS_V1", "input": info, "files": files,
                "scope": "diagnostic partial patch, not a complete deployable checkpoint"}
    write(path/f"{stem}_manifest.json", manifest)
    return manifest


def load_adapters(path, stem, shared, cfg, info):
    import copy
    import torch
    from tinylm.model.ternary import LoRA
    from scripts.p093b_native_repair import PROJECTIONS
    manifest = json.loads((path/f"{stem}_manifest.json").read_text(encoding="utf-8"))
    for key in ("parent_sha256", "source_selected_sha256", "code_sha256"):
        if manifest["input"].get(key) != info.get(key): raise ValueError("prior patch input/code differs")
    layers = [[] for _ in range(4)]
    for name, record in zip(PROJECTIONS, manifest["files"]):
        f = path/record["path"]
        if f.parent != path or not regular(f) or digest(f)!=record["sha256"]: raise ValueError("patch shard unsafe/stale")
        p = torch.load(f, map_location=shared.gate_proj.weight.device, weights_only=True)
        for i, payload in enumerate(p["adapters"]):
            local = copy.deepcopy(cfg); local.mlp_lora_bits=payload["bits"]
            a = LoRA(local, payload["D"].shape[1], payload["U"].shape[0], payload["D"].shape[0]).to(payload["D"].device)
            with torch.no_grad(): a.D.copy_(payload["D"]); a.U.copy_(payload["U"])
            layers[i].append(a)
    return [tuple(layer) for layer in layers]


def viable(candidate, baseline):
    return baseline>1e-12 and candidate<=.90 and 1-candidate/baseline>=.10


def execute_calibration(args, info, output):
    import torch
    from tinylm.infer.generate import load_model
    from scripts import p093b_native_repair as core
    from scripts.p106b_gate_runtime import idle_before_gpu
    if args.device != "cuda": raise ValueError("real gate preregisters CUDA; CPU only for fixtures")
    if not regular(PARENT) or not regular(POOL): raise FileNotFoundError("pinned parent/source absent or linked")
    if args.mode == "factor":
        previous = directory(args.tag,"calibrate_a")
        prior = json.loads((previous/"report.json").read_text(encoding="utf-8"))
        rank16 = next((r for r in prior.get("candidates",[]) if r.get("rank")==16),None)
        if (prior.get("status")!="CALIBRATION_COMPLETE" or rank16 is None or not rank16.get("local_viable")):
            return {"schema":SCHEMA,"input":info,"status":"PREREQUISITE_HOLD","reason":"rank16_A_viability_missing","model_loading":"NOT_RUN"},8
        if prior["input"].get("code_sha256")!=info["code_sha256"]:
            raise ValueError("A code fingerprint stale before factor model loading")
    idle_before_gpu(); torch.manual_seed(args.seed)
    deadline = time.monotonic()+args.max_wall_sec
    with torch.no_grad(): model, cfg, device = load_model("dense", str(PARENT), "cuda")
    if cfg.n_layers!=16 or cfg.tie_mlp or cfg.cla_group!=2 or cfg.n_modes!=1:
        raise ValueError("pinned parent geometry differs")
    ids = list(range(cfg.n_prelude, cfg.n_prelude+4)); mlps = [model.layers[i].mlp[0] for i in ids]
    if any(getattr(model.layers[i], f, False) for i in ids for f in ("has_lora", "has_film", "has_lrm")):
        raise ValueError("parent already has extra correction axes")
    for p in model.parameters(): p.requires_grad_(False)
    train_windows, val_windows, source = input_windows(POOL, cfg.vocab_size, args.seed)
    info.update(source, parent_sha256=digest(PARENT), group_layers=ids)
    x, y = capture(model, ids, train_windows, args.samples, device)
    vx, vy = capture(model, ids, val_windows, max(128, args.samples//4), device)
    info.update(calibration_x_sha256=tensor_sha(x), heldout_x_sha256=tensor_sha(vx),
        calibration_input_rows=sum(t.shape[0] for t in x), heldout_input_rows=sum(t.shape[0] for t in vx),
        model_loading="MEASURED", data_access="SELECTED_WINDOWS_MEASURED")
    shared = core.shared_native(mlps, cfg)
    baseline = core.measure(shared, vx, vy); report = {"schema": SCHEMA, "input": info,
        "shared_only": baseline, "parent_ce": ce_probe(model, val_windows, device), "candidates": []}
    torch.cuda.reset_peak_memory_stats()
    if args.mode == "calibrate_a":
        for rank in (8,16):
            before = time.perf_counter(); adapters = core.residual_adapters(mlps, shared, x, rank, cfg)
            init_sec = time.perf_counter()-before; init = core.measure(shared, vx, vy, adapters)
            fitted = core.fit(shared, x, y, adapters=adapters, steps=args.steps, deadline=deadline)
            after = core.measure(shared, vx, vy, adapters)
            with core.patched_group(model, ids, shared, adapters): ce=ce_probe(model, val_windows, device)
            manifest = save_candidate(output, f"rank{rank}", shared, adapters, info)
            report["candidates"].append({"rank": rank, "init_sec": init_sec, "init": init,
                "fit": fitted, "heldout": after, "ce": ce, "artifact": manifest,
                "local_viable": viable(after["nrms"], baseline["nrms"])})
    elif args.mode == "calibrate_b":
        candidate = core.gsq_shared(shared, cfg)
        init = core.measure(candidate, vx, vy)
        if abs(init["nrms"]-baseline["nrms"])>1e-5: raise ValueError("GSQ hard initialization differs from shared native")
        fitted = core.fit(candidate, x, y, steps=args.steps, strategy="lion", deadline=deadline)
        after = core.measure(candidate, vx, vy)
        with core.patched_group(model, ids, candidate): ce=ce_probe(model, val_windows, device)
        report["candidates"].append({"init": init, "fit": fitted, "heldout": after, "ce": ce,
            "artifact": save_candidate(output,"gsq_shared",candidate,None,info),
            "local_viable": viable(after["nrms"],baseline["nrms"])})
    else:
        previous = directory(args.tag,"calibrate_a")
        prior = json.loads((previous/"report.json").read_text(encoding="utf-8"))
        rank16 = next(r for r in prior["candidates"] if r["rank"]==16)
        floating = load_adapters(previous,"rank16",shared,cfg,info)
        quantized = [tuple(core.GSQAdapter(a) for a in layer) for layer in floating]
        init = core.measure(shared,vx,vy,quantized)
        fitted = core.fit(shared,x,y,adapters=quantized,steps=args.steps,strategy="lion",deadline=deadline)
        after = core.measure(shared,vx,vy,quantized)
        native = [tuple(a.native_export() for a in layer) for layer in quantized]
        restored = core.measure(shared,vx,vy,native)
        with torch.no_grad():
            qp=core.local_predictions(shared,vx,quantized); np=core.local_predictions(shared,vx,native)
            gap=max(float((a-b).abs().max()) for a,b in zip(qp,np))
        if gap>1e-5: raise ValueError("native factor round-trip exceeds preregistered absolute tolerance")
        with core.patched_group(model,ids,shared,native): ce=ce_probe(model,val_windows,device)
        report["candidates"].append({"rank":16,"float_heldout":rank16["heldout"],"init":init,
            "fit":fitted,"heldout":after,"native_restored":restored,"max_abs_roundtrip":gap,"ce":ce,
            "artifact":save_candidate(output,"factor_native",shared,native,info),
            "local_viable":viable(restored["nrms"],baseline["nrms"])})
    report.update(status="CALIBRATION_COMPLETE",local_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        local_peak_reserved_bytes=torch.cuda.max_memory_reserved(),quality="NOT_ESTABLISHED",
        memory_scope="diagnostic retains parent; not deployed graph/RSS savings")
    for candidate in report["candidates"]:
        print("[ACTUAL_FUNCTION_RESULT] "+json.dumps({"mode":args.mode,"rank":candidate.get("rank"),
            "shared_nrms":baseline["nrms"],"candidate_nrms":candidate["heldout"]["nrms"],
            "local_viable":candidate["local_viable"],"candidate_ce":candidate["ce"]["mean_ce"],
            "calibration_wall_sec":candidate["fit"]["wall_sec"],"quality":"NOT_ESTABLISHED"}),flush=True)
    return report,0 if any(r["local_viable"] for r in report["candidates"]) else 8


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=MODES,required=True); p.add_argument("--execute",action="store_true")
    p.add_argument("--check-only",action="store_true"); p.add_argument("--ckpt",type=Path,default=PARENT)
    p.add_argument("--data",type=Path,default=POOL); p.add_argument("--arch",default="dense",choices=("dense",))
    p.add_argument("--device",default="cuda",choices=("cpu","cuda")); p.add_argument("--ranks",default="8,16")
    p.add_argument("--samples",type=int,default=512); p.add_argument("--steps",type=int,default=250)
    p.add_argument("--seed",type=int,default=1337); p.add_argument("--tag",default="p093b_function_v1_s1337")
    p.add_argument("--max-wall-sec",type=int,default=3600)
    a=p.parse_args(); info=evidence_base(a); out=directory(a.tag,a.mode)
    if a.check_only or not a.execute:
        print("[PREFLIGHT] "+json.dumps(info,ensure_ascii=False)); print("[NOT_RUN] explicit --execute required; no checkpoint/cache/GPU read"); return 0
    if out.exists(): print("[PREREQUISITE_HOLD] preserve existing output; use new stage/tag"); return 8
    out.mkdir(parents=True)
    print("[PHASE] regression/preconditions then "+a.mode+"; only technical/scientific local disposition follows",flush=True)
    try:
        if a.mode=="contract":
            r=subprocess.run([sys.executable,"-B","-X","utf8","scripts/test_p093b_native_repair.py"],cwd=ROOT,timeout=600)
            if r.returncode: raise ValueError("CPU native fixture regression failed")
            report={"schema":SCHEMA,"input":info,"status":"CPU_CONTRACT_PASS","model_loading":"NOT_RUN"}; rc=0
        elif a.mode=="readback":
            rows=[json.loads((directory(a.tag,m)/"report.json").read_text(encoding="utf-8")) for m in ("calibrate_a","calibrate_b")]
            for key in ("parent_sha256","source_selected_sha256","calibration_x_sha256","heldout_x_sha256","code_sha256"):
                if rows[0]["input"].get(key)!=rows[1]["input"].get(key): raise ValueError("independent A/B inputs differ: "+key)
            report={"schema":SCHEMA,"input":info,"status":"PAIR_READBACK_COMPLETE","arms":rows,"quality":"NOT_ESTABLISHED"}; rc=0
        else:
            contract=json.loads((directory(a.tag,"contract")/"report.json").read_text(encoding="utf-8"))
            if contract.get("status")!="CPU_CONTRACT_PASS" or contract["input"]["code_sha256"]!=info["code_sha256"]:
                raise ValueError("CPU contract absent/stale")
            report,rc=execute_calibration(a,info,out)
    except (FileNotFoundError,StopIteration) as e:
        report={"schema":SCHEMA,"input":info,"status":"PREREQUISITE_HOLD","reason":str(e)}; rc=8
    except KeyboardInterrupt:
        report={"schema":SCHEMA,"input":info,"status":"INTERRUPTED"}; rc=130
    except Exception as e:
        report={"schema":SCHEMA,"input":info,"status":"TOOL_FAILURE","error_type":type(e).__name__,"reason":str(e)}; rc=9
    write(out/"report.json",report)
    print("[EXPERIMENT_FINAL] "+json.dumps({"mode":a.mode,"status":report["status"],"exit_code":rc,
        "output":str(out.relative_to(ROOT)),"quality":"NOT_ESTABLISHED"},ensure_ascii=False))
    return rc


if __name__=="__main__": raise SystemExit(main())
