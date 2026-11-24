"""Separate irrelevant context length, content repetition, and RoPE positions."""

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
from random import Random
import sys

import torch

from scripts import diag_p077_grounded_wide_distance as wide


trial = wide.trial
TAG = "p077_grounded_length_controls_gpu_v1_20261121"
OUT = wide.OUT.with_name(TAG)
DOSES = (128, 256, 512)
LIMIT = 2048
TOPICS = {
    "en": ("wool", "copper", "willow", "clay", "sandstone", "fern", "brass", "maple", "velvet", "quartz",
           "chalk", "granite", "cotton", "bark", "marble", "glass", "slate", "linden", "paper", "moss"),
    "ko": ("양모", "구리", "버드나무", "찰흙", "사암", "고사리", "황동", "단풍나무", "벨벳", "석영",
           "분필", "화강암", "무명천", "나무껍질", "대리석", "유리", "점판암", "피나무", "종이", "이끼"),
}
PATTERNS = {
    "en": ("The exhibition contrasted {a} with {b}, focusing on their surface texture and reflected light. ",
           "The shaded courtyard displayed {a} beside {b}. A caption described the origin and texture. ",
           "Someone sketched the edge of {a} and the irregular surface of {b} on a sheet of paper. "),
    "ko": ("전시에서는 {a}와 {b}를 나란히 배치해 표면의 질감과 빛 반사를 관찰할 수 있었다. ",
           "그늘진 마당에 {a}와 {b}를 놓았다. 짧은 설명문에는 재료의 기원과 질감이 적혀 있었다. ",
           "관람객이 종이에 {a}의 가장자리와 {b}의 고르지 않은 표면을 그려 보았다. "),
}


def diverse_filler(tokenizer, language, count):
    rng = Random(48148)
    terms = TOPICS[language]
    pairs = [(a,b) for a in terms for b in terms if a != b]
    rng.shuffle(pairs)
    lines = [PATTERNS[language][i%3].format(a=a,b=b) for i,(a,b) in enumerate(pairs[:192])]
    encode = lambda text: tokenizer.encode(text,add_special_tokens=False).ids
    start, end = encode("\n\n---\n"), encode("\n---\n\n")
    body = encode("".join(lines))
    size = count-len(start)-len(end)
    if not 0 < size <= len(body):
        raise ValueError("insufficient nonrepeated filler")
    return start + body[:size] + end


def prepare():
    initial, (tokenizer, special, rows, initial_inputs) = wide.prepare()
    report_file = wide.OUT / "report.json"
    report = trial.read_json(report_file)
    done = trial.read_json(wide.OUT / "supervisor.json")
    if (report["preflight"] != initial or report["decoder"] != "cached" or done["returncode"] or done["stop_reason"]
            or any(a["counts"][lang]["individual"] for a in report["summaries"] for lang in ("en","ko"))):
        raise ValueError("requires the completed matching noncompressed long-context reference")
    fixtures = {"shift_only": [p for row in rows for p in row["prompts"]]}
    for context in (*DOSES,LIMIT):
        for order in ("near","far"):
            name = f"{context}_{order}" if context != LIMIT else f"{context}_{order}_diverse"
            prompts = []
            for row in rows:
                short = row["prompts"]
                width = context-trial.GENERATION+1
                amount = width-len(short[0])
                task = {"ko":"kobest_copa","en":"winogrande"}[row["language"]]
                filler = (diverse_filler(tokenizer,row["language"],amount) if context==LIMIT else
                          wide.choices.filler_tokens(tokenizer,task,amount))
                for side in range(2):
                    head, table, query = wide.parts(tokenizer,row,side)
                    prompt = head + (filler+table if order=="near" else table+filler) + query
                    if len(prompt)!=width:
                        raise ValueError("wrong controlled context size")
                    prompts.append(prompt)
            fixtures[name] = prompts
    for order in ("near","far"):
        arm = f"{LIMIT}_{order}"
        fixtures[arm+"_interpolated"] = [p for row in rows for p in initial_inputs[row["root"]][arm]]
    plan = dict(tag=TAG, source=initial, reference_sha256=trial.file_sha(report_file),
                sources={"launcher_sha256":trial.file_sha(Path(__file__))},
                input_sha256=wide.foundation.data.authored.digest(fixtures), arms=list(fixtures))
    return plan, (tokenizer,special,rows,fixtures)


def batches(decode, prompts):
    return [output for start in range(0,len(prompts),wide.BATCH) for output in decode(prompts[start:start+wide.BATCH])]


def worker(plan, fraction):
    torch.set_num_threads(1)
    verified, (tokenizer,special,rows,fixtures) = prepare()
    if verified != plan:
        raise ValueError("the controlled context inputs changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(wide.foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if trial.state_sha(state["model"]) != plan["source"]["source"]["state_sha256"]:
        raise ValueError("unexpected common reference weights")
    cfg = wide.TMTConfig(**state["config"])
    model = wide.TiedMLPTransformer(replace(cfg,max_seq_len=LIMIT)).to("cuda")
    model.load_state_dict(state["model"])
    model.eval()
    original_cos, original_sin = model.rope_cos, model.rope_sin
    inv = 1 / (cfg.rope_theta**(torch.arange(0,cfg.head_dim,2,device="cuda").float()/cfg.head_dim))
    angles = torch.outer(torch.arange(LIMIT,device="cuda").float()*(cfg.max_seq_len/LIMIT),inv)
    interpolated = (angles.cos(),angles.sin())
    summaries = []

    def decode(prompts):
        return wide.cached(model,tokenizer,special,prompts)

    for arm,prompts in fixtures.items():
        model.rope_cos, model.rope_sin = interpolated if arm.endswith("interpolated") else (original_cos,original_sin)
        if arm=="shift_only":
            groups = {}
            for i,prompt in enumerate(prompts):
                groups.setdefault(len(prompt),[]).append(i)
            answers = [None]*len(prompts)
            for length,indices in groups.items():
                shift = LIMIT-trial.GENERATION+1-length
                model.rope_cos, model.rope_sin = original_cos[shift:],original_sin[shift:]
                generated = batches(decode,[prompts[i] for i in indices])
                for i,result in zip(indices,generated,strict=True):
                    answers[i] = result
        else:
            answers = batches(decode,prompts)
        records = []
        for i,row in enumerate(rows):
            made = answers[2*i:2*i+2]
            exact = [a["eot"] and a["answer"]==g for a,g in zip(made,row["gold"],strict=True)]
            records.append(dict(root=row["root"],language=row["language"],gold=row["gold"],both=all(exact),exact=exact,
                                kept=row["both_correct"] and all(exact),same_ids=made==row["outputs"],answers=made))
        counts = {lang:dict(both=sum(r["both"] for r in records if r["language"]==lang),
                            kept=sum(r["kept"] for r in records if r["language"]==lang),
                            individual=sum(sum(r["exact"]) for r in records if r["language"]==lang)) for lang in ("ko","en")}
        summary = dict(arm=arm,counts=counts,identical_short_pairs=sum(r["same_ids"] for r in records),
                       frequent=Counter(a["answer"] for r in records for a in r["answers"]).most_common(2))
        trial.publish(OUT/f"{arm}.json",dict(summary, rows=records))
        summaries.append(summary)
        print(json.dumps(summary,ensure_ascii=False),flush=True)
    trial.publish(OUT/"report.json",dict(preflight=plan,summaries=summaries))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("check","run"))
    parser.add_argument("--receipt",type=Path)
    parser.add_argument("--stop-by",type=datetime.fromisoformat)
    args=parser.parse_args()
    plan,_=prepare()
    if args.mode=="check":
        print(json.dumps(plan,indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt)!=plan:
        parser.error("run requires the exact preflight and time bound")
    return wide.owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=120)


if __name__=="__main__":
    sys.exit(main())
