"""Jointly learn first-token value location and selection among visible value pieces."""

import argparse
from dataclasses import asdict
from datetime import datetime
from functools import lru_cache
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from scripts import run_p109c_table_value_link as baseline


TAG = "p109c_first_answer_value_bridge_gpu_v1_20261121"
OUT = baseline.OUT.with_name(TAG)
INPUT = OUT.with_name(TAG + "_inputs")
trial, data, control = baseline.trial, baseline.data, baseline.control
REFERENCE = trial.ROOT / "test_result/109_log_20261121_P109C_TableValueLink_CPU.txt"
AUTHORIZATION_END = datetime.fromisoformat("2026-11-21T17:00:00+09:00")
BRIDGE_WEIGHT = .10


def first_piece_loss(logits, first, options, unique, target, use):
    scores = logits[first[:, None], options].masked_fill(~unique, -torch.inf)
    costs = F.cross_entropy(scores, target, reduction="none")
    return (costs * use).sum()


def verify_fixture():
    scores = torch.tensor([[0., 2., 3., 5.], [2., 1., 3., .4]], requires_grad=True)
    ids = torch.tensor(((1, 1, 2, 3), (0, 1, 1, 2)))
    distinct = torch.tensor(((True, False, True, True), (True, True, False, True)))
    gold = torch.tensor((0, 0))
    selected = torch.tensor((True, False))
    found = first_piece_loss(scores, torch.arange(2), ids, distinct, gold, selected)
    expected = F.cross_entropy(scores[:1, [1, 2, 3]], torch.tensor([0]))
    torch.testing.assert_close(found, expected)
    actual_grad, = torch.autograd.grad(found, scores)
    expected_grad, = torch.autograd.grad(expected, scores)
    torch.testing.assert_close(actual_grad, expected_grad)


def base_contract():
    control_receipt = baseline.load_receipt(REFERENCE)
    result = baseline.OUT / "report.json"
    terminal = baseline.OUT / "supervisor.json"
    measured, exit_status = trial.read_json(result), trial.read_json(terminal)
    if (measured["tag"] != baseline.TAG or measured["parent"] is not None or measured["updates"] != data.UPDATES
            or measured["initial_sha256"] != control_receipt["initial"] or exit_status["returncode"]
            or exit_status["stop_reason"] or measured["preflight_sha256"] != trial.file_sha(REFERENCE)):
        raise ValueError("requires the completed same-data first-position value link")
    return dict(tag=TAG, source=trial.file_sha(Path(__file__)), baseline=trial.file_sha(REFERENCE),
                baseline_report=trial.file_sha(result), baseline_terminal=trial.file_sha(terminal),
                initial=control_receipt["initial"], stages=control_receipt["stages"], weight=BRIDGE_WEIGHT)


def preflight():
    if INPUT.exists() or OUT.exists():
        raise FileExistsError(INPUT)
    plan = base_contract()
    tokenizer, _, (x, y, _), phases, _ = control.profile()
    if phases != plan["stages"]:
        raise ValueError("the authored training schedule changed")
    with np.load(baseline.INPUT / "sites.npz", allow_pickle=False) as arrays:
        places = arrays["sites"]

    @lru_cache(maxsize=None)
    def first_piece(value):
        return tokenizer.encode(value, add_special_tokens=False).ids[0]

    options = np.empty((len(x), 4), dtype=np.int32)
    unique = np.empty((len(x), 4), dtype=bool)
    target = np.empty(len(x), dtype=np.int8)
    for index, (tokens, labels, sites) in enumerate(zip(x, y, places, strict=True)):
        first = int(sites[0])
        names = baseline.VALUE.findall(tokenizer.decode(tokens[:first + 1].tolist(), skip_special_tokens=False))
        if len(names) != 4 or len(set(names)) != 4:
            raise ValueError("an authored table lacks four distinct numeric values")
        choices = [first_piece(value) for value in names]
        gold = int(labels[first])
        if choices[int(sites[-1])] != gold:
            raise ValueError("first content target disagrees with the original selected value")
        options[index] = choices
        unique[index] = [token not in choices[:column] for column, token in enumerate(choices)]
        target[index] = choices.index(gold)
    verify_fixture()
    INPUT.mkdir()
    file = INPUT / "first_pieces.npz"
    with file.open("xb") as out:
        np.savez_compressed(out, options=options, unique=unique, target=target)
    return dict(plan, metadata=trial.file_sha(file), candidate_rows=int((unique.sum(axis=1) > 1).sum()),
                duplicates=int(unique.size - unique.sum()))


def load_plan(receipt):
    checked = trial.read_json(receipt)
    if (any(checked[k] != v for k, v in base_contract().items())
            or checked["metadata"] != trial.file_sha(INPUT / "first_pieces.npz")):
        raise ValueError("the comparison conditions or candidates changed")
    return checked


def worker(receipt, fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    if not torch.cuda.is_bf16_supported():
        raise ValueError("CUDA BF16 required")
    plan = load_plan(receipt)
    tok, special, arrays, phases, _ = control.profile()
    if phases != plan["stages"]:
        raise ValueError("the split changed")
    x, y, context = [torch.as_tensor(v, device="cuda", dtype=torch.long) for v in arrays]
    with np.load(baseline.INPUT / "sites.npz", allow_pickle=False) as located:
        sites = torch.as_tensor(located["sites"], device="cuda", dtype=torch.long)
    with np.load(INPUT / "first_pieces.npz", allow_pickle=False) as first:
        options = torch.as_tensor(first["options"], device="cuda", dtype=torch.long)
        unique = torch.as_tensor(first["unique"], device="cuda")
        targets = torch.as_tensor(first["target"], device="cuda", dtype=torch.long)
    eligible = unique.sum(dim=1) > 1
    if len(x) != len(options) or int(eligible.sum().item()) != plan["candidate_rows"]:
        raise ValueError("the CPU and GPU candidate shapes differ")
    validation = trial.read_json(baseline.INPUT / "validation.json")
    evaluation = trial.read_json(data.DATA / "evaluation.json")
    torch.manual_seed(data.SEED)
    model = baseline.TiedMLPTransformer(trial.make_config())
    if trial.state_sha(model.state_dict()) != plan["initial"] or len(model.visit_schedule()) != 28:
        raise ValueError("the frozen initial state or route differs")
    selector = baseline.ValueLink(model.cfg.dim)
    model.to("cuda")
    selector.to("cuda")
    parameters = [*model.parameters(), *selector.parameters()]
    optimizer = torch.optim.AdamW(parameters, lr=.0015, weight_decay=.01, fused=True)
    step, stage_results = 0, []
    started = time.perf_counter()
    print(f"START {TAG}", flush=True)
    for phase in phases:
        stage = phase["stage"]
        bridge_enabled = stage == "wide"
        offset = phase["offset"]
        sums = torch.zeros(4, device="cuda")
        applied = torch.zeros((), dtype=torch.long, device="cuda")
        response_count, context_count, row_count = 0, 0, 0
        for start in range(offset, offset+phase["rows"], data.BATCH):
            block = slice(start, start+data.BATCH)
            answer, prefix = y[block], context[block]
            keep, keep_prefix = answer.ne(baseline.IGNORE), prefix.ne(baseline.IGNORE)
            answer_ids, context_ids = answer[keep], prefix[keep_prefix]
            per_row = keep.sum(dim=1)
            first = per_row.cumsum(0) - per_row
            step += 1
            optimizer.param_groups[0]["lr"] = .0015 * min(1., step/64) * (1 - .7 * (step/data.UPDATES)**2)
            model.set_anneal(min(1., step/(.6 * data.UPDATES)))
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                hidden = model(x[block], return_hidden=True)
                answer_logits = model._head_logits(hidden[keep]).float()
                answer_sum = F.cross_entropy(answer_logits, answer_ids, reduction="sum")
                nll, _ = control.target_nll(model, hidden[keep_prefix].unsqueeze(0),
                                            context_ids.unsqueeze(0), rows=control.CE_ROWS)
                prefix_sum = nll.sum()
                places = sites[block]
                link = selector(hidden, places).float()
                link_sum = F.cross_entropy(link, places[:, -1], reduction="sum")
                if bridge_enabled:
                    used = eligible[block] & link.detach().argmax(dim=1).eq(places[:, -1])
                    bridge_sum = first_piece_loss(answer_logits, first, options[block], unique[block], targets[block], used)
                    applied += used.sum()
                else:
                    bridge_sum = torch.zeros_like(answer_sum)
                loss = (answer_sum/answer_ids.numel() + control.WEIGHT*prefix_sum/context_ids.numel()
                        + baseline.WEIGHT*link_sum/len(answer) + BRIDGE_WEIGHT*bridge_sum/len(answer))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
            optimizer.step()
            response_count += answer_ids.numel()
            context_count += context_ids.numel()
            row_count += len(answer)
            sums += torch.stack([v.detach() for v in (answer_sum,prefix_sum,link_sum,bridge_sum)])
            if step % 128 == 0:
                print(json.dumps(dict(stage=stage, step=step, wall=time.perf_counter()-started,
                                      bridge_rows=int(applied.item()))), flush=True)
        counts = response_count, context_count, row_count
        if counts != (phase["targets"], phase["context_targets"], phase["rows"]):
            raise ValueError("the original supervision counts changed")
        model.eval()
        selector.eval()
        model.clear_quant()
        panel = validation["short" if stage == "two_digit" else "exchange"]
        greedy = data.evaluate(model, tok, special, panel, paired=True)
        slots = baseline.evaluate_slots(model, selector, panel, special["<pad>"])
        trial.publish(OUT / f"{stage}_eval.json", greedy)
        trial.publish(OUT / f"{stage}_slots.json", slots)
        stats = dict(stage=stage, step=step, counts=counts, bridge_rows=int(applied.item()),
                     ce=[value/n for value,n in zip(sums.tolist(), (*counts,row_count), strict=True)],
                     greedy_joint=greedy["both_correct"], by_language=greedy["by_language"],
                     selector_joint=slots["joint"], selector_individual=slots["individual"])
        stage_results.append(stats)
        print(json.dumps(stats), flush=True)
        model.train()
        selector.train()
        model.clear_quant()
    if step != data.UPDATES:
        raise ValueError("updated fewer rows than the original schedule")
    model.eval()
    selector.eval()
    switched = data.evaluate(model, tok, special, validation["question_switch"], paired=True)
    switch_slots = baseline.evaluate_slots(model, selector, validation["question_switch"], special["<pad>"])
    ordinary = data.evaluate(model, tok, special, evaluation["original"], paired=False)
    trial.publish(OUT/"question_switch_eval.json", switched)
    trial.publish(OUT/"question_switch_slots.json", switch_slots)
    trial.publish(OUT/"original_eval.json", ordinary)
    saved = {k:v.detach().cpu() for k,v in model.state_dict().items()}
    checkpoint = OUT/"foundation.pt"
    with checkpoint.open("xb") as handle:
        torch.save(dict(model=saved, train_head={k:v.detach().cpu() for k,v in selector.state_dict().items()},
                        config=asdict(model.cfg), tag=TAG, parent=None, step=step), handle)
    trial.publish(OUT/"report.json", dict(plan=plan, steps=step, stages=stage_results,
                                         original=ordinary["exact_with_eot"], switch=switched["both_correct"],
                                         switch_selector=switch_slots["individual"], state_sha256=trial.state_sha(saved),
                                         checkpoint_sha256=trial.file_sha(checkpoint),
                                         peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                                         peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                                         elapsed=time.perf_counter()-started))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(json.dumps(preflight(), indent=2))
        return 0
    if args.receipt is None or args.stop_by is None:
        parser.error("requires a sealed comparison and authorized cutoff")
    load_plan(args.receipt)
    return baseline.owner.supervise(worker, (args.receipt,), OUT, args.stop_by,
                                    authorization_end=AUTHORIZATION_END, min_seconds=1200)


if __name__ == "__main__":
    raise SystemExit(main())
