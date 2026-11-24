"""Compare conditional likelihoods of the two swapped table values."""

import argparse
from contextlib import ExitStack
import fcntl
import json
import os
from pathlib import Path
import time

import torch
import torch.nn.functional as F

from scripts import run_p109c_table_grounding as grounding
from scripts import run_p109c_correction_scratch as trial
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer


OUT = trial.DATA.parent / "p109c_table_grounding_scores_gpu_v1_20261121"


def candidate_input(tok, prefix, value, end_id):
    text = tok.decode(prefix, skip_special_tokens=False)
    ids = tok.encode(text + str(value) + "<|im_end|>").ids
    if ids[:len(prefix)] != prefix or ids[-1] != end_id or len(ids) > trial.WIDTH:
        raise ValueError("candidate continuation does not preserve its prompt and end marker")
    return ids[:-1], ids[len(prefix):], len(prefix)-1


def score(model, batch, pad_id, end_id):
    length = max(len(ids) for ids, _, _ in batch)
    x = torch.tensor([ids + [pad_id]*(length-len(ids)) for ids, _, _ in batch], device="cuda")
    rows, pos, gold, first = [], [], [], []
    for row, (_, labels, start) in enumerate(batch):
        first.append(len(rows))
        rows.extend([row]*len(labels))
        pos.extend(range(start, start+len(labels)))
        gold.extend(labels)
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        hidden = model(x, return_hidden=True)
        logits = model._head_logits(hidden[rows, pos]).float()
        logp = F.log_softmax(logits, dim=-1)
        nll = -logp[torch.arange(len(gold), device=x.device), torch.tensor(gold, device=x.device)]
        first_rows = logp[first]
        first_end_prob = first_rows[:, end_id].exp().tolist()
        first_top = first_rows.argmax(-1).tolist()
    positions = nll.tolist()
    details = []
    for index, (_, labels, _) in enumerate(batch):
        parts = positions[first[index]:first[index]+len(labels)]
        details.append(dict(content_nll=sum(parts[:-1]), end_nll=parts[-1], content_tokens=len(parts)-1,
                            first_end_probability=first_end_prob[index], first_top_is_end=first_top[index] == end_id))
    return details


def read_grounding(output, tag):
    run = trial.read_json(output / "report.json")
    sup = trial.read_json(output / "supervisor.json")
    weights_file = output / "foundation.pt"
    if (sup["returncode"] != 0 or sup["stop_reason"] is not None or run["tag"] != tag
            or run["parent"] is not None or run["checkpoint_sha256"] != trial.file_sha(weights_file)):
        raise ValueError("the finished grounding checkpoint and its CUDA receipt are required")
    return run, weights_file


def familiar_prompts(tok, data):
    cases = []
    for row in data:
        swap = list(row["values"])
        a, b = row["field"], row["other"]
        swap[a], swap[b] = swap[b], swap[a]
        prompts = [grounding.generation_prompt(tok, grounding.form(values, row["order"], a, row["language"], 0)[0])
                   for values in (row["values"], swap)]
        cases.append({**row, "prompts": prompts})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-ntp", action="store_true")
    changed = parser.parse_args().context_ntp
    output = OUT
    model_output, tag = grounding.OUT, grounding.TAG
    if changed:
        from scripts import run_p109c_table_context_ntp as context_ntp

        model_output, tag = context_ntp.OUT, context_ntp.TAG
        output = OUT.with_name("p109c_table_context_ntp_scores_gpu_v1_20261121")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or output.exists() or trial.CUTOFF.timestamp()-time.time() < 90:
        raise ValueError("requires a fresh output and one authorized CUDA device")
    run, weights_file = read_grounding(model_output, tag)
    if changed:
        preflight = trial.ROOT/"test_result/109_log_20261121_P109C_TableContextNTP_CPU.txt"
        if run["preflight_sha256"] != trial.file_sha(preflight):
            raise ValueError("trained context receipt changed")
        context_ntp.read_receipt(preflight)
        grounding.sealed(context_ntp.BASE_RECEIPT)
    else:
        grounding.sealed(run["preflight_sha256"])
    tok, special, _, _, _ = trial.load_cases()
    cases = trial.read_json(grounding.DATA / "evaluation.json")["wide"]
    end = special["<|im_end|>"]
    batches = [candidate_input(tok, prefix, value, end) for case in cases
               for prefix in case["prompts"] for value in case["gold"]]
    with ExitStack() as cleanup:
        lock = os.open(trial.ROOT / "runs", os.O_RDONLY | os.O_DIRECTORY)
        cleanup.callback(os.close, lock)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        total, used = trial.idle_gpu()
        torch.cuda.set_per_process_memory_fraction((trial.CARD_LIMIT_MIB-used-512)/total)
        torch.set_num_threads(1)
        state = torch.load(weights_file, weights_only=True, map_location="cpu")
        if state["tag"] != tag or state["parent"] is not None or trial.state_sha(state["model"]) != run["state_sha256"]:
            raise ValueError("the internal trained state differs from its receipt")
        model = TiedMLPTransformer(TMTConfig(**state["config"]))
        model.load_state_dict(state["model"])
        model = model.to("cuda").eval()
        model.clear_quant()
        if len(model.visit_schedule()) != 28:
            raise ValueError("R2 required for trained-state readback")
        scores = [row for start in range(0, len(batches), grounding.BATCH)
                  for row in score(model, batches[start:start+grounding.BATCH], special["<pad>"], end)]
        familiar = grounding.evaluate(model, tok, special, familiar_prompts(tok, cases), paired=True) if changed else None
    pairs = []
    for index, row in enumerate(cases):
        aa, ab, ba, bb = scores[index*4:index*4+4]
        nll_delta = [ab["content_nll"]-aa["content_nll"], ba["content_nll"]-bb["content_nll"]]
        end_delta = [ab["end_nll"]-aa["end_nll"], ba["end_nll"]-bb["end_nll"]]
        measured = [[aa, ab], [ba, bb]]
        pairs.append(dict(root=row["root"], gold=row["gold"], same_length=len({t["content_tokens"] for t in (aa, ab, ba, bb)}) == 1,
                          nll_margin=nll_delta, total_margin=[a+b for a, b in zip(nll_delta, end_delta)], scores=measured))
    comparable = [pair for pair in pairs if pair["same_length"]]
    first = [pair["scores"][side][side] for pair in pairs for side in (0, 1)]
    summary = dict(n=len(pairs), equal_length_pairs=len(comparable),
                   joint_content=sum(min(pair["nll_margin"]) > 0 for pair in comparable),
                   joint_with_end=sum(min(pair["total_margin"]) > 0 for pair in comparable),
                   first_end_top=sum(value["first_top_is_end"] for value in first),
                   first_end_probability=sum(value["first_end_probability"] for value in first)/len(first))
    output.mkdir()
    if familiar is not None:
        trial.publish(output / "familiar_wording.json", familiar)
        summary["familiar_joint"] = familiar["both_correct"]
    trial.publish(output / "report.json", dict(summary=summary, checkpoint=run["checkpoint_sha256"], pairs=pairs,
                  source_sha256=trial.file_sha(Path(__file__))))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
