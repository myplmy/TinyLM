"""Vary only a nearby assignment note in the fixed P077 two-source questions."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p077_linked_tables as linked


TAG = "p077_linked_tables_bridge_cpu_v1_20261124"
OUT = linked.OUT.with_name(TAG)
ARMS = ("correct_note", "unrelated_note", "conflicting_note")
files, native, trial, mapped = linked.files, linked.native, linked.trial, linked.mapped


def notes(language, field, alternate):
    fmt, target, decoy = (("확인 기록: {item}의 지정 항목은 {field}입니다.", "야간 점검", "주간 점검")
                           if language == "ko" else
                           ("Confirmation: The field assigned to the {item} is {field}.", "overnight audit", "daytime audit"))
    return dict(correct_note=fmt.format(item=target, field=field),
                unrelated_note=fmt.format(item=decoy, field=field),
                conflicting_note=fmt.format(item=target, field=alternate))


def fixtures(tokenizer, rows):
    index = {(r["language"], r["order"], r["assignment"], r["inventory"]): r for r in rows}
    ready = []
    for row in rows:
        language = row["language"]
        other = index[(language, row["order"], 1 - row["assignment"], row["inventory"])]
        suffix = linked.LANGUAGES[language][-1] + linked.TAIL
        text = row["prompt"]["both"]["text"]
        if not text.endswith(suffix) or other["field"] == row["field"] or other["gold"] == row["gold"]:
            raise ValueError("the two source views and the alternative assignment must reproduce")
        prefix = text[:-len(suffix)]
        prompts = {}
        for arm, note in notes(language, row["field"], other["field"]).items():
            altered = prefix + note + "\n\n" + suffix
            ids = linked.encode(tokenizer, altered)
            if (any(c.isdecimal() for c in note) or len(ids) > 896
                    or tokenizer.decode(ids, skip_special_tokens=False) != altered):
                raise ValueError("the assignment note must add no numbers and preserve the bounded UTF-8 path")
            prompts[arm] = dict(ids=ids, text=altered)
        ready.append(dict(case=row["case"], language=language, order=row["order"], assignment=row["assignment"],
                          inventory=row["inventory"], gold=row["gold"], alternate_gold=other["gold"], prompt=prompts))
    if len({tuple(p["ids"]) for row in ready for p in row["prompt"].values()}) != len(ready) * len(ARMS):
        raise ValueError("all new prompt conditions must be distinct")
    return ready


def prepare():
    prior, (identity, cli, rows, engine) = linked.prepare()
    report_path = linked.OUT / "report.json"
    report = trial.read_json(report_path)
    if report["profile"] != prior or report["distinct_requests"] != 40:
        raise ValueError("the archived comparison must use the exact same engine and panel")
    tokenizer, *_ = trial.load_cases()
    ready = fixtures(tokenizer, rows)
    encoded = json.dumps(ready, ensure_ascii=False, sort_keys=True).encode("utf-8")
    plan = dict(tag=TAG, source_sha256=trial.file_sha(Path(__file__)), previous_result=trial.file_sha(report_path),
                previous=prior, panel_sha256=sha256(encoded).hexdigest().upper(), mode="SHORT_SAME_TASK", arms=list(ARMS),
                token_counts={arm: sorted({len(row["prompt"][arm]["ids"]) for row in ready}) for arm in ARMS})
    return plan, (identity, cli, ready, engine)


def summarize(rows):
    answer = {}
    for arm in ARMS:
        result = {}
        for language in linked.LANGUAGES:
            subset = [row for row in rows if row["arm"] == arm and row["language"] == language]
            answer_by = {(row["order"], row["inventory"], row["assignment"]): row for row in subset}
            if len(answer_by) != 8:
                raise ValueError("all eight matched conditions per language are required")
            flips = [(answer_by[(order, inventory, 0)], answer_by[(order, inventory, 1)])
                     for order in (0, 1) for inventory in (0, 1)]
            result[language] = dict(exact=sum(row["exact"] for row in subset), eot=sum(row["eot"] for row in subset),
                                    alternative_exact=sum(row["alternative_exact"] for row in subset),
                                    changed_assignment=sum(a["answer"] != b["answer"] for a, b in flips),
                                    both_assignments_correct=sum(a["exact"] and b["exact"] for a, b in flips))
        answer[arm] = result
    return answer


def run(profile, deadline):
    expected, (identity, cli, rows, engine) = prepare()
    if (profile != expected or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or deadline.tzinfo is None or deadline > files.AUTHORIZATION_END
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 120):
        raise ValueError("requires the sealed CPU-only model window")
    prior = profile["previous"]
    os.sched_setaffinity(0, {prior["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    with patch.object(linked, "OUT", OUT):
        binary = linked.engine_path(engine, prior)
    output = []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            ancestor = prior["previous"]["previous"]["prior"]["source_receipt"]["prior"]["prior"]
            digest = ancestor["native"]["native"]["native"]["state_sha256"]
            model = mapped.request.pack_model(stack, digest, identity)
        archive = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for i, row in enumerate(rows):
            order = ARMS[i % len(ARMS):] + ARMS[:i % len(ARMS)]
            for arm in order:
                req = dict(row["prompt"][arm], case=row["case"])
                got, elapsed = files.request(OUT, req, arm, cli, binary, model, archive, deadline)
                answer = got["decoding"]["text"].strip()
                ids = got["native"]["ids"]
                eot = ids[-1] == prior["stop"][0]
                output.append(dict({key: value for key, value in row.items() if key != "prompt"}, arm=arm,
                                   ids=ids, answer=answer, eot=eot, exact=eot and answer == row["gold"],
                                   alternative_exact=eot and answer == row["alternate_gold"], elapsed=elapsed))
    summary = summarize(output)
    trial.publish(OUT / "report.json", dict(profile=profile, summaries=summary, results=output))
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        plan, _ = prepare()
        trial.publish(args.receipt, plan)
        print(trial.file_sha(args.receipt), plan["token_counts"], flush=True)
        return 0
    if args.stop_by is None:
        parser.error("an authorized time boundary is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
