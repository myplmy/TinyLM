"""Retry the two previously unstarted DSKD arms with populated optimizer roles."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p106b_dskd_native_batch_cuda as previous
from scripts import diag_p013_native_matched_training as training
from scripts.p107_active_optimizer_groups import keep_active_groups


TAG = "p106b_dskd_native_batch_cuda_synthetic_v3_20261118"
OUT = training.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"
SOURCES = (Path(__file__),training.ROOT / "scripts/p107_active_optimizer_groups.py")
PREVIOUS_RAW = training.ROOT / "test_result/101_log_20261118_P106B_Stage8fgFc_dskd_native_GPU.txt"
ORIGINAL = {name:getattr(previous,name) for name in ("OUT","TAG","PROFILE","DATA","verify")}


def read(path):
    return json.loads(path.read_bytes())


def frozen():
    with patch.multiple(previous,**ORIGINAL):
        profile = ORIGINAL["verify"]()
    original = ORIGINAL["OUT"]
    terminal = read(original / "actual.json")
    assert set(terminal["arms"]) == set(previous.ARMS) and not terminal["complete"]
    assert all(x["exit"]==1 and not x["report"] for x in terminal["arms"].values())
    assert all(not any((original / arm).glob("update_*.json")) for arm in previous.ARMS)
    raw = PREVIOUS_RAW.read_text()
    assert raw.count("ValueError: scaled group empty optimizer group") == 2
    assert [line.split()[2] for line in raw.splitlines() if line.startswith("[runlog] 종료코드 ")] == ["8"]
    result = dict(tag=TAG,original_profile=training.digest(ORIGINAL["PROFILE"]),original_raw=training.digest(PREVIOUS_RAW),
        original_terminal=training.digest(original / "actual.json"),old_optimizer_updates=0,
        sources={str(file.relative_to(training.ROOT)):training.digest(file) for file in SOURCES},
        fixture_sha256=profile["fixture_sha256"],features=profile["features"],
        declared_synthetic_identities=profile["declared_synthetic_identities"])
    return result


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    manifest = frozen()
    import torch
    from tinylm.config import build_config
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm.train.experimental_optimizers import build_experimental_optimizers

    torch.set_num_threads(1)
    torch.manual_seed(1337)
    cfg = build_config("m100s10","dense",previous.WIDTH,True)
    model = TiedMLPTransformer(cfg).train()
    route = build_experimental_optimizers(model,"muon_matched",lr=6e-4,matrix_lr_mult=1.)
    optimizers = (route.matrix,route.adamw)
    owned = [p for opt in optimizers for group in opt.param_groups for p in group["params"]]
    removed = keep_active_groups(optimizers)
    assert sum(removed)>0 and {id(p) for p in owned}=={id(p) for p in model.parameters() if p.requires_grad}
    assert owned == [p for opt in optimizers for group in opt.param_groups for p in group["params"]]
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    destination = OUT / "features"
    destination.mkdir(exist_ok=False)
    files = {previous.DATA:OUT / "fixture.json"}
    files.update({previous.OUT / "features" / name:destination / name for name in manifest["features"]})
    for old,new in files.items():
        with new.open("xb") as handle:
            handle.write(old.read_bytes())
    training.write(PROFILE,dict(**manifest,empty_roles_cpu=removed,parameters_checked=len(owned)))
    verify()
    print("DSKD_ACTIVE_ROLES_PREPARED",training.digest(PROFILE),removed,len(owned),flush=True)


def verify():
    profile = read(PROFILE)
    assert {key:value for key,value in profile.items() if key not in ("empty_roles_cpu","parameters_checked")} == frozen()
    assert training.digest(OUT / "fixture.json") == profile["fixture_sha256"]
    assert all(training.digest(OUT / "features" / name)==sha for name,sha in profile["features"].items())
    return profile


def worker(arm):
    profile = verify()
    from tinylm.train import experimental_optimizers as binding

    build = binding.build_experimental_optimizers
    def build_active(*args, **kwargs):
        route = build(*args,**kwargs)
        removed = keep_active_groups((route.matrix,route.adamw))
        assert removed == profile["empty_roles_cpu"]
        print("DSKD_ACTIVE_ROLES",arm,removed,flush=True)
        return route

    with (patch.object(binding,"build_experimental_optimizers",build_active),
          patch.multiple(previous,OUT=OUT,TAG=TAG,PROFILE=PROFILE,DATA=OUT / "fixture.json",verify=verify)):
        previous.worker(arm)


def run():
    from scripts.interactive_research_infer import require_idle_gpu

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0" and time.time()+1920<training.CUTOFF
    verify()
    results = {}
    for arm in previous.ARMS:
        require_idle_gpu()
        argv = [sys.executable,"-B","-u","-m","scripts.diag_p106b_dskd_native_active_groups","worker",arm]
        try:
            code = subprocess.run(argv,cwd=training.ROOT,timeout=900).returncode
        except subprocess.TimeoutExpired:
            code = 124
        results[arm] = dict(exit=code,report=(OUT/arm/"report.json").is_file(),after_exit=require_idle_gpu())
    complete = all(item["exit"]==0 and item["report"] for item in results.values())
    verify()
    training.write(OUT / "actual.json",dict(tag=TAG,complete=complete,arms=results,
        ended_UTC=datetime.now(timezone.utc).isoformat()))
    return 0 if complete else 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","check","run","worker"))
    parser.add_argument("arm",nargs="?",choices=previous.ARMS)
    args = parser.parse_args()
    if (args.stage=="worker") != (args.arm is not None):
        parser.error("only workers receive an arm")
    if args.stage=="prepare":
        prepare()
    elif args.stage=="check":
        verify()
        print("DSKD_ACTIVE_ROLES_CHECK",training.digest(PROFILE),flush=True)
    elif args.stage=="worker":
        worker(args.arm)
    else:
        raise SystemExit(run())


if __name__=="__main__":
    main()
