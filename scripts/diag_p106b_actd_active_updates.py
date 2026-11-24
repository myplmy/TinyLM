"""Apply the verified ACTD recipe with populated optimizer roles on CUDA."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p106b_actd_native_updates as original
from scripts import diag_p013_native_matched_training as training
from scripts import diag_p106b_dskd_native_active_groups as dskd
from scripts.p107_active_optimizer_groups import keep_active_groups


TAG = "p106b_actd_native_updates_synthetic_v2_20261118"
OUT = training.ROOT / "test_result/evidence" / TAG
PROFILE = OUT / "profile.json"


def inputs():
    data = original.verify()
    cpu_sha = original.read_cpu()
    earlier = dskd.verify()
    assert not (original.OUT / "cuda").exists()
    proof = dict(tag=TAG,cpu_profile_sha256=training.digest(original.PROFILE),cpu_report_sha256=cpu_sha,
        fixture_sha256=training.digest(original.FIXTURE),dskd_active_roles_profile=training.digest(dskd.PROFILE),
        roles_removed=earlier["empty_roles_cpu"],original_cpu_reexecuted=False,
        script_sha256=training.digest(Path(__file__)))
    return proof,data


def verify():
    proof,data = inputs()
    assert json.loads(PROFILE.read_bytes()) == proof
    return proof,data


def prepare():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    proof,_ = inputs()
    OUT.mkdir(exist_ok=False)
    training.write(PROFILE,proof)
    print("ACTD_ACTIVE_UPDATE_PREPARED",training.digest(PROFILE),proof["roles_removed"],flush=True)


def worker(arm):
    from tinylm.train import experimental_optimizers as binding

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
    proof,data = verify()
    build = binding.build_experimental_optimizers

    def build_active(*args, **kwargs):
        route = build(*args,**kwargs)
        assert keep_active_groups((route.matrix,route.adamw)) == proof["roles_removed"]
        return route

    device = training.reserve_device()
    with (patch.object(binding,"build_experimental_optimizers",build_active),
          patch.multiple(original,OUT=OUT,PROFILE=PROFILE)):
        original.train_arm(arm,data,"cuda",OUT/arm,device)


def run():
    from scripts.interactive_research_infer import require_idle_gpu

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "0" and time.time()+2*original.CAP+120<training.CUTOFF
    verify()
    statuses,reports = {},{}
    for arm in original.ARMS:
        require_idle_gpu()
        argv = [sys.executable,"-B","-u","-m","scripts.diag_p106b_actd_active_updates","worker",arm]
        try:
            child = subprocess.run(argv,cwd=training.ROOT,timeout=original.CAP).returncode
        except subprocess.TimeoutExpired:
            child = 124
        report = OUT/arm/"report.json"
        statuses[arm] = dict(exit=child,after_process=require_idle_gpu(),
            report_sha256=training.digest(report) if report.is_file() else None)
        if child==0 and report.is_file():
            reports[arm] = json.loads(report.read_bytes())
    verify()
    complete = set(reports)==set(original.ARMS)
    training.write(OUT/"terminal.json",dict(arms=statuses,complete_workers=complete))
    if not complete:
        return 8
    original.compare(reports)
    training.write(OUT/"report.json",dict(complete=True,profile_sha256=training.digest(PROFILE),arms=reports))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","check","run","worker"))
    parser.add_argument("arm",nargs="?",choices=original.ARMS)
    args = parser.parse_args()
    if (args.phase=="worker") != (args.arm is not None):
        parser.error("only workers receive an arm")
    if args.phase=="prepare":
        prepare()
    elif args.phase=="check":
        verify()
        print("ACTD_ACTIVE_UPDATE_CHECK",training.digest(PROFILE),flush=True)
    elif args.phase=="worker":
        worker(args.arm)
    else:
        raise SystemExit(run())


if __name__=="__main__":
    main()
