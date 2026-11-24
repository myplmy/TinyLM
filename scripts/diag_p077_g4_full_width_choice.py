"""Check the full-width online attention candidate on eight archived long choices."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import torch

from scripts import diag_p077_g4_full_width_prefill as full
from scripts import diag_p077_lowbit_native as previous
from scripts import diag_p077_long_choices as scoring


TAG = "p077_g4_full_width_choice_cpu_v1_20261121"
OUT = previous.RESULT.with_name(TAG)
trial = full.trial
native,base,bounded = full.native,full.base,full.bounded


def prepare():
    fixture = previous.OLD/"fixture.json"
    archived = previous.RESULT/"report.json"
    measured = full.OUT/"report.json"
    old,source,timing = (trial.read_json(path) for path in (archived,fixture,measured))
    if (old["model"]!=timing["plan"]["r5"] or old["model"]!=source["model"]
            or old["previous_fixture_sha256"]!=trial.file_sha(fixture)
            or any(not row["unchanged"] for row in timing["rows"])):
        raise ValueError("the measured engine or official archived choice cohort changed")
    chosen = source["chosen"]
    reference = {(row["task"],row["index"]):row for row in old["rows"] if row["mode"]=="k4v2"}
    if len(chosen)!=8 or set(reference)!={(row["task"],row["index"]) for row in chosen}:
        raise ValueError("the eight archived K4/V2 choice scores are required")
    source_code = (trial.ROOT/base.CPP).read_bytes()
    source_code = scoring.render_forcing(native.render(source_code,2048,3,True,True))
    source_code = native.replace_once(source_code,b"cache(capacity, 1024, 3)",b"cache(capacity, 1920, 4, 2)")
    candidate = full.wide.render(source_code,"online8")
    meta = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),fixture_sha256=trial.file_sha(fixture),
                archived_sha256=trial.file_sha(archived),timing_sha256=trial.file_sha(measured),
                engine_sha256=sha256(candidate).hexdigest().upper(),questions=len(chosen))
    return meta,(old["model"],candidate,chosen,reference)


def run(plan,deadline):
    if (os.environ.get("CUDA_VISIBLE_DEVICES")!="" or OUT.exists()
            or not deadline.tzinfo or deadline>full.wide.request.byte_table.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<360):
        raise ValueError("requires a new CPU run and an adequate authorized window")
    verified,(old,source,chosen,reference) = prepare()
    if verified!=plan:
        raise ValueError("the eight archived choice pairs changed")
    cpus = sorted(set(scoring.CPU_CORES)&os.sched_getaffinity(0))[:4]
    if not cpus:
        raise ValueError("the known CPU cores are unavailable")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    with patch.object(bounded,"OUT",OUT):
        binary = bounded.build(source,caps=(64,))[64][0]
    with ExitStack() as stack:
        r4,r5 = [base.memfile(f"p077-full-choice-{key}") for key in ("r4","r5")]
        for fd in (r4,r5):
            stack.callback(os.close,fd)
        profile = base.READ(bounded.text.OUT/"profile.json")["pins"]["candidate"]
        weights = base.prior.load_candidate(profile)
        base.model_blob(weights,r4,profile["model_tensor_bytes"])
        manifest = native.extend_positions(r4,r5,weights)
        del weights
        if manifest!=old:
            raise ValueError("the R5 deployment weights changed")

        def run_lane(cpu,entries):
            result = []
            for row in entries:
                answer = scoring.compare(row,binary,r5,cpu,OUT,"far",resources=True)
                if any(item["kv_bytes"]!=previous.ARMS["k4v2"][3] for item in answer["choices"]):
                    raise ValueError("the candidate choice cache has the wrong representation")
                original = reference[(row["task"],row["index"])]
                record = dict(task=row["task"],index=row["index"],correct=answer["correct"],
                              baseline_correct=original["correct"],margin=answer["margin"],
                              baseline_margin=original["margin"],choices=answer["choices"],
                              greedy_same=[a["greedy"]==b["greedy"] for a,b in zip(answer["choices"],original["choices"],strict=True)])
                result.append(record)
                trial.publish(OUT/f"{row['task']}-{row['index']}.json",record)
                print(json.dumps({key:record[key] for key in ("task","index","correct","margin","baseline_margin")}),flush=True)
            return result

        with patch.object(scoring,"CUTOFF",deadline), ThreadPoolExecutor(max_workers=len(cpus)) as pool:
            tasks = [pool.submit(run_lane,cpu,chosen[i::len(cpus)]) for i,cpu in enumerate(cpus)]
            rows = [item for task in tasks for item in task.result()]
    trial.publish(OUT/"report.json",dict(plan=plan,model=manifest,rows=rows))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("check","run"))
    p.add_argument("--receipt",type=Path)
    p.add_argument("--stop-by",type=datetime.fromisoformat)
    args = p.parse_args()
    plan,_ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        p.error("requires the sealed choice comparison and authorized cutoff")
    return run(plan,args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
