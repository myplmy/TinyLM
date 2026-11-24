"""Replace half the fixed replay with equivalent questions whose table value changed."""

import argparse
from datetime import datetime
import json
from pathlib import Path
from random import Random
import sys
from unittest.mock import patch

from scripts import run_p108_margin_write_replay as replay


TAG = "p108_counterfactual_write_replay_gpu_v1_20261121"
BASELINE_OUT,BASELINE_TAG = replay.OUT,replay.TAG
OUT = BASELINE_OUT.with_name(TAG)
trial = replay.trial
composition = replay.periodic.composition
original_prepare = replay.prepare


def matched_replay(tok,root,entry,excluded):
    messages = {view:tok.decode(ids,skip_special_tokens=False) for view,ids in entry["prompts"].items()}
    old_value = entry["gold"]
    rng = Random(int(root[:12],16))
    for _ in range(3000):
        value = str(rng.randrange(1000,9980))
        if value not in excluded and len(tok.encode(value).ids)==len(tok.encode(old_value).ids):
            break
    else:
        raise ValueError("no unused matching target token width was found")
    for view,old in messages.items():
        matches = [m for m in composition.VALUE.finditer(old) if m[1]==old_value]
        if len(matches)!=1:
            raise ValueError("the table's source value must occur exactly once")
        at = matches[0]
        messages[view] = [*tok.encode(old[:at.start(1)]+value+old[at.end(1):]).ids]
    counterfactual = dict(entry,gold=value,prompts=messages)
    return value,replay.authored_replay(tok,root+":"+value,counterfactual)


def replay_inputs():
    old, (tok,special,cases,profiles,dev,_,transfer) = original_prepare()
    original = BASELINE_OUT/"report.json"
    result = trial.read_json(original)
    terminal = trial.read_json(BASELINE_OUT/"supervisor.json")
    if result["plan"]!=old or terminal["returncode"] or terminal["stop_reason"]:
        raise ValueError("requires the completed same-value replay experiment")
    _,_,_,orders,_ = trial.load_cases()
    targets = {int(epoch):root for epoch,root in old["targets"].items()}
    rows,assignments = {},{}
    evaluated = [tuple(row["ids"]) for row in transfer]
    for root in sorted(targets.values()):
        entry = dev[root]
        unchanged = replay.authored_replay(tok,root,entry)
        raw = tok.decode(entry["prompts"]["single"],skip_special_tokens=False)
        forbidden = {match[1] for match in composition.VALUE.finditer(raw)}
        forbidden.update(row["wanted"] for row in transfer if row["root"]==root)
        first,records_first = matched_replay(tok,root,entry,forbidden)
        second,records_second = matched_replay(tok,root,entry,forbidden|{first})
        chosen = (unchanged[0],records_first[1],unchanged[2],records_second[3])
        if any(tuple(prefix) in evaluated for _,_,prefix in chosen):
            raise ValueError("counterfactual replay overlaps the sealed transfer requests")
        rows[root] = [(*record,entry["language"]) for record in chosen]
        assignments[root] = [entry["gold"],first,entry["gold"],second]
    schedule,changes = replay.build_schedule(cases,orders,rows,targets)
    comparable = ("epoch","index","replaced","targets","language")
    if ([tuple(row[k] for k in comparable) for row in changes]!=
            [tuple(row[k] for k in comparable) for row in old["slots"]]):
        raise ValueError("the replay format changed slot, language or target mass")
    plan = dict(old,tag=TAG,source_sha256=trial.file_sha(Path(__file__)),slots=changes,
                replay_sha256=replay.author.digest([(root,identifier,r.x,r.y) for root,records in rows.items()
                                                     for identifier,r,_,_ in records]),
                comparison_sha256=trial.file_sha(original),counterfactual_values=assignments)
    return plan,(tok,special,cases,profiles,dev,schedule,transfer)


def prepare():
    with patch.object(replay,"TAG",BASELINE_TAG):
        return replay_inputs()


def worker(profile,fraction):
    with patch.object(replay,"prepare",prepare), patch.object(replay,"OUT",OUT), patch.object(replay,"TAG",TAG):
        replay.worker(profile,fraction)


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
        parser.error("requires a sealed paired-replay plan and authorized cutoff")
    return replay.prior.owner.supervise(worker,(plan,),OUT,args.stop_by,
                                        authorization_end=replay.solver.AUTHORIZATION_END,min_seconds=420)


if __name__=="__main__":
    sys.exit(main())
