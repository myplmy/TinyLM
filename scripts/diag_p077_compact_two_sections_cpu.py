"""Remove only the background from the archived P077 8K lookup cases."""

from argparse import ArgumentParser
from contextlib import ExitStack
from datetime import datetime
import os
from pathlib import Path
import re
from time import time
from unittest.mock import patch

import torch

from scripts import diag_p077_long_named_section_cpu as baseline


END = datetime.fromisoformat("2026-11-26T15:00:00+09:00")
OUT = baseline.OUT.with_name("p077_compact_two_sections_cpu_20261126")
REPORT_SHA256 = "A7A984533B225B1F6FE5080DBE7C7D416E8076E54376642F0C420A89CCDF32D7"
COMPACT_SHA256 = "658AA4B69C86729D1A5498A4AE116222E3D13AF4A0583F46A34BBAF412B63B2A"
SECTION = re.compile(r"\[section [^\n]+\]\n.*?\n\[/section\]", re.S)


def compact_cases(cases, rows, tokenizer, target_only):
    by_case = {row["case"]: row for row in rows if row["arm"] == "short"
               and row["numeric_correct"] and len(row["gold"]) == 1}
    if len(by_case) != 7:
        raise ValueError("the archived known-answer panel must contain seven cases")
    compact = []
    for case in cases:
        if case["id"] not in by_case:
            continue
        archived = baseline.trial.read_json(baseline.OUT / f"{case['id']}_full8k.json")
        source = case["full8k"]["text"]
        if archived["encoding"]["ids"] != case["full8k"]["ids"] or case["gold"] != by_case[case["id"]]["gold"]:
            raise ValueError("the archived request or its expected number differs")
        sections = SECTION.findall(source)
        before, marker, question = source.partition("\n\n[request ")
        if len(sections) != 2 or not marker or not before.startswith(baseline.HEADER):
            raise ValueError("expected exactly the two archived sections and request suffix")
        if target_only:
            target = question.split("]", 1)[0]
            sections = [section for section in sections if section.startswith(f"[section {target}]\n")]
            if len(sections) != 1:
                raise ValueError("the archived request must identify exactly one section")
        text = baseline.HEADER + "\n\n".join(sections) + marker + question
        ids = baseline.encode(tokenizer, text)
        if not len(case["short"]["ids"]) < len(ids) < 512:
            raise ValueError("the compact input must retain the second table in a short context")
        compact.append(dict(id=case["id"], language=case["language"], location=case["location"],
                            gold=case["gold"], compact=dict(text=text, ids=ids)))
    if len(compact) != len(by_case):
        raise ValueError("the compact cases differ from the archived known-answer panel")
    return compact


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--target-only", action="store_true", help="remove the distractor from the compact control")
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {baseline.CPU} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14, hide CUDA and provide a cutoff inside the November 26 authorization")
    deadline = args.stop_by.timestamp()
    trial = baseline.trial
    report_path = baseline.OUT / "report.json"
    if trial.file_sha(report_path).upper() != REPORT_SHA256:
        raise ValueError("the archived P077 report differs")
    archived = trial.read_json(report_path)
    profile, identity, cases, _, _, _ = baseline.prepare()
    if profile != archived["profile"]:
        raise ValueError("the archived tokenizer, panel or source changed")
    compiler = trial.read_json(baseline.OUT / "8k" / "compiler.json")
    if compiler["source_sha256"] != profile["extended"]:
        raise ValueError("the 8K engine source differs from the archived execution")
    engine = Path(compiler["binaries"]["64"][1]["path"])
    driver = baseline.OUT / "request"
    engine_sha, driver_sha = trial.file_sha(engine), trial.file_sha(driver)
    if engine_sha.upper() != compiler["binaries"]["64"][1]["sha256"].upper() or driver_sha != archived["request_binary_sha256"]:
        raise ValueError("an archived executable differs")

    tokenizer, *_ = trial.load_cases()
    panel = compact_cases(cases, archived["rows"], tokenizer, args.target_only)
    output = OUT.with_name("p077_compact_target_section_cpu_20261126") if args.target_only else OUT
    if args.target_only:
        previous = OUT / "inputs.json"
        if (trial.file_sha(previous).upper() != COMPACT_SHA256
                or trial.read_json(previous)["cases"] != compact_cases(cases, archived["rows"], tokenizer, False)):
            raise ValueError("the two-section control differs from the completed experiment")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    output.mkdir(exist_ok=False)
    seal = output / "inputs.json"
    trial.publish(seal, dict(previous_report_sha256=REPORT_SHA256, engine_sha256=engine_sha,
                             driver_sha256=driver_sha, previous_profile=profile, cases=panel,
                             previous_compact_sha256=COMPACT_SHA256 if args.target_only else None,
                             target_only=args.target_only, source_sha256=trial.file_sha(Path(__file__)),
                             stop_by=args.stop_by.isoformat(), required_correct=7))
    if time() >= deadline:
        raise TimeoutError("the compact control reached its authorized cutoff")
    results = []
    with (ExitStack() as stack, patch.object(baseline, "OUT", output),
          patch.object(baseline.mapped.request, "OUT", output)):
        model = baseline.mapped.request.pack_model(stack, profile["model_state_sha256"], identity)
        archive = os.open(baseline.files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for case in panel:
            row = baseline.request(case, "compact", driver, engine, model, archive, deadline)
            row["eot"] = row["generated_ids"][-1] in profile["stop"]
            results.append(row)
            print(row["case"], row["input_tokens"], row["answer"], row["numeric_correct"], row["eot"], flush=True)
    summary = baseline.summarize(results)
    decision = sum(row["numeric_correct"] and row["eot"] for row in results) == len(panel)
    trial.publish(output / "report.json", dict(status="COMPLETE", input_sha256=trial.file_sha(seal), rows=results,
                    summary=summary, passed=decision, advance_to_8k=decision and not args.target_only))
    print("P077_COMPACT_COMPLETE", summary, "passed", decision, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
