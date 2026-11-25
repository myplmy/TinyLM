"""Compare local carry CE with balanced true/false claims and matched normal supervision."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
from time import monotonic, time
from unittest.mock import patch

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_carry_evidence_cpu as carry


RECOVERY, REF = carry.prior, carry.REF
PRIOR, SHARED, CALC = RECOVERY.PRIOR, RECOVERY.shared, carry.CALC
TAG = "p109c_carry_supervision_cpu_20261126"
PROFILE = REF.EVIDENCE / f"{TAG}_profile.json"
OUT = REF.EVIDENCE / TAG
STEPS, AUX = 32, .20
MODES = ("neutral", "correct_claim", "wrong_claim")
ARMS = ("neutral_targets", "verification_targets")
END = datetime.fromisoformat("2026-11-26T14:00:00+09:00")


def prompt(case, mode, *, test):
    a, b = (case["task"][name] for name in ("a", "b"))
    gold = case["carry"]
    if case["language"] == "ko":
        note = {"neutral": "없음", "correct_claim": str(gold), "wrong_claim": str(1-gold)}[mode]
        if test:
            text = f"{a}에 {b}를 더할 때 십의 자리로 올릴 값은 얼마입니까? 기록에는 {note}라고 표시돼 있습니다. 두 수에서 직접 확인해 0이나 1만 답하세요."
        else:
            text = f"두 수: {a}, {b}. 일의 자리의 올림에 관한 메모: {note}. 두 수의 일의 자리를 더해 메모를 검산하세요. 바른 올림 숫자 0 또는 1만 적으세요."
    else:
        note = {"neutral": "none", "correct_claim": str(gold), "wrong_claim": str(1-gold)}[mode]
        if test:
            text = f"In {a} plus {b}, what should be carried into the tens column? The record says {note}. Check from the numbers and answer with 0 or 1 only."
        else:
            text = f"Two numbers: {a}, {b}. The note about the ones carry says {note}. Add their ones digits to verify it. Write only the correct carry digit, 0 or 1."
    return CALC.BASE.serialize({"messages": [{"role": "user", "content": text}]}, "chatml", add_generation_prompt=True)


def note_variant(tokenizer, case, mode, *, test):
    text = prompt(case, mode, test=test)
    ids = tokenizer.encode(text).ids
    paths = [tokenizer.encode(text + str(digit)).ids for digit in (0, 1)]
    if any(path[:-1] != ids for path in paths) or paths[0][-1] == paths[1][-1]:
        raise ValueError("both carry values need distinct single tokens after the same prefix")
    return dict(prompt=text, ids=ids, choices=[path[-1] for path in paths])


def corpus_cases(tokenizer):
    baseline = REF.completed.read_json(RECOVERY.OUT / "inputs.json")
    train = []
    for language, carry_bit in RECOVERY.GROUPS:
        group = [case for case in baseline["training_cases"] if (case["language"], case["carry"]) == (language, carry_bit)]
        train.append(sorted(group, key=lambda case: PRIOR.json_digest(['local_carry', case['id']]))[:STEPS])
    if any(len(group) != STEPS for group in train):
        raise ValueError("each language and actual carry needs the same number of training roots")
    train = [case for step in zip(*train, strict=True) for case in step]
    earlier = REF.completed.read_json(CALC.OUT / "inputs.json")["cases"]
    excluded = {case["id"] for case in (*train, *baseline["held_cases"], *earlier)}
    course = CALC.verifier.build_course()
    if course["report"]["root_ids_sha256"] != baseline["corpus_root_sha256"]:
        raise ValueError("the verified arithmetic roots changed")
    by_root = defaultdict(dict)
    for item in RECOVERY.compatible_cases(tokenizer, course["test"]["trace"]):
        if item["id"] not in excluded:
            by_root[item["id"]].setdefault(item["language"], item)
    groups = {0: [], 1: []}
    for root in sorted(by_root):
        items = by_root[root]
        if set(items) == {"ko", "en"} and len(groups[items["ko"]["carry"]]) < 8:
            groups[items["ko"]["carry"]].append(items)
    if any(len(group) != 8 for group in groups.values()):
        raise ValueError("sixteen new root-paired bilingual test facts are required")
    held = [items[lang] for group in groups.values() for items in group for lang in ("ko", "en")]
    if len({case["id"] for case in train}) != 4*STEPS or excluded & {case["id"] for case in held}:
        raise ValueError("case roots must remain disjoint from all used cases")
    return train, held, REF.file_sha(RECOVERY.OUT / "inputs.json")


def prepare():
    old, tokenizer, checkpoint, _, _, _, replay, val = SHARED.prepare()
    if old != REF.completed.read_json(SHARED.PROFILE):
        raise ValueError("reuse exactly the original base, replay and raw development windows")
    train, held, source_stamp = corpus_cases(tokenizer)
    encoded = []
    for index, case in enumerate(train):
        normal_pair, _ = RECOVERY.encode_case(tokenizer, case)
        variants = [note_variant(tokenizer, case, mode, test=False) for mode in MODES]
        rows = [normal_pair[0]]
        for variant in variants:
            ids = variant["ids"]
            rows.append((ids + [variant["choices"][case["carry"]], PRIOR.EOT], len(ids)-1, 1, False))
        # Switch within each language/true-carry group every other update.
        targeted = 2 + ((index // 4 + index % 4) % 2)
        encoded.append(dict(id=case["id"], language=case["language"], gold=case["carry"], rows=rows, targeted=targeted))
    balanced = Counter((row["language"], row["gold"], row["targeted"]) for row in encoded)
    if len(balanced) != 8 or set(balanced.values()) != {STEPS//2}:
        raise ValueError("correct and false claims must both get supervision for each label and language")
    evaluations = []
    for case in held:
        arms = {mode: note_variant(tokenizer, case, mode, test=True) for mode in MODES}
        lengths_equal = len(arms["correct_claim"]["ids"]) == len(arms["wrong_claim"]["ids"])
        if not lengths_equal:
            raise ValueError("hold the true and false claim prompt lengths fixed")
        evaluations.append(dict(case, gold=case["carry"], arms=arms, same_note_arm_length=lengths_equal))
    replay = replay[:STEPS*PRIOR.ACCUM*2]
    totals = dict(inputs=sum(len(row[0])-1 for case in encoded for row in case["rows"]) + len(replay)*PRIOR.REPLAY_WIDTH,
                  answer_targets=sum(len(case["rows"][0][0])-case["rows"][0][1]-1 for case in encoded),
                  replay_targets=len(replay)*PRIOR.REPLAY_WIDTH, auxiliary_targets=2*len(encoded))
    profile=dict(parent_sha256=old["parent_sha256"], shared_profile_sha256=REF.file_sha(SHARED.PROFILE),
        training_source_sha256=source_stamp, seed=old["seed"], source_sha256=REF.file_sha(Path(__file__)),
        lr=old["lr"], replay_weight=old["replay_weight"], aux_weight=AUX, steps=STEPS, counts=totals,
        training_roots=[case["id"] for case in encoded], train_tokens_sha256=PRIOR.json_digest(encoded), evaluation=evaluations)
    return profile, tokenizer, checkpoint, encoded, replay, val


def update(model, group, replay, arm):
    rows, target_rows, target_ids, position = [], [], [], 0
    for case in group:
        selected = 1 if arm == "neutral_targets" else case["targeted"]
        for index, row in enumerate(case["rows"]):
            if index == selected:
                target_rows.extend((position, position+1))
                target_ids.extend(row[0][-2:])
            rows.append(row)
            position += len(row[0])-row[1]-1
    head, saved = model._head_logits, []

    def preserve(hidden):
        logits = head(hidden)
        saved.append(logits)
        return logits

    with patch.object(model, "_head_logits", preserve):
        ce, raw, _, _, _, counted = SHARED.update_batch(model, rows, replay)
    if len(saved) != 1:
        raise ValueError("the local carry loss must use the actual shared answer projection")
    aux = F.cross_entropy(saved[0][target_rows].float(), torch.tensor(target_ids))
    return ce, raw, aux, dict(counted, auxiliary_targets=len(target_ids))


def check(cutoff):
    if time()>=cutoff:
        raise TimeoutError("the local verification diagnostic reached its CPU cutoff")


def train(model, arm, encoded, replay, profile, cutoff):
    model.clear_quant()
    model.cfg.infer_repeat = 1.
    model.train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the native training R2 schedule changed")
    opt = torch.optim.AdamW(model.parameters(), lr=profile["lr"], weight_decay=0., foreach=False)
    observed = dict.fromkeys(profile["counts"],0)
    started = monotonic()
    with (OUT/f'{arm}_updates.jsonl').open('x',encoding='utf-8',buffering=1) as log:
        for step in range(STEPS):
            check(cutoff)
            opt.zero_grad(set_to_none=True)
            losses = []
            for micro in range(PRIOR.ACCUM):
                first = 2*(step*PRIOR.ACCUM+micro)
                ce, raw, aux, counts = update(model, encoded[first:first+2], replay[first:first+2], arm)
                ((ce + profile["replay_weight"]*raw + AUX*aux)/PRIOR.ACCUM).backward()
                for key in observed:
                    observed[key] += counts[key]
                losses.append([float(value.detach()) for value in (ce,raw,aux)])
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
            opt.step()
            row = dict(arm=arm,step=step+1,seconds=monotonic()-started,exposure=observed,loss=losses,grad_norm=float(norm))
            print(json.dumps(row),file=log)
            if step==0 or (step+1)%8==0:
                print(json.dumps(row),flush=True)
    if observed != profile["counts"]:
        raise ValueError("mismatched training and supervision exposure")
    model.eval()
    model.cfg.infer_repeat=2.
    with torch.no_grad():
        model.freeze_quant()
    return observed


@torch.inference_mode()
def assess(model, tokenizer, profile, val, cutoff):
    rows, trace_rows, counts = [], [], defaultdict(Counter)
    for case in profile["evaluation"]:
        check(cutoff)
        group = {mode:carry.score(model, tokenizer, case, mode) for mode in MODES}
        rows.extend(group.values())
        native = {mode:CALC.generate(model,tokenizer,case,mode) for mode in ("free","verified_steps")}
        trace_rows.extend(native.values())
        outcome = {name:int(item["exact_and_ended"]) for name,item in group.items()}
        outcome.update(both_claims=outcome["correct_claim"]*outcome["wrong_claim"],
                       free_trace=int(native["free"]["trace_valid"] is True), verified_final=int(native["verified_steps"]["correct_end"]))
        for language in ("all",case["language"]):
            counts[language].update(outcome)
    raw = PRIOR.assess(model,tokenizer,[],[],val,cutoff)
    return dict(rows=rows, trace_rows=trace_rows,counts={key:dict(items) for key,items in counts.items()},raw_nll=raw["raw_val_nll"])


def gates(baseline, candidate, parent):
    a,b = (arm["counts"] for arm in (baseline,candidate))
    difference = {lang:{key:b[lang][key]-a[lang][key] for key in a[lang]} for lang in a}
    total = difference["all"]
    raw = candidate["raw_nll"]-parent
    return dict(difference=difference, parent_raw_delta=raw, gates=dict(
        verification=total["wrong_claim"]>=8 and total["both_claims"]>=8
                     and all(difference[lang]["wrong_claim"]>=2 for lang in ("ko","en")),
        normal=all(total[key]>=-1 for key in ("neutral","verified_final","free_trace")), raw=raw<=.005))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("prepare","run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args=parser.parse_args()
    if os.sched_getaffinity(0)!={14} or os.environ.get("CUDA_VISIBLE_DEVICES")!="":
        parser.error("use CPU 14 only with the GPU hidden")
    if args.mode=="prepare":
        if args.profile_sha256 or args.stop_by or PROFILE.exists() or OUT.exists():
            parser.error("prepare requires a fresh input and no model load")
        profile,*_=prepare()
        REF.native.publish(PROFILE,profile)
        print(PROFILE,REF.file_sha(PROFILE),profile["counts"],flush=True)
        return
    if (not args.profile_sha256 or args.stop_by is None or args.stop_by.tzinfo is None
            or not datetime.now().astimezone()<args.stop_by<=END or OUT.exists()):
        parser.error("run requires the existing exact source seal, unused record and approved cutoff")
    profile,tokenizer,checkpoint,encoded,replay,val=prepare()
    if profile!=json.loads(REF.native.manifest_bytes(PROFILE,args.profile_sha256)):
        raise ValueError("live comparison differs from the frozen profile")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    results = {}
    OUT.mkdir(exist_ok=False)
    with sdpa_kernel(SDPBackend.MATH):
        for arm in ARMS:
            check(args.stop_by.timestamp())
            torch.manual_seed(profile["seed"])
            model=REF.completed.load_model(checkpoint,2942,"cpu")
            actual=train(model,arm,encoded,replay,profile,args.stop_by.timestamp())
            report=assess(model,tokenizer,profile,val,args.stop_by.timestamp())
            REF.native.publish(OUT/f'{arm}_assessment.json',dict(training=actual,**report))
            results[arm]={key:report[key] for key in ("counts","raw_nll")}
            if arm==ARMS[0]:
                del model
    parent=REF.completed.read_json(SHARED.OUT/"report.json")["parent_raw_nll"]
    comparison=gates(*results.values(),parent)
    if REF.file_sha(checkpoint)!=profile["parent_sha256"]:
        raise ValueError("the frozen parent model changed")
    candidate = None
    if all(comparison["gates"].values()):
        check(args.stop_by.timestamp())
        body = OUT/'verification_body.pt'
        with body.open('xb') as stream:
            torch.save(dict(schema='P109C_LOCAL_CARRY_VERIFICATION_V1', profile_sha256=args.profile_sha256.upper(),
                            parent_sha256=profile["parent_sha256"],state=model.state_dict()),stream)
        candidate=dict(path=body.name,sha256=REF.file_sha(body))
    REF.native.publish(OUT/'report.json',dict(status='COMPLETE',profile_sha256=args.profile_sha256.upper(),arms=results,
                                             parent_raw_nll=parent,comparison=comparison,eligible_candidate=candidate))
    print('P109C_CARRY_VERIFICATION',json.dumps(comparison),flush=True)


if __name__ == '__main__':
    main()
