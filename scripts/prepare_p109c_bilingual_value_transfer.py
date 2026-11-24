"""Prepare paired Korean/English training tables from the verified authored cohort."""

import argparse
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from random import Random

import numpy as np

from scripts import run_p109c_first_answer_value_bridge as bridge


TAG = "p109c_bilingual_value_transfer_cpu_v1_20261121"
OUT = bridge.OUT.with_name(TAG)
trial, data, control, baseline = bridge.trial, bridge.data, bridge.control, bridge.baseline


def encode_row(row, tokenizer, pad):
    sample = data.encode_record(row, tokenizer, context=data.WIDTH)
    tokens = np.full(data.WIDTH, pad, dtype=np.uint16)
    labels = np.full(data.WIDTH, baseline.IGNORE, dtype=np.int16)
    tokens[:len(sample.x)] = sample.x
    labels[:len(sample.y)] = sample.y
    return tokens,labels


def create(deadline):
    if (OUT.exists() or not deadline.tzinfo or deadline > bridge.AUTHORIZATION_END
            or (deadline-datetime.now(deadline.tzinfo)).total_seconds() < 120):
        raise ValueError("requires a fresh authored CPU preparation in the active window")
    base = bridge.base_contract()
    tokenizer,special,(x,y,_),phases,_ = control.profile()
    if phases != base["stages"] or phases[-1]["stage"] != "wide":
        raise ValueError("the completed baseline was run on a different authored schedule")
    wide = phases[-1]
    start,size = wide["offset"],wide["rows"]
    if size % data.BATCH or data.BATCH % 2 or tuple(data.authored.LANGUAGES) != ("ko","en"):
        raise ValueError("expected an even batch with an English row after each Korean row")
    cut = slice(start,start+size)
    tokens,labels = x[cut].copy(),y[cut].copy()
    sites = np.empty((size,6),dtype=np.int16)
    choices = np.empty((size//2,4),dtype=np.int32)
    distinct = np.empty((size//2,4),dtype=bool)
    targets = np.empty(size//2,dtype=np.int8)
    pad = special["<pad>"]
    _,_,cases,_,_ = trial.load_cases()
    sources = data.source_keys(tokenizer,cases)
    rng = Random(data.PROFILE_SEED)
    data.eval_pairs(tokenizer,rng,11,100,sources)
    data.eval_pairs(tokenizer,rng,11,9980,sources)
    archived_digest = sha256()
    paired_digest = sha256()

    @lru_cache(maxsize=None)
    def first_piece(text):
        return tokenizer.encode(text,add_special_tokens=False).ids[0]

    for phase,low,high,count in data.STAGES:
        for i in range(count):
            values,order,field,_,language = data.draw(rng,i,low,high,sources)
            fingerprint = bytes.fromhex(data.authored.digest(["table_values",sorted(values)]))
            archived_digest.update(fingerprint)
            if phase != "wide" or language != "en":
                continue
            phrasing = (i//32)%2
            original,gold = data.form(values,order,field,"en",phrasing)
            translated,translation_gold = data.form(values,order,field,"ko",phrasing)
            if gold != translation_gold:
                raise ValueError("a translation changed the selected source value")
            actual_en,label_en = encode_row(original,tokenizer,pad)
            if not (np.array_equal(actual_en,tokens[i]) and np.array_equal(label_en,labels[i])):
                raise ValueError("the English paired side must preserve the exact archived training row")
            tokens[i-1],labels[i-1] = encode_row(translated,tokenizer,pad)
            for row,record in ((i-1,translated),(i,original)):
                prompt = data.generation_prompt(tokenizer,record)
                sites[row] = baseline.sites_from_prompt(tokenizer,prompt,gold)
            pair = i//2
            candidates = [first_piece(str(values[slot])) for slot in order]
            first_left,first_right = labels[i-1,int(sites[i-1,0])],labels[i,int(sites[i,0])]
            if first_left != first_right or first_left != candidates[int(sites[i,-1])] or sites[i,-1] != sites[i-1,-1]:
                raise ValueError("the main supervised first token is not a bilingual shared target")
            choices[pair] = candidates
            distinct[pair] = [piece not in candidates[:index] for index,piece in enumerate(candidates)]
            targets[pair] = candidates.index(int(first_left))
            paired_digest.update(fingerprint)
    if archived_digest.hexdigest() != trial.read_json(data.DATA/"preflight.json")["train_values_sha256"]:
        raise ValueError("the authored lineage could not be reconstructed")
    if not np.array_equal(sites[::2,-1],sites[1::2,-1]):
        raise ValueError("paired first-position metadata differs")
    end = special["<|im_end|>"]
    if np.any((labels==end).sum(axis=1)!=1):
        raise ValueError("expected exactly one normal end label per translation")
    context = control.prefix_labels(tokens,labels,pad)
    OUT.mkdir()
    payload = OUT/"wide_pairs.npz"
    with payload.open("xb") as file:
        np.savez_compressed(file,tokens=tokens,labels=labels,context=context,sites=sites,
                            options=choices,unique=distinct,targets=targets)
    result = dict(tag=TAG, source=trial.file_sha(Path(__file__)), base=base, inputs=trial.file_sha(payload),
                  paired_rows=size, pairs=size//2, number_groups=paired_digest.hexdigest(),
                  eligible=int((distinct.sum(axis=1)>1).sum()), answer_labels=int(np.count_nonzero(labels!=baseline.IGNORE)),
                  context_labels=int(np.count_nonzero(context!=baseline.IGNORE)), input_slots=int(tokens.size))
    trial.publish(OUT/"report.json",result)
    print(f"{size//2} paired tables; {result['answer_labels']} answer labels; {result['context_labels']} context labels",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by",required=True,type=datetime.fromisoformat)
    args = parser.parse_args()
    create(args.stop_by)


if __name__ == "__main__":
    main()
