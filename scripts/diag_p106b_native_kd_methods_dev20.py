"""Reproduce four short native KD states and compare them on independent development inputs."""

import argparse
from datetime import datetime, timedelta
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import numpy as np
from tokenizers import Tokenizer
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p106b_actd_real_cache_updates as actd
from scripts import diag_p106b_dskdv2_real_cache_updates as dskd
from scripts import diag_p106b_dwa_real_cache_updates as dwa
from scripts import diag_p106b_gsq_actd_memory_phases as lineage
from scripts import p106b_final_holdout as response
from scripts.diag_p106b_gsq_scaled_actd_deploy import read, write
from scripts.diag_p106b_gsq_actual_actd_start import sampling
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from scripts.p106b_weight_route import weight_route


ROOT, manual = actd.ROOT, actd.manual
SHA = manual.file_sha
TAG = "p106b_native_kd_methods_dev20_v1_20261119"
OUT = actd.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
CASE = ("ce", "actd", "dskd", "dwa")
LIMIT = 240
END = datetime.fromisoformat("2026-11-20T16:58:00+09:00")
DEV = ROOT / "data_cache/p106b_final200_v2_20261101/dev.json"
DEV_MANIFEST = DEV.with_name("manifest.json")
HELD = ROOT / "test_result/evidence/p106b_p109_actual_prefix_kd_v1_20261119/profile.json"


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(END.tzinfo) + timedelta(seconds=reserve) >= END:
        raise RuntimeError("owned STOP or deadline")


def guard_card():
    gate()
    free, total = torch.cuda.mem_get_info()
    if total - free > 13_000_000_000:
        raise RuntimeError("card occupancy exceeded 13 GB")


def current_archived_pins(pins):
    result = dict(pins)
    key = lineage.TRANSFORMER
    assert result[key] == lineage.OLD_TRANSFORMER
    result[key] = lineage.CURRENT_TRANSFORMER
    assert all(SHA(ROOT / name) == expected for name, expected in result.items())
    return result


def source_inputs(name):
    with patch.object(actd, "verify_selected_checkpoint", lineage.verify_cache_lineage):
        if name == "dskd":
            return dskd.collect()
        if name in ("ce", "actd"):
            return actd.inputs()
        profile = read(dwa.PROFILE)
        current_archived_pins(profile["sources"])
        lineage.verify_cache_lineage(profile["student"])
        packed = read(actd.SOURCE / "profile.json")
        rows = list(actd.read_shards(actd.SOURCE, packed["prepared_manifest"]))
        ordered_ids = read(dwa.PAST / "profile.json")["row_ids"]
        assert [row["row_id"] for row in rows] == ordered_ids and len(rows) == 128
        descriptors = {r["row_id"]: r for r in read(dskd.RECOVERY / "features_manifest.json")["features"]}
        groups = []
        for row in rows:
            desc = descriptors[row["row_id"]]
            path = ROOT / desc["path"]
            assert path == dskd.FEATURES / (row["row_id"] + ".npy") and not path.is_symlink()
            assert desc["sha256"] == profile["sources"][str(path.relative_to(ROOT))]
            features = np.load(path, allow_pickle=False, mmap_mode="r")
            teacher = row["teacher"]
            dskd.feature_contract(features, tokens=len(teacher["ids"])-1)
            assert list(features.shape) == desc["shape"]
            native = row["packed"]["student"]
            assert all((target == token) if keep else (target == -100)
                       for target, keep, token in zip(native["labels"], native["supervised"], native["ids"], strict=True))
            groups.append((native, teacher, features))
        groups = [groups[i:i+32] for i in range(0, len(groups), 32)]
        counts = [dict(student=sum(sum(s["supervised"][1:]) for s, _, _ in g),
                       teacher=sum(sum(t["supervised"][1:]) for _, t, _ in g)) for g in groups]
        assert counts == profile["counts"]
        return profile, groups


def held_inputs(tokenizer):
    manifest = read(DEV_MANIFEST)
    dev = read(DEV)
    docs = [item for item in read(HELD)["data"]["documents"] if item["split"] == "held"]
    assert manifest["dev_file"] == str(DEV.relative_to(ROOT)) and manifest["max_new"] == response.MAX_NEW
    assert manifest["contract"]["dev_sha256"] == response.digest(dev) and len(dev) == 20
    assert manifest["tokenizer_sha256"] == SHA(ROOT / manual.TOKENIZER)
    assert all(row["split"] == "dev" for row in dev) and len({row["id"] for row in dev}) == 20
    assert len(docs) == len({item["id"] for item in docs}) == 48
    assert all(sum(item["language"] == lang for item in docs) == 24 for lang in ("ko", "en"))
    encoded = [tokenizer.encode(item["text"], add_special_tokens=False).ids for item in docs]
    assert all(2 <= len(row) <= 1024 for row in encoded)
    return dev, docs, encoded


def verify(profile):
    assert profile["tag"] == TAG and profile["approval"] == 177
    assert all(SHA(ROOT / name) == expected for name, expected in profile["pins"].items())


def prepare():
    ar, dr, wr = [read(module.OUT / "report.json") for module in (actd, dskd, dwa)]
    assert all(row["source_preserved"] and row["checkpoint_writes"] == 0 for row in (ar, dr, wr))
    assert all(row["profile_sha256"] == SHA(module.OUT / "profile.json")
               for row, module in zip((ar, dr, wr), (actd, dskd, dwa), strict=True))
    assert ar["arms"]["ce"]["final"] == dr["arms"]["ce"]["final"]
    refs = dict(ce=ar["arms"]["ce"], actd=ar["arms"]["ce_actd"], dskd=dr["arms"]["dskd"], dwa=wr)
    assert len({row["initial"] for row in refs.values()}) == 1 and all(row["optimizer_steps"] == [4] for row in refs.values())
    assert len({row["final"] for row in refs.values()}) == 4
    tokenizer = Tokenizer.from_file(str(ROOT / manual.TOKENIZER))
    dev, docs, encoded = held_inputs(tokenizer)
    pins = {}
    for module,key in ((actd,"sources"),(dskd,"source_pins"),(dwa,"sources")):
        raw = read(module.OUT / "profile.json")
        pins.update(current_archived_pins(raw.get("inputs", raw)[key]))
    _, train_groups = source_inputs("ce")
    train_text = [tokenizer.decode(ids, skip_special_tokens=False).strip() for group in train_groups for ids, _, _, _ in group]
    assert all(row["prompt"].strip() not in sample for row in dev for sample in train_text)
    assert all(row["text"].strip() not in sample for row in docs for sample in train_text)
    OUT.mkdir()
    sealed = OUT / "plan_at_execution.md"
    header = "### Stage8kdQ — "
    _, plan = actd.PLAN.read_text(encoding="utf8").split(header, 1)
    assert TAG in plan
    sealed.write_text(header + plan, encoding="utf8")
    files = (Path(__file__).resolve(), Path(lineage.__file__), Path(response.__file__), DEV, DEV_MANIFEST, HELD, sealed,
             *(m.OUT / k for m in (actd, dskd, dwa) for k in ("profile.json", "report.json")))
    pins.update({str(path.relative_to(ROOT)): SHA(path) for path in files})
    profile = dict(tag=TAG, approval=177, pins=pins, arms={key: value["final"] for key, value in refs.items()},
                   authored_targets={lang: sum(len(ids)-1 for doc, ids in zip(docs, encoded, strict=True)
                                              if doc["language"] == lang) for lang in ("ko", "en")},
                   dev_rows=len(dev), held_rows=len(docs), early_eval_policy="DEV20_AND_AUTHORED48_ONLY")
    verify(profile)
    write(PROFILE, profile)
    print("KD_DEV20_PREPARED", profile["authored_targets"], len(train_text), len(pins), flush=True)


@torch.no_grad()
def authored_scores(model, docs, encoded):
    result = {lang: dict(targets=0, nll_sum=0., correct=0) for lang in ("ko", "en")}
    with sdpa_kernel(SDPBackend.MATH):
        for doc, ids in zip(docs, encoded, strict=True):
            guard_card()
            sequence = torch.tensor(ids, dtype=torch.long, device="cuda")
            output = model(sequence[:-1].unsqueeze(0))[0].float()
            target = sequence[1:]
            row = result[doc["language"]]
            row["targets"] += len(target)
            row["nll_sum"] += float(F.cross_entropy(output, target, reduction="sum"))
            row["correct"] += int(output.argmax(-1).eq(target).sum())
    return {lang: dict(row, nll=row["nll_sum"]/row["targets"]) for lang, row in result.items()}


def compare_answer(model, expected, profile, directory):
    tokenizer = Tokenizer.from_file(str(ROOT / manual.TOKENIZER))
    dev, docs, encoded = held_inputs(tokenizer)
    with weight_route(model, "ternary") as route:
        model.clear_quant()
        model.eval()
        model.set_anneal(1.)
        with torch.no_grad():
            model.freeze_quant()
        before = manual.state_fingerprint(model)
        assert before == expected
        scores = authored_scores(model, docs, encoded)
        assert {k:v["targets"] for k,v in scores.items()} == profile["authored_targets"]
        active = dict(torch=torch, model=model, cfg=model.cfg, tokenizer=tokenizer, route=route, root=str(ROOT))
        answers = []
        with (directory / "answers.jsonl").open("x", encoding="utf8") as output:
            for case in dev:
                guard_card()
                answer, meta = manual.emit(active, case["prompt"], max_new=response.MAX_NEW)
                row = dict(id=case["id"], answer=answer, metadata=meta,
                           reference_match=response.reference_match(answer,case),
                           signals=response.review_signals(answer,meta,case))
                answers.append(row)
                print(json.dumps(row,ensure_ascii=False,allow_nan=False),file=output,flush=True)
        assert manual.state_fingerprint(model) == before
        model.clear_quant()
    return dict(authored=scores, dev_rows=len(answers), exact_reference_matches=sum(row["reference_match"] is True for row in answers))


def worker(name, profile):
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12500 * 2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    condition, groups = source_inputs(name)
    directory = OUT / name
    directory.mkdir()
    retained = []
    load = actd.load_student

    def retain(entry):
        model = load(entry)
        retained.append(model)
        return model

    with (patch.object(actd, "load_student", retain), patch.object(actd, "authority", gate),
          patch.object(dskd, "gate", gate), patch.object(dwa, "gate", gate)):
        watch = perf_counter()
        if name == "dwa":
            training = dwa.train(condition, groups)
        elif name == "dskd":
            training = dskd.train("dskd", condition, groups)
        else:
            training = actd.train_arm(condition, groups, enable_actd=name == "actd")
        training_wall = perf_counter() - watch
    del groups
    expected = profile["arms"][name]
    write(directory / "training.json", dict(result=training, expected_final=expected, elapsed=training_wall))
    assert len(retained) == 1 and training["optimizer_steps"] == [4] and training["final"] == expected
    gc.collect()
    torch.cuda.empty_cache()
    model = retained.pop()
    evaluation = compare_answer(model, expected, profile, directory)
    del model
    gc.collect()
    close_owned_cuda(torch, evaluation)
    write(directory / "evaluation.json", evaluation)
    print("KD_DEV20_ARM",name,"training_wall",training_wall,evaluation["authored"],evaluation["dev_rows"],flush=True)


def run(profile):
    assert idle(), "GPU has another compute process"
    samples = OUT / "device_100ms.csv"
    exits = {}
    with samples.open("xb") as stream:
        monitor = subprocess.Popen((*sampling.DEVICE, f"--loop-ms={sampling.INTERVAL_MS}"), stdout=stream)
        try:
            for arm in CASE:
                gate(LIMIT + 5)
                command = ["timeout", "--kill-after=4s", f"{LIMIT}s", sys.executable, "-B", "-m", __spec__.name, "worker", arm]
                env = {**os.environ, "TRITON_CACHE_DIR": str(OUT / "triton_cache")}
                exits[arm] = subprocess.run(command, cwd=ROOT, env=env).returncode
                print("KD_DEV20_EXIT",arm,exits[arm],flush=True)
                if not idle():
                    break
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    verify(profile)
    returned = idle()
    observed = sampling.read_samples(samples)
    report = dict(exits=exits, returned=returned, source_preserved=True,
                  peak=max(observed,key=lambda row:row["occupied_mib"]), samples=len(observed))
    write(OUT / "report.json", report)
    print("KD_DEV20_RELEASE", report, flush=True)
    if exits != dict.fromkeys(CASE,0) or not returned:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "worker", "run"))
    parser.add_argument("name", nargs="?", choices=CASE)
    args = parser.parse_args()
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.phase == "prepare" else "0")
    torch.set_num_threads(2)
    gate(len(CASE)*LIMIT + 15 if args.phase == "run" else 0)
    if args.phase == "prepare":
        prepare()
    else:
        profile = read(PROFILE)
        if args.phase == "run":
            verify(profile)
            run(profile)
        else:
            worker(args.name, profile)


if __name__ == "__main__":
    main()
