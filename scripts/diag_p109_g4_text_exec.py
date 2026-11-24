"""Verify a bounded, single-PID UTF-8 request through the compact G4 engine."""

import json
import os
from pathlib import Path
import struct
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
TAG = "p109_g4_text_r4_exec_v2_20261119"
OUT = ROOT / "test_result/evidence" / TAG
WRAPPER = "scripts/p109_g4_text_exec.cpp"
SCRIPT = "scripts/diag_p109_g4_text_exec.py"
GEN = 8


def snapshot():
    expected = {
        "/proc/self/status": ("VmHWM:", "vm_hwm_bytes"),
        "/proc/self/smaps_rollup": ("Rss:", "rss_bytes"),
    }
    result = {}
    for path, (prefix, name) in expected.items():
        with open(path, encoding="ascii") as stream:
            result[name] = int(next(line.split()[1] for line in stream if line.startswith(prefix))) * 1024
    return result


def tokenizer(vocab_fd, merges_fd):
    import sysconfig

    sys.path.append(sysconfig.get_path("purelib"))
    import tokenizers
    from tokenizers import AddedToken, Tokenizer, decoders, models, pre_tokenizers, processors

    paths = [f"/proc/self/fd/{fd}" for fd in (vocab_fd, merges_fd)]
    tok = Tokenizer(models.BPE.from_file(*paths))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    tok.post_processor = processors.ByteLevel(trim_offsets=False)
    tok.decoder = decoders.ByteLevel()
    tok.add_special_tokens([AddedToken(name, normalized=False, special=True)
                            for name in ("<pad>", "<bos>", "<eos>")])
    assert tok.get_vocab_size() == 32768
    assert [tok.token_to_id(s) for s in ("<pad>", "<bos>", "<eos>")] == [0, 1, 2]
    return tok, tokenizers.__version__, tokenizers.__file__


def store(fd, payload):
    with os.fdopen(os.dup(fd), "wb") as stream:
        stream.write(payload)


def read_fd(fd):
    with os.fdopen(os.dup(fd), "rb") as stream:
        stream.seek(0)
        return json.load(stream)


def encode(binary, model, vocab, merges, tokens, encoding, native):
    started = time.perf_counter()
    startup = snapshot()
    raw = sys.stdin.buffer.read(65537)
    assert 0 < len(raw) <= 65536, "invalid UTF-8 request length"
    tok, version, module = tokenizer(vocab, merges)
    loaded = snapshot()
    ids = tok.encode(raw.decode("utf-8"), add_special_tokens=False).ids
    assert 0 < len(ids) <= 1017 and all(0 <= i < 32768 for i in ids)
    store(tokens, struct.pack(f"<{len(ids) + 2}I", len(ids), GEN, *ids))
    store(encoding, json.dumps(dict(
        pid=os.getpid(), bytes=len(raw), ids=ids, tokenizers=version, tokenizer_path=module,
        startup=startup, loaded=loaded, complete=snapshot(), seconds=time.perf_counter() - started,
    )).encode("utf-8"))
    result_stream = os.dup(1)
    os.set_inheritable(result_stream, True)
    os.lseek(tokens, 0, os.SEEK_SET)
    os.dup2(tokens, 0)
    os.close(tokens)
    os.dup2(native, 1)
    os.execv(binary, [binary, str(model), str(result_stream), sys.executable, str(Path(__file__).resolve()),
                      str(vocab), str(merges), str(encoding), str(native)])


def decode(vocab, merges, encoding, native):
    started = time.perf_counter()
    startup = snapshot()
    encoded = read_fd(encoding)
    engine = read_fd(native)
    assert encoded["pid"] == engine["pid"] == os.getpid()
    ids = engine["native"]["ids"]
    assert len(ids) == GEN and all(0 <= i < 32768 for i in ids)
    tok, version, module = tokenizer(vocab, merges)
    loaded = snapshot()
    assert version == encoded["tokenizers"] and module == encoded["tokenizer_path"]
    text = tok.decode(ids, skip_special_tokens=True)
    print(json.dumps(dict(encoding=encoded, native=engine["native"], native_pid=engine["pid"], decoding=dict(
        pid=os.getpid(), startup=startup, loaded=loaded, complete=snapshot(),
        seconds=time.perf_counter() - started, text=text)), ensure_ascii=False))


def run():
    from contextlib import ExitStack
    from datetime import datetime, timedelta
    import fcntl
    from hashlib import sha256
    import subprocess
    import tempfile
    import torch
    from scripts import diag_p109_g4_compact_tile_cpu as tile
    from scripts import diag_p109_g4_tokenizer_budget as bytelevel

    base = tile.dynamic
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(base.prior.ORIGIN.CUTOFF.tzinfo) + timedelta(seconds=1200) < base.prior.ORIGIN.CUTOFF
    cpu = base.READ(base.OUT / "profile.json")["cpu"]
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    pins = base.pins()
    tile_profile, tile_report, tile_compiler = (base.READ(tile.OUT / name) for name in
                                               ("profile.json", "report.json", "compiler.json"))
    assert tile_profile["pins"] == pins
    assert tile_report["profile_sha256"] == base.SHA(tile.OUT / "profile.json")
    tok_profile, tok_report = (base.READ(bytelevel.OUT / name) for name in ("profile.json", "report.json"))
    assert base.SHA(Path(bytelevel.__file__)) == tok_profile["script_sha256"]
    source = bytelevel.TOK.read_bytes()
    assert sha256(source).hexdigest().upper() == bytelevel.EXPECTED_SHA == tok_profile["source_sha256"]
    vocab, merges = bytelevel.wire(json.loads(source))
    assert [sha256(value).hexdigest().upper() for value in (vocab, merges)] == [
        item["sha256"] for item in tok_profile["files"]["split_model"]
    ]
    report_source = tok_report["runs"]["split_model"][0]
    assert tok_report["summary"]["split_model"]["exact"]
    original_fp16 = base.READ(base.REFERENCE_PATH)["requests"]
    expected_ids = {language: original_fp16[language]["fp16"]["ids"] for language in ("english", "korean")}
    assert all(tile_report["cases"][language]["same_ids"]
               and tile_report["cases"][language]["ids"] == expected_ids[language] for language in expected_ids)
    core = (ROOT / base.CPP).read_bytes().replace(tile.ORIGINAL, tile.CHANGED, 1)
    assert sha256(core).hexdigest().upper() == tile_compiler["source_sha256"]
    OUT.mkdir(exist_ok=False)
    sources = {path: base.SHA(ROOT / path) for path in (SCRIPT, WRAPPER, base.CPP, base.C)}
    base.WRITE(OUT / "profile.json", dict(
        tag=TAG, sources=sources, pins=pins, cpu=cpu, tokenizer_profile=base.SHA(bytelevel.OUT / "profile.json"),
        tokenizer_reference=base.SHA(bytelevel.OUT / "report.json"),
        tile_reference=base.SHA(tile.OUT / "report.json"), core_sha256=tile_compiler["source_sha256"],
        execution_order=["english", "korean", "korean", "english"],
    ))

    work = Path(tempfile.mkdtemp(prefix="p109_g4_text_exec_", dir="/tmp"))
    lookup, engine, binary = (work / name for name in ("lookup.o", "compact.o", "g4_text"))
    flags = ["-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off",
             "-Wall", "-Wextra", "-Werror"]
    commands = [
        ["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
         "-c", base.C, "-o", str(lookup)],
        ["/usr/bin/g++", *flags, "-Dmain=run_compact_g4", "-x", "c++", "-", "-c", "-o", str(engine)],
        ["/usr/bin/g++", *flags, WRAPPER, str(engine), str(lookup), "-static", "-o", str(binary)],
    ]
    for index, command in enumerate(commands):
        subprocess.run(command, input=core if index == 1 else None, cwd=ROOT, timeout=90, check=True)
    assert "INTERP" not in subprocess.check_output(["/usr/bin/readelf", "-l", str(binary)], text=True)
    base.WRITE(OUT / "compiler.json", dict(commands=commands, binary=str(binary), sha256=base.SHA(binary),
                                          binary_bytes=binary.stat().st_size))
    runs = []
    with ExitStack() as stack:
        def alloc(name, *, contents=None):
            fd = base.memfile(name)
            stack.callback(os.close, fd)
            if contents is not None:
                store(fd, contents)
                fcntl.fcntl(fd, base.prior.DEPLOY.F_ADD_SEALS, base.prior.DEPLOY.SEALS)
                assert fcntl.fcntl(fd, base.prior.DEPLOY.F_GET_SEALS) == base.prior.DEPLOY.SEALS
            return fd

        model_fd = alloc("g4_text_model")
        model = base.prior.load_candidate(pins["candidate"])
        artifact = base.model_blob(model, model_fd, pins["candidate"]["model_tensor_bytes"])
        del model
        assert artifact == tile_report["artifact"]
        vocab_fd = alloc("g4_text_vocab", contents=vocab)
        merges_fd = alloc("g4_text_merges", contents=merges)
        for index, language in enumerate(("english", "korean", "korean", "english")):
            with ExitStack() as request:
                intermediates = [base.memfile(f"g4_stage_{index}_{i}") for i in range(3)]
                for fd in intermediates:
                    request.callback(os.close, fd)
                fds = (model_fd, vocab_fd, merges_fd, *intermediates)
                text = report_source["outputs"][language]["decoded"].encode("utf-8")
                command = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(ROOT / SCRIPT),
                           "encode", str(binary), *map(str, fds)]
                started = time.perf_counter()
                process = subprocess.run(command, input=text, pass_fds=fds, capture_output=True, timeout=300)
                if process.returncode:
                    print(process.stderr.decode("utf-8", "replace"), file=sys.stderr, flush=True)
                    process.check_returncode()
                elapsed = time.perf_counter() - started
            case = json.loads(process.stdout)
            case.update(case=language, index=index, wall_seconds=elapsed)
            base.WRITE(OUT / f"raw_case_{index}.json", case)
            assert case["encoding"]["tokenizers"] == report_source["tokenizers"]
            assert case["encoding"]["tokenizer_path"] == report_source["module_path"]
            case["matches"] = {
                "input_ids": case["encoding"]["ids"] == report_source["outputs"][language]["ids"],
                "output_ids": case["native"]["ids"] == expected_ids[language],
                "output_text": case["decoding"]["text"] == report_source["continuations"][language],
                "pid": case["encoding"]["pid"] == case["native_pid"] == case["decoding"]["pid"],
            }
            assert len(case["encoding"]["ids"]) == 1017 and case["native"]["kv_bytes"] == 11010048
            assert case["native"]["model_bytes"] == artifact["artifact_bytes"]
            native_peak = max(case["native"][phase][key]
                              for phase in ("before", "loaded", "prefilled", "complete")
                              for key in ("vm_hwm", "rss"))
            get_peak = lambda stage: max(value for phase in ("startup", "loaded", "complete")
                                         for value in case[stage][phase].values())
            case["peaks"] = dict(encoder=get_peak("encoding"), engine=native_peak, decoder=get_peak("decoding"))
            observed = max(case["peaks"].values())
            case.update(peak_rss_bytes=observed, within_si=observed <= 40_000_000,
                        within_mib=observed <= 40 * 2**20)
            runs.append(case)
            print("G4_TEXT_EXEC", index, language, case["peaks"], observed, elapsed, case["matches"], flush=True)
    assert not torch.cuda.is_initialized()
    assert all(base.SHA(ROOT / path) == digest for path, digest in sources.items())
    base.WRITE(OUT / "report.json", dict(runs=runs, source=artifact, any_gpu=False, checkpoint_writes=0,
                                        same_pid_exec=True, profile_sha256=base.SHA(OUT / "profile.json")))
    return 0 if all(all(case["matches"].values()) for case in runs) else 8


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        sys.exit(run())
    if len(sys.argv) == 9 and sys.argv[1] == "encode":
        encode(sys.argv[2], *map(int, sys.argv[3:]))
    elif len(sys.argv) == 6 and sys.argv[1] == "decode":
        decode(*map(int, sys.argv[2:]))
    else:
        raise SystemExit("expected run, encode, or decode with inherited descriptors")
