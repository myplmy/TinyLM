"""Train a matched table model with a contrast at the first differing answer token."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

from scripts import diag_p109c_table_grounding_scores as scores
from scripts import p109_cuda_owner as owner
from scripts import run_p109c_correction_scratch as trial
from scripts import run_p109c_table_context_ntp as control
from scripts import run_p109c_table_grounding as data
from tinylm.model import TiedMLPTransformer
from tinylm.train.mtp_sft import IGNORE


TAG = "p109c_table_first_divergence_gpu_v1_20261121"
INPUT = trial.DATA.parent / (TAG + "_inputs")
OUT = trial.DATA.parent / TAG
CONTROL_RECEIPT = trial.ROOT / "test_result/109_log_20261121_P109C_TableContextNTP_CPU.txt"
RANK_WEIGHT = 0.1


def sources():
    paths = Path(__file__), Path(owner.__file__), Path(scores.__file__)
    return {**control.sources(), **{str(p.relative_to(trial.ROOT)): trial.file_sha(p) for p in paths}}


def select_margin(logits, targets, sites):
    """Convert each real (row, shifted position) to the selected-logit row."""
    position, foil = sites.unbind(-1)
    compared = position.ge(0)
    rows = torch.arange(targets.size(0), device=targets.device)[:, None].expand_as(position)[compared]
    target_positions, alternatives = position[compared], foil[compared]
    ordinal = targets.ne(IGNORE).flatten().cumsum(0).view_as(targets) - 1
    take = ordinal[rows, target_positions]
    gold = targets[rows, target_positions]
    return logits[take, alternatives].float() - logits[take, gold].float()


def check_selection():
    label = torch.tensor([[IGNORE, 3, 1, IGNORE, IGNORE], [IGNORE, 5, 6, 1, IGNORE]])
    dense = torch.arange(2*5*11, dtype=torch.float32).reshape(2, 5, 11)
    dense[1, 2, 8] += 4.5
    site = torch.tensor([[[-1, -1]], [[2, 8]]])
    actual = select_margin(dense[label.ne(IGNORE)], label, site)
    torch.testing.assert_close(actual, (dense[1, 2, 8] - dense[1, 2, 6]).reshape(1))


def comparison_sites(tokenizer, end_id, tokens, answer):
    sites = np.full((len(tokens), 3, 2), -1, dtype=np.int16)
    for i, (x, y) in enumerate(zip(tokens, answer, strict=True)):
        supervised = np.flatnonzero(y != IGNORE)
        first = int(supervised[0])
        gold = y[supervised].tolist()
        prefix = x[:first+1].tolist()
        prompt = tokenizer.decode(prefix, skip_special_tokens=False)
        values = re.findall(r": ([0-9]+)", prompt)
        true_value = tokenizer.decode(gold[:-1], skip_special_tokens=False)
        if (len(values) != 4 or len(set(values)) != 4 or true_value not in values or gold[-1] != end_id
                or supervised.tolist() != list(range(first, first+len(gold)))):
            raise ValueError(f"expected a canonical table and a contiguous supervised answer on row {i}")
        for slot, other in enumerate(v for v in values if v != true_value):
            _, rival, _ = scores.candidate_input(tokenizer, prefix, other, end_id)
            for position, (true, foil) in enumerate(zip(gold[:-1], rival[:-1])):
                if true != foil:
                    sites[i, slot] = first + position, foil
                    break
    return sites


def prepare():
    if INPUT.exists() or OUT.exists():
        raise FileExistsError(INPUT)
    check_selection()
    frozen = control.read_receipt(CONTROL_RECEIPT)
    baseline = trial.read_json(control.OUT / "report.json")
    terminal = trial.read_json(control.OUT / "supervisor.json")
    if (baseline["preflight_sha256"] != trial.file_sha(CONTROL_RECEIPT) or terminal["returncode"] != 0
            or terminal["stop_reason"] is not None or baseline["initial_sha256"] != frozen["initial_sha256"]):
        raise ValueError("the completed context NTP control is required")
    tokenizer, special, (x, y, _), stages, _ = control.profile()
    end = special["<|im_end|>"]
    sites = comparison_sites(tokenizer, end, x, y)
    present = sites[:, :, 0] >= 0
    rows, slots = np.nonzero(present)
    target_pos, foils = sites[rows, slots].T
    gold = y[rows, target_pos]
    if np.any((gold == IGNORE) | (gold == end) | (gold == foils) | (foils == end)):
        raise ValueError("comparison uses padding, EOS or the same token")
    if np.any(present.reshape(-1, data.BATCH, 3).sum(axis=(1, 2)) == 0):
        raise ValueError("a comparison batch has no comparable content")
    offsets = target_pos - np.argmax(y[rows] != IGNORE, axis=1)
    counts = []
    for phase in stages:
        start, size = phase["offset"], phase["rows"]
        in_phase = (rows >= start) & (rows < start+size)
        counts.append(dict(stage=phase["stage"], alternatives=3*size, compared=int(in_phase.sum()),
                           later_than_first=int(np.count_nonzero(offsets[in_phase] > 0))))
    INPUT.mkdir()
    with (INPUT / "sites.npz").open("xb") as stream:
        np.savez_compressed(stream, sites=sites)
    return dict(tag=TAG, sources=sources(), comparisons=counts, rank_weight=RANK_WEIGHT,
                sites_sha256=trial.file_sha(INPUT / "sites.npz"), context_receipt_sha256=trial.file_sha(CONTROL_RECEIPT),
                context_run_sha256=trial.file_sha(control.OUT / "report.json"))


def load_receipt(path):
    ready = trial.read_json(path)
    if (ready["tag"] != TAG or ready["sources"] != sources() or ready["rank_weight"] != RANK_WEIGHT
            or ready["sites_sha256"] != trial.file_sha(INPUT / "sites.npz")
            or ready["context_receipt_sha256"] != trial.file_sha(CONTROL_RECEIPT)
            or ready["context_run_sha256"] != trial.file_sha(control.OUT / "report.json")):
        raise ValueError("the sealed first-divergence preflight differs")
    return ready


def worker(receipt_path, fraction):
    ready = load_receipt(receipt_path)
    frozen = control.read_receipt(CONTROL_RECEIPT)
    tokenizer, special, arrays, stages, _ = control.profile()
    if stages != frozen["stages"]:
        raise ValueError("the context and answer positions differ from the control")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA BF16 required")
    x, y, context = [torch.from_numpy(v).to("cuda", dtype=torch.long) for v in arrays]
    with np.load(INPUT / "sites.npz", allow_pickle=False) as loaded:
        sites = torch.from_numpy(loaded["sites"]).to("cuda", dtype=torch.long)
    torch.manual_seed(data.SEED)
    model = TiedMLPTransformer(trial.make_config())
    initial = trial.state_sha(model.state_dict())
    if initial != frozen["initial_sha256"] or len(model.visit_schedule()) != 28:
        raise ValueError("initial model or recursive route differs from the control")
    model.to("cuda")
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=.01, fused=True)
    evaluation = trial.read_json(data.DATA / "evaluation.json")
    step = 0
    stage_results = []
    started = time.perf_counter()
    print(f"START {TAG}", flush=True)
    for phase, comparisons in zip(stages, ready["comparisons"], strict=True):
        sums = torch.zeros(3, device="cuda")
        answer_count, prefix_count, rank_count = 0, 0, 0
        offset = phase["offset"]
        for start in range(offset, offset+phase["rows"], data.BATCH):
            block = slice(start, start+data.BATCH)
            tokens, answer, prefix = x[block], y[block], context[block]
            keep, keep_prefix = answer.ne(IGNORE), prefix.ne(IGNORE)
            target, prompt = answer[keep], prefix[keep_prefix]
            step += 1
            optimizer.param_groups[0]["lr"] = .0015 * min(1., step/64) * (1 - .7*(step/data.UPDATES)**2)
            model.set_anneal(min(1., step/(.6*data.UPDATES)))
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                hidden = model(tokens, return_hidden=True)
                logits = model._head_logits(hidden[keep])
                answer_sum = F.cross_entropy(logits.float(), target, reduction="sum")
                nll, _ = control.target_nll(model, hidden[keep_prefix].unsqueeze(0), prompt.unsqueeze(0), rows=control.CE_ROWS)
                prefix_sum = nll.sum()
                margin = select_margin(logits, answer, sites[block])
                rank_sum = F.softplus(margin).sum()
                loss = (answer_sum/target.numel() + control.WEIGHT*prefix_sum/prompt.numel()
                        + RANK_WEIGHT*rank_sum/margin.numel())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            answer_count += target.numel()
            prefix_count += prompt.numel()
            rank_count += margin.numel()
            sums += torch.stack([answer_sum.detach(), prefix_sum.detach(), rank_sum.detach()])
            if step % 128 == 0:
                print(json.dumps(dict(stage=phase["stage"], step=step, wall=time.perf_counter()-started,
                       losses=[v/n for v,n in zip(sums.tolist(), (answer_count, prefix_count, rank_count))])), flush=True)
        counts = answer_count, prefix_count, rank_count
        if counts != (phase["targets"], phase["context_targets"], comparisons["compared"]):
            raise RuntimeError("training target counts differ from the sealed comparison")
        model.eval()
        model.clear_quant()
        key = "two_digit" if phase["stage"] == "two_digit" else "wide"
        result = data.evaluate(model, tokenizer, special, evaluation[key], paired=True)
        info = dict(stage=phase["stage"], step=step, counts=counts, joint=result["both_correct"],
                    nonempty=result["nonempty_answers"], by_language=result["by_language"],
                    losses=[v/n for v,n in zip(sums.tolist(), counts)])
        trial.publish(OUT / f"{phase['stage']}_eval.json", result)
        stage_results.append(info)
        print(json.dumps(info), flush=True)
        model.train()
        model.clear_quant()
    if step != data.UPDATES:
        raise RuntimeError("optimizer update count differs")
    model.eval()
    val = data.evaluate(model, tokenizer, special, evaluation["original"], paired=False)
    trial.publish(OUT / "original_eval.json", val)
    final = stage_results[-1]
    gate = (final["joint"] >= data.GATE["wide_pairs"] and min(final["by_language"].values()) >= data.GATE["language_pairs"]
            and val["exact_with_eot"] >= data.GATE["original_single"])
    state = {name: param.detach().cpu() for name, param in model.state_dict().items()}
    saved = OUT / "foundation.pt"
    with saved.open("xb") as stream:
        torch.save(dict(model=state, config=asdict(model.cfg), parent=None, step=step, tag=TAG), stream)
    if ready != load_receipt(receipt_path):
        raise RuntimeError("sealed comparison changed during training")
    trial.publish(OUT / "report.json", dict(tag=TAG, parent=None, initial_sha256=initial,
                  preflight_sha256=trial.file_sha(receipt_path), checkpoint_sha256=trial.file_sha(saved),
                  state_sha256=trial.state_sha(state), updates=step, stages=stage_results, gate=gate,
                  original=val["exact_with_eot"], wall=time.perf_counter()-started,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                  peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))
    print(f"FINISH {TAG} gate={gate} exchange={final['joint']}/64 original={val['exact_with_eot']}/64", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(json.dumps(prepare(), indent=2))
        return 0
    if args.receipt is None or args.stop_by is None:
        parser.error("run requires --receipt and --stop-by")
    load_receipt(args.receipt)
    return owner.supervise(worker, (args.receipt,), OUT, args.stop_by, authorization_end=trial.CUTOFF, min_seconds=1200)


if __name__ == "__main__":
    sys.exit(main())
