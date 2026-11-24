"""Measure single-PID P077 text requests with 128 and 256 generation caps."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timedelta
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from unittest.mock import patch

import torch
from tokenizers import Tokenizer

from scripts import diag_p077_long_choices as saved
from scripts import diag_p077_lowbit_native as lowbit


OUT = saved.EVIDENCE / "p077_lowbit_full_text_cpu_v1_20261121"
CASES = {"short128": (1024, 896, 128), "long128": (2048, 1792, 128), "long256": (2048, 1792, 256)}


def make_prompt(tokenizer, row, limit):
    ctx = row["contexts"][row["gold"]]
    target = row["targets"][row["gold"]]
    cut = row["cut"]
    left = tokenizer.decode(ctx[:cut], skip_special_tokens=False)
    right = tokenizer.decode(ctx[cut:], skip_special_tokens=False)
    target_text = tokenizer.decode(target, skip_special_tokens=False)
    sentences = re.split(r"(?<=\.)\s+", saved.FILLER[row["task"]].strip())
    added = []
    best = None
    for index in range(limit):
        added.append(sentences[index % len(sentences)])
        prompt = f"{left.rstrip()} {' '.join(added)} {right.lstrip()}"
        actual = tokenizer.encode(prompt, add_special_tokens=False).ids
        if len(actual) > limit:
            break
        complete = tokenizer.encode(prompt+target_text, add_special_tokens=False).ids
        if limit-24 <= len(actual) <= limit and complete == actual+target:
            best = dict(prompt=prompt, ids=actual, target=target, expected=target_text, limit=limit)
    if best is None:
        raise ValueError(f"cannot keep the expected continuation around {limit} inputs")
    return best


def render_engine(source, context, eot, eos):
    native = saved.native
    replace = native.replace_once
    source = native.render(source, context, 3 if context == 2048 else 0, True, True)
    if context == 2048:
        source = replace(source, b"cache(capacity, 1024, 3)", b"cache(capacity, 1920, 4, 2)")
    source = replace(source, b"generate <= 8", b"generate <= 256")
    source = replace(source, b"std::array<uint32_t,8> ids{};", b"std::array<uint32_t,256> ids{};")
    source = replace(source, b"std::array<double,8> times{};", b"std::array<double,256> times{};")
    source = replace(source, b"Memory prefilled{};", b"Memory prefilled{};\n        uint32_t produced = 0;")
    source = replace(source, b"if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);",
                     ("if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);\n"
                      f"            produced = i + 1;\n            if (ids[i] == {eot} || ids[i] == {eos}) break;").encode())
    pos = source.index(b'printf(",\\"ids\\":[");')
    tail = source[pos:]
    marker = b"i < generate; ++i"
    if tail.count(marker) != 2:
        raise ValueError("text report generation loops changed")
    return source[:pos] + tail.replace(marker, b"i < produced; ++i")


def wrapper(path, input_limit, generation):
    text = saved.native.bounded.text
    source = (saved.ROOT / text.SCRIPT).read_bytes()
    replace = saved.native.replace_once
    for old, new in ((b"GEN = 8", f"GEN = {generation}".encode()),
                     (b"len(ids) <= 1017", f"len(ids) <= {input_limit}".encode()),
                     (b"assert len(ids) == GEN", b"assert 0 < len(ids) <= GEN")):
        source = replace(source, old, new)
    path.write_bytes(source)
    return path


def request(name, task, spec, binaries, wrappers, descriptors, stop_ids, directory):
    native = saved.native
    context, _, generation = CASES[name]
    asset, model_bytes = descriptors[context]
    capacity = len(spec["ids"]) + generation - 1
    prior = native.bounded.prior
    expected_kv = prior.int8_capacity(capacity)
    if context == 2048:
        old = min(1920, capacity//32*32)
        expected_kv -= old * prior.SLOTS * prior.KV * 10 // 8
        expected_kv += old * prior.SLOTS * (prior.KV//prior.HEAD) * 2
    path = directory / f"{task}-{name}.json"
    reference = dict(encoding=dict(ids=spec["ids"]), native=dict(kv_bytes=expected_kv, model_bytes=model_bytes))
    summary = native.request(binaries[context], asset, spec["prompt"].encode("utf-8"), path, reference,
                             wrapper=wrappers[name])
    raw = lowbit.read(path)
    ids = raw["native"]["ids"]
    if len(ids) > generation or len(ids) != len(raw["native"]["seconds"]):
        raise RuntimeError("generation exceeds the recorded fixed cap")
    sequence = ids[:-1] if ids[-1] in stop_ids else ids
    fourgrams = [tuple(sequence[i:i+4]) for i in range(len(sequence)-3)]
    stats = {key: summary[key] for key in ("seconds", "scratch_bytes", "peak_rss", "kv_bytes")}
    return dict(task=task, case=name, input_tokens=len(spec["ids"]), max_output=generation,
                outputs=len(ids), ended=ids[-1] in stop_ids, generated_ids=ids,
                first_token_seconds=raw["native"]["seconds"][0],
                token_per_second=(len(ids)-1)/sum(raw["native"]["seconds"][1:]) if len(ids)>1 else None,
                native_prefill_rss=raw["native"]["prefilled"]["rss"],
                gold_prefix=sequence[:len(spec["target"])] == spec["target"],
                repeated_fourgrams=len(fourgrams)-len(set(fourgrams)), **stats)


def main():
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or OUT.exists()
            or datetime.now(saved.CUTOFF.tzinfo)+timedelta(minutes=8) >= saved.CUTOFF):
        raise ValueError("requires CPU mode and a fresh output inside the authorized window")
    native = saved.native
    bounded = native.bounded
    base, text, token = bounded.base, bounded.text, bounded.token
    fixture = lowbit.read(lowbit.OLD / "fixture.json")
    codec_profile = base.READ(token.OUT / "profile.json")
    token_bytes = token.TOK.read_bytes()
    if sha256(token_bytes).hexdigest().upper() != codec_profile["source_sha256"]:
        raise ValueError("the saved tokenizer differs")
    parts = token.wire(json.loads(token_bytes))
    if [sha256(blob).hexdigest().upper() for blob in parts] != [r["sha256"] for r in codec_profile["files"]["split_model"]]:
        raise ValueError("wire tokenizer is not the archived split")
    tokenizer = Tokenizer.from_str(token_bytes.decode("utf-8"))
    stops = [tokenizer.token_to_id(s) for s in ("<|im_end|>", "<eos>")]
    if stops[1] is None:
        raise ValueError("the tokenizer has no document end token")
    stops = [stops[1] if x is None else x for x in stops]
    source = (saved.ROOT / base.CPP).read_bytes()
    cpus = sorted(set(saved.CPU_CORES) & os.sched_getaffinity(0))[:2]
    if len(cpus) != 2:
        raise ValueError("two distinct CPU cores are required for the matched cases")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    rows = {kind: max((r for r in fixture["chosen"] if r["task"] == kind), key=lambda r: r["short_margin"])
            for kind in ("winogrande", "kobest_copa")}
    inputs = {kind: {limit: make_prompt(tokenizer, row, limit) for limit in (896, 1792)} for kind, row in rows.items()}
    OUT.mkdir()
    lowbit.publish(OUT/"fixture.json", dict(inputs=inputs, selected={key: row["index"] for key,row in rows.items()}, cpus=cpus))
    wrappers = {case: wrapper(OUT/f"{case}.py", limit, generation) for case, (_,limit,generation) in CASES.items()}
    binaries = {}
    for context in (1024, 2048):
        folder = OUT / str(context)
        folder.mkdir()
        with patch.object(bounded, "OUT", folder):
            binaries[context] = bounded.build(render_engine(source, context, *stops), caps=(64,))[64][1]
    with ExitStack() as lease:
        fds = [base.memfile(f"p077-long-{name}") for name in ("r4", "r5", "vocab", "merges")]
        for fd in fds:
            lease.callback(os.close, fd)
        profile = base.READ(text.OUT / "profile.json")["pins"]["candidate"]
        g4 = base.prior.load_candidate(profile)
        packed = base.model_blob(g4, fds[0], profile["model_tensor_bytes"])
        r5 = native.extend_positions(fds[0], fds[1], g4)
        if packed != base.READ(text.OUT/"report.json")["source"] or r5 != fixture["model"]:
            raise ValueError("frozen native model identity differs")
        del g4
        for fd, blob in zip(fds[2:], parts, strict=True):
            text.store(fd, blob)
            fcntl.fcntl(fd, base.prior.DEPLOY.F_ADD_SEALS, base.prior.DEPLOY.SEALS)
        descriptors = {1024: ((fds[0], *fds[2:]), packed["artifact_bytes"]),
                       2048: ((fds[1], *fds[2:]), r5["artifact_bytes"])}

        def one_language(kind, cpu, order):
            os.sched_setaffinity(0, {cpu})
            for name in order:
                result = request(name, kind, inputs[kind][CASES[name][1]], binaries, wrappers, descriptors, stops, OUT)
                print(json.dumps({key: result[key] for key in ("task", "case", "seconds", "peak_rss", "outputs", "ended")}), flush=True)
                yield result

        order = tuple(CASES)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(lambda *args: list(one_language(*args)), kind, cpu, directions)
                       for kind,cpu,directions in zip(rows,cpus,(order,order[::-1]), strict=True)]
            results = [row for future in futures for row in future.result()]
    lowbit.publish(OUT/"report.json", dict(cases=results, r4=packed, r5=r5, stop_ids=stops,
                   sources=lowbit.seal((Path(__file__), saved.ROOT/base.CPP, saved.ROOT/"scripts"/lowbit.HEADER))))


if __name__ == "__main__":
    main()
