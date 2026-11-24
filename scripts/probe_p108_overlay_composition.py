"""Compare matched tied edits and compose two protected output overlays."""

import argparse
from datetime import datetime
from itertools import zip_longest
import json
import math
from pathlib import Path
import re
import sys

import torch

from scripts import probe_p108_protected_output_overlay as added


TAG = "p108_overlay_composition_gpu_v1_20261121"
OUT = added.OUT.with_name(TAG)
prior,trial = added.prior,added.trial
SOURCE = added.OUT/"output_overlay.pt"
AUTHOR = added.first.followup.authored
TURN = "<|im_start|>user\n"
ENDING = "<|im_end|>\n<|im_start|>assistant\n"
VALUE = re.compile(r": ([0-9]+)")
PARAPHRASES = {
    "ko": (
        "앞선 답을 다시 확인해 주세요. {field} 항목에 적힌 현재 번호만 알려 주세요.",
        "이전 답과 관계없이 작업표에서 {field} 번호를 읽어서 숫자만 답해 주세요.",
        "표를 기준으로 답을 고쳐 주세요. 지금 {field} 항목은 몇 번인가요?",
        "다른 항목의 숫자를 옮기지 말고, {field}에 연결된 번호 하나를 적어 주세요.",
    ),
    "en": (
        "Please check that answer again. Give only the current number shown for {field}.",
        "Use the work log to answer again. What number is listed under {field}?",
        "Correct your earlier reply by reading the number assigned to {field} in the table.",
        "Read the entry for {field} rather than another entry. Return a single number.",
    ),
}


def novel_requests(tok,dev,targets):
    rows = []
    for root in targets:
        record = dev[root]
        lang,gold,foil = (record[key] for key in ("language","gold","foil"))
        raw = tok.decode(record["prompts"]["correction"],skip_special_tokens=False)
        prefix,last = raw.rsplit(TURN,1)
        fields = [name for i,name in enumerate(AUTHOR.FIELDS[lang]) if AUTHOR.field_question(lang,i,1) in last]
        if len(fields)!=1 or not last.endswith(ENDING):
            raise ValueError("the original correction must identify a single field")
        values = [item[1] for item in VALUE.finditer(prefix)]
        replacements = [value for value in values if value not in (gold,foil)]
        if len(values)!=4 or len(replacements)!=2 or values.count(gold)!=1:
            raise ValueError("the correction needs four distinct values and an unchanged foil")
        counterfactual = replacements[0]

        def swap(match):
            value = match[1]
            if value==gold:
                return f": {counterfactual}"
            if value==counterfactual:
                return f": {gold}"
            return match[0]

        alternative = VALUE.sub(swap,prefix)
        for style in PARAPHRASES[lang]:
            prompt = TURN+style.format(field=fields[0])+ENDING
            for family,table,wanted in (("same_value",prefix,gold),("different_value",alternative,counterfactual)):
                ids = tok.encode(table+prompt).ids
                if len(ids)+trial.GENERATION>trial.WIDTH:
                    raise ValueError("the new expression exceeded the sealed runtime window")
                rows.append(dict(root=root,language=lang,family=family,wanted=wanted,prompt=table+prompt,ids=ids))
    return rows


def prepare():
    profile,data,original = added.prepare()
    file = added.OUT/"report.json"
    old = trial.read_json(file)
    terminal = trial.read_json(added.OUT/"supervisor.json")
    final = old["final"]
    if (old["plan"]!=profile or terminal["returncode"] or terminal["stop_reason"]
            or not final.get("same_prior_correct") or not SOURCE.is_file()):
        raise ValueError("requires the verified output-only experiment")
    choices = {}
    for case in old["attempts"]:
        admitted = [row["candidate"] for row in case["runs"]
                    if row.get("protected_sequences_unchanged") and row.get("development_sequences_unchanged")]
        if admitted:
            choices[case["root"]] = min(admitted,key=lambda c:c["norm_ratio"])
    if len(choices)!=2 or final["overlay"]!=choices[final["target"]]:
        raise ValueError("the completed experiment must provide two distinct successful edits")
    tok,_,_,_,_,dev = data
    wording = novel_requests(tok,dev,sorted(choices))
    return dict(tag=TAG,source_sha256=trial.file_sha(Path(__file__)),overlay_report_sha256=trial.file_sha(file),
                winning_sidecar_sha256=trial.file_sha(SOURCE),choices=choices,overlay=profile,
                wording_sha256=AUTHOR.digest(wording),wording_count=len(wording)),(data,original,wording,final)


def reconstruct(model,profile,original,dev,guards,end):
    deltas = {}
    for root,choice in profile["choices"].items():
        before = original[root]
        device_keys,device_scores,labels = prior.projected(model,dev[root]["records"]["correction"])
        actual = before["ids"]+([end] if before["eot"] else [])
        i = next(index for index,(a,b) in enumerate(zip_longest(labels.tolist(),actual)) if a!=b)
        wanted,rival = int(labels[i]),actual[i]
        if int(device_scores[i].argmax())!=rival:
            raise ValueError("the original greedy divergence moved")
        base_norm = float(model.emb.weight[rival if wanted==end else wanted].detach().norm())
        candidates = added.candidates(device_keys[i].double().cpu(),device_scores[i].double().cpu(),wanted,rival,end,
                                      guards,base_norm,profile["overlay"]["target_margin"])
        matched = [(candidate,delta) for candidate,delta in candidates if delta is not None and
                   candidate["pattern"]==choice["pattern"] and candidate["geometry"]==choice["geometry"]]
        if len(matched)!=1 or matched[0][0]["tokens"]!=choice["tokens"] or not math.isclose(matched[0][0]["norm"],choice["norm"],abs_tol=1e-7):
            raise ValueError("the previous admitted edit did not reproduce")
        deltas[root] = matched[0][1]
    return deltas


def run_wording(model,tok,special,wording):
    outputs = []
    for i in range(0,len(wording),trial.BATCH):
        batch = wording[i:i+trial.BATCH]
        answers = trial.generate(model,tok,special,[r["ids"] for r in batch])
        for row,answer in zip(batch,answers,strict=True):
            outputs.append(dict(root=row["root"],family=row["family"],wanted=row["wanted"],**answer,
                                exact=answer["eot"] and answer["answer"]==row["wanted"]))
    return outputs


def worker(profile,fraction):
    torch.set_num_threads(1)
    checked,((tok,special,cases,_,_,dev),original,wording,previous_final) = prepare()
    if checked!=profile:
        raise ValueError("the composition changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(added.first.CHECKPOINT,weights_only=True,map_location="cpu")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**state["config"])).to("cuda").eval()
    model.load_state_dict(state["model"])
    expected = profile["overlay"]["reference"]["state_sha256"]
    if trial.state_sha(model.state_dict())!=expected:
        raise ValueError("wrong unedited model state")
    manifest = profile["overlay"]["reference"]["setup"]
    control = trial.read_json(prior.CONTROL)
    guard = {root:cases["validation"][root] for root in manifest["guard"]}
    guard_before = dict(rows={root:control["validation"]["rows"][root] for root in guard})
    kept = prior.existing_answers(guard_before)
    bounds,_ = added.observed_guards(model,guard,guard_before)
    deltas = reconstruct(model,profile,original,dev,bounds,special["<|im_end|>"])
    archived = torch.load(SOURCE,weights_only=True,map_location="cpu")
    winner = previous_final["target"]
    if (archived["ids"]!=profile["choices"][winner]["tokens"] or archived["body_sha256"]!=expected or
            not torch.equal(archived["delta"],deltas[winner].half())):
        raise ValueError("recomputation differs from the archived successful overlay")

    comparisons = {}
    for root,choice in profile["choices"].items():
        table = model.emb.weight
        indices = choice["tokens"]
        stored = table[indices].detach().clone()
        base_keys,_,_ = prior.projected(model,dev[root]["records"]["correction"])
        try:
            with torch.no_grad():
                table[indices] = stored+deltas[root].to(stored)
            model.clear_quant()
            changed_keys,_,_ = prior.projected(model,dev[root]["records"]["correction"])
            evaluated = trial.evaluate(model,tok,special,{root:dev[root]})["rows"][root]
            after = trial.evaluate(model,tok,special,guard)
            comparisons[root] = dict(gold=dev[root]["gold"],shared=evaluated["correction"],
                                     shared_correct=prior.correct(evaluated,"correction"),
                                     shared_key_max_abs=float((changed_keys-base_keys).abs().max()),
                                     shared_protected=added.identical_sequences(guard_before,after,kept))
        finally:
            with torch.no_grad():
                table[indices] = stored
            model.clear_quant()
    if trial.state_sha(model.state_dict())!=expected:
        raise ValueError("the tied ablation did not restore the original checkpoint")

    ids = [token for root in profile["choices"] for token in profile["choices"][root]["tokens"]]
    if len(set(ids))!=len(ids):
        raise ValueError("the two admitted sidecars use overlapping output rows")
    delta = torch.cat([deltas[root] for root in profile["choices"]])
    fit = {root:dev[root] for root in deltas}
    audit = {root:cases["validation"][root] for root in manifest["audit"]}
    before_audit = dict(rows={root:control["validation"]["rows"][root] for root in audit})
    wording_base = run_wording(model,tok,special,wording)
    dev_before = trial.evaluate(model,tok,special,dev)
    with added.overlay(model,ids,delta):
        targets = trial.evaluate(model,tok,special,fit)
        after = trial.evaluate(model,tok,special,guard)
        after_audit = trial.evaluate(model,tok,special,audit)
        wording_candidate = run_wording(model,tok,special,wording)
        joined = dict(targets=targets,protected=added.identical_sequences(guard_before,after,kept),
                      audit=added.identical_sequences(before_audit,after_audit,prior.existing_answers(before_audit)),
                      ids=ids,fp16_bytes=delta.numel()*2)
        if (all(prior.correct(row,"correction") for row in targets["rows"].values())
                and joined["protected"] and joined["audit"]):
            dev_after = trial.evaluate(model,tok,special,dev)
            joined["development_protected"] = added.identical_sequences(dev_before,dev_after,prior.existing_answers(dev_before))
            if joined["development_protected"]:
                test = trial.evaluate(model,tok,special,cases["test"])
                joined.update(test=test,same_prior_correct=added.identical_sequences(control["test"],test,
                              prior.existing_answers(control["test"])))
    saved = None
    if joined.get("same_prior_correct") and all(not a["exact"] or b["exact"] for a,b in zip(wording_base,wording_candidate,strict=True)):
        saved = OUT/"joined_overlay.pt"
        with saved.open("xb") as file:
            torch.save(dict(ids=ids,delta=delta.half(),body_sha256=expected),file)
    if trial.state_sha(model.state_dict())!=expected:
        raise ValueError("the composition changed the original tensor state")
    trial.publish(OUT/"report.json",dict(plan=profile,comparisons=comparisons,joined=joined,wording=wording,
                  wording_base=wording_base,wording_candidate=wording_candidate,
                  saved_sha256=trial.file_sha(saved) if saved else None))
    print(json.dumps(dict(shared=[x["shared_correct"] for x in comparisons.values()],
                          targets=joined["targets"]["totals"],protected=joined["protected"],
                          audit=joined["audit"],test=joined.get("test",{}).get("totals"),
                          base=sum(x["exact"] for x in wording_base),candidate=sum(x["exact"] for x in wording_candidate),
                          saved=bool(saved))),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args = parser.parse_args()
    plan, _ = prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("requires the sealed comparison and an authorized cutoff")
    return prior.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=added.AUTHORIZATION_END,min_seconds=180)


if __name__ == "__main__":
    sys.exit(main())
