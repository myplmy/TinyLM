"""Measure an online CPU attention candidate through the AVX2 kernel and a UTF-8 request."""

import argparse
from contextlib import ExitStack
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import diag_p077_lowbit_full_text as text_test
from scripts import diag_p077_lowbit_native as native_test
from scripts import diag_p077_long_choices as saved


BASE = saved.ROOT
PROBE = saved.EVIDENCE / "p077_online_attention_probe_cpu_v1_20261121"
OUT = saved.EVIDENCE / "p077_online_grouped_attention_cpu_v1_20261121"
HEADER = BASE / "scripts/p077_g4_grouped_attention.hpp"
DRIVER = BASE / "scripts/test_p077_online_grouped_attention.cpp"


def probe():
    if PROBE.exists():
        raise FileExistsError(PROBE)
    cpu = min(set(saved.CPU_CORES) & os.sched_getaffinity(0))
    with TemporaryDirectory(prefix="p077_online_attn_") as folder:
        exe = Path(folder)/"probe"
        native_test.compile_probe(DRIVER,exe)
        output = subprocess.check_output(["taskset","-c",str(cpu),exe],timeout=120)
    report = json.loads(output)
    report["p50_ms"] = {"online" if key else "control": median(row["ms"] for row in report["timing"] if row["online"]==key)
                        for key in (False,True)}
    report.update(cpu=cpu,sources=native_test.seal((Path(__file__),HEADER,DRIVER)))
    PROBE.mkdir()
    native_test.publish(PROBE/"report.json",report)
    print(json.dumps({key:value for key,value in report.items() if key!="timing"}),flush=True)


def real_request():
    import torch

    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("the P077 comparison is CPU-only")
    checked = native_test.read(PROBE/"report.json")
    if checked["sources"] != native_test.seal((Path(__file__),HEADER,DRIVER)):
        raise ValueError("the AVX2 probe source proof is stale")
    fixture = native_test.read(text_test.OUT/"fixture.json")
    reference = native_test.read(text_test.OUT/"report.json")
    spec = fixture["inputs"]["kobest_copa"]["1792"]
    cpu = fixture["cpus"][1]
    os.sched_setaffinity(0,{cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    native = saved.native
    bounded = native.bounded
    base,text,token = bounded.base,bounded.text,bounded.token
    tok_source = token.TOK.read_bytes()
    tok_profile = base.READ(token.OUT/"profile.json")
    if sha256(tok_source).hexdigest().upper()!=tok_profile["source_sha256"]:
        raise ValueError("the frozen UTF-8 tokenizer differs")
    codec = token.wire(json.loads(tok_source))
    if [sha256(blob).hexdigest().upper() for blob in codec]!=[r["sha256"] for r in tok_profile["files"]["split_model"]]:
        raise ValueError("split tokenizer differs from the original profile")
    OUT.mkdir(exist_ok=False)
    wrapper = text_test.wrapper(OUT/"long256.py",1792,256)
    stop = reference["stop_ids"]
    control = text_test.render_engine((BASE/base.CPP).read_bytes(),2048,*stop)
    online = native.replace_once(control,b"attention_workspace(capacity)",b"attention_workspace(capacity, true)")
    binaries = {}
    for arm,source in (("control",control),("online",online)):
        folder = OUT/arm
        folder.mkdir()
        with patch.object(bounded,"OUT",folder):
            binaries[arm] = bounded.build(source,caps=(64,))[64][1]
    with ExitStack() as lease:
        fds = [base.memfile(f"p077-stream-{name}") for name in ("r4","r5","vocab","merges")]
        for descriptor in fds:
            lease.callback(os.close,descriptor)
        profile = base.READ(text.OUT/"profile.json")["pins"]["candidate"]
        weights = base.prior.load_candidate(profile)
        packed = base.model_blob(weights,fds[0],profile["model_tensor_bytes"])
        r5 = native.extend_positions(fds[0],fds[1],weights)
        if packed!=reference["r4"] or r5!=reference["r5"]:
            raise ValueError("the current native model differs from the earlier request")
        del weights
        for descriptor,blob in zip(fds[2:],codec,strict=True):
            text.store(descriptor,blob)
            fcntl.fcntl(descriptor,base.prior.DEPLOY.F_ADD_SEALS,base.prior.DEPLOY.SEALS)
        descriptors = {2048:((fds[1],*fds[2:]),r5["artifact_bytes"])}
        runs = []
        for index,variant in enumerate(("control","online","online","control")):
            folder = OUT/f"pass_{index+1}"
            folder.mkdir()
            result = text_test.request("long256","kobest_copa",spec,{2048:binaries[variant]},{"long256":wrapper},
                                       descriptors,stop,folder)
            result.update(order=index+1,variant=variant)
            runs.append(result)
            print(json.dumps({k:result[k] for k in ("order","variant","first_token_seconds","seconds","peak_rss","outputs")}),flush=True)
    native_test.publish(OUT/"report.json",dict(runs=runs,model=r5,cpu=cpu,same_ids=all(r["generated_ids"]==runs[0]["generated_ids"] for r in runs),
                                               sources=native_test.seal((Path(__file__),HEADER))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("probe","text"))
    (probe if parser.parse_args().mode=="probe" else real_request)()
