"""Compare complete 4K/8K requests with named evidence selection on the same CPU model."""

import argparse
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from random import Random
import re
from statistics import median
import subprocess
from time import perf_counter, time
from unittest.mock import patch

import torch

from scripts import build_p109c_authored_course as authored
from scripts import diag_p077_file_int8_staged24 as archived
from scripts.diag_p077_grounded_length_controls import PATTERNS, TOPICS


TAG = "p077_8k_section_cpu_20261125"
OUT = archived.OUT.with_name(TAG)
PROFILE = OUT.with_name(f"{TAG}_profile_retry1.json")
CPU = 14
GENERATE = 32
AUTHORIZED_END = datetime.fromisoformat("2026-11-25T13:00:00+09:00")
ARMS = ("short", "full4k", "full8k", "selected8k")
HEADER = "<|im_start|>user\n"
TAIL = "<|im_end|>\n<|im_start|>assistant\n"
files, native, trial, mapped = archived.files, archived.native, archived.trial, archived.mapped
SELECTOR = Path(__file__).with_name("p077_named_section_selector.hpp")
DRIVER = Path(__file__).with_name("p077_native_qbpe_request.cpp")


def digest(value):
    return sha256(value).hexdigest().upper()


def encode(tokenizer, text):
    return tokenizer.encode(text, add_special_tokens=False).ids


def filler(language, rng):
    choices = [(a, b) for a in TOPICS[language] for b in TOPICS[language] if a != b]
    rng.shuffle(choices)
    return [PATTERNS[language][i % len(PATTERNS[language])].format(a=a, b=b).strip()
            for i, (a, b) in enumerate(choices)]


def render_length(tokenizer, sections, target, question, sentences, location, limit):
    def at(count):
        before = (0, count // 2, count)[location]
        text = HEADER + "\n\n".join((*sentences[:before], *sections, *sentences[before:count]))
        text += f"\n\n[request {target}]\n" + question + TAIL
        return text, encode(tokenizer, text)

    low, high = 0, len(sentences)
    while low < high:
        middle = (low + high + 1) // 2
        if len(at(middle)[1]) + GENERATE - 1 <= limit:
            low = middle
        else:
            high = middle - 1
    text, ids = at(low)
    if not limit - 104 <= len(ids) <= limit - GENERATE + 1 or len(text.encode()) >= 65_537:
        raise ValueError("the independent background did not reach the sealed native input range")
    return dict(text=text, ids=ids)


def panel(tokenizer):
    full = []
    for language_index, language in enumerate(("ko", "en")):
        rng = Random(251125 + language_index)
        for index in range(6):
            target, distractor = f"ledger-{language_index}-{index}-a", f"ledger-{language_index}-{index}-b"
            values = rng.sample(range(1200, 9800), 8)
            gold_values, distracting = values[:4], values[4:]
            order = rng.sample(range(4), 4)
            lead = "작업표에는 다음과 같이 적혀 있습니다. " if language == "ko" else "The work log has these entries. "
            body, other = (lead + authored.values_text(language, values, order) for values in (gold_values, distracting))
            sections = (f"[section {target}]\n{body}\n[/section]",
                        f"[section {distractor}]\n{other}\n[/section]")
            if index % 2:
                sections = tuple(reversed(sections))
            if index < 4:
                question = authored.field_question(language, index, 2)
                gold = [str(gold_values[index])]
            else:
                question = ("표의 네 항목과 번호를 원문 순서대로 모두 한 줄에 다시 쓰세요."
                            if language == "ko" else "Write all four fields and numbers in the order in the record.")
                gold = [str(gold_values[field]) for field in order]
            short = HEADER + body + " " + question + TAIL
            sentences = filler(language, rng)
            lo, hi = [render_length(tokenizer, sections, target, question, sentences, index % 3, limit)
                      for limit in (4096, 8192)]
            full.append(dict(id=f"{language}{index}", language=language, location=index % 3, gold=gold,
                             short=dict(text=short, ids=encode(tokenizer, short)), full4k=lo, full8k=hi))
    return full


def driver_source():
    swap = native.port.replace_once
    data = DRIVER.read_bytes()
    data = swap(data, b'#include "p077_qbpe_generated.hpp"',
                b'#include "p077_qbpe_generated.hpp"\n#include "p077_named_section_selector.hpp"')
    data = swap(data, b"constexpr uint32_t generation = 8;", b"constexpr uint32_t generation = 32;")
    data = swap(data, b"input.size() + generation - 1 <= 4096", b"input.size() + generation - 1 <= 8192")
    data = swap(data, b"void encode(char* self, char* engine, char* model, char* archive_fd)",
                b"void encode(char* self, char* engine, char* model, char* archive_fd, bool select)")
    data = swap(data, b"        const auto input = tokenizer.encode(std::string_view(text.data(), bytes), scanner);",
                b"        const std::string_view raw(text.data(), bytes);\n"
                b"        const std::string selected = select ? p077::select_named_section(raw) : std::string{};\n"
                b"        const auto input = tokenizer.encode(select ? std::string_view(selected) : raw, scanner);")
    return swap(data, b'        if (argc == 5 && std::strcmp(argv[1], "encode") == 0) encode(argv[0],argv[2],argv[3],argv[4]);',
                b'        if (argc == 5 && (std::strcmp(argv[1], "encode") == 0 || std::strcmp(argv[1], "select") == 0))\n'
                b'            encode(argv[0],argv[2],argv[3],argv[4],std::strcmp(argv[1], "select") == 0);')


def prepare():
    prior, (identity, _, _, _, packed_source) = archived.prior.prepare()
    original = archived.render(packed_source)
    compiler = trial.read_json(archived.OUT / "width24" / "compiler.json")
    if digest(original) != compiler["source_sha256"]:
        raise ValueError("the regenerated width-24 file engine differs from the previous source")
    extended = native.port.replace_once(original, b"Limit = 4096;", b"Limit = 8192;")
    tokenizer, special, *_ = trial.load_cases()
    cases = panel(tokenizer)
    driver = driver_source()
    ancestor = prior["previous"]["prior"]["source_receipt"]["prior"]["prior"]
    fingerprint = ancestor["native"]["native"]["native"]["state_sha256"]
    codec_header = files.codec.OUT / "p077_qbpe_generated.hpp"
    profile = dict(tag=TAG, cpu=CPU, output_cap=GENERATE, model_state_sha256=fingerprint,
                   case_count=len(cases), stop=[special["<|im_end|>"], tokenizer.token_to_id("<eos>")],
                   cases_sha256=digest(json.dumps(cases, ensure_ascii=False, sort_keys=True).encode()),
                   inherited_compiler_sha256=trial.file_sha(archived.OUT / "width24" / "compiler.json"),
                   sources={p.name: trial.file_sha(p) for p in (Path(__file__), SELECTOR, DRIVER, codec_header)},
                   original=digest(original), extended=digest(extended), request_driver=digest(driver),
                   tokenizer_asset_sha256=trial.file_sha(files.codec.ASSET))
    return profile, identity, cases, original, extended, driver


def request(row, arm, driver, engine, model, archive, deadline):
    if (OUT / "STOP").exists() or time() >= deadline:
        raise TimeoutError("the authorized CPU requests reached the stop boundary")
    selected = arm == "selected8k"
    source = row["full8k" if selected else arm]
    expected = row["short" if selected else arm]["ids"]
    start = perf_counter()
    run = subprocess.run([driver, "select" if selected else "encode", engine, str(model), str(archive)],
                         input=source["text"].encode(), pass_fds=(model, archive), capture_output=True,
                         timeout=min(300, max(.1, deadline - time())))
    elapsed = perf_counter() - start
    if run.returncode:
        (OUT / f"{row['id']}_{arm}_error.txt").write_bytes(run.stderr)
        run.check_returncode()
    result = json.loads(run.stdout)
    if (result["encoding"]["ids"] != expected or result["encoding"]["pid"] != result["native_pid"]
            or result["decoding"]["pid"] != result["native_pid"]):
        raise ValueError("the native tokenizer, selection, or single-PID process differs from the profile")
    trial.publish(OUT / f"{row['id']}_{arm}.json", result)
    observed = result["native"]
    answer = result["decoding"]["text"].strip()
    returned = re.findall(r"\d+", answer)
    return dict(case=row["id"], language=row["language"], arm=arm, position=row["location"],
                gold=row["gold"], answer=answer, numeric_correct=returned == row["gold"],
                input_tokens=len(source["ids"]), model_tokens=len(expected), output_tokens=len(observed["ids"]),
                peak_rss=native.bounded.prior.peak(result), generated_ids=observed["ids"],
                elapsed=elapsed, first_seconds=observed["seconds"][0], decode_seconds=sum(observed["seconds"][1:]),
                scratch_bytes=observed["scratch_bytes"], model_bytes=observed["model_bytes"],
                **{k: v for k, v in observed.items() if k.startswith("kv_")})


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["arm"]].append(row)
    return {arm: dict(rows=len(group), correct=sum(row["numeric_correct"] for row in group),
                      max_rss=max(row["peak_rss"] for row in group), output_over_8=sum(row["output_tokens"] > 8 for row in group),
                      median_seconds=median(row["elapsed"] for row in group), max_kv_read=max(row["kv_read_bytes"] for row in group))
            for arm, group in groups.items()}


def run(profile, identity, cases, original, extended, driver_source_bytes, deadline):
    OUT.mkdir(exist_ok=False)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    driver_file, driver = OUT / "request.cpp", OUT / "request"
    driver_file.write_bytes(driver_source_bytes)
    subprocess.run(["/usr/bin/g++", "-std=c++17", "-O3", "-Wall", "-Wextra", "-Werror", "-I", str(files.codec.OUT),
                    "-I", str(files.codec.SCRIPTS), str(driver_file), "-ldl", "-o", str(driver)], check=True, timeout=80)
    engines = {}
    for arm, engine_source in (("4k", original), ("8k", extended)):
        directory = OUT / arm
        directory.mkdir()
        with patch.object(native.bounded, "OUT", directory):
            engines[arm] = native.bounded.build(engine_source, caps=(64,))[64][1]
    rows = []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            model = mapped.request.pack_model(stack, profile["model_state_sha256"], identity)
        archive = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for index, row in enumerate(cases):
            order = ARMS if index % 2 == 0 else reversed(ARMS)
            for arm in order:
                engine = engines["8k" if arm == "full8k" else "4k"]
                result = request(row, arm, driver, engine, model, archive, deadline)
                result["eot"] = result["generated_ids"][-1] in profile["stop"]
                rows.append(result)
                print(json.dumps({k: result[k] for k in ("case", "arm", "numeric_correct", "input_tokens", "peak_rss", "elapsed")}), flush=True)
    trial.publish(OUT / "report.json", dict(status="COMPLETE", profile=profile, rows=rows,
                                          request_binary_sha256=trial.file_sha(driver), summary=summarize(rows)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--profile-sha256")
    args = parser.parse_args()
    if os.sched_getaffinity(0) != {CPU} or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("pin CPU 14 and hide CUDA for the complete native request test")
    profile, *assets = prepare()
    if args.action == "prepare":
        trial.publish(PROFILE, profile)
        print(trial.file_sha(PROFILE), flush=True)
        return 0
    if (args.stop_by is None or args.stop_by.tzinfo is None or args.stop_by > AUTHORIZED_END
            or args.stop_by.timestamp() - time() < 180 or trial.read_json(PROFILE) != profile
            or args.profile_sha256 != trial.file_sha(PROFILE)):
        parser.error("run the frozen set under the approved CPU deadline")
    run(profile, *assets, args.stop_by.timestamp())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
