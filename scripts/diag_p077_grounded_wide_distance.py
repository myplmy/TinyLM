"""Measure length and evidence distance on the archived short-answer-capable G4."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys
from time import perf_counter

import torch

from scripts import diag_p077_long_choices as choices
from scripts import p109_cuda_owner as owner
from scripts import run_p109c_correction_grounded as grounded
from scripts import run_p109c_correction_scratch as trial
from scripts import run_p109c_table_value_link as foundation
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer


TAG = "p077_grounded_wide_distance_gpu_v1_20261121"
OUT = trial.DATA.parent / TAG
LENGTHS = (1024, 2048)
BATCH = 8


def parts(tokenizer, row, side):
    expected = row["prompts"][side]
    text = tokenizer.decode(expected, skip_special_tokens=False)
    question = foundation.data.authored.field_question(row["language"], row["field"], 2)
    split = text.rfind(question)
    encoding = tokenizer.encode(text)
    head = tokenizer.encode("<|im_start|>user\n", add_special_tokens=False).ids
    # The packed first question token includes its leading space.
    boundary = choices.token_boundary(encoding, len(text[:split].rstrip()))
    if (encoding.ids != expected or split < 1 or boundary is None or boundary <= len(head)
            or expected[:len(head)] != head):
        raise ValueError("the exact archived table and question could not be separated")
    return head, expected[len(head):boundary], expected[boundary:]


def prepare():
    proof = grounded.prepare()
    tok, special, _, _, _ = trial.load_cases()
    wide_path = foundation.OUT / "wide_eval.json"
    wide = trial.read_json(wide_path)
    wide_rows = wide["rows"]
    if len(wide_rows) != 64 or len({row["root"] for row in wide_rows}) != 64:
        raise ValueError("requires the entire archived wide split")
    fixtures = {}
    marks = []
    for row in wide_rows:
        divided = [parts(tok, row, side) for side in range(2)]
        left, right = divided
        if (left[0] != right[0] or left[2] != right[2] or len(left[1]) != len(right[1]) or left[1] == right[1]
                or row["gold"][0] == row["gold"][1]):
            raise ValueError("paired counterfactual inputs differ in their question or length")
        prompts = {}
        for length in LENGTHS:
            width = length - trial.GENERATION + 1
            task = {"ko": "kobest_copa", "en": "winogrande"}[row["language"]]
            filler = choices.filler_tokens(tok, task, width-len(row["prompts"][0]))
            for order in ("near", "far"):
                constructed = [h + (filler+t if order == "near" else t+filler) + q for h, t, q in divided]
                if any(len(prompt) != width for prompt in constructed):
                    raise ValueError("incorrect attention context size")
                prompts[f"{length}_{order}"] = constructed
        fixtures[row["root"]] = prompts
        marks.append(dict(root=row["root"], language=row["language"], short_tokens=len(row["prompts"][0]),
                          table_tokens=len(left[1]), table_offset=len(left[0]), question_tokens=len(left[2])))
    paths = (Path(__file__), Path(choices.__file__), trial.ROOT / "tinylm/model/modules.py")
    plan = dict(tag=TAG, source=proof, wide_sha256=trial.file_sha(wide_path),
                authored_input_sha256=foundation.data.authored.digest(fixtures), contexts=list(LENGTHS),
                prompt_index=marks, archived_short_both=wide["both_correct"],
                extra_sources={str(path.relative_to(trial.ROOT)):trial.file_sha(path) for path in paths})
    return plan, (tok, special, wide_rows, fixtures)


@torch.inference_mode()
def cached(model, tokenizer, special, prompts):
    if len({len(prompt) for prompt in prompts}) != 1:
        raise ValueError("one attention cache batch must have one real prefix length")
    x = torch.tensor(prompts, device="cuda")
    raw = [[] for _ in prompts]
    stopped = [False] * len(prompts)
    end = special["<|im_end|>"]
    bank = None
    with torch.autocast("cuda", dtype=torch.bfloat16):
        for _ in range(trial.GENERATION):
            logits, bank = model(x, past_kv=bank, use_cache=True, logits_last_only=True)
            x = logits.reshape(len(prompts), -1).argmax(-1)[:, None]
            for index, token in enumerate(x[:,0].tolist()):
                if not stopped[index]:
                    stopped[index] = token == end
                    if not stopped[index]:
                        raw[index].append(token)
            if all(stopped):
                break
    return [dict(answer=tokenizer.decode(tokens, skip_special_tokens=False).strip(), ids=tokens, eot=ended)
            for tokens, ended in zip(raw, stopped, strict=True)]


@torch.inference_mode()
def calibration(model, tokenizer, special, wide_rows):
    selected = []
    widths = set()
    for row in wide_rows:
        prompt = row["prompts"][0]
        if len(prompt) in widths:
            continue
        widths.add(len(prompt))
        x = torch.tensor([prompt], device="cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            first, bank = model(x, use_cache=True, logits_last_only=True)
            nxt = first.reshape(1, -1).argmax(-1)[:, None]
            second, _ = model(nxt, past_kv=bank, use_cache=True, logits_last_only=True)
            full = model(torch.cat((x,nxt),dim=1), return_hidden=True)
            reference = model._head_logits(full[:,-1:])
        value = cached(model,tokenizer,special,[prompt])[0]
        recomputed = trial.generate(model,tokenizer,special,[prompt])[0]
        selected.append(dict(root=row["root"], length=len(prompt),
                             second_max_absolute_error=float((second.float()-reference.float()).abs().max()),
                             same_second_argmax=int(second.argmax()) == int(reference.argmax()),
                             same_free_answer=value == recomputed, same_archive=recomputed == row["outputs"][0]))
        if len(selected) == 6:
            break
    if len(selected) < 2:
        raise ValueError("short prefill needs different real lengths")
    return selected


def worker(plan, fraction):
    torch.set_num_threads(1)
    checked, (tokenizer, special, wide_rows, fixtures) = prepare()
    if checked != plan:
        raise ValueError("the distance benchmark changed after preflight")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(foundation.OUT/"foundation.pt",weights_only=True,map_location="cpu")
    if trial.state_sha(state["model"]) != plan["source"]["state_sha256"]:
        raise ValueError("the short-answer reference weights changed")
    original = TMTConfig(**state["config"])
    model = TiedMLPTransformer(replace(original,max_seq_len=max(LENGTHS))).to("cuda")
    model.load_state_dict(state["model"])
    model.eval()
    short = calibration(model,tokenizer,special,wide_rows)
    decoder = cached if all(row["same_second_argmax"] and row["same_free_answer"] for row in short) else trial.generate
    print(json.dumps(dict(calibration=short, decoder=decoder.__name__)),flush=True)
    if not all(row["same_archive"] for row in short):
        raise ValueError("short generation did not reproduce the archived model path")
    summaries = []
    for arm in next(iter(fixtures.values())):
        start = perf_counter()
        label = [(row,side,prompt) for row in wide_rows for side,prompt in enumerate(fixtures[row["root"]][arm])]
        output = [answer for index in range(0,len(label),BATCH)
                  for answer in decoder(model,tokenizer,special,[entry[2] for entry in label[index:index+BATCH]])]
        rows = []
        for index,row in enumerate(wide_rows):
            answers = output[2*index:2*index+2]
            exact = [answer["eot"] and answer["answer"]==gold for answer,gold in zip(answers,row["gold"],strict=True)]
            rows.append(dict(root=row["root"],language=row["language"],gold=row["gold"],
                             short_both=row["both_correct"],both_correct=all(exact), exact=exact,answers=answers))
        counts = {lang:dict(pairs=len(selected), both=sum(row["both_correct"] for row in selected),
                            preserved=sum(row["both_correct"] and row["short_both"] for row in selected),
                            short=sum(row["short_both"] for row in selected),
                            individual=sum(sum(row["exact"]) for row in selected),
                            ended=sum(sum(answer["eot"] for answer in row["answers"]) for row in selected))
                  for lang in ("ko","en") if (selected := [r for r in rows if r["language"]==lang])}
        summary = dict(arm=arm, counts=counts, seconds=perf_counter()-start)
        trial.publish(OUT/f"{arm}.json",dict(summary,rows=rows))
        summaries.append(summary)
        print(json.dumps(summary),flush=True)
    trial.publish(OUT/"report.json",dict(preflight=plan,calibration=short, decoder=decoder.__name__, summaries=summaries,
                  temporal_max_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


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
        parser.error("run requires the matching receipt and stop time")
    return owner.supervise(worker,(plan,),OUT,args.stop_by,authorization_end=trial.CUTOFF,min_seconds=300)


if __name__=="__main__":
    sys.exit(main())
