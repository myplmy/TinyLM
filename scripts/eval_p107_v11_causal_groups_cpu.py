"""Score P107 matched checkpoints on frozen lexical groups and causal first answers."""

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
import unicodedata

import numpy as np
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import eval_p109b_first_use as first
from scripts import run_p107_v11_mask_pair as pair
from tinylm.config import TMTConfig
from tinylm.infer.generate import sample
from tinylm.model import TiedMLPTransformer
from tinylm.train.hybrid_mntp import causal_batch


SEED = 20261121
MICROS = 32


def validation(index):
    source = pair.documents.BinaryDocumentSource(index["splits"]["val"], batch=pair.BATCH,
                                                 micros=MICROS, length=pair.LENGTH, seed=SEED)
    return source.next_update()


def frame_sha(frames):
    digest = hashlib.sha256()
    for tokens, docs in frames:
        digest.update(tokens.numpy().tobytes())
        digest.update(docs.numpy().tobytes())
    return digest.hexdigest().upper()


def prepare(index, index_path, index_sha, target, tok):
    source = index["splits"]["train"]["binary"]
    path = Path(source["path"])
    if pair.documents.pin(path) != source:
        raise ValueError("the admitted training-frequency source differs")
    data = np.memmap(path, mode="r", dtype="<u2")
    count = np.zeros(pair.supervisor.VOCAB, dtype=np.int64)
    for start in range(0, len(data), 4_194_304):
        count += np.bincount(data[start:start + 4_194_304], minlength=len(count))
    if pair.documents.pin(path) != source or count.sum() != len(data):
        raise ValueError("the training frequencies do not close at the admitted corpus size")
    ordinary = np.arange(len(count)) > 34
    groups = {"unseen": np.flatnonzero(ordinary & (count == 0)).tolist(),
              "train_1_to_32": np.flatnonzero(ordinary & (count >= 1) & (count <= 32)).tolist(),
              "train_33_to_1024": np.flatnonzero(ordinary & (count >= 33) & (count <= 1024)).tolist(),
              "train_above_1024": np.flatnonzero(ordinary & (count > 1024)).tolist(),
              "hangul": [], "latin": [], "decimal": []}
    for token in np.flatnonzero(ordinary):
        text = tok.decode([int(token)])
        names = [unicodedata.name(char, "") for char in text]
        if any("HANGUL" in name for name in names):
            groups["hangul"].append(int(token))
        if any("LATIN" in name for name in names):
            groups["latin"].append(int(token))
        if any(char.isdecimal() for char in text):
            groups["decimal"].append(int(token))
    frames = validation(index)
    targets = np.zeros(len(count), dtype=np.int64)
    for tokens, docs in frames:
        suffix = tokens[:, 1:][docs[:, :-1] == docs[:, 1:]]
        targets += np.bincount(suffix.numpy(), minlength=len(count))
    report = dict(index_profile=str(index_path), index_sha256=index_sha, seed=SEED, micros=MICROS,
                  source_sha256=pair.evaluation.core6.digest(Path(__file__)),
                  frame_sha256=frame_sha(frames), train_tokens=len(data), validation_targets=int(targets.sum()),
                  groups=groups, group_targets={name: int(targets[ids].sum()) for name, ids in groups.items()},
                  first_use_questions=16, precision="CPU_FP32_MATH")
    pair.supervisor.publish(target, report)
    print("P107_CAUSAL_GROUP_PROFILE", pair.evaluation.core6.digest(target), report["group_targets"], flush=True)


def checkpoint_model(arm, end):
    proof = arm["final"]
    path = pair.evaluation.regular_file(Path(proof["path"]))
    if proof["updates"] != end or proof["slots"] != end * pair.SLOTS or pair.evaluation.core6.digest(path) != proof["sha256"]:
        raise ValueError("the exact matched boundary differs")
    stored = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    student = stored["session"]["trainer"]
    if student["cursor"] != end or student["mode"] != arm["arm"] or stored["initial_sha256"] != arm["initial_sha256"]:
        raise ValueError("the checkpoint contents do not close the same arm and sample budget")
    cfg = TMTConfig(**stored["cfg"])
    model = TiedMLPTransformer(cfg).eval()
    model.load_state_dict(student["model"], strict=True)
    model.freeze_quant()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the causal evaluation must retain the native repeat route")
    return model


def score_model(model, frames, profile, tok, check):
    group_masks = {}
    for name, ids in profile["groups"].items():
        group_masks[name] = torch.zeros(pair.supervisor.VOCAB, dtype=torch.bool)
        group_masks[name][ids] = True
    sizes, hits, loss = Counter(), Counter(), Counter()
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for tokens, docs in frames:
            check()
            batch = causal_batch(tokens, docs, vocab_size=pair.supervisor.VOCAB)
            logits = model(batch.inputs, attention_mask=batch.attention_mask, allow_fixed_g4_r2=True)
            valid = batch.targets != -100
            maxima = logits.argmax(-1)
            nll = F.cross_entropy(logits.flatten(0, 1), batch.targets.flatten(), reduction="none").reshape_as(batch.targets)
            masks = {name: group[batch.targets.clamp_min(0)] & valid for name, group in group_masks.items()}
            masks["all_valid"] = valid
            for name, active in masks.items():
                sizes[name] += int(active.sum())
                hits[name] += int((maxima[active] == batch.targets[active]).sum())
                loss[name] += float(nll[active].sum(dtype=torch.float64))
            del logits
        outputs = []
        for case in first.examples(tok):
            check()
            capture = first.DecodeSuffix(tok, case["input_ids"])
            text, meta = sample(model, model.cfg, capture, case["prompt"], max_new=first.ANSWER, temperature=0.,
                                top_k=0, device="cpu", eos_id=2, use_cache=True, logits_last_only=True,
                                return_metadata=True, stop_token_sequences=[[4]])
            ended = meta["finish_reason"] in ("EOS", "STOP_SEQUENCE")
            outputs.append(dict(case=case["case"], language=case["language"], expected=case["answer"], answer=text,
                                ids=capture.ids, finish=meta["finish_reason"], ended=ended,
                                exact=first.strict(text) == first.strict(case["answer"])))
    if any(sizes[name] != count for name, count in profile["group_targets"].items()) or sizes["all_valid"] != profile["validation_targets"]:
        raise ValueError("the lexical evaluation target counts differ from the sealed profile")
    groups = {name: dict(targets=n, argmax_hits=hits[name], nll=loss[name] / n if n else None)
              for name, n in sizes.items()}
    return dict(groups=groups, first_use=outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "score"))
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--index-sha256", required=True)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--training-record", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("CPU-only device mask required")
    torch.set_num_threads(3)
    index_path = args.index.absolute()
    index_sha = pair.supervisor.digest(args.index_sha256)
    index = pair.load_index(index_path, index_sha)
    tok = pair.evaluation.load_tokenizer()
    if args.mode == "prepare":
        prepare(index, index_path, index_sha, args.profile, tok)
        return 0
    if not all((args.profile_sha256, args.training_record, args.record, args.stop_by)) or args.stop_by.tzinfo is None:
        parser.error("the score needs a matched training receipt, sealed profile, output and cutoff")
    cutoff = args.stop_by.timestamp()

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the authorized CPU quality window ended")

    profile = json.loads(pair.supervisor.manifest_bytes(args.profile.absolute(), args.profile_sha256))
    terminal = pair.evaluation.read_json(args.training_record / "supervisor.json")
    report = pair.evaluation.read_json(args.training_record / "report.json")
    frames = validation(index)
    if (terminal["returncode"] or terminal["stop_reason"] is not None
            or report["status"] not in {"FULL_300M_PAIR", "MATCHED_PARTIAL_BUDGET_PAIR"}
            or profile["source_sha256"] != pair.evaluation.core6.digest(Path(__file__))
            or profile["index_sha256"] != index_sha or profile["frame_sha256"] != frame_sha(frames)):
        raise ValueError("the matched training terminal or frozen quality profile differs")
    control, adaptive = (report["arms"][name] for name in pair.ARMS)
    if any(control[key] != adaptive[key] for key in ("end", "initial_sha256", "source_end_rng", "causal_targets")):
        raise ValueError("the pair must have matched initialization, exposure and boundaries")
    check()
    args.record.mkdir(exist_ok=False)
    proof = {}
    for arm in (control, adaptive):
        check()
        name = arm["arm"]
        result = score_model(checkpoint_model(arm, arm["end"]), frames, profile, tok, check)
        result.update(checkpoint_sha256=arm["final"]["sha256"], steps=arm["end"], profile_sha256=args.profile_sha256)
        source = args.record / f"{name}.json"
        pair.supervisor.publish(source, result)
        proof[name] = pair.documents.pin(source.absolute())
        print("P107_CAUSAL_GROUP_ARM_COMPLETE", name, arm["end"], flush=True)
    pair.supervisor.publish(args.record / "report.json", dict(status="COMPLETE", training_record=str(args.training_record),
                            source_sha256=pair.evaluation.core6.digest(Path(__file__)), arms=proof))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
