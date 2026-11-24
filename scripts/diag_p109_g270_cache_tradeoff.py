"""Compare two G270 cache and prefill choices on the frozen full requests."""

from contextlib import ExitStack
from datetime import datetime, timedelta
from hashlib import sha256
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import tempfile
from unittest.mock import patch

import torch

from scripts import diag_p109_g270_text as prior


ROOT, io = prior.ROOT, prior.io
TAG = "p109_g270_cache_tradeoff_v1_20261119"
OUT = prior.OUT.with_name(TAG)
BASE = prior.OUT
KINDS = ("int8_full", "fp16_small")
ORDER = (KINDS[0], KINDS[1], KINDS[1], KINDS[0])
FP16_CACHE = b"""
class HalfG270Cache {
public:
    explicit HalfG270Cache(int capacity)
        : capacity_(capacity), key_(Slots * capacity * Kv), value_(Slots * capacity * Kv) {}
    size_t bytes() const { return sizeof(uint16_t) * (key_.capacity() + value_.capacity()); }
    void restore(int slot, int past, float* k, float* v) const {
        load_half(k, key_.data() + slot * capacity_ * Kv, past * Kv);
        load_half(v, value_.data() + slot * capacity_ * Kv, past * Kv);
    }
    void append(int slot, int past, int count, const float* k, const float* v) {
        const auto start = (slot * capacity_ + past) * Kv;
        store_half(key_.data() + start, k + past * Kv, count * Kv);
        store_half(value_.data() + start, v + past * Kv, count * Kv);
    }
private:
    int capacity_;
    std::vector<uint16_t> key_, value_;
};
"""


def build():
    _, int8 = prior.render()
    fp16 = prior.replace(int8, b'#include "p109_g4_grouped_int8_cache.hpp"', FP16_CACHE)
    fp16 = prior.replace(fp16, b"GroupedInt8Cache cache;", b"HalfG270Cache cache;")
    directory = Path(tempfile.mkdtemp(prefix="p109_g270_cache_tradeoff_", dir="/tmp"))
    scalar, lookup = (str(directory/n) for n in ("scalar.o", "lookup.o"))
    flags = ["-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off", "-Wall", "-Wextra", "-Werror",
             "-I", str(ROOT/"scripts")]
    commands = []

    def call(argv, data=None):
        subprocess.run(argv, input=data, cwd=ROOT, timeout=80, check=True)
        commands.append(argv)

    call(["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Werror", "-Dp014e_cpu_lookup=p014e_scalar_lookup",
          "-c", str(prior.SCALAR), "-o", scalar])
    compiled_lookup = prior.LOOKUP.read_bytes() + b"\n" + prior.EXTENSION.read_bytes()
    call(["/usr/bin/g++", *flags, "-x", "c++", "-", "-c", "-o", lookup], compiled_lookup)
    driver = b"int run_compact_g4(int, char**);\nint main(int n,char** a){return run_compact_g4(n,a);}\n"
    output = {}
    for name, source, cap in ((KINDS[0], int8, 1024), (KINDS[1], fp16, 64)):
        obj, numerical, full = (str(directory/f"{name}_{suffix}") for suffix in ("engine.o", "numeric", "text"))
        call(["/usr/bin/g++", *flags, f"-DP109_PREFILL_TOKENS={cap}", "-Dmain=run_compact_g4", "-x", "c++", "-",
              "-c", "-o", obj], source)
        call(["/usr/bin/g++", *flags, "-x", "c++", "-", "-x", "none", obj, lookup, scalar, "-static", "-o", numerical], driver)
        call(["/usr/bin/g++", *flags, str(prior.WRAPPER), obj, lookup, scalar, "-static", "-o", full])
        output[name] = (numerical, full)
    assert all("INTERP" not in subprocess.check_output(["/usr/bin/readelf", "-l", exe], text=True)
               for pair in output.values() for exe in pair)
    io.write(OUT/"compiler.json", dict(commands=commands,binaries={name:[dict(path=p,sha256=io.digest(p)) for p in files]
                            for name,files in output.items()}))
    return output


@torch.inference_mode()
def run():
    cutoff = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=360) < cutoff
    profile_path, report_path = BASE/"profile.json", BASE/"report.json"
    previous, report = io.load(profile_path), io.load(report_path)
    assert report["profile_sha256"] == io.digest(profile_path)
    assert report["native_fp32_port_passed"] and report["memory_passed"] and report["outputs_equal"]
    assert io.digest(prior.PAYLOAD) == previous["payload_sha256"]
    assert all(io.digest(ROOT/p)==sha for p,sha in previous["sources"].items())
    docs = {name: BASE/f"request_{name}_1.json" for name in ("english", "korean")}
    pins = {str(p.relative_to(ROOT)):io.digest(p) for p in (profile_path, report_path, Path(__file__), *docs.values())}
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    io.write(OUT/"profile.json",dict(tag=TAG,pins=pins,order=list(ORDER),prefill_tokens=[1024,64],
            original_result=io.digest(report_path),same_payload=previous["payload_sha256"]))
    binaries = build()
    numbers, results = [], []
    with ExitStack() as stack:
        def descriptor(name):
            fd = prior.prefill.base.memfile(name)
            stack.callback(os.close,fd)
            return fd

        model_fd = descriptor("g270_tradeoff_model")
        asset = prior.export(model_fd)
        assert asset == report["artifact"]
        tok_fds = tuple(descriptor(f"g270_tradeoff_tok_{i}") for i in range(3))
        for fd,path in zip(tok_fds,prior.QUANTIZED,strict=True):
            prior.text.store(fd,path.read_bytes())
            prior.seal(fd)
        for name in ("ko512", "en512"):
            gold = torch.load(prior.GOLD/f"{name}.pt",map_location="cpu",weights_only=True)
            ids, expected = gold["input"]["ids"], gold["teacher_ids"]
            reference = torch.stack(gold["logits"]).reshape(4,prior.VOCAB).numpy()
            for kind,(binary,_) in binaries.items():
                receipt,logits = prior.native(binary,model_fd,ids,4,True)
                row = dict(case=name,kind=kind,**prior.same_history(reference,expected,receipt,logits))
                print("G270_CACHE_TRADEOFF_NUMERIC",row,flush=True)
                numbers.append(row)
        with prior.tok.CsrGemma(*prior.QUANTIZED) as codec, patch.object(prior,"OUT",OUT):
            for lang,path in docs.items():
                original = io.load(path)["encoding"]["ids"]
                document = codec.decode(original,skip_special_tokens=False).encode("utf-8")
                control = report["long_controls"][lang]
                assert sha256(document).hexdigest().upper()==control["input_sha256"]
                for index,kind in enumerate(ORDER):
                    row = prior.full_request(binaries[kind][1],(model_fd,*tok_fds),document,f"{lang}_{kind}",index)
                    assert row.pop("source_ids")==original and row["model_bytes"]==asset["bytes"]
                    row.update(case=lang,kind=kind,same_output=row["ids"]==control["ids"] and row["text"]==control["text"])
                    results.append(row)
                    print("G270_CACHE_TRADEOFF_TEXT",lang,kind,row["peak"],row["same_output"],row["seconds"],flush=True)
    assert not torch.cuda.is_initialized() and io.digest(prior.PAYLOAD)==previous["payload_sha256"]
    assert all(io.digest(ROOT/p)==sha for p,sha in previous["sources"].items())
    assert all(io.digest(ROOT/p)==sha for p,sha in pins.items())
    table = {}
    for name in KINDS:
        rows = [r for r in results if r["kind"]==name]
        peak = max(r["peak"] for r in rows)
        table[name] = dict(peak=peak,within_40mb=peak<=40_000_000,all_outputs_equal=all(r["same_output"] for r in rows),
            median_seconds={lang:median(r["seconds"] for r in rows if r["case"]==lang) for lang in docs})
    io.write(OUT/"report.json",dict(numeric=numbers,runs=results,summary=table,payload=asset,
        previous_report=io.digest(report_path),profile_sha256=io.digest(OUT/"profile.json"),checkpoint_writes=0))


if __name__ == "__main__":
    run()
