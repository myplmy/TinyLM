"""Measure equivalent TinyLM ByteLevel loaders in isolated interpreter processes."""

import json
from pathlib import Path
import sys


TAG = "p109_g4_bytelevel_budget_v2_20261119"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test_result/evidence" / TAG
TOK = ROOT / "data_cache/tok-ko-en-32768.json"
EXPECTED_SHA = "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3"
REFERENCE = ROOT / "test_result/evidence/p109_g4_int8_kv1024_v1_20261119"
ARMS = ("source_json", "compact_json", "split_model")


def memory():
    keys = (
        ("/proc/self/status", "VmHWM:", "vm_hwm_bytes"),
        ("/proc/self/smaps_rollup", "Rss:", "rss_bytes"),
    )
    result = {}
    for path, prefix, field in keys:
        with open(path, encoding="ascii") as stream:
            result[field] = 1024 * int(next(row.split()[1] for row in stream if row.startswith(prefix)))
    return result


def worker(mode, files):
    import sysconfig
    from time import perf_counter

    sys.path.append(sysconfig.get_path("purelib"))
    import tokenizers
    from tokenizers import Tokenizer

    assert mode in ARMS
    points = {"starting": memory()}
    request = json.load(sys.stdin)
    paths = [f"/proc/self/fd/{int(fd)}" for fd in files]
    started = perf_counter()
    if mode == "split_model":
        from tokenizers import AddedToken, decoders, models, pre_tokenizers, processors

        tok = Tokenizer(models.BPE.from_file(*paths))
        tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
        tok.post_processor = processors.ByteLevel(trim_offsets=False)
        tok.decoder = decoders.ByteLevel()
        tok.add_special_tokens([AddedToken(name, normalized=False, special=True)
                                for name in ("<pad>", "<bos>", "<eos>")])
    else:
        assert len(paths) == 1
        tok = Tokenizer.from_file(paths[0])
    seconds = perf_counter() - started
    points["loaded"] = memory()
    assert tok.get_vocab_size() == 32768
    assert [tok.token_to_id(t) for t in ("<pad>", "<bos>", "<eos>")] == [0, 1, 2]
    outputs = {}
    for case, text in request["texts"].items():
        row = tok.encode(text, add_special_tokens=False)
        outputs[case] = dict(ids=row.ids, offsets=row.offsets, special=row.special_tokens_mask,
                             decoded=tok.decode(row.ids, skip_special_tokens=False))
    decoded = {k: tok.decode(ids, skip_special_tokens=True) for k, ids in request["continuations"].items()}
    points["processed"] = memory()
    peak = max(value for point in points.values() for value in point.values())
    print(json.dumps(dict(mode=mode, tokenizers=tokenizers.__version__, module_path=tokenizers.__file__,
                          measured=points, peak_bytes=peak,
                          load_seconds=seconds, outputs=outputs, continuations=decoded), ensure_ascii=False))


def wire(model, *, special_tokens=("<pad>", "<bos>", "<eos>")):
    s = model["model"]
    assert model["normalizer"] is model["truncation"] is model["padding"] is None
    assert model["pre_tokenizer"] == dict(type="ByteLevel", add_prefix_space=False, trim_offsets=True, use_regex=True)
    assert model["post_processor"] == dict(type="ByteLevel", add_prefix_space=True, trim_offsets=False, use_regex=True)
    assert model["decoder"] == dict(type="ByteLevel", add_prefix_space=True, trim_offsets=True, use_regex=True)
    assert {k: v for k, v in s.items() if k not in ("vocab", "merges")} == dict(
        type="BPE", dropout=None, unk_token=None, continuing_subword_prefix=None, end_of_word_suffix=None,
        fuse_unk=False, byte_fallback=False, ignore_merges=False)
    assert model["added_tokens"] == [
        dict(id=i, content=name, single_word=False, lstrip=False, rstrip=False, normalized=False, special=True)
        for i, name in enumerate(special_tokens)]
    assert len(s["vocab"]) == 32768 and len(s["merges"]) == 32768 - 256 - len(special_tokens)
    lines = ["#version: 0.2"]
    for pair in s["merges"]:
        assert len(pair) == 2 and all(t and not any(c in t for c in " \r\n\t") for t in pair)
        lines.append(" ".join(pair))
    return (json.dumps(s["vocab"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            ("\n".join(lines) + "\n").encode("utf-8"))


def run():
    from contextlib import ExitStack
    import ctypes
    from hashlib import sha256
    import fcntl
    import os
    import subprocess
    from tokenizers import Tokenizer

    def sha(data):
        return sha256(data).hexdigest().upper()

    def receipt(path, value):
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            print(file=stream)

    raw = TOK.read_bytes()
    assert sha(raw) == EXPECTED_SHA
    model = json.loads(raw)
    wires = {
        "source_json": (raw,),
        "compact_json": (json.dumps(model, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),),
        "split_model": wire(model),
    }
    old = json.loads((REFERENCE / "profile.json").read_bytes())
    report = json.loads((REFERENCE / "report.json").read_bytes())
    reference = Tokenizer.from_file(str(TOK))
    texts, continuations = {}, {}
    for name in ("english", "korean"):
        original_ids = old["cases"][name]["ids"]
        text = reference.decode(original_ids, skip_special_tokens=False)
        assert reference.encode(text, add_special_tokens=False).ids == original_ids and len(original_ids) == 1017
        texts[name] = text
        continuations[name] = report["requests"][name]["fp16"]["ids"]
    texts.update(ascii="The train arrived at 08:07.", hangul="정원에 비가 내렸다.",
                 mixed=" 서울, then Busan. 🚆", whitespace="  first\tsecond\r\n셋  ",
                 symbol="x ≥ 1? [2]; '3'.", special="<bos>안녕<eos> <pad>",
                 accented="Café / Café", empty="")
    request = json.dumps(dict(texts=texts, continuations=continuations), ensure_ascii=False).encode("utf-8")
    OUT.mkdir(exist_ok=False)
    profiles = {a: [dict(bytes=len(v), sha256=sha(v)) for v in items] for a, items in wires.items()}
    receipt(OUT / "profile.json", dict(tag=TAG, input_sha256=sha(request), source_sha256=sha(raw), files=profiles,
                                     script_sha256=sha(Path(__file__).read_bytes()), cases=list(texts),
                                     reference=sha((REFERENCE / "profile.json").read_bytes())))
    runs = {mode: [] for mode in ARMS}
    with ExitStack() as stack:
        descriptors = {}
        create = ctypes.CDLL(None, use_errno=True).memfd_create
        create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
        create.restype = ctypes.c_int
        add_seals, get_seals, all_seals = 1033, 1034, 15
        for mode, assets in wires.items():
            fds = []
            for data in assets:
                fd = create(b"p109_bytelevel", 3)
                if fd < 0:
                    raise OSError(ctypes.get_errno(), "memfd_create")
                stack.callback(os.close, fd)
                with os.fdopen(os.dup(fd), "wb") as stream:
                    stream.write(data)
                fcntl.fcntl(fd, add_seals, all_seals)
                assert fcntl.fcntl(fd, get_seals) == all_seals
                fds.append(fd)
            descriptors[mode] = tuple(fds)
        for order in (ARMS, ARMS[::-1]):
            for mode in order:
                fds = descriptors[mode]
                cmd = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(Path(__file__).resolve()),
                       mode, *map(str, fds)]
                out = subprocess.run(cmd, input=request, pass_fds=fds, capture_output=True, timeout=12)
                if out.returncode:
                    print(out.stderr.decode("utf-8", "replace"), file=sys.stderr, flush=True)
                    out.check_returncode()
                row = json.loads(out.stdout)
                runs[mode].append(row)
                print("G4_BYTELEVEL_RSS", mode, row["peak_bytes"], row["load_seconds"], flush=True)
    expected = runs["source_json"][0]
    summary = {}
    for mode, reports in runs.items():
        peak = max(r["peak_bytes"] for r in reports)
        exact = all(all(r[k] == expected[k] for k in ("outputs", "continuations")) for r in reports)
        summary[mode] = dict(peak_bytes=peak, exact=exact, within_si=peak <= 40_000_000, within_mib=peak <= 40 * 2**20)
    assert sha(TOK.read_bytes()) == EXPECTED_SHA
    receipt(OUT / "report.json", dict(runs=runs, summary=summary, exact_long_inputs=[1017, 1017], model_runs=0))
    return 0 if all(row["exact"] for row in summary.values()) else 8


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.exit(run())
    worker(sys.argv[1], sys.argv[2:])
