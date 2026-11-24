"""Compare repeat and switch supervision with balanced labels on the existing SODA split."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import eval_p109b_soda_speaker_switch as previous
from scripts import eval_p109c_completed as native
from scripts.p106b_shards import verify
from tinylm.infer.generate import sample


INPUT = previous.source.OUT
TAG = "p106b_soda_speaker_adapter_repeat_switch_cpu_v1_20261123"
ARTIFACT = previous.ROOT / "test_result/evidence" / TAG
RANK, UPDATES, BATCH, MAX_NEW = 8, 80, 8, 20
EOT = "<|im_end|>"


def cases_and_pins():
    pins, tokenizer, prior_holdout = previous.inputs()
    manifest = json.loads((INPUT / "candidate_shards_manifest.json").read_text(encoding="utf-8"))
    verify(INPUT, manifest)
    pools = {"candidate_train": [], "heldout": []}
    for shard in manifest["shards"]:
        with (INPUT / shard["path"]).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                meta = row["meta"]
                if meta["original_source_split"] != "train" or meta["source_license"] != "CC-BY-4.0":
                    raise ValueError("the admitted official TRAIN source and attribution are required")
                messages = [item["content"][0]["text"] for item in row["messages"]]
                context, marker, quote = messages[0].rpartition("\n\nWho says this exact utterance? ")
                second = messages[2].removeprefix("Refer to the same dialogue for a different speaker. ")
                names = meta["target_labels"]
                if not marker or len(set(names)) != 2 or names != [messages[1], messages[3]]:
                    raise ValueError("the validated speaker labels and quote prompts differ")
                questions = ["Who says this exact utterance? " + quote, second]
                case = dict(root=meta["source_group_id"], context=context, questions=questions, names=names)
                pools[meta["independent_candidate_split"]].append(case)
    if ([len(rows) for rows in pools.values()] != [171, 52]
            or len({row["root"] for rows in pools.values() for row in rows}) != 223
            or [row["root"] for row in pools["heldout"]] != [row["root"] for row in prior_holdout]):
        raise ValueError("the existing frozen source split changed")
    pins.add(Path(__file__))
    return pins, tokenizer, pools


def user_prompt(case, first, last):
    dialog = previous.first_use.dialog
    front = dialog(case["context"] + "\n\n" + case["questions"][first])
    return front + case["names"][first] + EOT + "\n" + dialog(case["questions"][last])


def features(model, tok, prompt, answer):
    prefix = tok.encode(prompt).ids
    encoded = tok.encode(prompt + answer + EOT).ids
    target = encoded[len(prefix):]
    if encoded[:len(prefix)] != prefix or len(encoded) > model.cfg.max_seq_len or target[-1] != 4:
        raise ValueError("the projected answer does not retain the ChatML assistant boundary")
    x = torch.tensor([encoded[:-1]], dtype=torch.long)
    with torch.no_grad():
        hidden = model(x, return_hidden=True)[0, -len(target):].clone()
    return hidden, torch.tensor(target, dtype=torch.long)


class Residual(torch.nn.Module):
    def __init__(self, width):
        super().__init__()
        self.down = torch.nn.Linear(width, RANK, bias=False)
        self.up = torch.nn.Linear(RANK, width, bias=False)
        torch.nn.init.zeros_(self.up.weight)

    def forward(self, values):
        return values + self.up(self.down(values))


def train(model, examples, picks, check, *, switch_examples=None):
    torch.manual_seed(31415)
    adapter = Residual(model.cfg.dim)
    opt = torch.optim.AdamW(adapter.parameters(), lr=.002, weight_decay=.01)
    losses = []
    for step, indices in enumerate(picks):
        check()
        mixed = [switch_examples[i] if switch_examples is not None and (step + j) % 2 else examples[i]
                 for j, i in enumerate(indices)]
        rows, labels = zip(*mixed)
        h, y = torch.cat(rows), torch.cat(labels)
        loss = F.cross_entropy(model._head_logits(adapter(h)), y)
        if not torch.isfinite(loss):
            raise ValueError("speaker adapter optimization has nonfinite loss")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach()))
    return adapter.eval(), losses


def generate(model, tok, case, prompt, expected):
    ids = tok.encode(prompt).ids
    if len(ids) + MAX_NEW > model.cfg.max_seq_len:
        raise ValueError("the independent prompt exceeds the native context")
    capture = previous.first_use.DecodeSuffix(tok, ids)
    answer, meta = sample(model, model.cfg, capture, prompt, max_new=MAX_NEW, temperature=0., top_k=0,
                          device="cpu", eos_id=2, stop_token_sequences=[[4]], logits_last_only=True,
                          return_metadata=True)
    exact = previous.first_use.strict(answer) == previous.first_use.strict(expected)
    return dict(root=case["root"], expected=expected, answer=answer, ids=capture.ids,
                exact=exact, exact_with_end=exact and meta["finish_reason"] in ("EOS", "STOP_SEQUENCE"),
                finish=meta["finish_reason"])


def score(model, tok, rows, check):
    outputs = {"repeat": [], "switch": []}
    with torch.no_grad():
        for item in rows:
            check()
            for first in range(2):
                for mode, last in (("repeat", first), ("switch", 1-first)):
                    response = generate(model, tok, item, user_prompt(item, first, last), item["names"][last])
                    outputs[mode].append(dict(response, first=item["names"][first],
                        copied_previous=previous.first_use.strict(response["answer"]) ==
                        previous.first_use.strict(item["names"][first])))
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("CPU-only mode and a timezone-aware deadline are required")
    def check():
        if time.time() >= args.stop_by.timestamp():
            raise TimeoutError("the approved CPU experiment window ended")
    check()
    ARTIFACT.mkdir(exist_ok=False)
    started = time.monotonic()
    pins, tok, pools = cases_and_pins()
    torch.set_num_threads(3)
    arm = native.read_json(previous.first_use.pair.OUT / "readback.json")["arms"][previous.POLICY]
    model = native.load_model(previous.ROOT / arm["checkpoint"], arm["updates"], "cpu")
    model.requires_grad_(False)
    cohorts = {"repeat": [], "switch": []}
    outcomes, summaries, counts = {}, {}, {}
    train_names = {speaker for case in pools["candidate_train"] for speaker in case["names"]}
    picks = np.random.default_rng(1337).integers(0, 2*len(pools["candidate_train"]), (UPDATES, BATCH))
    with sdpa_kernel(SDPBackend.MATH):
        for i, case in enumerate(pools["candidate_train"], 1):
            check()
            for target in range(2):
                for name, first in (("repeat", target), ("switch", 1-target)):
                    cohorts[name].append(features(model, tok, user_prompt(case, first, target), case["names"][target]))
            if i % 32 == 0:
                print("SODA_SPEAKER_TRAIN_FEATURES", i, flush=True)
        for index in range(len(cohorts["repeat"])):
            if not torch.equal(cohorts["repeat"][index][1], cohorts["switch"][index][1]):
                raise ValueError("the source pair did not preserve exact answer IDs and supervision")
        native.training.publish(ARTIFACT / "input.json", dict(pins=pins.files, primary="exact_with_normal_end",
            roots_training=len(pools["candidate_train"]), roots_heldout=len(pools["heldout"]),
            rows_per_arm=len(cohorts["repeat"]), steps=UPDATES, draws=UPDATES * BATCH, seed=1337, rank=RANK))
        for name in ("repeat_only", "repeat_and_switch"):
            unchanged = cohorts["repeat"]
            switched = cohorts["switch"] if name == "repeat_and_switch" else None
            adapter, losses = train(model, unchanged, picks, check, switch_examples=switched)
            head = model._head_logits
            with patch.object(model, "_head_logits", lambda hidden: head(adapter(hidden))):
                generated = score(model, tok, pools["heldout"], check)
            outcomes[name] = generated
            counts[name] = dict(unique_pool_targets=sum(len(row[1]) for row in unchanged),
                sampled_targets=sum(len(unchanged[i][1]) for i in picks.flatten()),
                switch_draws=UPDATES * BATCH // 2 if switched is not None else 0,
                first_loss=losses[0], final_loss=losses[-1])
            summaries[name] = {
                context: dict(rows=len(values), exact=sum(r["exact"] for r in values),
                              exact_with_end=sum(r["exact_with_end"] for r in values),
                              copied_previous=sum(r["copied_previous"] for r in values),
                              unseen_names=sum(r["expected"] not in train_names for r in values),
                              unseen_name_exact_with_end=sum(r["expected"] not in train_names and r["exact_with_end"]
                                                            for r in values))
                for context, values in generated.items()}
            native.training.publish(ARTIFACT / f"{name}.json", dict(summary=summaries[name], outputs=generated,
                training=counts[name], model_sha256=arm["checkpoint_sha256"]))
            print("SODA_SPEAKER_ADAPTER_ARM_COMPLETE", name, summaries[name], flush=True)
    pins.unchanged()
    native.training.publish(ARTIFACT / "report.json", dict(status="COMPLETE", summary=summaries,
        model_sha256=arm["checkpoint_sha256"], input_counts=counts, rank=RANK, base_weights_changed=False,
        teacher_calls=0, corpus_rows_admitted=0, official_student_training=False, seconds=time.monotonic()-started))


if __name__ == "__main__":
    main()
