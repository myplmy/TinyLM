"""Compare the eight-query online engine on the archived full-width G4."""

import argparse
from contextlib import ExitStack
from datetime import datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import torch

from scripts import diag_p077_g4_wide_query_prefill as wide
from scripts import diag_p077_lowbit_full_text as texts


TAG = "p077_g4_full_width_prefill_cpu_v1_20261121"
OUT = texts.OUT.with_name(TAG)
trial = wide.trial
native = texts.saved.native
bounded,base,text,codec = native.bounded,native.bounded.base,native.bounded.text,native.bounded.token
TASKS = ("kobest_copa","winogrande")
MODE = "long128"
ORDERS = (("full3","online8","online8","full3"),("online8","full3","full3","online8"))


def prepare():
    fixture_path = texts.OUT/"fixture.json"
    reference_path = texts.OUT/"report.json"
    fixture,baseline = (trial.read_json(p) for p in (fixture_path,reference_path))
    reference = {row["task"]:row for row in baseline["cases"] if row["case"]==MODE}
    if (set(reference)!=set(TASKS) or any(reference[k]["input_tokens"]!=len(fixture["inputs"][k]["1792"]["ids"])
            or reference[k]["outputs"]!=128 for k in TASKS)):
        raise ValueError("the two archived 128-token generation cases changed")
    token = codec.TOK.read_bytes()
    signature = trial.read_json(codec.OUT/"profile.json")
    parts = codec.wire(json.loads(token))
    if (sha256(token).hexdigest().upper()!=signature["source_sha256"]
            or [sha256(v).hexdigest().upper() for v in parts] !=
            [row["sha256"] for row in signature["files"]["split_model"]]):
        raise ValueError("the original tokenizer or its split wire changed")
    src = (trial.ROOT/base.CPP).read_bytes()
    engine = texts.render_engine(src,2048,*baseline["stop_ids"])
    original = trial.read_json(texts.OUT/"2048"/"compiler.json")
    if sha256(engine).hexdigest().upper()!=original["source_sha256"]:
        raise ValueError("the archived full-width engine source changed")
    profile = dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),fixture_sha256=trial.file_sha(fixture_path),
                   reference_sha256=trial.file_sha(reference_path),tokenizer_sha256=signature["source_sha256"],
                   r5=baseline["r5"],orders=[list(x) for x in ORDERS],
                   full_source_sha256=original["source_sha256"],
                   online_source_sha256=sha256(wide.render(engine,"online8")).hexdigest().upper())
    return profile,(fixture,baseline,reference,parts,engine,original)


def build(engine,original):
    old = original["binaries"]["64"][1]
    path = Path(old["path"])
    candidate = OUT/"online8"
    candidate.mkdir()
    if path.is_file() and native.bounded.base.SHA(path)==old["sha256"]:
        control = path
        trial.publish(OUT/"archived_compiler.json",original)
    else:
        folder = OUT/"full3"
        folder.mkdir()
        with patch.object(bounded,"OUT",folder):
            control = bounded.build(engine,caps=(64,))[64][1]
    with patch.object(bounded,"OUT",candidate):
        online = bounded.build(wide.render(engine,"online8"),caps=(64,))[64][1]
    return {"full3":control,"online8":online}


def run(plan,deadline):
    if (os.environ.get("CUDA_VISIBLE_DEVICES")!="" or OUT.exists() or not deadline.tzinfo
            or deadline>wide.request.byte_table.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<450):
        raise ValueError("requires a new CPU comparison within the authorized window")
    checked,(fixtures,baseline,reference,parts,engine,original) = prepare()
    if checked!=plan:
        raise ValueError("the full-width inputs changed")
    cpus = set(fixtures["cpus"])&os.sched_getaffinity(0)
    if not cpus:
        raise ValueError("the earlier CPU lanes are unavailable")
    cpu = max(cpus)
    os.sched_setaffinity(0,{cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    paths = build(engine,original)
    wrapper = texts.wrapper(OUT/"long128.py",1792,128)
    with ExitStack() as stack:
        r4,r5,vocab,merges = [base.memfile(f"p077-full-width-{name}") for name in ("r4","r5","vocab","merges")]
        for fd in (r4,r5,vocab,merges):
            stack.callback(os.close,fd)
        original_weights = base.READ(text.OUT/"profile.json")["pins"]["candidate"]
        weights = base.prior.load_candidate(original_weights)
        packed_old = base.model_blob(weights,r4,original_weights["model_tensor_bytes"])
        packed_wide = native.extend_positions(r4,r5,weights)
        del weights
        if packed_old!=baseline["r4"] or packed_wide!=baseline["r5"]:
            raise ValueError("reconstructed model is not the archived full-width G4")
        for fd,blob in zip((vocab,merges),parts,strict=True):
            text.store(fd,blob)
            fcntl.fcntl(fd,base.prior.DEPLOY.F_ADD_SEALS,base.prior.DEPLOY.SEALS)
        assets = {2048:((r5,vocab,merges),packed_wide["artifact_bytes"])}
        results = []
        for task,arms in zip(TASKS,ORDERS,strict=True):
            for order,arm in enumerate(arms):
                if (OUT/"STOP").exists() or (deadline-datetime.now(deadline.tzinfo)).total_seconds()<160:
                    raise TimeoutError("the comparison ended before the authorized cutoff")
                folder = OUT/f"{task}_{order}"
                folder.mkdir()
                row = texts.request(MODE,task,fixtures["inputs"][task]["1792"],{2048:paths[arm]},
                                    {MODE:wrapper},assets,baseline["stop_ids"],folder)
                row.update(arm=arm,order=order,unchanged=row["generated_ids"]==reference[task]["generated_ids"])
                results.append(row)
                print(json.dumps({k:v for k,v in row.items() if k!="generated_ids"}),flush=True)
    trial.publish(OUT/"report.json",dict(plan=plan,cpu=cpu,rows=results))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires a sealed full-width execution and authorized cutoff")
    return run(plan,args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
